"""Restore Frames Feature Core Code"""
import os
import sys
import argparse
from typing import Callable
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory
from webui_utils.simple_utils import restored_frame_searches
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Frame Restoration feature from the command line"""
    parser = argparse.ArgumentParser(description="Video Frame Interpolation (deep)")
    parser.add_argument("--model",
        default="ours", type=str)
    parser.add_argument("--gpu_ids", type=str, default="0",
        help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)")
    parser.add_argument("--img_before", default="images/image0.png", type=str,
        help="Path to image file before the damaged frames")
    parser.add_argument("--img_after", default="images/image2.png", type=str,
        help="Path to image file after the damaged frames")
    parser.add_argument("--num_frames", default=2, type=int,
        help="Number of frames to restore")
    parser.add_argument("--depth", default=10, type=int,
        help="How deep the frame splits go to reach the target")
    parser.add_argument("--output_path", default="images", type=str,
        help="Output path for interpolated PNGs")
    parser.add_argument("--base_filename", default="restored_frame", type=str,
        help="Base filename for interpolated PNGs")
    parser.add_argument("--time_step", dest="time_step", default=False, action="store_true",
        help="Use Time Step instead of Binary Search interpolation (Default: False)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    create_directory(args.output_path)
    engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step=args.time_step)
    interpolater = Interpolate(engine.model, log.log)
    target_interpolater = TargetInterpolate(interpolater, log.log)
    frame_restorer = RestoreFrames(interpolater, target_interpolater, args.time_step, log.log)

    frame_restorer.restore_frames(args.img_before, args.img_after, args.num_frames,
        args.depth, args.output_path, args.base_filename)

class RestoreFrames():
    """Encapsulate logic for the Frame Restoration feature"""
    def __init__(self,
                interpolater : Interpolate,
                target_interpolater : TargetInterpolate,
                time_step : bool,
                log_fn : Callable | None):
        self.interpolater = interpolater
        self.target_interpolater = target_interpolater
        self.time_step = time_step
        self.log_fn = log_fn
        self.output_paths = []

    def restore_frames(self,
                    img_before : str,
                    img_after : str,
                    num_frames : int,
                    depth: int,
                    output_path : str,
                    base_filename : str,
                    progress_label="Frames"):
        """Invoke the Frame Restoration feature"""
        searches = restored_frame_searches(num_frames)
        if self.time_step:
            output_filepath = os.path.join(output_path, base_filename)
            self.interpolater.create_between_frames(img_before, img_after, output_filepath,
                                                    num_frames)
            self.output_paths.extend(self.interpolater.output_paths)
            self.interpolater.output_paths = []
        else:
            with Mtqdm().open_bar(len(searches), desc=progress_label) as bar:
                for search in searches:
                    self.log(f"searching for frame {search}")
                    self.target_interpolater.split_frames(img_before,
                                                        img_after,
                                                        depth,
                                                        min_target=search,
                                                        max_target=search + sys.float_info.epsilon,
                                                        output_path=output_path,
                                                        base_filename=base_filename,
                                                        progress_label="Search")
                    Mtqdm().update_bar(bar)
            self.output_paths.extend(self.target_interpolater.output_paths)
            self.target_interpolater.output_paths = []

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
