"""Video Remixer UI state management"""
import os
import shutil
import yaml
from yaml import Loader, YAMLError
from webui_utils.auto_increment import AutoIncrementBackupFilename, AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, clean_filename, remove_directories, copy_files
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf, shrink, format_table
from webui_utils.video_utils import details_from_group_name, get_essential_video_details, \
    MP4toPNG, PNGtoMP4, combine_video_audio, combine_videos, PNGtoCustom, SourceToMP4, \
    rate_adjusted_count, image_size
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
from PIL import Image

class VideoRemixerState():
    def __init__(self):
        # set at various stages
        self.progress = "home"

        # source video from initial tab
        self.source_video = None # set on clicking New Project
                                 # and again during project set up (pointing to duplicate copy)
        self.source_audio = None
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
        self.split_time = None
        self.crop_offset_x = None
        self.crop_offset_y = None

        # set on confirming set up options
        self.split_frames = None
        self.project_info2 = None # re-set on re-opening project
        self.source_frames_invalid = False # ensure source frames are purged on deinterlace change
        self.processed_content_invalid = False # ensure processed content is purged on redo

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
        self.scene_labels = {}

        # set when done choosing scenes
        self.project_info4 = None # re-set on re-opening project

        # project processing options
        self.resynthesize = False
        self.inflate = False
        self.resize = False
        self.upscale = False
        self.upscale_option = None
        self.inflate_by_option = None
        self.inflate_slow_option = None
        self.resynth_option = None

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
        "upscale_option" : "2X",
        "min_frames_per_scene" : 10,
        "split_time" : 60,
        "crop_offsets" : -1,
        "inflate_by_option" : "2X",
        "inflate_slow_option" : "No",
        "resynth_option" : "Scrub"
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
        self.min_frames_per_scene = self.UI_SAFETY_DEFAULTS["min_frames_per_scene"]
        self.split_time = self.UI_SAFETY_DEFAULTS["split_time"]
        self.inflate_by_option = self.UI_SAFETY_DEFAULTS["inflate_by_option"]
        self.inflate_slow_option = self.UI_SAFETY_DEFAULTS["inflate_slow_option"]
        self.resynth_option = self.UI_SAFETY_DEFAULTS["resynth_option"]

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
            yaml.dump(self, file, width=1024)

    def project_filepath(self, filename : str=DEF_FILENAME):
        return os.path.join(self.project_path, filename)

    def ingested_video_report(self):
        title = f"Ingested Video Report: {self.source_video}"
        header_row = [
            "Frame Rate",
            "Duration",
            "Display Size",
            "Aspect Ratio",
            "Content Size",
            "Frame Count",
            "File Size",
            "Has Audio"]
        data_rows = [[
            self.video_details['frame_rate'],
            self.video_details['duration'],
            self.video_details['display_dimensions'],
            self.video_details['display_aspect_ratio'],
            self.video_details['content_dimensions'],
            self.video_details['frame_count_show'],
            self.video_details['file_size'],
            SimpleIcons.YES_SYMBOL if self.video_details['has_audio'] else SimpleIcons.NO_SYMBOL]]
        return format_table(header_row, data_rows, color="more", title=title)

    PROJECT_PATH_PREFIX = "REMIX-"
    FILENAME_FILTER = [" ", "'", "[", "]"]

    def ingest_video(self, video_path):
        """Inspect submitted video and collect important details about it for project set up"""
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

        filtered_filename = clean_filename(filename, self.FILENAME_FILTER)
        project_path = os.path.join(path, f"{self.PROJECT_PATH_PREFIX}{filtered_filename}")
        resize_w = int(video_details['display_width'])
        resize_h = int(video_details['display_height'])
        crop_w, crop_h = resize_w, resize_h

        self.project_path = project_path
        self.resize_w = resize_w
        self.resize_h = resize_h
        self.crop_w = crop_w
        self.crop_h = crop_h
        self.crop_offset_x = -1
        self.crop_offset_y = -1
        self.project_fps = float(video_details['frame_rate'])

    @staticmethod
    def determine_project_filepath(project_path):
        if os.path.isdir(project_path):
            project_file = os.path.join(project_path, VideoRemixerState.DEF_FILENAME)
        else:
            project_file = project_path
            project_path, _, _ = split_filepath(project_path)
        if not os.path.exists(project_file):
            raise ValueError(f"Project file {project_file} was not found")
        return project_file

    def calc_split_frames(self, fps, seconds):
        return round(float(fps) * float(seconds))

    def _project_settings_report_scene(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Scene Detection Threshold"]
        data_rows = [[
            f"{float(self.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.resize_w} x {self.resize_h}",
            f"{self.crop_w} x {self.crop_h}",
            f"{self.crop_offset_x} x {self.crop_offset_y}",
            self.split_type,
            self.scene_threshold]]
        return header_row, data_rows

    def _project_settings_report_break(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Minimum Duration",
            "Black Ratio"]
        data_rows = [[
            f"{float(self.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.resize_w} x {self.resize_h}",
            f"{self.crop_w} x {self.crop_h}",
            f"{self.crop_offset_x} x {self.crop_offset_y}",
            self.split_type,
            f"{self.break_duration}s",
            self.break_ratio]]
        return header_row, data_rows

    def _project_settings_report_time(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Split Time",
            "Split Frames"]
        self.split_frames = self.calc_split_frames(self.project_fps, self.split_time)
        data_rows = [[
            f"{float(self.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.resize_w} x {self.resize_h}",
            f"{self.crop_w} x {self.crop_h}",
            f"{self.crop_offset_x} x {self.crop_offset_y}",
            self.split_type,
            f"{self.split_time}s",
            self.split_frames]]
        return header_row, data_rows

    def _project_settings_report_none(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type"]
        data_rows = [[
            f"{float(self.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.resize_w} x {self.resize_h}",
            f"{self.crop_w} x {self.crop_h}",
            f"{self.crop_offset_x} x {self.crop_offset_y}",
            self.split_type]]
        return header_row, data_rows

    def project_settings_report(self):
        title = f"Project Path: {self.project_path}"
        if self.split_type == "Scene":
            header_row, data_rows = self._project_settings_report_scene()
        elif self.split_type == "Break":
            header_row, data_rows = self._project_settings_report_break()
        elif self.split_type == "Time":
            header_row, data_rows = self._project_settings_report_time()
        else: # "None"
            header_row, data_rows = self._project_settings_report_none()
        return format_table(header_row, data_rows, color="more", title=title)

    # keep project's own copy of original video
    # it will be needed later to cut thumbnails and audio clips
    def save_original_video(self, prevent_overwrite=True):
        _, filename, ext = split_filepath(self.source_video)
        video_filename = filename + ext

        # clean various problematic chars from filenames
        filtered_filename = clean_filename(video_filename, self.FILENAME_FILTER)
        project_video_path = os.path.join(self.project_path, filtered_filename)

        if os.path.exists(project_video_path) and prevent_overwrite:
            raise ValueError(
            f"The local project video file already exists, copying skipped: {project_video_path}")

        with Mtqdm().open_bar(total=1, desc="Copying") as bar:
            Mtqdm().message(bar, "Copying source video locally - no ETA")
            shutil.copy(self.source_video, project_video_path)
            self.source_video = project_video_path
            Mtqdm().update_bar(bar)

    # this is expected to be called after save_original_video()
    def create_source_audio(self, crf, global_options, prevent_overwrite=True, skip_mp4=True):
        _, filename, ext = split_filepath(self.source_video)
        if skip_mp4 and ext.lower() == ".mp4":
            self.source_audio = self.source_video
            return

        audio_filename = filename  + "-audio" + ".mp4"

        # clean various problematic chars from filenames
        filtered_filename = clean_filename(audio_filename, self.FILENAME_FILTER)
        self.source_audio = os.path.join(self.project_path, filtered_filename)

        if os.path.exists(self.source_audio) and prevent_overwrite:
            raise ValueError(
            f"The local project audio file already exists, copying skipped: {self.source_audio}")

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Creating source audio locally - no ETA")
            SourceToMP4(self.source_video, self.source_audio, crf, global_options=global_options)
            self.source_audio = self.source_audio
            Mtqdm().update_bar(bar)

    def copy_project_file(self, copy_path):
        project_file = VideoRemixerState.determine_project_filepath(self.project_path)
        saved_project_file = os.path.join(copy_path, self.DEF_FILENAME)
        shutil.copy(project_file, saved_project_file)
        return saved_project_file

    # when advancing forward from the Set Up Project step
    # the user may be redoing the project from this step
    # need to purge anything created based on old settings
    # TODO make purging on backing up smarter
    def reset_at_project_settings(self):
        purge_path = self.purge_paths([
            self.scenes_path,
            self.dropped_scenes_path,
            self.thumbnail_path,
            self.clips_path,
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path])
        if purge_path:
            self.copy_project_file(purge_path)
        self.scene_names = []
        self.current_scene = 0
        self.thumbnails = []

    FRAMES_PATH = "SOURCE"

    # split video into raw PNG frames
    def render_source_frames(self, global_options, prevent_overwrite=False):
        self.frames_path = os.path.join(self.project_path, self.FRAMES_PATH)
        if prevent_overwrite:
            if os.path.exists(self.frames_path) and get_files(self.frames_path, "png"):
                return None

        video_path = self.source_video

        source_frame_rate = float(self.video_details["frame_rate"])
        source_frame_count = int(self.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.project_fps)

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

    # this is intended to be called after source frames have been rendered
    def enhance_video_info(self, log_fn, ignore_errors=True):
        """Get the actual dimensions of the PNG frame files"""
        if self.scene_names and not self.video_details.get("source_width", None):
            self.uncompile_scenes()
            first_scene_name = self.scene_names[0]
            first_scene_path = os.path.join(self.scenes_path, first_scene_name)
            scene_files = sorted(get_files(first_scene_path, "png"))
            if scene_files:
                try:
                    width, height = image_size(scene_files[0])
                    self.video_details["source_width"] = width
                    self.video_details["source_height"] = height
                except ValueError as error:
                    log_fn(f"Error: {error}")
                    if not ignore_errors:
                        raise error
                return
            message = f"no frame PNG files found in {first_scene_path}"
            if ignore_errors:
                log_fn(message)
            else:
                raise ValueError(message)

    def scenes_present(self):
        self.uncompile_scenes()
        return self.scenes_path and \
            os.path.exists(self.scenes_path) and \
            get_directories(self.scenes_path)

    def split_scenes(self, log_fn, prevent_overwrite=False):
        if prevent_overwrite and self.scenes_present():
                return None
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
            elif self.split_type == "Time":
                # split by seconds
                SplitFrames(
                    self.frames_path,
                    self.scenes_path,
                    "png",
                    "precise",
                    0,
                    self.split_frames,
                    "copy",
                    False,
                    log_fn).split()
            else:
                # single split
                SplitFrames(
                    self.frames_path,
                    self.scenes_path,
                    "png",
                    "precise",
                    1,
                    0,
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
    def decode_scene_name(scene_name):
        if not scene_name:
            raise ValueError("'scene_name' is required")

        splits = scene_name.split("-")
        if len(splits) != 2:
            raise ValueError(f"scene_name ''{scene_name} is not parsable")

        first, last = int(splits[0]), int(splits[1])
        count = (last - first) + 1
        return first, last, count

    @staticmethod
    def encode_scene_name(num_width, first, last, first_diff, last_diff):
        first = int(first) + int(first_diff)
        last = int(last) + int(last_diff)
        return f"{str(first).zfill(num_width)}-{str(last).zfill(num_width)}"

    @staticmethod
    def move_frames(state, scene_name, scene_name_from):
        log_fn = state["log_fn"]
        path = state["path"]
        from_path = os.path.join(path, scene_name_from)
        to_path = os.path.join(path, scene_name)
        files = get_files(from_path)
        for file in files:
            path, filename, ext = split_filepath(file)
            new_file = os.path.join(to_path, filename + ext)
            log_fn(f"moving {file} to {new_file}")
            shutil.move(file, new_file)

    @staticmethod
    def remove_scene(state, scene_name):
        log_fn = state["log_fn"]
        path = state["path"]
        scene_name_path = os.path.join(path, scene_name)
        log_fn(f"removing {scene_name_path}")
        shutil.rmtree(scene_name_path)

    @staticmethod
    def rename_scene(state, scene_name, new_contents):
        log_fn = state["log_fn"]
        path = state["path"]
        num_width = state["num_width"]
        first, last, _ = VideoRemixerState.decode_scene_name(scene_name)
        new_scene_name = VideoRemixerState.encode_scene_name(num_width, first, last, 0,
                                                               new_contents)
        scene_name_path = os.path.join(path, scene_name)
        new_scene_name_path = os.path.join(path, new_scene_name)
        log_fn(f"renaming {scene_name_path} to {new_scene_name_path}")
        os.rename(scene_name_path, new_scene_name_path)
        return new_scene_name

    @staticmethod
    def get_container_data(path):
        scene_names = get_directories(path)
        result = {}
        for scene_name in scene_names:
            dir_path = os.path.join(path, scene_name)
            count = len(get_files(dir_path))
            result[scene_name] = count
        num_width = len(scene_names[0].split("-")[0])
        return result, num_width

    def consolidate_scenes(self, log_fn):
        container_data, num_width = VideoRemixerState.get_container_data(self.scenes_path)
        state = {"path" : self.scenes_path,
                 "num_width" : num_width,
                 "log_fn" : log_fn}
        with Mtqdm().open_bar(total=1, desc="Shrink") as bar:
            Mtqdm().message(bar, "Shrinking small scenes - no ETA")
            shrunk_container_data = shrink(container_data, self.min_frames_per_scene,
                                           VideoRemixerState.move_frames,
                                           VideoRemixerState.remove_scene,
                                           VideoRemixerState.rename_scene, state)
            Mtqdm().update_bar(bar)
        log_fn(f"shrunk container data: {shrunk_container_data}")

    THUMBNAILS_PATH = "THUMBNAILS"

    # create a scene thumbnail, assumes:
    # - scenes uncompiled
    # - thumbnail path already exists
    def create_thumbnail(self, scene_name, log_fn, global_options, remixer_settings):
        self.thumbnail_path = os.path.join(self.project_path, self.THUMBNAILS_PATH)
        frames_source = os.path.join(self.scenes_path, scene_name)

        source_frame_rate = float(self.video_details["frame_rate"])
        source_frame_count = int(self.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.project_fps)

        log_fn(f"auto-resequencing source frames at {frames_source}")
        ResequenceFiles(frames_source, "png", "scene_frame", 0, 1, 1, 0, index_width, True,
            log_fn).resequence()

        thumbnail_filename = f"thumbnail[{scene_name}]"

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
                        global_options=global_options).slice_png_group(scene_name,
                            slice_name=thumbnail_filename)

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
                        global_options=global_options).slice_png_group(scene_name,
                                                                    ignore_errors=True,
                                                                    slice_name=thumbnail_filename)
        else:
            raise ValueError(f"thumbnail type '{self.thumbnail_type}' is not implemented")

    def create_thumbnails(self, log_fn, global_options, remixer_settings):
        self.thumbnail_path = os.path.join(self.project_path, self.THUMBNAILS_PATH)
        create_directory(self.thumbnail_path)
        clean_directories([self.thumbnail_path])
        self.uncompile_scenes()

        with Mtqdm().open_bar(total=len(self.scene_names), desc="Create Thumbnails") as bar:
            for scene_name in self.scene_names:
                self.create_thumbnail(scene_name, log_fn, global_options, remixer_settings)
                Mtqdm().update_bar(bar)

    def set_scene_label(self, scene_index, scene_label):
        if scene_label:
            this_scene_name = self.scene_names[scene_index]

            # ensure label is not in use for another scene
            for scene_name in self.scene_names:
                if scene_name != this_scene_name:
                    if self.scene_labels.get(scene_name) == scene_label:
                        # add scene name to make the label unique
                        scene_label = f"{scene_label} {this_scene_name}"
                        break

            self.scene_labels[this_scene_name] = scene_label

        return scene_label

    def clear_scene_label(self, scene_index):
        scene_name = self.scene_names[scene_index]
        if scene_name in self.scene_labels:
            del self.scene_labels[scene_name]

    def clear_all_scene_labels(self):
        for scene_index in range(len(self.scene_names)):
            self.clear_scene_label(scene_index)

    def keep_all_scenes(self):
        self.scene_states = {scene_name : "Keep" for scene_name in self.scene_names}

    def drop_all_scenes(self):
        self.scene_states = {scene_name : "Drop" for scene_name in self.scene_names}

    def invert_all_scenes(self):
        new_states = {}
        for k, v in self.scene_states.items():
            new_states[k] = "Keep" if v == "Drop" else "Drop"
        self.scene_states = new_states

    GAP = " " * 5

    def scene_chooser_data(self, scene_index):
        # prevent an error if the thumbnails have been purged
        try:
            thumbnail_path = self.thumbnails[scene_index]
        except IndexError:
            thumbnail_path = None

        try:
            scene_name = self.scene_names[scene_index]
            scene_state = self.scene_states[scene_name]
            scene_position = f"{scene_index+1}-of-{len(self.scene_names)}"

            first_index, last_index, _ = details_from_group_name(scene_name)
            scene_start = seconds_to_hmsf(
                first_index / self.project_fps,
                self.project_fps)
            scene_duration = seconds_to_hmsf(
                ((last_index + 1) - first_index) / self.project_fps,
                self.project_fps)
            keep_state = True if scene_state == "Keep" else False
            scene_label = self.scene_labels.get(scene_name)
            return scene_name, thumbnail_path, scene_state, scene_position, scene_start, \
                scene_duration, keep_state, scene_label
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while computing scene chooser details: {error}")
        except IndexError as error:
            raise ValueError(
                f"IndexError encountered while computing scene chooser details: {error}")

    def scene_chooser_details(self, scene_index):
        try:
            scene_name, thumbnail_path, scene_state, scene_position, scene_start, scene_duration, \
                keep_state, scene_label = self.scene_chooser_data(scene_index)

            scene_time = f"{scene_start}{self.GAP}+{scene_duration}"
            keep_symbol = SimpleIcons.HEART if keep_state == True else ""
            scene_info = f"{scene_position}{self.GAP}{scene_time}{self.GAP}{keep_symbol}"
            return scene_name, thumbnail_path, scene_state, scene_info, scene_label
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while getting scene chooser data: {error}")

    def kept_scenes(self) -> list:
        """Returns kept scene names sorted"""
        return sorted([scene for scene in self.scene_states if self.scene_states[scene] == "Keep"])

    def dropped_scenes(self) -> list:
        """Returns dropped scene names sorted"""
        return sorted([scene for scene in self.scene_states if self.scene_states[scene] == "Drop"])

    def labeled_scenes(self) -> dict:
        """Returns dict mapping scene label to scene name."""
        result = {}
        for scene_name in self.scene_names:
            scene_label = self.scene_labels.get(scene_name)
            if scene_label:
                result[scene_label] = scene_name
        return result

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
        header_row = [
            "Scene Choices",
            "Scenes",
            "Frames",
            "Time"]
        all_scenes = len(self.scene_names)
        all_frames = self.scene_frames("all")
        all_time = self.scene_frames_time(all_frames)
        keep_scenes = len(self.kept_scenes())
        keep_frames = self.scene_frames("keep")
        keep_time = self.scene_frames_time(keep_frames)
        drop_scenes = len(self.dropped_scenes())
        drop_frames = self.scene_frames("drop")
        drop_time = self.scene_frames_time(drop_frames)
        data_rows = [
            [
                "Keep " + SimpleIcons.HEART,
                f"{keep_scenes:,d}",
                f"{keep_frames:,d}",
                f"+{keep_time}"],
            [
                "Drop",
                f"{drop_scenes:,d}",
                f"{drop_frames:,d}",
                f"+{drop_time}"],
            [
                "Total",
                f"{all_scenes:,d}",
                f"{all_frames:,d}",
                f"+{all_time}"]]
        return format_table(header_row, data_rows, color="more")

    def uncompile_scenes(self):
        if self.dropped_scenes_path and os.path.exists(self.dropped_scenes_path):
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

    def recompile_scenes(self):
        self.uncompile_scenes()
        self.compile_scenes()

    ## Main Processing ##

    RESIZE_STEP = "resize"
    RESYNTH_STEP = "resynth"
    INFLATE_STEP = "inflate"
    UPSCALE_STEP = "upscale"
    AUDIO_STEP = "audio"
    VIDEO_STEP = "video"

    PURGED_CONTENT = "purged_content"

    # returns auto-generated purge path or None if nothing to purge
    def purge_paths(self, path_list : list):
        paths_to_purge = []
        for path in path_list:
            if path and os.path.exists(path):
                paths_to_purge.append(path)
        if not paths_to_purge:
            return None

        purged_root_path = os.path.join(self.project_path, self.PURGED_CONTENT)
        create_directory(purged_root_path)
        purged_path, _ = AutoIncrementDirectory(purged_root_path).next_directory("purged")

        for path in paths_to_purge:
            shutil.move(path, purged_path)
        return purged_path

    def delete_purged_content(self):
        purged_root_path = os.path.join(self.project_path, self.PURGED_CONTENT)
        if os.path.exists(purged_root_path):
            with Mtqdm().open_bar(total=1, desc="Deleting") as bar:
                Mtqdm().message(bar, "Removing purged content - No ETA")
                shutil.rmtree(purged_root_path)
                Mtqdm().update_bar(bar)
            return purged_root_path
        else:
            return None

    def delete_path(self, path):
        if path and os.path.exists(path):
            with Mtqdm().open_bar(total=1, desc="Deleting") as bar:
                Mtqdm().message(bar, "Removing project content - No ETA")
                shutil.rmtree(path)
                Mtqdm().update_bar(bar)
            return path
        else:
            return None

    def purge_processed_content(self, purge_from):
        if purge_from == self.RESIZE_STEP:
            purge_path = self.purge_paths([
                self.resize_path,
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.RESYNTH_STEP:
            purge_path = self.purge_paths([
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.INFLATE_STEP:
            purge_path = self.purge_paths([
                self.inflation_path,
                self.upscale_path])
        elif purge_from == self.UPSCALE_STEP:
            purge_path = self.purge_paths([
                self.upscale_path])
        if purge_path:
            self.copy_project_file(purge_path)
        self.clean_remix_content(purge_from="audio_clips")

    def clean_remix_content(self, purge_from):
        if purge_from == "audio_clips":
            clean_directories([
                self.audio_clips_path,
                self.video_clips_path,
                self.clips_path])
            self.audio_clips = []
            self.video_clips = []
            self.clips = []
        elif purge_from == "video_clips":
            clean_directories([
                self.video_clips_path,
                self.clips_path])
            self.video_clips = []
            self.clips = []
        elif purge_from == "scene_clips":
            clean_directories([
                self.clips_path])
            self.clips = []

    def clean_remix_audio(self):
        clean_directories([self.audio_clips_path])

    RESIZE_PATH = "SCENES-RC"
    RESYNTH_PATH = "SCENES-RE"
    INFLATE_PATH = "SCENES-IN"
    UPSCALE_PATH = "SCENES-UP"

    def setup_processing_paths(self):
        self.resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
        self.resynthesis_path = os.path.join(self.project_path, self.RESYNTH_PATH)
        self.inflation_path = os.path.join(self.project_path, self.INFLATE_PATH)
        self.upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)

    def _processed_content_complete(self, path, expected_dirs = 0, expected_files = 0):
        if not path or not os.path.exists(path):
            return False
        if expected_dirs:
            return len(get_directories(path)) == expected_dirs
        if expected_files:
            return len(get_files(path)) == expected_files
        return True

    def processed_content_complete(self, processing_step):
        expected_items = len(self.kept_scenes())
        if processing_step == self.RESIZE_STEP:
            return self._processed_content_complete(self.resize_path, expected_dirs=expected_items)
        elif processing_step == self.RESYNTH_STEP:
            return self._processed_content_complete(self.resynthesis_path, expected_dirs=expected_items)
        elif processing_step == self.INFLATE_STEP:
            return self._processed_content_complete(self.inflation_path, expected_dirs=expected_items)
        elif processing_step == self.UPSCALE_STEP:
            return self._processed_content_complete(self.upscale_path, expected_dirs=expected_items)
        elif processing_step == self.AUDIO_STEP:
            return self._processed_content_complete(self.audio_clips_path, expected_files=expected_items)
        elif processing_step == self.VIDEO_STEP:
            return self._processed_content_complete(self.video_clips_path, expected_files=expected_items)
        else:
            raise RuntimeError(f"'processing_step' {processing_step} is unrecognized")

    # processed content is stale if it is not selected and exists
    def processed_content_stale(self, selected : bool, path : str):
        if selected:
            return False
        if not os.path.exists(path):
            return False
        contents = get_directories(path)
        content_present = len(contents) > 0
        return content_present

    # content is stale if it is present on disk but not currently selected
    # stale content and its derivative content should be purged
    def purge_stale_processed_content(self, purge_upscale, purge_inflation, purge_resynth):
        if self.processed_content_stale(self.resize, self.resize_path):
            self.purge_processed_content(purge_from=self.RESIZE_STEP)

        if self.processed_content_stale(self.resynthesize, self.resynthesis_path) or purge_resynth:
            self.purge_processed_content(purge_from=self.RESYNTH_STEP)

        if self.processed_content_stale(self.inflate, self.inflation_path) or purge_inflation:
            self.purge_processed_content(purge_from=self.INFLATE_STEP)

        if self.processed_content_stale(self.upscale, self.upscale_path) or purge_upscale:
            self.purge_processed_content(purge_from=self.UPSCALE_STEP)

    def purge_incomplete_processed_content(self):
        # content is incomplete if the wrong number of scene directories are present
        # if it is currently selected and incomplete, it should be purged
        if self.resize and not self.processed_content_complete(self.RESIZE_STEP):
            self.purge_processed_content(purge_from=self.RESIZE_STEP)

        if self.resynthesize and not self.processed_content_complete(self.RESYNTH_STEP):
            self.purge_processed_content(purge_from=self.RESYNTH_STEP)

        if self.inflate and not self.processed_content_complete(self.INFLATE_STEP):
            self.purge_processed_content(purge_from=self.INFLATE_STEP)

        if self.upscale and not self.processed_content_complete(self.UPSCALE_STEP):
            self.purge_processed_content(purge_from=self.UPSCALE_STEP)

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

    def get_resize_params(self, content_width, content_height, remixer_settings):
        if self.resize_w == content_width and self.resize_h == content_height:
            scale_type = "none"
        else:
            if self.resize_w <= content_width and self.resize_h <= content_height:
                # use the down scaling type if there are only reductions
                # the default "area" type preserves details better on reducing
                scale_type = remixer_settings["scale_type_down"]
            else:
                # otherwise use the upscaling type
                # the default "lanczos" type preserves details better on enlarging
                scale_type = remixer_settings["scale_type_up"]

        if self.crop_w == self.resize_w and self.crop_h == self.resize_h:
            # disable cropping if noop
            crop_type = "none"
        elif self.crop_w > self.resize_w or self.crop_h > self.resize_h:
            # disable cropping if it will wrap/is invalid
            # TODO put bounds on the crop parameters instead of disabling
            crop_type = "none"
        else:
            crop_type = "crop"
        return scale_type, crop_type

    def resize_scene(self,
                     log_fn,
                     scene_input_path,
                     scene_output_path,
                     resize_w,
                     resize_h,
                     scale_type,
                     crop_type="none"):

        ResizeFrames(scene_input_path,
                    scene_output_path,
                    resize_w,
                    resize_h,
                    scale_type,
                    log_fn,
                    crop_type=crop_type,
                    crop_width=self.crop_w,
                    crop_height=self.crop_h,
                    crop_offset_x=self.crop_offset_x,
                    crop_offset_y=self.crop_offset_y).resize()

    def resize_scenes(self, log_fn, kept_scenes, remixer_settings):
        scenes_base_path = self.scenes_source_path(self.RESIZE_STEP)
        create_directory(self.resize_path)

        content_width = self.video_details["content_width"]
        content_height = self.video_details["content_height"]
        scale_type, crop_type= self.get_resize_params(content_width, content_height, remixer_settings)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.resize_path, scene_name)
                self.resize_scene(log_fn,
                                  scene_input_path,
                                  scene_output_path,
                                  int(self.resize_w),
                                  int(self.resize_h),
                                  scale_type,
                                  crop_type)
                Mtqdm().update_bar(bar)

    # TODO dry up this code with same in resynthesize_video_ui - maybe a specific resynth script
    def one_pass_resynthesis(self, log_fn, input_path, output_path, output_basename, engine):
        file_list = sorted(get_files(input_path, extension="png"))
        log_fn(f"beginning series of frame recreations at {output_path}")
        engine.interpolate_series(file_list, output_path, 1, "interframe", offset=2)

        log_fn(f"auto-resequencing recreated frames at {output_path}")
        ResequenceFiles(output_path,
                        "png", "resynthesized_frame",
                        1, 1, # start, step
                        1, 0, # stride, offset
                        -1,   # auto-zero fill
                        True, # rename
                        log_fn).resequence()

    def two_pass_resynth_pass(self, log_fn, input_path, output_path, output_basename, engine):
        file_list = sorted(get_files(input_path, extension="png"))

        inflated_frames = os.path.join(output_path, "inflated_frames")
        log_fn(f"beginning series of interframe recreations at {inflated_frames}")
        create_directory(inflated_frames)
        engine.interpolate_series(file_list, inflated_frames, 1, "interframe")

        log_fn(f"selecting odd interframes only at {inflated_frames}")
        ResequenceFiles(inflated_frames,
                        "png",
                        output_basename,
                        1, 1,  # start, step
                        2, 1,  # stride, offset
                        -1,    # auto-zero fill
                        False, # rename
                        log_fn,
                        output_path=output_path).resequence()
        remove_directories([inflated_frames])

    def two_pass_resynthesis(self, log_fn, input_path, output_path, output_basename, engine, one_pass_only=False):
        passes = 1 if one_pass_only else 2
        with Mtqdm().open_bar(total=passes, desc="Two-Pass Resynthesis") as bar:
            if not one_pass_only:
                interframes = os.path.join(output_path, "interframes")
                create_directory(interframes)
                self.two_pass_resynth_pass(log_fn, input_path, interframes, "odd_interframe", engine)
                input_path = interframes

            self.two_pass_resynth_pass(log_fn, input_path, output_path, output_basename, engine)

            if not one_pass_only:
                remove_directories([interframes])

    def resynthesize_scenes(self, log_fn, kept_scenes, engine, engine_settings, resynth_option):
        interpolater = Interpolate(engine.model, log_fn)
        use_time_step = engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, log_fn)
        output_basename = "resynthesized_frames"

        scenes_base_path = self.scenes_source_path(self.RESYNTH_STEP)
        create_directory(self.resynthesis_path)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resynthesize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.resynthesis_path, scene_name)
                create_directory(scene_output_path)

                if resynth_option == "Replace":
                    self.one_pass_resynthesis(log_fn, scene_input_path, scene_output_path, output_basename, series_interpolater)
                else:
                    one_pass_only = resynth_option == "Clean"
                    self.two_pass_resynthesis(log_fn, scene_input_path, scene_output_path, output_basename, series_interpolater, one_pass_only=one_pass_only)

                Mtqdm().update_bar(bar)

    def inflate_scenes(self, log_fn, kept_scenes, engine, engine_settings):
        interpolater = Interpolate(engine.model, log_fn)
        use_time_step = engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, log_fn)

        scenes_base_path = self.scenes_source_path(self.INFLATE_STEP)
        create_directory(self.inflation_path)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Inflate") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.inflation_path, scene_name)
                create_directory(scene_output_path)

                num_splits = 1
                if self.inflate_by_option == "4X":
                    num_splits = 2
                elif self.inflate_by_option == "8X":
                    num_splits = 3

                output_basename = "interpolated_frames"
                file_list = sorted(get_files(scene_input_path, extension="png"))
                series_interpolater.interpolate_series(file_list,
                                                       scene_output_path,
                                                       num_splits,
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

    def get_upscaler(self, log_fn, realesrgan_settings, remixer_settings):
        model_name = realesrgan_settings["model_name"]
        gpu_ids = realesrgan_settings["gpu_ids"]
        fp32 = realesrgan_settings["fp32"]

        # determine if cropped image size is above memory threshold requiring tiling
        use_tiling_over = remixer_settings["use_tiling_over"]
        size = self.crop_w * self.crop_h

        if size > use_tiling_over:
            tiling = realesrgan_settings["tiling"]
            tile_pad = realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        return UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, log_fn)

    FIXED_UPSCALE_FACTOR = 4.0
    TEMP_UPSCALE_PATH = "upscaled_frames"
    DEFAULT_DOWNSCALE_TYPE = "area"

    def upscale_scene(self,
                      log_fn,
                      upscaler,
                      scene_input_path,
                      scene_output_path,
                      upscale_factor,
                      downscale_type=DEFAULT_DOWNSCALE_TYPE):
        log_fn(f"creating scene output path {scene_output_path}")
        create_directory(scene_output_path)

        working_path = os.path.join(scene_output_path, self.TEMP_UPSCALE_PATH)
        log_fn(f"about to create working path {working_path}")
        create_directory(working_path)

        # upscale first at the engine's native scale
        file_list = sorted(get_files(scene_input_path))
        output_basename = "upscaled_frames"
        log_fn(f"about to upscale images to {working_path}")
        upscaler.upscale_series(file_list, working_path, self.FIXED_UPSCALE_FACTOR, output_basename,
                                "png")

        # get size of upscaled frames
        upscaled_files = sorted(get_files(working_path))
        width, height = image_size(upscaled_files[0])
        log_fn(f"size of upscaled images: {width} x {height}")

        # compute downscale factor
        downscale_factor = self.FIXED_UPSCALE_FACTOR / upscale_factor
        log_fn(f"downscale factor is {downscale_factor}")

        downscaled_width = int(width / downscale_factor)
        downscaled_height = int(height / downscale_factor)
        log_fn(f"size of downscaled images: {downscaled_width} x {downscaled_height}")

        if downscaled_width != width or downscaled_height != height:
            # downsample to final size
            log_fn(f"about to downscale images in {working_path} to {scene_output_path}")
            self.resize_scene(log_fn,
                                    working_path,
                                    scene_output_path,
                                    downscaled_width,
                                    downscaled_height,
                                    downscale_type)
        else:
            log_fn("copying instead of unneeded downscaling")
            copy_files(working_path, scene_output_path)

        try:
            log_fn(f"about to delete working path {working_path}")
            shutil.rmtree(working_path)
        except OSError as error:
            log_fn(f"ignoring error deleting working path: {error}")

    def upscale_factor_from_options(self) -> float:
        upscale_factor = 1.0
        if self.upscale:
            if self.upscale_option == "2X":
                upscale_factor = 2.0
            elif self.upscale_option == "3X":
                upscale_factor = 3.0
            elif self.upscale_option == "4X":
                upscale_factor = 4.0
        return upscale_factor

    def upscale_scenes(self, log_fn, kept_scenes, realesrgan_settings, remixer_settings):
        upscaler = self.get_upscaler(log_fn, realesrgan_settings, remixer_settings)
        scenes_base_path = self.scenes_source_path(self.UPSCALE_STEP)
        downscale_type = remixer_settings["scale_type_down"]
        create_directory(self.upscale_path)

        upscale_factor = self.upscale_factor_from_options()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Upscale") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.upscale_path, scene_name)
                self.upscale_scene(log_fn, upscaler, scene_input_path, scene_output_path, upscale_factor,
                                   downscale_type=downscale_type)
                Mtqdm().update_bar(bar)

    def remix_filename_suffix(self, extra_suffix):
        label = "remix"
        label += "-rc" if self.resize else "-or"
        if self.resynthesize:
            label += "-re"
            if self.resynth_option == "Clean":
                label += "C"
            elif self.resynth_option == "Scrub":
                label += "S"
            elif self.resynth_option == "Replace":
                label += "R"
        if self.inflate:
            label += "-in" + self.inflate_by_option[0]
            if self.inflate_slow_option == "Audio":
                label += "SA"
            elif self.inflate_slow_option == "Silent":
                label += "SM"

        label += "-up" + self.upscale_option[0] if self.upscale else ""
        label += "-" + extra_suffix if extra_suffix else ""
        return label

    def default_remix_filepath(self, extra_suffix=""):
        _, filename, _ = split_filepath(self.source_video)
        suffix = self.remix_filename_suffix(extra_suffix)
        return os.path.join(self.project_path, f"{filename}-{suffix}.mp4")

    # drop a kept scene after scene compiling has already been done
    # used for dropping empty processed scenes, and force dropping processed scenes
    def drop_kept_scene(self, scene_name):
        self.scene_states[scene_name] = "Drop"
        current_path = os.path.join(self.scenes_path, scene_name)
        dropped_path = os.path.join(self.dropped_scenes_path, scene_name)
        if os.path.exists(current_path):
            if not os.path.exists(dropped_path):
                shutil.move(current_path, dropped_path)
            else:
                raise ValueError(
                    f"cannot move {current_path} to {dropped_path} which already exists")

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
                    self.drop_kept_scene(scene_name)
                Mtqdm().update_bar(bar)

    def delete_processed_scene(self, path, scene_name):
        removed = []
        if path and os.path.exists(path):
            full_path = os.path.join(path, scene_name)
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
                removed.append(full_path)
        return removed

    def delete_processed_clip(self, path, scene_name):
        removed = []
        if path and os.path.exists(path):
            files = get_files(path)
            # some clips are formatted like "original_namee[000-999].ext",
            # and some like "000-000.ext"
            # TODO resequence audio clips and thumbnails to make the naming consistent
            for file in files:
                if file.find(scene_name) != -1:
                    os.remove(file)
                    removed.append(file)
        return removed

    # drop an already-processed scene to cut it from the remix video
    def force_drop_processed_scene(self, scene_index):
        scene_name = self.scene_names[scene_index]
        self.drop_kept_scene(scene_name)
        removed = []
        for path in [
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path
        ]:
            removed += self.delete_processed_scene(path, scene_name)
        for path in [
            self.audio_clips_path,
            self.video_clips_path,
            self.clips_path
        ]:
            removed += self.delete_processed_clip(path, scene_name)
        if self.audio_clips_path:
            self.audio_clips = sorted(get_files(self.audio_clips_path))
        return removed

    AUDIO_CLIPS_PATH = "AUDIO"

    def create_audio_clips(self, log_fn, global_options, audio_format):
        self.audio_clips_path = os.path.join(self.clips_path, self.AUDIO_CLIPS_PATH)
        create_directory(self.audio_clips_path)
        # save the project now to preserve the newly established path
        self.save()

        edge_trim = 1 if self.resynthesize else 0
        SliceVideo(self.source_audio,
                    self.project_fps,
                    self.scenes_path,
                    self.audio_clips_path,
                    0.0,
                    audio_format,
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

    def compute_inflated_fps(self):
        """Compute the video clip FPS considering project FPS and inflation settings.
        For 2X and 4X inflation, when slow motion is enabled, the 50% audio slowdown will reduce the FPS by 2X.
        For 8X inflation with slow motion, the 75% audio slowdown will reduce the FPS by 4X"""
        if self.inflate:
            if self.inflate_slow_option == "No":
                # Set FPS for maximum smoothness
                if self.inflate_by_option == "2X":
                    inflate_factor = 2.0
                elif self.inflate_by_option == "4X":
                    inflate_factor = 4.0
                elif self.inflate_by_option == "8X":
                    inflate_factor = 8.0
            elif self.inflate_slow_option == "Audio":
                # Set FPS for maximum audio quality
                if self.inflate_by_option == "2X":
                    inflate_factor = 1.0
                elif self.inflate_by_option == "4X":
                    inflate_factor = 2.0
                elif self.inflate_by_option == "8X":
                    inflate_factor = 2.0
            elif self.inflate_slow_option == "Silent":
                # Set FPS for maximum slow motion
                inflate_factor = 1.0
        else:
            # Keep project FPS unchanged
            inflate_factor = 1.0
        return inflate_factor * self.project_fps

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

        video_clip_fps = self.compute_inflated_fps()

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

    def compute_inflated_audio_options(self, custom_audio_options):
        if self.inflate:
            if self.inflate_slow_option == "Audio":
                if self.inflate_by_option == "8X":
                    output_options = '-filter:a "atempo=0.5,atempo=0.5" -c:v copy ' + custom_audio_options
                else:
                    output_options = '-filter:a "atempo=0.5" -c:v copy ' + custom_audio_options
            elif self.inflate_slow_option == "Silent":
                output_options = '-f lavfi -i anullsrc -ac 2 -ar 48000 -map 0:v:0 -map 2:a:0 -c:v copy -shortest ' + custom_audio_options
            else:
                output_options = custom_audio_options
        else:
            output_options = custom_audio_options
        return output_options

    def create_scene_clips(self, kept_scenes, global_options):
        if self.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.video_clips[index]
                    scene_audio_path = self.audio_clips[index]
                    scene_output_filepath = os.path.join(self.clips_path, f"{scene_name}.mp4")

                    output_options = self.compute_inflated_audio_options("-c:a aac -shortest")

                    combine_video_audio(scene_video_path,
                                        scene_audio_path,
                                        scene_output_filepath,
                                        global_options=global_options,
                                        output_options=output_options)
                    Mtqdm().update_bar(bar)
            self.clips = sorted(get_files(self.clips_path))
        else:
            self.clips = sorted(get_files(self.video_clips_path))

    def create_custom_video_clips(self,
                                  log_fn,
                                  kept_scenes,
                                  global_options,
                                  custom_video_options,
                                  custom_ext,
                                  draw_text_options=None):
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

        if custom_video_options.find("<LABEL>") != -1:
            if not draw_text_options:
                raise RuntimeError("'draw_text_options' is None at create_custom_video_clips()")
            try:
                font_factor = draw_text_options["font_size"]
                font_color = draw_text_options["font_color"]
                font_file = draw_text_options["font_file"]
                draw_box = draw_text_options["draw_box"]
                box_color = draw_text_options["box_color"]
                border_factor = draw_text_options["border_size"]
                marked_position = draw_text_options["marked_position"]
                crop_width = draw_text_options["crop_width"]
                labels = draw_text_options["labels"]
            except IndexError as error:
                raise RuntimeError(f"error retrieving 'draw_text_options': {error}")

            font_size = crop_width / float(font_factor)
            border_size = font_size / float(border_factor)
            box_x = "(w-text_w)/2"

            if marked_position == "Bottom":
                box_y = f"h-(text_h*2)-({2*int(border_size)})"
            elif marked_position == "Middle":
                box_y = f"(h/2)-(text_h/2)-({int(border_size)})"
            else:
                box_y = "(text_h*1)"
            box = "1" if draw_box else "0"

        video_clip_fps = self.compute_inflated_fps()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for index, scene_name in enumerate(kept_scenes):
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.video_clips_path,
                                                     f"{scene_name}.{custom_ext}")
                use_custom_video_options = custom_video_options
                if use_custom_video_options.find("<LABEL>") != -1:
                    try:
                        label : str = labels[index]

                        # remove the sorting mark if present
                        if label.startswith("("):
                            endpoint = label.find(")")
                            if endpoint != -1:
                                label = label[endpoint + 1:]

                        # trim whitespace
                        label = label.strip()

                        # FFmpeg needs the colons escaped
                        label = label.replace(":", "\:")
                        if draw_box:
                            draw_text = f"text='{label}':x={box_x}:y={box_y}:fontsize={font_size}:fontcolor={font_color}:fontfile='{font_file}':box={box}:boxcolor={box_color}:boxborderw={border_size}"
                        else:
                            draw_text = f"text='{label}':x={box_x}:y={box_y}:fontsize={font_size}:fontcolor={font_color}:fontfile='{font_file}':box={box}"
                        use_custom_video_options = use_custom_video_options \
                            .replace("<LABEL>", draw_text)
                    except IndexError as error:
                        use_custom_video_options = use_custom_video_options\
                            .replace("<LABEL>", f"[{error}]")

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
                            custom_options=use_custom_video_options)
                Mtqdm().update_bar(bar)
        self.video_clips = sorted(get_files(self.video_clips_path))

    def create_custom_scene_clips(self,
                                  kept_scenes,
                                  global_options,
                                  custom_audio_options,
                                  custom_ext):
        if self.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.video_clips[index]
                    scene_audio_path = self.audio_clips[index]
                    scene_output_filepath = os.path.join(self.clips_path,
                                                         f"{scene_name}.{custom_ext}")

                    output_options = self.compute_inflated_audio_options(custom_audio_options)

                    combine_video_audio(scene_video_path, scene_audio_path,
                                        scene_output_filepath, global_options=global_options,
                                        output_options=output_options)
                    Mtqdm().update_bar(bar)
            self.clips = sorted(get_files(self.clips_path))
        else:
            self.clips = sorted(get_files(self.video_clips_path))

    def assembly_list(self, clip_filepaths : list) -> list:
        """Get list clips to assemble in order.
        'clip_filepaths' is expected to be full path and filename to the remix clips, corresponding to the list of kept scenes.
        If there are labeled scenes, they are arranged first in sorted order, followed by non-labeled scenes."""
        if not self.scene_labels:
            return clip_filepaths

        # map scene names to clip filepaths
        kept_scenes = self.kept_scenes()
        map_scene_name_to_clip = {}
        for index, scene_name in enumerate(kept_scenes):
            map_scene_name_to_clip[scene_name] = clip_filepaths[index]

        # assemble the labeled part of the clip list in label order
        # and remove labeled scenes from the unlabeled scene list
        assembly = []
        unlabeled_scenes = kept_scenes
        labeled_scenes = self.labeled_scenes()
        scene_labels = sorted(list(labeled_scenes.keys()))
        for scene_label in scene_labels:
            scene_name = labeled_scenes[scene_label]
            kept_clip = map_scene_name_to_clip.get(scene_name)
            if kept_clip:
                assembly.append(kept_clip)
                unlabeled_scenes.remove(scene_name)

        # add the unlabeled clips
        for scene_name in unlabeled_scenes:
            assembly.append(map_scene_name_to_clip[scene_name])

        return assembly

    def create_remix_video(self, global_options, output_filepath, labeled_scenes_first=True):
        with Mtqdm().open_bar(total=1, desc="Saving Remix") as bar:
            Mtqdm().message(bar, "Using FFmpeg to concatenate scene clips - no ETA")

            if labeled_scenes_first:
                assembly_list = self.assembly_list(self.clips)
            else:
                assembly_list = self.clips
            ffcmd = combine_videos(assembly_list,
                                   output_filepath,
                                   global_options=global_options)
            Mtqdm().update_bar(bar)
        return ffcmd

    # returns validated version of path and files, and an optional messages str
    def ensure_valid_populated_path(self, description : str, path : str, files : list | None=None):
        if not path:
            return None, None, None

        messages = Jot()
        if not os.path.exists(path):
            messages.add(f"{description} path '{path}' not found - recreating")
            create_directory(path)

        path_files = get_files(path)
        file_count = len(files) if files else 0
        path_file_count = len(path_files)

        if not files and not path_files:
            return path, [], messages.report()

        if not files and path_files:
            messages.add(f"{description} path '{path}' has {path_file_count} files unknown " +
                         " to the project. The files are being ignored (safe to delete).")
            return path, [], messages.report()

        if path_file_count != file_count:
            messages.add(f"{description} path '{path}' should have {file_count} files" +
                    f" but has {path_file_count}. The files are being ignored (safe to delete).")
            return path, [], messages.report()

        # TODO further possible checks: files have bytes,
        # files are found to be the right binary type, etc

        return path, files, messages.report()

    # returns validated version of path, and an optional messages str
    def ensure_valid_path(self, description : str, path : str, files : list | None=None):
        if not path:
            return None, None

        messages = Jot()
        if not os.path.exists(path):
            messages.add(f"{description} path '{path}' not found - recreating")
            create_directory(path)

        return path, messages.report()

    def post_load_integrity_check(self):
        messages = Jot()

        self.thumbnail_path, self.thumbnails, message = self.ensure_valid_populated_path(
            "Thumbnails", self.thumbnail_path, self.thumbnails)
        if message:
            messages.add(message)

        self.clips_path, self.clips, message = self.ensure_valid_populated_path(
            "Clips", self.clips_path, self.clips)
        if message:
            messages.add(message)

        self.audio_clips_path, self.audio_clips, message = self.ensure_valid_populated_path(
            "Audio Clips", self.audio_clips_path, self.audio_clips)
        if message:
            messages.add(message)

        self.video_clips_path, self.video_clips, message = self.ensure_valid_populated_path(
            "Video Clips", self.video_clips_path, self.video_clips)
        if message:
            messages.add(message)

        self.dropped_scenes_path, message = self.ensure_valid_path(
            "Dropped Scenes", self.dropped_scenes_path)
        if message:
            messages.add(message)

        self.frames_path, message = self.ensure_valid_path("Frames Path", self.frames_path)
        if message:
            messages.add(message)

        self.inflation_path, message = self.ensure_valid_path("Inflation Path", self.inflation_path)
        if message:
            messages.add(message)

        self.inflation_path, message = self.ensure_valid_path("Inflation Path", self.inflation_path)
        if message:
            messages.add(message)

        self.resize_path, message = self.ensure_valid_path("Resize Path", self.resize_path)
        if message:
            messages.add(message)

        self.resynthesis_path, message = self.ensure_valid_path(
            "Resynthesis Path", self.resynthesis_path)
        if message:
            messages.add(message)

        self.scenes_path, message = self.ensure_valid_path("Scenes Path", self.scenes_path)
        if message:
            messages.add(message)

        self.upscale_path, message = self.ensure_valid_path("Upscale Path", self.upscale_path)
        if message:
            messages.add(message)

        return messages.report()

    def recover_project(self, global_options, remixer_settings, log_fn):
        log_fn("beginning project recovery")

        # purge project paths ahead of recreating
        purged_path = self.purge_paths([
            self.scenes_path,
            self.dropped_scenes_path,
            self.thumbnail_path,
            self.audio_clips_path,
            self.video_clips_path,
            self.clips_path,
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path
        ])
        log_fn(f"generated content directories purged to {purged_path}")

        self.render_source_frames(global_options=global_options, prevent_overwrite=True)
        log_fn(f"source frames rendered to {self.frames_path}")

        source_audio_crf = remixer_settings["source_audio_crf"]
        try:
            self.create_source_audio(source_audio_crf, global_options, prevent_overwrite=True)
            log_fn(f"created source audio {self.source_audio} from {self.source_video}")
        except ValueError as error:
            # ignore, don't create the file if present or same as video
            log_fn(f"ignoring: {error}")

        create_directory(self.scenes_path)
        log_fn(f"created scenes directory {self.scenes_path}")
        create_directory(self.dropped_scenes_path)
        log_fn(f"created dropped scenes directory {self.dropped_scenes_path}")

        log_fn("beginning recreating of scenes from source frames")
        source_frames = sorted(get_files(self.frames_path))
        with Mtqdm().open_bar(total=len(self.scene_names), desc="Recreating Scenes") as bar:
            for scene_name in self.scene_names:
                scene_path = os.path.join(self.scenes_path, scene_name)
                create_directory(scene_path)
                log_fn(f"created scene directory {scene_path}")

                first_index, last_index, _ = details_from_group_name(scene_name)
                num_frames = (last_index - first_index) + 1
                with Mtqdm().open_bar(total=num_frames, desc="Copying") as inner_bar:
                    for index in range(first_index, last_index + 1):
                        source_path = source_frames[index]
                        _, filename, ext = split_filepath(source_path)
                        frame_path = os.path.join(scene_path, filename + ext)
                        shutil.copy(source_path, frame_path)
                        Mtqdm().update_bar(inner_bar)

                log_fn(f"scene frames copied to {scene_path}")
                Mtqdm().update_bar(bar)
        log_fn(f"recreated scenes")

        log_fn(f"about to create thumbnails of type {self.thumbnail_type}")
        self.create_thumbnails(log_fn, global_options, remixer_settings)
        self.thumbnails = sorted(get_files(self.thumbnail_path))

        self.clips_path = os.path.join(self.project_path, "CLIPS")
        log_fn(f"creating clips directory {self.clips_path}")
        create_directory(self.clips_path)

        # user will expect to return to scene chooser on reopening
        log_fn("saving project after recovery process")
        self.save_progress("choose")

    @staticmethod
    def load(filepath : str, log_fn):
        with open(filepath, "r") as file:
            try:
                state : VideoRemixerState = yaml.load(file, Loader=Loader)

                # reload some things
                # TODO maybe reload from what's found on disk
                state.scene_names = sorted(state.scene_names) if state.scene_names else []
                state.thumbnails = sorted(state.thumbnails) if state.thumbnails else []
                state.audio_clips = sorted(state.audio_clips) if state.audio_clips else []
                state.video_clips = sorted(state.video_clips) if state.video_clips else []
                state.setup_processing_paths()

                ## Compatibility
                # state.current_scene was originally a string
                if isinstance(state.current_scene, str):
                    try:
                        state.current_scene = state.scene_names.index(state.current_scene)
                    except IndexError:
                        state.current_scene = 0
                # originally implied only a 60 second split
                if state.split_type == "Minute":
                    state.split_type = "Time"
                    state.split_time = 60
                    state.split_frames = state.calc_split_frames(state.project_fps, state.split_time)
                # new attribute
                state.processed_content_invalid = False
                # new separate audio source
                try:
                    if not state.source_audio:
                        state.source_audio = state.source_video
                except AttributeError:
                    state.source_audio = state.source_video
                # new crop offsets
                try:
                    if state.crop_offset_x == None or state.crop_offset_y == None:
                        state.crop_offset_x = -1
                        state.crop_offset_y = -1
                except AttributeError:
                    state.crop_offset_x = -1
                    state.crop_offset_y = -1
                # new scene labels
                try:
                    if state.scene_labels == None:
                        state.scene_labels = {}
                except AttributeError:
                    state.scene_labels = {}
                # new inflation options
                try:
                    if state.inflate_by_option == None:
                        state.inflate_by_option = "2X"
                except AttributeError:
                    state.inflate_by_option = "2X"
                # new inflation slow options
                try:
                    if isinstance(state.inflate_slow_option, bool):
                        if state.inflate_slow_option:
                            state.inflate_slow_option = "Audio"
                        else:
                            state.inflate_slow_option = "No"
                except AttributeError:
                    state.inflate_slow_option = "No"
                # new attribute
                state.source_frames_invalid = False
                # new resynthesis option
                try:
                    if not state.resynth_option:
                        state.resynth_option = "Scrub"
                except AttributeError:
                        state.resynth_option = "Scrub"

                return state

            except YAMLError as error:
                if hasattr(error, 'problem_mark'):
                    mark = error.problem_mark
                    message = \
                f"Error loading project file on line {mark.line+1} column {mark.column+1}: {error}"
                else:
                    message = error
                raise ValueError(message)

    @staticmethod
    def load_ported(original_project_path, ported_project_file : str, log_fn, save_original = True):
        new_path, _, _ = split_filepath(ported_project_file)

        if save_original:
            backup_path = os.path.join(new_path, "ported_project_files")
            create_directory(backup_path)
            backup_filepath = \
                AutoIncrementBackupFilename(ported_project_file, backup_path).next_filepath()
            shutil.copy(ported_project_file, backup_filepath)

        if new_path[-1] != "\\":
            new_path += "\\"
        if original_project_path[-1] != "\\":
            original_project_path += "\\"

        lines = []
        with open(ported_project_file, "r", encoding="UTF-8") as file:
            lines = file.readlines()
        new_lines = []

        original_project_path_escaped = original_project_path.replace("\\", "\\\\")
        new_path_escaped = new_path.replace("\\", "\\\\")
        original_project_path_trimmed = original_project_path[:-1]
        new_path_trimmed = new_path[:-1]
        for line in lines:
            if line.find(original_project_path_escaped) != -1:
                new_line = line.replace(original_project_path_escaped, new_path_escaped)
            if line.find(original_project_path_trimmed) != -1:
                new_line = line.replace(original_project_path_trimmed, new_path_trimmed)
            elif line.find(original_project_path) != -1:
                new_line = line.replace(original_project_path, new_path)
            else:
                new_line = line
            new_lines.append(new_line)

        with open(ported_project_file, "w", encoding="UTF-8") as file:
            file.writelines(new_lines)

        state = VideoRemixerState.load(ported_project_file, log_fn)
        state.save(ported_project_file)

        return state

    def tryattr(self, attribute : str, default=None):
        return getattr(self, attribute) if hasattr(self, attribute) else default

    def project_ported(self, opened_project_file):
        opened_path, _, _ = split_filepath(opened_project_file)
        return self.project_path != opened_path
