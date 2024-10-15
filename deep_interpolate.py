"""Frame Interpolation Core Code"""
import os
import argparse
from typing import Callable
import cv2
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from webui_utils.simple_log import SimpleLog
from webui_utils.simple_utils import max_steps, sortable_float_index
from webui_utils.file_utils import create_directory
from webui_utils.mtqdm import Mtqdm

def main():
    """Use Frame Interpolation from the command line"""
    parser = argparse.ArgumentParser(description="Video Frame Interpolation (deep)")
    parser.add_argument("--model",
        default="ours", type=str)
    parser.add_argument("--gpu_ids", type=str, default="0",
        help="gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU")
    parser.add_argument("--img_before", default="images/image0.png", type=str,
        help="Path to before frame image")
    parser.add_argument("--img_after", default="images/image2.png", type=str,
        help="Path to after frame image")
    parser.add_argument("--depth", default=2, type=int,
        help="how many doublings of the frames")
    parser.add_argument("--output_path", default="images", type=str,
        help="Output path for interpolated PNGs")
    parser.add_argument("--base_filename", default="interpolated_frame", type=str,
        help="Base filename for interpolated PNGs")
    parser.add_argument("--time_step", dest="time_step", default=False, action="store_true",
        help="Use Time Step instead of Binary Search interpolation (Default: False)")
    parser.add_argument("--type", default="png", type=str,
                        help="File type for frame files (Default 'png')")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    create_directory(args.output_path)
    engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step=args.time_step)
    interpolater = Interpolate(engine.model, log.log)
    deep_interpolater = DeepInterpolate(interpolater, args.time_step, log.log)
    deep_interpolater.split_frames(args.img_before,
                                   args.img_after,
                                   args.depth,
                                   args.output_path,
                                   args.base_filename,
                                   type=args.type)

class DeepInterpolate():
    """Encapsulates logic for the Frame Interpolation feature"""
    def __init__(self,
                interpolater : Interpolate,
                time_step : bool,
                log_fn : Callable | None):
        self.interpolater = interpolater
        self.time_step = time_step
        self.log_fn = log_fn
        self.split_count = 0
        self.frame_register = []
        self.progress = None
        self.output_paths = []

    def split_frames(self,
                    before_filepath,
                    after_filepath,
                    num_splits,
                    output_path,
                    base_filename,
                    progress_label="Frame",
                    continued=False,
                    resynthesis=False,
                    type : str="png"):
        """Invoke the Frame Interpolation feature"""
        self.init_frame_register()
        self.reset_split_manager(num_splits)
        num_steps = max_steps(num_splits)
        self.init_progress(num_splits, num_steps, progress_label)
        output_filepath_prefix = os.path.join(output_path, base_filename)

        if self.time_step:
            self.interpolater.create_between_frames(before_filepath, after_filepath,
                                                    output_filepath_prefix, num_steps)
            for path in self.interpolater.output_paths:
                self.register_frame(path)
            self.interpolater.output_paths = []
        else:
            self._set_up_outer_frames(before_filepath, after_filepath, output_filepath_prefix, type)
            self._recursive_split_frames(0.0, 1.0, output_filepath_prefix, type)
        self._integerize_filenames(output_path, base_filename, continued, resynthesis, type)
        self.close_progress()

    def _set_up_outer_frames(self,
                            before_file : str,
                            after_file : str,
                            output_filepath_prefix : str,
                            type : str):
        """Start with the original frames at 0.0 and 1.0"""
        img0 = cv2.imread(before_file)
        img1 = cv2.imread(after_file)

        # create outer 0.0 and 1.0 versions of original frames
        before_index, after_index = 0.0, 1.0
        before_file = self.indexed_filepath(output_filepath_prefix, before_index, type)
        after_file = self.indexed_filepath(output_filepath_prefix, after_index, type)

        cv2.imwrite(before_file, img0)
        self.register_frame(before_file)
        # self.log("copied " + before_file)

        cv2.imwrite(after_file, img1)
        self.register_frame(after_file)
        # self.log("copied " + after_file)

    def _recursive_split_frames(self,
                                first_index : float,
                                last_index : float,
                                filepath_prefix : str,
                                type : str):
        """Create a new frame between the given frames, and re-enter to split deeper"""
        if self.enter_split():
            mid_index = first_index + (last_index - first_index) / 2.0
            first_filepath = self.indexed_filepath(filepath_prefix, first_index, type)
            last_filepath = self.indexed_filepath(filepath_prefix, last_index, type)
            mid_filepath = self.indexed_filepath(filepath_prefix, mid_index, type)

            self.interpolater.create_between_frame(first_filepath, last_filepath, mid_filepath)
            self.register_frame(mid_filepath)
            self.step_progress()

            # deal with two new split regions
            self._recursive_split_frames(first_index, mid_index, filepath_prefix, type)
            self._recursive_split_frames(mid_index, last_index, filepath_prefix, type)
            self.exit_split()

    def _integerize_filenames(self, output_path, base_name, continued, resynthesis, type):
        """Keep the interpolated frame files with an index number for sorting"""
        file_prefix = os.path.join(output_path, base_name)
        frame_files = self.sorted_registered_frames()
        num_files = len(frame_files)
        num_width = len(str(num_files))
        index = 0
        self.output_paths = []

        for file in frame_files:
            if resynthesis and (index == 0 or index == num_files - 1):
                # if a resynthesis process, keep only the interpolated frames
                os.remove(file)
                # self.log("resynthesis - removed uneeded " + file)
            elif continued and index == 0:
                # if a continuation from a previous set of frames, delete the first frame
                # to maintain continuity since it's duplicate of the previous round last frame
                os.remove(file)
                # self.log("continuation - removed uneeded " + file)
            else:
                new_filename = file_prefix + str(index).zfill(num_width) + "." + type
                os.replace(file, new_filename)
                self.output_paths.append(new_filename)
                # self.log("renamed " + file + " to " + new_filename)
            index += 1

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

    def sorted_registered_frames(self):
        """Return a sorted list of the currently registered found frame files"""
        return sorted(self.frame_register)

    def init_progress(self, num_splits, _max, description):
        """Start managing progress bar for a new found of searches"""
        if num_splits < 2:
            self.progress = None
        else:
            self.progress = Mtqdm().enter_bar(total=_max, desc=description)

    def step_progress(self):
        """Advance the progress bar"""
        if self.progress:
            Mtqdm().update_bar(self.progress)

    def close_progress(self):
        """Done with the progress bar"""
        if self.progress:
            Mtqdm().leave_bar(self.progress)

    # filepath prefix representing the split position while splitting
    def indexed_filepath(self, filepath_prefix, index, type : str="png"):
        """Filepath prefix representing the split position while splitting"""
        float_index = sortable_float_index(index, fixed_width=True)
        return filepath_prefix + f"{float_index}.{type}"

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
