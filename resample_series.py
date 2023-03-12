"""Change FPS Feature Core Code"""
import os
import argparse
import shutil
import math
from typing import Callable
from tqdm import tqdm
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, get_files
from webui_utils.simple_utils import restored_frame_searches, sortable_float_index

def main():
    """Use the Change FPS feature from the command line"""
    parser = argparse.ArgumentParser(description="Video Frame Interpolation - Upsample Video")
    parser.add_argument("--model", default="ours",
        type=str)
    parser.add_argument("--gpu_ids", type=str, default="0",
        help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)")
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path for PNGs to interpolate")
    parser.add_argument("--original_fps", default=25, type=int,
        help="Original FPS of PNG frames")
    parser.add_argument("--resampled_fps", default=100, type=int,
        help="Resampled FPS of new PNG frames")
    parser.add_argument("--depth", default=10, type=int,
        help="How deep the frame splits go to reach the target")
    parser.add_argument("--output_path", default="images", type=str,
        help="Output path for interpolated PNGs")
    parser.add_argument("--base_filename", default="upsampled_frames", type=str,
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
    series_resampler = ResampleSeries(interpolater, target_interpolater, args.time_step, log.log)

    series_resampler.resample_series(args.input_path, args.output_path, args.original_fps,
        args.resampled_fps, args.depth, args.base_filename)

class ResampleSeries():
    """Enscapsulate logic for the Change FPS feature"""
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

    def resample_series(self,
                        input_path : str,
                        output_path : str,
                        original_fps : int,
                        resampled_fps : int,
                        depth : int,
                        base_filename : str):
        "Invoke the Change FPS feature"
        lowest_common_rate = math.lcm(original_fps, resampled_fps)
        expanded_frames = int(lowest_common_rate / original_fps)
        filler_frames = expanded_frames - 1

        # set of needed frame times including original frames
        searches = [0.0] + restored_frame_searches(filler_frames)

        # PNG files found in the input path
        file_list = sorted(get_files(input_path, "png"))
        file_count = len(file_list)

        # superset of all files and all possible search times
        superset=[]
        for frame in range(file_count - 1):
            before_file = file_list[frame]
            after_file = file_list[frame + 1]
            for search in searches:
                superset.append({
                    "frame" : frame,
                    "before_file" : before_file,
                    "after_file" : after_file,
                    "search" : search})

        # sample the super set at the new frame rate
        sample_rate = int(lowest_common_rate / resampled_fps)
        sample_set = superset[::sample_rate]
        num_width = len(str(len(sample_set)))

        pbar_desc = "Resamples"
        for sample in tqdm(sample_set, desc=pbar_desc, position=0):
            frame = sample["frame"]
            before_file = sample["before_file"]
            after_file = sample["after_file"]
            search = sample["search"]
            frame_number = str(frame).zfill(num_width)

            if search == 0.0:
                filename = f"{base_filename}[{frame_number}]@0.0.png"
                output_filepath = os.path.join(output_path, filename)
                self.log(f"copying keyframe {before_file} to {output_filepath}")
                shutil.copy(before_file, output_filepath)
            else:
                if self.time_step:
                    filename = f"{base_filename}[{frame_number}]"
                    time = sortable_float_index(search)
                    output_filepath = os.path.join(output_path, f"{filename}@{time}.png")
                    self.log(f"rendering {output_filepath} from {before_file}")
                    self.interpolater.create_between_frame(before_file, after_file, output_filepath,
                                                           time_step=search)
                else:
                    self.log(f"searching {before_file} for frame time {search}")
                    filename = f"{base_filename}[{frame_number}]"
                    self.target_interpolater.split_frames(before_file,
                                                            after_file,
                                                            depth,
                                                            min_target=search,
                                                            max_target=search,
                                                            output_path=output_path,
                                                            base_filename=filename,
                                                            progress_label="Search")
        self.output_paths.extend(self.target_interpolater.output_paths)
        self.target_interpolater.output_paths = []

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
