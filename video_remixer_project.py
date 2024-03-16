"""Video Remixer project management"""
import os
import shutil
import sys
from typing import Callable, TYPE_CHECKING
import yaml
from yaml import Loader, YAMLError
from webui_utils.auto_increment import AutoIncrementBackupFilename, AutoIncrementDirectory
from webui_utils.file_utils import split_filepath, create_directory, get_directories, get_files,\
    duplicate_directory
from webui_utils.simple_utils import ranges_overlap
from webui_utils.video_utils import details_from_group_name
from webui_utils.jot import Jot
from webui_utils.mtqdm import Mtqdm

if TYPE_CHECKING:
    from video_remixer import VideoRemixerState

class VideoRemixerProject():
    def __init__(self, state : "VideoRemixerState", log_fn : Callable):
        self.state = state
        self.log_fn = log_fn

    def log(self, message):
        if self.log_fn:
            self.log_fn(message)

    SAFETY_DEFAULTS = {
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
        "resynth_option" : "Scrub",
        "resize_w" : 1920,
        "resize_h" : 1080,
        "crop_w" : 1920,
        "crop_h" : 1080,
        "frame_format" : "png",
        "sound_format" : "wav"
    }

    DEF_FILENAME = "project.yaml"

    ## Exports --------------------------

    @staticmethod
    def load(filepath : str, remixer_settings : dict, global_options : dict, log_fn : Callable):
        with open(filepath, "r") as file:
            try:
                state : "VideoRemixerState" = yaml.load(file, Loader=Loader)

                # establish some internal state
                state.remixer_settings = remixer_settings
                state.global_options = global_options
                state.log_fn = log_fn

                # reload some things
                if not state.scene_names:
                    state.scene_names = sorted(get_directories(state.scenes_path,
                                                               ignore_empty_path=True))
                if not state.thumbnails:
                    state.thumbnails = sorted(get_files(state.thumbnail_path,
                                                        ignore_empty_path=True))
                if not state.audio_clips:
                    state.audio_clips = sorted(get_files(state.audio_clips_path,
                                                        ignore_empty_path=True))
                if not state.video_clips:
                    state.video_clips = sorted(get_files(state.video_clips_path,
                                                        ignore_empty_path=True))
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
    def load_ported(original_project_path, ported_project_file : str, remixer_settings,
                    global_options, log_fn, save_original = True):
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

        state = VideoRemixerProject.load(ported_project_file, remixer_settings, global_options,
                                         log_fn)
        state.save(ported_project_file)

        return state

    def project_ported(self, opened_project_file):
        opened_path, _, _ = split_filepath(opened_project_file)
        return self.state.project_path != opened_path

    def save(self, filepath : str=None):
        filepath = filepath or self.project_filepath()
        with open(filepath, "w", encoding="UTF-8") as file:
            yaml.dump(self.state, file, width=1024)

    # when advancing forward from the Set Up Project step
    # the user may be redoing the project from this step
    # need to purge anything created based on old settings
    def reset_at_project_settings(self):
        purge_path = self.state.purge_paths([
            self.state.scenes_path,
            self.state.dropped_scenes_path,
            self.state.thumbnail_path,
            self.state.clips_path,
            self.state.resize_path,
            self.state.resynthesis_path,
            self.state.inflation_path,
            self.state.upscale_path])

        if purge_path:
            self.copy_project_file(purge_path)
        self.state.scene_names = []
        self.state.current_scene = 0
        self.state.thumbnails = []

    def copy_project_file(self, copy_path):
        project_file = self.determine_project_filepath(self.state.project_path)
        saved_project_file = os.path.join(copy_path, self.DEF_FILENAME)
        shutil.copy(project_file, saved_project_file)
        return saved_project_file

    def post_load_integrity_check(self):
        messages = Jot()

        self.state.thumbnail_path, self.state.thumbnails, message = \
            self.ensure_valid_populated_path(
                "Thumbnails", self.state.thumbnail_path, self.state.thumbnails)
        if message:
            messages.add(message)

        self.state.clips_path, self.state.clips, message = \
            self.ensure_valid_populated_path(
                "Clips", self.state.clips_path, self.state.clips)
        if message:
            messages.add(message)

        self.state.audio_clips_path, self.state.audio_clips, message = \
            self.ensure_valid_populated_path(
                "Audio Clips", self.state.audio_clips_path, self.state.audio_clips)
        if message:
            messages.add(message)

        self.state.video_clips_path, self.state.video_clips, message = \
            self.ensure_valid_populated_path(
                "Video Clips", self.state.video_clips_path, self.state.video_clips)
        if message:
            messages.add(message)

        self.state.dropped_scenes_path, message = self.ensure_valid_path(
            "Dropped Scenes", self.state.dropped_scenes_path)
        if message:
            messages.add(message)

        self.state.frames_path, message = self.ensure_valid_path(
            "Frames Path", self.state.frames_path)
        if message:
            messages.add(message)

        self.state.resize_path, message = self.ensure_valid_path(
            "Resize Path", self.state.resize_path)
        if message:
            messages.add(message)

        self.state.resynthesis_path, message = self.ensure_valid_path(
            "Resynthesis Path", self.state.resynthesis_path)
        if message:
            messages.add(message)

        self.state.inflation_path, message = self.ensure_valid_path(
            "Inflation Path", self.state.inflation_path)
        if message:
            messages.add(message)

        self.state.upscale_path, message = self.ensure_valid_path(
            "Upscale Path", self.state.upscale_path)
        if message:
            messages.add(message)

        self.state.scenes_path, message = self.ensure_valid_path(
            "Scenes Path", self.state.scenes_path)
        if message:
            messages.add(message)

        return messages.report()

    def recover_project(self):
        self.log("beginning project recovery")

        # purge project paths ahead of recreating
        purged_path = self.state.purge_paths([
            self.state.scenes_path,
            self.state.dropped_scenes_path,
            self.state.thumbnail_path,
            self.state.audio_clips_path,
            self.state.video_clips_path,
            self.state.clips_path,
            self.state.resize_path,
            self.state.resynthesis_path,
            self.state.inflation_path,
            self.state.upscale_path
        ])
        self.log(f"generated content directories purged to {purged_path}")

        self.state.render_source_frames(prevent_overwrite=True)
        self.log(f"source frames rendered to {self.state.frames_path}")

        source_audio_crf = self.state.remixer_settings["source_audio_crf"]
        try:
            self.state.create_source_audio(source_audio_crf, prevent_overwrite=True)
            self.log(f"created source audio {self.state.source_audio} from {self.state.source_video}")
        except ValueError as error:
            # ignore, don't create the file if present or same as video
            self.log(f"ignoring: {error}")

        create_directory(self.state.scenes_path)
        self.log(f"created scenes directory {self.state.scenes_path}")
        create_directory(self.state.dropped_scenes_path)
        self.log(f"created dropped scenes directory {self.state.dropped_scenes_path}")

        self.log("beginning recreating of scenes from source frames")
        source_frames = sorted(get_files(self.state.frames_path))
        with Mtqdm().open_bar(total=len(self.state.scene_names), desc="Recreating Scenes") as bar:
            for scene_name in self.state.scene_names:
                scene_path = os.path.join(self.state.scenes_path, scene_name)
                create_directory(scene_path)
                self.log(f"created scene directory {scene_path}")

                first_index, last_index, _ = details_from_group_name(scene_name)
                num_frames = (last_index - first_index) + 1
                with Mtqdm().open_bar(total=num_frames, desc="Copying") as inner_bar:
                    for index in range(first_index, last_index + 1):
                        source_path = source_frames[index]
                        _, filename, ext = split_filepath(source_path)
                        frame_path = os.path.join(scene_path, filename + ext)
                        shutil.copy(source_path, frame_path)
                        Mtqdm().update_bar(inner_bar)

                self.log(f"scene frames copied to {scene_path}")
                Mtqdm().update_bar(bar)
        self.log(f"recreated scenes")

        self.log(f"about to create thumbnails of type {self.state.thumbnail_type}")
        self.state.create_thumbnails()
        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))

        self.state.clips_path = os.path.join(self.state.project_path, self.state.CLIPS_PATH)
        self.log(f"creating clips directory {self.state.clips_path}")
        create_directory(self.state.clips_path)

    def export_project(self, new_project_path, new_project_name, kept_scenes):
        new_project_name = new_project_name.strip()
        full_new_project_path = os.path.join(new_project_path, new_project_name)

        create_directory(full_new_project_path)
        new_profile_filepath = self.copy_project_file(full_new_project_path)

        # load the copied project file
        new_state = VideoRemixerProject.load(new_profile_filepath, self.state.remixer_settings,
                                           self.state.global_options, self.log_fn)

        # update project paths to the new one
        new_state = VideoRemixerProject.load_ported(new_state.project_path, new_profile_filepath,
                    self.state.remixer_settings, self.state.global_options, self.log_fn,
                    save_original=False)

        # ensure the project directories exist
        new_state.project.post_load_integrity_check()

        # copy the source video
        with Mtqdm().open_bar(total=1, desc="Copying") as bar:
            Mtqdm().message(bar, "Copying source video - no ETA")
            shutil.copy(self.state.source_video, new_state.source_video)
            Mtqdm().update_bar(bar)

        # copy the source audio (if not using the source video as audio source)
        if self.state.source_audio != self.state.source_video:
            with Mtqdm().open_bar(total=1, desc="Copying") as bar:
                Mtqdm().message(bar, "Copying source audio - no ETA")
                shutil.copy(self.state.source_audio, new_state.source_audio)
                Mtqdm().update_bar(bar)

        # ensure scenes path contains all / only kept scenes
        self.state.recompile_scenes()

        # prepare to rebuild scene_states dict, and scene_names, thumbnails lists
        # in the new project
        new_state.scene_states = {}
        new_state.scene_names = []
        new_state.thumbnails = []

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Exporting") as bar:
            for index, scene_name in enumerate(self.state.scene_names):
                state = self.state.scene_states[scene_name]
                if state == self.state.KEEP_MARK:
                    scene_name = self.state.scene_names[index]
                    new_state.scene_states[scene_name] = self.state.KEEP_MARK

                    new_state.scene_names.append(scene_name)
                    scene_dir = os.path.join(self.state.scenes_path, scene_name)
                    new_scene_dir = os.path.join(new_state.scenes_path, scene_name)
                    duplicate_directory(scene_dir, new_scene_dir)

                    scene_thumbnail = self.state.thumbnails[index]
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
    def determine_project_filepath(project_path):
        if os.path.isdir(project_path):
            project_file = os.path.join(project_path, VideoRemixerProject.DEF_FILENAME)
        else:
            project_file = project_path
            project_path, _, _ = split_filepath(project_path)
        if not os.path.exists(project_file):
            raise ValueError(f"Project file {project_file} was not found")
        return project_file

    ## Internal -------------------------

    def set_project_defaults(self, defaults=None):
        defaults = defaults or self.SAFETY_DEFAULTS
        self.state.project_fps = self.state.remixer_settings["def_project_fps"]
        self.state.deinterlace = defaults["deinterlace"]
        self.state.split_type = defaults["split_type"]
        self.state.scene_threshold = defaults["scene_threshold"]
        self.state.break_duration = defaults["break_duration"]
        self.state.break_ratio = defaults["break_ratio"]
        self.state.thumbnail_type = defaults["thumbnail_type"]
        self.state.resize = defaults["resize"]
        self.state.resynthesize = defaults["resynthesize"]
        self.state.inflate = defaults["inflate"]
        self.state.upscale = defaults["upscale"]
        self.state.upscale_option = defaults["upscale_option"]
        self.state.min_frames_per_scene = defaults["min_frames_per_scene"]
        self.state.split_time = defaults["split_time"]
        self.state.inflate_by_option = defaults["inflate_by_option"]
        self.state.inflate_slow_option = defaults["inflate_slow_option"]
        self.state.resynth_option = defaults["resynth_option"]
        self.state.frame_format = defaults["frame_format"]
        self.state.audio_format = defaults["sound_format"]

    def project_filepath(self, filename : str=DEF_FILENAME):
        return os.path.join(self.state.project_path, filename)

    def backup_project_file(self, purged_path=None):
        if not purged_path:
            purged_root_path = os.path.join(self.state.project_path, self.state.PURGED_CONTENT)
            create_directory(purged_root_path)
            purged_path, _ = AutoIncrementDirectory(purged_root_path).next_directory(self.state.PURGED_DIR)
        return self.copy_project_file(purged_path)

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

    def import_project(self, import_path):
        try:
            import_file = VideoRemixerProject.determine_project_filepath(import_path)
        except ValueError as error:
            message = f"import_project(): error determining project filepath: {error}"
            self.log(message)
            raise ValueError(message)

        try:
            imported = VideoRemixerProject.load(import_file, None, None, self.log_fn)
        except ValueError as error:
            message = f"import_project(): error loading import project: {error}"
            self.log(message)
            raise ValueError(message)

        if imported.project_ported(import_file):
            try:
                imported = VideoRemixerProject.load_ported(imported.project_path, import_file, None,
                                                         None, self.log_fn)
            except ValueError as error:
                message = f"import_project(): error loading ported import project: {error}"
                self.log(message)
                raise ValueError(message)

        messages = imported.project.post_load_integrity_check()
        self.log(f"import_project(): port_load_integrity_check():\r\n{messages}")

        _, source_video, source_ext = split_filepath(self.state.source_video)
        _, import_video, import_ext = split_filepath(imported.source_video)
        source_video += source_ext
        import_video += import_ext

        if source_video != import_video:
            message = "Unable to import from a project created from a different source video"
            self.log(message)
            raise ValueError(message)

        current_lowest, current_highest = self.scene_frame_limits(self)
        import_lowest, import_highest = self.scene_frame_limits(imported)
        current_range = range(current_lowest, current_highest + 1)
        import_range = range(import_lowest, import_highest + 1)

        if ranges_overlap(current_range, import_range):
            message = "Unable to import from a project with overlapping scene ranges"
            self.log(message)
            raise ValueError(message)

        self.state.uncompile_scenes()
        imported.uncompile_scenes()

        self.backup_project_file()

        self.state.scene_names = sorted(self.state.scene_names + imported.scene_names)

        for scene_name, state in imported.scene_states.items():
            self.state.scene_states[scene_name] = state

        for scene_name, label in imported.scene_labels.items():
            self.state.scene_labels[scene_name] = label

        duplicate_directory(imported.scenes_path, self.state.scenes_path)
        duplicate_directory(imported.thumbnail_path, self.state.thumbnail_path)

        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))

        self.state.current_scene = self.state.scene_names.index(imported.scene_names[0])

        # save the imported project state since its been altered
        imported.save()

        self.state.save()

    def scene_frame_limits(self, state : "VideoRemixerState"):
        highest_frame = -1
        lowest_frame = sys.maxsize
        for scene_name in sorted(state.scene_names):
            first, last, _ = details_from_group_name(scene_name)
            lowest_frame = first if first < lowest_frame else lowest_frame
            highest_frame = last if last > highest_frame else highest_frame
        return lowest_frame, highest_frame

    def tryattr(self, attribute : str, default=None):
        return getattr(self, attribute) if hasattr(self, attribute) else default
