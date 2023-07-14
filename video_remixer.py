"""Video Remixer UI state management"""
import os
import yaml
from yaml import Loader, YAMLError
from webui_utils.file_utils import get_files
from webui_utils.simple_utils import seconds_to_hmsf
from webui_utils.video_utils import details_from_group_name
class VideoRemixerState():
    def __init__(self):
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
        self.thumbnail_type = None
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

    DEF_FILENAME = "project.yaml"

    def save(self, filepath : str=None):
        filepath = filepath or self.project_filepath()
        with open(filepath, "w", encoding="UTF-8") as file:
            yaml.dump(self, file)

    def project_filepath(self, filename : str=DEF_FILENAME):
        return os.path.join(self.project_path, filename)

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

    def check_for_bad_scenes(self):
        bad_scenes = []
        for scene in self.scene_names:
            first, last, _ = details_from_group_name(scene)
            if last <= first:
                bad_scenes.append(scene)
        return bad_scenes

    @staticmethod
    def load(filepath : str):
        with open(filepath, "r") as file:
            try:
                state = yaml.load(file, Loader=Loader)
                state.scene_names = sorted(state.scene_names)
                state.thumbnails = sorted(state.thumbnails)
                state.audio_clips = sorted(state.audio_clips)
                state.video_clips = sorted(state.video_clips)
                return state
            except YAMLError as error:
                if hasattr(error, 'problem_mark'):
                    mark = error.problem_mark
                    message = f"Error loading project file on line {mark.line+1} column {mark.column+1}: {error}"
                else:
                    message = error
                raise ValueError(message)
