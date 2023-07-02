"""Merge Frames Feature Core Code"""
import os
import shutil
import glob
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.file_utils import create_directory, is_safe_path, split_filepath
from webui_utils.video_utils import details_from_group_name, validate_input_path,\
    validate_group_names, group_path, group_files
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
    parser.add_argument("--delete", default=False, type=bool,
                        help="Delete source split groups after merging (default False)")
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
                args.delete,
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
                delete : bool,
                dry_run : bool,
                log_fn : Callable | None):
        self.input_path = input_path
        self.output_path = output_path
        self.file_ext = file_ext
        self.type = type
        self.num_groups = num_groups
        self.action = action
        self.delete = delete
        self.dry_run = dry_run
        self.log_fn = log_fn
        valid_types = ["precise", "resynthesis", "inflation"]
        valid_actions = ["revert", "combine"]

        if not is_safe_path(self.input_path):
            raise ValueError("'input_path' must be a legal path")
        if not is_safe_path(self.output_path):
            raise ValueError("'output_path' must be a legal path")
        if self.num_groups < -1 or self.num_groups == 0:
            raise ValueError("'num_groups' must be > 0 or -1")
        if not self.type in valid_types:
            raise ValueError(f"'type' must be one of {', '.join([t for t in valid_types])}")
        if not self.action in valid_actions:
            raise ValueError(f"'action' must be one of {', '.join([t for t in valid_actions])}")

    def merge(self) -> None:
        """Invoke the Merge Frames feature"""
        group_names = validate_input_path(self.input_path, self.num_groups)
        if self.dry_run:
            print(f"[Dry Run] Creating output path {self.output_path}")
        else:
            self.log(f"Creating output path {self.output_path}")
            create_directory(self.output_path)

        if self.type == "resynthesis":
            self.merge_resynthesis(group_names)
        elif self.type == "inflation":
            self.merge_inflation(group_names)
        else:
            self.merge_precise(group_names)

        if self.delete:
            if self.dry_run:
                print(f"[Dry Run] Deleting split groups in {self.input_path}")
            else:
                self.log(f"Deleting split groups in {self.input_path}")
            with Mtqdm().open_bar(total=len(group_names), desc="Deleting") as bar:
                for group_name in group_names:
                    _group_path = group_path(self.input_path, group_name)
                    if self.dry_run:
                        print(f"[Dry Run] Deleting group {_group_path}")
                    else:
                        self.log(f"Deleting group {_group_path}")
                        shutil.rmtree(_group_path)
                    Mtqdm().update_bar(bar)

    def merge_precise(self, group_names):
        if self.action == "revert":
            # if undoing a precise split, the group names are expected to be unchanged
            # (but whole groups can have been deleted)
            validate_group_names(group_names)

        fix_up_final_files = False
        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_name in group_names:
                _group_files = group_files(self.input_path, self.file_ext, group_name)

                original_group_files = []
                if self.action == "revert":
                    first_index, last_index, _ = details_from_group_name(group_name)
                    group_size = last_index - first_index + 1
                    expected_files = group_size
                    if len(_group_files) != expected_files:
                        raise RuntimeError(
                    f"expected {expected_files} files in {group_name} but found {len(_group_files)}")
                else:
                    # when combining, if the group 'first' and 'last' indexes CAN be obtained,
                    # assume the group needs recombining after processing like 'Upscale Frames',
                    # because the filenames may have been changed which could clash on merging
                    try:
                        first_index, _, num_width = details_from_group_name(group_name)
                        _group_path = group_path(self.input_path, group_name)
                        self.log(
                f"group name {group_name} is parsable, resequencing files to prevent name clash")

                        original_group_files = group_files(self.input_path, self.file_ext, group_name)
                        if self.dry_run:
                            print(f"[Dry Run] Resequencing files in {_group_path}")
                        else:
                            self.log(f"Resequencing files in {_group_path}")
                            base_filename = "copied-frames"
                            ResequenceFiles(_group_path,
                                            self.file_ext,
                                            base_filename,
                                            first_index, 1, 1, 0, num_width,
                                            True,
                                            self.log).resequence()
                        _group_files = group_files(self.input_path, self.file_ext, group_name)
                        fix_up_final_files = True
                    except RuntimeError:
                        # group name is not parsable, don't bother renaming files,
                        # the user is responsible for ensuring the names don't clash on merging
                        self.log(
                            f"group name {group_name} not is parsable, skipping file resequencing")

                with Mtqdm().open_bar(total=len(_group_files), desc="Copying") as file_bar:
                    for file in _group_files:
                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(
                                f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)

                if original_group_files:
                    self.log(f"Restoring original filenames in {_group_path}")
                    with Mtqdm().open_bar(total=len(_group_files),
                                            desc="Renaming") as bar:
                        for index, file in enumerate(_group_files):
                            original_filename = original_group_files[index]
                            if self.dry_run:
                                print(
                                f"[Dry Run] Restoring file '{file}' to '{original_filename}'")
                            else:
                                self.log(f"Restoring file '{file}' to '{original_filename}'")
                                os.replace(file, original_filename)
                            Mtqdm().update_bar(bar)
                Mtqdm().update_bar(group_bar)

        if fix_up_final_files:
            if self.dry_run:
                print(f"[Dry Run] Resequencing fina set of files in {self.output_path}")
            else:
                self.log(f"Resequencing files in {self.output_path}")
                base_filename = "combined-precision-split"
                ResequenceFiles(self.output_path,
                                self.file_ext,
                                base_filename,
                                0, 1, 1, 0, num_width,
                                True,
                                self.log).resequence()

        if self.action == "move":
            with Mtqdm().open_bar(total=len(group_names), desc="Deleting Groups") as bar:
                for group_name in group_names:
                    _group_path = group_path(self.input_path, group_name)
                    if self.dry_run:
                        print(f"[Dry Run] deleting group {_group_path}")
                    else:
                        self.log(f"deleting group {_group_path}")
                        shutil.rmtree(_group_path)
                    Mtqdm().update_bar(bar)

    def merge_resynthesis(self, group_names):
        validate_group_names(group_names)
        first_group_name = group_names[0]
        first_index, last_index, num_width = details_from_group_name(first_group_name)
        group_size = last_index - first_index

        if self.action == "combine":
            self.merge_resynthesis_combine(first_index, last_index, num_width, group_size, group_names)
        else:
            self.merge_resynthesis_revert(first_index, last_index, num_width, group_size, group_names)

    def merge_resynthesis_revert(self, first_index, last_index, num_width, group_size, group_names):
        expected_files = group_size + 2 # outer frames added to support resynthesis

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_index, group_name in enumerate(group_names):
                group_expected_files = expected_files

                if group_index == 0:
                    # one fewer frame; outer frames can't have anchor frames
                    group_expected_files -=1
                elif group_index == len(group_names)-1:
                    # get this group's file count, as it may be truncated being the final group
                    # next, have one fewer frame; outer frames can't have anchor frames
                    first_index, last_index, _ = details_from_group_name(group_name)
                    group_size = last_index - first_index
                    group_expected_files = group_size + 1

                _group_files = group_files(self.input_path, self.file_ext, group_name)
                if len(_group_files) != group_expected_files:
                    raise RuntimeError(
                        f"expected {group_expected_files} files in {group_name} but found {len(_group_files)}")

                # renumber all present files according to the first, last indexes
                # including files that will not be ulitmately copied back
                _group_path = group_path(self.input_path, group_name)
                first_index, _, _ = details_from_group_name(group_name)
                if self.dry_run:
                    print(f"[Dry Run] Resequencing files in {_group_path}")
                else:
                    self.log(f"Resequencing files in {_group_path}")
                    base_filename = "reverted-resynthesis-split"

                    ResequenceFiles(_group_path,
                                    self.file_ext,
                                    base_filename,
                                    first_index, 1, 1, 0, num_width,
                                    True,
                                    self.log).resequence()

                renamed_group_files = group_files(self.input_path, self.file_ext, group_name)
                with Mtqdm().open_bar(total=len(renamed_group_files), desc="Copying") as file_bar:
                    for file_index, file in enumerate(renamed_group_files):
                        if group_index == 0:
                            # for the first group, include the first file also
                            # it is the outer anchor frame at beginning
                            if file_index == len(renamed_group_files)-1:
                                Mtqdm().update_bar(file_bar)
                                continue
                        elif group_index == len(group_names)-1:
                            # for the last group, include the last file also
                            # it is the outer ancjor frame and the end
                            if file_index == 0:
                                Mtqdm().update_bar(file_bar)
                                continue
                        else:
                            # for all other groups copy all but the first & last files
                            # they are duplicate anchor frames added to support resynthesis
                            if file_index == 0 or file_index == len(renamed_group_files)-1:
                                Mtqdm().update_bar(file_bar)
                                continue

                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(
                                f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)

                # restore the original filenames
                self.log(f"Restoring original filenames in {_group_path}")
                with Mtqdm().open_bar(total=len(renamed_group_files),
                                        desc="Renaming") as bar:
                    for index, file in enumerate(renamed_group_files):
                        original_filename = _group_files[index]
                        if self.dry_run:
                            print(
                            f"[Dry Run] Restoring file '{file}' to '{original_filename}'")
                        else:
                            self.log(f"Restoring file '{file}' to '{original_filename}'")
                            os.replace(file, original_filename)
                        Mtqdm().update_bar(bar)
                Mtqdm().update_bar(group_bar)

    def merge_resynthesis_combine(self, first_index, last_index, num_width, group_size, group_names):
        expected_files = group_size # outer anchor frames not present resynthesis

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_index, group_name in enumerate(group_names):
                group_expected_files = expected_files

                if group_index == 0:
                    # one fewer frame; outer frames can't have anchor frames
                    group_expected_files -=1
                elif group_index == len(group_names)-1:
                    # get this group's file count, as it may be truncated being the final group
                    # next, have one fewer frame; outer frames can't have anchor frames
                    first_index, last_index, _ = details_from_group_name(group_name)
                    group_size = last_index - first_index
                    group_expected_files = group_size - 1

                _group_files = group_files(self.input_path, self.file_ext, group_name)
                if len(_group_files) != group_expected_files:
                    raise RuntimeError(
                        f"expected {group_expected_files} files in {group_name} but found {len(_group_files)}")

                # renumber all present files according to the first, last indexes
                # including files that will not be ulitmately copied back
                _group_path = group_path(self.input_path, group_name)
                first_index, _, _ = details_from_group_name(group_name)
                # add one since first index names a frame that has been removed
                first_index += 1

                if self.dry_run:
                    print(f"[Dry Run] Resequencing files in {_group_path}")
                else:
                    self.log(f"Resequencing files in {_group_path}")
                    base_filename = "combined-resynthesis-split"

                    ResequenceFiles(_group_path,
                                    self.file_ext,
                                    base_filename,
                                    first_index, 1, 1, 0, num_width,
                                    True,
                                    self.log).resequence()

                renamed_group_files = group_files(self.input_path, self.file_ext, group_name)
                with Mtqdm().open_bar(total=len(renamed_group_files), desc="Copying") as file_bar:
                    for file_index, file in enumerate(renamed_group_files):
                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(
                                f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)

                # restore the original filenames
                self.log(f"Restoring original filenames in {_group_path}")
                with Mtqdm().open_bar(total=len(renamed_group_files),
                                        desc="Renaming") as bar:
                    for index, file in enumerate(renamed_group_files):
                        original_filename = _group_files[index]
                        if self.dry_run:
                            print(
                            f"[Dry Run] Restoring file '{file}' to '{original_filename}'")
                        else:
                            self.log(f"Restoring file '{file}' to '{original_filename}'")
                            os.replace(file, original_filename)
                        Mtqdm().update_bar(bar)
                Mtqdm().update_bar(group_bar)

    def merge_inflation(self, group_names):
        validate_group_names(group_names)
        first_group_name = group_names[0]
        first_index, last_index, num_width = details_from_group_name(first_group_name)
        group_size = last_index - first_index
        if self.action == "combine":
            self.merge_inflation_combine(first_index, last_index, num_width, group_size, group_names)
        else:
            self.merge_inflation_revert(first_index, last_index, num_width, group_size, group_names)

    def merge_inflation_revert(self, first_index, last_index, num_width, group_size, group_names):
        expected_files = group_size + 1 # extra file is unneeded ending outer anchor

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_index, group_name in enumerate(group_names):
                group_expected_files = expected_files

                first_index, last_index, _ = details_from_group_name(group_name)

                if group_index == len(group_names)-1:
                    # last group's expected files based on its own name
                    group_expected_files = last_index - first_index + 1

                _group_files = group_files(self.input_path, self.file_ext, group_name)
                if len(_group_files) != group_expected_files:
                    raise RuntimeError(
                        f"expected {group_expected_files} files in {group_name} but found {len(_group_files)}")

                # renumber all present files according to the first, last indexes
                # including files that will not be ulitmately copied back
                _group_path = group_path(self.input_path, group_name)
                first_index, last_index, _ = details_from_group_name(group_name)
                if self.dry_run:
                    print(f"[Dry Run] Resequencing files in {_group_path}")
                else:
                    self.log(f"Resequencing files in {_group_path}")
                    base_filename = "reverted-inflated-split"

                    ResequenceFiles(_group_path,
                                    self.file_ext,
                                    base_filename,
                                    first_index, 1, 1, 0, num_width,
                                    True,
                                    self.log).resequence()

                renamed_group_files = group_files(self.input_path, self.file_ext, group_name)
                with Mtqdm().open_bar(total=len(renamed_group_files), desc="Copying") as file_bar:
                    for file_index, file in enumerate(renamed_group_files):
                        if group_index < len(group_names)-1:
                            # for all groups except last, copy all but the last file
                            # it's anchor frame duplicated during splitting
                            if file_index == len(renamed_group_files)-1:
                                Mtqdm().update_bar(file_bar)
                                continue

                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(
                                f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)

                # restore the original filenames
                self.log(f"Restoring original filenames in {_group_path}")
                with Mtqdm().open_bar(total=len(renamed_group_files),
                                        desc="Renaming") as bar:
                    for index, file in enumerate(renamed_group_files):
                        original_filename = _group_files[index]
                        if self.dry_run:
                            print(
                            f"[Dry Run] Restoring file '{file}' to '{original_filename}'")
                        else:
                            self.log(f"Restoring file '{file}' to '{original_filename}'")
                            os.replace(file, original_filename)
                        Mtqdm().update_bar(bar)
                Mtqdm().update_bar(group_bar)

    def merge_inflation_combine(self, first_index, last_index, num_width, group_size, group_names):
        first_group_files = group_files(self.input_path, self.file_ext, group_names[0])
        file_count = len(first_group_files)

        # after inflation there will be more files than accounted for in group name
        # there's a final keyframe that should not be accounted for in the detection
        detection_file_count = file_count - 1
        detected_inflation = detection_file_count / group_size
        # the detected inflation must be an even multiple of the computed group size
        if detection_file_count % group_size:
            raise RuntimeError(f"inflated file count {detection_file_count} must be" +\
                                f" a multiple of group size {group_size}")
        inflated_group_size = int(group_size * detected_inflation)
        expected_files = inflated_group_size + 1 # extra file is uneeded keyframe copied during inflation

        with Mtqdm().open_bar(total=len(group_names), desc="Groups") as group_bar:
            for group_index, group_name in enumerate(group_names):
                group_expected_files = expected_files

                first_index, last_index, _ = details_from_group_name(group_name)

                if group_index == len(group_names)-1:
                    # last group's expected files based on its own name
                    group_expected_files = (last_index - first_index) * detected_inflation + 1

                _group_files = group_files(self.input_path, self.file_ext, group_name)
                if len(_group_files) != group_expected_files:
                    raise RuntimeError(
            f"expected {group_expected_files} files in {group_name} but found {len(_group_files)}")

                # renumber all present files according to the first, last indexes
                # including files that will not be ulitmately copied back
                _group_path = group_path(self.input_path, group_name)
                first_index, last_index, _ = details_from_group_name(group_name)

                # take inflated frame counts into consideration in index used for renumbering
                first_index = int(first_index * detected_inflation)

                if self.dry_run:
                    print(f"[Dry Run] Resequencing files in {_group_path}")
                else:
                    self.log(f"Resequencing files in {_group_path}")
                    base_filename = "combined-inflation-split"

                    ResequenceFiles(_group_path,
                                    self.file_ext,
                                    base_filename,
                                    first_index, 1, 1, 0, num_width,
                                    True,
                                    self.log).resequence()

                renamed_group_files = group_files(self.input_path, self.file_ext, group_name)
                with Mtqdm().open_bar(total=len(renamed_group_files), desc="Copying") as file_bar:
                    for file_index, file in enumerate(renamed_group_files):
                        if group_index < len(group_names)-1:
                            # for all groups except last, copy all but the last file
                            # it's anchor frame duplicated during splitting
                            if file_index == len(renamed_group_files)-1:
                                Mtqdm().update_bar(file_bar)
                                continue

                        _, filename, ext = split_filepath(file)
                        to_filepath = os.path.join(self.output_path, filename + ext)
                        if os.path.exists(to_filepath):
                            raise RuntimeError(
                                f"file {to_filepath} already exists in the output path")
                        if self.dry_run:
                            print(f"[Dry Run] copying {file} to {to_filepath}")
                        else:
                            self.log(f"copying {file} to {to_filepath}")
                            shutil.copy(file, to_filepath)
                        Mtqdm().update_bar(file_bar)

                # restore the original filenames
                self.log(f"Restoring original filenames in {_group_path}")
                with Mtqdm().open_bar(total=len(renamed_group_files),
                                        desc="Renaming") as bar:
                    for index, file in enumerate(renamed_group_files):
                        original_filename = _group_files[index]
                        if self.dry_run:
                            print(
                            f"[Dry Run] Restoring file '{file}' to '{original_filename}'")
                        else:
                            self.log(f"Restoring file '{file}' to '{original_filename}'")
                            os.replace(file, original_filename)
                        Mtqdm().update_bar(bar)
                Mtqdm().update_bar(group_bar)

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
