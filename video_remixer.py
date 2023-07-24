"""Video Remixer UI state management"""
import os
import shutil
import yaml
from yaml import Loader, YAMLError
from webui_utils.file_utils import split_filepath, remove_directories, create_directory, get_directories, get_files, purge_directories
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf, shrink
from webui_utils.video_utils import details_from_group_name, get_essential_video_details, MP4toPNG, PNGtoMP4, combine_video_audio, combine_videos, PNGtoCustom
from webui_utils.jot import Jot
from webui_utils.mtqdm import Mtqdm
from split_scenes import SplitScenes
from split_frames import SplitFrames
from slice_video import SliceVideo
from resize_frames import ResizeFrames
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from upscale_series import UpscaleSeries

class VideoRemixerState():
    def __init__(self):
        # set at various stages
        self.progress = "home"

        # source video from initial tab
        self.source_video = None # set on clicking New Project
                                 # and again during project set up (pointing to duplicate copy)
        self.video_details = {}
        self.video_info1 = None

        # project set up options
        self.project_path = None
        self.project_fps = None
        self.split_type = None
        self.scene_threshold = None
        self.break_duration = None
        self.break_ratio = None
        self.resize_w = None
        self.resize_h = None
        self.crop_w = None
        self.crop_h = None
        self.deinterlace = None
        self.min_frames_per_scene = None

        # set on confirming set up options
        self.frames_per_minute = None
        self.project_info2 = None # re-set on re-opening project

        # set on confirming project setup
        self.thumbnail_type = None

        # set during project set up
        self.output_pattern = None
        self.frames_path = None
        self.scenes_path = None
        self.dropped_scenes_path = None
        self.thumbnail_path = None
        self.thumbnails = []
        self.clips_path = None
        self.scene_names = []
        self.scene_states = {}
        self.current_scene = None

        # set when done choosing scenes
        self.project_info4 = None # re-set on re-opening project

        # project processing options
        self.resynthesize = False
        self.inflate = False
        self.resize = False
        self.upscale = False
        self.upscale_option = None

        # set during processing
        self.audio_clips_path = None
        self.audio_clips = []
        self.resize_path = None
        self.resynthesis_path = None
        self.inflation_path = None
        self.upscale_path = None
        self.summary_info6 = None # re-set on re-opening project
        self.output_filepath = None
        self.output_quality = None

        # set during final clip creation and remix merging
        self.video_clips_path = None
        self.video_clips = []
        self.clips = []

    def reset(self):
        self.__init__()

    UI_SAFETY_DEFAULTS = {
        "project_fps" : 29.97,
        "deinterlace" : False,
        "split_type" : "Scene",
        "scene_threshold" : 0.6,
        "break_duration" : 2.0,
        "break_ratio" : 0.98,
        "thumbnail_type" : "JPG",
        "resize" : True,
        "resynthesize" : True,
        "inflate" : True,
        "upscale" : True,
        "upscale_option" : "2X"
    }

    # set project settings UI defaults in case the project is reopened
    # otherwise some UI elements get set to None on reopened new projects
    def set_project_ui_defaults(self, default_fps):
        self.project_fps = default_fps
        self.deinterlace = self.UI_SAFETY_DEFAULTS["deinterlace"]
        self.split_type = self.UI_SAFETY_DEFAULTS["split_type"]
        self.scene_threshold = self.UI_SAFETY_DEFAULTS["scene_threshold"]
        self.break_duration = self.UI_SAFETY_DEFAULTS["break_duration"]
        self.break_ratio = self.UI_SAFETY_DEFAULTS["break_ratio"]
        self.thumbnail_type = self.UI_SAFETY_DEFAULTS["thumbnail_type"]
        self.resize = self.UI_SAFETY_DEFAULTS["resize"]
        self.resynthesize = self.UI_SAFETY_DEFAULTS["resynthesize"]
        self.inflate = self.UI_SAFETY_DEFAULTS["inflate"]
        self.upscale = self.UI_SAFETY_DEFAULTS["upscale"]
        self.upscale_option = self.UI_SAFETY_DEFAULTS["upscale_option"]

    # how far progressed into project and the tab ID to return to on re-opening
    PROGRESS_STEPS = {
        "home" : 1,
        "settings" : 1,
        "setup" : 2,
        "choose" : 3,
        "compile" : 4,
        "process" : 5,
        "save" : 6
    }

    def save_progress(self, progress : str, save_project : bool=True):
        self.progress = progress
        if save_project:
            self.save()

    def get_progress_tab(self) -> int:
        try:
            return self.PROGRESS_STEPS[self.progress]
        except:
            return self.PROGRESS_STEPS["home"]

    DEF_FILENAME = "project.yaml"

    def save(self, filepath : str=None):
        filepath = filepath or self.project_filepath()
        with open(filepath, "w", encoding="UTF-8") as file:
            yaml.dump(self, file)

    def project_filepath(self, filename : str=DEF_FILENAME):
        return os.path.join(self.project_path, filename)

    def ingested_video_report(self):
        with Jot() as jot:
            jot.down(f"Source Video: {self.video_details['source_video']}")
            jot.down(f"| Frame Rate | Duration | Display Size | Aspect Ratio | Content Size | Frame Count | File Size | Has Audio |")
            jot.down(f"| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |")
            jot.down(f"| {self.video_details['frame_rate']} | {self.video_details['duration']} | {self.video_details['display_dimensions']} | {self.video_details['display_aspect_ratio']} | {self.video_details['content_dimensions']} | {self.video_details['frame_count_show']} | {self.video_details['file_size']} | {True if self.video_details['has_audio'] else False} |")
        return jot.grab()

    PROJECT_PATH_PREFIX = "REMIX-"

    def ingest_video(self, video_path):
        self.source_video = video_path
        path, filename, _ = split_filepath(video_path)

        with Mtqdm().open_bar(total=1, desc="FFprobe") as bar:
            Mtqdm().message(bar, "Inspecting source video - no ETA")
            try:
                video_details = get_essential_video_details(video_path)
                self.video_details = video_details
            except RuntimeError as error:
                raise ValueError(str(error))
            finally:
                Mtqdm().update_bar(bar)

        project_path = os.path.join(path, f"{self.PROJECT_PATH_PREFIX}{filename}")
        resize_w = video_details['display_width']
        resize_h = video_details['display_height']
        crop_w, crop_h = resize_w, resize_h

        self.project_path = project_path
        self.resize_w = resize_w
        self.resize_h = resize_h
        self.crop_w = crop_w
        self.crop_h = crop_h

    def determine_project_filepath(self, project_path):
        if os.path.isdir(project_path):
            project_file = os.path.join(project_path, VideoRemixerState.DEF_FILENAME)
        else:
            project_file = project_path
            project_path, _, _ = split_filepath(project_path)
        if not os.path.exists(project_file):
            raise ValueError(f"Project file {project_file} was not found")
        return project_file

    def project_settings_report(self):
        with Jot() as jot:
            jot.down(f"Project Path: {self.project_path}")
            if self.split_type == "Scene":
                jot.down(f"| Frame Rate | Deinterlace | Resize To | Crop To | Split Type | Scene Detection Threshold |")
                jot.down(f"| :-: | :-: | :-: | :-: | :-: | :-: |")
                jot.down(f"| {float(self.project_fps):.2f} | {self.deinterlace} | {self.resize_w} x {self.resize_h} | {self.crop_w} x {self.crop_h} | {self.split_type} | {self.scene_threshold} |")
            elif self.split_type == "Break":
                jot.down(f"| Frame Rate | Deinterlace | Resize To | Crop To | Split Type | Minimum Duration | Black Ratio |")
                jot.down(f"| :-: | :-: | :-: | :-: | :-: | :-: | :-: |")
                jot.down(f"| {float(self.project_fps):.2f} | {self.deinterlace} | {self.resize_w} x {self.resize_h} | {self.crop_w} x {self.crop_h} | {self.split_type} | {self.break_duration} | {self.break_ratio} |")
            else:
                self.frames_per_minute = int(float(self.project_fps) * 60)
                jot.down(f"| Frame Rate | Deinterlace | Resize To | Crop To | Split Type | Frames Per Minute |")
                jot.down(f"| :-: | :-: | :-: | :-: | :-: | :-: |")
                jot.down(f"| {float(self.project_fps):.2f} | {self.deinterlace} | {self.resize_w} x {self.resize_h} | {self.crop_w} x {self.crop_h} | {self.split_type} | {self.frames_per_minute} |")
        return jot.grab()

    # keep project's own copy of original video
    # it will be needed later to cut thumbnails and audio clips
    def save_original_video(self, prevent_overwrite=True):
        _, filename, ext = split_filepath(self.source_video)
        video_filename = filename + ext
        # remove single quotes that cause issues with FFmpeg
        filtered_filename = video_filename.replace("'", "")
        project_video_path = os.path.join(self.project_path, filtered_filename)

        if os.path.exists(project_video_path) and prevent_overwrite:
            raise ValueError(
            f"The local project video file already exists, copying skipped: {project_video_path}")

        with Mtqdm().open_bar(total=1, desc="Copying") as bar:
            Mtqdm().message(bar, "Copying source video locally - no ETA")
            shutil.copy(self.source_video, project_video_path)
            self.source_video = project_video_path
            Mtqdm().update_bar(bar)

    # when advancing forward from the Set Up Project step
    # the user may be redoing the project from this step
    # need to purge anything created based on old settings
    # TODO make purging on backing up smarter
    def reset_at_project_settings(self):
        remove_directories([
            self.scenes_path,
            self.dropped_scenes_path,
            self.thumbnail_path,
            self.clips_path,
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path])
        self.scene_names = []
        self.current_scene = 0
        self.thumbnails = []

    FRAMES_PATH = "SOURCE"

    # split video into raw PNG frames
    def render_source_frames(self, global_options, prevent_overwrite=True):
        self.frames_path = os.path.join(self.project_path, self.FRAMES_PATH)
        if prevent_overwrite:
            if os.path.exists(self.frames_path) and get_files(self.frames_path, "png"):
                return None

        video_path = self.source_video
        index_width = self.video_details["index_width"]
        self.output_pattern = f"source_%0{index_width}d.png"
        frame_rate = self.project_fps
        create_directory(self.frames_path)

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Copying source video frames to PNG files - no ETA")
            ffmpeg_cmd = MP4toPNG(video_path,
                                  self.output_pattern,
                                  frame_rate,
                                  self.frames_path,
                                  deinterlace=self.deinterlace,
                                  global_options=global_options)
            Mtqdm().update_bar(bar)
        return ffmpeg_cmd

    def split_scenes(self, log_fn):
        try:
            if self.split_type == "Scene":
                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "Splitting video by detected scene - no ETA")
                    SplitScenes(self.frames_path,
                                self.scenes_path,
                                "png",
                                "scene",
                                self.scene_threshold,
                                0.0,
                                0.0,
                                log_fn).split()
                    Mtqdm().update_bar(bar)

            elif self.split_type == "Break":
                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "Splitting video by detected break - no ETA")
                    SplitScenes(self.frames_path,
                                self.scenes_path,
                                "png",
                                "break",
                                0.0,
                                float(self.break_duration),
                                float(self.break_ratio),
                                log_fn).split()
                    Mtqdm().update_bar(bar)

            else: # split by minute
                SplitFrames(
                    self.frames_path,
                    self.scenes_path,
                    "png",
                    "precise",
                    0,
                    self.frames_per_minute,
                    "copy",
                    False,
                    log_fn).split()
            return None
        except ValueError as error:
            return error
        except RuntimeError as error:
            return error

    # shrink low-frame count scenes related code

    @staticmethod
    def decode_scene_label(scene_label):
        if not scene_label:
            raise ValueError("'scene_label' is required")

        splits = scene_label.split("-")
        if len(splits) != 2:
            raise ValueError(f"scene_label ''{scene_label} is not parsable")

        first, last = int(splits[0]), int(splits[1])
        count = (last - first) + 1
        return first, last, count

    @staticmethod
    def encode_scene_label(num_width, first, last, first_diff, last_diff):
        first = int(first) + int(first_diff)
        last = int(last) + int(last_diff)
        return f"{str(first).zfill(num_width)}-{str(last).zfill(num_width)}"

    @staticmethod
    def move_frames(state, scene_label, scene_label_from):
        log_fn = state["log_fn"]
        path = state["path"]
        from_path = os.path.join(path, scene_label_from)
        to_path = os.path.join(path, scene_label)
        files = get_files(from_path)
        for file in files:
            path, filename, ext = split_filepath(file)
            new_file = os.path.join(to_path, filename + ext)
            log_fn(f"moving {file} to {new_file}")
            shutil.move(file, new_file)

    @staticmethod
    def remove_scene(state, scene_label):
        log_fn = state["log_fn"]
        path = state["path"]
        scene_label_path = os.path.join(path, scene_label)
        log_fn(f"removing {scene_label_path}")
        shutil.rmtree(scene_label_path)

    @staticmethod
    def rename_scene(state, scene_label, new_contents):
        log_fn = state["log_fn"]
        path = state["path"]
        num_width = state["num_width"]
        first, last, _ = VideoRemixerState.decode_scene_label(scene_label)
        new_scene_label = VideoRemixerState.encode_scene_label(num_width, first, last, 0, new_contents)
        scene_label_path = os.path.join(path, scene_label)
        new_scene_label_path = os.path.join(path, new_scene_label)
        log_fn(f"renaming {scene_label_path} to {new_scene_label_path}")
        os.rename(scene_label_path, new_scene_label_path)
        return new_scene_label

    @staticmethod
    def get_container_data(path):
        scene_labels = get_directories(path)
        result = {}
        for scene_label in scene_labels:
            dir_path = os.path.join(path, scene_label)
            count = len(get_files(dir_path))
            result[scene_label] = count
        num_width = len(scene_labels[0].split("-")[0])
        return result, num_width

    def consolidate_scenes(self, log_fn):
        container_data, num_width = VideoRemixerState.get_container_data(self.scenes_path)
        state = {"path" : self.scenes_path,
                 "num_width" : num_width,
                 "log_fn" : log_fn}
        with Mtqdm().open_bar(total=1, desc="Shrink") as bar:
            Mtqdm().message(bar, "Shrinking small scenes - no ETA")
            shrunk_container_data = shrink(container_data, self.min_frames_per_scene, VideoRemixerState.move_frames, VideoRemixerState.remove_scene, VideoRemixerState.rename_scene, state)
            Mtqdm().update_bar(bar)
        log_fn(f"shrunk container data: {shrunk_container_data}")

    THUMBNAILS_PATH = "THUMBNAILS"

    def create_thumbnails(self, log_fn, global_options, remixer_settings):
        self.thumbnail_path = os.path.join(self.project_path, self.THUMBNAILS_PATH)
        create_directory(self.thumbnail_path)

        if self.thumbnail_type == "JPG":
            thumb_scale = remixer_settings["thumb_scale"]
            max_thumb_size = remixer_settings["max_thumb_size"]
            video_w = self.video_details['display_width']
            video_h = self.video_details['display_height']
            max_frame_dimension = video_w if video_w > video_h else video_h
            thumb_size = max_frame_dimension * thumb_scale
            if thumb_size > max_thumb_size:
                thumb_scale = max_thumb_size / max_frame_dimension

            SliceVideo(self.source_video,
                        self.project_fps,
                        self.scenes_path,
                        self.thumbnail_path,
                        thumb_scale,
                        "jpg",
                        0,
                        1,
                        0,
                        False,
                        0.0,
                        0.0,
                        log_fn,
                        global_options=global_options).slice()

        elif self.thumbnail_type == "GIF":
            gif_fps = remixer_settings["default_gif_fps"]
            gif_factor = remixer_settings["gif_factor"]
            gif_end_delay = remixer_settings["gif_end_delay"]
            thumb_scale = remixer_settings["thumb_scale"]
            max_thumb_size = remixer_settings["max_thumb_size"]
            video_w = self.video_details['display_width']
            video_h = self.video_details['display_height']

            max_frame_dimension = video_w if video_w > video_h else video_h
            thumb_size = max_frame_dimension * thumb_scale
            if thumb_size > max_thumb_size:
                thumb_scale = max_thumb_size / max_frame_dimension
            self.thumbnail_path = os.path.join(self.project_path, "THUMBNAILS")
            SliceVideo(self.source_video,
                        self.project_fps,
                        self.scenes_path,
                        self.thumbnail_path,
                        thumb_scale,
                        "gif",
                        0,
                        gif_factor,
                        0,
                        False,
                        gif_fps,
                        gif_end_delay,
                        log_fn,
                        global_options=global_options).slice()
        else:
            raise ValueError(f"thumbnail type '{self.thumbnail_type}' is not implemented")

    def keep_all_scenes(self):
        self.scene_states = {scene_name : "Keep" for scene_name in self.scene_names}

    def drop_all_scenes(self):
        self.scene_states = {scene_name : "Drop" for scene_name in self.scene_names}

    GAP = " " * 6

    def scene_chooser_details(self, scene_index):
        try:
            scene_name = self.scene_names[scene_index]
            thumbnail_path = self.thumbnails[scene_index]
            scene_state = self.scene_states[scene_name]
            scene_position = f"{scene_index+1} of {len(self.scene_names)}"

            first_index, last_index, _ = details_from_group_name(scene_name)
            scene_start = seconds_to_hmsf(
                first_index / self.project_fps,
                self.project_fps)
            scene_duration = seconds_to_hmsf(
                (last_index - first_index) / self.project_fps,
                self.project_fps)
            scene_time = f"{scene_start}{self.GAP}+{scene_duration}"
            keep_state = SimpleIcons.HEART if scene_state == "Keep" else ""
            scene_info = f"{scene_position}{self.GAP}{scene_time}{self.GAP}{keep_state}"
            return scene_name, thumbnail_path, scene_state, scene_info
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while computing scene chooser details: {error}")
        except IndexError as error:
            raise ValueError(
                f"IndexError encountered while computing scene chooser details: {error}")

    def kept_scenes(self):
        return [scene for scene in self.scene_states if self.scene_states[scene] == "Keep"]

    def dropped_scenes(self):
        return [scene for scene in self.scene_states if self.scene_states[scene] == "Drop"]

    def scene_frames(self, type : str="all") -> int:
        if type.lower() == "keep":
            scenes = self.kept_scenes()
        elif type.lower() == "drop":
            scenes = self.dropped_scenes()
        else:
            scenes = self.scene_names
        accum = 0
        for scene in scenes:
            first, last, _ = details_from_group_name(scene)
            accum += (last - first) + 1
        return accum

    def scene_frames_time(self, frames : int) -> str:
        return seconds_to_hmsf(frames / self.project_fps, self.project_fps)

    def chosen_scenes_report(self):
        all_scenes = len(self.scene_names)
        all_frames = self.scene_frames("all")
        all_time = self.scene_frames_time(all_frames)
        keep_scenes = len(self.kept_scenes())
        keep_frames = self.scene_frames("keep")
        keep_time = self.scene_frames_time(keep_frames)
        drop_scenes = len(self.dropped_scenes())
        drop_frames = self.scene_frames("drop")
        drop_time = self.scene_frames_time(drop_frames)

        with Jot() as jot:
            jot.down(f"| Scene Choices | Scenes | Frames | Time |")
            jot.down(f"| :-: | :-: | :-: | :-: |")
            jot.down(f"| Keep {SimpleIcons.HEART} | {keep_scenes:,d} | {keep_frames:,d} | +{keep_time} |")
            jot.down(f"| Drop | {drop_scenes:,d} | {drop_frames:,d} | +{drop_time} |")
            jot.down(f"| Total | {all_scenes:,d} | {all_frames:,d} | +{all_time} |")
        return jot.grab()

    def uncompile_scenes(self):
        dropped_dirs = get_directories(self.dropped_scenes_path)
        for dir in dropped_dirs:
            current_path = os.path.join(self.dropped_scenes_path, dir)
            undropped_path = os.path.join(self.scenes_path, dir)
            shutil.move(current_path, undropped_path)

    def compile_scenes(self):
        dropped_scenes = self.dropped_scenes()
        for dir in dropped_scenes:
            current_path = os.path.join(self.scenes_path, dir)
            dropped_path = os.path.join(self.dropped_scenes_path, dir)
            shutil.move(current_path, dropped_path)

    ## Main Processing ##

    RESIZE_STEP = "resize"
    RESYNTH_STEP = "resynth"
    INFLATE_STEP = "inflate"
    UPSCALE_STEP = "upscale"

    def purge_processed_content(self, purge_from):
        if purge_from == self.RESIZE_STEP:
            remove_directories([
                self.resize_path,
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.RESYNTH_STEP:
            remove_directories([
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.INFLATE_STEP:
            remove_directories([
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.UPSCALE_STEP:
            remove_directories([
                self.upscale_path])
        self.purge_remix_content(purge_from="audio_clips")

    def purge_remix_content(self, purge_from):
        if purge_from == "audio_clips":
            purge_directories([
                self.audio_clips_path,
                self.video_clips_path,
                self.clips_path])
            self.audio_clips = []
            self.video_clips = []
            self.clips = []
        elif purge_from == "video_clips":
            purge_directories([
                self.video_clips_path,
                self.clips_path])
            self.video_clips = []
            self.clips = []
        elif purge_from == "scene_clips":
            purge_directories([
                self.clips_path])
            self.clips = []

    def processed_content_present(self, present_at):
        if present_at == self.RESIZE_STEP:
            resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
            return True if os.path.exists(resize_path) and \
                get_directories(resize_path) else False
        elif present_at == self.RESYNTH_STEP:
            resynth_path = os.path.join(self.project_path, self.RESYNTH_PATH)
            return True if os.path.exists(resynth_path) and \
                get_directories(resynth_path) else False
        elif present_at == self.INFLATE_STEP:
            inflate_path = os.path.join(self.project_path, self.INFLATE_PATH)
            return True if os.path.exists(inflate_path) and \
                get_directories(inflate_path) else False
        elif present_at == self.UPSCALE_STEP:
            upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)
            return True if os.path.exists(upscale_path) and \
                get_directories(upscale_path) else False
        elif present_at == "audio":
            audio_clips_path = os.path.join(self.clips_path, self.AUDIO_CLIPS_PATH)
            return True if os.path.exists(audio_clips_path) and \
                get_files(audio_clips_path) else False
        elif present_at == "video":
            video_clips_path = os.path.join(self.clips_path, self.VIDEO_CLIPS_PATH)
            return True if os.path.exists(video_clips_path) and \
                get_files(video_clips_path) else False

    def purge_stale_processed_content(self, purge_upscale):
        # content is stale if it is present on disk but currently deselected
        # its presence indicates it and dependent content is now stale
        if self.processed_content_present(self.RESIZE_STEP) and not self.resize:
            self.purge_processed_content(self.RESIZE_STEP)
        if self.processed_content_present(self.RESYNTH_STEP) and not self.resynthesize:
            self.purge_processed_content(self.RESYNTH_STEP)
        if self.processed_content_present(self.INFLATE_STEP) and not self.inflate:
            self.purge_processed_content(self.INFLATE_STEP)
        if self.processed_content_present(self.UPSCALE_STEP) and (not self.upscale or purge_upscale):
            self.purge_processed_content(self.UPSCALE_STEP)

    def processed_content_incomplete(self, present_at):
        expected_dirs = len(self.kept_scenes())
        if present_at == self.RESIZE_STEP:
            resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
            return True if os.path.exists(resize_path) and \
                len(get_directories(resize_path)) != expected_dirs else False
        elif present_at == self.RESYNTH_STEP:
            resynth_path = os.path.join(self.project_path, self.RESYNTH_PATH)
            return True if os.path.exists(resynth_path) and \
                len(get_directories(resynth_path)) != expected_dirs else False
        elif present_at == self.INFLATE_STEP:
            inflate_path = os.path.join(self.project_path, self.INFLATE_PATH)
            return True if os.path.exists(inflate_path) and \
                len(get_directories(inflate_path)) != expected_dirs else False
        elif present_at == self.UPSCALE_STEP:
            upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)
            return True if os.path.exists(upscale_path) and \
                len(get_directories(upscale_path)) != expected_dirs else False

    def purge_incomplete_processed_content(self):
        # content is incomplete if the wrong number of scene directories are present
        # if it is currently selected and incomplete, it should be purged
        if self.processed_content_incomplete(self.RESIZE_STEP) and self.resize:
            self.purge_processed_content(self.RESIZE_STEP)
        if self.processed_content_incomplete(self.RESYNTH_STEP) and self.resynthesize:
            self.purge_processed_content(self.RESYNTH_STEP)
        if self.processed_content_incomplete(self.INFLATE_STEP) and self.inflate:
            self.purge_processed_content(self.INFLATE_STEP)
        if self.processed_content_incomplete(self.UPSCALE_STEP) and self.upscale:
            self.purge_processed_content(self.UPSCALE_STEP)

    def scenes_source_path(self, processing_step):
        processing_path = self.scenes_path

        if processing_step == self.RESIZE_STEP:
            # resize is the first processing step and always draws from the scenes path
            pass

        elif processing_step == self.RESYNTH_STEP:
            # resynthesis is the second processing step
            if self.resize:
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        elif processing_step == self.INFLATE_STEP:
            # inflation is the third processing step
            if self.resynthesize:
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.resynthesis_path
            elif self.resize:
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        elif processing_step == self.UPSCALE_STEP:
            # upscaling is the fourth processing step
            if self.inflate:
                # if inflation is enabled, draw from the inflation path
                processing_path = self.inflation_path
            elif self.resynthesize:
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.resynthesis_path
            elif self.resize:
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        return processing_path

    RESIZE_PATH = "SCENES-RC"

    def resize_scenes(self, log_fn, kept_scenes, remixer_settings):
        scenes_base_path = self.scenes_source_path(self.RESIZE_STEP)
        self.resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
        create_directory(self.resize_path)
        self.save()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.resize_path, scene_name)

                if self.resize_w == self.video_details["content_width"] and \
                        self.resize_h == self.video_details["content_height"]:
                    scale_type = "none"
                else:
                    scale_type = remixer_settings["scale_type"]

                if self.crop_w == self.resize_w and \
                        self.crop_h == self.resize_h:
                    crop_type = "none"
                else:
                    crop_type = "crop"
                crop_offset = -1

                ResizeFrames(scene_input_path,
                            scene_output_path,
                            int(self.resize_w),
                            int(self.resize_h),
                            scale_type,
                            log_fn,
                            crop_type=crop_type,
                            crop_width=self.crop_w,
                            crop_height=self.crop_h,
                            crop_offset_x=crop_offset,
                            crop_offset_y=crop_offset).resize()
                Mtqdm().update_bar(bar)

    RESYNTH_PATH = "SCENES-RE"

    def resynthesize_scenes(self, log_fn, kept_scenes, engine, engine_settings):
        interpolater = Interpolate(engine.model, log_fn)
        use_time_step = engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, log_fn)

        scenes_base_path = self.scenes_source_path(self.RESYNTH_STEP)
        self.resynthesis_path = os.path.join(self.project_path, self.RESYNTH_PATH)
        create_directory(self.resynthesis_path)
        self.save()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resynth") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.resynthesis_path, scene_name)
                create_directory(scene_output_path)

                output_basename = "resynthesized_frames"
                file_list = sorted(get_files(scene_input_path, extension="png"))
                series_interpolater.interpolate_series(file_list,
                                                       scene_output_path,
                                                       1,
                                                       output_basename,
                                                       offset=2)
                ResequenceFiles(scene_output_path,
                                "png",
                                "resynthesized_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                log_fn).resequence()
                Mtqdm().update_bar(bar)

    INFLATE_PATH = "SCENES-IN"

    def inflate_scenes(self, log_fn, kept_scenes, engine, engine_settings):
        interpolater = Interpolate(engine.model, log_fn)
        use_time_step = engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, log_fn)

        scenes_base_path = self.scenes_source_path(self.INFLATE_STEP)
        self.inflation_path = os.path.join(self.project_path, self.INFLATE_PATH)
        create_directory(self.inflation_path)
        self.save()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Inflate") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.inflation_path, scene_name)
                create_directory(scene_output_path)

                output_basename = "interpolated_frames"
                file_list = sorted(get_files(scene_input_path, extension="png"))
                series_interpolater.interpolate_series(file_list,
                                                       scene_output_path,
                                                       1,
                                                       output_basename)
                ResequenceFiles(scene_output_path,
                                "png",
                                "inflated_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                log_fn).resequence()
                Mtqdm().update_bar(bar)

    UPSCALE_PATH = "SCENES-UP"

    def upscale_scenes(self, log_fn, kept_scenes, realesrgan_settings, remixer_settings):
        model_name = realesrgan_settings["model_name"]
        gpu_ids = realesrgan_settings["gpu_ids"]
        fp32 = realesrgan_settings["fp32"]
        use_tiling = remixer_settings["use_tiling"]
        if use_tiling:
            tiling = realesrgan_settings["tiling"]
            tile_pad = realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        upscaler = UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, log_fn)

        scenes_base_path = self.scenes_source_path(self.UPSCALE_STEP)
        self.upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)
        create_directory(self.upscale_path)
        # save the project now to preserve the newly established path
        self.save()

        if self.upscale_option == "1X":
            upscale_factor = 1.0
        elif self.upscale_option == "2X":
            upscale_factor = 2.0
        else:
            upscale_factor = 4.0

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Upscale") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.upscale_path, scene_name)
                create_directory(scene_output_path)

                file_list = sorted(get_files(scene_input_path))
                output_basename = "upscaled_frames"

                upscaler.upscale_series(file_list, scene_output_path, upscale_factor,
                                                    output_basename, "png")
                Mtqdm().update_bar(bar)

    def remix_filename_suffix(self):
        label = "remix"
        label += "-rc" if self.resize else "-or"
        label += "-re" if self.resynthesize else ""
        label += "-in" if self.inflate else ""
        label += "-up" + self.upscale_option[0] if self.upscale else ""
        return label

    def default_remix_filepath(self):
        _, filename, _ = split_filepath(self.source_video)
        suffix = self.remix_filename_suffix()
        return os.path.join(self.project_path, f"{filename}-{suffix}.mp4")

    # find scenes that are empty now after processing and should be automatically dropped
    # this can happen when resynthesis and/or inflation are used on scenes with only a few frames
    def drop_empty_processed_scenes(self, kept_scenes):
        # TODO might need to better manage the flow of content between processing steps
        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate:
            scenes_base_path = self.inflation_path
        elif self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Checking Clips") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                files = get_files(scene_input_path)
                if len(files) == 0:
                    self.scene_states[scene_name] = "Drop"
                    current_path = os.path.join(self.scenes_path, scene_name)
                    dropped_path = os.path.join(self.dropped_scenes_path, scene_name)
                    shutil.move(current_path, dropped_path)
                Mtqdm().update_bar(bar)

    AUDIO_CLIPS_PATH = "AUDIO"

    def create_audio_clips(self, log_fn, global_options):
        self.audio_clips_path = os.path.join(self.clips_path, self.AUDIO_CLIPS_PATH)
        create_directory(self.audio_clips_path)
        # save the project now to preserve the newly established path
        self.save()

        edge_trim = 1 if self.resynthesize else 0
        SliceVideo(self.source_video,
                    self.project_fps,
                    self.scenes_path,
                    self.audio_clips_path,
                    0.0,
                    "wav",
                    0,
                    1,
                    edge_trim,
                    False,
                    0.0,
                    0.0,
                    log_fn,
                    global_options=global_options).slice()
        self.audio_clips = sorted(get_files(self.audio_clips_path))

    VIDEO_CLIPS_PATH = "VIDEO"

    def create_video_clips(self, log_fn, kept_scenes, global_options):
        self.video_clips_path = os.path.join(self.clips_path, self.VIDEO_CLIPS_PATH)
        create_directory(self.video_clips_path)
        # save the project now to preserve the newly established path
        self.save()

        # TODO might need to better manage the flow of content between processing steps
        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate:
            scenes_base_path = self.inflation_path
        elif self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        video_clip_fps = 2 * self.project_fps if self.inflate else self.project_fps
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.video_clips_path, f"{scene_name}.mp4")

                ResequenceFiles(scene_input_path,
                                "png",
                                "processed_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                log_fn).resequence()
                PNGtoMP4(scene_input_path,
                                None,
                                video_clip_fps,
                                scene_output_filepath,
                                crf=self.output_quality,
                                global_options=global_options)
                Mtqdm().update_bar(bar)
        self.video_clips = sorted(get_files(self.video_clips_path))

    def create_scene_clips(self, kept_scenes, global_options):
        if self.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.video_clips[index]
                    scene_audio_path = self.audio_clips[index]
                    scene_output_filepath = os.path.join(self.clips_path, f"{scene_name}.mp4")
                    combine_video_audio(scene_video_path, scene_audio_path,
                                        scene_output_filepath, global_options=global_options)
                    Mtqdm().update_bar(bar)
            self.clips = sorted(get_files(self.clips_path))
        else:
            self.clips = sorted(get_files(self.video_clips_path))

    def create_custom_video_clips(self, log_fn, kept_scenes, global_options, custom_video_options, custom_ext):
        self.video_clips_path = os.path.join(self.clips_path, self.VIDEO_CLIPS_PATH)
        create_directory(self.video_clips_path)

        # TODO might need to better manage the flow of content between processing steps
        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate:
            scenes_base_path = self.inflation_path
        elif self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        video_clip_fps = 2 * self.project_fps if self.inflate else self.project_fps
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.video_clips_path, f"{scene_name}.{custom_ext}")

                ResequenceFiles(scene_input_path,
                                "png",
                                "processed_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                log_fn).resequence()
                PNGtoCustom(scene_input_path,
                            None,
                            video_clip_fps,
                            scene_output_filepath,
                            global_options=global_options,
                            custom_options=custom_video_options)
                Mtqdm().update_bar(bar)
        self.video_clips = sorted(get_files(self.video_clips_path))

    def create_custom_scene_clips(self, kept_scenes, global_options, custom_audio_options, custom_ext):
        if self.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.video_clips[index]
                    scene_audio_path = self.audio_clips[index]
                    scene_output_filepath = os.path.join(self.clips_path, f"{scene_name}.{custom_ext}")
                    combine_video_audio(scene_video_path, scene_audio_path,
                                        scene_output_filepath, global_options=global_options,
                                        output_options=custom_audio_options)
                    Mtqdm().update_bar(bar)
            self.clips = sorted(get_files(self.clips_path))
        else:
            self.clips = sorted(get_files(self.video_clips_path))

    def create_remix_video(self, global_options, output_filepath):
        with Mtqdm().open_bar(total=1, desc="Saving Remix") as bar:
            Mtqdm().message(bar, "Using FFmpeg to concatenate scene clips - no ETA")
            ffcmd = combine_videos(self.clips,
                                   output_filepath,
                                   global_options=global_options)
            Mtqdm().update_bar(bar)
        return ffcmd

    @staticmethod
    def load(filepath : str):
        with open(filepath, "r") as file:
            try:
                state = yaml.load(file, Loader=Loader)

                # reload some things
                state.scene_names = sorted(state.scene_names) if state.scene_names else []
                state.thumbnails = sorted(state.thumbnails) if state.thumbnails else []
                state.audio_clips = sorted(state.audio_clips) if state.audio_clips else []
                state.video_clips = sorted(state.video_clips) if state.video_clips else []

                # Compatibility
                # state.current_scene was originally a string
                if isinstance(state.current_scene, str):
                    try:
                        state.current_scene = state.scene_names.index(state.current_scene)
                    except IndexError:
                        state.current_scene = 0

                return state
            except YAMLError as error:
                if hasattr(error, 'problem_mark'):
                    mark = error.problem_mark
                    message = f"Error loading project file on line {mark.line+1} column {mark.column+1}: {error}"
                else:
                    message = error
                raise ValueError(message)

    def tryattr(self, attribute : str, default=None):
        return getattr(self, attribute) if hasattr(self, attribute) else default
