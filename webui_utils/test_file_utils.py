import os
import pytest # pylint: disable=import-error
from .file_utils import *
from .test_shared import *

GOOD_IS_SAFE_PATH_ARGS = [
    (FIXTURE_PATH, True),
    (FIXTURE_PATH_BAD, True),
    (os.path.join(FIXTURE_PATH, "a"), True),
    ("a", True),
    ("a/a", True),
    ("a\\a", True),
    ("", False),
    (".", False),
    ("..", False),
    ("/", False),
    ("\\", False),
    ("/.", False),
    ("\\.", False),
    ("/..", False),
    ("\\..", False),
    ("./", False),
    (".\\", False),
    ("../", False),
    ("..\\", False),
    ("../a", False),
    ("..\\a", False),
    ("a/.", False),
    ("a/..", False),
    ("a\\.", False),
    ("a\\..", False),
    ("../..", False),
    ("..\\..", False),
    ("a/../b", False),
    ("a\\..\\b", False),
    (None, False)]

BAD_IS_SAFE_PATH_ARGS = [
    (1, "'path' must be a string or None"),
    (2.0, "'path' must be a string or None"),
    ({3:3}, "'path' must be a string or None"),
    ([4], "'path' must be a string or None"),
]

def test_is_safe_path():
    for good_args, result in GOOD_IS_SAFE_PATH_ARGS:
        assert result == is_safe_path(good_args)

    for bad_args, match_text in BAD_IS_SAFE_PATH_ARGS:
        with pytest.raises(ValueError, match=match_text):
            is_safe_path(bad_args)

GOOD_CREATE_DIRECTORY_ARGS = [
    (os.path.join(FIXTURE_PATH, "testdir")),
    (os.path.join(FIXTURE_PATH, "testdir/subdir")),
    (os.path.join(FIXTURE_PATH, "testdir/dir/dir/dir"))]

BAD_CREATE_DIRECTORY_ARGS = [
    (None, "'_dir' must be a string"),
    (1, "'_dir' must be a string"),
    (2.0, "'_dir' must be a string"),
    ({3:3}, "'_dir' must be a string"),
    ([4], "'_dir' must be a string"),
    (os.path.join(FIXTURE_PATH, "."), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, ".."), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "../.."), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "testdir/."), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "../testdir"), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "../../testdir"), "'_dir' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "testdir/../somedir"), "'_dir' must be a legal path")]

def test_create_directory():
    for _dir in GOOD_CREATE_DIRECTORY_ARGS:
        assert not os.path.exists(_dir)
        create_directory(_dir)
        assert os.path.exists(_dir)
        clean_fixture_path(_dir)

    for _dir, match_text in BAD_CREATE_DIRECTORY_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_directory(_dir)

GOOD_CREATE_DIRECTORIES_ARGS = [
    ({"dir1" : os.path.join(FIXTURE_PATH, "testdir1"),
      "dir2" : os.path.join(FIXTURE_PATH, "testdir2/subdir"),
      "dir3" : os.path.join(FIXTURE_PATH, "testdir3/dir/dir/dir")}),
    ({"dir1" : os.path.join(FIXTURE_PATH, "testdir")}),
    ({})]

BAD_CREATE_DIRECTORIES_ARGS = [
    ({"dir1" : os.path.join(FIXTURE_PATH_BAD, "../testdir1"),
      "dir2" : os.path.join(FIXTURE_PATH_BAD, "testdir2/subdir"),
      "dir3" : os.path.join(FIXTURE_PATH_BAD, "testdir3/dir/dir/dir")}, "'_dir' must be a legal path"),
    ({"dir1" : os.path.join(FIXTURE_PATH_BAD, "testdir1"),
      "dir2" : os.path.join(FIXTURE_PATH_BAD, "../testdir2/subdir"),
      "dir3" : os.path.join(FIXTURE_PATH_BAD, "testdir3/dir/dir/dir")}, "'_dir' must be a legal path"),
    ({"dir1" : os.path.join(FIXTURE_PATH_BAD, "testdir1"),
      "dir2" : os.path.join(FIXTURE_PATH_BAD, "testdir2/subdir"),
      "dir3" : os.path.join(FIXTURE_PATH_BAD, "../testdir3/dir/dir/dir")}, "'_dir' must be a legal path"),
    ({"dir1" : os.path.join(FIXTURE_PATH_BAD, "../testdir1"),
      "dir2" : os.path.join(FIXTURE_PATH_BAD, "../testdir2/subdir"),
      "dir3" : os.path.join(FIXTURE_PATH_BAD, "../testdir3/dir/dir/dir")}, "'_dir' must be a legal path")]

def test_create_directories(capsys):
    for good_args in GOOD_CREATE_DIRECTORIES_ARGS:
        for name, path in good_args.items():
            if path:
                assert not os.path.exists(path)
        create_directories(good_args)
        for name, path in good_args.items():
            if path:
                assert os.path.exists(path)
                clean_fixture_path(path)

    for bad_args, match_text in BAD_CREATE_DIRECTORIES_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_directories(bad_args)
        clean_fixture_path(FIXTURE_PATH_BAD)

BAD_PATH_ARGS = [None, 1, 2.0, {3:3}, [4]]
GOOD_PATH_ARGS = [FIXTURE_PATH]
BAD_EXTENSION_ARGS = [1, 2.0, {3:3}]
GOOD_EXTENSION_ARGS = [FIXTURE_EXTENSION, None, "*", ".png", "png,gif", "png, gif", ".png,.gif",
                        ["gif", "png"], [".gif", ".png"]]
DUPLICATE_EXTENSION_ARGS = [("png", "png,png"), ("png", "png,.png"), ("*", "*,*"), ("*", "*,png")]

def test_get_files(capsys):
    # with capsys.disabled():
    #     print(os.path.abspath(FIXTURE_PATH))

    for bad_arg in BAD_PATH_ARGS:
        with pytest.raises(ValueError, match="'path' must be a string"):
            get_files(bad_arg, FIXTURE_EXTENSION)

    for bad_arg in BAD_EXTENSION_ARGS:
        with pytest.raises(ValueError, match="'extension' must be a string, a list of strings, or 'None'"):
            get_files(FIXTURE_PATH, bad_arg)

    # good paths should return real results
    for good_arg in GOOD_PATH_ARGS:
        result = get_files(good_arg, FIXTURE_EXTENSION)
        assert len(result) > 0

    # excess whitespace and dots should be ignored
    for good_arg in GOOD_EXTENSION_ARGS:
        result = get_files(FIXTURE_PATH, good_arg)
        assert len(result) > 0

    # should get a predicted set of files including the prepended path
    result = get_files(FIXTURE_PATH, FIXTURE_EXTENSION)
    assert set(result) == set(FIXTURE_PNG_LIST)

    # should not get overlapping results
    for nondupe, dupe in DUPLICATE_EXTENSION_ARGS:
        nondupe_result = get_files(FIXTURE_PATH, nondupe)
        dupe_result = get_files(FIXTURE_PATH, dupe)
        assert len(dupe_result) == len(nondupe_result)

SETUP_GET_DIRECTORIES = {
    "dir1" : os.path.join(FIXTURE_PATH_ALT, "testdir1"),
    "dir2" : os.path.join(FIXTURE_PATH_ALT, "testdir2/subdir"),
    "dir3" : os.path.join(FIXTURE_PATH_ALT, "testdir3/dir/dir/dir")}

GOOD_GET_DIRECTORIES_ARGS = [
    (FIXTURE_PATH, 1),
    (FIXTURE_PATH_ALT, 3),
    (os.path.join(FIXTURE_PATH_ALT, "testdir1"), 0),
    (os.path.join(FIXTURE_PATH_ALT, "testdir2"), 1),
    (os.path.join(FIXTURE_PATH_ALT, "testdir3"), 1),
    (os.path.join(FIXTURE_PATH_ALT, "testdir3/dir"), 1),
    (os.path.join(FIXTURE_PATH_ALT, "testdir3/dir/dir"), 1),
    (os.path.join(FIXTURE_PATH_ALT, "testdir3/dir/dir/dir"), 0)]

BAD_GET_DIRECTORIES_ARGS = [
    (None, "'path' must be a string"),
    (1, "'path' must be a string"),
    (2.0, "'path' must be a string"),
    ({3:3}, "'path' must be a string"),
    ([4], "'path' must be a string"),
    (os.path.join(FIXTURE_PATH, ".."), "'path' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "../.."), "'path' must be a legal path"),
    (os.path.join(FIXTURE_PATH, "test/../test"), "'path' must be a legal path"),
]

def test_get_directories():
    assert len(get_directories(FIXTURE_PATH)) == 0
    create_directories(SETUP_GET_DIRECTORIES)
    for path, count in GOOD_GET_DIRECTORIES_ARGS:
        assert count == len(get_directories(path))
    clean_fixture_path(FIXTURE_PATH_ALT)
    assert len(get_directories(FIXTURE_PATH)) == 0

    for path, match_text in BAD_GET_DIRECTORIES_ARGS:
        with pytest.raises(ValueError, match=match_text):
            get_directories(path)

GOOD_CREATE_ZIP_ARGS = [
    (FIXTURE_PNG_LIST, os.path.join(FIXTURE_PATH, "test.zip"), 600_000, 800_000),
    ([FIXTURE_PNG_LIST[0]], os.path.join(FIXTURE_PATH, "test.zip"), 100_000, 300_000)]

BAD_CREATE_ZIP_ARGS = [
    (None, None, "'files' must be a list"),
    ([None], None, "'files' members must be strings"),
    ([""], None, "file '' does not exist"),
    ([os.path.join(FIXTURE_PATH, "a")], "", "file .* does not exist"),
    ([FIXTURE_PNG_LIST[0]], None, "'filepath' must be a string"),
    ([FIXTURE_PNG_LIST[0]], "", "'filepath' must be a legal path"),
    ([FIXTURE_PNG_LIST[0]], "..", "'filepath' must be a legal path"),
]

def test_create_zip():
    for file_list, zip_file, min_size, max_size in GOOD_CREATE_ZIP_ARGS:
        create_zip(file_list, zip_file)
        zip_existed = os.path.exists(zip_file)
        zip_size_ok = max_size > os.path.getsize(zip_file) > min_size
        os.remove(zip_file)
        assert zip_existed
        assert zip_size_ok

    for file_list, zip_file, match_text in BAD_CREATE_ZIP_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_zip(file_list, zip_file)

GOOD_LOCATE_FRAME_FILE_ARGS = [
    ((FIXTURE_PATH, 0), FIXTURE_PNG_LIST[0]),
    ((FIXTURE_PATH, 1), FIXTURE_PNG_LIST[1]),
    ((FIXTURE_PATH, 1.0), FIXTURE_PNG_LIST[1]),
    ((FIXTURE_PATH, 2), FIXTURE_PNG_LIST[2]),
    ((FIXTURE_PATH, 100), None),
    ((FIXTURE_PATH, -1), None),
]

BAD_LOCATE_FRAME_FILE_ARGS = [
    ((None, None), "'png_files_path' must be a string"),
    (("", None), "'png_files_path' must be a legal path"),
    ((os.path.join(FIXTURE_PATH, ".."), None), "'png_files_path' must be a legal path"),
    ((FIXTURE_PATH, None), "'frame_number' must be an int or float"),
]

def test_locate_frame_file():
    for good_args, result in GOOD_LOCATE_FRAME_FILE_ARGS:
        assert result == locate_frame_file(*good_args)

    for bad_args, match_text in BAD_LOCATE_FRAME_FILE_ARGS:
        with pytest.raises(ValueError, match=match_text):
            locate_frame_file(*bad_args)

GOOD_PATH_SPLITS = [
    ("path1/path2/filename.extension", ("path1/path2", "filename", ".extension")),
    ("/filename.extension", ("/", "filename", ".extension")),
    ("/filename", ("/", "filename", "")),
    ("filename", ("", "filename", "")),
    (".filename", ("", ".filename", "")),
    (".", ("", ".", "")),
    ("", ("", "", ""))]

BAD_PATH_SPLITS = [
    (None, (None, None, None)),
    (1, (None, None, None)),
    (2.0, (None, None, None)),
    ({3:3}, (None, None, None)),
    ([4], (None, None, None))]

def test_split_filepath():
    for split_str, split_list in BAD_PATH_SPLITS:
        with pytest.raises(ValueError, match="'filepath' must be a string"):
            split_filepath(split_str) == split_list

    for split_str, split_list in GOOD_PATH_SPLITS:
        assert split_filepath(split_str) == split_list

GOOD_BUILD_FILENAME_ARGS = [
    (("filename1.ext", None, None), "filename1.ext"),
    (("filename2.ext", "", ""), ""),
    ((None, "somefile1", "txt"), "somefile1.txt"),
    (("", "somefile2", "txt"), "somefile2.txt"),
    ((None, None, None), ""),
    (("", "", ""), ""),
    (("filename1.ext", None, ".txt"), "filename1.txt"),
    (("filename2.ext", None, "txt"), "filename2.txt"),
    (("filename.ext", "somefile3", None), "somefile3.ext"),
    (("filename4.ext", "", ".txt"), ".txt"),
    (("filename5.ext", "", "txt"), ".txt"),
    (("filename.ext", "somefile4", ""), "somefile4"),
    (("filename.ext", "somefile5", "txt"), "somefile5.txt"),
    (("filename.ext", None, ""), "filename"),
    (("filename.ext", "", None), ".ext")]

BAD_BUILD_FILENAME_ARGS = [
    ((1, 1, 1), "'base_file_ext' must be a string or None"),
    ((2.0, 2.0, 2.0), "'base_file_ext' must be a string or None"),
    (({3:3}, {3:3}, {3:3}), "'base_file_ext' must be a string or None"),
    (([4], [4], [4]), "'base_file_ext' must be a string or None"),
    (("", 1, 1), "'file_part' must be a string or None"),
    (("", 2.0, 2.0), "'file_part' must be a string or None"),
    (("", {3:3}, {3:3}), "'file_part' must be a string or None"),
    (("", [4], [4]), "'file_part' must be a string or None"),
    ((None, 1, 1), "'file_part' must be a string or None"),
    ((None, 2.0, 2.0), "'file_part' must be a string or None"),
    ((None, {3:3}, {3:3}), "'file_part' must be a string or None"),
    ((None, [4], [4]), "'file_part' must be a string or None"),
    (("", "", 1), "'ext_part' must be a string or None"),
    (("", "", 2.0), "'ext_part' must be a string or None"),
    (("", "", {3:3}), "'ext_part' must be a string or None"),
    (("", "", [4]), "'ext_part' must be a string or None"),
    ((None, None, 1), "'ext_part' must be a string or None"),
    ((None, None, 2.0), "'ext_part' must be a string or None"),
    ((None, None, {3:3}), "'ext_part' must be a string or None"),
    ((None, None, [4]), "'ext_part' must be a string or None")]

def test_build_filename():
    for good_args, result in GOOD_BUILD_FILENAME_ARGS:
        assert result == build_filename(*good_args)

    for bad_args, match_text in BAD_BUILD_FILENAME_ARGS:
        with pytest.raises(ValueError, match=match_text):
            build_filename(*bad_args)

GOOD_BUILD_INDEXED_FILENAME_ARGS = [
    (("filename1", "ext", 1, 100), "filename1001.ext"),
    (("filename2.ext", None, 1, 100), "filename2001.ext"),
    (("filename3", "ext", 12345, 99999), "filename312345.ext"),
    (("filename4", "ext", 0, 100), "filename4000.ext"),
    (("", "ext", 1, 100), "001.ext"),
    (("filename5", None, 1, 100), "filename5001"),
    (("filename6", "", 1, 100), "filename6001")]

BAD_BUILD_INDEXED_FILENAME_ARGS = [
    ((None, "ext", 1, 100), "'filename' must be a string"),
    ((1, "ext", 1, 100), "'filename' must be a string"),
    ((2.0, "ext", 1, 100), "'filename' must be a string"),
    (({3:3}, "ext", 1, 100), "'filename' must be a string"),
    (([4], "ext", 1, 100), "'filename' must be a string"),
    (("", 1, 1, 100), "'extension' must be a string"),
    (("", 2.0, 1, 100), "'extension' must be a string"),
    (("", {3:3}, 1, 100), "'extension' must be a string"),
    (("", [4], 1, 100), "'extension' must be a string"),
    (("", "", None, 100), "'index' must be an int or float"),
    (("", "", "", 100), "'index' must be an int or float"),
    (("", "", {3:3}, 100), "'index' must be an int or float"),
    (("", "", [4], 100), "'index' must be an int or float"),
    (("", "", 0, None), "'max_index' must be an int or float"),
    (("", "", 0, ""), "'max_index' must be an int or float"),
    (("", "", 0, {3:3}), "'max_index' must be an int or float"),
    (("", "", 0, [4]), "'max_index' must be an int or float"),
    (("", "", -1, 100), "'index' value must be >= 0"),
    (("", "", -2.0, 100), "'index' value must be >= 0"),
    (("", "", 0, -1), "'max_index' value must be >= 1"),
    (("", "", 0, -2.0), "'max_index' value must be >= 1"),
    (("", "", 100, 90), "'max_index' value must be >= 'index'")]

def test_build_indexed_filename():
    for good_args, result in GOOD_BUILD_INDEXED_FILENAME_ARGS:
        assert result == build_indexed_filename(*good_args)

    for bad_args, match_text in BAD_BUILD_INDEXED_FILENAME_ARGS:
        with pytest.raises(ValueError, match=match_text):
            build_indexed_filename(*bad_args)

GOOD_BUILD_SERIES_FILENAME_ARGS = [
    (("pngsequence", "png", 1, 10, None), "pngsequence01.png"),
    (("pngsequence", ".png", 2, 100, None), "pngsequence002.png"),
    (("pngsequence", "gif", 10, 1000, "somefile.txt"), "pngsequence0010.gif"),
    (("pngsequence00", "png", 1, 10, None), "pngsequence0001.png"),
    (("pngsequence", None, 1, 9, "somefile.txt"), "pngsequence1.txt"),
    ((None, "jpg", 0, 9, "somefile.txt"), "somefile.jpg"),
    ((None, None, 0, 1, "somefile.txt"), "somefile.txt"),
    (("pngsequence", "png", 2.0, 10, None), "pngsequence02.png"),
    (("pngsequence", "png", 3, 333.0, None), "pngsequence003.png"),
    (("pngsequence", "png", 4.0, 4444.0, None), "pngsequence0004.png"),
    ((None, None, 0, 1, "somefile"), "somefile"),
    ((None, "png", 0, 1, "somefile"), "somefile.png"),
    ((None, None, 0, 1, ".ext"), ".ext"),
    ((None, None, 0, 1, ""), ""),
    ((None, None, 0, 1, None), ""),
    (("somefile", None, 0, 1, ".ext"), "somefile0"),
    (("somefile", None, 0, 1, "other.ext"), "somefile0.ext"),
    ((None, None, 0, 0, None), ""),
]

BAD_BUILD_SERIES_FILENAME_ARGS = [
    (("pngsequence", None, 0, 0, None), "'max_index' value must be >= 1"),
    (("pngsequence", None, -1, 0, None), "'index' value must be >= 0"),
    (("pngsequence", None, 0, -1, None), "'max_index' value must be >= 1"),
    (("pngsequence", None, 2, 1, None), "'max_index' value must be >= 'index'"),
    ((1, None, 0, 0, None), "'filename' must be a string"),
    ((2.0, None, 0, 0, None), "'filename' must be a string"),
    (({3:3}, None, 0, 0, None), "'filename' must be a string"),
    (([4], None, 0, 0, None), "'filename' must be a string"),
    (("", 1, 0, 0, None), "'ext_part' must be a string or None"),
    (("", 2.0, 0, 0, None), "'ext_part' must be a string or None"),
    (("", {3:3}, 0, 0, None), "'ext_part' must be a string or None"),
    (("", [4], 0, 0, None), "'ext_part' must be a string or None"),
    (("", "", 0, 0, 1), "'base_file_ext' must be a string or None"),
    (("", "", 0, 0, 2.0), "'base_file_ext' must be a string or None"),
    (("", "", 0, 0, {3:3}), "'base_file_ext' must be a string or None"),
    (("", "", 0, 0, [4]), "'base_file_ext' must be a string or None"),
]

def test_build_series_filename():
    for good_args, result in GOOD_BUILD_SERIES_FILENAME_ARGS:
        assert result == build_series_filename(*good_args)

    for bad_args, match_text in BAD_BUILD_SERIES_FILENAME_ARGS:
        with pytest.raises(ValueError, match=match_text):
            build_series_filename(*bad_args)
