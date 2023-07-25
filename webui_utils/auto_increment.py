"""Classes for managing auto-incrementing files and directories"""
import os
import glob
from .file_utils import get_files, get_directories, is_safe_path, split_filepath

class AutoIncrementFilename():
    """Encapsulates logic to create new unique sequentially-numbered filenames"""
    def __init__(self, path : str, extension : str | None):
        self.path = path
        if not is_safe_path(path):
            raise ValueError("'path' must be a legal path")
        self.running_file_count = len(get_files(path, extension))

    def next_filename(self, basename : str, extension : str) -> tuple[str, int]:
        """Compute the next filename"""
        if isinstance(basename, str):
            if basename:
                filename = os.path.join(self.path, f"{basename}{self.running_file_count}.{extension}")
                this_index = self.running_file_count
                self.running_file_count += 1
                return filename, this_index
            else:
                raise ValueError("'basename' must be a non-empty string")
        else:
            raise ValueError("'basename' must be a string")

class AutoIncrementDirectory():
    """Encapsulates logic to create new unique sequentially-numbered directories"""
    def __init__(self, path : str):
        self.path = path
        if not is_safe_path(path):
            raise ValueError("'path' must be a legal path")
        self.running_dir_count = len(get_directories(path))

    def next_directory(self, basename : str, auto_create=True) -> tuple[str, int]:
        """Compute the next directory and optionally create it"""
        if isinstance(basename, str):
            if basename:
                dirname = os.path.join(self.path, f"{basename}{self.running_dir_count}")
                if auto_create:
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                this_index = self.running_dir_count
                self.running_dir_count += 1
                return dirname, this_index
            else:
                raise ValueError("'basename' must be a non-empty string")
        else:
            raise ValueError("'basename' must be a string")

class AutoIncrementBackupFilename():
    """Encapsulates logic to save a uniquely numbered backup file"""
    def __init__(self, filepath : str, backup_path : str):
        self.filepath = filepath
        self.backup_path = backup_path

    def next_filepath(self):
        _, filename, ext = split_filepath(self.filepath)
        filename_filter = f"{filename}*{ext}"
        filepath = os.path.join(self.backup_path, filename_filter)
        files = glob.glob(filepath)
        count = len(files)
        next_filename = f"{filename}{count+1}{ext}"
        return os.path.join(self.backup_path, next_filename )
