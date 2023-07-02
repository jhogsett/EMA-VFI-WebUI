"""Slice Video Feature Core Code"""
import os
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path, split_filepath
from webui_utils.video_utils import validate_input_path, details_from_group_name, slice_video
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Video feature from the command line"""
    parser = argparse.ArgumentParser(description='Slice a video based on split groups')
    parser.add_argument("--input_path", default=None, type=str,
        help="Input path to video file to be sliced")
    parser.add_argument("--fps", default=30, type=int, help="Frame rate of the video to be sliced")
    parser.add_argument("--group_path", default=None, type=str,
        help="Input path to PNG frame group directories")
    parser.add_argument("--type", default="mp4", type=str,
        help="Sliced output 'mp4' (default), 'wav'") # future gif, mp3
    parser.add_argument("--output_path", default=None, type=str,
        help="Output path for sliced segments files (default '' = save in group directories")
    parser.add_argument("--mp4_quality", default=23, type=int,
                        help="MP4 video quality 17 (best) to 28, default 23")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SliceVideos(args.input_path,
                args.fps,
                args.group_path,
                args.output_path,
                args.type,
                args.mp4_quality,
                log.log).slice()

class SliceVideos:
    """Encapsulate logic for Split Scenes feature"""
    def __init__(self,
                input_path : str,
                fps : int,
                group_path : str,
                output_path : str,
                type : str,
                mp4_quality : int,
                log_fn : Callable | None):
        self.input_path = input_path
        self.fps = fps
        self.group_path = group_path
        self.output_path = output_path
        self.type = type
        self.mp4_quality = mp4_quality
        self.log_fn = log_fn
        valid_types = ["mp4", "wav"]

        if not is_safe_path(self.input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(self.group_path):
            raise ValueError("'group_path' must be a legal path")
        if self.output_path:
            if not is_safe_path(self.output_path):
                raise ValueError("'output_path' must be a legal path")
        if not self.type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")

    def slice(self):
        # get groups
        # go through groups
        # details_from_group_name
        # compute output path based on if its blank

        group_names = validate_input_path(self.group_path, -1)
        self.log(f"Creating output path {self.output_path}")
        create_directory(self.output_path)

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as bar:
            for group_name in group_names:
                first_index, last_index, _ = details_from_group_name(group_name)
                output_path = self.output_path or os.path.join(self.group_path, group_name)
                slice_video(self.input_path, output_path, self.fps, first_index, last_index,
                            self.type, self.mp4_quality)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
