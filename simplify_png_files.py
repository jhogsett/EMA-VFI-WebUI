"""Simplify PNG Files Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
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

        with Mtqdm().open_bar(len(files), desc="Simplifying") as bar:
            for file in files:
                self.log(f"removing image info from {file}")
                img = Image.open(file)
                if img.info:
                    self.log(f"removing: {img.info}")
                img.save(file)
                Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
