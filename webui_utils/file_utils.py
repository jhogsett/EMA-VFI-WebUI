"""Functions for dealing with files"""
import os
import glob
from zipfile import ZipFile

def is_safe_path(path : str | None):
    if isinstance(path, (str, type(None))):
        if path == None:
            return False
        path = path.replace("/", os.sep).replace("\\", os.sep)
        norm_path = os.path.normpath(os.sep + path).lstrip(os.sep)
        return len(norm_path) > 0 and path == norm_path
    else:
        raise ValueError("'path' must be a string or None")

def create_directory(_dir):
    """Create a directory if it does not already exist"""
    if isinstance(_dir, str):
        if is_safe_path(_dir):
            if not os.path.exists(_dir):
                os.makedirs(_dir)
        else:
            raise ValueError("'_dir' must be a legal path")
    else:
        raise ValueError("'_dir' must be a string")

def create_directories(dirs : dict):
    """Create directories stored as dict values"""
    for key in dirs.keys():
        create_directory(dirs[key])

def _get_files(path : str):
    entries = glob.glob(path)
    files = []
    for entry in entries:
        if not os.path.isdir(entry):
            files.append(entry)
    return files

def _get_types(extension : str | list | None) -> list:
    extensions = []
    if isinstance(extension, type(None)):
        extensions.append("*")
    elif isinstance(extension, str):
        extensions += extension.split(",")
    elif isinstance(extension, list):
        extensions += extension
    result, unused = [], []
    for ext in extensions:
        if isinstance(ext, str):
            result.append(ext.strip(" ."))
        else:
            unused.append(ext)
    return list(set(result)), unused

def get_files(path : str, extension : list | str | None=None) -> list:
    """Get a list of files in the path per the extension(s)"""
    if isinstance(path, str):
        if isinstance(extension, (list, str, type(None))):
            files = []
            extensions, bad_extensions = _get_types(extension)
            if bad_extensions:
                raise ValueError("extension list items must be a strings")
            for ext in extensions:
                files += _get_files(os.path.join(path, "*." + ext))
            return list(set(files))
        else:
            raise ValueError("'extension' must be a string, a list of strings, or 'None'")
    else:
        raise ValueError("'path' must be a string")

def get_directories(path : str) -> list:
    """Get a list of directories in the path"""
    if isinstance(path, str):
        if is_safe_path(path):
            entries = os.listdir(path)
            directories = []
            for entry in entries:
                fullpath = os.path.join(path, entry)
                if os.path.isdir(fullpath):
                    directories.append(entry)
            return directories
        else:
            raise ValueError("'path' must be a legal path")
    else:
        raise ValueError("'path' must be a string")

def create_zip(files : list, filepath : str):
    """Create a zip file from a list of files"""
    if isinstance(files, list):
        for file in files:
            if not isinstance(file, str):
                raise ValueError("'files' members must be strings")
            elif not os.path.exists(file):
                raise ValueError(f"file '{file}' does not exist")
        if not isinstance(filepath, str):
            raise ValueError("'filepath' must be a string")
        else:
            if not is_safe_path(filepath):
                raise ValueError("'filepath' must be a legal path")
            if len(filepath) < 1:
                raise ValueError("'filepath' must be a non-empty string")
        with ZipFile(filepath, "w") as zip_obj:
            for file in files:
                zip_obj.write(file, arcname=os.path.basename(file))
    else:
        raise ValueError("'files' must be a list")

def locate_frame_file(png_files_path : str, frame_number : int | float) -> str | None:
    """Given a path and index, return the file found at that sorted position"""
    if not isinstance(png_files_path, str):
        raise ValueError("'png_files_path' must be a string")
    if not is_safe_path(png_files_path):
        raise ValueError("'png_files_path' must be a legal path")
    if not isinstance(frame_number, (int, float)):
        raise ValueError("'frame_number' must be an int or float")
    frame_number = int(frame_number)
    files = sorted(get_files(png_files_path, "png"))
    if 0 <= frame_number < len(files):
        if os.path.exists(png_files_path):
            return files[frame_number]
    return None

def split_filepath(filepath : str):
    """Split a filepath into path, filename, extension"""
    if isinstance(filepath, str):
        path, filename = os.path.split(filepath)
        filename, ext = os.path.splitext(filename)
        return path, filename, ext
    else:
        raise ValueError("'filepath' must be a string")

def build_filename(base_file_ext : str | None, file_part : str | None, ext_part : str | None):
    """Build a new filename from a base with optional replacements for name and type"""
    if isinstance(base_file_ext, (str, type(None))):
        if base_file_ext:
            base_file, base_ext = os.path.splitext(base_file_ext)
        else:
            base_file, base_ext = "", ""
    else:
        raise ValueError("'base_file_ext' must be a string or None")
    if isinstance(file_part, (str, type(None))):
        if file_part != None:
            filename = file_part
        else:
            filename = base_file
    else:
        raise ValueError("'file_part' must be a string or None")
    if isinstance(ext_part, (str, type(None))):
        if ext_part != None:
            extension = ext_part
        else:
            extension = base_ext
    else:
        raise ValueError("'ext_part' must be a string or None")
    extension = extension.strip(".")
    if extension:
        extension = "." + extension
    return f"{filename}{extension}" #if filename and extension else ""

# extension can be None if it is included with the filename argument
def build_indexed_filename(filename : str, extension : str | None, index : int | float, max_index : int | float):
    """Build a new filename including an integer index from a base filename + extension"""
    if not isinstance(filename, str):
        raise ValueError("'filename' must be a string")
    if isinstance(extension, (str, type(None))):
        if extension == None:
            filename, extension = os.path.splitext(filename)
        extension = extension.strip(".")
        if extension:
            extension = "." + extension
    else:
        raise ValueError("'extension' must be a string or None")
    if isinstance(index, (int, float)):
        index = int(index)
        if index < 0:
            raise ValueError("'index' value must be >= 0")
    else:
        raise ValueError("'index' must be an int or float")
    if isinstance(max_index, (int, float)):
        max_index = int(max_index)
        if max_index < 1:
            raise ValueError("'max_index' value must be >= 1")
        if max_index < index:
            raise ValueError("'max_index' value must be >= 'index'")
    else:
        raise ValueError("'max_index' must be an int or float")
    num_width = len(str(max_index))
    return f"{filename}{str(index).zfill(num_width)}{extension}"

def build_series_filename(base_filename : str | None, output_type : str | None, index : int | float, max_index : int | float, input_filename : str | None):
    """Build an output filename for a series operation, given a base filename, output type,
       index, index range and optional overriding original filename"""
    if base_filename:
        base_filename = build_indexed_filename(base_filename, None, index, max_index)
    return build_filename(input_filename, base_filename, output_type)
