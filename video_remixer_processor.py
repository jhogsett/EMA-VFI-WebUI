"""Video Remixer Content Processing"""
import os
import math
import re
import shutil
import sys
from typing import Callable
import yaml
from yaml import Loader, YAMLError
from webui_utils.auto_increment import AutoIncrementBackupFilename, AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, clean_filename, remove_directories, copy_files, directory_populated, \
    simple_sanitize_filename, duplicate_directory
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf, shrink, format_table, evenify, ranges_overlap
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

from video_remixer import VideoRemixerState

class VideoRemixerProcessor():
    def __init__(self, state : VideoRemixerState, log_fn : Callable):
        self.state = state
        self.log_fn = log_fn

    RESIZE_STEP = "resize"
    RESYNTH_STEP = "resynth"
    INFLATE_STEP = "inflate"
    UPSCALE_STEP = "upscale"
    AUDIO_STEP = "audio"
    VIDEO_STEP = "video"

    PURGED_CONTENT = "purged_content"
    PURGED_DIR = "purged"

    def prepare_process_remix(self, redo_resynth, redo_inflate, redo_upscale):
        self.setup_processing_paths()

        self.state.recompile_scenes()

        if self.state.rocessed_content_invalid:
            self.purge_processed_content(purge_from=self.RESIZE_STEP)
            self.processed_content_invalid = False
        else:
            self.purge_stale_processed_content(redo_resynth, redo_inflate, redo_upscale)
            self.purge_incomplete_processed_content()
        self.state.save()

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
                                     self.state.resynth_option)

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

    def resize_needed(self):
        return (self.state.resize \
                and not self.processed_content_complete(self.RESIZE_STEP)) \
                or self.state.resize_chosen()

    def resynthesize_needed(self):
        return self.state.resynthesize_chosen() \
            and not self.processed_content_complete(self.RESYNTH_STEP)

    def inflate_needed(self):
        return self.state.inflate_chosen() \
            and not self.processed_content_complete(self.INFLATE_STEP)

    def upscale_needed(self):
        return self.state.upscale_chosen() \
            and not self.processed_content_complete(self.UPSCALE_STEP)

    ## Purging ##

    # TODO maybe move to utils
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

        purged_root_path = os.path.join(self.state.project_path, self.PURGED_CONTENT)
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
        purged_root_path = os.path.join(self.state.project_path, self.PURGED_CONTENT)
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
        clean_paths = [self.state.audio_clips_path,
                       self.state.video_clips_path,
                       self.state.clips_path]

        # purge all of the paths, keeping the originals, for safekeeping ahead of reprocessing
        purge_root = self.purge_paths(clean_paths, keep_original=True, purged_path=purge_root,
                                      skip_empty_paths=True)
        if purge_root:
            self.state.copy_project_file(purge_root)

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

    RESIZE_PATH = "SCENES-RC"
    RESYNTH_PATH = "SCENES-RE"
    INFLATE_PATH = "SCENES-IN"
    UPSCALE_PATH = "SCENES-UP"

    def setup_processing_paths(self):
        self.resize_path = os.path.join(self.state.project_path, self.RESIZE_PATH)
        self.resynthesis_path = os.path.join(self.state.project_path, self.RESYNTH_PATH)
        self.inflation_path = os.path.join(self.state.project_path, self.INFLATE_PATH)
        self.upscale_path = os.path.join(self.state.project_path, self.UPSCALE_PATH)

    def _processed_content_complete(self, path, expected_dirs = 0, expected_files = 0):
        if not path or not os.path.exists(path):
            return False
        if expected_dirs:
            return len(get_directories(path)) == expected_dirs
        if expected_files:
            return len(get_files(path)) == expected_files
        return True

    def processed_content_complete(self, processing_step):
        expected_items = len(self.state.kept_scenes())
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
        if self.processed_content_stale(self.state.resize_chosen(), self.resize_path):
            self.purge_processed_content(purge_from=self.RESIZE_STEP)

        if self.processed_content_stale(self.state.resynthesize_chosen(), self.resynthesis_path) or purge_resynth:
            self.purge_processed_content(purge_from=self.RESYNTH_STEP)

        if self.processed_content_stale(self.state.inflate_chosen(), self.inflation_path) or purge_inflation:
            self.purge_processed_content(purge_from=self.INFLATE_STEP)

        if self.processed_content_stale(self.state.upscale_chosen(), self.upscale_path) or purge_upscale:
            self.purge_processed_content(purge_from=self.UPSCALE_STEP)

    def purge_incomplete_processed_content(self):
        # content is incomplete if the wrong number of scene directories are present
        # if it is currently selected and incomplete, it should be purged
        if self.state.resize_chosen() and not self.processed_content_complete(self.RESIZE_STEP):
            self.purge_processed_content(purge_from=self.RESIZE_STEP)

        if self.state.resynthesize_chosen() and not self.processed_content_complete(self.RESYNTH_STEP):
            self.purge_processed_content(purge_from=self.RESYNTH_STEP)

        if self.state.inflate_chosen() and not self.processed_content_complete(self.INFLATE_STEP):
            self.purge_processed_content(purge_from=self.INFLATE_STEP)

        if self.state.upscale_chosen() and not self.processed_content_complete(self.UPSCALE_STEP):
            self.purge_processed_content(purge_from=self.UPSCALE_STEP)

    def scenes_source_path(self, processing_step):
        processing_path = self.state.scenes_path

        if processing_step == self.RESIZE_STEP:
            # resize is the first processing step and always draws from the scenes path
            pass

        elif processing_step == self.RESYNTH_STEP:
            # resynthesis is the second processing step
            if self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        elif processing_step == self.INFLATE_STEP:
            # inflation is the third processing step
            if self.state.resynthesize_chosen():
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.resynthesis_path
            elif self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        elif processing_step == self.UPSCALE_STEP:
            # upscaling is the fourth processing step
            if self.state.inflate_chosen():
                # if inflation is enabled, draw from the inflation path
                processing_path = self.inflation_path
            elif self.state.resynthesize_chosen():
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.resynthesis_path
            elif self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.resize_path

        return processing_path

    def get_resize_params(self, resize_w, resize_h, crop_w, crop_h, content_width, content_height, remixer_settings):
        if resize_w == content_width and resize_h == content_height:
            scale_type = "none"
        else:
            if resize_w <= content_width and resize_h <= content_height:
                # use the down scaling type if there are only reductions
                # the default "area" type preserves details better on reducing
                scale_type = remixer_settings["scale_type_down"]
            else:
                # otherwise use the upscaling type
                # the default "lanczos" type preserves details better on enlarging
                scale_type = remixer_settings["scale_type_up"]

        if crop_w == resize_w and crop_h == resize_h:
            # disable cropping if none to do
            crop_type = "none"
        elif crop_w > resize_w or crop_h > resize_h:
            # disable cropping if it will wrap/is invalid
            # TODO put bounds on the crop parameters instead of disabling
            crop_type = "none"
        else:
            crop_type = "crop"
        return scale_type, crop_type

    def prepare_save_remix(self, log_fn, global_options, remixer_settings, output_filepath : str,
                           invalidate_video_clips=True):
        if not output_filepath:
            raise ValueError("Enter a path for the remixed video to proceed")

        self.state.recompile_scenes()

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes were found")

        self.drop_empty_processed_scenes(kept_scenes)
        self.state.save()

        # get this again in case scenes have been auto-dropped
        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes after removing empties")

        # create audio clips only if they do not already exist
        # this depends on the audio clips being purged at the time the scene selection are compiled
        if self.state.video_details["has_audio"] and not self.processed_content_complete(
                self.AUDIO_STEP):
            audio_format = remixer_settings["audio_format"]
            self.create_audio_clips(log_fn, global_options, audio_format=audio_format)
            self.state.save()

        # leave video clips if they are complete since we may be only making audio changes
        if invalidate_video_clips or not self.processed_content_complete(self.VIDEO_STEP):
            self.clean_remix_content(purge_from="video_clips")
        else:
            # always recreate remix clips
            self.clean_remix_content(purge_from="remix_clips")

        return kept_scenes

    def save_remix(self, log_fn, global_options, kept_scenes):
        # leave video clips if they are complete since we may be only making audio changes
        if not self.processed_content_complete(self.VIDEO_STEP):
            self.create_video_clips(log_fn, kept_scenes, global_options)
            self.state.save()

        self.create_scene_clips(log_fn, kept_scenes, global_options)
        self.state.save()

        if not self.clips:
            raise ValueError("No processed video clips were found")

        ffcmd = self.create_remix_video(log_fn, global_options, self.state.output_filepath)
        log_fn(f"FFmpeg command: {ffcmd}")
        self.state.save()

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

        # leave video clips if they are complete since we may be only making audio changes
        if not self.processed_content_complete(self.VIDEO_STEP):
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
                     crop_w,
                     crop_h,
                     crop_offset_x,
                     crop_offset_y,
                     scale_type,
                     crop_type,
                     params_fn : Callable | None = None,
                     params_context : any=None):

        ResizeFrames(scene_input_path,
                    scene_output_path,
                    resize_w,
                    resize_h,
                    scale_type,
                    log_fn,
                    crop_type=crop_type,
                    crop_width=crop_w,
                    crop_height=crop_h,
                    crop_offset_x=crop_offset_x,
                    crop_offset_y=crop_offset_y).resize(type=self.frame_format, params_fn=params_fn,
                                                        params_context=params_context)

    def setup_resize_hint(self, content_width, content_height):
        # use the main resize/crop settings if resizing, or the content native
        # dimensions if not, as a foundation for handling resize hints
        if self.resize:
            main_resize_w = self.resize_w
            main_resize_h = self.resize_h
            main_crop_w = self.crop_w
            main_crop_h = self.crop_h
            if self.crop_offset_x < 0:
                main_offset_x = (main_resize_w - main_crop_w) / 2.0
            else:
                main_offset_x = self.crop_offset_x
            if self.crop_offset_y < 0:
                main_offset_y = (main_resize_h - main_crop_h) / 2.0
            else:
                main_offset_y = self.crop_offset_y
        else:
            main_resize_w = content_width
            main_resize_h = content_height
            main_crop_w = content_width
            main_crop_h = content_height
            main_offset_x = 0
            main_offset_y = 0
        return main_resize_w, main_resize_h, main_crop_w, main_crop_h, main_offset_x, main_offset_y

    QUADRANT_ZOOM_HINT = "/"
    QUADRANT_GRID_CHAR = "X"
    PERCENT_ZOOM_HINT = "%"
    COMBINED_ZOOM_HINT = "@"
    ANIMATED_ZOOM_HINT = "-"
    QUADRANT_ZOOM_MIN_LEN = 3 # 1/3
    PERCENT_ZOOM_MIN_LEN = 4  # 123%
    COMBINED_ZOOM_MIN_LEN = 8 # 1/1@100%
    ANIMATED_ZOOM_MIN_LEN = 7 # 1/3-5/7

    def get_quadrant_zoom(self, hint):
        if self.QUADRANT_ZOOM_HINT in hint:
            if len(hint) >= self.QUADRANT_ZOOM_MIN_LEN:
                split_pos = hint.index(self.QUADRANT_ZOOM_HINT)
                quadrant = hint[:split_pos]
                quadrants = hint[split_pos+1:]
            else:
                quadrant, quadrants = 1, 1

            return quadrant, quadrants
        else:
            return None, None

    def get_percent_zoom(self, hint):
        if self.PERCENT_ZOOM_HINT in hint:
            if len(hint) >= self.PERCENT_ZOOM_MIN_LEN:
                zoom_percent = int(hint.replace(self.PERCENT_ZOOM_HINT, ""))
                if zoom_percent >= 100:
                    return zoom_percent
            return 100
        else:
            return None

    def get_zoom_part(self, hint):
        if self.COMBINED_ZOOM_HINT in hint and len(hint) >= self.COMBINED_ZOOM_MIN_LEN:
            type = self.COMBINED_ZOOM_HINT
            quadrant, quadrants, zoom_percent = self.get_combined_zoom(hint)
            return type, quadrant, quadrants, zoom_percent
        if self.QUADRANT_ZOOM_HINT in hint and len(hint) >= self.QUADRANT_ZOOM_MIN_LEN:
            type = self.QUADRANT_ZOOM_HINT
            quadrant, quadrants = self.get_quadrant_zoom(hint)
            return type, quadrant, quadrants, None
        elif self.PERCENT_ZOOM_HINT in hint and len(hint) >= self.PERCENT_ZOOM_MIN_LEN:
            type = self.PERCENT_ZOOM_HINT
            self.get_percent_zoom(hint)
            zoom_percent = self.get_percent_zoom(hint)
            return type, None, None, zoom_percent
        return None, None, None, None

    def get_combined_zoom(self, hint):
        if self.COMBINED_ZOOM_HINT in hint:
            if len(hint) >= self.COMBINED_ZOOM_MIN_LEN:
                split_pos = hint.index(self.COMBINED_ZOOM_HINT)
                hint_a = hint[:split_pos]
                hint_b = hint[split_pos+1:]
                a_type, a_quadrant, a_quadrants, a_zoom_percent = self.get_zoom_part(hint_a)
                b_type, b_quadrant, b_quadrants, b_zoom_percent = self.get_zoom_part(hint_b)
                if a_type == self.PERCENT_ZOOM_HINT and b_type == self.QUADRANT_ZOOM_HINT:
                    zoom_percent = a_zoom_percent
                    quadrant, quadrants = b_quadrant, b_quadrants
                elif a_type == self.QUADRANT_ZOOM_HINT and b_type == self.PERCENT_ZOOM_HINT:
                    zoom_percent = b_zoom_percent
                    quadrant, quadrants = a_quadrant, a_quadrants
                return quadrant, quadrants, zoom_percent
        return None, None, None

    def get_animated_zoom(self, hint):
        if self.ANIMATED_ZOOM_HINT in hint:
            if len(hint) >= self.ANIMATED_ZOOM_MIN_LEN:
                split_pos = hint.index(self.ANIMATED_ZOOM_HINT)
                hint_from = hint[:split_pos]
                hint_to = hint[split_pos+1:]
                from_type, from_param1, from_param2, from_param3 = self.get_zoom_part(hint_from)
                to_type, to_param1, to_param2, to_param3 = self.get_zoom_part(hint_to)
                if from_type and to_type:
                    return from_type, from_param1, from_param2, from_param3, to_type, to_param1, to_param2, to_param3
        return None, None, None, None, None, None, None, None

    def compute_zoom_type(self, type, param1, param2, param3, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h, log_fn):
        if type == self.COMBINED_ZOOM_HINT:
            quadrant, quadrants, zoom_percent = param1, param2, param3
            if quadrant and quadrants and zoom_percent:
                return self.compute_combined_zoom(quadrant, quadrants, zoom_percent,
                                                  main_resize_w, main_resize_h,
                                                  main_offset_x, main_offset_y,
                                                  main_crop_w, main_crop_h, log_fn=log_fn)
        elif type == self.QUADRANT_ZOOM_HINT:
            quadrant, quadrants = param1, param2
            if quadrant and quadrants:
                return self.compute_quadrant_zoom(quadrant, quadrants,
                                                  main_resize_w, main_resize_h,
                                                  main_offset_x, main_offset_y,
                                                  main_crop_w, main_crop_h, log_fn=log_fn)
        elif type == self.PERCENT_ZOOM_HINT:
            zoom_percent = param3
            if zoom_percent:
                return self.compute_percent_zoom(zoom_percent,
                                                 main_resize_w, main_resize_h,
                                                 main_offset_x, main_offset_y,
                                                 main_crop_w, main_crop_h, log_fn=log_fn)

    def compute_quadrant_zoom(self, quadrant, quadrants, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h, log_fn):
        quadrant = int(quadrant) - 1

        if self.QUADRANT_GRID_CHAR in quadrants:
            parts = quadrants.split(self.QUADRANT_GRID_CHAR)
            if len(parts) == 2:
                grid_x = int(parts[0])
                grid_y = int(parts[1])
                magnitude_x = grid_x
                magnitude_y = grid_y

                if magnitude_x >= magnitude_y:
                    magnitude = magnitude_x
                    row = int(quadrant / magnitude_x)
                    column = quadrant % magnitude_x
                else:
                    magnitude = magnitude_y
                    row = int(quadrant / magnitude_x)
                    column = quadrant % magnitude_x
            else:
                magnitude = 1
                magnitude_x = magnitude
                magnitude_y = magnitude
                row = 0
                column = 0
        else:
            magnitude = int(math.sqrt(int(quadrants)))
            magnitude_x = magnitude
            magnitude_y = magnitude
            row = int(quadrant / magnitude)
            column = quadrant % magnitude

        # compute frame scaling
        resize_w = main_resize_w * magnitude
        resize_h = main_resize_h * magnitude

        # compute crop area scaling
        crop_w = main_crop_w * magnitude
        crop_h = main_crop_h * magnitude

        # if the main crop offset is negative, auto-center it within the frame
        # otherwise scale up the specific offset
        offset_x, offset_y = 0, 0
        if main_offset_x < 0:
            offset_x = (resize_w - crop_w) / 2.0
        else:
            offset_x = main_offset_x * magnitude
        if main_offset_y < 0:
            offset_y = (resize_h - crop_h) / 2.0
        else:
            offset_y = main_offset_y * magnitude

        # compute the dimensions of one grid cell given the crop and magnitude(s)
        cell_width = crop_w / magnitude_x
        cell_height = crop_h / magnitude_y

        # compute the upper left corner of the grid cell given the cell dimensions,
        # and row, column; unadjusted for main crop offset
        cell_offset_x = column * cell_width
        cell_offset_y = row * cell_height

        # add the main offset
        cell_offset_x += offset_x
        cell_offset_y += offset_y

        # compute the center point
        center_x = cell_offset_x + (cell_width / 2.0)
        center_y = cell_offset_y + (cell_height / 2.0)

        return resize_w, resize_h, center_x, center_y

    def compute_percent_zoom(self, zoom_percent, main_resize_w, main_resize_h, main_offset_x,
                            main_offset_y, main_crop_w, main_crop_h, log_fn):
        magnitude = zoom_percent / 100.0

        # compute frame scaling
        resize_w = main_resize_w * magnitude
        resize_h = main_resize_h * magnitude

        # compute crop area scaling
        crop_w = main_crop_w * magnitude
        crop_h = main_crop_h * magnitude

        # if the main crop offset is negative, auto-center it within the frame
        # otherwise scale up the specific offset
        offset_x, offset_y = 0, 0
        if main_offset_x < 0:
            offset_x = (resize_w - crop_w) / 2.0
        else:
            offset_x = main_offset_x * magnitude
        if main_offset_y < 0:
            offset_y = (resize_h - crop_h) / 2.0
        else:
            offset_y = main_offset_y * magnitude

        # compute the centerpoint of the scaled crop area
        center_x = (crop_w / 2.0) + offset_x
        center_y = (crop_h / 2.0) + offset_y

        return resize_w, resize_h, center_x, center_y

    MAX_SELF_FIT_ZOOM = 1000

    def compute_combined_zoom(self, quadrant, quadrants, zoom_percent, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h, log_fn):
        resize_w, resize_h, _, _ = self.compute_percent_zoom(zoom_percent,
                                                            main_resize_w, main_resize_h,
                                                            main_offset_x, main_offset_y,
                                                            main_crop_w, main_crop_h, log_fn)
        quadrant_resize_w, _, quadrant_center_x, quadrant_center_y = self.compute_quadrant_zoom(quadrant, quadrants,
                                                            main_resize_w, main_resize_h,
                                                            main_offset_x, main_offset_y,
                                                            main_crop_w, main_crop_h, log_fn)

        # scale the quadrant center point to the percent resize
        scale = resize_w / quadrant_resize_w
        center_x = quadrant_center_x * scale
        center_y = quadrant_center_y * scale

        if self.check_crop_bounds(resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
            # fit the requested zoom percent to be in bounds
            fit_zoom_percent = zoom_percent
            while fit_zoom_percent < self.MAX_SELF_FIT_ZOOM and \
            self.check_crop_bounds(resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
                fit_zoom_percent += 1
                resize_w, resize_h, _, _ = self.compute_percent_zoom(fit_zoom_percent,
                                                                    main_resize_w, main_resize_h,
                                                                    main_offset_x, main_offset_y,
                                                                    main_crop_w, main_crop_h, log_fn)
                quadrant_resize_w, _, quadrant_center_x, quadrant_center_y = self.compute_quadrant_zoom(quadrant, quadrants,
                                                                    main_resize_w, main_resize_h,
                                                                    main_offset_x, main_offset_y,
                                                                    main_crop_w, main_crop_h, log_fn)

                # scale the quadrant center point to the percent resize
                # this seems to work on the left and middle but not on the right
                scale = resize_w / quadrant_resize_w
                center_x = quadrant_center_x * scale
                center_y = quadrant_center_y * scale

            # if still out of bounds, restore to quadrant zoom
            if self.check_crop_bounds(resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
                log_fn("Can't find fitting zoom percentage; ignoring percent part.")
                resize_w, resize_h, center_x, center_y = \
                    self.compute_quadrant_zoom(quadrant, quadrants, main_resize_w, main_resize_h,
                                    main_offset_x, main_offset_y, main_crop_w, main_crop_h, log_fn)
            else:
                log_fn(f"Found fitting zoom percentage: {fit_zoom_percent}%.")

        return resize_w, resize_h, center_x, center_y

    def check_crop_bounds(self, resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
        crop_offset_x = center_x - (main_crop_w / 2.0)
        crop_offset_y = center_y - (main_crop_h / 2.0)
        return crop_offset_x < 0 or crop_offset_x + main_crop_w > resize_w \
            or crop_offset_y < 0 or crop_offset_y + main_crop_h > resize_h

    def compute_animated_zoom(self, num_frames, from_type, from_param1, from_param2, from_param3,
                                    to_type, to_param1, to_param2, to_param3,
                                    main_resize_w, main_resize_h, main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h, log_fn):

        from_resize_w, from_resize_h, from_center_x, from_center_y = \
            self.compute_zoom_type(from_type, from_param1, from_param2, from_param3,
                                    main_resize_w, main_resize_h,
                                    main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h, log_fn=log_fn)

        to_resize_w, to_resize_h, to_center_x, to_center_y = \
            self.compute_zoom_type(to_type, to_param1, to_param2, to_param3,
                                    main_resize_w, main_resize_h,
                                    main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h, log_fn=log_fn)

        diff_resize_w = to_resize_w - from_resize_w
        diff_resize_h = to_resize_h - from_resize_h
        diff_center_x = to_center_x - from_center_x
        diff_center_y = to_center_y - from_center_y

        # TODO why is this needed? without it, the last transition doesn't happen
        # - maybe it needs to be the number of transitions between frames not number of frames
        # ensure the final transition occurs
        num_frames -= 1

        step_resize_w = diff_resize_w / num_frames
        step_resize_h = diff_resize_h / num_frames
        step_center_x = diff_center_x / num_frames
        step_center_y = diff_center_y / num_frames

        context = {}
        context["from_resize_w"] = from_resize_w
        context["from_resize_h"] = from_resize_h
        context["from_center_x"] = from_center_x
        context["from_center_y"] = from_center_y
        context["step_resize_w"] = step_resize_w
        context["step_resize_h"] = step_resize_h
        context["step_center_x"] = step_center_x
        context["step_center_y"] = step_center_y
        context["main_crop_w"] = main_crop_w
        context["main_crop_h"] = main_crop_h
        return context

    def _resize_frame_param(self, index, context):
        from_resize_w = context["from_resize_w"]
        from_resize_h = context["from_resize_h"]
        from_center_x = context["from_center_x"]
        from_center_y = context["from_center_y"]
        step_resize_w = context["step_resize_w"]
        step_resize_h = context["step_resize_h"]
        step_center_x = context["step_center_x"]
        step_center_y = context["step_center_y"]
        main_crop_w = context["main_crop_w"]
        main_crop_h = context["main_crop_h"]

        resize_w = from_resize_w + (index * step_resize_w)
        resize_h = from_resize_h + (index * step_resize_h)
        center_x = from_center_x + (index * step_center_x)
        center_y = from_center_y + (index * step_center_y)
        crop_offset_x = center_x - (main_crop_w / 2.0)
        crop_offset_y = center_y - (main_crop_h / 2.0)

        return int(resize_w), int(resize_h), int(crop_offset_x), int(crop_offset_y)

    def resize_scenes(self, log_fn, kept_scenes, remixer_settings):
        scenes_base_path = self.scenes_source_path(self.RESIZE_STEP)
        create_directory(self.resize_path)

        content_width = self.video_details["content_width"]
        content_height = self.video_details["content_height"]
        scale_type, crop_type= self.get_resize_params(self.resize_w, self.resize_h, self.crop_w,
                                                      self.crop_h, content_width, content_height,
                                                      remixer_settings)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.resize_path, scene_name)
                create_directory(scene_output_path)

                resize_handled = False
                resize_hint = self.get_hint(self.scene_labels.get(scene_name), self.state.RESIZE_HINT)
                if resize_hint:
                    main_resize_w, main_resize_h, main_crop_w, main_crop_h, main_offset_x, \
                        main_offset_y = self.setup_resize_hint(content_width, content_height)

                    try:
                        if self.ANIMATED_ZOOM_HINT in resize_hint:
                            # interprent 'any-any' as animating from one to the other zoom factor
                            from_type, from_param1, from_param2, from_param3, to_type, to_param1, to_param2, to_param3 = \
                                self.get_animated_zoom(resize_hint)
                            if from_type and to_type:
                                first_frame, last_frame, _ = details_from_group_name(scene_name)
                                num_frames = (last_frame - first_frame) + 1
                                context = self.compute_animated_zoom(num_frames,
                                        from_type, from_param1, from_param2, from_param3,
                                        to_type, to_param1, to_param2, to_param3,
                                        main_resize_w, main_resize_h, main_offset_x, main_offset_y,
                                        main_crop_w, main_crop_h, log_fn)

                                scale_type = remixer_settings["scale_type_up"]
                                self.resize_scene(log_fn,
                                                scene_input_path,
                                                scene_output_path,
                                                None,
                                                None,
                                                main_crop_w,
                                                main_crop_h,
                                                None,
                                                None,
                                                scale_type,
                                                crop_type="crop",
                                                params_fn=self._resize_frame_param,
                                                params_context=context)
                                resize_handled = True

                        elif self.COMBINED_ZOOM_HINT in resize_hint:
                            quadrant, quadrants, zoom_percent = self.get_combined_zoom(resize_hint)
                            if quadrant and quadrants and zoom_percent:
                                resize_w, resize_h, center_x, center_y = \
                                    self.compute_combined_zoom(quadrant, quadrants, zoom_percent,
                                                               main_resize_w, main_resize_h,
                                                               main_offset_x, main_offset_y,
                                                               main_crop_w, main_crop_h, log_fn)

                                crop_offset_x = center_x - (main_crop_w / 2.0)
                                crop_offset_y = center_y - (main_crop_h / 2.0)

                                scale_type = remixer_settings["scale_type_up"]
                                self.resize_scene(log_fn,
                                                scene_input_path,
                                                scene_output_path,
                                                int(resize_w),
                                                int(resize_h),
                                                int(main_crop_w),
                                                int(main_crop_h),
                                                int(crop_offset_x),
                                                int(crop_offset_y),
                                                scale_type,
                                                crop_type="crop")
                                resize_handled = True

                        elif self.QUADRANT_ZOOM_HINT in resize_hint:
                            # interpret 'x/y' as x: quadrant, y: square-based number of quadrants
                            # '5/9' and '13/25' would be the center squares of 3x3 and 5x5 grids
                            #   zoomed in at 300% and 500%
                            quadrant, quadrants = self.get_quadrant_zoom(resize_hint)
                            if quadrant and quadrants:
                                resize_w, resize_h, center_x, center_y = \
                                    self.compute_quadrant_zoom(quadrant, quadrants,
                                                               main_resize_w, main_resize_h,
                                                               main_offset_x, main_offset_y,
                                                               main_crop_w, main_crop_h, log_fn)

                                scale_type = remixer_settings["scale_type_up"]
                                crop_offset_x = center_x - (main_crop_w / 2.0)
                                crop_offset_y = center_y - (main_crop_h / 2.0)
                                self.resize_scene(log_fn,
                                                scene_input_path,
                                                scene_output_path,
                                                int(resize_w),
                                                int(resize_h),
                                                int(main_crop_w),
                                                int(main_crop_h),
                                                int(crop_offset_x),
                                                int(crop_offset_y),
                                                scale_type,
                                                crop_type="crop")
                                resize_handled = True

                        elif self.PERCENT_ZOOM_HINT in resize_hint:
                                # interpret z% as zoom percent to zoom into center
                                zoom_percent = self.get_percent_zoom(resize_hint)
                                if zoom_percent:
                                    resize_w, resize_h, center_x, center_y = \
                                        self.compute_percent_zoom(zoom_percent,
                                                                    main_resize_w, main_resize_h,
                                                                    main_offset_x, main_offset_y,
                                                                    main_crop_w, main_crop_h, log_fn)
                                    scale_type = remixer_settings["scale_type_up"]
                                    crop_offset_x = center_x - (main_crop_w / 2.0)
                                    crop_offset_y = center_y - (main_crop_h / 2.0)
                                    self.resize_scene(log_fn,
                                                    scene_input_path,
                                                    scene_output_path,
                                                    int(resize_w),
                                                    int(resize_h),
                                                    int(main_crop_w),
                                                    int(main_crop_h),
                                                    int(crop_offset_x),
                                                    int(crop_offset_y),
                                                    scale_type,
                                                    crop_type="crop")
                                    resize_handled = True
                    except Exception as error:
                        # TODO
                        print(error)
                        raise
                        log_fn(
f"Error in resize_scenes() handling processing hint {resize_hint} - skipping processing: {error}")
                        resize_handled = False

                if not resize_handled:
                    self.resize_scene(log_fn,
                                    scene_input_path,
                                    scene_output_path,
                                    int(self.resize_w),
                                    int(self.resize_h),
                                    int(self.crop_w),
                                    int(self.crop_h),
                                    int(self.crop_offset_x),
                                    int(self.crop_offset_y),
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

                resynth_type = resynth_option if self.resynthesize else None
                resynth_hint = self.get_hint(self.scene_labels.get(scene_name), self.state.RESYNTHESIS_HINT)
                if resynth_hint:
                    if "C" in resynth_hint:
                        resynth_type = "Clean"
                    elif "S" in resynth_hint:
                        resynth_type = "Scrub"
                    elif "R" in resynth_hint:
                        resynth_type = "Replace"
                    elif "N" in resynth_hint:
                        resynth_type = None

                if resynth_type == "Replace":
                    self.one_pass_resynthesis(log_fn, scene_input_path, scene_output_path,
                                              output_basename, series_interpolater)
                elif resynth_type == "Clean" or resynth_type == "Scrub":
                    one_pass_only = resynth_type == "Clean"
                    self.two_pass_resynthesis(log_fn, scene_input_path, scene_output_path,
                                              output_basename, series_interpolater,
                                              one_pass_only=one_pass_only)
                else:
                    # no need to resynthesize so just copy the files using the resequencer
                    ResequenceFiles(scene_input_path,
                                    self.frame_format,
                                    "resynthesized_frame",
                                    1, 1,
                                    1, 0,
                                    -1,
                                    False,
                                    log_fn,
                                    output_path=scene_output_path).resequence()

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

                project_splits = 0
                if self.inflate:
                    if self.inflate_by_option == "1X":
                        project_splits = 0
                    if self.inflate_by_option == "2X":
                        project_splits = 1
                    elif self.inflate_by_option == "4X":
                        project_splits = 2
                    elif self.inflate_by_option == "8X":
                        project_splits = 3
                    elif self.inflate_by_option == "16X":
                        project_splits = 4

                # if it's for slow motion, the split should be relative to the
                # project inflation rate

                hinted_splits = 0
                force_inflation, force_audio, force_inflate_by, force_silent =\
                    self.compute_forced_inflation(scene_name)
                if force_inflation:
                    if force_inflate_by == "1X":
                        disable_inflation = True
                    elif force_inflate_by == "2X":
                        hinted_splits = 1
                    elif force_inflate_by == "4X":
                        hinted_splits = 2
                    elif force_inflate_by == "8X":
                        hinted_splits = 3
                    elif force_inflate_by == "16X":
                        hinted_splits = 4

                if hinted_splits:
                    if force_audio or force_silent:
                        # the figures for audio slow motion are relative to the project split rate
                        # splits are really exponents of 2^n
                        num_splits = project_splits + hinted_splits
                    else:
                        # if not for slow motion, force an exact split
                        num_splits = hinted_splits
                else:
                    num_splits = 0 if disable_inflation else project_splits

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

        # TODO make this logic general

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
            ResizeFrames(scene_input_path,
                        scene_output_path,
                        downscaled_width,
                        downscaled_height,
                        downscale_type,
                        log_fn).resize(type=self.frame_format)
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
                create_directory(scene_output_path)

                upscale_handled = False
                upscale_hint = self.get_hint(self.scene_labels.get(scene_name), self.state.UPSCALE_HINT)

                if upscale_hint and not self.upscale:
                    # only apply the hint if not already upscaling, otherwise the
                    # frames may have mismatched sizes
                    try:
                        # for now ignore the hint value and upscale just at 1X, to clean up zooming
                        self.upscale_scene(log_fn,
                                        upscaler,
                                        scene_input_path,
                                        scene_output_path,
                                        1.0,
                                        downscale_type=downscale_type)
                        upscale_handled = True

                    except Exception as error:
                        log_fn(
f"Error in upscale_scenes() handling processing hint {upscale_hint} - skipping processing: {error}")
                        upscale_handled = False

                if not upscale_handled:
                    if self.upscale:
                        self.upscale_scene(log_fn,
                                        upscaler,
                                        scene_input_path,
                                        scene_output_path,
                                        upscale_factor,
                                        downscale_type=downscale_type)
                    else:
                        # no need to upscale so just copy the files using the resequencer
                        ResequenceFiles(scene_input_path,
                                        self.frame_format,
                                        "upscaled_frames",
                                        1, 1,
                                        1, 0,
                                        -1,
                                        False,
                                        log_fn,
                                        output_path=scene_output_path).resequence()
                Mtqdm().update_bar(bar)

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
                label += "-in" + self.inflate_by_option[0]
                if self.inflate_slow_option == "Audio":
                    label += "SA"
                elif self.inflate_slow_option == "Silent":
                    label += "SM"
            else:
                label += "-inH"

        if self.upscale_chosen():
            if self.upscale:
                label += "-up" + self.upscale_option[0]
            else:
                label += "-upH"

        label += "-" + extra_suffix if extra_suffix else ""
        return label

    def default_remix_filepath(self, extra_suffix=""):
        _, filename, _ = split_filepath(self.source_video)
        suffix = self.remix_filename_suffix(extra_suffix)
        return os.path.join(self.project_path, f"{filename}-{suffix}.mp4")

    # get path to the furthest processed content
    def furthest_processed_path(self):
        if self.upscale_chosen():
            path = self.upscale_path
        elif self.inflate_chosen():
            path = self.inflation_path
        elif self.resynthesize_chosen():
            path = self.resynthesis_path
        elif self.resize_chosen():
            path = self.resize_path
        else:
            path = self.scenes_path
        return path
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
        scenes_base_path = self.furthest_processed_path()
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
            self.video_clips_path,
            self.audio_clips_path,
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
        _, audio_slow_motion, silent_slow_motion, project_inflation_rate, forced_inflated_rate = \
            self.compute_effective_slow_motion(force_inflation, force_audio, force_inflate_by,
                                               force_silent)
        if audio_slow_motion or silent_slow_motion:
            fps_factor = project_inflation_rate
        else:
            if force_inflation:
                fps_factor = forced_inflated_rate
            else:
                fps_factor = project_inflation_rate
        return self.project_fps * fps_factor

    def compute_forced_inflation(self, scene_name):
        force_inflation = False
        force_audio = False
        force_inflate_by = None
        force_silent = False

        inflation_hint = self.get_hint(self.scene_labels.get(scene_name), self.state.INFLATION_HINT)
        if inflation_hint:
            if "16" in inflation_hint:
                force_inflation = True
                force_inflate_by = "16X"
            elif "1" in inflation_hint:
                force_inflation = True
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
            # else "N" for no slow motion
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

        scenes_base_path = self.furthest_processed_path()
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
        return int(inflate_by[:-1])

    def compute_effective_slow_motion(self, force_inflation, force_audio, force_inflate_by,
                                      force_silent):

        audio_slow_motion = force_audio or (self.inflate and self.inflate_slow_option == "Audio")
        silent_slow_motion = force_silent or (self.inflate and self.inflate_slow_option == "Silent")

        project_inflation_rate = self.inflation_rate(self.inflate_by_option) if self.inflate else 1
        forced_inflation_rate = self.inflation_rate(force_inflate_by) if force_inflation else 1

        # For slow motion hints, interpret the 'force_inflate_by' as relative to the project rate
        # If the forced inflation rate is 1 it means no inflation, not even at the projecr fate
        if audio_slow_motion or silent_slow_motion:
            if forced_inflation_rate != 1:
                forced_inflation_rate *= project_inflation_rate

        motion_factor = forced_inflation_rate / project_inflation_rate
        return motion_factor, audio_slow_motion, silent_slow_motion, project_inflation_rate, \
            forced_inflation_rate

    def compute_inflated_audio_options(self, custom_audio_options, force_inflation, force_audio,
                                       force_inflate_by, force_silent):

        motion_factor, audio_slow_motion, silent_slow_motion, _, _ = \
            self.compute_effective_slow_motion(force_inflation, force_audio, force_inflate_by,
                                               force_silent)

        audio_motion_factor = motion_factor

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
            else:
                raise ValueError(f"audio_motion_factor {audio_motion_factor} is not supported")
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

        scenes_base_path = self.furthest_processed_path()
        if custom_video_options.find("<LABEL>") != -1:
            if not draw_text_options:
                raise RuntimeError("'draw_text_options' is None at create_custom_video_clips()")
            try:
                font_factor = draw_text_options["font_size"]
                font_color = draw_text_options["font_color"]
                font_file = draw_text_options["font_file"]
                draw_shadow = draw_text_options["draw_shadow"]
                shadow_color = draw_text_options["shadow_color"]
                shadow_factor = draw_text_options["shadow_size"]
                draw_box = draw_text_options["draw_box"]
                box_color = draw_text_options["box_color"]
                border_factor = draw_text_options["border_size"]
                label_position_v = draw_text_options["label_position_v"]
                label_position_h = draw_text_options["label_position_h"]
                crop_width = draw_text_options["crop_width"]
                labels = draw_text_options["labels"]

            except IndexError as error:
                raise RuntimeError(f"error retrieving 'draw_text_options': {error}")

            font_size = crop_width / float(font_factor)
            border_size = font_size / float(border_factor)
            shadow_offset = font_size / float(shadow_factor)

            shadow_x = f"((w-text_w)/2)+{shadow_offset}"

            # using text height as a left/right margin
            if label_position_h == "Left":
                box_x = "(text_h-bottom_d)"
            elif label_position_h == "Center":
                box_x = "(w-text_w)/2"
            else:
                box_x = "(w-text_w)-(text_h-bottom_d)"
            shadow_x = f"{box_x}+{shadow_offset}"

            if label_position_v == "Bottom":
                box_y = f"h-((text_h-bottom_d)*2)-({2*int(border_size)})"
            elif label_position_v == "Middle":
                box_y = f"(h/2)-((text_h-bottom_d)/2)-({int(border_size)})"
            else:
                box_y = "((text_h-bottom_d)*1)"
            shadow_y = f"{box_y}+{shadow_offset}"

            # FFmpeg requires forward slashes in font file path
            font_file = font_file.replace(r"\\", "/").replace("\\", "/")

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

                        # FFmpeg needs some things escaped
                        label = label.\
                            replace(":", "\:").\
                            replace(",", "\,").\
                            replace("{", "\{").\
                            replace("}", "\}").\
                            replace("%", "\%")

                        box_part = f":box=1:boxcolor={box_color}:boxborderw={border_size}" if draw_box else ""
                        label_part = f"text='{label}':x={box_x}:y={box_y}:fontsize={font_size}:fontcolor={font_color}:fontfile='{font_file}':expansion=none{box_part}"
                        shadow_part = f"text='{label}':x={shadow_x}:y={shadow_y}:fontsize={font_size}:fontcolor={shadow_color}:fontfile='{font_file}'" if draw_shadow else ""
                        draw_text = f"{shadow_part},drawtext={label_part}" if draw_shadow else label_part
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
