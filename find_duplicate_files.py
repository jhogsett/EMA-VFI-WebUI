"""Find Duplicate0 Files Feature Core Code"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import time
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
from webui_utils.color_out import ColorOut
from webui_utils.file_utils import create_directory, split_filepath
# from PIL import Image

def main():
    """Use the Find Duplicate Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Find Duplicate files')
    parser.add_argument("--path", default="./", type=str,
        help="Path to files to check and deduplicate (default: '.\')")
    parser.add_argument("--path2", default=None, type=str,
        help="Secondary path to files to check (optional, default None)")
    parser.add_argument("--wild", default="*.*", type=str,
        help="Wildcard for last part of selection path (default: '*.*')")
    parser.add_argument("--subpaths", dest="recursive", default=False, action="store_true",
        help="Recursively check all sub-paths")
    parser.add_argument("--dupepath", default=None, type=str,
        help="If specified, duplicate files from path are moved to this path, preserving their directory structure (optional, default None)")
    parser.add_argument("--keep", default=None, type=str,
        help="If specified, indicates a selection 'type' for keeping a single file while dedeuplicating all others (default: None)")
    parser.add_argument("--keepre", default=None, type=str,
        help="If specified, indicates a selection regex for keeping a single file while deduplicating all others (default: None)")
    parser.add_argument("--move", dest="move", default=False, action="store_true",
        help="Move duplicate files in path1 to 'dupepath'")
    parser.add_argument("--funnel", dest="funnel", default=False, action="store_true",
        help="Repeatedly deduplicate to auto-numbered directories")
    parser.add_argument("--defunnel", dest="defunnel", default=False, action="store_true",
        help="Undo a funnel operation")

    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    if args.keep and args.keep not in FindDuplicateFiles.KEEPTYPES:
        ColorOut(f"Please choose one of these values for '--keep':\r\n{', '.join(FindDuplicateFiles.KEEPTYPES)}", "green")
        return

    if args.dupepath and not args.keep:
        ColorOut(f"Please include the '--keep' argument whe specifying '--dupepath'", "green")
        return

    if args.keep and not args.dupepath:
        ColorOut("Please include the '--dupepath' argument when specifying '--keep'", "green")
        return

    if args.keepre:
        ColorOut("The '-keepre' feature is not yet implemented", "green")
        return

    log = SimpleLog(args.verbose)
    if args.funnel:
        FindDuplicateFiles(args.path, args.path2, args.wild, args.recursive, args.dupepath, args.keep, args.keepre, args.move, log.log).funnel()
    elif args.defunnel:
        FindDuplicateFiles(args.path, args.path2, args.wild, args.recursive, args.dupepath, args.keep, args.keepre, args.move, log.log).defunnel()
    else:
        FindDuplicateFiles(args.path, args.path2, args.wild, args.recursive, args.dupepath, args.keep, args.keepre, args.move, log.log).find()

class FindDuplicateFiles:
    """Encapsulate logic for Find Duplicate Files feature"""
    def __init__(self,
                path : str,
                path2 : str,
                wild : str,
                recursive : bool,
                dupepath : str,
                keep : str,
                keepre : str,
                move : bool,
                log_fn : Callable | None):
        self.path = path
        self.path2 = path2
        self.wild = wild
        self.recursive = recursive
        self.dupepath = dupepath
        self.keep = keep
        self.keepre = keepre
        self.move = move
        self.log_fn = log_fn

    KEEPTYPES = [
        # 'firstfound',
        # 'lastfound',
        # 'shortestpath',
        # 'longestpath',
        # 'shortestname',
        # 'longestname',
        # 'mostcomplexname',
        # 'leastcomplexname',
        'mostcomplexpath',
        # 'leastcomplexpath',
        # 'createdoldest',
        # 'creatednewest',
        # 'modifieddoldest',
        # 'modifieddnewest',
        # 'random'
    ]

    def defunnel(self) -> None:
        """
        Flatten a set of directories previously created using self.funnel()
        """
        print("First dedplication")
        glob_dedupe_path = os.path.join(self.dupepath, "**", "*.*")

        files = sorted(glob.glob(glob_dedupe_path, recursive=True))
        with Mtqdm().open_bar(len(files), desc="Restoring Files") as bar:
            for file in files:
                if self.move:
                    try:
                        shutil.move(file, self.path)
                    except Exception as error:
                        self.log(f"error {str(error)} for file {file})")
                bar.update()

        step = 0
        while True:
            step += 1
            deeper_path = f"{self.dupepath}{step:02d}"
            if not os.path.exists(deeper_path):
                break

            glob_deeper_path = os.path.join(deeper_path, "**", "*.*")
            print(f"Step {step} {glob_deeper_path}")

            files = sorted(glob.glob(glob_deeper_path, recursive=True))
            with Mtqdm().open_bar(len(files), desc="Restoring Files") as bar:
                for file in files:
                    if self.move:
                        try:
                            shutil.move(file, self.path)
                        except Exception as error:
                            self.log(f"error {str(error)} for file {file})")
                    bar.update()

        # the dupepath becomes the new root name for all the numbered paths
        # using self.dupapath as a base, move all found directories and files
        # to the original self.path



    def funnel(self) -> None:
        """
        Recursively deduplicate a directory into nested, automatically-numbered
        directories containing further duplies. Stops when no more files are moved.
        """
        # do an initial deduplication to the dupepath
        print("First dedplication")
        have_moved = self.find()
        last_dedupe_path = self.dupepath
        step = 0

        while have_moved:
            step += 1
            deeper_path = f"{self.dupepath}{step:02d}"
            print(f"Step {step}")
            have_moved = self.find(override_path=last_dedupe_path, override_dupepath=deeper_path)
            last_dedupe_path = deeper_path
            print(".", end="")
        print()

    def find(self, override_path : str | None=None, override_dupepath : str | None=None) -> int:
        """
        Invoke the Find Duplicate Files feature
        returns the count of files moved
        """
        moved = 0
        files = []
        files2 = []
        root_path = override_path or self.path
        dupe_path = override_dupepath or self.dupepath
        if self.recursive:
            path = os.path.join(root_path, "**", self.wild)
            files = sorted(glob.glob(path, recursive=True))
            if self.path2:
                files2 = sorted(glob.glob(os.path.join(self.path2, "**", self.wild), recursive=True))
        else:
            path = os.path.join(root_path, self.wild)
            files = sorted(glob.glob(path, recursive=False))
            if self.path2:
                files2 = sorted(glob.glob(os.path.join(self.path2, self.wild), recursive=False))
        files = files + files2
        num_files = len(files)
        self.log(f"Found {num_files} files")

        files_info = {}
        inaccessible_paths = {}

        if files:
            with Mtqdm().open_bar(len(files), desc="Collecting File Data") as bar:
                for file in files:
                    file_info = {}
                    file_info["basename"] = os.path.basename(file)
                    file_info["abspath"] = os.path.abspath(file)
                    stats = os.stat(file)
                    file_info["stats"] = stats
                    file_info["bytes"] = stats.st_size
                    file_info["modified"] = stats.st_mtime
                    file_info["created"] = stats.st_ctime

                    try:
                        file_info["hash"] = FindDuplicateFiles.compute_file_hash(file)
                    except Exception as error:
                        inaccessible_paths[file] = str(error)
                        self.log(f"\r\nSkipping file {file} due to error: {str(error)}")
                        continue

                    files_info[file] = file_info
                    Mtqdm().update_bar(bar)

        if inaccessible_paths:
            # print("Inaccessible Paths:")
            for path, error in inaccessible_paths.items():
                # print(f"{path} : {error}")
                files.remove(path)

        if files_info:
            result = {}
            kinds = [
                "hash",
                "bytes",
                # "basename",
                # "modified",
                # "created",
            ]

            with Mtqdm().open_bar(len(kinds), desc="Finding Duplicates") as bar:
                for kind in kinds:
                    kind_result = []
                    dupes = self.find_duplicate_info(files_info, kind)
                    if dupes:
                        dupe_list = [dupe['info'] for dupe in dupes]
                        dupe_set = sorted(set(dupe_list))
                        with Mtqdm().open_bar(len(dupe_set), desc=f"Scanning for [{kind}] Matches") as bar2:
                            for dupe_info in dupe_set:
                                dupe_result = {}
                                dupe_result_infos = []
                                for _, info in files_info.items():
                                    if info[kind] == dupe_info:
                                        dupe_result_infos.append(info)

                                dupe_result[dupe_info] = dupe_result_infos
                                kind_result.append(dupe_result)

                                if(kind_result):
                                    result[kind] = kind_result
                                bar2.update()
                    bar.update()

            if result:
                reports = []
                kind1_seen = []
                kind2_seen = []

                kind_keys1 = result.keys()
                for kind1 in kind_keys1:
                    kind1_seen.append(kind1)
                    dupes1 = result[kind1]

                    kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                    for kind2 in kind_keys2:
                        kind2_seen.append(kind2)
                        dupes2 = result[kind2]

                        with Mtqdm().open_bar(len(dupes1), desc="Matching Duplicates") as bar:
                            for dupe in dupes1:
                                kind_values1 = sorted(dupe.keys())

                                for dupe2 in dupes2:
                                    kind_values2 = sorted(dupe2.keys())

                                    for kind_value in kind_values1:
                                        entries1 = dupe[kind_value]
                                        entries_paths1 = [entry['abspath'] for entry in entries1]

                                        for kind_value2 in kind_values2:
                                            entries2 = dupe2[kind_value2]
                                            entries_paths2 = [entry['abspath'] for entry in entries2]

                                            common_entries = list(set(entries_paths1).intersection(entries_paths2))
                                            if len(common_entries) > 1:
                                                record = {}
                                                record["kind1"] = kind1
                                                record["kind2"] = kind2
                                                record["kindvalue1"] = kind_value
                                                record["kindvalue2"] = kind_value2
                                                record["dupes"] = common_entries
                                                reports.append(record)
                                bar.update()

                if dupe_path and self.keep:
                    if self.move:
                        create_directory(dupe_path)

                    for report in reports:
                        print()
                        print("-" * 100)
                        abspaths = report['dupes']
                        scores = self.abspath_complexity_scores(abspaths)
                        score_list = sorted(scores.values(), reverse=True)
                        dupe_abspaths = []

                        keep_abspath = None
                        for abspath, score in scores.items():
                            if not keep_abspath and score == score_list[0]:
                                keep_abspath = abspath
                            else:
                                dupe_abspaths.append(abspath)

                        print(f"KEEP: {keep_abspath}")
                        path_len = len(root_path)
                        for dupe in dupe_abspaths:
                            if self.path2 and dupe.startswith(self.path2):
                                continue
                            new_dupe_path = os.path.join(dupe_path, dupe[path_len+1:])
                            print(f"MOVE: {dupe} to {new_dupe_path}")
                            if self.move:
                                path, _, _ = split_filepath(new_dupe_path)
                                create_directory(path)
                                shutil.move(dupe, new_dupe_path)
                                moved += 1
                else:
                    for report in reports:
                        print()
                        print("-" * 100)
                        print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}]:")
                        for entry in report['dupes']:
                            print(entry)
                        print()




                # reports = []
                # kind1_seen = []
                # kind2_seen = []
                # kind3_seen = []

                # kind_keys1 = result.keys()
                # with Mtqdm().open_bar(len(kind_keys1), desc="Finding Triple Matches-1") as bar:
                #     for kind1 in kind_keys1:
                #         kind1_seen.append(kind1)
                #         dupes1 = result[kind1]

                #         kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                #         with Mtqdm().open_bar(len(kind_keys2), desc="Finding Triple Matches-2") as bar2:
                #             for kind2 in kind_keys2:
                #                 kind2_seen.append(kind2)
                #                 dupes2 = result[kind2]

                #                 kind_keys3 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen]
                #                 with Mtqdm().open_bar(len(kind_keys3), desc="Finding Triple Matches-3") as bar3:
                #                     for kind3 in kind_keys3:
                #                         kind3_seen.append(kind3)
                #                         dupes3 = result[kind3]

                #                         with Mtqdm().open_bar(len(dupes1), desc="Examinging Duplicates-1") as bar4:
                #                             for dupe in dupes1:
                #                                 kind_values1 = sorted(dupe.keys())

                #                         # with Mtqdm().open_bar(len(dupes1), desc="Examinging Duplicates-2") as bar5:
                #                             for dupe2 in dupes2:
                #                                 kind_values2 = sorted(dupe2.keys())

                #                                 for dupe3 in dupes3:
                #                                     kind_values3 = sorted(dupe3.keys())

                #                                     for kind_value in kind_values1:
                #                                         entries1 = dupe[kind_value]
                #                                         entries_paths1 = [entry['abspath'] for entry in entries1]

                #                                         for kind_value2 in kind_values2:
                #                                             entries2 = dupe2[kind_value2]
                #                                             entries_paths2 = [entry['abspath'] for entry in entries2]

                #                                             for kind_value3 in kind_values3:
                #                                                 entries3 = dupe3[kind_value3]
                #                                                 entries_paths3 = [entry['abspath'] for entry in entries3]

                #                                                 common_entries = list(set(entries_paths1).intersection(entries_paths2).intersection(entries_paths3))
                #                                                 if len(common_entries) > 1:
                #                                                     record = {}
                #                                                     record["kind1"] = kind1
                #                                                     record["kind2"] = kind2
                #                                                     record["kind3"] = kind3
                #                                                     record["kindvalue1"] = kind_value
                #                                                     record["kindvalue2"] = kind_value2
                #                                                     record["kindvalue3"] = kind_value3
                #                                                     record["dupes"] = common_entries
                #                                                     reports.append(record)
                #                                 # bar5.update()
                #                                 bar4.update()
                #                         bar3.update()
                #                 bar2.update()
                #         bar.update()

                # for report in reports:
                #     print()
                #     print("-" * 100)
                #     print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}] and [{report['kind3']}]")
                #     for entry in report['dupes']:
                #         print(entry)
                #     print()






                # reports = []
                # kind1_seen = []
                # kind2_seen = []
                # kind3_seen = []
                # kind4_seen = []

                # with Mtqdm().open_bar(len(kinds) * (len(kinds)-1) * (len(kinds)-2) * (len(kinds)-3), desc="Finding Full Matches") as bar:

                #     kind_keys1 = result.keys()
                #     for kind1 in kind_keys1:
                #         kind1_seen.append(kind1)
                #         dupes1 = result[kind1]

                #         kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                #         for kind2 in kind_keys2:
                #             kind2_seen.append(kind2)
                #             dupes2 = result[kind2]

                #             kind_keys3 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen]
                #             for kind3 in kind_keys3:
                #                 kind3_seen.append(kind3)
                #                 dupes3 = result[kind3]

                #                 kind_keys4 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen and key not in kind3_seen]
                #                 for kind4 in kind_keys4:
                #                     kind4_seen.append(kind4)
                #                     dupes4 = result[kind4]


                #                     for dupe in dupes1:
                #                         kind_values1 = sorted(dupe.keys())

                #                         for dupe2 in dupes2:
                #                             kind_values2 = sorted(dupe2.keys())

                #                             for dupe3 in dupes3:
                #                                 kind_values3 = sorted(dupe3.keys())

                #                                 for dupe4 in dupes4:
                #                                     kind_values4 = sorted(dupe4.keys())


                #                                     for kind_value in kind_values1:
                #                                         entries1 = dupe[kind_value]
                #                                         entries_paths1 = [entry['abspath'] for entry in entries1]

                #                                         for kind_value2 in kind_values2:
                #                                             entries2 = dupe2[kind_value2]
                #                                             entries_paths2 = [entry['abspath'] for entry in entries2]

                #                                             for kind_value3 in kind_values3:
                #                                                 entries3 = dupe3[kind_value3]
                #                                                 entries_paths3 = [entry['abspath'] for entry in entries3]

                #                                                 for kind_value4 in kind_values4:
                #                                                     entries4 = dupe4[kind_value4]
                #                                                     entries_paths4 = [entry['abspath'] for entry in entries4]

                #                                                     common_entries = list(set(entries_paths1).intersection(entries_paths2).intersection(entries_paths3).intersection(entries_paths4))
                #                                                     if len(common_entries) > 1:
                #                                                         record = {}
                #                                                         record["kind1"] = kind1
                #                                                         record["kind2"] = kind2
                #                                                         record["kind3"] = kind3
                #                                                         record["kind4"] = kind4
                #                                                         record["kindvalue1"] = kind_value
                #                                                         record["kindvalue2"] = kind_value2
                #                                                         record["kindvalue3"] = kind_value3
                #                                                         record["kindvalue4"] = kind_value4
                #                                                         record["dupes"] = common_entries
                #                                                         reports.append(record)

                #                     bar.update()
                #                 bar.update()
                #             bar.update()
                #         bar.update()

                # for report in reports:
                #     print()
                #     print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}] and [{report['kind3']}] and [{report['kind4']}]")
                #     for entry in report['dupes']:
                #         print(entry)
                #     print()

        return moved










    @staticmethod
    def compute_file_hash(file_path : str, algorithm="sha256") -> str:
        """Compute the hash of a file using the specified algorithm."""
        hash_func = hashlib.new(algorithm)

        try:
            with open(file_path, "rb") as file:
                while chunk := file.read(8192):  # Read the file in chunks of 8192 bytes
                    hash_func.update(chunk)

            return hash_func.hexdigest()
        except PermissionError as error:
            raise error

    # https://stackoverflow.com/questions/9835762/how-do-i-find-the-duplicates-in-a-list-and-create-another-list-with-them
    @staticmethod
    def find_duplicates(L : list) -> list:
        seen = set()
        seen2 = set()
        seen_add = seen.add
        seen2_add = seen2.add
        for item in L:
            if item in seen:
                seen2_add(item)
            else:
                seen_add(item)
        return list(seen2)

    # find duplicates in a dictionary, specifying the dictionary, and the nested dictionary item name to inspect
    def find_duplicate_info(self, file_info : dict, kind : str) -> list:
        entries = []
        for name, info in file_info.items():
            entries.append(info[kind])
        dupes = FindDuplicateFiles.find_duplicates(entries)
        result = []
        for name, info in file_info.items():
            if info[kind] in dupes:
                entry = {}
                entry["name"] = name
                entry["kind"] = kind
                entry["info"] = info[kind]
                result.append(entry)
        return result

    def abspath_complexity_scores(self, abspaths : list) -> dict:
        result = {}
        for abspath in abspaths:
            score = self.complexity_score(abspath)
            result[abspath] = score
        return result

    # from Gemini AI, vefified
    # prompt: I need a methodology and a python algorithm for the following:
    # I want to evaluate a set of Windows File names and determine whether they are
    # simpler or more complex, for example Maybe by more complex it means a wider variety
    # of characters or additional character sets or something. I'm looking for ideas.
    def complexity_score(self, filename):
        """
        Calculates a complexity score for a given Windows filename.

        Args:
        filename: The Windows filename to evaluate.

        Returns:
        A complexity score, where higher scores indicate higher complexity.
        """

        score = 0

        # Check for special characters
        special_chars = re.findall(r"[^\w\s\.-]", filename)
        score += len(set(special_chars)) * 2  # Weight special characters

        # Check for uppercase letters
        uppercase_count = sum(1 for char in filename if char.isupper())
        score += uppercase_count / len(filename)  # Normalize by filename length

        # Check for digits
        digit_count = sum(1 for char in filename if char.isdigit())
        score += digit_count / len(filename)  # Normalize by filename length

        # Check for length
        score += len(filename) / 100  # Normalize by length (longer filenames are slightly more complex)

        return score

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
