"""Simplify PNG Files Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from tqdm import tqdm
from simple_log import SimpleLog
from PIL import Image

def main():
    """Use the Simplify PNG Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Simplify video frame PNG files')
    parser.add_argument("--path", default="./images", type=str,
        help="Path to PNG files to simplify")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SimplifyPngFiles(args.path, log.log).simplify()

class SimplifyPngFiles:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                path : str,
                log_fn : Callable | None):
        self.path = path
        self.log_fn = log_fn

    def simplify(self) -> None:
        """Invoke the Simplify PNG Files feature"""
        files = sorted(glob.glob(os.path.join(self.path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        pbar_title = "Simplifying"
        for file in tqdm(files, desc=pbar_title):
            self.log(f"removing image info from {file}")
            img = Image.open(file)
            if img.info:
                self.log(f"removing: {img.info}")
            img.save(file)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
