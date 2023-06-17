"""Deduplicate Frames Feature Core Code"""
import os
import glob
import argparse
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from PIL import Image
from webui_utils.video_utils import get_duplicate_frames_report, get_duplicate_frames
from webui_utils.file_utils import split_filepath
def main():
    """Use the Deduplicate Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Deduplicate video frame PNG files')
    parser.add_argument("--input_path", default=None, type=str,
        help="Path to PNG frames files to deduplicate")
    parser.add_argument("--output_path", default=None, type=str,
        help="Path to store deduplicated PNG frames files")
    parser.add_argument("--threshold", default="2500", type=int,
                        help="Detection threshold (default:2500), larger=more duplicates found")
    parser.add_argument("--max_dupes", default="0", type=int,
                        help="Max duplicates per group (default:0), 0=no limit, 1=no dupes allowed")
    parser.add_argument("--disposition", default="report", type=str,
                help="Outcome for found duplicate frames: 'report' (default), 'delete', 'autofill'")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    DeduplicateFrames(args.input_path,
                      args.output_path,
                      args.threshold,
                      args.max_dupes,
                      args.disposition,
                      log.log).invoke()

class DeduplicateFrames:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                threshold : int,
                max_dupes : int,
                disposition : str,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.threshold = threshold
        self.max_dupes = max_dupes
        self.disposition = disposition
        self.log_fn = log_fn

    def invoke(self):
        """Invoke the Deduplicate Frames feature"""
        if self.disposition.startswith("d"):
            return self.invoke_delete()
        elif self.disposition.startswith("a"):
            return self.invoke_autofill()
        else:
            return self.invoke_report()

    def invoke_report(self):
        try:
            self.log("calling 'get_duplicate_frames_report' with" + \
        f" input_path: {self.input_path} threshold: {self.threshold} max_dupes: {self.max_dupes} ")
            report = get_duplicate_frames_report(self.input_path, self.threshold, self.max_dupes)
            if self.output_path:
                _path, _filename, _ext = split_filepath(self.output_path)
                filename = _filename or "Duplicate Frames Report"
                ext = _ext or ".txt"
                report_path = os.path.join(_path, filename + ext)
                with open(report_path, "w", encoding="UTF-8") as file:
                    file.write(report)
                print(f"Duplicate Frames Report written to {report_path}")
            else:
                print()
                print(report)
                print()
        except RuntimeError as error:
            print(f"Error generating report: {error}")

    def invoke_delete(self):
        pass

    def invoke_autofill(self):
        pass

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
