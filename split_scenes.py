"""Split Scenes Feature Core Code"""
import os
import glob
import argparse
import shutil
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path, split_filepath
from webui_utils.video_utils import get_detected_scenes, get_detected_breaks, scene_list_to_ranges
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Split Scenes feature from the command line"""
    parser = argparse.ArgumentParser(description='Split a directory of PNG frame files')
    parser.add_argument("--input_path", default=None, type=str,
        help="Input path to PNG frame files to split")
    parser.add_argument("--output_path", default=None, type=str,
        help="Base path for frame group directories")
    parser.add_argument("--file_ext", default="png", type=str,
                        help="File extension, default: 'png'; any extension or or '*'")
    parser.add_argument("--type", default="scene", type=str,
        help="Scene detect type 'scene' (default), 'break'")
    parser.add_argument("--scene_threshold", default=0.6, type=float,
                        help="Threshold between 0.0 and 1.0 for scene detection (default 0.6)")
    parser.add_argument("--break_duration", default=2.0, type=float,
                        help="Duration in seconds for break to be detectable (default 2.0)")
    parser.add_argument("--break_ratio", default=0.98, type=float,
            help="Percent 0.0 to 1.0 of frame that must be black to be detectable (default 0.98)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SplitScenes(args.input_path,
                args.output_path,
                args.file_ext,
                args.type,
                args.scene_threshold,
                args.break_duration,
                args.break_ratio,
                log.log).split()

class SplitScenes:
    """Encapsulate logic for Split Scenes feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                file_ext : str,
                type : str,
                scene_threshold : float,
                break_duration : float,
                break_ratio : float,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.file_ext = file_ext
        self.type = type
        self.scene_threshold = scene_threshold
        self.break_duration = break_duration
        self.break_ratio = break_ratio
        self.dry_run = False
        self.log_fn = log_fn
        valid_types = ["scene", "break"]

        if not is_safe_path(self.input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(self.output_path):
            raise ValueError("'output_path' must be a legal path")
        if not self.type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")

    def split_scenes(self, format : str="png"):
        files = sorted(glob.glob(os.path.join(self.input_path, f"*.{self.file_ext}")))
        num_files = len(files)
        num_width = len(str(num_files))
        self.log(f"calling `get_detected_scenes` with input path '{self.input_path}'" +\
                 f" threshold '{self.scene_threshold}'")
        scenes = get_detected_scenes(self.input_path, float(self.scene_threshold), type=format)
        # add one more final fake detection past the end to include frames past the last detection
        scenes.append(num_files+1)
        ranges = scene_list_to_ranges(scenes, num_files)

        group_paths = []
        with Mtqdm().open_bar(total=len(ranges), desc="Scenes") as scene_bar:
            for _range in ranges:
                first_index = _range["first_frame"]
                last_index = _range["last_frame"]
                if last_index >= num_files:
                    last_index = num_files
                group_size = _range["scene_size"]
                group_name = f"{str(first_index).zfill(num_width)}" +\
                            f"-{str(last_index).zfill(num_width)}"
                group_path = os.path.join(self.output_path, group_name)
                group_paths.append(group_path)

                if self.dry_run:
                    self.log(f"[Dry Run] Creating directory {group_path}")
                else:
                    self.log(f"Creating directory {group_path}")
                    create_directory(group_path)

                desc = "Copying"
                with Mtqdm().open_bar(total=group_size, desc=desc) as file_bar:
                    for index in range(first_index, last_index+1):
                        frame_file = files[index]
                        from_filepath = frame_file
                        _, filename, ext = split_filepath(frame_file)
                        to_filepath = os.path.join(group_path, filename + ext)

                        if self.dry_run:
                            print(f"[Dry Run] Copying {from_filepath} to {to_filepath}")
                        else:
                            self.log(f"Copying {from_filepath} to {to_filepath}")
                            shutil.copy(from_filepath, to_filepath)
                        Mtqdm().update_bar(file_bar)
                Mtqdm().update_bar(scene_bar)

        return group_paths

    def split_breaks(self, format : str="jpg"):
        files = sorted(glob.glob(os.path.join(self.input_path, f"*.{self.file_ext}")))
        num_files = len(files)
        num_width = len(str(num_files))
        self.log(f"calling `get_detected_breaks` with input path '{self.input_path}'" +\
                 f" duration '{self.break_duration}' ratio '{self.break_ratio}'")
        scenes = get_detected_breaks(self.input_path, float(self.break_duration),
                                     float(self.break_ratio), type=format)
        # add one more final fake detection past the end to include frames past the last detection
        scenes.append(num_files+1)
        ranges = scene_list_to_ranges(scenes, num_files)

        group_paths = []
        with Mtqdm().open_bar(total=len(ranges), desc="Scenes") as scene_bar:
            for _range in ranges:
                first_index = _range["first_frame"]
                last_index = _range["last_frame"]
                if last_index >= num_files:
                    last_index = num_files
                group_size = _range["scene_size"]
                group_name = f"{str(first_index).zfill(num_width)}" +\
                            f"-{str(last_index).zfill(num_width)}"
                group_path = os.path.join(self.output_path, group_name)
                group_paths.append(group_path)

                if self.dry_run:
                    self.log(f"[Dry Run] Creating directory {group_path}")
                else:
                    self.log(f"Creating directory {group_path}")
                    create_directory(group_path)

                desc = "Copying"
                with Mtqdm().open_bar(total=group_size, desc=desc) as file_bar:
                    for index in range(first_index, last_index+1):
                        frame_file = files[index]
                        from_filepath = frame_file
                        _, filename, ext = split_filepath(frame_file)
                        to_filepath = os.path.join(group_path, filename + ext)

                        if self.dry_run:
                            print(f"[Dry Run] Copying {from_filepath} to {to_filepath}")
                        else:
                            self.log(f"Copying {from_filepath} to {to_filepath}")
                            shutil.copy(from_filepath, to_filepath)
                        Mtqdm().update_bar(file_bar)
                Mtqdm().update_bar(scene_bar)

        return group_paths

    def split(self, type : str="png") -> list:
        """Invoke the Split Scenes feature"""
        # files = sorted(glob.glob(os.path.join(self.input_path, f"*.{self.file_ext}")))
        # num_files = len(files)
        # num_width = len(str(num_files))

        if self.type == "scene":
            if self.scene_threshold < 0.0 or self.scene_threshold > 1.0:
                raise ValueError("'scene_threshold' must be between 0.0 and 1.0")
            self.split_scenes(type)
        else:
            if self.break_duration < 0.0:
                raise ValueError("'break_duration' >= 0.0")
            if self.break_ratio < 0.0 or self.break_ratio > 1.0:
                raise ValueError("'break_ratio' must be between 0.0 and 1.0")
            self.split_breaks(type)

        if self.dry_run:
            print(f"[Dry Run] Creating base output path {self.output_path}")
        else:
            self.log(f"Creating base output path {self.output_path}")
            create_directory(self.output_path)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
