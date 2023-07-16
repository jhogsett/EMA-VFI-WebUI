"""Video Remixer UI state management"""
import os
import shutil
import yaml
from yaml import Loader, YAMLError
from webui_utils.file_utils import split_filepath, remove_directories, create_directory, get_directories, get_files
from webui_utils.simple_utils import seconds_to_hmsf
from webui_utils.video_utils import details_from_group_name, get_essential_video_details, MP4toPNG, PNGtoMP4, combine_video_audio, combine_videos
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
        self.source_video = None
        self.video_details = {} # set again during project set up (pointing to duplicate copy)

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

    # set project settings UI defaults in case the project is reopened
    # otherwise some UI elements get set to None on reopened new projects
    def set_project_ui_defaults(self, default_fps):
        self.project_fps = default_fps
        self.split_type = "Scene"
        self.scene_threshold = 0.6
        self.break_duration = 2.0
        self.break_ratio = 0.98
        self.thumbnail_type = "JPG"
        self.resynthesize = True
        self.inflate = True
        self.resize = True
        self.upscale = True
        self.upscale_option = "2X"

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

    def save_progress(self, progress : str):
        self.progress = progress
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
            jot.down(f"Frame Rate: {self.video_details['frame_rate']}")
            jot.down(f"Duration: {self.video_details['duration']}")
            jot.down(f"Display Size: {self.video_details['display_dimensions']}")
            jot.down(f"Aspect Ratio: {self.video_details['display_aspect_ratio']}")
            jot.down(f"Content Size: {self.video_details['content_dimensions']}")
            jot.down(f"Frame Count: {self.video_details['frame_count']}")
            jot.down(f"File Size: {self.video_details['file_size']}")
            jot.down(f"Has Audio: {True if self.video_details['has_audio'] else False}")
        return jot

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
            jot.down(f"Project Frame Rate: {self.project_fps}")
            jot.down(f"Deinterlace Source: {self.deinterlace}")
            jot.down(f"Resize To: {self.resize_w}x{self.resize_h}")
            jot.down(f"Crop To: {self.crop_w}x{self.crop_h}")
            jot.down(f"Scene Split Type: {self.split_type}")

            if self.split_type == "Scene":
                jot.down(f"Scene Detection Threshold: {self.scene_threshold}")
            elif self.split_type == "Break":
                jot.down(f"Break Minimum Duration: {self.break_duration}")
                jot.down(f"Break Black Frame Ratio: {self.break_duration}")
            else:
                self.frames_per_minute = int(float(self.project_fps) * 60)
                jot.down(f"Frames per Minute: {self.frames_per_minute}")

            jot.down()

            jot.down(f"Source Video: {self.source_video}")
            jot.down(f"Duration: {self.video_details['duration']}")
            jot.down(f"Frame Rate: {self.video_details['frame_rate']}")
            jot.down(f"File Size: {self.video_details['file_size']}")
            jot.down(f"Frame Count: {self.video_details['frame_count']}")
        return jot

    # keep project's own copy of original video
    # it will be needed later to cut thumbnails and audio clips
    def save_original_video(self, prevent_overwrite=True):
        _, filename, ext = split_filepath(self.source_video)
        video_filename = filename + ext
        project_video_path = os.path.join(self.project_path, video_filename)

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
            self.frames_path,
            self.scenes_path,
            self.dropped_scenes_path,
            self.thumbnail_path,
            self.clips_path,
            self.resize_path,
            self.resynthesis_path,
            self.inflation_path,
            self.upscale_path])
        self.scene_names = []
        self.current_scene = None
        self.thumbnails = []

    FRAMES_PATH = "SOURCE"

    # split video into raw PNG frames
    def render_source_frames(self, global_options):
        video_path = self.source_video
        index_width = self.video_details["index_width"]
        self.output_pattern = f"source_%0{index_width}d.png"
        frame_rate = self.project_fps
        self.frames_path = os.path.join(self.project_path, self.FRAMES_PATH)
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

    def scene_chooser_details(self, scene_name):
        try:
            scene_index = self.scene_names.index(scene_name)
            thumbnail_path = self.thumbnails[scene_index]
            scene_state = self.scene_states[scene_name]
            scene_position = f"{scene_index+1}/{len(self.scene_names)}"

            first_index, last_index, _ = details_from_group_name(scene_name)
            scene_start = seconds_to_hmsf(
                first_index / self.project_fps,
                self.project_fps)
            scene_duration = seconds_to_hmsf(
                (last_index - first_index) / self.project_fps,
                self.project_fps)

            sep = "     "
            scene_info = f"{scene_position}{sep}Time: {scene_start}{sep}Span: {scene_duration}"
            return thumbnail_path, scene_state, scene_info
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
        with Jot() as jot:
            all_scenes = len(self.scene_names)
            all_frames = self.scene_frames("all")
            all_time = self.scene_frames_time(all_frames)
            keep_scenes = len(self.kept_scenes())
            keep_frames = self.scene_frames("keep")
            keep_time = self.scene_frames_time(keep_frames)
            drop_scenes = len(self.dropped_scenes())
            drop_frames = self.scene_frames("drop")
            drop_time = self.scene_frames_time(drop_frames)

            jot.down(f"SOURCE: Scenes: {all_scenes:,d} Frames: {all_frames:,d} Length: {all_time}")
            jot.down()
            jot.down(f"KEEP: Scenes: {keep_scenes:,d} Frames: {keep_frames:,d} Length: {keep_time}")
            jot.down()
            jot.down(f"DROP: Scenes: {drop_scenes:,d} Frames: {drop_frames:,d} Length: {drop_time}")

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

    def purge_processed_content(self, purge_from):
        if purge_from == "resize":
            remove_directories([
                self.resize_path,
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == "resynth":
            remove_directories([
                self.resynthesis_path,
                self.inflation_path,
                self.upscale_path])
        elif purge_from == "inflate":
            remove_directories([
                self.inflation_path,
                self.upscale_path])
        elif purge_from == "upscale":
            remove_directories([
                self.upscale_path])
        remove_directories([self.video_clips_path])
        self.video_clips = []
        self.clips = []

    def processed_content_present(self, present_at):
        if present_at == "resize":
            resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
            return True if os.path.exists(resize_path) and get_directories(resize_path) else False
        elif present_at == "resynth":
            resynth_path = os.path.join(self.project_path, self.RESYNTH_PATH)
            return True if os.path.exists(resynth_path) and get_directories(resynth_path) else False
        elif present_at == "inflate":
            inflate_path = os.path.join(self.project_path, self.INFLATE_PATH)
            return True if os.path.exists(inflate_path) and get_directories(inflate_path) else False
        elif present_at == "upscale":
            upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)
            return True if os.path.exists(upscale_path) and get_directories(upscale_path) else False

    def purge_stale_processed_content(self, purge_upscale):
        # content is stale if it is present on disk but currently deselected
        # its presence indicates it and dependent content is now stale
        if self.processed_content_present("resize") and not self.resize:
            self.purge_processed_content("resize")
        elif self.processed_content_present("resynth") and not self.resynthesize:
            self.purge_processed_content("resynth")
        elif self.processed_content_present("inflate") and not self.inflate:
            self.purge_processed_content("inflate")
        elif self.processed_content_present("upscale") and (not self.upscale or purge_upscale):
            self.purge_processed_content("upscale")

    AUDIO_CLIPS_PATH = "AUDIO"

    def create_audio_clips(self, log_fn, global_options):
        self.audio_clips_path = os.path.join(self.clips_path, self.AUDIO_CLIPS_PATH)
        create_directory(self.audio_clips_path)

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

    RESIZE_PATH = "SCENES-RC"

    def resize_scenes(self, log_fn, kept_scenes, remixer_settings):
        scenes_base_path = self.scenes_path
        self.resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
        create_directory(self.resize_path)

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

        if self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        self.resynthesis_path = os.path.join(self.project_path, self.RESYNTH_PATH)
        create_directory(self.resynthesis_path)

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

        # TODO might need to better manage the flow of content between processing steps
        if self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        self.inflation_path = os.path.join(self.project_path, self.INFLATE_PATH)
        create_directory(self.inflation_path)

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

        # TODO might need to better manage the flow of content between processing steps
        if self.inflate:
            scenes_base_path = self.inflation_path
        elif self.resynthesize:
            scenes_base_path = self.resynthesis_path
        elif self.resize:
            scenes_base_path = self.resize_path
        else:
            scenes_base_path = self.scenes_path

        self.upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)
        create_directory(self.upscale_path)

        upscale_factor = 2.0 if self.upscale_option == "2X" else 4.0
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

    def default_remix_filepath(self):
        _, filename, _ = split_filepath(self.source_video)
        return os.path.join(self.project_path, f"{filename}-remixed.mp4")

    VIDEO_CLIPS_PATH = "VIDEO"

    def create_video_clips(self, log_fn, kept_scenes, global_options):
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
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
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
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Merge Clips") as bar:
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

    def create_remix_video(self, global_options):
        with Mtqdm().open_bar(total=1, desc="Saving Remix") as bar:
            Mtqdm().message(bar, "Using FFmpeg to concatenate scene clips - no ETA")
            ffcmd = combine_videos(self.clips,
                                   self.output_filepath,
                                   global_options=global_options)
            Mtqdm().update_bar(bar)
        return ffcmd

    @staticmethod
    def load(filepath : str):
        with open(filepath, "r") as file:
            try:
                state = yaml.load(file, Loader=Loader)
                state.scene_names = sorted(state.scene_names) if state.scene_names else []
                state.thumbnails = sorted(state.thumbnails) if state.thumbnails else []
                state.audio_clips = sorted(state.audio_clips) if state.audio_clips else []
                state.video_clips = sorted(state.video_clips) if state.video_clips else []
                return state
            except YAMLError as error:
                if hasattr(error, 'problem_mark'):
                    mark = error.problem_mark
                    message = f"Error loading project file on line {mark.line+1} column {mark.column+1}: {error}"
                else:
                    message = error
                raise ValueError(message)
