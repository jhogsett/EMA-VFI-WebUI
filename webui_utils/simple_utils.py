"""Functions for computing various things"""
import sys
import math
import datetime
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

def seconds_to_hms(seconds):
    return str(datetime.timedelta(seconds = seconds))

def seconds_to_hmsf(seconds : float, framerate : float, framechar : str="/"):
    if not isinstance(seconds, (float, int)):
        raise ValueError("'seconds' must be a float(able)")
    if not isinstance(framerate, (float, int)):
        raise ValueError("'framerate' must be a float(able)")
    seconds = float(seconds)
    framerate = float(framerate)

    hms = seconds_to_hms(seconds).split(".")
    hms_only = hms[0].zfill(8)
    hms_frac = int((seconds % 1) * framerate)
    frame_width = len(str(int(framerate)))
    frames = str(hms_frac).zfill(frame_width)
    return f"{hms_only}{framechar}{frames}"

def clean_dict(_dict):
    cleaned = {}
    for k, v in _dict.items():
        if v:
            if isinstance(v, dict):
                cleaned[k] = clean_dict(v)
            else:
                cleaned[k] = v
    return cleaned

def get_frac_str_as_float(fraction_string : str) -> float:
    try:
        return float(Fraction(fraction_string))
    except ZeroDivisionError:
        return 0.0

def _shrink_merge(container_data, key, key_from, move_fn, remove_fn, rename_fn, state):
    # update the container count in memory
    count_from = container_data[key_from]
    container_data[key] += count_from

    move_fn(state, key, key_from)
    remove_fn(state, key_from)
    new_key = rename_fn(state, key, count_from)

    # update the key in memory
    del container_data[key_from]
    new_containers = {new_key if k == key else k :v for k, v in container_data.items()}

    return new_containers, new_key

## Shrink function
# containers : dict with container arbitrary key names associated with container contents counts
#              Meant to represent a set of Ordered containers, containing items of some kind,
#              where the number of containers should be reduced, so that no container
#              has fewer than 'minimum' items if possible
#              example {"000-123" : 124, "124-419" : 296}
# minimum    : target for the minimum number of items per container
# move_fn    : callback to move contents between containers
# remove_fn  : callback to eliminate a container
# rename_fn  : callback to rekey a container
# state      : state info passed to callback functions
# Returns    : a new dict representing the shrunken containers set
def shrink(container_data, minimum, move_fn, remove_fn, rename_fn, state):
    last_keys = []
    last_merged = None
    while True:
        keys = list(container_data.keys())

        # if fewer than two container items, work is unneeded
        if len(keys) < 2:
            break

        # if the keys have not changed this round, work is done
        if keys == last_keys:
            break
        last_keys = keys

        # merging assumes the following key is always available to merge from
        for index in range(len(keys) - 1):
            key = keys[index]
            # skip processing previous containers until reaching the last merged one
            # it is the first one that may need merging
            if last_merged and key != last_merged:
                continue
            else:
                last_merged = None
            count = container_data[key]
            if count < minimum:
                next_key = keys[index + 1]
                container_data, last_merged = \
                    _shrink_merge(container_data, key, next_key, move_fn, remove_fn, rename_fn, state)
                break
    # handle the final container item, merging back if needed
    if len(keys) > 1:
        key = keys[-1]
        prev_key = keys[-2]
        count = container_data[key]
        if count < minimum:
            container_data, _ = \
                _shrink_merge(container_data, prev_key, key, move_fn, remove_fn, rename_fn, state)
    return container_data

TEXT_TERM = "\r\n"
HTML_TERM = "<br/>"
DELETE_TERM = ""
TEXT_TO_HTML = {
    TEXT_TERM : DELETE_TERM,
    "- " : "• ",
    "(!)" : SimpleIcons.WARNING
}
STYLE_COLORS = {
    "none" : "",
    "info" : "color:hsl(120 100% 65%)",
    "more" : "color:hsl(39 100% 65%)",
    "warning" : "color:hsl(60 100% 65%)",
    "error" : "color:hsl(0 100% 65%)",
    "highlight" : "color:hsl(284 100% 65%)",
}

def _compute_style(color : str, bold : bool, italic : bool):
    color_style = STYLE_COLORS.get(color, "")
    font_weight = "font-weight:bold" if bold else ""
    font_style = "font-style:italic" if italic else ""
    styles = [color_style, font_weight, font_style]
    return ";".join([style for style in styles if style])

def _format_markdown_line(text : str, style : str):
    terminate = text.find(TEXT_TERM) != -1
    for k,v in TEXT_TO_HTML.items():
        text = text.replace(k, v, 1)
    term = HTML_TERM + TEXT_TERM if terminate else TEXT_TERM
    return f"<span style=\"{style}\">{text}</span>{term}"

def format_markdown(text, color="info", bold=True, bold_heading_only=False, italic=False):
    heading_style = _compute_style(color, bold, italic)
    lines_style = _compute_style(color, False, italic) if bold_heading_only else heading_style
    lines = text.splitlines()
    if len(lines) == 1:
        return _format_markdown_line(text, heading_style)
    else:
        result = []
        for index, line in enumerate(lines):
            line += TEXT_TERM
            if index == 0:
                result.append(_format_markdown_line(line, heading_style))
            else:
                result.append(_format_markdown_line(line, lines_style))
        return "\r\n".join(result)

def _format_text(text, color="info", bold=False, italic=False):
    style = _compute_style(color, bold, italic)
    return f"<span style='{style}'>{text}</span>"

def _format_table_row(row : list):
    return "| " + " | ".join(row) + " |"

def _format_table_aligner(row : list):
    aligner_row = [":-:" for _ in row]
    return _format_table_row(aligner_row)

def style_row(row : str | list, color="info", bold=False, italic=False):
    if isinstance(row, str):
        return _format_text(row, color, bold, italic)
    else:
        return [_format_text(entry, color, bold, italic) for entry in row]

def style_report(title : str, rows : list[str], color="info"):
    report = []
    report.append(style_row(title, color=color, bold=True, italic=True))
    for row in rows:
        report.append(style_row(row, color=color))
    return "</br>\r\n".join(report)

def format_table(header_row : list,
                 data_rows : list[list],
                 color : str="info",
                 title : str=None):
    num_cols = len(header_row)
    if num_cols < 1:
        raise ValueError("header row must have one more more entries")

    styled_header_row = style_row(header_row, color=color)
    table = []

    if title:
        table.append(_format_text(title, color=color, bold=True, italic=True))

    table.append(_format_table_row(styled_header_row))
    table.append(_format_table_aligner(header_row))

    for row in data_rows:
        styled_row = style_row(row, color=color)
        table.append(_format_table_row(styled_row))

    return "\r\n".join(table)
