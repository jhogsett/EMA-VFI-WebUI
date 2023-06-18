"""Deduplicate Frames Feature Core Code"""
import os
import shutil
import argparse
from typing import Callable
from tqdm import tqdm
from webui_utils.simple_log import SimpleLog
from webui_utils.video_utils import get_duplicate_frames_report, get_duplicate_frames
from webui_utils.file_utils import split_filepath, create_directory
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from restore_frames import RestoreFrames

def main():
    """Use the Deduplicate Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Deduplicate video frame PNG files')
    parser.add_argument("--input_path", default=None, type=str,
                        help="Path to PNG frames files to deduplicate")
    parser.add_argument("--output_path", default=None, type=str,
                        help="Path to store deduplicated PNG frames files (optional)")
    parser.add_argument("--threshold", default="2500", type=int,
                        help="Detection threshold (default:2500), larger=more duplicates found")
    parser.add_argument("--max_dupes", default="0", type=int,
                        help="Max duplicates per group (default:0), 0=no limit, 1=no dupes allowed")
    parser.add_argument("--disposition", default="report", type=str,
                help="Outcome for found duplicate frames: 'report' (default), 'delete', 'autofill'")
    parser.add_argument('--model', default='ours', type=str)
    parser.add_argument('--gpu_ids', type=str, default='0',
                        help='gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)')
    parser.add_argument("--time_step", dest="time_step", default=False, action="store_true",
                    help="Use Time Step instead of Binary Search interpolation (Default: False)")
    parser.add_argument("--depth", default=10, type=int,
                        help="How deep the frame splits go to reach the target")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
                        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step=args.time_step)
    interpolater = Interpolate(engine.model, log.log)
    target_interpolater = TargetInterpolate(interpolater, log.log)
    frame_restorer = RestoreFrames(interpolater, target_interpolater, args.time_step, log.log)

    DeduplicateFrames(frame_restorer,
                      args.input_path,
                      args.output_path,
                      args.threshold,
                      args.max_dupes,
                      args.depth,
                      log.log).invoke(args.disposition)

class DeduplicateFrames:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                frame_restorer : RestoreFrames,
                input_path : str,
                output_path : str,
                threshold : int,
                max_dupes : int,
                depth : int,
                log_fn : Callable | None):
        self.frame_restorer = frame_restorer
        self.input_path = input_path
        self.output_path = output_path
        self.threshold = threshold
        self.max_dupes = max_dupes
        self.depth = depth
        self.log_fn = log_fn
        if not self.input_path:
            raise ValueError("'input_path' must be specified")
        if not os.path.exists(self.input_path):
            raise ValueError("'input_path' must exist")
        if self.threshold < 0:
            raise ValueError("'threshold' must be positive")
        if self.max_dupes < 0:
            raise ValueError("'max_dupes' must be positive")

    valid_dispositions = ["report", "delete", "autofill"]

    def valid_disposition(self, disposition):
        return disposition in self.valid_dispositions

    def invoke(self, disposition : str):
        """Invoke the Deduplicate Frames feature"""
        if not self.valid_disposition(disposition):
            raise ValueError(
                    f"'disposition' must be one of the values: {','.join(self.valid_dispositions)}")
        if disposition.startswith("d"):
            return self.invoke_delete()
        elif disposition.startswith("a"):
            return self.invoke_autofill()
        else:
            return self.invoke_report()

    def invoke_report(self, suppress_output=False):
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
                message = f"Duplicate Frames Report written to {report_path}"
                self.log(message)
                if not suppress_output:
                    print(message)
            else:
                if not suppress_output:
                    print()
                    print(report)
                    print()
            return report
        except RuntimeError as error:
            message = f"Error generating report: {error}"
            self.log(message)
            if suppress_output:
                raise error
            else:
                print(message)

    def invoke_delete(self, suppress_output=False):
        if not self.output_path:
            raise ValueError("'output_path' must be specified")
        create_directory(self.output_path)

        try:
            self.log("invoke_delete() calling 'get_duplicate_frames' with" + \
        f" input_path: {self.input_path} threshold: {self.threshold} max_dupes: {self.max_dupes} ")
            dupe_groups, frame_filenames, mpdecimate_log = get_duplicate_frames(self.input_path,
                                                                                self.threshold,
                                                                                self.max_dupes)
            self.log("mpdecimate data received from 'get_duplicate_frames:")
            self.log(mpdecimate_log)
            self.log(f"beginning processing of {len(dupe_groups)} duplicate groups for deletion")

            # remove duplicates from full list of frame files
            all_filenames = frame_filenames.copy()
            dupe_count = 0
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

            message = f"{len(frame_filenames)} frame files," +\
                  f" excluding {dupe_count} duplicates, copied to: {self.output_path}"
            self.log(message)
            if not suppress_output:
                print(message)
            return message, dupe_groups, all_filenames
        except RuntimeError as error:
            message = f"Error generating report: {error}"
            self.log(message)
            if suppress_output:
                raise error
            else:
                print(message)

    def invoke_autofill(self, suppress_output=False):
        self.log("invoke_autofill() using invoke_delete() to copy non-duplicate frames")
        _, dupe_groups, frame_filenames = self.invoke_delete(True)

        pbar_title = "Auto-Filling"
        self.log(f"beginning processing of {len(dupe_groups)} duplicate frame groups")
        restored_total = 0
        for index, group in enumerate(tqdm(dupe_groups, desc=pbar_title)):
            self.log(f"processing group #{index+1}")
            group_indexes = list(group.keys())
            group_files = list(group.values())
            restore_count = len(group) - 1
            self.log(f"restore count: {restore_count}")

            # first file in group is a "keep" frame
            before_file = group_files[0]
            self.log(f"before frame file: {before_file}")

            # index after last index in group is the next "keep" frame
            after_index = group_indexes[-1] + 1
            if after_index >= len(frame_filenames):
                message = [
                    "The last group has no 'after' file for interpolation, skipping.",
                    "Affected files:"]
                message += group_files[1:]
                message = "\r\n".join(message)
                self.log(message)
                if suppress_output:
                    raise RuntimeError(message)
                else:
                    print("Warning: " + message)
            else:
                after_file = frame_filenames[after_index]
                self.log(f"after frame file: {after_file}")

                # use frame restorer
                self.log(f"using frame restorer with: img_before={before_file}" +\
                         f" img_after={after_file} num_frames={restore_count} depth={self.depth}")

                self.frame_restorer.restore_frames(before_file,
                                                   after_file,
                                                   restore_count,
                                                   self.depth,
                                                   self.output_path,
                                                   "autofilled_frame")
                restored_total += restore_count
                restored_files = self.frame_restorer.output_paths
                self.frame_restorer.output_paths = []
                self.log(f"restored files: {','.join(restored_files)}")

                for index, file in enumerate(group_files):
                    if index: # skip the first ("keep") file
                        _, filename, ext = split_filepath(file)
                        restored_file = restored_files[index-1]
                        new_filename = os.path.join(self.output_path, filename + ext)
                        self.log(f"renaming {restored_file} to {new_filename}")
                        os.replace(restored_file, new_filename)

        message = f"{restored_total} duplicate frames filled with interpolated replacements at" +\
                  f" {self.output_path}"
        self.log(message)
        if not suppress_output:
            print(message)
        return message, dupe_groups, frame_filenames

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
