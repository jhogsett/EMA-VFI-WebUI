"""Deduplicate Frames Feature Core Code"""
import os
import shutil
import argparse
import csv
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.video_utils import get_duplicate_frames_report, get_duplicate_frames,\
    compute_report_stats
from webui_utils.file_utils import split_filepath, create_directory
from webui_utils.console_colors import ColorOut
from webui_utils.mtqdm import Mtqdm
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
    help="Outcome for found duplicate frames: 'report' (default), 'delete', 'autofill', 'tuning'")
    parser.add_argument('--model', default='ours', type=str)
    parser.add_argument('--gpu_ids', type=str, default='0',
                        help='gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)')
    parser.add_argument("--time_step", dest="time_step", default=False, action="store_true",
                    help="Use Time Step instead of Binary Search interpolation (Default: False)")
    parser.add_argument("--depth", default=10, type=int,
                        help="How deep the frame splits go to reach the target")
    parser.add_argument("--tune_min", default=0, type=int,
                        help="Minimum threshold for tuning (default 0)")
    parser.add_argument("--tune_max", default=25000, type=int,
                        help="Maximum threshold for tuning (default 25000)")
    parser.add_argument("--tune_step", default=100, type=int,
                        help="Threshold step for tuning (default 100)")
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
                      log.log,
                      tune_min=args.tune_min,
                      tune_max=args.tune_max,
                      tune_step=args.tune_step).invoke(args.disposition)

class DeduplicateFrames:
    """Encapsulate logic for Resequence Files feature"""
    def __init__(self,
                frame_restorer : RestoreFrames,
                input_path : str,
                output_path : str,
                threshold : int,
                max_dupes : int,
                depth : int,
                log_fn : Callable | None,
                tune_min : int=0,
                tune_max : int=25000,
                tune_step : int=100):
        self.frame_restorer = frame_restorer
        self.input_path = input_path
        self.output_path = output_path
        self.threshold = threshold
        self.max_dupes = max_dupes
        self.depth = depth
        self.log_fn = log_fn
        self.tune_min = tune_min
        self.tune_max = tune_max
        self.tune_step = tune_step
        if not self.input_path:
            raise ValueError("'input_path' must be specified")
        if not os.path.exists(self.input_path):
            raise ValueError("'input_path' must exist")
        if self.threshold < 0:
            raise ValueError("'threshold' must be positive")
        if self.max_dupes < 0:
            raise ValueError("'max_dupes' must be positive")

    valid_dispositions = ["report", "delete", "autofill", "tuning"]

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
        elif disposition.startswith("t"):
            return self.invoke_tuning()
        else:
            return self.invoke_report()

    def invoke_tuning(self, suppress_output=False):
        message = f"beginning threshold tuning process for {self.input_path} with" +\
            f" min={self.tune_min} max={self.tune_max} step={self.tune_step}"
        self.log(message)

        tuning_data = []
        csv_path = None
        csv_fields = [
            "threshold", "dupe_percent", "max_group", "dupe_count", "first_dupe"]
        if self.output_path:
            path, filename, ext = split_filepath(self.output_path)
            csv_path = os.path.join(path, filename + ".csv")
            with open(csv_path, 'w', encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames = csv_fields)
                writer.writeheader()

        try:
            with Mtqdm().open_bar(total=len(range(self.tune_min, self.tune_max, self.tune_step)),
                                  desc="Tuning") as bar:
                for threshold in range(self.tune_min, self.tune_max, self.tune_step):
                    message = f"geting duplicates for threshold={threshold}"
                    self.log(message)
                    dupe_groups, frame_filenames, _ = get_duplicate_frames(self.input_path,
                                                                            threshold,
                                                                            self.max_dupes)
                    stats = compute_report_stats(dupe_groups, frame_filenames)
                    message = f"dupe_percent={stats['dupe_percent']} max_group={stats['max_group']}" +\
                        f" dupe_count={stats['dupe_count']} first_dupe={stats['first_dupe']}"
                    self.log(message)

                    data = {}
                    data["threshold"] = threshold
                    data["dupe_percent"] = stats["dupe_percent"]
                    data["max_group"] = stats["max_group"]
                    data["dupe_count"] = stats["dupe_count"]
                    data["first_dupe"] = stats["first_dupe"]
                    tuning_data.append(data)
                    Mtqdm().update_bar(bar)

            if csv_path:
                with open(csv_path, 'a', encoding="utf-8", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames = csv_fields)
                    writer.writerows(tuning_data)
                message = f"tuning report saved to {csv_path}"
                self.log(message)
                if not suppress_output:
                    print(message)
            else:
                if not suppress_output:
                    print()
                    print("Tuning Results:")
                    for data in tuning_data:
                        message = f"threshold={data['threshold']}" +\
                            f" dupe_percent={stats['dupe_percent']}" +\
                            f" max_group={stats['max_group']}" +\
                            f" dupe_count={stats['dupe_count']}" +\
                            f" first_dupe={stats['first_dupe']}"
                        print(message)
                    print()
            return tuning_data

        except RuntimeError as error:
            message = f"Error generating report at threshold {threshold} : {error}"
            self.log(message)
            if suppress_output:
                raise RuntimeError(message)
            else:
                ColorOut(message, "red")

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
                ColorOut(message, "red")

    def invoke_delete(self, suppress_output=False, max_size_for_delete=0):
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
            self.log("/r/n".join(mpdecimate_log))
            self.log(f"beginning processing of {len(dupe_groups)} duplicate groups for deletion")

            # remove duplicates from full list of frame files
            all_filenames = frame_filenames.copy()
            dupe_count = 0
            for index, group in enumerate(dupe_groups):
                self.log(f"processing group #{index+1}")

                if max_size_for_delete and len(group) > max_size_for_delete:
                    self.log(f"skipping deleting group #{index}, group size {len(group)}" +\
                             f" exceeds max size for deletion {max_size_for_delete}")
                    continue

                dupes = list(group.values())
                dupes = dupes[1:] # first entry is the 'keep' frame
                for filepath in dupes:
                    self.log(f"excluding {filepath}")
                    frame_filenames.remove(filepath)
                    dupe_count += 1

            with Mtqdm().open_bar(total=len(frame_filenames), desc="Copying") as bar:
                for filepath in frame_filenames:
                    _, filename, ext = split_filepath(filepath)
                    output_filepath = os.path.join(self.output_path, filename + ext)
                    self.log(f"copying {filepath} to {output_filepath}")
                    shutil.copy(filepath, output_filepath)
                    Mtqdm().update_bar(bar)

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
                ColorOut(message, "red")

    def invoke_autofill(self, suppress_output=False):
        self.log("invoke_autofill() using invoke_delete() to copy non-duplicate frames")

        # repurpose max_dupes for auto-fill to mean:
        # skip auto-fill on groups larger than this size
        ignore_over_size = self.max_dupes
        self.max_dupes = 0
        _, dupe_groups, frame_filenames = self.invoke_delete(True,
                                                             max_size_for_delete=ignore_over_size)

        self.log(f"beginning processing of {len(dupe_groups)} duplicate frame groups")
        restored_total = 0
        with Mtqdm().open_bar(total=len(dupe_groups), desc="Auto-Filling") as bar:
            for index, group in enumerate(dupe_groups):
                self.log(f"processing group #{index+1}")
                group_indexes = list(group.keys())
                group_files = list(group.values())
                restore_count = len(group) - 1
                self.log(f"restore count: {restore_count}")

                if ignore_over_size and len(group) > ignore_over_size:
                    self.log(f"skipping restoring group #{index}, restore count {len(group)}" +\
                            f" exceeds max size {ignore_over_size}")
                    Mtqdm().update_bar(bar)
                    continue

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
                        ColorOut("Warning: " + message, "red")
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
                Mtqdm().update_bar(bar)

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
