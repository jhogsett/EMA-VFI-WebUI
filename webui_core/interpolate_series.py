"""Video Inflation Core Code"""
import argparse
from typing import Callable
from tqdm import tqdm
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from simple_log import SimpleLog
from file_utils import create_directory, get_files

def main():
    """Use Video Inflation from the command line"""
    parser = argparse.ArgumentParser(description="Video Frame Interpolation (deep)")
    parser.add_argument("--model",
        default="ours", type=str)
    parser.add_argument("--gpu_ids", type=str, default="0",
        help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU")
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path for PNGs to interpolate")
    parser.add_argument("--depth", default=2, type=int,
        help="How many doublings of the frames")
    parser.add_argument("--offset", default=1, type=int,
        help="Frame series offset, 1 for slow motion, 2+ for frame resynthesis")
    parser.add_argument("--output_path", default="images", type=str,
        help="Output path for interpolated PNGs")
    parser.add_argument("--base_filename", default="interpolated_frames", type=str,
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
    deep_interpolater = DeepInterpolate(interpolater, args.time_step, log.log)
    series_interpolater = InterpolateSeries(deep_interpolater, log.log)

    file_list = get_files(args.input_path, extension="png")
    series_interpolater.interpolate_series(file_list, args.output_path, args.depth,
        args.base_filename, args.offset)

class InterpolateSeries():
    """Encapsulate logic for the Video Inflation feature"""
    def __init__(self,
                deep_interpolater : DeepInterpolate,
                log_fn : Callable | None):
        self.deep_interpolater = deep_interpolater
        self.log_fn = log_fn

    def interpolate_series(self,
                            file_list : list,
                            output_path : str,
                            num_splits : int,
                            base_filename : str,
                            offset : int = 1):
        """Invoke the Video Inflation feature"""
        file_list = sorted(file_list)
        count = len(file_list)
        num_width = len(str(count))
        pbar_desc = "Frames" if num_splits < 2 else "Total"

        for frame in tqdm(range(count - offset), desc=pbar_desc, position=0):
            # for other than the first around, the duplicated real "before" frame is deleted for
            # continuity, since it's identical to the "after" from the previous round
            continued = frame > 0

            # if the offset is > 1 treat this as a resynthesis of frames
            # and inform the deep interpolator to not keep the real frames
            resynthesis = offset > 1

            before_file = file_list[frame]
            after_file = file_list[frame + offset]

            # if a resynthesis, start the file numbering at 1 to match the restored frame
            # if an offset other than 2 is used, the frame numbers won't generally match
            base_index = frame + (1 if resynthesis else 0)
            filename = base_filename + "[" + str(base_index).zfill(num_width) + "]"

            inner_bar_desc = f"Frame #{frame}"
            self.log(f"creating inflated frames for frame files {before_file} - {after_file}")
            self.deep_interpolater.split_frames(before_file, after_file, num_splits, output_path,
                filename, progress_label=inner_bar_desc, continued=continued,
                resynthesis=resynthesis)

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
