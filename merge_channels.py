"""Merge Channels Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory

def main():
    """Use the Split Channels feature from the command line"""
    parser = argparse.ArgumentParser(description='Split channels of PNG files')
    parser.add_argument("--input_path", default="images/channels", type=str,
        help="Base path for input channel directories")
    parser.add_argument("--output_path", default="images/merged", type=str,
        help="Output path for merged PNG files")
    parser.add_argument("--type", default="rgb", type=str,
        help="Merge type 'rgb' (default) or 'hsl'")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    MergeChannels(args.input_path, args.output_path, args.type, log.log).merge()

class MergeChannels:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                type : str,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.type = type
        self.log_fn = log_fn

    def merge(self) -> None:
        """Invoke the Merge Channels feature"""
        create_directory(self.output_path)
        merge_hsl = self.type.startswith("hsl")

        if merge_hsl:
            hue_path = os.path.join(self.input_path, "H")
            sat_path = os.path.join(self.input_path, "S")
            light_path = os.path.join(self.input_path, "L")

            if not os.path.exists(hue_path):
                raise ValueError(f"Path {hue_path} not found")
            if not os.path.exists(sat_path):
                raise ValueError(f"Path {sat_path} not found")
            if not os.path.exists(light_path):
                raise ValueError(f"Path {light_path} not found")

            hue_files = sorted(glob.glob(os.path.join(hue_path, "*.png")))
            sat_files = sorted(glob.glob(os.path.join(sat_path, "*.png")))
            light_files = sorted(glob.glob(os.path.join(light_path, "*.png")))

            if not len(hue_files) == len(sat_files) == len(light_files):
                raise ValueError(
                    f"Subdirectories of {self.input_path} must have the same file count")

            num_files = len(hue_files)
            if num_files < 1:
                raise ValueError(f"Subdirectories of {self.input_path} must contain files")
            self.log(f"Found {num_files} files")

            pbar_title = "Merging"
            for index, file in enumerate(tqdm(hue_files, desc=pbar_title)):
                hue_img = cv2.imread(hue_files[index], cv2.IMREAD_GRAYSCALE)
                sat_img = cv2.imread(sat_files[index], cv2.IMREAD_GRAYSCALE)
                light_img = cv2.imread(light_files[index], cv2.IMREAD_GRAYSCALE)
                merged = cv2.merge([hue_img, light_img, sat_img])
                merged_rgb = cv2.cvtColor(merged, cv2.COLOR_HLS2BGR_FULL)
                _, file, ext = split_filepath(file)
                new_file_path = os.path.join(self.output_path, file + ext)
                cv2.imwrite(new_file_path, merged_rgb)
        else:
            red_path = os.path.join(self.input_path, "R")
            green_path = os.path.join(self.input_path, "G")
            blue_path = os.path.join(self.input_path, "B")

            if not os.path.exists(red_path):
                raise ValueError(f"Path {red_path} not found")
            if not os.path.exists(green_path):
                raise ValueError(f"Path {green_path} not found")
            if not os.path.exists(blue_path):
                raise ValueError(f"Path {blue_path} not found")

            red_files = sorted(glob.glob(os.path.join(red_path, "*.png")))
            green_files = sorted(glob.glob(os.path.join(green_path, "*.png")))
            blue_files = sorted(glob.glob(os.path.join(blue_path, "*.png")))

            if not len(red_files) == len(green_files) == len(blue_files):
                raise ValueError(
                    f"Subdirectories of {self.input_path} must have the same file count")

            num_files = len(red_files)
            if num_files < 1:
                raise ValueError(f"Subdirectories of {self.input_path} must contain files")
            self.log(f"Found {num_files} files")

            pbar_title = "Merging"
            for index, file in enumerate(tqdm(red_files, desc=pbar_title)):
                red_img = cv2.imread(red_files[index], cv2.IMREAD_GRAYSCALE)
                green_img = cv2.imread(green_files[index], cv2.IMREAD_GRAYSCALE)
                blue_img = cv2.imread(blue_files[index], cv2.IMREAD_GRAYSCALE)
                merged = cv2.merge([blue_img, green_img, red_img])
                _, file, ext = split_filepath(file)
                new_file_path = os.path.join(self.output_path, file + ext)
                cv2.imwrite(new_file_path, merged)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
