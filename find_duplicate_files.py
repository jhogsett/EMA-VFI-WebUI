"""Find Duplicate0 Files Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
# from PIL import Image

def main():
    """Use the Find Duplicate Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Find Duplicate files')
    parser.add_argument("--path", default="./", type=str,
        help="Path to files to check")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    FindDuplicateFiles(args.path, log.log).find()

class FindDuplicateFiles:
    """Encapsulate logic for Find Duplicate Files feature"""
    def __init__(self,
                path : str,
                log_fn : Callable | None):
        self.path = path
        self.log_fn = log_fn

    def find(self) -> None:
        """Invoke the Find Duplicate Files feature"""
        files = sorted(glob.glob(os.path.join(self.path, "*.*")))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        if files:
            with Mtqdm().open_bar(len(files), desc="Checking") as bar:
                for file in files:
                    print(file)
                    # self.log(f"removing image info from {file}")
                    # img = Image.open(file)
                    # if img.info:
                    #     self.log(f"removing: {img.info}")
                    # img.save(file)
                    Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
