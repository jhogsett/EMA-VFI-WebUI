"""Functions for dealing with video using FFmpeg"""
import os
import glob
import subprocess
import json
from fractions import Fraction
from ffmpy import FFmpeg, FFprobe, FFRuntimeError
from .image_utils import gif_frame_count
from .file_utils import split_filepath, get_directories
from .simple_utils import seconds_to_hms, get_frac_str_as_float
from .jot import Jot

QUALITY_NEAR_LOSSLESS = 17
QUALITY_SMALLER_SIZE = 28
QUALITY_DEFAULT = 23

def determine_input_pattern(png_files_path : str) -> str:
    """Determine the FFmpeg wildcard pattern needed to read a set of PNG files"""
    files = sorted(glob.glob(os.path.join(png_files_path, "*.png")))
    first_file = files[0]
    file_count = len(files)
    num_width = len(str(file_count))
    _, name_part, ext_part = split_filepath(first_file)
    return f"{name_part[:-num_width]}%0{num_width}d{ext_part}"

def determine_output_pattern(mp4_file_path : str) -> str:
    """Determine the FFmpeg wildcard pattern needed to write a set of PNG files"""
    frame_count = get_frame_count(mp4_file_path)
    num_width = len(str(frame_count))
    _, filename, _ = split_filepath(mp4_file_path)
    return f"{filename}%0{num_width}d.png"

def PNGtoMP4(input_path : str, # pylint: disable=invalid-name
            filename_pattern : str,
            frame_rate : float,
            output_filepath : str,
            crf : int=QUALITY_DEFAULT,
            global_options : str=""):
    """Encapsulate logic for the PNG Sequence to MP4 feature"""
    # if filename_pattern is empty it uses the filename of the first found file
    # and the count of file to determine the pattern, .png as the file type
    # ffmpeg -framerate 60 -i .\upscaled_frames%05d.png -c:v libx264 -r 60  -pix_fmt yuv420p
    #   -crf 28 test.mp4
    pattern = filename_pattern or determine_input_pattern(input_path)
    ffcmd = FFmpeg(
        inputs= {os.path.join(input_path, pattern) : f"-framerate {frame_rate}"},
        outputs={output_filepath : f"-r {frame_rate} -pix_fmt yuv420p -c:v libx264 -crf {crf}"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def PNGtoCustom(input_path : str, # pylint: disable=invalid-name
                filename_pattern : str,
                frame_rate : float,
                output_filepath : str,
                global_options : str="",
                custom_options : str=""):
    pattern = filename_pattern or determine_input_pattern(input_path)
    ffcmd = FFmpeg(
        inputs= {os.path.join(input_path, pattern) : f"-framerate {frame_rate}"},
        outputs={output_filepath : f"-r {frame_rate} -pix_fmt yuv420p {custom_options}"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# ffmpeg -y -i frames.mp4 -filter:v fps=25 -pix_fmt rgba -start_number 0 output_%09d.png
# ffmpeg -y -i frames.mp4 -filter:v fps=25 -start_number 0 output_%09d.png
def MP4toPNG(input_path : str,  # pylint: disable=invalid-name
            filename_pattern : str,
            frame_rate : float,
            output_path : str,
            start_number : int = 0,
            deinterlace : bool = False,
            global_options : str = ""):
    """Encapsulate logic for the MP4 to PNG Sequence feature"""
    pattern = filename_pattern or determine_output_pattern(input_path)
    if deinterlace:
        filter = f"bwdif=mode=send_field:parity=auto:deint=all,fps={frame_rate}"
    else:
        filter = f"fps={frame_rate}"

    ffcmd = FFmpeg(inputs= {input_path : None},
        outputs={os.path.join(output_path, pattern) :
            f"-filter:v {filter} -start_number {start_number}"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# making a high quality GIF from images requires first creating a color palette,
# then supplying it to the conversion command
# https://stackoverflow.com/questions/58832085/colors-messed-up-distorted-when-making-a-gif-from-png-files-using-ffmpeg

# ffmpeg -i gifframes_%02d.png -vf palettegen palette.png
def PNGtoPalette(input_path : str, # pylint: disable=invalid-name
                filename_pattern : str,
                output_filepath : str,
                global_options : str=""):
    """Create a palette from a set of PNG files to feed into animated GIF creation"""
    if filename_pattern == "auto":
        filename_pattern = determine_input_pattern(input_path)
    ffcmd = FFmpeg(inputs= {os.path.join(input_path, filename_pattern) : None},
                outputs={output_filepath : "-vf palettegen"},
                global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def PNGtoGIF(input_path : str, # pylint: disable=invalid-name
            filename_pattern : str,
            output_filepath : str,
            frame_rate : float,
            global_options : str=""):
    """Encapsulates logic for the PNG sequence to GIF feature"""
    # if filename_pattern is empty it uses the filename of the first found file
    # and the count of file to determine the pattern, .png as the file type
    # ffmpeg -i gifframes_%02d.png -i palette.png -lavfi paletteuse video.gif
    # ffmpeg -framerate 3 -i image%01d.png video.gif
    pattern = filename_pattern or determine_input_pattern(input_path)
    output_path, base_filename, _ = split_filepath(output_filepath)
    palette_filepath = os.path.join(output_path, base_filename + "-palette.png")
    palette_cmd = PNGtoPalette(input_path, pattern, palette_filepath, global_options=global_options)

    ffcmd = FFmpeg(inputs= {
            os.path.join(input_path, pattern) : f"-framerate {frame_rate}",
            palette_filepath : None},
        outputs={output_filepath : "-lavfi paletteuse"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return "\n".join([palette_cmd, cmd])

def GIFtoPNG(input_path : str, # pylint: disable=invalid-name
            output_path : str,
            start_number : int = 0,
            global_options : str = ""):
    """Encapsulates logic for the GIF to PNG Sequence feature"""
    # ffmpeg -y -i images\example.gif -start_number 0 gifframes_%09d.png
    _, base_filename, extension = split_filepath(input_path)

    if extension.lower() == ".gif":
        frame_count = gif_frame_count(input_path)
    elif extension.lower() == ".mp4":
        frame_count = get_frame_count(input_path)
    else:
        # assume an arbitrarily high frame count to ensure a wide index
        frame_count = 1_000_000

    num_width = len(str(frame_count))
    filename_pattern = f"{base_filename}%0{num_width}d.png"
    ffcmd = FFmpeg(inputs= {input_path : None},
        outputs={os.path.join(output_path, filename_pattern) : f"-start_number {start_number}"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def deduplicate_frames(input_path : str,
                      output_path : str,
                      threshold : int,
                      global_options : str = ""):
    """Encapsulate logic for detecting and removing duplicate frames"""
    # ffmpeg -i "C:\CONTENT\ODDS\odds%04d.png"
    # -vf mpdecimate=hi=2047:lo=2047:frac=1:max=0,setpts=N/FRAME_RATE/TB
    # -start_number 0 "C:\CONTENT\TEST\odds%04d.png"
    filename_pattern = determine_input_pattern(input_path)
    input_sequence = os.path.join(input_path, filename_pattern)
    output_sequence = os.path.join(output_path, filename_pattern)
    filter = f"mpdecimate=hi={threshold}:lo={threshold}:frac=1:max=0,setpts=N/FRAME_RATE/TB"

    ffcmd = FFmpeg(inputs= {input_sequence : None},
        outputs={output_sequence : f"-vf {filter} -start_number 0"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def get_frame_count(input_path : str) -> int:
    """Use FFprobe to determine MP4 frame count"""
    # ffprobe.exe -v quiet -count_frames -show_entries stream=nb_read_frames -print_format default=nokey=1:noprint_wrappers=1 file.mp4
    # 1763
    ffcmd = FFprobe(inputs= {input_path :
        " -select_streams v -count_frames -show_entries stream=nb_read_frames" +
        " -print_format default=nokey=1:noprint_wrappers=1"},
                    global_options="-v quiet")
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8").strip()
    # sometimes it's output twice
    stdout = stdout.splitlines()[0]
    return int(stdout)

def get_frame_rate(input_path : str) -> float:
    """Use FFprobe to determine MP4 frame rate"""
    # ffprobe.exe -v quiet -show_entries stream=r_frame_rate -print_format default=nokey=1:noprint_wrappers=1 file.mp4
    # 25/1
    ffcmd = FFprobe(inputs= {input_path :
        "-show_entries stream=r_frame_rate -print_format default=nokey=1:noprint_wrappers=1"},
                    global_options="-v quiet")
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8").strip()
    fraction = Fraction(stdout)
    return float(fraction)

def get_video_details(input_path : str, count_frames = True) -> dict:
    """Use FFprobe to get streams and format information for a video"""
    # ffprobe.exe -v quiet -show_format -show_streams -count_frames -of json file.mp4
    if count_frames:
        ffcmd = FFprobe(inputs= {input_path : "-show_format -show_streams -count_frames -of json"})
    else:
        ffcmd = FFprobe(inputs= {input_path : "-show_format -show_streams -of json"})

    try:
        result = ffcmd.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = result[0].decode("UTF-8").strip()
        return json.loads(stdout)
    except FFRuntimeError as error:
        return {
            "error" : {
                "ffprobe_cmd" : error.cmd,
                "exit_code" : error.exit_code,
                "console_output" : str(error.stderr.decode("UTF-8"))}}

def get_essential_video_details(input_path : str, count_frames=False) -> dict:
    """Use FFprobe to get video details essential for automatic processing
       If count_type is True and frames can't be determined, a RuntimeError is raised
    """
    video_details = get_video_details(input_path, count_frames=count_frames)
    if video_details.get("error"):
        error = video_details["error"]
        error_message = error["console_output"]
        # keep only the last line, presumably with the error (the rest is ffprobe spew)
        console_error = error_message.splitlines()[-1]
        message = f"error getting video details for '{input_path}':\r\n'{console_error}'"
        raise RuntimeError(message)
    else:
        video_essentials = {}
        video_essentials["has_audio"] = False

        format_data = video_details["format"]
        file_size = f"{int(format_data.get('size', 0)):,d}"
        video_essentials["file_size"] = file_size

        streams_data = video_details["streams"]
        for stream_data in streams_data:
            codec_type = stream_data.get("codec_type")

            if codec_type == "audio":
                video_essentials["has_audio"] = True
                continue

            if codec_type != "video":
                continue

            frame_count = stream_data.get("nb_frames") or stream_data.get("nb_read_frames")
            if not frame_count:
                if count_frames:
                    raise RuntimeError(f"unable to determine frame count for '{input_path}'")
                else:
                    # rerun with frame counting
                    return get_essential_video_details(input_path, count_frames=True)
            video_essentials["frame_count"] = frame_count

            video_essentials["source_video"] = input_path
            video_essentials["video_index"] = stream_data.get("index")

            avg_frame_rate = stream_data.get("avg_frame_rate")
            avg_frame_rate = get_frac_str_as_float(avg_frame_rate)
            r_frame_rate = stream_data.get("r_frame_rate")
            r_frame_rate = get_frac_str_as_float(r_frame_rate)
            frame_rate = avg_frame_rate or r_frame_rate
            frame_rate = f"{frame_rate:0.2f}" if frame_rate else "0.00"
            video_essentials["frame_rate"] = frame_rate

            duration = seconds_to_hms(float(stream_data.get("duration", 0)))
            video_essentials["duration"] = "+" + duration[:duration.find(".")].zfill(8)

            width = stream_data.get("width")
            height = stream_data.get("height")
            video_essentials["content_width"] = width
            video_essentials["content_height"] = height
            video_essentials["content_dimensions"] = f"{width} x {height}"

            video_essentials["index_width"] = len(str(frame_count))
            video_essentials["frame_count_show"] = f"{int(frame_count):,d}"

            sample_factor = 1.0
            display_width = width
            display_height = height
            sample_aspect_ratio = stream_data.get("sample_aspect_ratio")
            if sample_aspect_ratio:
                try:
                    sample_factor = decode_aspect(sample_aspect_ratio)
                    display_width = int(width * sample_factor)
                    display_height = height
                except ValueError:
                    pass
            video_essentials["sample_factor"] = sample_factor
            video_essentials["display_width"] = display_width
            video_essentials["display_height"] = display_height
            video_essentials["display_dimensions"] = f"{display_width} x {display_height}"

            video_essentials["display_aspect_ratio"] = stream_data.get("display_aspect_ratio")
        return video_essentials

def get_duplicate_frames(input_path : str, threshold : int, max_dupes_per_group : int):
    """Use FFmpeg to get a list of duplicate frames without making changes
        - input_path: path to PNG frame files
        - threshold: passed to FFmpeg as 'hi' and 'lo' mpdecimate value
        - max_dupes_per_group: raises RuntimeError if more frames are added to a group
          set to 0 to disable
       Returns:
        - array of duplicate frame groups: arrays of dicts with frame index and filename
        - array of frame filenames
        - array of found mpdecimate lines for debugging
    """
    # ffmpeg -i file.mp4 -vf mpdecimate=hi=5000:lo=5000:frac=1 -loglevel debug -f null -
    if not os.path.exists(input_path):
        raise ValueError(f"path does not exist: {input_path}")
    if threshold < 0:
        raise ValueError(f"'threshold' must be positive")
    if max_dupes_per_group < 0:
        max_dupes_per_group = 0

    filename_pattern = determine_input_pattern(input_path)
    input_sequence = os.path.join(input_path, filename_pattern)
    output_sequence = "-"
    filter = f"mpdecimate=hi={threshold}:lo={threshold}:frac=1:max=0"

    ffcmd = FFmpeg(inputs= {input_sequence : None},
        outputs={output_sequence : f"-vf {filter} -f null"},
        global_options="-loglevel debug")
    cmd = ffcmd.cmd
    result = ffcmd.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = result[1].decode("UTF-8")
    stderr_lines = stderr.splitlines()
    decimate_lines = [line for line in stderr_lines if line.startswith("[Parsed_mpdecimate")]
    keep_drop_lines = [line for line in decimate_lines if " keep " in line or " drop " in line]
    is_dupe_map = [None] * len(keep_drop_lines)
    for index, line in enumerate(keep_drop_lines):
        is_dupe_map[index] = " drop " in line

    filenames = sorted(glob.glob(os.path.join(input_path, "*.png")))
    if len(filenames) != len(keep_drop_lines):
        raise ValueError(
    f"frame count mismatch FFmpeg ({len(keep_drop_lines)}) vs found files ({len(filenames)})")

    groups = []
    group = {}
    is_in_group = False
    for index, is_dupe in enumerate(is_dupe_map):
        if is_dupe:
            if max_dupes_per_group == 1:
                raise RuntimeError(
f"max_dupes_per_group exceeded: 2 in group #{len(groups)+1}, duplicate frame #{index}")
            if not is_in_group:
                is_in_group = True
                group = {}
                # add the preceding frame as the first duplicate of this group
                group[index-1] = filenames[index-1]
            else:
                if max_dupes_per_group:
                    if len(group)+1 > max_dupes_per_group:
                        raise RuntimeError(
f"max_dupes_per_group exceeded: {len(group)+1} in group #{len(groups)+1}, duplicate frame #{index}")
            group[index] = filenames[index]
        else:
            if is_in_group:
                groups.append(group)
                is_in_group = False
    if is_in_group:
        groups.append(group)
    return groups, filenames, decimate_lines

def compute_report_stats(duplicate_frame_groups, filenames):
    group_count = len(duplicate_frame_groups)
    frame_count = len(filenames)
    duplicate_frame_count = 0
    for group in duplicate_frame_groups:
        duplicate_frame_count += len(group.keys())
    # subtract the group count, to include only the actual duplicates (frames marked 'drop')
    duplicate_frame_count -= group_count

    # find largest and smallest group sizes
    max_group = 0
    min_group = 0
    if duplicate_frame_groups:
        min_group = frame_count + 1
        for group in duplicate_frame_groups:
            leng = len(group)
            max_group = leng if leng > max_group else max_group
            min_group = leng if leng < min_group else min_group

    # find first duplicate frame
    if group_count:
        first_group = duplicate_frame_groups[0]
        # first entry in group is a "keep" frame
        first_drop_frame = list(first_group.keys())[1]
    else:
        first_drop_frame = -1

    stats = {}
    stats["frame_count"] = frame_count
    stats["group_count"] = group_count
    stats["dupe_count"] = duplicate_frame_count
    dupe_ratio = duplicate_frame_count * 1.0 / frame_count
    stats["dupe_ratio"] = dupe_ratio
    stats["dupe_percent"] = f"{100.0 * dupe_ratio:0.2f}"
    stats["min_group"] = min_group
    stats["max_group"] = max_group
    stats["first_dupe"] = first_drop_frame
    return stats

def get_duplicate_frames_report(input_path : str,
                                threshold : int,
                                max_dupes_per_group : int) -> str:
    """Create a human-readable report of duplicate frame groups"""
    separator = ""
    duplicate_frame_groups, filenames, _ = get_duplicate_frames(input_path,
                                                                threshold,
                                                                max_dupes_per_group)
    stats = compute_report_stats(duplicate_frame_groups, filenames)
    report = []
    report.append("[Duplicate Frames Report]")
    report.append(f"Input Path: {input_path}")
    report.append(f"Frame Count: {stats['frame_count']}")
    report.append(f"Detection Threshold: {threshold}")
    report.append(f"Duplicate Frames: {stats['dupe_count']}")
    report.append(f"Duplicate Ratio: {stats['dupe_percent']}")
    report.append(f"Duplicate Frame Groups: {stats['group_count']}")
    report.append(f"Smallest Group Size: {stats['min_group']}")
    report.append(f"Largest Group Size: {stats['max_group']}")

    for index, entry in enumerate(duplicate_frame_groups):
        report.append(separator)
        report.append(f"[Group #{index+1}]")
        for key in entry.keys():
            report.append(f"Frame#{key} : {entry[key]}")
    return "\r\n".join(report)

def get_detected_scenes(input_path : str, threshold : float=0.5):
    # ffmpeg -framerate 1 -i "G:\CONTENT\HH\TEST\png%05d.png" -filter_complex "select='gt(scene,0.6)',metadata=print:file=-" -f null -
    # frame:0    pts:5152    pts_time:5152
    # lavfi.scene_score=0.973331
    if not os.path.exists(input_path):
        raise ValueError(f"path does not exist: {input_path}")
    if not isinstance(threshold, float):
        raise ValueError(f"'threshold' must a float between 0.0 and 1.0")
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError(f"'threshold' must between 0.0 and 1.0")

    filename_pattern = determine_input_pattern(input_path)
    input_sequence = os.path.join(input_path, filename_pattern)
    output_sequence = "-"
    filter = f"select='gt(scene\\,{threshold})',metadata=print:file=-"

    ffcmd = FFmpeg(inputs= {input_sequence : None},
        outputs={output_sequence : f"-filter_complex {filter} -f null"},
        global_options="-loglevel quiet")
    # cmd = ffcmd.cmd
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8")
    stdout_lines = stdout.splitlines()
    return [
        int(line.split()[1].split(":")[1]) for line in stdout_lines if line.startswith("frame:")]

def get_detected_breaks(input_path : str, duration : float=0.5, ratio : float=0.98):
    # ffmpeg -framerate 1 -i "G:\CONTENT\HH\TEST\png%05d.png" -filter_complex "blackdetect=d=0.5,metadata=print:file=bldet.txt" -f null -
    # frame:5106 pts:5106    pts_time:5106
    # lavfi.black_start=5106
    # frame:5152 pts:5152    pts_time:5152
    # lavfi.black_end=5152
    if not os.path.exists(input_path):
        raise ValueError(f"path does not exist: {input_path}")
    if not isinstance(duration, float):
        raise ValueError(f"'duration' (seconds) must be a float")
    if duration <= 0.0:
        raise ValueError(f"'duration' must > 0.0")
    if not isinstance(ratio, float):
        raise ValueError(f"'ratio' (0.0-1.0) must be a float")
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError(f"'ratio' must between 0.0 and 1.0")

    filename_pattern = determine_input_pattern(input_path)
    input_sequence = os.path.join(input_path, filename_pattern)
    output_sequence = "-"
    filter = f"blackdetect=d={duration}:pic_th={ratio},metadata=print:file=-"

    ffcmd = FFmpeg(inputs= {input_sequence : "-framerate 1"},
        outputs={output_sequence : f"-filter_complex {filter} -f null"},
        global_options="-loglevel quiet")
    # cmd = ffcmd.cmd
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8")
    stdout_lines = stdout.splitlines()
    start_frames = [
        int(line.split("=")[1]) for line in stdout_lines if line.startswith("lavfi.black_start")]
    end_frames = [
        int(line.split("=")[1]) for line in stdout_lines if line.startswith("lavfi.black_end")]
    if len(start_frames) != len(end_frames):
        # it could be the last break never ended
        if len(end_frames) == len(start_frames) - 1:
            del start_frames[-1]
        else:
            raise RuntimeError("unable to parse detected breaks")

    breaks = []
    for index, start in enumerate(start_frames):
        end = end_frames[index]
        # break at the midpoint
        breaks.append(int((start + end) / 2))
    return breaks

def scene_list_to_ranges(scene_list, num_files):
    last_scene_index = 0
    result = []
    for scene_frame in scene_list:
        first_frame = last_scene_index
        last_frame = scene_frame - 1
        if last_frame >= num_files:
            last_frame = num_files - 1
        scene_size = (last_frame - first_frame) + 1
        result.append({
            "first_frame" : first_frame,
            "last_frame" : last_frame,
            "scene_size" : scene_size})
        last_scene_index = scene_frame
    return result

# in: group name such as 000-123
# out: first index, last index, num width
def details_from_group_name(group_name : str):
    indexes = group_name.split("-")
    if len(indexes) != 2:
        raise RuntimeError(f"group name '{group_name}' cannot be parsed into indexes")
    first_index = indexes[0]
    last_index = indexes[1]
    num_width = len(str(first_index))
    if num_width < 1:
        raise RuntimeError(f"group name '{group_name}' cannot be parsed into index fill width")
    try:
        return int(first_index), int(last_index), num_width
    except ValueError:
        raise RuntimeError(f"group name '{group_name}' cannot be parsed into frames indexes")

def validate_input_path(input_path, num_groups):
    """returns the list of group names"""
    if not os.path.exists(input_path):
        raise ValueError("'input_path' must be the path of an existing directory")

    group_names = get_directories(input_path)
    if len(group_names) < 1:
        raise ValueError(f"no folders found in directory {input_path}")

    if num_groups == -1:
        num_groups = len(group_names)
    else:
        if len(group_names) != num_groups:
            raise ValueError(
                f"'num_groups' should match count of directories found at {input_path}")
    return group_names

def validate_group_names(group_names):
    try:
        for name in group_names:
            _, _, _ = details_from_group_name(name)
    except RuntimeError as error:
        raise RuntimeError(f"one or more group directory namaes is not valid: {error}")

def group_path(input_path, group_name):
    return os.path.join(input_path, group_name)

def group_files(input_path, file_ext, group_name):
    _group_path = group_path(input_path, group_name)
    return sorted(glob.glob(os.path.join(_group_path, f"*.{file_ext}")))

def slice_video(input_path : str,
                fps : float,
                output_path : str,
                num_width : int,
                first_frame : int,
                last_frame : int,
                type : str="mp4",
                mp4_quality : int=28,
                gif_speed : int=1,
                scale_factor : float=0.5,
                gif_high_quality : bool=False,
                gif_fps : float=0.0,
                gif_end_delay : float=0.0,
                global_options : str=""):
    # 153=5.1
    # 203+1=6.8
    # ffmpeg -y -i WINDCHIME.mp4 -ss 0:00:05.100000 -to 0:00:06.800000 -copyts 153-203-WINDCHIME.mp4
    # ffmpeg -y -i WINDCHIME.mp4 -ss 0:00:05.100000 -to 0:00:06.800000 -copyts 153-203-WINDCHIME.wav
    _, filename, ext = split_filepath(input_path)
    output_filename =\
f"{filename}[{str(first_frame).zfill(num_width)}-{str(last_frame).zfill(num_width)}].{type}"
    output_filepath = os.path.join(output_path, output_filename)
    start_second = first_frame / fps
    end_second = (last_frame + 1) / fps
    start_time = seconds_to_hms(start_second)
    end_time = seconds_to_hms(end_second)

    if type == "mp4":
        ffcmd = FFmpeg(inputs= {input_path : None},
                                outputs={output_filepath :
                f"-ss {start_time} -to {end_time} -copyts -vf 'scale=iw*{scale_factor}:-2,fps={fps}' -crf {mp4_quality}"},
            global_options="-y " + global_options)

    if type == "gif":
        # ffmpeg -y -i "C:\CONTENT\UHURA BUTTONS\ST apollo H and I-06232023-0800PM.mp4" -ss 0:00:44.488933 -to 0:00:55.612279 -vf setpts=PTS/30,fps=5,scale=iw*0.5:-2 -loop 0 "C:\CONTENT\UHURA BUTTONS\SOURCE\040000-050000\ST apollo H and I-06232023-0800PM[040000-050000]5fps.gif"
        start_time = seconds_to_hms(start_second / gif_speed)
        end_time = seconds_to_hms(end_second / gif_speed)
        gif_fps = fps if gif_fps == 0.0 else gif_fps

        # expressed in 1/100th seconds
        final_delay = f"-final_delay {int(gif_end_delay * 100)}" if gif_end_delay else ""

        if gif_high_quality: # extremely slow
            ffcmd = FFmpeg(inputs= {input_path : None},
                                    outputs={output_filepath :
                    f"-ss {start_time} -to {end_time} -vf 'setpts=PTS/{gif_speed},fps={gif_fps},scale=iw*{scale_factor}:-2,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse' -loop 0 {final_delay}"},
                global_options="-y " + global_options)
        else:
            ffcmd = FFmpeg(inputs= {input_path : None},
                                    outputs={output_filepath :
                    f"-ss {start_time} -to {end_time} -vf 'setpts=PTS/{gif_speed},fps={gif_fps},scale=iw*{scale_factor}:-2' -loop 0 {final_delay}"},
                global_options="-y " + global_options)

        try:
            cmd = ffcmd.cmd
            ffcmd.run()
            return cmd
        except FFRuntimeError:
            # try again as a static gif at the mid frame
            mid_frame = int((last_frame + first_frame) / 2)
            start_second = mid_frame / (fps * 1.0)
            start_time = seconds_to_hms(start_second)

            if gif_high_quality:
                ffcmd = FFmpeg(inputs= {input_path : None},
                                        outputs={output_filepath :
                        f"-ss {start_time} -vf 'scale=iw*{scale_factor}:-2,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse' -vframes 1"},
                    global_options="-y " + global_options)
            else:
                ffcmd = FFmpeg(inputs= {input_path : None},
                                        outputs={output_filepath :
                        f"-ss {start_time} -vf 'scale=iw*{scale_factor}:-2' -vframes 1"},
                    global_options="-y " + global_options)

    elif type == "wav" or type == "mp3":
        ffcmd = FFmpeg(inputs= {input_path : None},
                                outputs={output_filepath :
                f"-ss {start_time} -to {end_time} -copyts -ac 2"},
            global_options="-y " + global_options)

    elif type == "jpg":
        mid_frame = int((last_frame + first_frame) / 2)
        start_second = mid_frame / (fps * 1.0)
        start_time = seconds_to_hms(start_second)
        ffcmd = FFmpeg(inputs= {input_path : f"-ss {start_time}"},
                                outputs={output_filepath :
                f"-vf scale=iw*{scale_factor}:-2 -qscale:v 2 -vframes 1"},
            global_options="-y " + global_options)

    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# input: "40:30"
# output: 1.2121212121...
def decode_aspect(aspect):
    if not aspect or not isinstance(aspect, str):
        raise ValueError("'aspect' must be a string")
    parts = aspect.split(":")
    if len(parts) != 2:
        raise ValueError(f"'{aspect}' must be two values joined by ':'")
    try:
        den = float(int(parts[0]))
        div = float(int(parts[1]))
        return den / div
    except ValueError:
        raise ValueError(f"'{aspect}' must be two integers joined by ':'")
    except ZeroDivisionError:
        raise ValueError(f"the aspect '{aspect}' is not valid'")

# presumes AAC audio output
def combine_video_audio(video_path : str,
                        audio_path : str,
                        output_filepath : str,
                        global_options : str = "",
                        output_options : str = "-c:a aac"):
# ffmpeg -y -i "MALE Me-TV-03192023-0335PM[000001-001245].wav" -i "MALE Me-TV-03192023-0335PM[000001-001245].mp4" -c:v copy -c:a aac output1.mp4
    ffcmd = FFmpeg(
        inputs= {video_path : None,
                 audio_path : None},
        outputs={output_filepath : f"-c:v copy {output_options}"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# combine videos that have the same code,dimensions,etc
def combine_videos(input_paths : list,
                   output_filepath : str,
                   global_options : str="",
                   keep_concat_file : bool=False):
# ffmpeg -y -f concat -i file.txt -c copy final.mp4
# file 'output1.mp4'
# file 'output2.mp4'
    for input_path in input_paths:
        if not os.path.exists(input_path):
            raise ValueError(f"input path '{input_path}' not found")

    # uses the FFmpeg concat demuxer that only works with an input file
    path, filename, _ = split_filepath(output_filepath)
    concat_file = os.path.join(path, f"{filename}-files.txt")
    with Jot(file=concat_file) as jot:
        for input_path in input_paths:
            jot.down(f"file '{input_path}'")

    ffcmd = FFmpeg(
        inputs= {concat_file : "-safe 0 -f concat"},
        outputs={output_filepath : "-c: copy"},
        global_options="-y " + global_options)
    cmd = ffcmd.cmd
    try:
        ffcmd.run()
        if not keep_concat_file:
            os.remove(concat_file)
        return cmd
    except FFRuntimeError as error:
        raise ValueError(f"combine_video() received an error using FFmpeg: {str(error)}")
