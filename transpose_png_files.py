"""Transpose PNG Files Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
from PIL import Image
import numpy as np
import cv2

def main():
    """Use the Transpose PNG Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Transpose video frame image files')
    parser.add_argument("--path", default="./images", type=str,
        help="Path to PNG files to simplify")
    parser.add_argument("--operation", type=str,
    help=f"Transformation operation: {', '.join(TransposePngFiles.OPERATIONS)}")
    parser.add_argument("--type", default="png", type=str,
                    help="File type for frame files (Default 'png')")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    try:
        args.operation = args.operation.lower()
        _ = TransposePngFiles.OPERATIONS.index(args.operation)
    except:
        print(f"'operation' must be one of: {', '.join(TransposePngFiles.OPERATIONS)}")
        return

    log = SimpleLog(args.verbose)
    TransposePngFiles(args.path, args.operation, log.log).transpose(type=args.type)

class TransposePngFiles:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                path : str,
                operation: str,
                log_fn : Callable | None):
        self.path = path
        self.operation = operation.lower()
        self.log_fn = log_fn

    OPERATIONS = ["fliph", "flipv", "ccw90", "rot180", "cw90", "transp", "transv"]
    PIL_TYPES = {
        "fliph" : Image.Transpose.FLIP_LEFT_RIGHT,
        "flipv" : Image.Transpose.FLIP_TOP_BOTTOM,
        "ccw90" : Image.Transpose.ROTATE_90,
        "rot180" : Image.Transpose.ROTATE_180,
        "cw90" : Image.Transpose.ROTATE_270,
        "transp" : Image.Transpose.TRANSPOSE,
        "transv" : Image.Transpose.TRANSVERSE
    }

    METHODS = {
        "fliph" : "opencv",
        "flipv" : "opencv",
        "ccw90" : "pillow",
        "rot180" : "opencv",
        "cw90" : "pillow",
        "transp" : "pillow",
        "transv" : "pillow"
    }

    def pillow_transpose(self, file) -> bool:
        try:
            pil_method = self.PIL_TYPES[self.operation]
            img = Image.open(file)
            new_img = img.transpose(method=pil_method)
            new_img.save(file)
        except Exception as error:
            raise ValueError(f"pillow_transpose() failed for file {file} with error '{error}'.")

    def opencv_transpose(self, file) -> bool:
        try:
            frame = cv2.imread(file)
            data = np.array(frame, np.uint8)

            if self.operation == "fliph":
                data = np.flip(data, axis = 1)
            elif self.operation == "flipv":
                data = np.flip(data, axis = 0)
            elif self.operation == "rot180":
                data = np.flip(data, axis = 1)
                data = np.flip(data, axis = 0)
                data = np.flip(data, axis = 1)

            img = data.astype(np.uint8)
            cv2.imwrite(file, img)
        except Exception as error:
            raise ValueError(f"opencv_transpose() failed for file {file} with error '{error}'.")

    def transpose(self, type) -> None:
        """Invoke the Transpose Image Files feature"""
        if not self.operation in self.OPERATIONS:
            raise ValueError(f"Transpose type '{self.operation}' is not valid")

        files = sorted(glob.glob(os.path.join(self.path, "*." + type)))
        num_files = len(files)

        with Mtqdm().open_bar(len(files), desc="Transposing") as bar:
            for file in files:
                method = self.METHODS[self.operation]
                if method == "pillow":
                    self.pillow_transpose(file)
                else:
                    self.opencv_transpose(file)
                Mtqdm().update_bar(bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
