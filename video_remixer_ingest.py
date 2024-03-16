"""Video Remixer UI state management"""
import os
import shutil
from typing import Callable, TYPE_CHECKING
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, clean_filename
from webui_utils.simple_utils import shrink
from webui_utils.video_utils import get_essential_video_details, MP4toPNG, SourceToMP4, \
    rate_adjusted_count, image_size
from webui_utils.mtqdm import Mtqdm
from split_scenes import SplitScenes
from split_frames import SplitFrames
from slice_video import SliceVideo
from resequence_files import ResequenceFiles

if TYPE_CHECKING:
    from video_remixer import VideoRemixerState

class VideoRemixerIngest():
    def __init__(self, state : "VideoRemixerState", log_fn : Callable):
        self.state = state
        self.log_fn = log_fn

    def log(self, message):
        if self.log_fn:
            self.log_fn(message)

    PROJECT_PATH_PREFIX = "REMIX-"
    FILENAME_FILTER = [" ", "'", "[", "]"]
    FRAMES_PATH = "SOURCE"

    ## Exports -------------------

    # keep project's own copy of original video
    # it will be needed later if restarting the project
    def save_original_video(self, prevent_overwrite=True):
        _, filename, ext = split_filepath(self.state.source_video)
        video_filename = filename + ext

        # clean various problematic chars from filenames
        filtered_filename = clean_filename(video_filename, self.FILENAME_FILTER)
        project_video_path = os.path.join(self.state.project_path, filtered_filename)

        if os.path.exists(project_video_path) and prevent_overwrite:
            raise ValueError(
            f"The local project video file already exists, copying skipped: {project_video_path}")

        with Mtqdm().open_bar(total=1, desc="Copying") as bar:
            Mtqdm().message(bar, "Copying source video locally - no ETA")
            shutil.copy(self.state.source_video, project_video_path)
            self.state.source_video = project_video_path
            Mtqdm().update_bar(bar)

    def ingest_video(self, video_path):
        """Inspect submitted video and collect important details about it for project set up"""
        self.state.source_video = video_path
        path, filename, _ = split_filepath(video_path)

        with Mtqdm().open_bar(total=1, desc="FFprobe") as bar:
            Mtqdm().message(bar, "Inspecting source video - no ETA")
            try:
                video_details = get_essential_video_details(video_path)
                self.state.video_details = video_details
            except RuntimeError as error:
                raise ValueError(str(error))
            finally:
                Mtqdm().update_bar(bar)

        filtered_filename = clean_filename(filename, self.FILENAME_FILTER)
        project_path = os.path.join(path, f"{self.PROJECT_PATH_PREFIX}{filtered_filename}")
        resize_w = int(video_details['display_width'])
        resize_h = int(video_details['display_height'])
        crop_w, crop_h = resize_w, resize_h

        self.state.project_path = project_path
        self.state.resize_w = resize_w
        self.state.resize_h = resize_h
        self.state.crop_w = crop_w
        self.state.crop_h = crop_h
        self.state.crop_offset_x = -1
        self.state.crop_offset_y = -1
        self.state.project_fps = float(video_details['frame_rate'])

    # create a scene thumbnail, assumes:
    # - scenes uncompiled
    # - thumbnail path already exists
    def create_thumbnail(self, scene_name):
        self.state.thumbnail_path = os.path.join(self.state.project_path, self.state.THUMBNAILS_PATH)
        frames_source = os.path.join(self.state.scenes_path, scene_name)

        source_frame_rate = float(self.state.video_details["frame_rate"])
        source_frame_count = int(self.state.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.state.project_fps)

        self.state.log(f"auto-resequencing source frames at {frames_source}")
        ResequenceFiles(frames_source, self.state.frame_format, "scene_frame", 0, 1, 1, 0, index_width,
                        True, self.state.log_fn).resequence()

        thumbnail_filename = f"thumbnail[{scene_name}]"

        if self.state.thumbnail_type == "JPG":
            thumb_scale = self.state.remixer_settings["thumb_scale"]
            max_thumb_size = self.state.remixer_settings["max_thumb_size"]
            video_w = self.state.video_details['display_width']
            video_h = self.state.video_details['display_height']
            max_frame_dimension = video_w if video_w > video_h else video_h
            thumb_size = max_frame_dimension * thumb_scale
            if thumb_size > max_thumb_size:
                thumb_scale = max_thumb_size / max_frame_dimension

            SliceVideo(self.state.source_video,
                        self.state.project_fps,
                        self.state.scenes_path,
                        self.state.thumbnail_path,
                        thumb_scale,
                        "jpg",
                        0,
                        1,
                        0,
                        False,
                        0.0,
                        0.0,
                        self.state.log,
                        global_options=self.state.global_options).slice_frame_group(scene_name,
                                                                    slice_name=thumbnail_filename,
                                                                    type=self.state.frame_format)
        elif self.state.thumbnail_type == "GIF":
            gif_fps = self.state.remixer_settings["default_gif_fps"]
            gif_factor = self.state.remixer_settings["gif_factor"]
            gif_end_delay = self.state.remixer_settings["gif_end_delay"]
            thumb_scale = self.state.remixer_settings["thumb_scale"]
            max_thumb_size = self.state.remixer_settings["max_thumb_size"]
            video_w = self.state.video_details['display_width']
            video_h = self.state.video_details['display_height']

            max_frame_dimension = video_w if video_w > video_h else video_h
            thumb_size = max_frame_dimension * thumb_scale
            if thumb_size > max_thumb_size:
                thumb_scale = max_thumb_size / max_frame_dimension
            self.state.thumbnail_path = os.path.join(self.state.project_path, "THUMBNAILS")

            SliceVideo(self.state.source_video,
                        self.state.project_fps,
                        self.state.scenes_path,
                        self.state.thumbnail_path,
                        thumb_scale,
                        "gif",
                        0,
                        gif_factor,
                        0,
                        False,
                        gif_fps,
                        gif_end_delay,
                        self.state.log,
                        global_options=self.state.global_options).slice_frame_group(scene_name,
                                                                    ignore_errors=True,
                                                                    slice_name=thumbnail_filename,
                                                                    type=self.state.frame_format)
        else:
            raise ValueError(f"thumbnail type '{self.state.thumbnail_type}' is not implemented")

    def consolidate_scenes(self):
        container_data, num_width = VideoRemixerIngest.get_container_data(self.state.scenes_path)
        state = {"path" : self.state.scenes_path,
                 "num_width" : num_width,
                 "log_fn" : self.state.log_fn}
        with Mtqdm().open_bar(total=1, desc="Shrink") as bar:
            Mtqdm().message(bar, "Shrinking small scenes - no ETA")
            shrunk_container_data = shrink(container_data, self.state.min_frames_per_scene,
                                           VideoRemixerIngest.move_frames,
                                           VideoRemixerIngest.remove_scene,
                                           VideoRemixerIngest.rename_scene, state)
            Mtqdm().update_bar(bar)
        self.state.log(f"shrunk container data: {shrunk_container_data}")

    def scenes_present(self):
        self.state.uncompile_scenes()
        return self.state.scenes_path and \
            os.path.exists(self.state.scenes_path) and \
            get_directories(self.state.scenes_path)

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


    ## Internal ------------------

    # split video into frames
    def render_source_frames(self, prevent_overwrite=False):
        self.state.frames_path = os.path.join(self.state.project_path, self.FRAMES_PATH)
        if prevent_overwrite:
            if os.path.exists(self.state.frames_path) and get_files(self.state.frames_path, self.state.frame_format):
                return None

        video_path = self.state.source_video

        source_frame_rate = float(self.state.video_details["frame_rate"])
        source_frame_count = int(self.state.video_details["frame_count"])
        _, index_width = rate_adjusted_count(source_frame_count, source_frame_rate, self.state.project_fps)

        self.state.output_pattern = f"source_%0{index_width}d.{self.state.frame_format}"
        frame_rate = self.state.project_fps
        create_directory(self.state.frames_path)

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Copying source video to frame files - no ETA")
            ffmpeg_cmd = MP4toPNG(video_path,
                                  self.state.output_pattern,
                                  frame_rate,
                                  self.state.frames_path,
                                  deinterlace=self.state.deinterlace,
                                  global_options=self.state.global_options,
                                  type=self.state.frame_format)
            Mtqdm().update_bar(bar)
        return ffmpeg_cmd

    # this is intended to be called after source frames have been rendered
    def enhance_video_info(self, ignore_errors=True):
        """Get the actual dimensions of the frame files"""
        if self.state.scene_names and not self.state.video_details.get("source_width", None):
            self.state.uncompile_scenes()
            first_scene_name = self.state.scene_names[0]
            first_scene_path = os.path.join(self.state.scenes_path, first_scene_name)
            scene_files = sorted(get_files(first_scene_path, self.state.frame_format))
            if scene_files:
                try:
                    width, height = image_size(scene_files[0])
                    self.state.video_details["source_width"] = width
                    self.state.video_details["source_height"] = height
                except ValueError as error:
                    self.state.log(f"Error: {error}")
                    if not ignore_errors:
                        raise error
                return
            message = f"no frame files found in {first_scene_path}"
            if ignore_errors:
                self.state.log(message)
            else:
                raise ValueError(message)

    # make a .mp4 container copy of original video if it's not already .mp4
    # this will be needed later to cut audio wav files
    # this is expected to be called after save_original_video()
    def create_source_audio(self, crf, prevent_overwrite=True, skip_mp4=True):
        _, filename, ext = split_filepath(self.state.source_video)
        if skip_mp4 and ext.lower() == ".mp4":
            self.state.source_audio = self.state.source_video
            return

        audio_filename = filename  + "-audio" + ".mp4"

        # clean various problematic chars from filenames
        filtered_filename = clean_filename(audio_filename, self.FILENAME_FILTER)
        self.state.source_audio = os.path.join(self.state.project_path, filtered_filename)

        if os.path.exists(self.state.source_audio) and prevent_overwrite:
            raise ValueError(
            f"The local project audio file already exists, copying skipped: {self.state.source_audio}")

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Creating source audio locally - no ETA")
            SourceToMP4(self.state.source_video, self.state.source_audio, crf,
                        global_options=self.state.global_options)
            Mtqdm().update_bar(bar)

    def split_scenes(self, prevent_overwrite=False):
        if prevent_overwrite and self.state.scenes_present():
                return None
        try:
            if self.state.split_type == "Scene":
                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "Splitting video by detected scene - no ETA")
                    SplitScenes(self.state.frames_path,
                                self.state.scenes_path,
                                self.state.frame_format,
                                "scene",
                                self.state.scene_threshold,
                                0.0,
                                0.0,
                                self.state.log_fn).split(type=self.state.frame_format)
                    Mtqdm().update_bar(bar)

            elif self.state.split_type == "Break":
                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "Splitting video by detected break - no ETA")
                    SplitScenes(self.state.frames_path,
                                self.state.scenes_path,
                                self.state.frame_format,
                                "break",
                                0.0,
                                float(self.state.break_duration),
                                float(self.state.break_ratio),
                                self.state.log_fn).split(type=self.state.frame_format)
                    Mtqdm().update_bar(bar)
            elif self.state.split_type == "Time":
                # split by seconds
                SplitFrames(
                    self.state.frames_path,
                    self.state.scenes_path,
                    self.state.frame_format,
                    "precise",
                    0,
                    self.state.split_frames,
                    "copy",
                    False,
                    self.state.log_fn).split()
            else:
                # single split
                SplitFrames(
                    self.state.frames_path,
                    self.state.scenes_path,
                    self.state.frame_format,
                    "precise",
                    1,
                    0,
                    "copy",
                    False,
                    self.state.log_fn).split()
            return None
        except ValueError as error:
            return error
        except RuntimeError as error:
            return error

    def create_thumbnails(self):
        self.state.thumbnail_path = os.path.join(self.state.project_path, self.state.THUMBNAILS_PATH)
        create_directory(self.state.thumbnail_path)
        clean_directories([self.state.thumbnail_path])
        self.state.uncompile_scenes()

        with Mtqdm().open_bar(total=len(self.state.scene_names), desc="Create Thumbnails") as bar:
            for scene_name in self.state.scene_names:
                self.create_thumbnail(scene_name)
                Mtqdm().update_bar(bar)

    # shrink low-frame count scenes related code

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
        first, last, _ = VideoRemixerIngest.decode_scene_name(scene_name)
        new_scene_name = VideoRemixerIngest.encode_scene_name(num_width, first, last, 0,
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

