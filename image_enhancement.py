"""Image Enhancement Feature Core Code"""
import os
import glob
import argparse
import cv2
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import split_filepath, create_directory
import numpy as np

def main():
    """Use the Split Channels feature from the command line"""
    parser = argparse.ArgumentParser(
        description=
        'Image Enhancement using Contrast Limited Adaptive Histogram Equalization')
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to PNG files to enhance")
    parser.add_argument("--output_path", default="images/enhanced", type=str,
        help="Base path for enhanced PNG files")
    parser.add_argument("--clip_limit", default=2.0, type=float,
                        help="Threshold value for contrast limiting (default 2.0)")
    parser.add_argument("--tile_grid_size", default=1, type=int,
                        help="Size of grid for histogram equalization (default 1 for full image)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    ImageEnhancement(args.input_path,
                     args.output_path,
                     args.clip_limit,
                     args.tile_grid_size,
                     log.log).enhance()

class ImageEnhancement:
    """Encapsulate logic for Split Channels feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                clip_limit : float,
                tile_grid_size : int,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self.log_fn = log_fn

    def enhance(self) -> None:
        """Invoke the Image Enhancement feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        create_directory(self.output_path)

        clahe = cv2.createCLAHE(
             clipLimit=self.clip_limit, tileGridSize=(self.tile_grid_size, self.tile_grid_size))

        pbar_title = "Enhancing"
        for file in tqdm(files, desc=pbar_title):
            self.log(f"enhancing {file}")
            img = cv2.imread(file)

            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            lab[...,0] = clahe.apply(lab[...,0])
            img_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            # simple, colors diverge
            # img_b = clahe_model.apply(img[:,:,0])
            # img_g = clahe_model.apply(img[:,:,1])
            # img_r = clahe_model.apply(img[:,:,2])
            # img_clahe = np.stack((img_b, img_g, img_r), axis=2)

            _, name, ext = split_filepath(file)
            new_file_path = os.path.join(self.output_path, name + ext)
            cv2.imwrite(new_file_path, img_clahe)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
