"""Video Remixer UI state management"""
import os
import yaml
from yaml import Loader, YAMLError
from webui_utils.file_utils import split_filepath
from webui_utils.simple_utils import seconds_to_hmsf
from webui_utils.video_utils import details_from_group_name, get_essential_video_details
from webui_utils.jot import Jot
from webui_utils.mtqdm import Mtqdm

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

    def ingest_video(self, video_path):
        self.source_video = video_path
        path, filename, _ = split_filepath(video_path)

        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "FFmpeg in use ...")
            try:
                video_details = get_essential_video_details(video_path)
                self.video_details = video_details
            except RuntimeError as error:
                raise ValueError(str(error))
            finally:
                Mtqdm().update_bar(bar)

        project_path = os.path.join(path, f"REMIX-{filename}")
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

























    def keep_all_scenes(self):
        self.scene_states = {scene_name : "Keep" for scene_name in self.scene_names}

    def drop_all_scenes(self):
        self.scene_states = {scene_name : "Drop" for scene_name in self.scene_names}

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

    # def check_for_bad_scenes(self):
    #     bad_scenes = []
    #     for scene in self.scene_names:
    #         first, last, _ = details_from_group_name(scene)
    #         if last <= first:
    #             bad_scenes.append(scene)
    #     return bad_scenes

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
