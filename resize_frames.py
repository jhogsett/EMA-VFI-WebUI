"""Resize Frames Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory

def main():
    """Use the Resize Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Resize PNG files')
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to PNG files to resize")
    parser.add_argument("--output_path", default="images/resized", type=str,
        help="Output path for resized PNG files")
    parser.add_argument("--new_width", default=None, type=int,
        help="Resized image width (default=None)")
    parser.add_argument("--new_height", default=None, type=int,
        help="Resized image height (default=None)")
    parser.add_argument("--scale_type", default="lanczos", type=str,
        help="Scaling type 'lanczos' (default), 'nearest', 'linear', 'cubic', 'area'")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    ResizeFrames(args.input_path,
                 args.output_path,
                 args.new_width,
                 args.new_height,
                 args.scale_type,
                 log.log).resize()

class ResizeFrames:
    """Encapsulate logic for Resize Frames feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                new_width : int,
                new_height : int,
                scale_type : str,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.new_width = new_width
        self.new_height = new_height
        self.scale_type = scale_type
        self.log_fn = log_fn

    def get_scale_type(self, scale_type : str) -> int:
        try:
            return {
                "lanczos" : cv2.INTER_LANCZOS4,
                "nearest" : cv2.INTER_NEAREST,
                "linear" : cv2.INTER_LINEAR,
                "cubic" : cv2.INTER_CUBIC,
                "area" : cv2.INTER_AREA
            }[scale_type]
        except KeyError:
            raise ValueError(f"The type {scale_type} is unknown")

    def resize(self) -> None:
        """Invoke the Resize Frames feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")
        create_directory(self.output_path)
        scale_type = self.get_scale_type(self.scale_type)

        pbar_title = "Resizing"
        for file in tqdm(files, desc=pbar_title):
            self.log(f"resizing {file}")
            image = cv2.imread(file)
            size = (self.new_width, self.new_height)
            resized_image = cv2.resize(image, size, interpolation = scale_type)
            _, filename, ext = split_filepath(file)
            output_filepath = os.path.join(self.output_path, f"{filename}{ext}")
            self.log(f"saving resized file {output_filepath}")
            cv2.imwrite(output_filepath, resized_image)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
