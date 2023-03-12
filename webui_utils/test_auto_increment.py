import pytest # pylint: disable=import-error
from .test_shared import *
from .file_utils import get_files, get_directories, create_directory
from .auto_increment import *

GOOD_AIF_EXAMPLES = [
    ((FIXTURE_PATH, "*"), ("file", "txt"), (os.path.join(FIXTURE_PATH, "file4.txt"), 4)),
    ((FIXTURE_PATH, None), ("file", "txt"), (os.path.join(FIXTURE_PATH, "file4.txt"), 4)),
    ((FIXTURE_PATH, FIXTURE_EXTENSION), ("file", "txt"), (os.path.join(FIXTURE_PATH, "file3.txt"), 3)),
    ((FIXTURE_PATH, "doesnotexist"), ("file", "txt"), (os.path.join(FIXTURE_PATH, "file0.txt"), 0)),
    ((FIXTURE_PATH_ALT, FIXTURE_EXTENSION), ("file", "txt"), (os.path.join(FIXTURE_PATH_ALT, "file0.txt"), 0))
]

BAD_AIF_EXAMPLES = [
    ((1, "*"), (None, None), False, "'path' must be a string"),
    ((2.0, "*"), (None, None), False, "'path' must be a string"),
    (({3:3}, "*"), (None, None), False, "'path' must be a string"),
    (([4], "*"), (None, None), False, "'path' must be a string"),
    ((None, "*"), (None, None), False, "'path' must be a legal path"),
    (("", "*"), (None, None), False, "'path' must be a legal path"),
    ((".", "*"), (None, None), False, "'path' must be a legal path"),
    (("..", "*"), (None, None), False, "'path' must be a legal path"),
    (("../..", "*"), (None, None), False, "'path' must be a legal path"),
    (("test/../test", "*"), (None, None), False, "'path' must be a legal path"),
    (("..\\..", "*"), (None, None), False, "'path' must be a legal path"),
    (("test\\..\\test", "*"), (None, None), False, "'path' must be a legal path"),
    ((FIXTURE_PATH, "*"), (None, None), True, "'basename' must be a string"),
    ((FIXTURE_PATH, "*"), (1, None), True, "'basename' must be a string"),
    ((FIXTURE_PATH, "*"), (2.0, None), True, "'basename' must be a string"),
    ((FIXTURE_PATH, "*"), ({3:3}, None), True, "'basename' must be a string"),
    ((FIXTURE_PATH, "*"), ([4], None), True, "'basename' must be a string"),
    ((FIXTURE_PATH, "*"), ("", None), True, "'basename' must be a non-empty string")]

def test_AutoIncrementFilename():
    assert len(FIXTURE_FILES) == len(get_files(FIXTURE_PATH, "*"))

    for class_args, instance_args, expected in GOOD_AIF_EXAMPLES:
        assert expected == AutoIncrementFilename(*class_args).next_filename(*instance_args)

    for class_args, instance_args, test_instance, match_text in BAD_AIF_EXAMPLES:
        if not test_instance:
            # instantiating the class should raise the error
            with pytest.raises(ValueError, match=match_text):
                AutoIncrementFilename(*class_args)
        else:
            # calling the 'next' function should raise the error
            try:
                instance = AutoIncrementFilename(*class_args)
            except:
                assert False, "instantiating the class should not raise an error"
            with pytest.raises(ValueError, match=match_text):
                instance.next_filename(*instance_args)

GOOD_AID_EXAMPLES = [
    (FIXTURE_PATH, ("directory", False), (os.path.join(FIXTURE_PATH, "directory1"), 1), 1),
    (FIXTURE_PATH, ("directory", True), (os.path.join(FIXTURE_PATH, "directory1"), 1), 2),
    (FIXTURE_PATH_ALT, ("directory", False), (os.path.join(FIXTURE_PATH_ALT, "directory0"), 0), 0),
    (FIXTURE_PATH_ALT, ("directory", True), (os.path.join(FIXTURE_PATH_ALT, "directory0"), 0), 1)]

BAD_AID_EXAMPLES = [
    (None, (None, None), False, "'path' must be a legal path"),
    (1, (None, None), False, "'path' must be a string"),
    (2.0, (None, None), False, "'path' must be a string"),
    ({3:3}, (None, None), False, "'path' must be a string"),
    ([4], (None, None), False, "'path' must be a string"),
    ("", (None, None), False, "'path' must be a legal path"),
    (".", (None, None), False, "'path' must be a legal path"),
    ("..", (None, None), False, "'path' must be a legal path"),
    ("../..", (None, None), False, "'path' must be a legal path"),
    ("test/../test", (None, None), False, "'path' must be a legal path"),
    ("..\\..", (None, None), False, "'path' must be a legal path"),
    ("test\\..\\test", (None, None), False, "'path' must be a legal path"),
    (FIXTURE_PATH, (None, None), True, "'basename' must be a string"),
    (FIXTURE_PATH, (1, None), True, "'basename' must be a string"),
    (FIXTURE_PATH, (2.0, None), True, "'basename' must be a string"),
    (FIXTURE_PATH, ({3:3}, None), True, "'basename' must be a string"),
    (FIXTURE_PATH, ([4], None), True, "'basename' must be a string"),
    (FIXTURE_PATH, ("", None), True, "'basename' must be a non-empty string")]

def test_AutoIncrementDirectory():
    create_directory(FIXTURE_PATH_ALT)
    try:
        for class_args, instance_args, expected, expected_dirs in GOOD_AID_EXAMPLES:
            result = AutoIncrementDirectory(class_args).next_directory(*instance_args)
            root_path = class_args
            dir_count = len(get_directories(root_path))
            auto_create = instance_args[1]
            new_path = result[0]
            if auto_create:
                clean_fixture_path(new_path)
            assert result == expected
            assert dir_count == expected_dirs
    finally:
        clean_fixture_path(FIXTURE_PATH_ALT)

    for class_args, instance_args, test_instance, match_text in BAD_AID_EXAMPLES:
        if not test_instance:
            # instantiating the class should raise the error
            with pytest.raises(ValueError, match=match_text):
                AutoIncrementDirectory(class_args)
        else:
            # calling the 'next' function should raise the error
            try:
                instance = AutoIncrementDirectory(class_args)
            except:
                assert False, "instantiating the class should not raise an error"
            with pytest.raises(ValueError, match=match_text):
                instance.next_directory(*instance_args)
