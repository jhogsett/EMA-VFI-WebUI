import os
import shutil
import pytest # pylint: disable=import-error
from .file_utils import is_safe_path

FIXTURE_PATH = os.path.join(os.path.abspath("test_fixtures"))
FIXTURE_PATH_BAD = os.path.join(FIXTURE_PATH, "bad")
FIXTURE_PATH_ALT = os.path.join(FIXTURE_PATH, "alt")
FIXTURE_EXTENSION = "png"
FIXTURE_PNG_LIST = [os.path.join(FIXTURE_PATH, file)
                    for file in ["image0.png", "image1.png", "image2.png"]]
FIXTURE_GIF_LIST = [os.path.join(FIXTURE_PATH, "example.gif")]
FIXTURE_FILES = FIXTURE_PNG_LIST + ["example.gif"]

def clean_fixture_path(path : str | None):
    """Remove directories created under FIXTURE_PATH"""
    cleaned = False
    if path:
        path = path.replace("/", os.sep).replace("\\", os.sep)
        if path[:len(FIXTURE_PATH)] == FIXTURE_PATH:
            if is_safe_path(path):
                remainder_path = path[len(FIXTURE_PATH):]
                if remainder_path:
                    root_dir = remainder_path.strip(os.sep).split(os.sep)[0]
                    root_path = os.path.join(FIXTURE_PATH, root_dir)
                    if os.path.exists(root_path):
                        shutil.rmtree(root_path, ignore_errors=False)
                        cleaned = True
            else:
                raise ValueError(f"attempt to clean unsafe path {path}")
        else:
            raise ValueError(f"unable to clean path {path}")
    return cleaned

BAD_clean_fixture_path_ARGS = [
    (".", r"unable to clean path.*"),
    ("..", r"unable to clean path.*"),
    ("\\", r"unable to clean path.*"),
    ("/", r"unable to clean path.*"),
    (os.path.join(FIXTURE_PATH, "."), r"attempt to clean unsafe path.*"),
    (os.path.join(FIXTURE_PATH, ".."), r"attempt to clean unsafe path.*"),
    (os.path.join(FIXTURE_PATH, "../dir"), r"attempt to clean unsafe path.*"),
    (os.path.join(FIXTURE_PATH, "dir/../dir"), r"attempt to clean unsafe path.*"),
    (os.path.join(FIXTURE_PATH, "..\\dir"), r"attempt to clean unsafe path.*"),
    (os.path.join(FIXTURE_PATH, "dir\\..\\dir"), r"attempt to clean unsafe path.*"),
]

GOOD_clean_fixture_path_ARGS = [
    (FIXTURE_PATH, False),
    (None, False),
    ("", False),
    (FIXTURE_PATH_BAD, True),
    (os.path.join(FIXTURE_PATH, "testdir"), True),
    (os.path.join(FIXTURE_PATH, "testdir/subdir"), True),
    (os.path.join(FIXTURE_PATH, "testdir\\subdir"), True),
    (os.path.join(FIXTURE_PATH, "testdir/dir/dir/dir"), True),
]

def test_clean_fixture_path():
    for bad_args, match_text in BAD_clean_fixture_path_ARGS:
        with pytest.raises(ValueError, match=match_text):
            clean_fixture_path(bad_args)

    for path, should_clean in GOOD_clean_fixture_path_ARGS:
        if should_clean:
            assert not os.path.exists(path)
            os.makedirs(path)
        assert should_clean == clean_fixture_path(path)
        if should_clean:
            remainder_path = path[len(FIXTURE_PATH):]
            root_dir = remainder_path.strip(os.sep).split(os.sep)[0]
            assert len(root_dir) > 0
            root_path = os.path.join(FIXTURE_PATH, root_dir)
            assert not os.path.exists(root_path)

