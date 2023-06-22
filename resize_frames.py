"""Resize Frames Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Resize Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Resize PNG files')
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to PNG files to resize")
    parser.add_argument("--output_path", default="images/resized", type=str,
        help="Output path for resized PNG files")

    parser.add_argument("--scale_width", default=None, type=int,
        help="Resized image width (default=None)")
    parser.add_argument("--scale_height", default=None, type=int,
        help="Resized image height (default=None)")
    parser.add_argument("--scale_type", default="lanczos", type=str,
        help="Scaling type 'lanczos' (default), 'nearest', 'linear', 'cubic', 'area', 'none'")

    parser.add_argument("--crop_width", default=-1, type=int,
        help="Cropped image width (default=-1 - same as scale width)")
    parser.add_argument("--crop_height", default=-1, type=int,
        help="Cropped image height (default=-1 - same as scale height)")
    parser.add_argument("--crop_offset_x", default=-1, type=int,
        help="Crop Area X Offset (default=-1 - auto centered)")
    parser.add_argument("--crop_offset_y", default=-1, type=int,
        help="Crop Area Y Offset (default=-1 - auto centered)")
    parser.add_argument("--crop_type", default="none", type=str,
        help="Cropping type 'crop' (default), 'none'")

    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    ResizeFrames(args.input_path,
                 args.output_path,
                 args.scale_width,
                 args.scale_height,
                 args.scale_type,
                 log.log,
                 args.crop_width,
                 args.crop_height,
                 args.crop_offset_x,
                 args.crop_offset_y,
                 args.crop_type,
                 ).resize()

class ResizeFrames:
    """Encapsulate logic for Resize Frames feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                scale_width : int,
                scale_height : int,
                scale_type : str,
                log_fn : Callable | None,
                crop_width : int=-1,
                crop_height : int=-1,
                crop_offset_x : int=-1,
                crop_offset_y : int=-1,
                crop_type : str="none"):
        self.input_path = input_path
        self.output_path = output_path
        self.scale_width = scale_width
        self.scale_height = scale_height
        self.scale_type = scale_type
        self.log_fn = log_fn
        self.crop_width = crop_width
        self.crop_height = crop_height
        self.crop_offset_x = crop_offset_x
        self.crop_offset_y = crop_offset_y
        self.crop_type = crop_type

    def get_scale_type(self, scale_type : str) -> int:
        try:
            return {
                "lanczos" : cv2.INTER_LANCZOS4,
                "nearest" : cv2.INTER_NEAREST,
                "linear" : cv2.INTER_LINEAR,
                "cubic" : cv2.INTER_CUBIC,
                "area" : cv2.INTER_AREA,
                "none" : None
            }[scale_type]
        except KeyError:
            raise ValueError(f"The scale type {scale_type} is unknown")

    def get_crop_type(self, crop_type : str) -> bool:
        try:
            return {
                "crop" : True,
                "none" : False
            }[crop_type]
        except KeyError:
            raise ValueError(f"The crop type {crop_type} is unknown")

    def resize(self) -> None:
        """Invoke the Resize Frames feature"""
        if not self.scale_width:
            raise ValueError("scale_width must be provided")
        if not self.scale_height:
            raise ValueError("scale_height must be provided")

        files = sorted(glob.glob(os.path.join(self.input_path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")
        create_directory(self.output_path)
        scale_type = self.get_scale_type(self.scale_type)
        crop_type = self.get_crop_type(self.crop_type)

        with Mtqdm().open_bar(len(files), desc="Resizing") as bar:
            for file in files:
                self.log(f"processing {file}")
                image = cv2.imread(file)

                if scale_type:
                    size = (self.scale_width, self.scale_height)
                    self.log(f"resizing {file} to {self.scale_width}x{self.scale_height}")
                    image = cv2.resize(image, size, interpolation = scale_type)

                if crop_type:
                    if self.crop_width < 0:
                        self.crop_width = self.scale_width
                    if self.crop_height < 0:
                        self.crop_height = self.scale_height
                    if self.crop_offset_x < 0:
                        self.crop_offset_x = int((self.scale_width - self.crop_width) / 2)
                    if self.crop_offset_y < 0:
                        self.crop_offset_y = int((self.scale_height - self.crop_height) / 2)
                    min_x = int(self.crop_offset_x)
                    min_y = int(self.crop_offset_y)
                    max_x = int(min_x + self.crop_width)
                    max_y = int(min_y + self.crop_height)

                    self.log(f"cropping {file} with [{min_y}:{max_y}, {min_x}:{max_x}]")
                    image = image[min_y:max_y, min_x:max_x]

                _, filename, ext = split_filepath(file)
                output_filepath = os.path.join(self.output_path, f"{filename}{ext}")
                self.log(f"saving resized file {output_filepath}")
                cv2.imwrite(output_filepath, image)
            Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
