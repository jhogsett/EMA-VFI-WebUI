import os
import pytest # pylint: disable=import-error
from .test_shared import *
from .image_utils import *

GOOD_GIF_FRAME_COUNT_ARGS = [
    (FIXTURE_GIF_LIST[0], 17),
]

BAD_GIF_FRAME_COUNT_ARGS = [
    (None, "'filepath' must be a string"),
    ("", "'filepath' must be a legal path"),
    (1, "'filepath' must be a string"),
    (2.0, "'filepath' must be a string"),
    ({3:3}, "'filepath' must be a string"),
    ([4], "'filepath' must be a string"),
    (os.path.join(FIXTURE_PATH, "doesnotexist.gif"), "file '.*doesnotexist.gif' does not exist"),
]

def test_gif_frame_count():
    for good_args, expected_count in GOOD_GIF_FRAME_COUNT_ARGS:
        assert expected_count == gif_frame_count(good_args)

    for bad_args, match_text in BAD_GIF_FRAME_COUNT_ARGS:
        with pytest.raises(ValueError, match=match_text):
            gif_frame_count(bad_args)

GOOD_CREATE_GIF_ARGS = [
    ((FIXTURE_PNG_LIST, os.path.join(FIXTURE_PATH, "images.gif"), 1000), 200_000, 300_000, 3),
    ((FIXTURE_PNG_LIST, os.path.join(FIXTURE_PATH, "images.gif"), 1000.0), 200_000, 300_000, 3),
    (([FIXTURE_PNG_LIST[0]], os.path.join(FIXTURE_PATH, "images.gif")), 100_000, 150_000, 1),
]

BAD_CREATE_GIF_ARGS = [
    ((None, None, None), "'images' must be a list"),
    (([], None, None), "'images' must be a non-empty list"),
    (([1], None, None), "'images' must be a list of strings"),
    (([""], None, None), "'images' contains an illegal path"),
    (([FIXTURE_PATH], None, None),  "'filepath' must be a string"),
    (([FIXTURE_PATH], "", None),  "'filepath' must be a safe path"),
    (([FIXTURE_PATH], 1, None), "'filepath' must be a string"),
    (([FIXTURE_PATH], 2.0, None), "'filepath' must be a string"),
    (([FIXTURE_PATH], {3:3}, None), "'filepath' must be a string"),
    (([FIXTURE_PATH], {3:3}, None), "'filepath' must be a string"),
    (([FIXTURE_PATH], [4], None), "'filepath' must be a string"),
    (([FIXTURE_PATH], FIXTURE_PATH, None), "'duration' must be an int or float"),
    (([FIXTURE_PATH], FIXTURE_PATH, ""), "'duration' must be an int or float"),
    (([FIXTURE_PATH], FIXTURE_PATH, {3:3}), "'duration' must be an int or float"),
    (([os.path.join(FIXTURE_PATH, "doesnotexist.png")], FIXTURE_PATH, 0), "image file '.*doesnotexist.png' does not exist"),
]

def test_create_gif():
    for good_args, min_size, max_size, num_frames in GOOD_CREATE_GIF_ARGS:
        create_gif(*good_args)
        filepath = good_args[1]
        is_present = os.path.exists(filepath)
        is_good_size = min_size < os.path.getsize(filepath) < max_size
        has_good_frames = gif_frame_count(filepath) == num_frames
        os.remove(filepath)
        assert is_present and is_good_size and has_good_frames

    for bad_args, match_text in BAD_CREATE_GIF_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_gif(*bad_args)
