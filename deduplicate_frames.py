"""Deduplicate Frames Feature Core Code"""
import os
import shutil
import argparse
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from PIL import Image
from webui_utils.video_utils import get_duplicate_frames_report, get_duplicate_frames
from webui_utils.file_utils import split_filepath, create_directory
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

    valid_dispositions = ["report", "delete", "autofill"]

    def valid_disposition(self, disposition):
        return disposition in self.valid_dispositions

    def invoke(self):
        """Invoke the Deduplicate Frames feature"""
        if not self.input_path:
            raise ValueError("'input_path' must be specified")
        if not os.path.exists(self.input_path):
            raise ValueError("'input_path' must exist")
        if self.threshold < 0:
            raise ValueError("'threshold' must be positive")
        if self.max_dupes < 0:
            raise ValueError("'max_dupes' must be positive")
        if not self.valid_disposition(self.disposition):
            raise ValueError(
                    f"'disposition' must be one of the values: {','.join(self.valid_dispositions)}")
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
                self.log(f"writing report to {report_path}")
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
        if not self.output_path:
            raise ValueError("'output_path' must be specified")
        create_directory(self.output_path)

        try:
            self.log("calling 'get_duplicate_frames' with" + \
        f" input_path: {self.input_path} threshold: {self.threshold} max_dupes: {self.max_dupes} ")
            dupe_groups, frame_filenames, mpdecimate_log = get_duplicate_frames(self.input_path,
                                                                                self.threshold,
                                                                                self.max_dupes)
            self.log("mpdecimate data received from 'get_duplicate_frames:")
            self.log(mpdecimate_log)

            # remove duplicates from full list of frame files
            dupe_count = 0
            self.log(f"beginning processing of {len(dupe_groups)} duplicate groups for deletion")
            for index, group in enumerate(dupe_groups):
                self.log(f"processing group #{index+1}")
                dupes = list(group.values())
                dupes = dupes[1:] # first entry is the 'keep' frame
                for filepath in dupes:
                    self.log(f"excluding {filepath}")
                    frame_filenames.remove(filepath)
                    dupe_count += 1

            pbar_title = "Copying"
            for filepath in tqdm(frame_filenames, desc=pbar_title):
                _, filename, ext = split_filepath(filepath)
                output_filepath = os.path.join(self.output_path, filename + ext)
                self.log(f"copying {filepath} to {output_filepath}")
                shutil.copy(filepath, output_filepath)
            print(f"{len(frame_filenames)} frame files," + \
                  f" excluding {dupe_count} duplicates, copied to: {self.output_path}")
        except RuntimeError as error:
            print(f"Error generating report: {error}")

    def invoke_autofill(self):
        pass

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
