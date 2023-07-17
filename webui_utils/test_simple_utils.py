import pytest # pylint: disable=import-error
from .simple_utils import *

GOOD_CREATE_SAMPLE_INDICES_ARGS = [
    ((10, 0, 1), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    ((10, 1, 1), [1, 2, 3, 4, 5, 6, 7, 8, 9]),
    ((10, 2, 1), [2, 3, 4, 5, 6, 7, 8, 9]),
    ((10, 3, 1), [3, 4, 5, 6, 7, 8, 9]),
    ((10, 4, 1), [4, 5, 6, 7, 8, 9]),
    ((10, 5, 1), [5, 6, 7, 8, 9]),
    ((10, 6, 1), [6, 7, 8, 9]),
    ((10, 7, 1), [7, 8, 9]),
    ((10, 8, 1), [8, 9]),
    ((10, 9, 1), [9]),
    ((10, 10, 1), []),
    ((10, 11, 1), []),

    ((10, 0, 2), [0, 2, 4, 6, 8]),
    ((10, 1, 2), [1, 3, 5, 7, 9]),
    ((10, 2, 2), [2, 4, 6, 8]),
    ((10, 3, 2), [3, 5, 7, 9]),
    ((10, 4, 2), [4, 6, 8]),
    ((10, 5, 2), [5, 7, 9]),
    ((10, 6, 2), [6, 8]),
    ((10, 7, 2), [7, 9]),
    ((10, 8, 2), [8]),
    ((10, 9, 2), [9]),
    ((10, 10, 2), []),
    ((10, 11, 2), []),

    ((10, 0, 3), [0, 3, 6, 9]),
    ((10, 1, 3), [1, 4, 7]),
    ((10, 2, 3), [2, 5, 8]),
    ((10, 3, 3), [3, 6, 9]),
    ((10, 4, 3), [4, 7]),
    ((10, 5, 3), [5, 8]),
    ((10, 6, 3), [6, 9]),
    ((10, 7, 3), [7]),
    ((10, 8, 3), [8]),
    ((10, 9, 3), [9]),
    ((10, 10, 3), []),
    ((10, 11, 3), []),

    ((0, 0, 1), []),
    ((0, 1, 1), []),
    ((0, 2, 1), []),
    ((0, 0, 2), []),
    ((0, 1, 2), []),
    ((0, 2, 2), []),
    ((1, 0, 1), [0]),
    ((1, 1, 1), []),
    ((1, 2, 2), []),
    ((1, 0, 2), [0]),
    ((1, 1, 2), []),
    ((1, 2, 2), []),
    ((5, 2, 3), [2]),
]

BAD_CREATE_SAMPLE_INDICES_ARGS = [
    ((-1, 0, 1), "'set_size' must be zero or positive"),
    ((10, -1, 1), "'offset' must be zero or positive"),
    ((10, 0, 0), "'stride' must be >= 1"),
    ((10, 0, -1), "'stride' must be >= 1")]

def test_create_sample_indices():
    for args, expected in GOOD_CREATE_SAMPLE_INDICES_ARGS:
        result = create_sample_indices(*args)
        assert result == expected

    for bad_args, match_text in BAD_CREATE_SAMPLE_INDICES_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_sample_indices(*bad_args)

GOOD_CREATE_SAMPLE_SET_ARGS = [
    (([1, 2, 3, 4, 5], 0, 1), [1, 2, 3, 4, 5]),
    (([1, 2, 3, 4, 5], 1, 1), [2, 3, 4, 5]),
    (([1, 2, 3, 4, 5], 0, 2), [1, 3, 5]),
    (([1, 2, 3, 4, 5], 1, 2), [2, 4]),
    (([1, 2, 3, 4, 5], 0, 3), [1, 4]),
    (([1, 2, 3, 4, 5], 1, 3), [2, 5]),
    (([1, 2, 3, 4, 5], 0, 4), [1, 5]),
    (([1, 2, 3, 4, 5], 1, 4), [2]),
    (([1, 2, 3, 4, 5], 0, 5), [1]),
    (([1, 2, 3, 4, 5], 1, 5), [2]),
    ((["1", "2", "3", "4", "5"], 0, 1), ["1", "2", "3", "4", "5"]),
    (([1, 2.0, {3:3}, "four", {5}], 1, 1), [2.0, {3:3}, "four", {5}])]

BAD_CREATE_SAMPLE_SET_ARGS = [
    ((1, 0, 0), "'samples' must be a list"),
    ((2.0, 0, 0), "'samples' must be a list"),
    (({3:3}, 0, 0), "'samples' must be a list"),
    (("four", 0, 0), "'samples' must be a list"),
    (({5, 5}, 0, 0), "'samples' must be a list")]

def test_create_sample_set():
    for args, expected in GOOD_CREATE_SAMPLE_SET_ARGS:
        result = create_sample_set(*args)
        assert result == expected

    for bad_args, match_text in BAD_CREATE_SAMPLE_SET_ARGS:
        with pytest.raises(ValueError, match=match_text):
            create_sample_set(*bad_args)

GOOD_SECONDS_TO_HMSF_ARGS = [
    ((0, 0), "00:00:00/0"),
    ((0/1, 1), "00:00:00/0"),
    ((1/1, 1), "00:00:01/0"),
    ((0/29.97, 29.97), "00:00:00/00"),
    ((0/30, 30), "00:00:00/00"),
    ((1/23.976, 23.976), "00:00:00/01"),
    ((23/23.976, 23.976), "00:00:00/23"),
    ((1/24, 24), "00:00:00/01"),
    ((23/24, 24), "00:00:00/23"),
    ((1/29.97, 29.97), "00:00:00/01"),
    ((29/29.97, 29.97), "00:00:00/29"),
    ((1/30, 30), "00:00:00/01"),
    ((29/30, 30), "00:00:00/29"),
    ((1/59.94, 59.94), "00:00:00/01"),
    ((59/59.94, 59.94), "00:00:00/59"),
    ((1/60, 60), "00:00:00/01"),
    ((59/60, 60), "00:00:00/59"),
    ((1/119.88, 119.88), "00:00:00/001"),
    ((119/119.88, 119.88), "00:00:00/119"),
    ((1/120, 120), "00:00:00/001"),
    ((119/120, 120), "00:00:00/119"),
    ((1/239.76, 239.76), "00:00:00/001"),
    ((239/239.76, 239.76), "00:00:00/239"),
    ((1/240, 240), "00:00:00/001"),
    ((239/240, 240), "00:00:00/239"),
    ((1/479.52, 479.52), "00:00:00/001"),
    ((479/479.52, 479.52), "00:00:00/479"),
    ((1/480, 480), "00:00:00/001"),
    ((479/480, 480), "00:00:00/479"),
    ((1/959.04, 959.04), "00:00:00/001"),
    ((959/959.04, 959.04), "00:00:00/959"),
    ((1/960, 960), "00:00:00/001"),
    ((959/960, 960), "00:00:00/959"),
    ((1/1918.08, 1918.08), "00:00:00/0001"),
    ((1918/1918.08, 1918.08), "00:00:00/1918"),
    ((1/1920, 1920), "00:00:00/0001"),
    ((1919/1920, 1920), "00:00:00/1919"),
    ((1/99999, 99999), "00:00:00/00001"),
    ((99998/99999, 99999), "00:00:00/99998"),
    ((1/100000, 100000), "00:00:00/000001"),
    # ((99999/100000, 99999), "00:00:00/999999"), # returns '0:00:00/99998'
    ((1/1000000, 1000000), "00:00:00/0000001"),
    # ((999999/1000000, 999999), "00:00:00/999999"), # returns '0:00:00/999998'
    ((1/29.97, 29.97, ";"), "00:00:00;01"),
    ((29/29.97, 29.97, ":"), "00:00:00:29"),
]

BAD_SECONDS_TO_HMSF_ARGS = [
    ((None, None), "'seconds' must be a float\\(able\\)"),
    ((0, None), "'framerate' must be a float\\(able\\)"),
]

def test_seconds_to_hmsf():
    for args, expected in GOOD_SECONDS_TO_HMSF_ARGS:
        result = seconds_to_hmsf(*args)
        assert result == expected

    for bad_args, match_text in BAD_SECONDS_TO_HMSF_ARGS:
        with pytest.raises(ValueError, match=match_text):
            seconds_to_hmsf(*bad_args)
