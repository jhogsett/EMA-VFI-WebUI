"""Merge Frames Feature Core Code"""
import os
import shutil
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path, split_filepath, get_directories
from webui_utils.mtqdm import Mtqdm
from resequence_files import ResequenceFiles

def main():
    """Use the Merge Frames feature from the command line"""
    parser = argparse.ArgumentParser(description='Split a directory of PNG frame files')
    parser.add_argument("--input_path", default=None, type=str,
        help="Base path with frame group directories")
    parser.add_argument("--output_path", default=None, type=str,
        help="Output path for recombined files")
    parser.add_argument("--file_ext", default="png", type=str,
                        help="File extension, default: 'png'; any extension or '*'")
    parser.add_argument("--type", default="precise", type=str,
        help="Merge type 'precise' (default), 'resynthesis', 'inflation'")
    parser.add_argument("--num_groups", default=-1, type=int,
                        help="Number of file groups, -1 for auto-detect (default)")
    parser.add_argument("--action", default="combine", type=str,
        help="Files action 'combine' (default), 'revert'")
    parser.add_argument("--dry_run", dest="dry_run", default=False, action="store_true",
                        help="Show changes that will be made")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    MergeFrames(args.input_path,
                args.output_path,
                args.file_ext,
                args.type,
                args.num_groups,
                args.action,
                args.dry_run,
                log.log).merge()

class MergeFrames:
    """Encapsulate logic for Merge Frames feature"""
    def __init__(self,
                input_path : str,
                output_path : str,
                file_ext : str,
                type : str,
                num_groups : int,
                action : str,
                dry_run : bool,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.file_ext = file_ext
        self.type = type
        self.num_groups = num_groups
        self.action = action
        self.dry_run = dry_run
        self.log_fn = log_fn
        valid_types = ["precise", "resynthesis", "inflation"]
        valid_actions = ["revert", "combine"]

        if not is_safe_path(input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(output_path):
            raise ValueError("'output_path' must be a legal path")
        if num_groups < -1 or num_groups == 0:
            raise ValueError("'num_groups' must be > 0 or -1")
        if not type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")
        if not action in valid_actions:
            raise ValueError(f"'action' must be one of {', '.join([t for t in valid_actions])}")

    def merge(self) -> None:
        """Invoke the Merge Frames feature"""
        group_names = self.validate_input_path()
        self.validate_group_names(group_names)

        if self.dry_run:
            print(f"[Dry Run] Creating output path {self.output_path}")
        else:
            self.log(f"Creating output path {self.output_path}")
            create_directory(self.output_path)

        first_group_name = group_names[0]
        first_index, last_index, num_width = self.details_from_group_name(first_group_name)

        if type == "resynthesis":
            self.merge_resynthesis(first_index, last_index, num_width, group_names)
        elif type == "inflation":
            self.merge_inflation(first_index, last_index, num_width, group_names)
        else:
            self.merge_precise(num_width, group_names)

    def group_path(self, group_name):
        return os.path.join(self.input_path, group_name)

    def group_files(self, group_name):
        group_path = self.group_path(group_name)
        return sorted(glob.glob(os.path.join(group_path, f"*.{self.file_ext}")))


    def merge_precise(self, num_width, group_names):
        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_name in group_names:
                first_index, last_index, _ = self.details_from_group_name(group_name)
                group_size = last_index - first_index + 1
                expected_files = group_size
                group_files = self.group_files(group_name)
                if len(group_files) != expected_files:
                    raise RuntimeError(
                        f"expected {expected_files} files in {group_name} but found {len(group_files)}")

                with Mtqdm().open_bar(total=len(group_files), desc="Copying") as file_bar:
                    for file in group_files:
                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)
                Mtqdm().update_bar(group_bar)

        if self.action == "move":
            with Mtqdm().open_bar(total=len(group_names), desc="Deleting Groups") as bar:
                for group_name in group_names:
                    group_path = self.group_path(group_name)
                    if self.dry_run:
                        print(f"[Dry Run] deleting group {group_path}")
                    else:
                        self.log(f"deleting group {group_path}")
                        shutil.rmtree(group_path)
                    Mtqdm().update_bar(bar)

    def merge_precise_combine(self, num_width, group_names):
        # go through each group, renumbering files

        # FILE COUNT = count of files in group

        # - for each group, the count of files must match EXPECTED FILES
        # - the renumbering START INDEX is FIRST INDEX
        # - renumber the files starting START INDEX using NUM WIDTH padding
        # - copy all group files to the output directory
        # - each file should not already exist at destination
        pass


                    # if self.dry_run:
                    #     print(f"[Dry Run] Resequencing files in {group_path}")
                    # else:
                    #     self.log(f"Resequencing files in {group_path}")
                    #     base_filename = f"{group_name}-{self.type}-split-frame"
                    #     ResequenceFiles(group_path,
                    #                     self.file_ext,
                    #                     base_filename,
                    #                     0, 1, 1, 0, num_width,
                    #                     True,
                    #                     self.log).resequence()

    def merge_resynthesis(self, first_index, last_index, num_width, group_names):
        group_size = last_index - first_index
        if self.action == "combine":
            self.merge_resynthesis_combine(first_index, last_index, num_width, group_size)
        else:
            self.merge_resynthesis_revert(first_index, last_index, num_width, group_size)

    def merge_resynthesis_revert(self, first_index, last_index, num_width, group_size, group_names):
            # EXPECTED FILES = GROUP SIZE + 2

        # go through each group, renumbering files
        # FILE COUNT = count of files in group

        # - for each group, the count of files must match EXPECTED FILES
        #   - except the first group, where the count of files should be EXPECTED FILES - 1
        #   - except the last group, where the count of files should be EXPECTED FILES - 1

        # - the renumbering START INDEX is FIRST INDEX + 1
        # - renumber the files starting START INDEX using NUM WIDTH padding

            # - copy all EXCEPT first and last group files to the output directory
            #   - except first group, copy all but last file
            #   - except last group, copy all but first file

        # - each file should not already exist at destination
        pass

    def merge_resynthesis_combine(self, first_index, last_index, num_width, group_size, group_names):
            # EXPECTED FILES = GROUP SIZE - 1

        # go through each group, renumbering files
        # FILE COUNT = count of files in group

        # - for each group, the count of files must match EXPECTED FILES
        #   - except the first group, where the count of files should be EXPECTED FILES - 1

            #   - except the last group, where the count of files should match THAT group size - 1
                # same group size and expected files calculation just on last group

        # - the renumbering START INDEX is FIRST INDEX + 1
        # - renumber the files starting START INDEX using NUM WIDTH padding

            # - copy all group files to the output directory

        # - each file should not already exist at destination
        pass


    def merge_inflation(self, first_index, last_index, num_width, group_names):
        if self.action == "combine":
            self.merge_inflation_combine(first_index, last_index, num_width)
        else:
            self.merge_inflation_revert(first_index, last_index, num_width)

    def merge_inflation_revert(self, first_index, last_index, num_width, group_names):
            # GROUP SIZE = LAST INDEX - FIRST INDEX

        # FILE COUNT = count of files in group

        # EXPECTED FILES = GROUP SIZE + 1
        # - extra file is ending outer anchor frame and won't be copied
        # go through each group, renumbering files
        # FILE COUNT = count of files in group
        # - for each group, the count of files must match EXPECTED FILES
        #   - except the last group, where the count of files should match THAT group size + 1
        #   - (GROUP SIZE * (LAST INDEX - FIRST INDEX)) + 1
              # same group size and expected files calculation just on last group

            # - the renumbering START INDEX is FIRST INDEX

        # - renumber the files starting START INDEX using NUM WIDTH padding
        # - copy all group files to the output directory EXCEPT THE LAST FILE
        #   - except the last group - COPY ALL FILES
        # - each file should not already exist at destination
        pass

    def merge_inflation_combine(self, first_index, last_index, num_width, group_names):
            # ORIG GROUP SIZE = LAST INDEX - FIRST INDEX

        # FILE COUNT = count of files in group

            # DETECTED INFLATION = FILE COUNT / ORIG GROUP SIZE
            # DETECTED INFLATION must be an integer
            # GROUP SIZE = DETECTED INFLATION * ORIG GROUP SIZE

        # EXPECTED FILES = GROUP SIZE + 1
        # - extra file is ending outer anchor frame and won't be copied
        # go through each group, renumbering files
        # FILE COUNT = count of files in group
        # - for each group, the count of files must match EXPECTED FILES
        #   - except the last group, where the count of files should match THAT group size + 1
        #   - (GROUP SIZE * (LAST INDEX - FIRST INDEX)) + 1
              # same group size and expected files calculation just on last group

            # - the renumbering START INDEX is FIRST INDEX * DETECTED INFLATION

        # - renumber the files starting START INDEX using NUM WIDTH padding
        # - copy all group files to the output directory EXCEPT THE LAST FILE
        #   - except the last group - COPY ALL FILES
        # - each file should not already exist at destination
        pass









    def validate_input_path(self):
        """returns the list of group names"""
        if not os.path.exists(self.input_path):
            raise ValueError("'input_path' must be the path of an existing directory")

        group_names = get_directories(self.input_path)
        if len(group_names) < 1:
            raise ValueError(f"no folders founder in directory {self.input_path}")

        if self.num_groups == -1:
            self.num_groups = len(group_names)
        else:
            if len(group_names) != self.num_groups:
                raise ValueError(
                    f"'num_groups' should match count of directories found at {self.input_path}")
        return group_names

    def validate_group_names(self, group_names):
            try:
                for name in group_names:
                    _, _, _ = self.details_from_group_name(name)
            except RuntimeError as error:
                raise RuntimeError(f"one or more group directory namaes is not valid: {error}")

    def details_from_group_name(self, group_name : str):
        indexes = group_name.split("-")
        if len(indexes) != 2:
            raise RuntimeError(f"group name '{group_name}' cannot be parsed into indexes")
        first_index = int(indexes[0])
        last_index = int(indexes[1])
        num_width = len(str(first_index))
        if num_width < 1:
            raise RuntimeError(f"group name '{group_name}' cannot be parsed into index fill width")
        return first_index, last_index, num_width

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
