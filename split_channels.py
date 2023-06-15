"""Split Channels Feature Core Code"""
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
    parser.add_argument("--input_path", default="images", type=str,
        help="Input path to PNG files to split")
    parser.add_argument("--output_path", default="images/channels", type=str,
        help="Base path for output channel directories")
    parser.add_argument("--type", default="rgb", type=str,
        help="Split type 'rgb' (default) or 'hsl'")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SplitChannels(args.input_path, args.output_path, args.type, log.log).split()

class SplitChannels:
    """Encapsulate logic for Split Channels feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                type : str,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.type = type
        self.log_fn = log_fn

    def save_channel(self, img, channel, file_path):
        _, name, ext = split_filepath(file_path)
        new_file_path = os.path.join(self.output_path, channel, name + ext)
        cv2.imwrite(new_file_path, img)

    def split(self) -> None:
        """Invoke the Split Channels feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")
        create_directory(self.output_path)
        split_hsl = self.type.startswith("hsl")
        if split_hsl:
            create_directory(os.path.join(self.output_path, "H"))
            create_directory(os.path.join(self.output_path, "S"))
            create_directory(os.path.join(self.output_path, "L"))
        else:
            create_directory(os.path.join(self.output_path, "R"))
            create_directory(os.path.join(self.output_path, "G"))
            create_directory(os.path.join(self.output_path, "B"))

        pbar_title = "Splitting"
        for file in tqdm(files, desc=pbar_title):
            self.log(f"splitting channels from {file}")

            if split_hsl:
                img = cv2.imread(file)
                img_hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS_FULL)
                hue, light, sat = cv2.split(img_hls)
                self.save_channel(hue, "H", file)
                self.save_channel(light, "L", file)
                self.save_channel(sat, "S", file)
            else:
                img = cv2.imread(file)
                blue, green, red = cv2.split(img)
                self.save_channel(blue, "B", file)
                self.save_channel(green, "G", file)
                self.save_channel(red, "R", file)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
