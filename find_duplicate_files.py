"""Find Duplicate0 Files Feature Core Code"""
import argparse
import glob
import hashlib
import os
import time
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.mtqdm import Mtqdm
# from PIL import Image

def main():
    """Use the Find Duplicate Files feature from the command line"""
    parser = argparse.ArgumentParser(description='Find Duplicate files')
    parser.add_argument("--path", default="./", type=str,
        help="Path to files to check (default: '.\')")
    parser.add_argument("--path2", default="", type=str,
        help="Secondary path to files to check (optional, default none)")
    parser.add_argument("--type", default="*", type=str,
        help="Type of files to check (default: all types)")
    parser.add_argument("--subpaths", dest="recursive", default=False, action="store_true",
        help="Recursively check all sub-paths")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    FindDuplicateFiles(args.path, args.path2, args.type, args.recursive, log.log).find()

class FindDuplicateFiles:
    """Encapsulate logic for Find Duplicate Files feature"""
    def __init__(self,
                path : str,
                path2 : str,
                type : str,
                recursive : bool,
                log_fn : Callable | None):
        self.path = path
        self.path2 = path2
        self.type = type
        self.recursive = recursive
        self.log_fn = log_fn

    def find(self) -> None:
        """Invoke the Find Duplicate Files feature"""
        wildcard = f"*.{self.type}"
        files = []
        files2 = []
        if self.recursive:
            files = sorted(glob.glob(os.path.join(self.path, "**", wildcard), recursive=True))
            if self.path2:
                files2 = sorted(glob.glob(os.path.join(self.path2, "**", wildcard), recursive=True))
        else:
            files = sorted(glob.glob(os.path.join(self.path, wildcard), recursive=False))
            if self.path2:
                files2 = sorted(glob.glob(os.path.join(self.path2, wildcard), recursive=False))
        files = files + files2

        num_files = len(files)
        self.log(f"Found {num_files} files")

        files_info = {}

        if files:
            with Mtqdm().open_bar(len(files), desc="Inspecting Files") as bar:
                for file in files:
                    file_info = {}
                    file_info["basename"] = os.path.basename(file)
                    file_info["abspath"] = os.path.abspath(file)
                    stats = os.stat(file)
                    file_info["stats"] = stats
                    file_info["bytes"] = stats.st_size
                    file_info["modified"] = stats.st_mtime
                    file_info["created"] = stats.st_ctime
                    file_info["hash"] = FindDuplicateFiles.compute_file_hash(file)
                    files_info[file] = file_info
                    Mtqdm().update_bar(bar)

        if files_info:
            result = {}
            kinds = ["basename", "bytes", "modified", "created", "hash"]
            for kind in kinds:
                kind_result = []
                dupes = self.find_duplicate_info(files_info, kind)
                if dupes:
                    dupe_list = [dupe['info'] for dupe in dupes]
                    dupe_set = sorted(set(dupe_list))
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
            if result:
                reports = []
                kind1_seen = []
                kind2_seen = []

                with Mtqdm().open_bar(len(kinds) * (len(kinds)-1), desc="Finding Doubles") as bar:

                    kind_keys1 = result.keys()
                    for kind1 in kind_keys1:
                        kind1_seen.append(kind1)
                        dupes1 = result[kind1]

                        kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                        for kind2 in kind_keys2:
                            kind2_seen.append(kind2)
                            dupes2 = result[kind2]

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
                        bar.update()

                for report in reports:
                    print()
                    print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}]:")
                    for entry in report['dupes']:
                        print(entry)
                    print()




                reports = []
                kind1_seen = []
                kind2_seen = []
                kind3_seen = []

                with Mtqdm().open_bar(len(kinds) * (len(kinds)-1) * (len(kinds)-2), desc="Finding Triples") as bar:

                    kind_keys1 = result.keys()
                    for kind1 in kind_keys1:
                        kind1_seen.append(kind1)
                        dupes1 = result[kind1]

                        kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                        for kind2 in kind_keys2:
                            kind2_seen.append(kind2)
                            dupes2 = result[kind2]

                            kind_keys3 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen]
                            for kind3 in kind_keys3:
                                kind3_seen.append(kind3)
                                dupes3 = result[kind3]

                                for dupe in dupes1:
                                    kind_values1 = sorted(dupe.keys())

                                    for dupe2 in dupes2:
                                        kind_values2 = sorted(dupe2.keys())

                                        for dupe3 in dupes3:
                                            kind_values3 = sorted(dupe3.keys())

                                            for kind_value in kind_values1:
                                                entries1 = dupe[kind_value]
                                                entries_paths1 = [entry['abspath'] for entry in entries1]

                                                for kind_value2 in kind_values2:
                                                    entries2 = dupe2[kind_value2]
                                                    entries_paths2 = [entry['abspath'] for entry in entries2]

                                                    for kind_value3 in kind_values3:
                                                        entries3 = dupe3[kind_value3]
                                                        entries_paths3 = [entry['abspath'] for entry in entries3]

                                                        common_entries = list(set(entries_paths1).intersection(entries_paths2).intersection(entries_paths3))
                                                        if len(common_entries) > 1:
                                                            record = {}
                                                            record["kind1"] = kind1
                                                            record["kind2"] = kind2
                                                            record["kind3"] = kind3
                                                            record["kindvalue1"] = kind_value
                                                            record["kindvalue2"] = kind_value2
                                                            record["kindvalue3"] = kind_value3
                                                            record["dupes"] = common_entries
                                                            reports.append(record)

                                bar.update()
                            bar.update()
                        bar.update()

                for report in reports:
                    print()
                    print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}] and [{report['kind3']}]")
                    for entry in report['dupes']:
                        print(entry)
                    print()






                reports = []
                kind1_seen = []
                kind2_seen = []
                kind3_seen = []
                kind4_seen = []

                with Mtqdm().open_bar(len(kinds) * (len(kinds)-1) * (len(kinds)-2) * (len(kinds)-3), desc="Finding Quaduples") as bar:

                    kind_keys1 = result.keys()
                    for kind1 in kind_keys1:
                        kind1_seen.append(kind1)
                        dupes1 = result[kind1]

                        kind_keys2 = [key for key in result.keys() if key not in kind1_seen]
                        for kind2 in kind_keys2:
                            kind2_seen.append(kind2)
                            dupes2 = result[kind2]

                            kind_keys3 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen]
                            for kind3 in kind_keys3:
                                kind3_seen.append(kind3)
                                dupes3 = result[kind3]

                                kind_keys4 = [key for key in result.keys() if key not in kind1_seen and key not in kind2_seen and key not in kind3_seen]
                                for kind4 in kind_keys4:
                                    kind4_seen.append(kind4)
                                    dupes4 = result[kind4]


                                    for dupe in dupes1:
                                        kind_values1 = sorted(dupe.keys())

                                        for dupe2 in dupes2:
                                            kind_values2 = sorted(dupe2.keys())

                                            for dupe3 in dupes3:
                                                kind_values3 = sorted(dupe3.keys())

                                                for dupe4 in dupes4:
                                                    kind_values4 = sorted(dupe4.keys())


                                                    for kind_value in kind_values1:
                                                        entries1 = dupe[kind_value]
                                                        entries_paths1 = [entry['abspath'] for entry in entries1]

                                                        for kind_value2 in kind_values2:
                                                            entries2 = dupe2[kind_value2]
                                                            entries_paths2 = [entry['abspath'] for entry in entries2]

                                                            for kind_value3 in kind_values3:
                                                                entries3 = dupe3[kind_value3]
                                                                entries_paths3 = [entry['abspath'] for entry in entries3]

                                                                for kind_value4 in kind_values4:
                                                                    entries4 = dupe4[kind_value4]
                                                                    entries_paths4 = [entry['abspath'] for entry in entries4]

                                                                    common_entries = list(set(entries_paths1).intersection(entries_paths2).intersection(entries_paths3).intersection(entries_paths4))
                                                                    if len(common_entries) > 1:
                                                                        record = {}
                                                                        record["kind1"] = kind1
                                                                        record["kind2"] = kind2
                                                                        record["kind3"] = kind3
                                                                        record["kind4"] = kind4
                                                                        record["kindvalue1"] = kind_value
                                                                        record["kindvalue2"] = kind_value2
                                                                        record["kindvalue3"] = kind_value3
                                                                        record["kindvalue4"] = kind_value4
                                                                        record["dupes"] = common_entries
                                                                        reports.append(record)

                                    bar.update()
                                bar.update()
                            bar.update()
                        bar.update()

                for report in reports:
                    print()
                    print(f"Duplicates by [{report['kind1']}] and [{report['kind2']}] and [{report['kind3']}] and [{report['kind4']}]")
                    for entry in report['dupes']:
                        print(entry)
                    print()












    @staticmethod
    def compute_file_hash(file_path : str, algorithm="sha256") -> str:
        """Compute the hash of a file using the specified algorithm."""
        hash_func = hashlib.new(algorithm)

        with open(file_path, "rb") as file:
            while chunk := file.read(8192):  # Read the file in chunks of 8192 bytes
                hash_func.update(chunk)

        return hash_func.hexdigest()

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

    def log(self, message : str) -> None:
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
