"""Transpose PNG Files Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
from PIL import Image

def main():
    """Use the Transpose PNG Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Transpose video frame PNG files')
    parser.add_argument("--path", default="./images", type=str,
        help="Path to PNG files to simplify")
    parser.add_argument("--type", type=str,
    help=f"Transformation type: {', '.join(TransposePngFiles.TYPES)}")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    try:
        args.type = args.type.lower()
        _ = TransposePngFiles.TYPES.index(args.type)
    except:
        print(f"'type' must be one of: {', '.join(TransposePngFiles.TYPES)}")
        return

    log = SimpleLog(args.verbose)
    TransposePngFiles(args.path, args.type, log.log).transpose()

class TransposePngFiles:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                path : str,
                type: str,
                log_fn : Callable | None):
        self.path = path
        self.type = type.lower()
        self.log_fn = log_fn

    TYPES = ["fliph", "flipv", "rot90", "rot180", "rot270", "transp", "transv"]
    PIL_TYPES = {
        "fliph" : Image.Transpose.FLIP_LEFT_RIGHT,
        "flipv" : Image.Transpose.FLIP_TOP_BOTTOM,
        "rot90" : Image.Transpose.ROTATE_90,
        "rot180" : Image.Transpose.ROTATE_180,
        "rot270" : Image.Transpose.ROTATE_270,
        "transp" : Image.Transpose.TRANSPOSE,
        "transv" : Image.Transpose.TRANSVERSE
    }
    DEFAULT_TYPE = "rot90"

    def transpose(self) -> None:
        """Invoke the Simplify PNG Files feature"""
        files = sorted(glob.glob(os.path.join(self.path, "*.png")))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        try:
            method = self.PIL_TYPES[self.type]
        except:
            raise ValueError(f"Transpose type '{self.type}' is not valid")

        with Mtqdm().open_bar(len(files), desc="Transposing") as bar:
            for file in files:
                self.log(f"removing image info from {file}")
                img = Image.open(file)
                new_img = img.transpose(method=method)
                new_img.save(file)
                Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
