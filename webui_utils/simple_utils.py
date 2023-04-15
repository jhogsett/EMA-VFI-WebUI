"""Functions for computing various things"""
import sys
import math
from collections import namedtuple
from fractions import Fraction
from .simple_icons import SimpleIcons

def max_steps(num_splits : int) -> int:
    """Computing the count of work steps needed based on the number of splits"""
    # Before splitting, there's one existing region between the before and after frames.
    # Each split doubles the number of regions.
    # Work steps = the final number of regions - the existing region.
    return 2 ** num_splits - 1

def FauxArgs(**kwargs): #pylint: disable=invalid-name
    """Create an object with properies like what argparse provides"""
    # Useful if using 3rd-party code expecting an args object
    return namedtuple("FauxArgs", kwargs.keys())(**kwargs)

def float_range_in_range(target_min : float,
                        target_max : float,
                        domain_min : float,
                        domain_max : float,
                        use_midpoint=False):
    """True if target range is entirely within the domain range, inclusive"""
    if use_midpoint:
        target = target_min + (target_max - target_min) / 2.0
        if target >= domain_min and target <= domain_max:
            return True
    else:
        if target_min >= domain_min and target_max <= domain_max:
            return True
    return False

def predict_search_frame(num_splits : int, fractional_time : float) -> float:
    """Compute fractional search time"""
    # For Frame Search, given a frame time 0.0 - 1.0
    # and a search precision (split count) compute the fractional
    # time that will actually be found
    resolution = 2 ** num_splits
    return round(resolution * fractional_time) / resolution

def restored_frame_searches(restored_frame_count : int) -> list:
    """Compute frame restoration times as floats"""
    # For Frame Restoration, given a count of restored frames
    # compute the frame search times for the new frames that will be created
    return [(n + 1.0) / (restored_frame_count + 1.0) for n in range(restored_frame_count)]

def restored_frame_fractions(restored_frame_count : int) -> str:
    """Compute frame restoration times as fractions for display in the UI"""
    # For Frame Restoration, given a count of restored frames
    # compute a human friendly display of the fractional
    # times for the new frames that will be created
    result = []
    for frame in range(restored_frame_count):
        div = frame + 1
        den = restored_frame_count + 1
        result.append(str(Fraction(div/den).limit_denominator()))
    return ", ".join(result)

# For Frame Restoration, given a count of restored frames
# and a precision (split count) compute the frames that
# are likely to be found given that precision
def restored_frame_predictions(restored_frame_count : int, num_splits : int) -> list:
    """Computed predicted frame restoration results times as floats for display in the UI"""
    searches = restored_frame_searches(restored_frame_count)
    predictions = [str(predict_search_frame(num_splits, search)) for search in searches]

    # prepare to detect duplicates, including the outer frames
    all_frames = predictions + ["0.0"] + ["1.0"]

    warning = ""
    if len(set(all_frames)) != len(all_frames):
        warning = f" {SimpleIcons.WARNING} Repeated frames - increase precision"
    return ", ".join(predictions) + warning

def fps_change_details(starting_fps : int, ending_fps : int, precision : int):
    """Compute details needed to display Change FPS feature page details"""
    lowest_common_rate = math.lcm(starting_fps, ending_fps)
    expansion = int(lowest_common_rate / starting_fps)
    num_frames = expansion - 1
    sample_rate = int(lowest_common_rate / ending_fps)

    filled = num_frames
    sampled = f"1/{sample_rate}"

    if filled > 100:
        filled = str(filled) + " " + SimpleIcons.WARNING

    fractions = restored_frame_fractions(num_frames) or "n/a"
    predictions = restored_frame_predictions(num_frames, precision) or "n/a"
    return lowest_common_rate, filled, sampled, fractions, predictions

def sortable_float_index(float_value : float,
                        fixed_width = False,
                        mantissa_width : float | None = None):
    """return a floating point number formatted to be sortable"""
    if mantissa_width is None:
        mantissa_width = sys.float_info.mant_dig
    _format = "f" if fixed_width else "g"
    format_str = "{:0." + str(mantissa_width) + _format + "}"
    return format_str.format(float_value)

def is_power_of_two(var):
    """True for 1, 2, 4, 8 etc"""
    return (var & (var-1) == 0) and var != 0

def power_of_two_precision(var):
    """Computes needed splits for a power-of-two inflation"""
    if is_power_of_two(var):
        return int(math.log2(var))
    else:
        raise ValueError(f"{var} is not a power of 2")

def _should_sample(index : int, offset : int, stride : int):
    if index < offset:
        return False
    # (index - offset) ensures 1: first sample gets taken,
    # 2: sampling is synchronized to frame #0 regardless of offset
    return (index - offset) % stride == 0

def create_sample_indices(set_size : int, offset : int, stride : int):
    if set_size < 0:
        raise ValueError("'set_size' must be zero or positive")
    if offset < 0:
        raise ValueError("'offset' must be zero or positive")
    if stride < 1:
        raise ValueError("'stride' must be >= 1")
    sample_indices = []
    for index in range(set_size):
        if _should_sample(index, offset, stride):
            sample_indices.append(index)
    return sample_indices

def create_sample_set(samples : list, offset : int, stride : int):
    if not isinstance(samples, list):
        raise ValueError("'samples' must be a list")
    sample_set = create_sample_indices(len(samples), offset, stride)
    return [samples[index] for index in sample_set]
