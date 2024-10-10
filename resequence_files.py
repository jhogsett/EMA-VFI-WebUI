"""Resequence Files Feature Core Code"""
import os
import shutil
import glob
import argparse
import re
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.simple_utils import create_sample_set
from webui_utils.mtqdm import Mtqdm
from webui_utils.file_utils import get_directories, check_for_name_clash, get_files

def main():
    """Use the Resequence Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Resequence video frame PNG files')
    parser.add_argument("--input_path", default="./images", type=str,
        help="Path to files to resequence")
    parser.add_argument("--output_path", default="", type=str,
        help="Path to store resequenced files (leave blank to use input path)")
    parser.add_argument("--file_type", default="png", type=str,
        help="File type of the files to resequence")
    parser.add_argument("--new_name", default="pngsequence", type=str,
        help="New filename, default 'pngsequence'")
    parser.add_argument("--start", default=0, type=int,
        help="Starting running_index, default 0")
    parser.add_argument("--step", default=1, type=int,
        help="Index step, default is 1")
    parser.add_argument("--stride", default=1, type=int,
        help="Sampling stride, default 1 (sample each 1 file(s))")
    parser.add_argument("--offset", default=0, type=int,
        help="Sampling offset, default 0 (sample starting with 0th file)")
    parser.add_argument("--zero_fill", default=-1, type=int,
        help="Zero-filled width of new frame IDs, -1 = auto")
    parser.add_argument("--rename", dest="rename", default=False, action="store_true",
        help="Rename rather than copy files")
    parser.add_argument("--reverse", dest="reverse", default=False, action="store_true",
        help="Sample files in reverse order")
    parser.add_argument("--batch", dest="batch", default=False, action="store_true",
        help="Resequence files in directories at input path")
    parser.add_argument("--contiguous", dest="contiguous", default=False, action="store_true",
        help="Use sequential index numbering across batch")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    sequencer = ResequenceFiles(args.input_path,
                    args.file_type,
                    args.new_name,
                    args.start,
                    args.step,
                    args.stride,
                    args.offset,
                    args.zero_fill,
                    args.rename,
                    log.log,
                    args.output_path,
                    args.reverse)

    if args.batch:
        sequencer.resequence_batch(contiguous=args.contiguous)
    else:
        sequencer.resequence()

class ResequenceFiles:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                input_path : str,
                file_type : str,
                new_base_filename : str,
                start_index : int,
                index_step : int,
                sample_stride: int,
                sample_offset: int,
                zero_fill : int,
                rename : bool ,
                log_fn : Callable | None,
                output_path : str | None=None,
                reverse=False):
        self.input_path = input_path
        self.file_type = file_type
        self.new_base_filename = new_base_filename
        self.start_index = start_index
        self.index_step = index_step
        self.sample_stride = sample_stride if sample_stride > 0 else 1
        self.sample_offset = sample_offset if sample_offset >= 0 else 0
        self.zero_fill = zero_fill
        self.rename = rename
        self.reverse = reverse
        self.log_fn = log_fn
        self.output_path = output_path or input_path

    ZERO_FILL_AUTO_DETECT = -1

    def resequence_groups(self, group_names : list, contiguous=True, ignore_name_clash=True):
        """Resequence files contained in the specified directory names at the input path. Returns a string with any errors."""
        all_files_count = 0
        for group_name in group_names:
            check_path = self.input_path if self.rename else self.output_path
            group_check_path = os.path.join(check_path, group_name)
            try:
                group_files = glob.glob(os.path.join(group_check_path, "*." + self.file_type))
                all_files_count += len(group_files)
                if not ignore_name_clash:
                    check_for_name_clash(group_files, self.file_type, self.new_base_filename)
            except ValueError as error:
                return str(error)

        if self.zero_fill == ResequenceFiles.ZERO_FILL_AUTO_DETECT:
            max_index_num = all_files_count * self.index_step
            batch_zero_fill = len(str(max_index_num))
        else:
            batch_zero_fill = self.zero_fill

        errors = []
        if group_names:
            with Mtqdm().open_bar(total=len(group_names), desc="Resequence Groups") as bar:
                running_start = self.start_index
                for group_name in group_names:
                    group_input_path = os.path.join(self.input_path, group_name)
                    group_output_path = os.path.join(self.output_path, group_name)
                    try:
                        if contiguous:
                            group_start = running_start
                            group_files = get_files(group_input_path, self.file_type)
                            running_start += len(group_files)
                        else:
                            group_start = self.start_index

                        ResequenceFiles(
                            group_input_path,
                            self.file_type,
                            self.new_base_filename,
                            group_start,
                            self.index_step,
                            self.sample_stride,
                            self.sample_offset,
                            batch_zero_fill,
                            self.rename,
                            self.log_fn,
                            group_output_path,
                            self.reverse).resequence(ignore_name_clash=ignore_name_clash,
                                                     skip_if_not_required=False)
                    except ValueError as error:
                        errors.append(f"Error handling directory {group_name}: " + str(error))
                    Mtqdm().update_bar(bar)
        if errors:
            return "\r\n".join(errors)

    def resequence_batch(self, contiguous=True, ignore_name_clash=True):
        """Resequence groups of files. Returns a string with any errors."""
        group_names = sorted(get_directories(self.input_path), reverse=self.reverse)
        return self.resequence_groups(group_names,
                                      contiguous=contiguous,
                                      ignore_name_clash=ignore_name_clash)

    def resequence(self, ignore_name_clash=True, skip_if_not_required=True) -> None:
        """Resesequence files in the directory per settings. Returns a count of the files resequenced. Raises ValueError on name clash."""
        files = sorted(glob.glob(os.path.join(self.input_path, "*." + self.file_type)),
                       reverse=self.reverse)
        num_files = len(files)

        # if renaming files in place, check to see that they are not already in proper sequence
        if self.rename and skip_if_not_required:
            required, messages = self.required()
            for message in messages:
                self.log(message)
            if not required:
                self.log(f"skipping resequencing as not required per skip_if_not_required=True")
                return

        if not ignore_name_clash:
            check_for_name_clash(files, self.new_base_filename, self.file_type)

        if self.zero_fill == self.ZERO_FILL_AUTO_DETECT:
            max_file_num = num_files * self.index_step
            num_width = len(str(max_file_num))
        else:
            num_width = self.zero_fill

        running_index = self.start_index
        sample_set = create_sample_set(files, self.sample_offset, self.sample_stride)
        pbar_title = "Resequence Rename" if self.rename else "Resequence Copy"
        with Mtqdm().open_bar(total=len(sample_set), desc=pbar_title) as bar:
            for file in sample_set:
                new_filename = \
                    self.new_base_filename + str(running_index).zfill(num_width) + "." + self.file_type
                old_filepath = file

                if self.rename:
                    new_filepath = os.path.join(self.input_path, new_filename)
                    if old_filepath != new_filepath:
                        os.replace(old_filepath, new_filepath)
                else:
                    new_filepath = os.path.join(self.output_path, new_filename)
                    shutil.copy(old_filepath, new_filepath)

                running_index += self.index_step
                Mtqdm().update_bar(bar)

    # before reqsequencing, check if the file set is already properly sequenced:
    # - determine number width/positions based on file count
    # - check that all files have only digits in the final number positions
    # - and that they are all zero-filled
    # - check that the first file is all zeroes or starts with one
    # - and record whether the origin is 0 or 1
    # - check that the last file equals the count of files (origin == 1) or count-1 (origin == 0)
    # - check that there are no extra files
    # - check that there are no missing files
    # - check that there are no duplicate files
    # - check that all integer positions are covered
    # - check that the portion ahead of the number positions is identical for all files

    def _required_get_file_index(self, num_width, filename):
        test = f"(.*)(\d{{{num_width}}})\.(.*)"
        matches = re.search(test, filename)
        index = matches[2]
        try:
            return int(index)
        except Exception:
            raise ValueError(f"unable to determine index for file {filename}")

    def required(self):
        messages = ["ResequenceFiles.reuired() check"]
        files = sorted(glob.glob(os.path.join(self.input_path, "*." + self.file_type)),
                       reverse=self.reverse)
        num_files = len(files)
        if not num_files:
            messages.append(f"directory {self.input_path} contains no files of type {self.file_type}")
            return False, messages

        num_width = len(str(num_files))
        origin = 0
        first_file = files[0]
        last_file = files[-1]

        messages.append("check for starting file index being zero or one")
        try:
            index = self._required_get_file_index(num_width, first_file)
            if index == 0:
                origin = 0
            elif index == 1:
                origin = 1
            else:
                messages.append("zero or one index starting file not found")
                return True, messages
        except Exception as error:
            messages.append(str(error))
            return True, messages

        last_valid_index = ((num_files - 1) + origin)

        messages.append(f"checking for ending file index being {last_valid_index}")
        try:
            index = self._required_get_file_index(num_width, last_file)
            if index != last_valid_index:
                messages.append(f"{last_valid_index} ending file not found")
                return True, messages
        except Exception as error:
            messages.append(str(error))
            return True, messages

        messages.append("scan files for invalid missing, duplicate or invalid indexes")
        next_valid_index = origin
        for file in files[1:-1]:
            next_valid_index += 1
            try:
                index = self._required_get_file_index(num_width, file)
                if index != next_valid_index:
                    messages.append(f"next valid file index {next_valid_index} not found")
                    return True, messages
            except Exception as error:
                messages.append(str(error))
                return True, messages

        messages.append("Resequencing not required")
        return False, messages

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
