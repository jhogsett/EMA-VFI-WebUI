"""Video Remixer Content Processing"""
import os
import math
import shutil
from typing import Callable, TYPE_CHECKING
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    remove_directories, copy_files, simple_sanitize_filename
from webui_utils.video_utils import details_from_group_name, PNGtoMP4, combine_video_audio,\
    combine_videos, PNGtoCustom, image_size
from webui_utils.mtqdm import Mtqdm
from slice_video import SliceVideo
from resize_frames import ResizeFrames
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from upscale_series import UpscaleSeries

if TYPE_CHECKING:
    from video_remixer import VideoRemixerState

class VideoRemixerProcessor():
    def __init__(self, state : "VideoRemixerState", engine : any, engine_settings : dict,
                 realesrgan_settings : dict, global_options : dict, log_fn : Callable):
        self.state = state
        self.engine = engine
        self.engine_settings = engine_settings
        self.realesrgan_settings = realesrgan_settings
        self.global_options = global_options
        self.log_fn = log_fn
        self.saved_view = self.DEFAULT_VIEW

    def log(self, message):
        if self.log_fn:
            self.log_fn(message)

    QUADRANT_ZOOM_HINT = "/"
    QUADRANT_GRID_CHAR = "X"
    PERCENT_ZOOM_HINT = "%"
    COMBINED_ZOOM_HINT = "@"
    ANIMATED_ZOOM_HINT = "-"
    ANIMATION_TIME_HINT = "#"
    ANIMATION_SCHEDULE_HINT = "$"
    QUADRATRIC_SCHEDULE = "Q"
    BEZIER_SCHEDULE = "B"
    PARAMETRIC_SCHEDULE = "P"
    LINEAR_SCHEDULE = "L"
    LENS_SCHEDULE = "Z"
    QUADRANT_ZOOM_MIN_LEN = 3 # 1/3
    PERCENT_ZOOM_MIN_LEN = 4  # 123%
    COMBINED_ZOOM_MIN_LEN = 8 # 1/1@100%
    ANIMATED_ZOOM_MIN_LEN = 1 # -
    MAX_SELF_FIT_ZOOM = 1000
    FIXED_UPSCALE_FACTOR = 4.0
    TEMP_UPSCALE_PATH = "upscaled_frames"
    DEFAULT_DOWNSCALE_TYPE = "area"
    DEFAULT_VIEW = "100%"
    DEFAULT_ANIMATION_SCHEDULE = "L" # linear
    DEFAULT_ANIMATION_TIME = 0 # whole scene

    ### Exports --------------------

    def prepare_process_remix(self, redo_resynth, redo_inflate, redo_upscale):
        self.state.setup_processing_paths()

        self.state.recompile_scenes()

        if self.state.processed_content_invalid:
            self.state.purge_processed_content(purge_from=self.state.RESIZE_STEP)
            self.state.processed_content_invalid = False
        else:
            self.purge_stale_processed_content(redo_resynth, redo_inflate, redo_upscale)
            self.purge_incomplete_processed_content()
        self.state.save()

    def process_remix(self, kept_scenes):
        if self.resize_needed():
            self.resize_scenes(kept_scenes)

        if self.resynthesize_needed():
            self.resynthesize_scenes(kept_scenes)

        if self.inflate_needed():
            self.inflate_scenes(kept_scenes)

        if self.upscale_needed():
            self.upscale_scenes(kept_scenes)

    def processed_content_complete(self, processing_step):
        expected_items = len(self.state.kept_scenes())
        if processing_step == self.state.RESIZE_STEP:
            return self._processed_content_complete(self.state.resize_path, expected_dirs=expected_items)
        elif processing_step == self.state.RESYNTH_STEP:
            return self._processed_content_complete(self.state.resynthesis_path, expected_dirs=expected_items)
        elif processing_step == self.state.INFLATE_STEP:
            return self._processed_content_complete(self.state.inflation_path, expected_dirs=expected_items)
        elif processing_step == self.state.UPSCALE_STEP:
            return self._processed_content_complete(self.state.upscale_path, expected_dirs=expected_items)
        elif processing_step == self.state.AUDIO_STEP:
            return self._processed_content_complete(self.state.audio_clips_path, expected_files=expected_items)
        elif processing_step == self.state.VIDEO_STEP:
            return self._processed_content_complete(self.state.video_clips_path, expected_files=expected_items)
        else:
            raise RuntimeError(f"'processing_step' {processing_step} is unrecognized")

    def _processed_content_complete(self, path, expected_dirs = 0, expected_files = 0):
        if not path or not os.path.exists(path):
            return False
        if expected_dirs:
            return len(get_directories(path)) == expected_dirs
        if expected_files:
            return len(get_files(path)) == expected_files
        return True

    def prepare_save_remix(self, output_filepath : str, invalidate_video_clips=True):
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
                self.state.AUDIO_STEP):
            self.create_audio_clips()
            self.state.save()

        # leave video clips if they are complete since we may be only making audio changes
        if invalidate_video_clips or not self.processed_content_complete(self.state.VIDEO_STEP):
            self.state.clean_remix_content(purge_from="video_clips")
        else:
            # always recreate remix clips
            self.state.clean_remix_content(purge_from="remix_clips")

        return kept_scenes

    def save_remix(self, kept_scenes):
        # leave video clips if they are complete since we may be only making audio changes
        if not self.processed_content_complete(self.state.VIDEO_STEP):
            self.create_video_clips(kept_scenes)
            self.state.save()

        self.create_scene_clips(kept_scenes)
        self.state.save()

        if not self.state.clips:
            raise ValueError("No processed video clips were found")

        ffcmd = self.create_remix_video(self.state.output_filepath)
        self.log(f"FFmpeg command: {ffcmd}")
        self.state.save()

    def save_custom_remix(self,
                          output_filepath,
                          kept_scenes,
                          custom_video_options,
                          custom_audio_options,
                          draw_text_options=None,
                          use_scene_sorting=True):
        _, _, output_ext = split_filepath(output_filepath)
        output_ext = output_ext[1:]

        # leave video clips if they are complete since we may be only making audio changes
        if not self.processed_content_complete(self.state.VIDEO_STEP):
            self.create_custom_video_clips(kept_scenes, custom_video_options=custom_video_options,
                                                custom_ext=output_ext,
                                                draw_text_options=draw_text_options)
            self.state.save()

        self.create_custom_scene_clips(kept_scenes, custom_audio_options=custom_audio_options,
                                             custom_ext=output_ext)
        self.state.save()

        if not self.state.clips:
            raise ValueError("No processed video clips were found")

        ffcmd = self.create_remix_video(output_filepath,
                                        use_scene_sorting=use_scene_sorting)
        self.log(f"FFmpeg command: {ffcmd}")
        self.state.save()

    def sort_marked_scenes(self) -> dict:
        """Returns dict mapping scene sort mark to scene name."""
        result = {}
        for scene_name in self.state.scene_names:
            scene_label = self.state.scene_labels.get(scene_name)
            sort, _, _ = self.state.split_label(scene_label)
            if sort:
                result[sort] = scene_name
        return result


    ### Internal --------------------

    # Preprocessing

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
        if self.processed_content_stale(self.state.resize_chosen(), self.state.resize_path):
            self.state.purge_processed_content(purge_from=self.state.RESIZE_STEP)

        if self.processed_content_stale(self.state.resynthesize_chosen(), self.state.resynthesis_path) or purge_resynth:
            self.state.purge_processed_content(purge_from=self.state.RESYNTH_STEP)

        if self.processed_content_stale(self.state.inflate_chosen(), self.state.inflation_path) or purge_inflation:
            self.state.purge_processed_content(purge_from=self.state.INFLATE_STEP)

        if self.processed_content_stale(self.state.upscale_chosen(), self.state.upscale_path) or purge_upscale:
            self.state.purge_processed_content(purge_from=self.state.UPSCALE_STEP)

    def purge_incomplete_processed_content(self):
        # content is incomplete if the wrong number of scene directories are present
        # if it is currently selected and incomplete, it should be purged
        if self.state.resize_chosen() and not self.processed_content_complete(self.state.RESIZE_STEP):
            self.state.purge_processed_content(purge_from=self.state.RESIZE_STEP)

        if self.state.resynthesize_chosen() and not self.processed_content_complete(self.state.RESYNTH_STEP):
            self.state.purge_processed_content(purge_from=self.state.RESYNTH_STEP)

        if self.state.inflate_chosen() and not self.processed_content_complete(self.state.INFLATE_STEP):
            self.state.purge_processed_content(purge_from=self.state.INFLATE_STEP)

        if self.state.upscale_chosen() and not self.processed_content_complete(self.state.UPSCALE_STEP):
            self.state.purge_processed_content(purge_from=self.state.UPSCALE_STEP)


    # General Processing

    def resize_needed(self):
        return self.state.resize_chosen() \
            and not self.processed_content_complete(self.state.RESIZE_STEP)

    def resynthesize_needed(self):
        return self.state.resynthesize_chosen() \
            and not self.processed_content_complete(self.state.RESYNTH_STEP)

    def inflate_needed(self):
        return self.state.inflate_chosen() \
            and not self.processed_content_complete(self.state.INFLATE_STEP)

    def upscale_needed(self):
        return self.state.upscale_chosen() \
            and not self.processed_content_complete(self.state.UPSCALE_STEP)

    def scenes_source_path(self, processing_step):
        processing_path = self.state.scenes_path

        if processing_step == self.state.RESIZE_STEP:
            # resize is the first processing step and always draws from the scenes path
            pass

        elif processing_step == self.state.RESYNTH_STEP:
            # resynthesis is the second processing step
            if self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.state.resize_path

        elif processing_step == self.state.INFLATE_STEP:
            # inflation is the third processing step
            if self.state.resynthesize_chosen():
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.state.resynthesis_path
            elif self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.state.resize_path

        elif processing_step == self.state.UPSCALE_STEP:
            # upscaling is the fourth processing step
            if self.state.inflate_chosen():
                # if inflation is enabled, draw from the inflation path
                processing_path = self.state.inflation_path
            elif self.state.resynthesize_chosen():
                # if resynthesis is enabled, draw from the resyntheized scenes path
                processing_path = self.state.resynthesis_path
            elif self.state.resize_chosen():
                # if resize is enabled, draw from the resized scenes path
                processing_path = self.state.resize_path

        return processing_path

    # get path to the furthest processed content
    def furthest_processed_path(self):
        if self.state.upscale_chosen():
            path = self.state.upscale_path
        elif self.state.inflate_chosen():
            path = self.state.inflation_path
        elif self.state.resynthesize_chosen():
            path = self.state.resynthesis_path
        elif self.state.resize_chosen():
            path = self.state.resize_path
        else:
            path = self.state.scenes_path
        return path


    # Resize Processing

    def resize_scene(self,
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
                    self.log_fn,
                    crop_type=crop_type,
                    crop_width=crop_w,
                    crop_height=crop_h,
                    crop_offset_x=crop_offset_x,
                    crop_offset_y=crop_offset_y).resize(type=self.state.frame_format,
                                                        params_fn=params_fn,
                                                        params_context=params_context)

    def resize_scenes(self, kept_scenes):
        scenes_base_path = self.scenes_source_path(self.state.RESIZE_STEP)
        create_directory(self.state.resize_path)

        content_width = self.state.video_details["content_width"]
        content_height = self.state.video_details["content_height"]
        scale_type, crop_type= self.get_resize_params(self.state.resize_w, self.state.resize_h,
                                                      self.state.crop_w, self.state.crop_h,
                                                      content_width, content_height)

        self.saved_view = self.DEFAULT_VIEW
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.state.resize_path, scene_name)
                create_directory(scene_output_path)

                resize_handled = False
                resize_hint = self.state.get_hint(self.state.scene_labels.get(scene_name),
                                                  self.state.RESIZE_HINT)

                # if there's no resize hint, and the saved view differs from the default,
                # presume the saved view is what's wanted for an unhinted scene
                if not resize_hint and self.saved_view != self.DEFAULT_VIEW:
                    resize_hint = self.saved_view

                if resize_hint:
                    main_resize_w, main_resize_h, main_crop_w, main_crop_h, main_offset_x, \
                        main_offset_y = self.setup_resize_hint(content_width, content_height)

                    try:
                        if self.ANIMATED_ZOOM_HINT in resize_hint:
                            # interprent 'any-any' as animating from one to the other zoom factor
                            resize_hint = self.get_implied_zoom(resize_hint)
                            self.log(f"get_implied_zoom()) filtered resize hint: {resize_hint}")
                            from_type, from_param1, from_param2, from_param3, to_type, to_param1, \
                                to_param2, to_param3, time, schedule \
                                    = self.get_animated_zoom(resize_hint)
                            if from_type and to_type:
                                first_frame, last_frame, _ = details_from_group_name(scene_name)
                                num_frames = (last_frame - first_frame) + 1
                                context = self.compute_animated_zoom(num_frames,
                                        from_type, from_param1, from_param2, from_param3,
                                        to_type, to_param1, to_param2, to_param3, time, schedule,
                                        main_resize_w, main_resize_h, main_offset_x, main_offset_y,
                                        main_crop_w, main_crop_h)

                                scale_type = self.state.remixer_settings["scale_type_up"]
                                self.resize_scene(scene_input_path,
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
                                                               main_crop_w, main_crop_h)

                                crop_offset_x = center_x - (main_crop_w / 2.0)
                                crop_offset_y = center_y - (main_crop_h / 2.0)

                                scale_type = self.state.remixer_settings["scale_type_up"]
                                self.resize_scene(scene_input_path,
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
                                                               main_crop_w, main_crop_h)

                                scale_type = self.state.remixer_settings["scale_type_up"]
                                crop_offset_x = center_x - (main_crop_w / 2.0)
                                crop_offset_y = center_y - (main_crop_h / 2.0)
                                self.resize_scene(scene_input_path,
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
                                                                  main_crop_w, main_crop_h)
                                    scale_type = self.state.remixer_settings["scale_type_up"]
                                    crop_offset_x = center_x - (main_crop_w / 2.0)
                                    crop_offset_y = center_y - (main_crop_h / 2.0)
                                    self.resize_scene(scene_input_path,
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
                        # TODO capture and report processing issues
                        # print(error)
                        self.log(
f"Error in resize_scenes() handling processing hint {resize_hint} - skipping processing: {error}")
                        resize_handled = False
                        raise

                if not resize_handled:
                    self.resize_scene(scene_input_path,
                                      scene_output_path,
                                      int(self.state.resize_w),
                                      int(self.state.resize_h),
                                      int(self.state.crop_w),
                                      int(self.state.crop_h),
                                      int(self.state.crop_offset_x),
                                      int(self.state.crop_offset_y),
                                      scale_type,
                                      crop_type)

                Mtqdm().update_bar(bar)

    def get_resize_params(self, resize_w, resize_h, crop_w, crop_h, content_width, content_height):
        if resize_w == content_width and resize_h == content_height:
            scale_type = "none"
        else:
            if resize_w <= content_width and resize_h <= content_height:
                # use the down scaling type if there are only reductions
                # the default "area" type preserves details better on reducing
                scale_type = self.state.remixer_settings["scale_type_down"]
            else:
                # otherwise use the upscaling type
                # the default "lanczos" type preserves details better on enlarging
                scale_type = self.state.remixer_settings["scale_type_up"]

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

    # Resize Processing Hints

    def setup_resize_hint(self, content_width, content_height):
        # use the main resize/crop settings if resizing, or the content native
        # dimensions if not, as a foundation for handling resize hints
        if self.state.resize:
            main_resize_w = self.state.resize_w
            main_resize_h = self.state.resize_h
            main_crop_w = self.state.crop_w
            main_crop_h = self.state.crop_h
            if self.state.crop_offset_x < 0:
                main_offset_x = (main_resize_w - main_crop_w) / 2.0
            else:
                main_offset_x = self.state.crop_offset_x
            if self.state.crop_offset_y < 0:
                main_offset_y = (main_resize_h - main_crop_h) / 2.0
            else:
                main_offset_y = self.state.crop_offset_y
        else:
            main_resize_w = content_width
            main_resize_h = content_height
            main_crop_w = content_width
            main_crop_h = content_height
            main_offset_x = 0
            main_offset_y = 0
        return main_resize_w, main_resize_h, main_crop_w, main_crop_h, main_offset_x, main_offset_y

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

    def get_implied_zoom(self, hint):
        if self.ANIMATED_ZOOM_HINT in hint:
            if len(hint) >= self.ANIMATED_ZOOM_MIN_LEN:
                split_pos = hint.index(self.ANIMATED_ZOOM_HINT)
                hint_from = hint[:split_pos]
                hint_to = hint[split_pos+1:]

                # if the hint_to part includes time or schedule info, remove it to get only the view
                view_to = hint_to
                remainder = ""
                if self.ANIMATION_TIME_HINT in view_to:
                    split_pos = view_to.index(self.ANIMATION_TIME_HINT)
                    remainder = view_to[split_pos:]
                    view_to = view_to[:split_pos]
                    # may include schedule part, which can come after time part
                elif self.ANIMATION_SCHEDULE_HINT in view_to:
                    split_pos = view_to.index(self.ANIMATION_SCHEDULE_HINT)
                    remainder = view_to[split_pos:]
                    view_to = view_to[:split_pos]

                if not hint_from or not view_to:
                    if not hint_from and not view_to:
                        # single dash (both missing) means return to default zoom
                        hint_from = self.saved_view
                        hint_to = self.DEFAULT_VIEW
                        view_to = self.DEFAULT_VIEW
                        self.log(f"get_implied_zoom(): using saved zoom for from: {hint_from} and default zoom for to: {hint_to}")

                    elif hint_from and not view_to:
                        # missing 'to' means go to saved zoom
                        hint_to = self.saved_view
                        self.log(f"get_implied_zoom(): using passed zoom for from: {hint_from} and saved zoom for to: {hint_to}")

                    elif not hint_from and view_to:
                        # missing 'from' means go from saved zoom
                        hint_from = self.saved_view
                        self.log(f"get_implied_zoom(): using saved zoom for from: {hint_from} and passed zoom for to: {hint_to}")

                    else:
                        self.log(f"get_implied_zoom(): using passed zoom for from: {hint_from} and passed zoom for to: {hint_to}")

                if view_to:
                    self.saved_view = view_to

                return f"{hint_from}-{view_to}{remainder}"
        return hint

    def get_animated_zoom(self, hint):
        if self.ANIMATED_ZOOM_HINT in hint:
            if len(hint) >= self.ANIMATED_ZOOM_MIN_LEN:
                schedule = self.DEFAULT_ANIMATION_SCHEDULE
                time = self.DEFAULT_ANIMATION_TIME
                if self.ANIMATION_SCHEDULE_HINT in hint:
                    split_pos = hint.index(self.ANIMATION_SCHEDULE_HINT)
                    remainder = hint[:split_pos]
                    schedule = hint[split_pos+1:]
                    hint = remainder
                if self.ANIMATION_TIME_HINT in hint:
                    split_pos = hint.index(self.ANIMATION_TIME_HINT)
                    remainder = hint[:split_pos]
                    time = int(hint[split_pos+1:])
                    hint = remainder
                split_pos = hint.index(self.ANIMATED_ZOOM_HINT)
                hint_from = hint[:split_pos]
                hint_to = hint[split_pos+1:]
                from_type, from_param1, from_param2, from_param3 = self.get_zoom_part(hint_from)
                to_type, to_param1, to_param2, to_param3 = self.get_zoom_part(hint_to)
                return from_type, from_param1, from_param2, from_param3, to_type, to_param1, to_param2, to_param3, time, schedule
        return None, None, None, None, None, None, None, None, None, None

    def compute_zoom_type(self, type, param1, param2, param3, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h):
        if type == self.COMBINED_ZOOM_HINT:
            quadrant, quadrants, zoom_percent = param1, param2, param3
            if quadrant and quadrants and zoom_percent:
                return self.compute_combined_zoom(quadrant, quadrants, zoom_percent,
                                                  main_resize_w, main_resize_h,
                                                  main_offset_x, main_offset_y,
                                                  main_crop_w, main_crop_h)
        elif type == self.QUADRANT_ZOOM_HINT:
            quadrant, quadrants = param1, param2
            if quadrant and quadrants:
                return self.compute_quadrant_zoom(quadrant, quadrants,
                                                  main_resize_w, main_resize_h,
                                                  main_offset_x, main_offset_y,
                                                  main_crop_w, main_crop_h)
        elif type == self.PERCENT_ZOOM_HINT:
            zoom_percent = param3
            if zoom_percent:
                return self.compute_percent_zoom(zoom_percent,
                                                 main_resize_w, main_resize_h,
                                                 main_offset_x, main_offset_y,
                                                 main_crop_w, main_crop_h)

    def compute_quadrant_zoom(self, quadrant, quadrants, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h):
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
                            main_offset_y, main_crop_w, main_crop_h):
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

    def compute_combined_zoom(self, quadrant, quadrants, zoom_percent, main_resize_w, main_resize_h,
            main_offset_x, main_offset_y, main_crop_w, main_crop_h):
        resize_w, resize_h, _, _ = self.compute_percent_zoom(zoom_percent,
                                                            main_resize_w, main_resize_h,
                                                            main_offset_x, main_offset_y,
                                                            main_crop_w, main_crop_h)
        quadrant_resize_w, _, quadrant_center_x, quadrant_center_y = self.compute_quadrant_zoom(quadrant, quadrants,
                                                            main_resize_w, main_resize_h,
                                                            main_offset_x, main_offset_y,
                                                            main_crop_w, main_crop_h)

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
                                                                    main_crop_w, main_crop_h)
                quadrant_resize_w, _, quadrant_center_x, quadrant_center_y = self.compute_quadrant_zoom(quadrant, quadrants,
                                                                    main_resize_w, main_resize_h,
                                                                    main_offset_x, main_offset_y,
                                                                    main_crop_w, main_crop_h)

                # scale the quadrant center point to the percent resize
                # this seems to work on the left and middle but not on the right
                scale = resize_w / quadrant_resize_w
                center_x = quadrant_center_x * scale
                center_y = quadrant_center_y * scale

            # if still out of bounds, restore to quadrant zoom
            if self.check_crop_bounds(resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
                self.log("Can't find fitting zoom percentage; ignoring percent part.")
                resize_w, resize_h, center_x, center_y = \
                    self.compute_quadrant_zoom(quadrant, quadrants,
                                               main_resize_w, main_resize_h,
                                               main_offset_x, main_offset_y,
                                               main_crop_w, main_crop_h)
            else:
                self.log(f"Found fitting zoom percentage: {fit_zoom_percent}%.")

        return resize_w, resize_h, center_x, center_y

    def check_crop_bounds(self, resize_w, resize_h, center_x, center_y, main_crop_w, main_crop_h):
        crop_offset_x = center_x - (main_crop_w / 2.0)
        crop_offset_y = center_y - (main_crop_h / 2.0)
        return crop_offset_x < 0 or crop_offset_x + main_crop_w > resize_w \
            or crop_offset_y < 0 or crop_offset_y + main_crop_h > resize_h

    def compute_animated_zoom(self, num_frames, from_type, from_param1, from_param2, from_param3,
                                    to_type, to_param1, to_param2, to_param3, time, schedule,
                                    main_resize_w, main_resize_h, main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h):

        # animation time override
        if time > 0 and time <= num_frames:
            num_frames = time

        from_resize_w, from_resize_h, from_center_x, from_center_y = \
            self.compute_zoom_type(from_type, from_param1, from_param2, from_param3,
                                    main_resize_w, main_resize_h,
                                    main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h)

        to_resize_w, to_resize_h, to_center_x, to_center_y = \
            self.compute_zoom_type(to_type, to_param1, to_param2, to_param3,
                                    main_resize_w, main_resize_h,
                                    main_offset_x, main_offset_y,
                                    main_crop_w, main_crop_h)

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
        context["num_frames"] = num_frames
        context["schedule"] = schedule
        return context

    # https://stackoverflow.com/questions/13462001/ease-in-and-ease-out-animation-formula
    def _apply_animation_schedule(self, schedule, num_frames, frame, zooming_in):
        t = float(frame) / float(num_frames)
        if schedule == self.QUADRATRIC_SCHEDULE:
            if t <= 0.5:
                f = 2.0 * t * t
            else:
                t -= 0.5
                f = 2.0 * t * (1.0 - t) + 0.5
        elif schedule == self.BEZIER_SCHEDULE:
            f = t * t * (3.0 - 2.0 * t)
        elif schedule == self.PARAMETRIC_SCHEDULE:
            f = (t * t) / (2.0 * ((t * t) - t) + 1.0)
        elif schedule == self.LENS_SCHEDULE:
            # experimental, not working properly, too dependent on number of frames
            # a 10-second zoom ends half way through (but looks really nice)
            frame_factor = 66_667
            if zooming_in:
                factor = (1 + (frame / frame_factor)) ** frame
            else:
                factor = (1 + ((num_frames - frame) / frame_factor)) ** (num_frames - frame)
            if t <= 0.5:
                f = t / factor
            else:
                f = t * factor
            f = t * factor
            f = min(1.0, f)
        else: # Linear
            f = t
        return int(f * num_frames)

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
        num_frames = context["num_frames"]
        schedule = context["schedule"]

        # TODO handle range, offset from end
        # limit animation to maximum frames
        if index > num_frames:
            index = num_frames

        zooming_in = step_resize_w > 0.0
        index = self._apply_animation_schedule(schedule, num_frames, index, zooming_in)

        resize_w = from_resize_w + (index * step_resize_w)
        resize_h = from_resize_h + (index * step_resize_h)
        center_x = from_center_x + (index * step_center_x)
        center_y = from_center_y + (index * step_center_y)
        crop_offset_x = center_x - (main_crop_w / 2.0)
        crop_offset_y = center_y - (main_crop_h / 2.0)

        return int(resize_w), int(resize_h), int(crop_offset_x), int(crop_offset_y)


    # Resynthesis Processing

    # TODO dry up this code with same in resynthesize_video_ui - maybe a specific resynth script
    def one_pass_resynthesis(self, input_path, output_path, output_basename,
                             engine : InterpolateSeries):
        file_list = sorted(get_files(input_path, extension=self.state.frame_format))
        self.log(f"beginning series of frame recreations at {output_path}")
        engine.interpolate_series(file_list, output_path, 1, "interframe", offset=2,
                                  type=self.state.frame_format)

        self.log(f"auto-resequencing recreated frames at {output_path}")
        ResequenceFiles(output_path,
                        self.state.frame_format,
                        output_basename,
                        1, 1, # start, step
                        1, 0, # stride, offset
                        -1,   # auto-zero fill
                        True, # rename
                        self.log_fn).resequence()

    def two_pass_resynth_pass(self, input_path, output_path, output_basename,
                              engine : InterpolateSeries):
        file_list = sorted(get_files(input_path, extension=self.state.frame_format))
        inflated_frames = os.path.join(output_path, "inflated_frames")
        self.log(f"beginning series of interframe recreations at {inflated_frames}")
        create_directory(inflated_frames)
        engine.interpolate_series(file_list, inflated_frames, 1, "interframe",
                                  type=self.state.frame_format)

        self.log(f"selecting odd interframes only at {inflated_frames}")
        ResequenceFiles(inflated_frames,
                        self.state.frame_format,
                        output_basename,
                        1, 1,  # start, step
                        2, 1,  # stride, offset
                        -1,    # auto-zero fill
                        False, # rename
                        self.log_fn,
                        output_path=output_path).resequence()
        remove_directories([inflated_frames])

    def two_pass_resynthesis(self, input_path, output_path, output_basename, engine,
                             one_pass_only=False):
        if one_pass_only:
            passes = 1
            desc = "Two-Pass Resynthesis (1 Pass)"
        else:
            passes = 2
            desc = "Two-Pass Resynthesis"
        passes = 1 if one_pass_only else 2
        with Mtqdm().open_bar(total=passes, desc=desc) as bar:
            if not one_pass_only:
                interframes = os.path.join(output_path, "interframes")
                create_directory(interframes)
                self.two_pass_resynth_pass(input_path, interframes, "odd_interframe", engine)
                input_path = interframes
            self.two_pass_resynth_pass(input_path, output_path, output_basename, engine)

            if not one_pass_only:
                remove_directories([interframes])

    def resynthesize_scenes(self, kept_scenes):
        interpolater = Interpolate(self.engine.model, self.log_fn)
        use_time_step = self.engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, self.log_fn)
        output_basename = "resynthesized_frames"

        scenes_base_path = self.scenes_source_path(self.state.RESYNTH_STEP)
        create_directory(self.state.resynthesis_path)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Resynthesize") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.state.resynthesis_path, scene_name)
                create_directory(scene_output_path)

                resynth_type = self.state.resynth_option if self.state.resynthesize else None
                resynth_hint = self.state.get_hint(self.state.scene_labels.get(scene_name),
                                                   self.state.RESYNTHESIS_HINT)
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
                    self.one_pass_resynthesis(scene_input_path, scene_output_path,
                                              output_basename, series_interpolater)
                elif resynth_type == "Clean" or resynth_type == "Scrub":
                    one_pass_only = resynth_type == "Clean"
                    self.two_pass_resynthesis(scene_input_path, scene_output_path,
                                              output_basename, series_interpolater,
                                              one_pass_only=one_pass_only)
                else:
                    # no need to resynthesize so just copy the files using the resequencer
                    ResequenceFiles(scene_input_path,
                                    self.state.frame_format,
                                    output_basename,
                                    1, 1,
                                    1, 0,
                                    -1,
                                    False,
                                    self.log_fn,
                                    output_path=scene_output_path).resequence()
                Mtqdm().update_bar(bar)


    # Inflation Processing

    def inflate_scenes(self, kept_scenes):
        interpolater = Interpolate(self.engine.model, self.log_fn)
        use_time_step = self.engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log_fn)
        series_interpolater = InterpolateSeries(deep_interpolater, self.log_fn)

        scenes_base_path = self.scenes_source_path(self.state.INFLATE_STEP)
        create_directory(self.state.inflation_path)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Inflate") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.state.inflation_path, scene_name)
                create_directory(scene_output_path)

                num_splits = 0
                disable_inflation = False

                project_splits = 0
                if self.state.inflate:
                    if self.state.inflate_by_option == "1X":
                        project_splits = 0
                    if self.state.inflate_by_option == "2X":
                        project_splits = 1
                    elif self.state.inflate_by_option == "4X":
                        project_splits = 2
                    elif self.state.inflate_by_option == "8X":
                        project_splits = 3
                    elif self.state.inflate_by_option == "16X":
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
                    file_list = sorted(get_files(scene_input_path, extension=self.state.frame_format))
                    series_interpolater.interpolate_series(file_list,
                                                        scene_output_path,
                                                        num_splits,
                                                        output_basename,
                                                        type=self.state.frame_format)
                    ResequenceFiles(scene_output_path,
                                    self.state.frame_format,
                                    "inflated_frame",
                                    1, 1,
                                    1, 0,
                                    -1,
                                    True,
                                    self.log_fn).resequence()
                else:
                    # no need to inflate so just copy the files using the resequencer
                    ResequenceFiles(scene_input_path,
                                    self.state.frame_format,
                                    "inflated_frame",
                                    1, 1,
                                    1, 0,
                                    -1,
                                    False,
                                    self.log_fn,
                                    output_path=scene_output_path).resequence()

                Mtqdm().update_bar(bar)


    # Upscaling Processing

    def upscale_scene(self,
                      upscaler,
                      scene_input_path,
                      scene_output_path,
                      upscale_factor,
                      downscale_type=DEFAULT_DOWNSCALE_TYPE):
        self.log(f"creating scene output path {scene_output_path}")
        create_directory(scene_output_path)

        working_path = os.path.join(scene_output_path, self.TEMP_UPSCALE_PATH)
        create_directory(working_path)

        # TODO make this logic general

        # upscale first at the engine's native scale
        file_list = sorted(get_files(scene_input_path))
        output_basename = "upscaled_frames"
        upscaler.upscale_series(file_list, working_path, self.FIXED_UPSCALE_FACTOR, output_basename,
                                self.state.frame_format)

        # get size of upscaled frames
        upscaled_files = sorted(get_files(working_path))
        width, height = image_size(upscaled_files[0])
        self.log(f"size of upscaled images: {width} x {height}")

        # compute downscale factor
        downscale_factor = self.FIXED_UPSCALE_FACTOR / upscale_factor
        self.log(f"downscale factor is {downscale_factor}")

        downscaled_width = int(width / downscale_factor)
        downscaled_height = int(height / downscale_factor)
        self.log(f"size of downscaled images: {downscaled_width} x {downscaled_height}")

        if downscaled_width != width or downscaled_height != height:
            # downsample to final size
            ResizeFrames(scene_input_path,
                        scene_output_path,
                        downscaled_width,
                        downscaled_height,
                        downscale_type,
                        self.log_fn).resize(type=self.state.frame_format)
        else:
            self.log("copying instead of unneeded downscaling")
            copy_files(working_path, scene_output_path)

        try:
            shutil.rmtree(working_path)
        except OSError as error:
            self.log(f"ignoring error deleting working path: {error}")

    def upscale_scenes(self, kept_scenes):
        upscaler = self.get_upscaler()
        scenes_base_path = self.scenes_source_path(self.state.UPSCALE_STEP)
        downscale_type = self.state.remixer_settings["scale_type_down"]
        create_directory(self.state.upscale_path)

        upscale_factor = self.upscale_factor_from_options()

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Upscale") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_path = os.path.join(self.state.upscale_path, scene_name)
                create_directory(scene_output_path)

                upscale_handled = False
                upscale_hint = self.state.get_hint(self.state.scene_labels.get(scene_name), self.state.UPSCALE_HINT)

                if upscale_hint and not self.state.upscale:
                    # only apply the hint if not already upscaling, otherwise the
                    # frames may have mismatched sizes
                    try:
                        # for now ignore the hint value and upscale just at 1X, to clean up zooming
                        self.upscale_scene(upscaler,
                                           scene_input_path,
                                           scene_output_path,
                                           1.0,
                                           downscale_type=downscale_type)
                        upscale_handled = True

                    except Exception as error:
                        self.log(
f"Error in upscale_scenes() handling processing hint {upscale_hint} - skipping processing: {error}")
                        upscale_handled = False

                if not upscale_handled:
                    if self.state.upscale:
                        self.upscale_scene(upscaler,
                                           scene_input_path,
                                           scene_output_path,
                                           upscale_factor,
                                           downscale_type=downscale_type)
                    else:
                        # no need to upscale so just copy the files using the resequencer
                        ResequenceFiles(scene_input_path,
                                        self.state.frame_format,
                                        "upscaled_frames",
                                        1, 1,
                                        1, 0,
                                        -1,
                                        False,
                                        self.log_fn,
                                        output_path=scene_output_path).resequence()
                Mtqdm().update_bar(bar)

    def get_upscaler(self, size : int | None=None):
        """Get Real-ESRGAN upscaler. 'size' is pixels W x H and used for auto-tiling"""
        model_name = self.realesrgan_settings["model_name"]
        gpu_ids = self.realesrgan_settings["gpu_ids"]
        fp32 = self.realesrgan_settings["fp32"]

        # determine if cropped image size is above memory threshold requiring tiling
        use_tiling_over = self.state.remixer_settings["use_tiling_over"]
        size = size or self.state.crop_w * self.state.crop_h

        if size > use_tiling_over:
            tiling = self.realesrgan_settings["tiling"]
            tile_pad = self.realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        return UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, self.log_fn)

    def upscale_factor_from_options(self) -> float:
        upscale_factor = 1.0
        if self.state.upscale:
            if self.state.upscale_option == "2X":
                upscale_factor = 2.0
            elif self.state.upscale_option == "3X":
                upscale_factor = 3.0
            elif self.state.upscale_option == "4X":
                upscale_factor = 4.0
        return upscale_factor


    # Post Processing

    # drop a kept scene after scene compiling has already been done
    # used for dropping empty processed scenes, and force dropping processed scenes
    def drop_kept_scene(self, scene_name):
        self.state.scene_states[scene_name] = self.state.DROP_MARK
        current_path = os.path.join(self.state.scenes_path, scene_name)
        dropped_path = os.path.join(self.state.dropped_scenes_path, scene_name)
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

    # def delete_processed_clip(self, path, scene_name):
    #     removed = []
    #     if path and os.path.exists(path):
    #         files = get_files(path)
    #         # some clips are formatted like "original_namee[000-999].ext",
    #         # and some like "000-000.ext"
    #         # TODO resequence audio clips and thumbnails to make the naming consistent
    #         for file in files:
    #             if file.find(scene_name) != -1:
    #                 os.remove(file)
    #                 removed.append(file)
    #     return removed

    # TODO the last three paths in the list won't have scene name directories but instead files
    #      also it should delete the audio wav file if found since that isn't deleted each save
    # drop an already-processed scene to cut it from the remix video
    def force_drop_processed_scene(self, scene_index):
        scene_name = self.state.scene_names[scene_index]
        self.drop_kept_scene(scene_name)
        removed = []
        purge_dirs = []
        for path in [
            self.state.resize_path,
            self.state.resynthesis_path,
            self.state.inflation_path,
            self.state.upscale_path,
            self.state.video_clips_path,
            self.state.audio_clips_path,
            self.state.clips_path
        ]:
            content_path = os.path.join(path, scene_name)
            if os.path.exists(content_path):
                purge_dirs.append(content_path)
        purge_root = self.state.purge_paths(purge_dirs)
        removed += purge_dirs

        if purge_root:
            self.state.project.copy_project_file(purge_root)

        # audio clips aren't cleaned each time a remix is saved
        # clean now to ensure the dropped scene audio clip is removed
        self.state.clean_remix_content(purge_from="audio_clips")

        return removed

    # General Remix Video Processing

    def compute_effective_slow_motion(self, force_inflation, force_audio, force_inflate_by,
                                      force_silent):
        audio_slow_motion = force_audio or (self.state.inflate and self.state.inflate_slow_option == "Audio")
        silent_slow_motion = force_silent or (self.state.inflate and self.state.inflate_slow_option == "Silent")

        project_inflation_rate = self.inflation_rate(self.state.inflate_by_option) if self.state.inflate else 1
        forced_inflation_rate = self.inflation_rate(force_inflate_by) if force_inflation else 1

        # For slow motion hints, interpret the 'force_inflate_by' as relative to the project rate
        # If the forced inflation rate is 1 it means no inflation, not even at the projecr fate
        if audio_slow_motion or silent_slow_motion:
            if forced_inflation_rate != 1:
                forced_inflation_rate *= project_inflation_rate

        motion_factor = forced_inflation_rate / project_inflation_rate
        return motion_factor, audio_slow_motion, silent_slow_motion, project_inflation_rate, \
            forced_inflation_rate

    def inflation_rate(self, inflate_by : str):
        if not inflate_by:
            return 1
        return int(inflate_by[:-1])


    # Audio Clip Processing

    def create_audio_clips(self):
        self.state.audio_clips_path = os.path.join(self.state.clips_path,
                                                   self.state.AUDIO_CLIPS_PATH)
        create_directory(self.state.audio_clips_path)
        # save the project now to preserve the newly established path
        self.state.save()

        # TODO this may be not needed
        edge_trim = 1 if self.state.resynthesize else 0

        SliceVideo(self.state.source_audio,
                    self.state.project_fps,
                    self.state.scenes_path,
                    self.state.audio_clips_path,
                    0.0,
                    self.state.sound_format,
                    0,
                    1,
                    edge_trim,
                    False,
                    0.0,
                    0.0,
                    self.log_fn,
                    global_options=self.global_options).slice()
        self.state.audio_clips = sorted(get_files(self.state.audio_clips_path))

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
            sample_rate = self.state.video_details.get("sample_rate", "48000")
            output_options = \
                '-f lavfi -i anullsrc -ac 2 -ar ' + sample_rate + ' -map 0:v:0 -map 2:a:0 -c:v copy -shortest ' \
                + custom_audio_options
        else:
            output_options = custom_audio_options

        return output_options


    # Video Clip Processing

    def create_video_clips(self, kept_scenes):
        self.state.video_clips_path = os.path.join(self.state.clips_path,
                                                   self.state.VIDEO_CLIPS_PATH)
        create_directory(self.state.video_clips_path)
        # save the project now to preserve the newly established path
        self.state.save()

        scenes_base_path = self.furthest_processed_path()
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
            for scene_name in kept_scenes:
                scene_input_path = os.path.join(scenes_base_path, scene_name)
                scene_output_filepath = os.path.join(self.state.video_clips_path,
                                                     f"{scene_name}.mp4")

                video_clip_fps = self.compute_scene_fps(scene_name)

                ResequenceFiles(scene_input_path,
                                self.state.frame_format,
                                "processed_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                self.log_fn).resequence()

                PNGtoMP4(scene_input_path,
                                None,
                                video_clip_fps,
                                scene_output_filepath,
                                crf=self.state.output_quality,
                                global_options=self.global_options,
                                type=self.state.frame_format)
                Mtqdm().update_bar(bar)

        self.state.video_clips = sorted(get_files(self.state.video_clips_path))

    def create_custom_video_clips(self,
                                  kept_scenes,
                                  custom_video_options,
                                  custom_ext,
                                  draw_text_options=None):
        self.state.video_clips_path = os.path.join(self.state.clips_path, self.state.VIDEO_CLIPS_PATH)
        create_directory(self.state.video_clips_path)
        # save the project now to preserve the newly established path
        self.state.save()

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
                scene_output_filepath = os.path.join(self.state.video_clips_path,
                                                     f"{scene_name}.{custom_ext}")
                use_custom_video_options = custom_video_options
                if use_custom_video_options.find("<LABEL>") != -1:
                    try:
                        label : str = labels[index]

                        # strip the sort and hint marks in case present
                        _, _, label = self.state.split_label(label)

                        # trim whitespace
                        label = label.strip() if label else ""

                        # FFmpeg needs some things escaped
                        label = label.\
                            replace(":", "\:").\
                            replace(",", "\,").\
                            replace("{", "\{").\
                            replace("}", "\}").\
                            replace("%", "\%")

                        box_part = f":box=1:boxcolor={box_color}:boxborderw={border_size}" \
                            if draw_box else ""
                        label_part = f"text='{label}':x={box_x}:y={box_y}:fontsize={font_size}:fontcolor={font_color}:fontfile='{font_file}':expansion=none{box_part}"
                        shadow_part = f"text='{label}':x={shadow_x}:y={shadow_y}:fontsize={font_size}:fontcolor={shadow_color}:fontfile='{font_file}'" \
                            if draw_shadow else ""
                        draw_text = f"{shadow_part},drawtext={label_part}" \
                            if draw_shadow else label_part
                        use_custom_video_options = use_custom_video_options \
                            .replace("<LABEL>", draw_text)

                    except IndexError as error:
                        use_custom_video_options = use_custom_video_options\
                            .replace("<LABEL>", f"[{error}]")

                video_clip_fps = self.compute_scene_fps(scene_name)

                ResequenceFiles(scene_input_path,
                                self.state.frame_format,
                                "processed_frame",
                                1,
                                1,
                                1,
                                0,
                                -1,
                                True,
                                self.log_fn).resequence()
                PNGtoCustom(scene_input_path,
                            None,
                            video_clip_fps,
                            scene_output_filepath,
                            global_options=self.global_options,
                            custom_options=use_custom_video_options,
                            type=self.state.frame_format)
                Mtqdm().update_bar(bar)
        self.state.video_clips = sorted(get_files(self.state.video_clips_path))

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
        return self.state.project_fps * fps_factor

    def compute_forced_inflation(self, scene_name):
        force_inflation = False
        force_audio = False
        force_inflate_by = None
        force_silent = False

        inflation_hint = self.state.get_hint(self.state.scene_labels.get(scene_name), self.state.INFLATION_HINT)
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
            # else implied "N" for no slow motion
        return force_inflation, force_audio, force_inflate_by, force_silent

    def compute_scene_fps(self, scene_name):
        force_inflation, force_audio, force_inflate_by, force_silent =\
            self.compute_forced_inflation(scene_name)

        return self.compute_inflated_fps(force_inflation,
                                         force_audio,
                                         force_inflate_by,
                                         force_silent)


    # Scene Clip Processing

    def create_scene_clips(self, kept_scenes):
        if self.state.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.state.video_clips[index]
                    scene_audio_path = self.state.audio_clips[index]
                    scene_output_filepath = os.path.join(self.state.clips_path, f"{scene_name}.mp4")

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
                                        global_options=self.global_options,
                                        output_options=output_options)
                    Mtqdm().update_bar(bar)
            self.state.clips = sorted(get_files(self.state.clips_path))
        else:
            self.state.clips = sorted(get_files(self.state.video_clips_path))

    def create_custom_scene_clips(self,
                                  kept_scenes,
                                  custom_audio_options,
                                  custom_ext):
        if self.state.video_details["has_audio"]:
            with Mtqdm().open_bar(total=len(kept_scenes), desc="Remix Clips") as bar:
                for index, scene_name in enumerate(kept_scenes):
                    scene_video_path = self.state.video_clips[index]
                    scene_audio_path = self.state.audio_clips[index]
                    scene_output_filepath = os.path.join(self.state.clips_path,
                                                         f"{scene_name}.{custom_ext}")

                    force_inflation, force_audio, force_inflate_by, force_silent =\
                        self.compute_forced_inflation(scene_name)

                    output_options = self.compute_inflated_audio_options(custom_audio_options,
                                                                force_inflation,
                                                                force_audio=force_audio,
                                                                force_inflate_by=force_inflate_by,
                                                                force_silent=force_silent)

                    combine_video_audio(scene_video_path, scene_audio_path,
                                        scene_output_filepath, global_options=self.global_options,
                                        output_options=output_options)
                    Mtqdm().update_bar(bar)
            self.state.clips = sorted(get_files(self.state.clips_path))
        else:
            self.state.clips = sorted(get_files(self.state.video_clips_path))


    # Remix Video Processing

    def create_remix_video(self, output_filepath, use_scene_sorting=True):
        with Mtqdm().open_bar(total=1, desc="Saving Remix") as bar:
            Mtqdm().message(bar, "Using FFmpeg to concatenate scene clips - no ETA")
            assembly_list = self.assembly_list(self.state.clips) \
                if use_scene_sorting else self.state.clips
            ffcmd = combine_videos(assembly_list,
                                   output_filepath,
                                   global_options=self.global_options)
            Mtqdm().update_bar(bar)
        return ffcmd

    def assembly_list(self, clip_filepaths : list, rename_clips=True) -> list:
        """Get list clips to assemble in order.
        'clip_filepaths' is expected to be full path and filename to the remix clips, corresponding to the list of kept scenes.
        If there are labeled scenes, they are arranged first in sorted order, followed by non-labeled scenes."""
        if not self.state.scene_labels:
            return clip_filepaths

        # map scene names to clip filepaths
        kept_scenes = self.state.kept_scenes()
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
                    scene_label = self.state.scene_labels.get(scene_name)
                    if scene_label:
                        _, _, title = self.state.split_label(scene_label)
                        if title:
                            new_filename = simple_sanitize_filename(title)
                            path, filename, ext = split_filepath(kept_clip_filepath)
                            new_filepath = os.path.join(path, f"{new_filename}_{filename}" + ext)
                            self.log(f"renaming clip {kept_clip_filepath} to {new_filepath}")
                            os.replace(kept_clip_filepath, new_filepath)
                            kept_clip_filepath = new_filepath

                assembly.append(kept_clip_filepath)
                unlabeled_scenes.remove(scene_name)

        # add the unlabeled clips
        for scene_name in unlabeled_scenes:
            assembly.append(map_scene_name_to_clip[scene_name])

        return assembly
