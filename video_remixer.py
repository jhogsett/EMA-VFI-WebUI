"""Video Remixer UI state management"""
import os
import math
import re
import shutil
from typing import Callable
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, clean_filename, copy_files, directory_populated
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf, shrink, format_table
from webui_utils.video_utils import details_from_group_name, get_essential_video_details, \
    MP4toPNG, SourceToMP4, rate_adjusted_count, image_size
from webui_utils.jot import Jot
from webui_utils.mtqdm import Mtqdm
from split_scenes import SplitScenes
from split_frames import SplitFrames
from slice_video import SliceVideo
from resequence_files import ResequenceFiles
from video_remixer_project import VideoRemixerProject

class VideoRemixerState():
    def __init__(self, remixer_settings : dict, global_options : dict, log_fn : Callable):
        # used internally only
        self.project = VideoRemixerProject(self, log_fn)
        self.remixer_settings = remixer_settings
        self.global_options = global_options
        self.log_fn = log_fn
        self.split_scene_cache = []
        self.split_scene_cached_index = -1

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

    # remove transient state
    def __getstate__(self):
        state = self.__dict__.copy()
        internal_state = [
            "project",
            "remixer_settings",
            "global_options",
            "log_fn",
            "split_scene_cache",
            "split_scene_cached_index"
        ]
        for attribute in internal_state:
            if attribute in state:
                del state[attribute]
        return state

    PROJECT_PATH_PREFIX = "REMIX-"
    FILENAME_FILTER = [" ", "'", "[", "]"]
    SCENES_PATH = "SCENES"
    DROPPED_SCENES_PATH = "DROPPED_SCENES"
    FRAMES_PATH = "SOURCE"
    THUMBNAILS_PATH = "THUMBNAILS"
    SPLIT_LABELS = r"(?P<sort>\(.*?\))?(?P<hint>\{.*?\})?\s*(?P<title>.*)?"
    KEEP_MARK = "Keep"
    DROP_MARK = "Drop"
    RESIZE_HINT = "R"
    RESYNTHESIS_HINT = "Y"
    INFLATION_HINT = "I"
    UPSCALE_HINT = "U"
    RESIZE_STEP = "resize"
    RESYNTH_STEP = "resynth"
    INFLATE_STEP = "inflate"
    UPSCALE_STEP = "upscale"
    AUDIO_STEP = "audio"
    VIDEO_STEP = "video"
    PURGED_CONTENT = "purged_content"
    PURGED_DIR = "purged"
    RESIZE_PATH = "SCENES-RC"
    RESYNTH_PATH = "SCENES-RE"
    INFLATE_PATH = "SCENES-IN"
    UPSCALE_PATH = "SCENES-UP"
    CLIPS_PATH = "CLIPS"
    AUDIO_CLIPS_PATH = "AUDIO"
    VIDEO_CLIPS_PATH = "VIDEO"

    ## Global Concern

    def log(self, message):
        self.log_fn(message)

    def save(self, filepath : str=None):
        self.project.save(filepath)

    def kept_scenes(self) -> list:
        """Returns kept scene names sorted"""
        return sorted([scene for scene in self.scene_states
                       if self.scene_states[scene] == self.KEEP_MARK])

    def dropped_scenes(self) -> list:
        """Returns dropped scene names sorted"""
        return sorted([scene for scene in self.scene_states
                       if self.scene_states[scene] == self.DROP_MARK])



    # ## Ingestion Concern

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

    # split video into frames
    def render_source_frames(self, prevent_overwrite=False):
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
                                  global_options=self.global_options,
                                  type=self.frame_format)
            Mtqdm().update_bar(bar)
        return ffmpeg_cmd

    # this is intended to be called after source frames have been rendered
    def enhance_video_info(self, ignore_errors=True):
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
                    self.log(f"Error: {error}")
                    if not ignore_errors:
                        raise error
                return
            message = f"no frame files found in {first_scene_path}"
            if ignore_errors:
                self.log(message)
            else:
                raise ValueError(message)

    # make a .mp4 container copy of original video if it's not already .mp4
    # this will be needed later to cut audio wav files
    # this is expected to be called after save_original_video()
    def create_source_audio(self, crf, prevent_overwrite=True, skip_mp4=True):
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
            SourceToMP4(self.source_video, self.source_audio, crf,
                        global_options=self.global_options)
            Mtqdm().update_bar(bar)

    def scenes_present(self):
        self.uncompile_scenes()
        return self.scenes_path and \
            os.path.exists(self.scenes_path) and \
            get_directories(self.scenes_path)

    def split_scenes(self, prevent_overwrite=False):
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
                                self.log_fn).split(type=self.frame_format)
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
                                self.log_fn).split(type=self.frame_format)
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
                    self.log_fn).split()
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
                    self.log_fn).split()
            return None
        except ValueError as error:
            return error
        except RuntimeError as error:
            return error

    # create a scene thumbnail, assumes:
    # - scenes uncompiled
    # - thumbnail path already exists
    def create_thumbnail(self, scene_name):
        self.thumbnail_path = os.path.join(self.project_path, self.THUMBNAILS_PATH)
        frames_source = os.path.join(self.scenes_path, scene_name)

        source_frame_rate = float(self.video_details["frame_rate"])
        source_frame_count = int(self.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.project_fps)

        self.log(f"auto-resequencing source frames at {frames_source}")
        ResequenceFiles(frames_source, self.frame_format, "scene_frame", 0, 1, 1, 0, index_width,
                        True, self.log_fn).resequence()

        thumbnail_filename = f"thumbnail[{scene_name}]"

        if self.thumbnail_type == "JPG":
            thumb_scale = self.remixer_settings["thumb_scale"]
            max_thumb_size = self.remixer_settings["max_thumb_size"]
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
                        self.log,
                        global_options=self.global_options).slice_frame_group(scene_name,
                                                                    slice_name=thumbnail_filename,
                                                                    type=self.frame_format)
        elif self.thumbnail_type == "GIF":
            gif_fps = self.remixer_settings["default_gif_fps"]
            gif_factor = self.remixer_settings["gif_factor"]
            gif_end_delay = self.remixer_settings["gif_end_delay"]
            thumb_scale = self.remixer_settings["thumb_scale"]
            max_thumb_size = self.remixer_settings["max_thumb_size"]
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
                        self.log,
                        global_options=self.global_options).slice_frame_group(scene_name,
                                                                    ignore_errors=True,
                                                                    slice_name=thumbnail_filename,
                                                                    type=self.frame_format)
        else:
            raise ValueError(f"thumbnail type '{self.thumbnail_type}' is not implemented")

    def create_thumbnails(self):
        self.thumbnail_path = os.path.join(self.project_path, self.THUMBNAILS_PATH)
        create_directory(self.thumbnail_path)
        clean_directories([self.thumbnail_path])
        self.uncompile_scenes()

        with Mtqdm().open_bar(total=len(self.scene_names), desc="Create Thumbnails") as bar:
            for scene_name in self.scene_names:
                self.create_thumbnail(scene_name)
                Mtqdm().update_bar(bar)

    # shrink low-frame count scenes related code

    @staticmethod
    def decode_scene_name(scene_name):
        """Returns the first frame, last frame and count of frames"""
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

    def consolidate_scenes(self):
        container_data, num_width = VideoRemixerState.get_container_data(self.scenes_path)
        state = {"path" : self.scenes_path,
                 "num_width" : num_width,
                 "log_fn" : self.log_fn}
        with Mtqdm().open_bar(total=1, desc="Shrink") as bar:
            Mtqdm().message(bar, "Shrinking small scenes - no ETA")
            shrunk_container_data = shrink(container_data, self.min_frames_per_scene,
                                           VideoRemixerState.move_frames,
                                           VideoRemixerState.remove_scene,
                                           VideoRemixerState.rename_scene, state)
            Mtqdm().update_bar(bar)
        self.log(f"shrunk container data: {shrunk_container_data}")


    ## Scene Labels, Sort Marks, Processing Hints, Titles Concern

    def split_label(self, label):
        """Splits a label such as '(01){I:2S} My Title (part1){b}' into
        sort: '01', hint: 'I:2S' label: 'My Title (part1){b}' parts """
        if not label:
            return None, None, None
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

    def get_hint(self, scene_label, hint_type):
        """return a found hint of the passed type if the label exists and it is found"""
        if scene_label:
            _, hint, _ = self.split_label(scene_label)
            if hint:
                hints = self.split_hint(hint)
                return hints.get(hint_type)
        return None

    def hint_present(self, hint_type):
        """return True if any kept scene has the passed hint type"""
        kept_scenes = self.kept_scenes()
        for scene_name in kept_scenes:
            label = self.scene_labels.get(scene_name)
            if self.get_hint(label, hint_type):
                return True
        return False

    # remove scene labels that do not have a corresponding scene name
    def clean_scene_labels(self):
        for scene_name, scene_label in self.scene_labels.copy().items():
            if not scene_name in self.scene_names:
                self.log(f"deleting unused scene label {scene_label}")
                del self.scene_labels[scene_name]
        self.save()

    def add_slomo(self, scene_index, slomo_hint):
        scene_name = self.scene_names[scene_index]
        scene_label = self.scene_labels.get(scene_name) or ""

        # TODO need to add/modify instead of replace all existing hints
        sort_mark, _, title = self.split_label(scene_label)
        new_label = self.compose_label(sort_mark, slomo_hint, title)
        self.set_scene_label(scene_index, new_label)
        self.save()

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
        self.scene_states = {scene_name : self.KEEP_MARK for scene_name in self.scene_names}

    def drop_all_scenes(self):
        self.scene_states = {scene_name : self.DROP_MARK for scene_name in self.scene_names}

    def invert_all_scenes(self):
        new_states = {}
        for k, v in self.scene_states.items():
            new_states[k] = self.KEEP_MARK if v == self.DROP_MARK else self.DROP_MARK
        self.scene_states = new_states

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
            keep_state = True if scene_state == self.KEEP_MARK else False
            scene_label = self.scene_labels.get(scene_name)
            return scene_name, thumbnail_path, scene_state, scene_position, scene_start, \
                scene_duration, keep_state, scene_label
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while computing scene chooser details: {error}")
        except IndexError as error:
            raise ValueError(
                f"IndexError encountered while computing scene chooser details: {error}")

    def scene_marker(self, scene_name):
        scene_index = self.scene_names.index(scene_name)
        _, _, _, _, scene_start, scene_duration, _, _ = self.scene_chooser_data(scene_index)
        marker = f"[{scene_index} {scene_name} {scene_start} +{scene_duration}]"
        return marker

    def scene_title(self, scene_name):
        scene_index = self.scene_names.index(scene_name)
        _, _, _, scene_position, _, _, _, _ = self.scene_chooser_data(scene_index)
        return scene_position


    ## Processing Concern

    def sort_marked_scenes(self) -> dict:
        """Returns dict mapping scene sort mark to scene name."""
        result = {}
        for scene_name in self.scene_names:
            scene_label = self.scene_labels.get(scene_name)
            sort, _, _ = self.split_label(scene_label)
            if sort:
                result[sort] = scene_name
        return result

    def setup_processing_paths(self):
        self.resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
        self.resynthesis_path = os.path.join(self.project_path, self.RESYNTH_PATH)
        self.inflation_path = os.path.join(self.project_path, self.INFLATE_PATH)
        self.upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)

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

    def resize_chosen(self):
        return self.resize or self.hint_present(self.RESIZE_HINT)

    def resynthesize_chosen(self):
        return self.resynthesize or self.hint_present(self.RESYNTHESIS_HINT)

    def inflate_chosen(self):
        return self.inflate or self.hint_present(self.INFLATION_HINT)

    def upscale_chosen(self):
        return self.upscale or self.hint_present(self.UPSCALE_HINT)

    def purge_paths(self, path_list : list, keep_original=False, purged_path=None,
                    skip_empty_paths=False, additional_path=""):
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
            purged_path, _ = AutoIncrementDirectory(purged_root_path).next_directory(self.PURGED_DIR)

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
            self.project.copy_project_file(purge_root)

        if purge_from == "audio_clips":
            clean_paths = clean_paths[0:]
            self.audio_clips = []
            self.video_clips = []
            self.clips = []
        elif purge_from == "video_clips":
            clean_paths = clean_paths[1:]
            self.video_clips = []
            self.clips = []
        elif purge_from == "remix_clips":
            clean_paths = clean_paths[2:]
            self.clips = []

        # clean directories as needed by purge_from
        # audio wav files can be slow to extract, so they are carefully not cleaned unless needed
        clean_directories(clean_paths)
        return purge_root

    def clean_remix_audio(self):
        clean_directories([self.audio_clips_path])

    def default_remix_filepath(self, extra_suffix=""):
        _, filename, _ = split_filepath(self.source_video)
        suffix = self.remix_filename_suffix(extra_suffix)
        return os.path.join(self.project_path, f"{filename}-{suffix}.mp4")

    def remix_filename_suffix(self, extra_suffix):
        label = "remix"

        if self.resize_chosen():
            label += "-rc" if self.resize else "-rcH"
        else:
            label += "-or"

        if self.resynthesize_chosen():
            if self.resynthesize:
                label += "-re"
                if self.resynth_option == "Clean":
                    label += "C"
                elif self.resynth_option == "Scrub":
                    label += "S"
                elif self.resynth_option == "Replace":
                    label += "R"
            else:
                label += "-reH"

        if self.inflate_chosen():
            if self.inflate:
                label += "-in" + self.state.inflate_by_option[0]
                if self.inflate_slow_option == "Audio":
                    label += "SA"
                elif self.inflate_slow_option == "Silent":
                    label += "SM"
            else:
                label += "-inH"

        if self.upscale_chosen():
            if self.upscale:
                label += "-up" + self.state.upscale_option[0]
            else:
                label += "-upH"

        label += "-" + extra_suffix if extra_suffix else ""
        return label


    ## UI Concern

    # set project settings UI defaults in case the project is reopened
    # otherwise some UI elements get set to None on reopened new projects

    def scene_chooser_details(self, scene_index, display_gap):
        try:
            scene_name, thumbnail_path, scene_state, scene_position, scene_start, scene_duration, \
                keep_state, scene_label = self.scene_chooser_data(scene_index)

            scene_time = f"{scene_start}{display_gap}+{scene_duration}"
            keep_symbol = SimpleIcons.HEART if keep_state == True else ""
            scene_info = f"{scene_position}{display_gap}{scene_time}{display_gap}{keep_symbol}"
            return scene_index, scene_name, thumbnail_path, scene_state, scene_info, scene_label
        except ValueError as error:
            raise ValueError(
                f"ValueError encountered while getting scene chooser data: {error}")

    def compute_preview_frame(self, scene_index, split_percent):
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
            self.log(f"compute_preview_frame(): expected {num_frame_files} frame files but found {num_frames} for scene index {scene_index} - returning None")
            return None
        return frame_files[split_frame]

    def compute_advance_702(self,
                            scene_index,
                            split_percent,
                            by_next : bool,
                            by_minute=False,
                            by_second=False,
                            by_exact_second=False,
                            exact_second=0,
                            by_exact_frame=False,
                            exact_frame=0):
        if not isinstance(scene_index, (int, float)):
            return None

        scene_index = int(scene_index)
        scene_name = self.scene_names[scene_index]
        first_frame, last_frame, _ = details_from_group_name(scene_name)
        num_frames = (last_frame - first_frame) + 1
        split_percent_frame = num_frames * split_percent / 100.0
        frames_1s = self.project_fps
        frames_60s = frames_1s * 60

        if by_exact_frame:
            if exact_frame < 0:
                new_split_frame = (num_frames + exact_frame) #- 1
            else:
                new_split_frame = exact_frame
        elif by_exact_second:
            if exact_second < 0:
                new_split_frame = (num_frames + (frames_1s * exact_second)) #- 1
            else:
                new_split_frame = frames_1s * exact_second
        elif by_minute:
            new_split_frame = \
                split_percent_frame + frames_60s if by_next else split_percent_frame - frames_60s
        elif by_second:
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

    def split_scene(self, scene_index, split_percent, keep_before=False, keep_after=False,
                    backup_scene=True):
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

        if backup_scene:
            scene_path = os.path.join(self.scenes_path, scene_name)
            purge_root = self.purge_paths([scene_path], keep_original=True,
                                          additional_path=self.SCENES_PATH)
            if purge_root:
                self.project.copy_project_file(purge_root)

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
            self.scene_states[new_lower_scene_name] = self.KEEP_MARK
            self.scene_states[new_upper_scene_name] = self.DROP_MARK
            self.current_scene = scene_index
        elif keep_after:
            self.scene_states[new_lower_scene_name] = self.DROP_MARK
            self.scene_states[new_upper_scene_name] = self.KEEP_MARK
            self.current_scene = scene_index + 1
        else:
            # retain original scene state for both splits
            self.scene_states[new_lower_scene_name] = scene_state
            self.scene_states[new_upper_scene_name] = scene_state
            self.current_scene = scene_index

        thumbnail_file = self.thumbnails[scene_index]
        self.log(f"about to delete original thumbnail file '{thumbnail_file}'")
        os.remove(thumbnail_file)
        self.create_thumbnail(new_lower_scene_name)
        self.log(f"about to create thumbnail for new upper scene {new_upper_scene_name}")
        self.create_thumbnail(new_upper_scene_name)
        self.thumbnails = sorted(get_files(self.thumbnail_path))

        paths = [
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path
        ]
        processed_content_split = False
        purge_root = None
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
                        self.log(
                            f"Error splitting processed content path {path}: {error} - ignored")
                        continue
                else:
                    self.log(f"Planned skip of splitting processed content path {path}: scene {scene_name} not found")
            else:
                self.log(f"Planned skip of splitting processed content path {path}: path not found")

        if processed_content_split:
            self.log("invalidating processed audio content after splitting")
            self.clean_remix_audio()

        self.invalidate_split_scene_cache()

        return f"Scene split into new scenes {new_lower_scene_name} and {new_upper_scene_name}"

    def save_progress(self, progress : str, save_project : bool=True):
        self.progress = progress
        if save_project:
            self.save()


    ## Reporting Concern

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

    # TODO consolidate reports
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
