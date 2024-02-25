"""Image Enhancement Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory
import numpy as np
from webui_utils.mtqdm import Mtqdm

def main():
    """Use the Split Channels feature from the command line"""
    parser = argparse.ArgumentParser(
        description=
        'Image Enhancement using Contrast Limited Adaptive Histogram Equalization')
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to image files to enhance")
    parser.add_argument("--output_path", default="images/enhanced", type=str,
        help="Base path for enhanced image files")
    parser.add_argument("--clip_limit", default=2.0, type=float,
                        help="Threshold value for contrast limiting (default 2.0)")
    parser.add_argument("--tile_grid_size", default=1, type=int,
                        help="Size of grid for histogram equalization (default 1 for full image)")
    parser.add_argument("--type", default="png", type=str,
                        help="File type for frame files (Default 'png')")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    ImageEnhancement(args.input_path,
                     args.output_path,
                     args.clip_limit,
                     log.log,
                     tile_grid_size=args.tile_grid_size).enhance(type=args.type)

class ImageEnhancement:
    """Encapsulate logic for Split Channels feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                clip_limit : float,
                log_fn : Callable | None,
                tile_grid_size : int=1):
        self.input_path = input_path
        self.output_path = output_path
        self.clip_limit = clip_limit
        self.log_fn = log_fn
        self.tile_grid_size = tile_grid_size

    def enhance(self, type : str="png") -> None:
        """Invoke the Image Enhancement feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, "*." + type)))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        create_directory(self.output_path)

        clahe = cv2.createCLAHE(
             clipLimit=self.clip_limit, tileGridSize=(self.tile_grid_size, self.tile_grid_size))

        with Mtqdm().open_bar(total=num_files, desc="Enhancing") as bar:
            for file in files:
                self.log(f"enhancing {file}")
                img = cv2.imread(file)

                # RGB - don't use - simple, but colors diverge
                # img_b = clahe_model.apply(img[:,:,0])
                # img_g = clahe_model.apply(img[:,:,1])
                # img_r = clahe_model.apply(img[:,:,2])
                # img_clahe = np.stack((img_b, img_g, img_r), axis=2)

                # LAB - don't use - works but seems too sensitive to blue
                # lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                # lab[...,0] = clahe.apply(lab[...,0])
                # img_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

                # HSL - best overall results
                hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS_FULL)
                hls[...,1] = clahe.apply(hls[...,1])
                img_clahe = cv2.cvtColor(hls, cv2.COLOR_HLS2BGR_FULL)

                _, name, ext = split_filepath(file)
                new_file_path = os.path.join(self.output_path, name + ext)
                cv2.imwrite(new_file_path, img_clahe)
                Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
