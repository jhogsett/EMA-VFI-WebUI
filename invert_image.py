"""Invert Image Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory

def main():
    """Use the Invert Image feature from the command line"""
    parser = argparse.ArgumentParser(description='Invert PNG image files')
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to PNG files to invert")
    parser.add_argument("--output_path", default="images/inverted", type=str,
        help="Output path inverted images")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    InvertImage(args.input_path, args.output_path, log.log).invert()

class InvertImage:
    """Encapsulate logic for Invert Image feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.log_fn = log_fn

    def invert(self) -> None:
        """Invoke the Ivert Image feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")
        create_directory(self.output_path)

        pbar_title = "Inverting"
        for file in tqdm(files, desc=pbar_title):
            self.log(f"inverting {file}")

            img = cv2.imread(file)
            img = cv2.bitwise_not(img)

            _, filename, ext = split_filepath(file)
            new_file_path = os.path.join(self.output_path, filename + ext)
            cv2.imwrite(new_file_path, img)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
