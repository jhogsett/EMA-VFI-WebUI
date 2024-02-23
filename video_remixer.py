"""Video Remixer UI state management"""
import os
import math
import re
import shutil
import yaml
from yaml import Loader, YAMLError
from webui_utils.auto_increment import AutoIncrementBackupFilename, AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, clean_filename, remove_directories, copy_files, directory_populated, \
    simple_sanitize_filename, duplicate_directory
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
        self.frame_format = None
        self.sound_format = None

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

        # used internally only
        self.split_scene_cache = []
        self.split_scene_cached_index = -1

    # remove transient state
    def __getstate__(self):
        state = self.__dict__.copy()
        if "split_scene_cache" in state:
            del state["split_scene_cache"]
        if "split_scene_cached_index" in state:
            del state["split_scene_cached_index"]
        return state

    def reset(self):
        self.__init__()

    # set project settings UI defaults in case the project is reopened
    # otherwise some UI elements get set to None on reopened new projects
    def set_project_ui_defaults(self, default_fps, defaults):
        self.project_fps = default_fps
        self.deinterlace = defaults["deinterlace"]
        self.split_type = defaults["split_type"]
        self.scene_threshold = defaults["scene_threshold"]
        self.break_duration = defaults["break_duration"]
        self.break_ratio = defaults["break_ratio"]
        self.thumbnail_type = defaults["thumbnail_type"]
        self.resize = defaults["resize"]
        self.resynthesize = defaults["resynthesize"]
        self.inflate = defaults["inflate"]
        self.upscale = defaults["upscale"]
        self.upscale_option = defaults["upscale_option"]
        self.min_frames_per_scene = defaults["min_frames_per_scene"]
        self.split_time = defaults["split_time"]
        self.inflate_by_option = defaults["inflate_by_option"]
        self.inflate_slow_option = defaults["inflate_slow_option"]
        self.resynth_option = defaults["resynth_option"]
        self.frame_format = defaults["frame_format"]
        self.audio_format = defaults["sound_format"]

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
        self.split_frames = self._calc_split_frames(self.project_fps, self.split_time)
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

    def _calc_split_frames(self, fps, seconds):
        return round(float(fps) * float(seconds))

    # keep project's own copy of original video
    # it will be needed later if restarting the project
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

    # make a .mp4 container copy of original video if it's not already .mp4
    # this will be needed later to cut audio wav files
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
            Mtqdm().update_bar(bar)

    def copy_project_file(self, copy_path):
        project_file = VideoRemixerState.determine_project_filepath(self.project_path)
        saved_project_file = os.path.join(copy_path, self.DEF_FILENAME)
        shutil.copy(project_file, saved_project_file)
        return saved_project_file

    SCENES_PATH = "SCENES"
    DROPPED_SCENES_PATH = "DROPPED_SCENES"

    # when advancing forward from the Set Up Project step
    # the user may be redoing the project from this step
    # need to purge anything created based on old settings
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

    # split video into frames
    def render_source_frames(self, global_options, prevent_overwrite=False):
        self.frames_path = os.path.join(self.project_path, self.FRAMES_PATH)
        if prevent_overwrite:
            if os.path.exists(self.frames_path) and get_files(self.frames_path, self.frame_format):
                return None

        video_path = self.source_video

        source_frame_rate = float(self.video_details["frame_rate"])
        source_frame_count = int(self.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.project_fps)

        self.output_pattern = f"source_%0{index_width}d.{self.frame_format}"
        frame_rate = self.project_fps
        create_directory(self.frames_path)

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Copying source video to frame files - no ETA")
            ffmpeg_cmd = MP4toPNG(video_path,
                                  self.output_pattern,
                                  frame_rate,
                                  self.frames_path,
                                  deinterlace=self.deinterlace,
                                  global_options=global_options,
                                  type=self.frame_format)
            Mtqdm().update_bar(bar)
        return ffmpeg_cmd

    # this is intended to be called after source frames have been rendered
    def enhance_video_info(self, log_fn, ignore_errors=True):
        """Get the actual dimensions of the frame files"""
        if self.scene_names and not self.video_details.get("source_width", None):
            self.uncompile_scenes()
            first_scene_name = self.scene_names[0]
            first_scene_path = os.path.join(self.scenes_path, first_scene_name)
            scene_files = sorted(get_files(first_scene_path, self.frame_format))
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
            message = f"no frame files found in {first_scene_path}"
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
                                self.frame_format,
                                "scene",
                                self.scene_threshold,
                                0.0,
                                0.0,
                                log_fn).split(type=self.frame_format)
                    Mtqdm().update_bar(bar)

            elif self.split_type == "Break":
                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "Splitting video by detected break - no ETA")
                    SplitScenes(self.frames_path,
                                self.scenes_path,
                                self.frame_format,
                                "break",
                                0.0,
                                float(self.break_duration),
                                float(self.break_ratio),
                                log_fn).split(type=self.frame_format)
                    Mtqdm().update_bar(bar)
            elif self.split_type == "Time":
                # split by seconds
                SplitFrames(
                    self.frames_path,
                    self.scenes_path,
                    self.frame_format,
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
                    self.frame_format,
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
        ResequenceFiles(frames_source, self.frame_format, "scene_frame", 0, 1, 1, 0, index_width, True,
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
                        global_options=global_options).slice_frame_group(scene_name,
                            slice_name=thumbnail_filename, type=self.frame_format)

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
                        global_options=global_options).slice_frame_group(scene_name,
                                                                    ignore_errors=True,
                                                                    slice_name=thumbnail_filename,
                                                                    type=self.frame_format)
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

    SPLIT_LABELS = r"(?P<sort>\(.*?\))?(?P<hint>\{.*?\})?\s*(?P<title>.*)?"

    def split_label(self, label):
        """Splits a label such as '(01){I:2S} My Title (part1){b}' into
        sort: '01', hint: 'I:2S' label: 'My Title (part1){b}' parts """
        try:
            matches = re.search(self.SPLIT_LABELS, label)
            groups = matches.groups()
            sort = groups[0][1:-1] if groups[0] else None
            hint = groups[1][1:-1] if groups[1] else None
            title = groups[2].strip() if groups[2] else None
            return sort, hint, title
        except Exception:
            return None, None, None

    def compose_label(self, sort_mark, hint_mark, title):
        composed = []
        if sort_mark:
            composed.append(f"({sort_mark})")
        if hint_mark:
            composed.append(f"{{{hint_mark}}}")
        if title:
            if(len(composed)):
                composed.append(" ")
            composed.append(title)
        return "".join(composed)

    def split_hint(self, hint : str):
        """Splits a processing hint string such as 'a:1,B:22,C:3c3' into a dict"""
        hints = hint.split(",")
        results = {}
        hint : str
        for hint in hints:
            parts = hint.split(":")
            if len(parts) == 2:
                results[parts[0].upper()] = parts[1].upper()
        return results

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
            return scene_index, scene_name, thumbnail_path, scene_state, scene_info, scene_label
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while getting scene chooser data: {error}")

    def kept_scenes(self) -> list:
        """Returns kept scene names sorted"""
        return sorted([scene for scene in self.scene_states if self.scene_states[scene] == "Keep"])

    def dropped_scenes(self) -> list:
        """Returns dropped scene names sorted"""
        return sorted([scene for scene in self.scene_states if self.scene_states[scene] == "Drop"])

    def sort_marked_scenes(self) -> dict:
        """Returns dict mapping scene sort mark to scene name."""
        result = {}
        for scene_name in self.scene_names:
            scene_label = self.scene_labels.get(scene_name)
            sort, _, _ = self.split_label(scene_label)
            if sort:
                result[sort] = scene_name
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

    ## Scene Splitter Functions ##

    def compute_preview_frame(self, log_fn, scene_index, split_percent):
        scene_index = int(scene_index)
        num_scenes = len(self.scene_names)
        last_scene = num_scenes - 1
        if scene_index < 0 or scene_index > last_scene:
            return None

        scene_name = self.scene_names[scene_index]
        _, num_frames, _, _, split_frame = self.compute_scene_split(scene_name, split_percent)
        original_scene_path = os.path.join(self.scenes_path, scene_name)
        frame_files = self.valid_split_scene_cache(scene_index)
        if not frame_files:
            # optimize to uncompile only the first time it's needed
            self.uncompile_scenes()

            frame_files = sorted(get_files(original_scene_path))
            self.fill_split_scene_cache(scene_index, frame_files)

        num_frame_files = len(frame_files)
        if num_frame_files != num_frames:
            log_fn(f"compute_preview_frame(): expected {num_frame_files} frame files but found {num_frames} for scene index {scene_index} - returning None")
            return None
        return frame_files[split_frame]

    def compute_advance_702(self,
                            scene_index,
                            split_percent,
                            by_next : bool,
                            by_minute=False,
                            by_second=False,
                            by_exact_second=False,
                            exact_second=0):
        if not isinstance(scene_index, (int, float)):
            return None

        scene_index = int(scene_index)
        scene_name = self.scene_names[scene_index]
        first_frame, last_frame, _ = details_from_group_name(scene_name)
        num_frames = (last_frame - first_frame) + 1
        split_percent_frame = num_frames * split_percent / 100.0

        if by_exact_second:
            frames_1s = self.project_fps
            new_split_frame = frames_1s * exact_second
        elif by_minute:
            frames_60s = self.project_fps * 60
            new_split_frame = \
                split_percent_frame + frames_60s if by_next else split_percent_frame - frames_60s
        elif by_second:
            frames_1s = self.project_fps
            new_split_frame = \
                split_percent_frame + frames_1s if by_next else split_percent_frame - frames_1s
        else: # by frame
            new_split_frame = split_percent_frame + 1 if by_next else split_percent_frame - 1

        new_split_frame = 0 if new_split_frame < 0 else new_split_frame
        new_split_frame = num_frames if new_split_frame > num_frames else new_split_frame

        new_split_percent = new_split_frame / num_frames
        return new_split_percent * 100.0

    def compute_scene_split(self, scene_name : str, split_percent : float, override_num_frames=0):
        split_percent = 0.0 if isinstance(split_percent, type(None)) else split_percent
        split_point = split_percent / 100.0

        # these are not reliable if override_num_frames is in use
        first_frame, last_frame, num_width = details_from_group_name(scene_name)

        num_frames = override_num_frames or ((last_frame - first_frame) + 1)
        split_frame = math.ceil(num_frames * split_point)

        # ensure at least one frame remains in the lower scene
        split_frame = 1 if split_frame == 0 else split_frame
        # ensure at least one frame remains in the upper scene
        split_frame = num_frames-1 if split_frame >= num_frames else split_frame

        return num_width, num_frames, first_frame, last_frame, split_frame

    def split_scene_content(self,
                            content_path : str,
                            scene_name : str,
                            new_lower_scene_name : str,
                            new_upper_scene_name : str,
                            num_frames : int,
                            split_frame : int):
        original_scene_path = os.path.join(content_path, scene_name)
        new_lower_scene_path = os.path.join(content_path, new_lower_scene_name)
        new_upper_scene_path = os.path.join(content_path, new_upper_scene_name)

        frame_files = sorted(get_files(original_scene_path))
        num_frame_files = len(frame_files)
        if num_frame_files != num_frames:
            message = f"Mismatch between expected frames ({num_frames}) and found frames " + \
                f"({num_frame_files}) in content path '{original_scene_path}'"
            raise ValueError(message)

        create_directory(new_upper_scene_path)

        for index, frame_file in enumerate(frame_files):
            if index < split_frame:
                continue
            frame_path = os.path.join(original_scene_path, frame_file)
            _, filename, ext = split_filepath(frame_path)
            new_frame_path = os.path.join(new_upper_scene_path, filename + ext)
            shutil.move(frame_path, new_frame_path)
        os.replace(original_scene_path, new_lower_scene_path)

    def split_processed_content(self,
                                content_path : str,
                                scene_name : str,
                                new_lower_scene_name : str,
                                new_upper_scene_name : str,
                                split_percent : float):
        original_scene_path = os.path.join(content_path, scene_name)
        new_lower_scene_path = os.path.join(content_path, new_lower_scene_name)
        new_upper_scene_path = os.path.join(content_path, new_upper_scene_name)

        frame_files = sorted(get_files(original_scene_path))
        create_directory(new_upper_scene_path)

        _, _, _, _, split_frame = self.compute_scene_split(
            scene_name, split_percent, override_num_frames=len(frame_files))
        for index, frame_file in enumerate(frame_files):
            if index < split_frame:
                continue
            frame_path = os.path.join(original_scene_path, frame_file)
            _, filename, ext = split_filepath(frame_path)
            new_frame_path = os.path.join(new_upper_scene_path, filename + ext)
            shutil.move(frame_path, new_frame_path)
        os.replace(original_scene_path, new_lower_scene_path)

    def split_scene(self, log_fn, scene_index, split_percent, remixer_settings, global_options,
                    keep_before=False, keep_after=False):
        if not isinstance(scene_index, (int, float)):
            raise ValueError("Scene index must be an int or float")

        num_scenes = len(self.scene_names)
        last_scene = num_scenes - 1
        scene_index = int(scene_index)

        if scene_index < 0 or scene_index > last_scene:
            raise ValueError(f"Scene index is outside of valid range 0 to {last_scene}")

        # ensure all scenes are in the scenes directory
        self.uncompile_scenes()

        scene_name = self.scene_names[scene_index]
        num_width, num_frames, first_frame, last_frame, split_frame = self.compute_scene_split(
            scene_name, split_percent)

        if num_frames < 2:
            raise ValueError(f"Scene has fewer than two frames")

        new_lower_first_frame = first_frame
        new_lower_last_frame = first_frame + (split_frame - 1)
        new_lower_scene_name = VideoRemixerState.encode_scene_name(num_width,
                                                new_lower_first_frame, new_lower_last_frame, 0, 0)
        new_upper_first_frame = first_frame + split_frame
        new_upper_last_frame = last_frame
        new_upper_scene_name = VideoRemixerState.encode_scene_name(num_width,
                                                new_upper_first_frame, new_upper_last_frame, 0, 0)

        # this may fail, so copy the original scene and project file to the purged content directory
        scene_path = os.path.join(self.scenes_path, scene_name)
        purge_root = self.purge_paths([scene_path], keep_original=True, additional_path=self.SCENES_PATH)
        if purge_root:
            self.copy_project_file(purge_root)

        try:
            self.split_scene_content(self.scenes_path,
                                    scene_name,
                                    new_lower_scene_name,
                                    new_upper_scene_name,
                                    num_frames,
                                    split_frame)
        except ValueError as error:
            raise ValueError(f"Error '{error}' encountered while splitting scene")

        self.scene_names[scene_index] = new_lower_scene_name
        self.scene_names.append(new_upper_scene_name)
        self.scene_names = sorted(self.scene_names)

        # remember original scene's state before splitting
        scene_state = self.scene_states[scene_name]
        del self.scene_states[scene_name]

        if keep_before:
            self.scene_states[new_lower_scene_name] = "Keep"
            self.scene_states[new_upper_scene_name] = "Drop"
            self.current_scene = scene_index
        elif keep_after:
            self.scene_states[new_lower_scene_name] = "Drop"
            self.scene_states[new_upper_scene_name] = "Keep"
            self.current_scene = scene_index + 1
        else:
            # retain original scene state for both splits
            self.scene_states[new_lower_scene_name] = scene_state
            self.scene_states[new_upper_scene_name] = scene_state
            self.current_scene = scene_index

        thumbnail_file = self.thumbnails[scene_index]
        log_fn(f"about to delete original thumbnail file '{thumbnail_file}'")
        os.remove(thumbnail_file)
        self.create_thumbnail(new_lower_scene_name, log_fn, global_options,
                                    remixer_settings)
        log_fn(f"about to create thumbnail for new upper scene {new_upper_scene_name}")
        self.create_thumbnail(new_upper_scene_name, log_fn, global_options,
                                    remixer_settings)
        self.thumbnails = sorted(get_files(self.thumbnail_path))

        paths = [
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path
        ]
        processed_content_split = False
        for path in paths:
            if path and os.path.exists(path):
                dirs = get_directories(path)
                if scene_name in dirs:

                    # this may fail, so copy the processed content to the purged content directory
                    processed_path = os.path.join(path, scene_name)
                    _, last_path, _ = split_filepath(path)
                    purge_root = self.purge_paths([processed_path], purged_path=purge_root,
                                            keep_original=True, additional_path=last_path)

                    try:
                        processed_content_split = True
                        self.split_processed_content(path,
                                                    scene_name,
                                                    new_lower_scene_name,
                                                    new_upper_scene_name,
                                                    split_percent)
                    except ValueError as error:
                        log_fn(
                            f"Error splitting processed content path {path}: {error} - ignored")
                        continue
                else:
                    log_fn(f"Planned skip of splitting processed content path {path}: scene {scene_name} not found")
            else:
                log_fn(f"Planned skip of splitting processed content path {path}: path not found")

        if processed_content_split:
            log_fn("invalidating processed audio content after splitting")
            self.clean_remix_audio()

        self.invalidate_split_scene_cache()

        return f"Scene split into new scenes {new_lower_scene_name} and {new_upper_scene_name}"

    ## Main Processing ##

    RESIZE_STEP = "resize"
    RESYNTH_STEP = "resynth"
    INFLATE_STEP = "inflate"
    UPSCALE_STEP = "upscale"
    AUDIO_STEP = "audio"
    VIDEO_STEP = "video"

    PURGED_CONTENT = "purged_content"

    def prepare_process_remix(self, redo_resynth, redo_inflate, redo_upscale):
        self.setup_processing_paths()

        self.recompile_scenes()

        if self.processed_content_invalid:
            self.purge_processed_content(purge_from=self.RESIZE_STEP)
            self.processed_content_invalid = False
        else:
            self.purge_stale_processed_content(redo_resynth, redo_inflate, redo_upscale)
            self.purge_incomplete_processed_content()
        self.save()

    def process_remix(self, log_fn, kept_scenes, remixer_settings, engine, engine_settings,
                      realesrgan_settings):
        if self.resize_needed():
            self.resize_scenes(log_fn,
                               kept_scenes,
                               remixer_settings)

        if self.resynthesize_needed():
            self.resynthesize_scenes(log_fn,
                                     kept_scenes,
                                     engine,
                                     engine_settings,
                                     self.resynth_option)

        if self.inflate_needed():
            self.inflate_scenes(log_fn,
                                kept_scenes,
                                engine,
                                engine_settings)

        if self.upscale_needed():
            self.upscale_scenes(log_fn,
                                kept_scenes,
                                realesrgan_settings,
                                remixer_settings)

        return self.generate_remix_report(self.processed_content_complete(self.RESIZE_STEP),
                                          self.processed_content_complete(self.RESYNTH_STEP),
                                          self.processed_content_complete(self.INFLATE_STEP),
                                          self.processed_content_complete(self.UPSCALE_STEP))

    def resize_needed(self):
        return self.resize \
            and not self.processed_content_complete(self.RESIZE_STEP)

    def resynthesize_needed(self):
        return self.resynthesize \
            and not self.processed_content_complete(self.RESYNTH_STEP)

    def inflate_chosen(self):
        if self.inflate:
            return True

        # see if a processing hint requires inflation
        kept_scenes = self.kept_scenes()
        for scene_name in kept_scenes:
            label = self.scene_labels.get(scene_name)
            if label:
                _, hint, _ = self.split_label(label)
                if hint:
                    hints = self.split_hint(hint)
                    inflation_hint = hints.get("I")
                    if inflation_hint:
                        return True
        return False

    def inflate_needed(self):
        if self.inflate_chosen() and not self.processed_content_complete(self.INFLATE_STEP):
            return True

    def upscale_needed(self):
        return self.upscale \
            and not self.processed_content_complete(self.UPSCALE_STEP)

    def purge_paths(self, path_list : list, keep_original=False, purged_path=None, skip_empty_paths=False, additional_path=""):
        """Purge a list of paths to the purged content directory
        keep_original: True=don't remove original content when purging
        purged_path: Used if calling multiple times to store purged content in the same purge directory
        skip_empty_paths: True=don't purge directories that have no files inside
        additional_path: If set, adds an additional segment onto the storage path (not returned)
        Returns: Path to the purged content directory (not incl. additional_path)
        """
        paths_to_purge = []
        for path in path_list:
            if path and os.path.exists(path):
                if not skip_empty_paths or directory_populated(path, files_only=True):
                    paths_to_purge.append(path)
        if not paths_to_purge:
            return None

        purged_root_path = os.path.join(self.project_path, self.PURGED_CONTENT)
        create_directory(purged_root_path)

        if not purged_path:
            purged_path, _ = AutoIncrementDirectory(purged_root_path).next_directory("purged")

        for path in paths_to_purge:
            use_purged_path = os.path.join(purged_path, additional_path)
            if keep_original:
                _, last_path, _ = split_filepath(path)
                copy_path = os.path.join(use_purged_path, last_path)
                copy_files(path, copy_path)
            else:
                shutil.move(path, use_purged_path)
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

    def purge_processed_content(self, purge_from=RESIZE_STEP):
        purge_paths = [self.resize_path,
                       self.resynthesis_path,
                       self.inflation_path,
                       self.upscale_path]

        if purge_from == self.RESIZE_STEP:
            purge_paths = purge_paths[0:]
        elif purge_from == self.RESYNTH_STEP:
            purge_paths = purge_paths[1:]
        elif purge_from == self.INFLATE_STEP:
            purge_paths = purge_paths[2:]
        elif purge_from == self.UPSCALE_STEP:
            purge_paths = purge_paths[3:]
        else:
            raise RuntimeError(f"Unrecognized value {purge_from} passed to purge_processed_content()")

        purge_root = self.purge_paths(purge_paths)
        self.clean_remix_content(purge_from="audio_clips", purge_root=purge_root)
        return purge_root

    def clean_remix_content(self, purge_from, purge_root=None):
        clean_paths = [self.audio_clips_path,
                       self.video_clips_path,
                       self.clips_path]

        # purge all of the paths, keeping the originals, for safekeeping ahead of reprocessing
        purge_root = self.purge_paths(clean_paths, keep_original=True, purged_path=purge_root,
                                      skip_empty_paths=True)
        if purge_root:
            self.copy_project_file(purge_root)

        if purge_from == "audio_clips":
            clean_paths = clean_paths[0:]
            self.audio_clips = []
            self.video_clips = []
            self.clips = []
        elif purge_from == "video_clips":
            clean_paths = clean_paths[1:]
            self.video_clips = []
            self.clips = []
        elif purge_from == "scene_clips":
            clean_paths = clean_paths[2:]
            self.clips = []

        # clean directories as needed by purge_from
        # audio wav files can be slow to extract, so they are carefully not cleaned unless needed
        clean_directories(clean_paths)
        return purge_root

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
    def purge_stale_processed_content(self, purge_resynth, purge_inflation, purge_upscale):
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

        if self.inflate_chosen() and not self.processed_content_complete(self.INFLATE_STEP):
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
            if self.inflate_chosen():
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

    def prepare_save_remix(self, log_fn, global_options, remixer_settings, output_filepath : str):
        if not output_filepath:
            raise ValueError("Enter a path for the remixed video to proceed")

        self.recompile_scenes()

        kept_scenes = self.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes were found")

        self.drop_empty_processed_scenes(kept_scenes)
        self.save()

        # get this again in case scenes have been auto-dropped
        kept_scenes = self.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes after removing empties")

        # create audio clips only if they do not already exist
        # this depends on the audio clips being purged at the time the scene selection are compiled
        if self.video_details["has_audio"] and not self.processed_content_complete(
                self.AUDIO_STEP):
            audio_format = remixer_settings["audio_format"]
            self.create_audio_clips(log_fn, global_options, audio_format=audio_format)
            self.save()

        # always recreate video and scene clips
        self.clean_remix_content(purge_from="video_clips")
        return kept_scenes

    def save_remix(self, log_fn, global_options, kept_scenes):
        self.create_video_clips(log_fn, kept_scenes, global_options)
        self.save()

        self.create_scene_clips(log_fn, kept_scenes, global_options)
        self.save()

        if not self.clips:
            raise ValueError("No processed video clips were found")

        ffcmd = self.create_remix_video(log_fn, global_options, self.output_filepath)
        log_fn(f"FFmpeg command: {ffcmd}")
        self.save()

    def save_custom_remix(self,
                          log_fn,
                          output_filepath,
                          global_options,
                          kept_scenes,
                          custom_video_options,
                          custom_audio_options,
                          draw_text_options=None,
                          use_scene_sorting=True):
        _, _, output_ext = split_filepath(output_filepath)
        output_ext = output_ext[1:]

        self.create_custom_video_clips(log_fn, kept_scenes, global_options,
                                             custom_video_options=custom_video_options,
                                             custom_ext=output_ext,
                                             draw_text_options=draw_text_options)
        self.save()

        self.create_custom_scene_clips(kept_scenes, global_options,
                                             custom_audio_options=custom_audio_options,
                                             custom_ext=output_ext)
        self.save()

        if not self.clips:
            raise ValueError("No processed video clips were found")

        ffcmd = self.create_remix_video(log_fn, global_options, output_filepath,
                                        use_scene_sorting=use_scene_sorting)
        log_fn(f"FFmpeg command: {ffcmd}")
        self.save()

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
                    crop_offset_y=self.crop_offset_y).resize(type=self.frame_format)

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
    def one_pass_resynthesis(self, log_fn, input_path, output_path, output_basename,
                             engine : InterpolateSeries):
        file_list = sorted(get_files(input_path, extension=self.frame_format))
        log_fn(f"beginning series of frame recreations at {output_path}")
        engine.interpolate_series(file_list, output_path, 1, "interframe", offset=2,
                                  type=self.frame_format)

        log_fn(f"auto-resequencing recreated frames at {output_path}")
        ResequenceFiles(output_path,
                        self.frame_format,
                        "resynthesized_frame",
                        1, 1, # start, step
                        1, 0, # stride, offset
                        -1,   # auto-zero fill
                        True, # rename
                        log_fn).resequence()

    def two_pass_resynth_pass(self, log_fn, input_path, output_path, output_basename,
                              engine : InterpolateSeries):
        file_list = sorted(get_files(input_path, extension=self.frame_format))

        inflated_frames = os.path.join(output_path, "inflated_frames")
        log_fn(f"beginning series of interframe recreations at {inflated_frames}")
        create_directory(inflated_frames)
        engine.interpolate_series(file_list, inflated_frames, 1, "interframe",
                                  type=self.frame_format)

        log_fn(f"selecting odd interframes only at {inflated_frames}")
        ResequenceFiles(inflated_frames,
                        self.frame_format,
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

                num_splits = 0
                disable_inflation = False

                # see if the scene has a processing hint such as 'I:4A'
                label = self.scene_labels.get(scene_name)
                if label:
                    _, hint, _ = self.split_label(label)
                    if hint:
                        log_fn(f"inflate_scenes(): found processing hint: {hint}")
                        hints = self.split_hint(hint)
                        inflation_hint = hints.get("I")
                        if inflation_hint:
                            log_fn(f"found inflation processing hint: {inflation_hint}")
                            if "1" in inflation_hint:
                                log_fn("forcing disable of inflation")
                                num_splits = 0
                                disable_inflation = True
                            elif "2" in inflation_hint:
                                log_fn("forcing 2X inflation")
                                num_splits = 1
                            elif "4" in inflation_hint:
                                log_fn("forcing 4X inflation")
                                num_splits = 2
                            elif "8" in inflation_hint:
                                log_fn("forcing 8X inflation")
                                num_splits = 3

                if num_splits == 0 and self.inflate and not disable_inflation:
                    if self.inflate_by_option == "2X":
                        num_splits = 1
                    elif self.inflate_by_option == "4X":
                        num_splits = 2
                    elif self.inflate_by_option == "8X":
                        num_splits = 3

                if num_splits:
                    # the scene needs inflating
                    output_basename = "interpolated_frames"
                    file_list = sorted(get_files(scene_input_path, extension=self.frame_format))
                    series_interpolater.interpolate_series(file_list,
                                                        scene_output_path,
                                                        num_splits,
                                                        output_basename,
                                                        type=self.frame_format)
                    ResequenceFiles(scene_output_path,
                                    self.frame_format,
                                    "inflated_frame",
                                    1, 1,
                                    1, 0,
                                    -1,
                                    True,
                                    log_fn).resequence()
                else:
                    # no need to inflate so just copy the files using the resequencer
                    ResequenceFiles(scene_input_path,
                                    self.frame_format,
                                    "inflated_frame",
                                    1, 1,
                                    1, 0,
                                    -1,
                                    False,
                                    log_fn,
                                    output_path=scene_output_path).resequence()

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
                                self.frame_format)

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
        if self.inflate_chosen():
            if self.inflate:
                # enabled overall in the project
                label += "-in" + self.inflate_by_option[0]
            else:
                # enabled via a processing hint
                label += "-inH"
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

    def generate_remix_report(self, resize, resynthesize, inflate, upscale):
        report = Jot()

        if not resize \
            and not resynthesize \
            and not inflate \
            and not upscale:
            report.add(f"Original source scenes in {self.scenes_path}")

        if resize:
            report.add(f"Resized/cropped scenes in {self.resize_path}")

        if resynthesize:
            report.add(f"Resynthesized scenes in {self.resynthesis_path}")

        if inflate:
            report.add(f"Inflated scenes in {self.inflation_path}")

        if upscale:
            report.add(f"Upscaled scenes in {self.upscale_path}")

        return report.lines




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
        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate_chosen():
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

    # TODO the last three paths in the list won't have scene name directories but instead files
    #      also it should delete the audio wav file if found since that isn't deleted each save
    # drop an already-processed scene to cut it from the remix video
    def force_drop_processed_scene(self, scene_index):
        scene_name = self.scene_names[scene_index]
        self.drop_kept_scene(scene_name)
        removed = []
        purge_dirs = []
        for path in [
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path,
            self.audio_clips_path,
            self.video_clips_path,
            self.clips_path
        ]:
            content_path = os.path.join(path, scene_name)
            if os.path.exists(content_path):
                purge_dirs.append(content_path)
        purge_root = self.purge_paths(purge_dirs)
        removed += purge_dirs

        if purge_root:
            self.copy_project_file(purge_root)

        # audio clips aren't cleaned each time a remix is saved
        # clean now to ensure the dropped scene audio clip is removed
        self.clean_remix_content(purge_from="audio_clips")

        # TODO this didn't ever work
        # if self.audio_clips_path:
        #     self.audio_clips = sorted(get_files(self.audio_clips_path))

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

    def compute_inflated_fps(self, force_inflation, force_audio, force_inflate_by, force_silent):
        motion_factor, audio_slow_motion, silent_slow_motion, project_inflation_rate = \
            self.compute_effective_slow_motion(force_inflation, force_audio, force_inflate_by,
                                               force_silent)

        if audio_slow_motion or silent_slow_motion:
            fps_factor = project_inflation_rate
        else:
            fps_factor = motion_factor

        return self.project_fps * fps_factor

    def compute_forced_inflation(self, scene_name):
        force_inflation = False
        force_audio = False
        force_inflate_by = None
        force_silent = False
        label = self.scene_labels.get(scene_name)
        if label:
            _, hint, _ = self.split_label(label)
            if hint:
                hints = self.split_hint(hint)
                inflation_hint = hints.get("I")
                if inflation_hint:
                    if "1" in inflation_hint:
                        # noop inflation
                        force_inflate_by = "1X"
                    elif "2" in inflation_hint:
                        force_inflation = True
                        force_inflate_by = "2X"
                    elif "4" in inflation_hint:
                        force_inflation = True
                        force_inflate_by = "4X"
                    elif "8" in inflation_hint:
                        force_inflation = True
                        force_inflate_by = "8X"

                    if "A" in inflation_hint:
                        force_audio = True
                    elif "S" in inflation_hint:
                        force_silent = True
        return force_inflation, force_audio, force_inflate_by, force_silent

    def compute_scene_fps(self, scene_name):
        force_inflation, force_audio, force_inflate_by, force_silent =\
            self.compute_forced_inflation(scene_name)

        return self.compute_inflated_fps(force_inflation,
                                         force_audio,
                                         force_inflate_by,
                                         force_silent)

    def create_video_clips(self, log_fn, kept_scenes, global_options):
        self.video_clips_path = os.path.join(self.clips_path, self.VIDEO_CLIPS_PATH)
        create_directory(self.video_clips_path)
        # save the project now to preserve the newly established path
        self.save()

        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate_chosen():
            scenes_base_path = self.inflation_path
        elif self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.video_clips_path, f"{scene_name}.mp4")

                video_clip_fps = self.compute_scene_fps(scene_name)

                ResequenceFiles(scene_input_path,
                                self.frame_format,
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
                                global_options=global_options,
                                type=self.frame_format)
                Mtqdm().update_bar(bar)

        self.video_clips = sorted(get_files(self.video_clips_path))

    def inflation_rate(self, inflate_by : str):
        if not inflate_by:
            return 1
        return int(inflate_by[0])

    def compute_effective_slow_motion(self, force_inflation, force_audio, force_inflate_by,
                                      force_silent):
        motion_factor = 1.0
        audio_slow_motion = False
        silent_slow_motion = False
        project_inflation_rate = 1
        audio_slow_motion = force_audio or self.inflate_slow_option == "Audio"
        silent_slow_motion = force_silent or self.inflate_slow_option == "Silent"

        if self.inflate or force_inflation:
            if self.inflate:
                # for slow motion, the project FPS should not be increased
                if not audio_slow_motion and not silent_slow_motion:
                    project_inflation_rate = self.inflation_rate(self.inflate_by_option)

            forced_inflation_rate = self.inflation_rate(force_inflate_by)
            motion_factor = project_inflation_rate

            if forced_inflation_rate != project_inflation_rate:
                if forced_inflation_rate > project_inflation_rate:
                    motion_factor = forced_inflation_rate
                else:
                    motion_factor = project_inflation_rate / float(forced_inflation_rate)

        return motion_factor, audio_slow_motion, silent_slow_motion, project_inflation_rate

    def compute_inflated_audio_options(self, custom_audio_options, force_inflation, force_audio,
                                       force_inflate_by, force_silent):

        motion_factor, audio_slow_motion, silent_slow_motion, _ = \
            self.compute_effective_slow_motion(force_inflation, force_audio, force_inflate_by,
                                               force_silent)

        audio_inflation = 1 #self.inflation_rate(self.inflate_by_option) if self.inflate else 1
        audio_motion_factor = motion_factor / audio_inflation

        if audio_slow_motion:
            if audio_motion_factor == 8:
                output_options = '-filter:a "atempo=0.5,atempo=0.5,atempo=0.5" -c:v copy -shortest ' \
                    + custom_audio_options
            elif audio_motion_factor == 4:
                output_options = '-filter:a "atempo=0.5,atempo=0.5" -c:v copy -shortest ' \
                    + custom_audio_options
            elif audio_motion_factor == 2:
                output_options = '-filter:a "atempo=0.5" -c:v copy -shortest ' + custom_audio_options
            elif audio_motion_factor == 1:
                output_options = '-filter:a "atempo=1.0" -c:v copy -shortest ' + custom_audio_options
            elif audio_motion_factor == 0.5:
                output_options = '-filter:a "atempo=2.0" -c:v copy -shortest ' + custom_audio_options
            elif audio_motion_factor == 0.25:
                output_options = '-filter:a "atempo=2.0,atempo=2.0" -c:v copy -shortest ' \
                    + custom_audio_options
            elif audio_motion_factor == 0.125:
                output_options = '-filter:a "atempo=2.0,atempo=2.0,atempo=2.0" -c:v copy -shortest ' \
                    + custom_audio_options
        elif silent_slow_motion:
            # check for an existing audio sample rate, so the silent footage will blend properly
            # with non-silent footage, otherwise there may be an audio/video data length mismatch
            sample_rate = self.video_details.get("sample_rate", "48000")
            output_options = \
                '-f lavfi -i anullsrc -ac 2 -ar ' + sample_rate + ' -map 0:v:0 -map 2:a:0 -c:v copy -shortest ' \
                + custom_audio_options
        else:
            output_options = custom_audio_options

        return output_options

    def create_scene_clips(self, log_fn, kept_scenes, global_options):
        if self.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.video_clips[index]
                    scene_audio_path = self.audio_clips[index]
                    scene_output_filepath = os.path.join(self.clips_path, f"{scene_name}.mp4")

                    force_inflation, force_audio, force_inflate_by, force_silent =\
                        self.compute_forced_inflation(scene_name)

                    output_options = self.compute_inflated_audio_options("-c:a aac -shortest ",
                                                                         force_inflation,
                                                                         force_audio,
                                                                         force_inflate_by,
                                                                         force_silent)
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
        # save the project now to preserve the newly established path
        self.save()

        if self.upscale:
            scenes_base_path = self.upscale_path
        elif self.inflate_chosen():
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

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for index, scene_name in enumerate(kept_scenes):
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.video_clips_path,
                                                     f"{scene_name}.{custom_ext}")
                use_custom_video_options = custom_video_options
                if use_custom_video_options.find("<LABEL>") != -1:
                    try:
                        label : str = labels[index]

                        # strip the sort and hint marks in case present
                        _, _, label = self.split_label(label)

                        # trim whitespace
                        label = label.strip() if label else ""

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

                video_clip_fps = self.compute_scene_fps(scene_name)

                ResequenceFiles(scene_input_path,
                                self.frame_format,
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
                            custom_options=use_custom_video_options,
                            type=self.frame_format)
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

                    force_inflation, force_audio, force_inflate_by, force_silent =\
                        self.compute_forced_inflation(scene_name)

                    output_options = self.compute_inflated_audio_options(custom_audio_options,
                                                                         force_inflation,
                                                                         force_audio=force_audio,
                                                                         force_inflate_by=force_inflate_by,
                                                                         force_silent=force_silent)

                    combine_video_audio(scene_video_path, scene_audio_path,
                                        scene_output_filepath, global_options=global_options,
                                        output_options=output_options)
                    Mtqdm().update_bar(bar)
            self.clips = sorted(get_files(self.clips_path))
        else:
            self.clips = sorted(get_files(self.video_clips_path))

    def assembly_list(self, log_fn, clip_filepaths : list, rename_clips=True) -> list:
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

        # assemble scenes with sorting marks ahead of unmarked scenes
        assembly = []
        unlabeled_scenes = kept_scenes

        sort_marked_scenes = self.sort_marked_scenes()
        sort_marks = sorted(list(sort_marked_scenes.keys()))
        for sort_mark in sort_marks:
            scene_name = sort_marked_scenes[sort_mark]
            kept_clip_filepath = map_scene_name_to_clip.get(scene_name)
            if kept_clip_filepath:
                if rename_clips:
                    scene_label = self.scene_labels.get(scene_name)
                    if scene_label:
                        _, _, title = self.split_label(scene_label)
                        if title:
                            new_filename = simple_sanitize_filename(title)
                            path, filename, ext = split_filepath(kept_clip_filepath)
                            new_filepath = os.path.join(path, f"{new_filename}_{filename}" + ext)
                            log_fn(f"renaming clip {kept_clip_filepath} to {new_filepath}")
                            os.replace(kept_clip_filepath, new_filepath)
                            kept_clip_filepath = new_filepath

                assembly.append(kept_clip_filepath)
                unlabeled_scenes.remove(scene_name)

        # add the unlabeled clips
        for scene_name in unlabeled_scenes:
            assembly.append(map_scene_name_to_clip[scene_name])

        return assembly

    def create_remix_video(self, log_fn, global_options, output_filepath, use_scene_sorting=True):
        with Mtqdm().open_bar(total=1, desc="Saving Remix") as bar:
            Mtqdm().message(bar, "Using FFmpeg to concatenate scene clips - no ETA")
            assembly_list = self.assembly_list(log_fn, self.clips) \
                if use_scene_sorting else self.clips
            ffcmd = combine_videos(assembly_list,
                                   output_filepath,
                                   global_options=global_options)
            Mtqdm().update_bar(bar)
        return ffcmd

    def choose_scene_range(self, first_scene_index, last_scene_index, scene_state):
        for scene_index in range(first_scene_index, last_scene_index + 1):
            scene_name = self.scene_names[scene_index]
            self.scene_states[scene_name] = scene_state

    def valid_split_scene_cache(self, scene_index):
        if self.split_scene_cache and self.split_scene_cached_index == scene_index:
            return self.split_scene_cache
        else:
            return None

    def fill_split_scene_cache(self, scene_index, data):
        self.split_scene_cache = data
        self.split_scene_cached_index = scene_index

    def invalidate_split_scene_cache(self):
        self.split_scene_cache = []
        self.split_scene_cached_index = -1




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

        # IDEA further possible checks: files have bytes,
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

    def export_project(self, log_fn, new_project_path, new_project_name, kept_scenes):
        new_project_name = new_project_name.strip()
        full_new_project_path = os.path.join(new_project_path, new_project_name)

        create_directory(full_new_project_path)
        new_profile_filepath = self.copy_project_file(full_new_project_path)

        # load the copied project file
        new_state = VideoRemixerState.load(new_profile_filepath, log_fn)

        # update project paths to the new one
        new_state = VideoRemixerState.load_ported(new_state.project_path, new_profile_filepath,
                                                  log_fn, save_original=False)

        # ensure the project directories exist
        new_state.post_load_integrity_check()

        # copy the source video
        with Mtqdm().open_bar(total=1, desc="Copying") as bar:
            Mtqdm().message(bar, "Copying source video - no ETA")
            shutil.copy(self.source_video, new_state.source_video)
            Mtqdm().update_bar(bar)

        # copy the source audio (if not using the source video as audio source)
        if self.source_audio != self.source_video:
            with Mtqdm().open_bar(total=1, desc="Copying") as bar:
                Mtqdm().message(bar, "Copying source audio - no ETA")
                shutil.copy(self.source_audio, new_state.source_audio)
                Mtqdm().update_bar(bar)

        # ensure scenes path contains all / only kept scenes
        self.recompile_scenes()

        # prepare to rebuild scene_states dict, and scene_names, thumbnails lists
        # in the new project
        new_state.scene_states = {}
        new_state.scene_names = []
        new_state.thumbnails = []

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Exporting") as bar:
            for index, scene_name in enumerate(self.scene_names):
                state = self.scene_states[scene_name]
                if state == "Keep":
                    scene_name = self.scene_names[index]
                    new_state.scene_states[scene_name] = "Keep"

                    new_state.scene_names.append(scene_name)
                    scene_dir = os.path.join(self.scenes_path, scene_name)
                    new_scene_dir = os.path.join(new_state.scenes_path, scene_name)
                    duplicate_directory(scene_dir, new_scene_dir)

                    scene_thumbnail = self.thumbnails[index]
                    _, filename, ext = split_filepath(scene_thumbnail)
                    new_thumbnail = os.path.join(new_state.thumbnail_path, filename + ext)
                    new_state.thumbnails.append(new_thumbnail)
                    shutil.copy(scene_thumbnail, new_thumbnail)
                    Mtqdm().update_bar(bar)

        # reset some things
        new_state.current_scene = 0
        new_state.audio_clips = []
        new_state.clips = []
        new_state.processed_content_invalid = False
        new_state.progress = "choose"

        new_state.save()

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
                    state.split_frames = state._calc_split_frames(state.project_fps, state.split_time)
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
                # new frame and found format options
                try:
                    if not state.frame_format:
                        state.frame_format = "png"
                except AttributeError:
                        state.frame_format = "png"
                try:
                    if not state.sound_format:
                        state.sound_format = "wav"
                except AttributeError:
                        state.sound_format = "wav"

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
