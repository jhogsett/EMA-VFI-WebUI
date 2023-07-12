import pytest # pylint: disable=import-error
from .video_utils import *

GOOD_DECODE_ASPECT_ARGS = [
    ("1:1", 1.0),
    ("0:1", 0.0),
    ("40:33", 40 / 33),
    ("32:27", 32 / 27)]

BAD_DECODE_ASPECT_ARGS = [
    ("0:0", "the aspect '0:0' is not valid"),
    (1, "'aspect' must be a string"),
    ("16:nine", "must be two integers joined by ':'"),
    ("4.0:3.0", "must be two integers joined by ':'"),
    ("720", "must be two values joined by ':'")]

def test_decode_aspect():
    for arg, expected in GOOD_DECODE_ASPECT_ARGS:
        result = decode_aspect(arg)
        assert result == expected

    for bad_arg, match_text in BAD_DECODE_ASPECT_ARGS:
        with pytest.raises(ValueError, match=match_text):
            decode_aspect(bad_arg)
