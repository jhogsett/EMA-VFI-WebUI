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
        help="Path to files to check")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    FindDuplicateFiles(args.path, log.log).find()

class FindDuplicateFiles:
    """Encapsulate logic for Find Duplicate Files feature"""
    def __init__(self,
                path : str,
                log_fn : Callable | None):
        self.path = path
        self.log_fn = log_fn

    def find(self) -> None:
        """Invoke the Find Duplicate Files feature"""
        files = sorted(glob.glob(os.path.join(self.path, "*.*")))
        num_files = len(files)
        self.log(f"Found {num_files} files")

        files_info = {}

        if files:
            with Mtqdm().open_bar(len(files), desc="Inspecting Files") as bar:
                for file in files:
                    file_info = {}
                    file_info["basename"] = os.path.basename(file)
                    stats = os.stat(file)
                    file_info["stats"] = stats
                    file_info["bytes"] = stats.st_size
                    file_info["modified"] = stats.st_mtime
                    file_info["created"] = stats.st_ctime
                    file_info["hash"] = FindDuplicateFiles.compute_file_hash(file)
                    files_info[file] = file_info
                    Mtqdm().update_bar(bar)

        if files_info:
            # for name, info in files_info.items():
                # print("File Name:", info["basename"])
                # print("File Size:", info["bytes"])
                # print("Modified:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["modified"])))
                # print("Created:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["created"])))
                # print("Hash:", info["hash"])
                # print("\r\n")

            result = {}
            kinds = ["basename", "bytes", "modified", "created", "hash"]
            for kind in kinds:
                kind_result = []
                dupes = self.find_duplicate_info(files_info, kind)
                if dupes:
                    # print(f"Duplicates by {kind}")

                    dupe_list = [dupe['info'] for dupe in dupes]
                    dupe_set = sorted(set(dupe_list))
                    # print(dupe_set)
                    for dupe_info in dupe_set:
                        dupe_result = {}
                        dupe_result_infos = []
                        for name, info in files_info.items():
                            if info[kind] == dupe_info:
                                dupe_result_infos.append(info)
                        dupe_result[dupe_info] = dupe_result_infos
                        kind_result.append(dupe_result)
                    if(kind_result):
                        result[kind] = kind_result
            if result:
                print()
                for kind, dupes in result.items():
                    print(f"Duplicates by {kind}")
                    for dupe in dupes:
                        # for kind_value, entries in dupe.items():
                        kind_values = sorted(dupe.keys())
                        for kind_value in kind_values:
                            entries = dupe[kind_value]
                            if isinstance(kind_value, int):
                                print(f"[{kind_value:,}]")
                            elif isinstance(kind_value, float):
                                # print(time.strftime('%Y-%m-%d %H:%M:%S:{}'.format(kind_value%1000), time.gmtime(kind_value/1000.0)))
                                # print(time.strftime('%Y-%m-%d %H:%M:%S:{}'.format(kind_value), time.gmtime(kind_value/1000.0)))
                                # print(kind_value)
                                milliseconds = f"{kind_value - int(kind_value):.4f}"[2:]
                                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(kind_value))}.{milliseconds}]")
                            else:
                                print(f"[{kind_value}]")
                            for entry in entries:
                                print(f"{entry['basename']}")
                        print()
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
