"""Frame Search Feature Core Code"""
import os
import shutil
import argparse
from typing import Callable
import re
import cv2
from tqdm import tqdm
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from webui_utils.simple_log import SimpleLog
from webui_utils.simple_utils import float_range_in_range, sortable_float_index
from webui_utils.file_utils import create_directory

def main():
    """Use the Frame Search feature from the command line"""
    parser = argparse.ArgumentParser(description="Video Frame Interpolation to a specify time")
    parser.add_argument("--model",
        default="ours", type=str)
    parser.add_argument("--gpu_ids", type=str, default="0",
        help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)")
    parser.add_argument("--img_before", default="images/image0.png", type=str,
        help="Path to before frame image")
    parser.add_argument("--img_after", default="images/image2.png", type=str,
        help="Path to after frame image")
    parser.add_argument("--depth", default=10, type=int,
        help="How deep the frame splits go to reach the target")
    parser.add_argument("--min_target", default=0.333, type=float,
        help="Lower bound of target time")
    parser.add_argument("--max_target", default=0.334, type=float,
        help="Upper bound of target time")
    parser.add_argument("--output_path", default="images", type=str,
        help="Output path for interpolated PNGs")
    parser.add_argument("--base_filename", default="interpolated_frame", type=str,
        help="Base filename for interpolated PNGs")
    parser.add_argument("--keep_samples", dest="keep_samples", default=False, action="store_true",
        help="Keep the interative sample PNGs (Default: False)")
    parser.add_argument("--time_step", dest="time_step", default=False, action="store_true",
        help="Use Time Step instead of Binary Search interpolation (Default: False)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details (Default: False)")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    create_directory(args.output_path)

    if args.time_step:
        # use the time step feature of the model to reach the midpoint of the target range
        engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step=True)
        interpolater = Interpolate(engine.model, log.log)
        midpoint = args.min_target + (args.max_target - args.min_target) / 2.0
        img_new = os.path.join(args.output_path, f"{args.base_filename}@{midpoint}.png")
        interpolater.create_between_frame(args.img_before, args.img_after, img_new, midpoint)
    else:
        # use binary search interpolation to reach the target range
        engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step=False)
        interpolater = Interpolate(engine.model, log.log)
        target_interpolater = TargetInterpolate(interpolater, log.log)
        target_interpolater.split_frames(args.img_before, args.img_after, args.depth,
                                         args.min_target, args.max_target, args.output_path,
                                         args.base_filename, args.keep_samples)

class TargetInterpolate():
    """Enscapsulate logic for the Frame Search feature"""
    def __init__(self,
                interpolater : Interpolate,
                log_fn : Callable | None):
        self.interpolater = interpolater
        self.log_fn = log_fn
        self.split_count = 0
        self.frame_register = []
        self.progress = None
        self.output_paths = []

    def split_frames(self,
                    before_filepath : str,
                    after_filepath : str,
                    num_splits : int,
                    min_target : float,
                    max_target : float,
                    output_path : str,
                    base_filename : str,
                    keep_samples=False,
                    progress_label="Split"):
        """Invoke the Frame Search feature"""
        self.init_frame_register()
        self.reset_split_manager(num_splits)
        self.init_progress(num_splits, num_splits, progress_label)

        output_filepath_prefix = os.path.join(output_path, base_filename)
        self._set_up_outer_frames(before_filepath, after_filepath, output_filepath_prefix)
        self._recursive_split_frames(0.0, 1.0, output_filepath_prefix, min_target, max_target)
        self._isolate_target_frame(keep_samples)
        self.close_progress()

    def _set_up_outer_frames(self,
                            before_file,
                            after_file,
                            output_filepath_prefix):
        """Start with the original frames at 0.0 and 1.0"""
        img0 = cv2.imread(before_file)
        img1 = cv2.imread(after_file)

        # create outer 0.0 and 1.0 versions of original frames
        before_index, after_index = 0.0, 1.0
        before_file = self.indexed_filepath(output_filepath_prefix, before_index)
        after_file = self.indexed_filepath(output_filepath_prefix, after_index)

        cv2.imwrite(before_file, img0)
        self.register_frame(before_file)
        self.log("copied " + before_file)

        cv2.imwrite(after_file, img1)
        self.register_frame(after_file)
        self.log("copied " + after_file)

    def _recursive_split_frames(self,
                                first_index : float,
                                last_index : float,
                                filepath_prefix : str,
                                min_target : float,
                                max_target : float):
        """Create a new frame between the given frames, and re-enter to split deeper"""
        if self.enter_split():
            mid_index = first_index + (last_index - first_index) / 2.0
            first_filepath = self.indexed_filepath(filepath_prefix, first_index)
            last_filepath = self.indexed_filepath(filepath_prefix, last_index)
            mid_filepath = self.indexed_filepath(filepath_prefix, mid_index)

            self.interpolater.create_between_frame(first_filepath, last_filepath, mid_filepath)
            self.register_frame(mid_filepath)
            self.step_progress()

            # no more work if the mid point entirely within the target range
            if float_range_in_range(mid_index, mid_index, min_target, max_target):
                self.log("skipping, current split range " + f"{mid_index}"
                    + " is inside target range " + f"{min_target},{max_target}")
            else:
                # recurse into the half that gets closer to the target range
                if float_range_in_range(min_target, max_target, first_index, mid_index,
                    use_midpoint=True):
                    self._recursive_split_frames(first_index, mid_index, filepath_prefix,
                        min_target, max_target)
                elif float_range_in_range(min_target, max_target, mid_index, last_index,
                    use_midpoint=True):
                    self._recursive_split_frames(mid_index, last_index, filepath_prefix,
                        min_target, max_target)
                else:
                    self.log("skipping, unable to locate target "+ f"{min_target},{max_target}"
                        + " within split ranges " + f"{first_index},{mid_index}" + " and "
                        + "{mid_index},{last_index}")
            self.exit_split()

    def _isolate_target_frame(self, keep_samples : bool):
        """Keep the found frame after the search process, optionally keep the work frames"""
        frame_files = self.registered_frames()

        # the found frame will be the last frame registered
        if keep_samples:
            found_file = frame_files[-1]
        else:
            found_file = frame_files.pop(-1)

        filepath, fvalue, ext = self.split_indexed_filepath(found_file)
        float_index = sortable_float_index(fvalue)
        new_found_file = f"{filepath}@{float_index}{ext}"

        if keep_samples:
            self.log("copying " + found_file + " to " + new_found_file)
            shutil.copy(found_file, new_found_file)
        else:
            self.log("renaming " + found_file + " to " + new_found_file)
            os.replace(found_file, new_found_file)
        self.output_paths.append(new_found_file)

        if keep_samples:
            for file in frame_files:
                self.output_paths.append(file)
        else:
            # duplicates may have been registered
            frame_files = [file for file in frame_files if file != found_file]
            frame_files = list(set(frame_files))
            for file in frame_files:
                self.log("removing uneeded " + file)
                os.remove(file)

    def reset_split_manager(self, num_splits : int):
        """Start managing split depths of a new round of searches"""
        self.split_count = num_splits

    def enter_split(self):
        """Enter a split depth if allowed, returns True if so"""
        if self.split_count < 1:
            return False
        self.split_count -= 1
        return True

    def exit_split(self):
        """Exit the current split depth"""
        self.split_count += 1

    def init_frame_register(self):
        """Start managing interpolated frame files for a new round of searches"""
        self.frame_register = []

    def register_frame(self, filepath : str):
        """Register a found frame file"""
        self.frame_register.append(filepath)

    def registered_frames(self):
        """Return a list of the currently registered found frame files"""
        return self.frame_register

    def sorted_registered_frames(self):
        """Return a sorted list of the currently registered found frame files"""
        return sorted(self.frame_register)

    def init_progress(self, num_splits, _max, description):
        """Start managing progress bar for a new found of searches"""
        if num_splits < 2:
            self.progress = None
        else:
            self.progress = tqdm(range(_max), desc=description)

    def step_progress(self):
        """Advance the progress bar"""
        if self.progress:
            self.progress.update()
            self.progress.refresh()

    def close_progress(self):
        """Done with the progress bar"""
        if self.progress:
            self.progress.close()

    def indexed_filepath(self, filepath_prefix, index):
        """Filepath prefix representing the split position while splitting"""
        float_index = sortable_float_index(index)
        return filepath_prefix + f"{float_index}.png"

    def split_indexed_filepath(self, filepath : str):
        """Split an indexed filepath, return filename, index, extension"""
        regex = r"(.+)([1|0]\..+)(\..+$)"
        result = re.search(regex, filepath)
        if result:
            file_part = result.group(1)
            float_part = result.group(2)
            ext_part = result.group(3)
            return file_part, float(float_part), ext_part
        self.log("unable to split indexed filepath {filepath}")
        return None, 0.0, None

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
