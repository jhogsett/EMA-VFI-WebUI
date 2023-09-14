"""Split Frames Feature Core Code"""
import os
import glob
import argparse
import math
import shutil
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path, split_filepath
from webui_utils.mtqdm import Mtqdm
from resequence_files import ResequenceFiles

def main():
    """Use the Split Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Split a directory of PNG frame files')
    parser.add_argument("--input_path", default=None, type=str,
        help="Input path to PNG frame files to split")
    parser.add_argument("--output_path", default=None, type=str,
        help="Base path for frame group directories")
    parser.add_argument("--file_ext", default="png", type=str,
                        help="File extension, default: 'png'; any extension or or '*'")
    parser.add_argument("--type", default="precise", type=str,
        help="Split type 'precise' (default), 'resynthesis', 'inflation'")
    parser.add_argument("--num_groups", default=10, type=int, help="Number of new file groups")
    parser.add_argument("--max_files_per_group", default=0, type=int,
                        help="Maximum allowed files per group (default: 0 - no limit)")
    parser.add_argument("--action", default="copy", type=str,
        help="Files action 'copy' (default), 'move'")
    parser.add_argument("--dry_run", dest="dry_run", default=False, action="store_true",
                        help="Show changes that will be made")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    SplitFrames(args.input_path,
                args.output_path,
                args.file_ext,
                args.type,
                args.num_groups,
                args.max_files_per_group,
                args.action,
                args.dry_run,
                log.log).split()

class SplitFrames:
    """Encapsulate logic for Split Frames feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                file_ext : str,
                type : str,
                num_groups : int,
                max_files : int,
                action : str,
                dry_run : bool,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.file_ext = file_ext
        self.type = type
        self.num_groups = num_groups
        self.max_files = max_files
        self.action = action
        self.dry_run = dry_run
        self.log_fn = log_fn
        valid_types = ["precise", "resynthesis", "inflation"]
        valid_actions = ["copy", "move"]

        if not is_safe_path(self.input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(self.output_path):
            raise ValueError("'output_path' must be a legal path")
        if not self.type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")
        if not self.action in valid_actions:
            raise ValueError(f"'action' must be one of {', '.join([t for t in valid_actions])}")
        if self.max_files < 0:
            raise ValueError("'max_files_per_group' must be >= 0")

    def split(self) -> list:
        """Invoke the Split Frames feature"""
        files = sorted(glob.glob(os.path.join(self.input_path, f"*.{self.file_ext}")))
        num_files = len(files)
        if self.num_groups > num_files:
            raise ValueError(f"'num_groups' must be <= source file count {num_files}")
        num_width = len(str(num_files))

        if self.max_files > 0:
            files_per_group = self.max_files
            needed_groups = int(math.ceil(num_files / self.max_files))
            self.num_groups = needed_groups
            self.log(f"overriding 'num_groups' with computed value {needed_groups}")
        else:
            if self.num_groups < 1:
                raise ValueError("'num_groups' must be >= 1")
            files_per_group = int(math.ceil(num_files / self.num_groups))
        self.log(f"Splitting files to {self.num_groups} groups of {files_per_group} files")

        add_resynthesis_frames = self.type == "resynthesis"
        add_inflation_frame = self.type == "inflation"

        if self.dry_run:
            print(f"[Dry Run] Creating base output path {self.output_path}")
        else:
            self.log(f"Creating base output path {self.output_path}")
            create_directory(self.output_path)

        file_groups = [[] for n in range(self.num_groups)]
        for group in range(self.num_groups):
            self.log(f"Collecting filenames for group {group}")
            start_index = group * files_per_group
            for index in range(files_per_group):
                file_index = start_index + index
                if file_index < num_files:
                    file_groups[group].append(files[file_index])

            if add_resynthesis_frames:
                self.log("Adding surrounding anchor frames for resynthesis")
                prev_group = group - 1
                _prev_start_index = prev_group * files_per_group
                prev_last_index = _prev_start_index + files_per_group-1
                next_group = group + 1
                next_start_index = next_group * files_per_group

                if _prev_start_index >= 0:
                    prev_last_file = files[prev_last_index]
                else:
                    prev_last_file = None
                if next_start_index < num_files:
                    next_start_file = files[next_start_index]
                else:
                    next_start_file = None
                self.log(
        f"Anchor files for resynthesis frames: prev '{prev_last_file}' next '{next_start_file}'")

                if group == 0:
                    self.log("Adding after anchor frame")
                    file_groups[group] = file_groups[group] + [next_start_file]
                elif group == self.num_groups-1:
                    self.log("Adding before anchor frame")
                    file_groups[group] = [prev_last_file] + file_groups[group]
                else:
                    self.log("Adding before and after anchor frames")
                    file_groups[group] = [prev_last_file] + file_groups[group] + [next_start_file]

            elif add_inflation_frame:
                self.log("Adding ending anchor frame for inflation")
                next_group = group + 1
                next_start_index = next_group * files_per_group

                if next_start_index < num_files:
                    next_start_file = files[next_start_index]
                else:
                    next_start_file = None
                self.log(
                f"Anchor File for inflation frames: next '{next_start_file}'")

                if group < self.num_groups-1:
                    self.log("Adding after anchor frame")
                    file_groups[group] = file_groups[group] + [next_start_file]

        group_paths = []
        with Mtqdm().open_bar(total=self.num_groups, desc="Split") as group_bar:
            for group in range(self.num_groups):
                group_files = file_groups[group]
                num_group_files = len(group_files)
                first_index = group * files_per_group
                last_index = ((group+1) * files_per_group) - 1

                # deal with a possibly incomplete last group
                if last_index >= num_files:
                    last_index = num_files-1

                group_name_first_index = first_index
                group_name_last_index = last_index

                if add_resynthesis_frames:
                    if group == 0:
                        group_name_last_index += 1
                    elif group == self.num_groups-1:
                        group_name_first_index -= 1
                    else:
                        group_name_first_index -= 1
                        group_name_last_index += 1
                elif add_inflation_frame:
                    if group < self.num_groups-1:
                        group_name_last_index += 1

                group_name = f"{str(group_name_first_index).zfill(num_width)}" +\
                    f"-{str(group_name_last_index).zfill(num_width)}"
                group_path = os.path.join(self.output_path, group_name)
                group_paths.append(group_path)

                if self.dry_run:
                    self.log(f"[Dry Run] Creating directory {group_path}")
                else:
                    self.log(f"Creating directory {group_path}")
                    create_directory(group_path)

                desc = "Copying" if self.action == "copy" else "Moving"
                with Mtqdm().open_bar(total=num_group_files, desc=desc) as file_bar:
                    for file in group_files:
                        from_filepath = file
                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(group_path, filename + ext)
                        if self.dry_run:
                            print(f"[Dry Run] Copying {from_filepath} to {to_filepath}")
                        else:
                            self.log(f"Copying {from_filepath} to {to_filepath}")
                            shutil.copy(from_filepath, to_filepath)
                        Mtqdm().update_bar(file_bar)
                Mtqdm().update_bar(group_bar)

                if add_resynthesis_frames or add_inflation_frame:
                    if self.dry_run:
                        print(f"[Dry Run] Resequencing files in {group_path}")
                    else:
                        self.log(f"Resequencing files in {group_path}")
                        base_filename = f"{group_name}-{self.type}-split-frame"
                        ResequenceFiles(group_path,
                                        self.file_ext,
                                        base_filename,
                                        0, 1, 1, 0, num_width,
                                        True,
                                        self.log).resequence()

        if self.action != "copy":
            with Mtqdm().open_bar(total=num_files, desc="Deleting") as bar:
                for file in files:
                    if os.path.exists(file):
                        if self.dry_run:
                            print(f"[Dry Run] Deleting {file}")
                        else:
                            self.log(f"Deleting {file}")
                            os.remove(file)
                    Mtqdm().update_bar(bar)

        return group_paths

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
