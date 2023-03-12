"""Resequence Files Featuer Core Code"""
import os
import shutil
import glob
import argparse
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog

def main():
    """Use the Resequence Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Resequence video frame PNG files')
    parser.add_argument("--path", default="./images", type=str,
        help="Path to files to resequence")
    parser.add_argument("--file_type", default="png", type=str,
        help="File type of the files to resequence")
    parser.add_argument("--new_name", default="pngsequence", type=str,
        help="New filename, default 'pngsequence'")
    parser.add_argument("--start", default=0, type=int,
        help="Starting index, default 0")
    parser.add_argument("--step", default=1, type=int,
        help="Index step, default is 1")
    parser.add_argument("--zero_fill", default=-1, type=int,
        help="Zero-filled width of new frame IDs, -1 = auto")
    parser.add_argument("--rename", dest="rename", default=False, action="store_true",
        help="Rename rather than copy files")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    ResequenceFiles(args.path, args.file_type, args.new_name, args.start, args.step,
        args.zero_fill, args.rename, log.log).resequence()

class ResequenceFiles:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                path : str,
                file_type : str,
                new_base_filename : str,
                start_index : int,
                index_step : int,
                zero_fill : int,
                rename : bool ,
                log_fn : Callable | None):
        self.path = path
        self.file_type = file_type
        self.new_base_filename = new_base_filename
        self.start_index = start_index
        self.index_step = index_step
        self.zero_fill = zero_fill
        self.rename = rename
        self.log_fn = log_fn

    def resequence(self) -> None:
        """Invoke the Resequence Files feature"""
        files = sorted(glob.glob(os.path.join(self.path, "*." + self.file_type)))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        max_file_num = num_files * self.index_step
        num_width = len(str(max_file_num)) if self.zero_fill < 0 else self.zero_fill
        index = self.start_index
        pbar_title = "Renaming" if self.rename else "Copying"

        for file in tqdm(files, desc=pbar_title):
            new_filename = self.new_base_filename + str(index).zfill(num_width) + "." +\
                self.file_type
            old_filepath = file
            new_filepath = os.path.join(self.path, new_filename)

            if self.rename:
                os.replace(old_filepath, new_filepath)
                self.log(f"File {file} renamed to {new_filename}")
            else:
                shutil.copy(old_filepath, new_filepath)
                self.log(f"File {file} copied to {new_filename}")

            index += self.index_step

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
