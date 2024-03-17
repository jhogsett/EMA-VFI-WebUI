"""Video Remixer UI state management"""
import os
import math
import re
import shutil
from typing import Callable
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    clean_directories, copy_files, directory_populated
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf
from webui_utils.video_utils import details_from_group_name
from webui_utils.mtqdm import Mtqdm
from video_remixer_project import VideoRemixerProject
from video_remixer_ingest import VideoRemixerIngest

class VideoRemixerState():
    def __init__(self, remixer_settings : dict, global_options : dict, log_fn : Callable):
        # used internally only
        self.project = VideoRemixerProject(self, log_fn)
        self.ingest = VideoRemixerIngest(self, log_fn)
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
            "ingest",
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

    SCENES_PATH = "SCENES"
    DROPPED_SCENES_PATH = "DROPPED_SCENES"
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

    def log(self, message):
        self.log_fn(message)


    @staticmethod
    def new_project(remixer_settings : dict, global_options : dict, log_fn : Callable):
        state = VideoRemixerState(remixer_settings, global_options, log_fn)
        state.project.set_project_defaults()
        return state

    def setup_processing_paths(self):
        self.resize_path = os.path.join(self.project_path, self.RESIZE_PATH)
        self.resynthesis_path = os.path.join(self.project_path, self.RESYNTH_PATH)
        self.inflation_path = os.path.join(self.project_path, self.INFLATE_PATH)
        self.upscale_path = os.path.join(self.project_path, self.UPSCALE_PATH)

    def project_ported(self, opened_project_file):
        opened_path, _, _ = split_filepath(opened_project_file)
        return self.project_path != opened_path

    def tryattr(self, attribute : str, default=None):
        return getattr(self, attribute) if hasattr(self, attribute) else default

    def save(self, filepath : str=None):
        self.project.save(filepath)

    def save_progress(self, progress : str, save_project : bool=True):
        self.progress = progress
        if save_project:
            self.save()

    def _calc_split_frames(self, fps, seconds):
        return round(float(fps) * float(seconds))

    def kept_scenes(self) -> list:
        """Returns kept scene names sorted"""
        return sorted([scene for scene in self.scene_states
                       if self.scene_states[scene] == self.KEEP_MARK])

    def dropped_scenes(self) -> list:
        """Returns dropped scene names sorted"""
        return sorted([scene for scene in self.scene_states
                       if self.scene_states[scene] == self.DROP_MARK])

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

    def scene_marker(self, scene_name):
        scene_index = self.scene_names.index(scene_name)
        _, _, _, _, scene_start, scene_duration, _, _ = self.scene_chooser_data(scene_index)
        marker = f"[{scene_index} {scene_name} {scene_start} +{scene_duration}]"
        return marker

    def scene_title(self, scene_name):
        scene_index = self.scene_names.index(scene_name)
        _, _, _, scene_position, _, _, _, _ = self.scene_chooser_data(scene_index)
        return scene_position



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
                label += "-in" + str(self.inflate_by_option)[0]
                if self.inflate_slow_option == "Audio":
                    label += "SA"
                elif self.inflate_slow_option == "Silent":
                    label += "SM"
            else:
                label += "-inH"

        if self.upscale_chosen():
            if self.upscale:
                label += "-up" + str(self.upscale_option)[0]
            else:
                label += "-upH"

        label += "-" + extra_suffix if extra_suffix else ""
        return label

    def resize_chosen(self):
        return self.resize or self.hint_present(self.RESIZE_HINT)

    def resynthesize_chosen(self):
        return self.resynthesize or self.hint_present(self.RESYNTHESIS_HINT)

    def inflate_chosen(self):
        return self.inflate or self.hint_present(self.INFLATION_HINT)

    def upscale_chosen(self):
        return self.upscale or self.hint_present(self.UPSCALE_HINT)


    def delete_path(self, path):
        if path and os.path.exists(path):
            with Mtqdm().open_bar(total=1, desc="Deleting") as bar:
                Mtqdm().message(bar, "Removing project content - No ETA")
                shutil.rmtree(path)
                Mtqdm().update_bar(bar)
            return path
        else:
            return None

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
        new_lower_scene_name = VideoRemixerIngest.encode_scene_name(num_width,
                                                new_lower_first_frame, new_lower_last_frame, 0, 0)
        new_upper_first_frame = first_frame + split_frame
        new_upper_last_frame = last_frame
        new_upper_scene_name = VideoRemixerIngest.encode_scene_name(num_width,
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
        self.ingest.create_thumbnail(new_lower_scene_name)
        self.log(f"about to create thumbnail for new upper scene {new_upper_scene_name}")
        self.ingest.create_thumbnail(new_upper_scene_name)
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
