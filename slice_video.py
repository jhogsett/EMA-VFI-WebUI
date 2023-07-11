"""Slice Video Feature Core Code"""
import os
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path
from webui_utils.video_utils import validate_input_path, details_from_group_name, slice_video
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Slice Video feature from the command line"""
    parser = argparse.ArgumentParser(description='Slice a video based on split groups')
    parser.add_argument("--input_path", default=None, type=str,
        help="Input path to video file to be sliced")
    parser.add_argument("--fps", default=29.97, type=float,
                        help="Frame rate of the video to be sliced")
    parser.add_argument("--group_path", default=None, type=str,
        help="Input path to PNG frame group directories")
    parser.add_argument("--output_path", default="", type=str,
        help="Output path for sliced segments files (default '' = save in group directories")
    parser.add_argument("--output_scale", default="0.5", type=float,
                        help="Scale factor for output 0.0 to 1.0 (default 0.5)")
    parser.add_argument("--type", default="mp4", type=str,
        help="Sliced output 'mp4' (default), 'gif', 'wav', 'mp3', 'jpg'")
    parser.add_argument("--mp4_quality", default=23, type=int,
                        help="MP4 video quality 17 (best) to 28, default 23")
    parser.add_argument("--gif_factor", default=1, type=int,
                        help="GIF speed-up factor (default: 1 = real-time)")
    parser.add_argument("--edge_trim", default=0, type=int,
                        help="Extend (< 0) or shrink (> 0) end frames (default: 0)")
    parser.add_argument("--gif_high_quality", default=False, type=bool,
                        help="Enable high-qualty GIF palette - slow (default: False)")
    parser.add_argument("--gif_fps", default=0.0, type=float,
                        help="GIF frame rate (default 0.0 = same as input FPS)")
    parser.add_argument("--gif_end_delay", default=0.0, type=float,
                        help="GIF seconds delay after last frame (default 0.0)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SliceVideo(args.input_path,
                args.fps,
                args.group_path,
                args.output_path,
                args.output_scale,
                args.type,
                args.mp4_quality,
                args.gif_factor,
                args.edge_trim,
                args.gif_high_quality,
                args.gif_fps,
                args.gif_end_delay,
                log.log).slice()

class SliceVideo:
    """Encapsulate logic for Split Scenes feature"""
    def __init__(self,
                input_path : str,
                fps : float,
                group_path : str,
                output_path : str,
                output_scale : float,
                type : str,
                mp4_quality : int,
                gif_factor : int,
                edge_trim : int,
                gif_high_quality : bool,
                gif_fps : float,
                gif_end_delay : float,
                log_fn : Callable | None):
        self.input_path = input_path
        self.fps = fps
        self.group_path = group_path
        self.output_path = output_path
        self.output_scale = output_scale
        self.type = type
        self.mp4_quality = mp4_quality
        self.gif_factor = gif_factor
        self.edge_trim = edge_trim
        self.gif_high_quality = gif_high_quality
        self.gif_fps = gif_fps
        self.gif_end_delay = gif_end_delay
        self.log_fn = log_fn
        valid_types = ["mp4", "gif", "wav", "mp3", "jpg"]

        if not is_safe_path(self.input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(self.group_path):
            raise ValueError("'group_path' must be a legal path")
        if self.output_path:
            if not is_safe_path(self.output_path):
                raise ValueError("'output_path' must be a legal path")
        self.output_scale = float(self.output_scale)
        if self.output_scale < 0.0 or self.output_scale > 1.0:
            raise ValueError("'output_scale' must be between 0.0 and 1.0")
        if not self.type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")
        if self.mp4_quality < 0:
            raise ValueError(f"'mp4_quality' must be >= 0")
        if self.gif_factor < 1:
            raise ValueError(f"'gif_factor' must be >= 1")

    def slice(self):
        group_names = validate_input_path(self.group_path, -1)
        if self.output_path:
            self.log(f"Creating output path {self.output_path}")
            create_directory(self.output_path)

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as bar:
            for group_name in group_names:
                first_index, last_index, num_width = details_from_group_name(group_name)
                output_path = self.output_path or os.path.join(self.group_path, group_name)
                self.log("using slice_video (may cause long delay while processing request)")
                first_index += self.edge_trim
                if first_index < 0:
                    first_index = 0
                last_index -= self.edge_trim

                # With edge trim this can end up with a zero or negative duration
                # render at least one frame's worth so a valid file is produced.
                # The combine_video_audio() function will trim to the shortest stream
                if last_index <= first_index:
                    last_index = first_index + 1

                ffmpeg_cmd = slice_video(self.input_path,
                            self.fps,
                            output_path,
                            num_width,
                            first_index,
                            last_index,
                            self.type,
                            self.mp4_quality,
                            self.gif_factor,
                            self.output_scale,
                            self.gif_high_quality,
                            self.gif_fps,
                            self.gif_end_delay)
                self.log(f"FFmpeg command line: '{ffmpeg_cmd}'")
                Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
