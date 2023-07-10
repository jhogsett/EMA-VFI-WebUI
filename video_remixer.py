"""Video Remixer UI state management"""
import os
import yaml
from yaml import Loader
class VideoRemixerState():
    def __init__(self):
        self.source_video = None
        self.video_details = {}
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
        self.scene_names = []
        self.scene_states = {}
        self.current_scene = None
        self.resynthesize = False
        self.inflate = False
        self.resize = False
        self.upscale = False
        self.upscale_option = None
        self.assemble = False
        self.keep_scene_clips = False
        self.output_pattern = None
        self.frames_path = None
        self.scenes_path = None
        self.frames_per_minute = None
        self.thumbnail_path = None
        self.thumbnails = []
        self.clips_path = None
        self.audio_clips_path = None
        self.audio_clips = []
        self.video_clips_path = None
        self.video_clips = []
        self.video_info1 = None
        self.project_info2 = None
        self.project_info4 = None
        self.summary_info6 = None

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

    @staticmethod
    def load(filepath : str):
        with open(filepath, "r") as file:
            return yaml.load(file, Loader=Loader)
