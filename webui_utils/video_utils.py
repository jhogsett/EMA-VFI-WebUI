"""Functions for dealing with video using FFmpeg"""
import os
import glob
import subprocess
import json
from fractions import Fraction
from ffmpy import FFmpeg, FFprobe, FFRuntimeError
from .image_utils import gif_frame_count
from .file_utils import split_filepath

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
            frame_rate : int,
            output_filepath : str,
            crf : int = QUALITY_DEFAULT):
    """Encapsulate logic for the PNG Sequence to MP4 feature"""
    # if filename_pattern is empty it uses the filename of the first found file
    # and the count of file to determine the pattern, .png as the file type
    # ffmpeg -framerate 60 -i .\upscaled_frames%05d.png -c:v libx264 -r 60  -pix_fmt yuv420p
    #   -crf 28 test.mp4
    pattern = filename_pattern or determine_input_pattern(input_path)
    ffcmd = FFmpeg(
        inputs= {os.path.join(input_path, pattern) : f"-framerate {frame_rate}"},
        outputs={output_filepath : f"-c:v libx264 -r {frame_rate} -pix_fmt yuv420p -crf {crf}"},
        global_options="-y")
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# ffmpeg -y -i frames.mp4 -filter:v fps=25 -pix_fmt rgba -start_number 0 output_%09d.png
# ffmpeg -y -i frames.mp4 -filter:v fps=25 -start_number 0 output_%09d.png
def MP4toPNG(input_path : str,  # pylint: disable=invalid-name
            filename_pattern : str,
            frame_rate : int,
            output_path : str,
            start_number : int = 0,
            deinterlace : bool = False):
    """Encapsulate logic for the MP4 to PNG Sequence feature"""
    pattern = filename_pattern or determine_output_pattern(input_path)
    if deinterlace:
        filter = f"bwdif=mode=send_field:parity=auto:deint=all,fps={frame_rate}"
    else:
        filter = f"fps={frame_rate}"

    ffcmd = FFmpeg(inputs= {input_path : None},
        outputs={os.path.join(output_path, pattern) :
            f"-filter:v {filter} -start_number {start_number}"},
        global_options="-y")
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

# making a high quality GIF from images requires first creating a color palette,
# then supplying it to the conversion command
# https://stackoverflow.com/questions/58832085/colors-messed-up-distorted-when-making-a-gif-from-png-files-using-ffmpeg

# ffmpeg -i gifframes_%02d.png -vf palettegen palette.png
def PNGtoPalette(input_path : str, # pylint: disable=invalid-name
                filename_pattern : str,
                output_filepath : str):
    """Create a palette from a set of PNG files to feed into animated GIF creation"""
    if filename_pattern == "auto":
        filename_pattern = determine_input_pattern(input_path)
    ffcmd = FFmpeg(inputs= {os.path.join(input_path, filename_pattern) : None},
                outputs={output_filepath : "-vf palettegen"},
                global_options="-y")
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def PNGtoGIF(input_path : str, # pylint: disable=invalid-name
            filename_pattern : str,
            output_filepath : str,
            frame_rate : int):
    """Encapsulates logic for the PNG sequence to GIF feature"""
    # if filename_pattern is empty it uses the filename of the first found file
    # and the count of file to determine the pattern, .png as the file type
    # ffmpeg -i gifframes_%02d.png -i palette.png -lavfi paletteuse video.gif
    # ffmpeg -framerate 3 -i image%01d.png video.gif
    pattern = filename_pattern or determine_input_pattern(input_path)
    output_path, base_filename, _ = split_filepath(output_filepath)
    palette_filepath = os.path.join(output_path, base_filename + "-palette.png")
    palette_cmd = PNGtoPalette(input_path, pattern, palette_filepath)

    ffcmd = FFmpeg(inputs= {
            os.path.join(input_path, pattern) : f"-framerate {frame_rate}",
            palette_filepath : None},
        outputs={output_filepath : "-lavfi paletteuse"},
        global_options="-y")
    cmd = ffcmd.cmd
    ffcmd.run()
    return "\n".join([palette_cmd, cmd])

def GIFtoPNG(input_path : str, # pylint: disable=invalid-name
            output_path : str,
            start_number : int = 0):
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
        global_options="-y")
    cmd = ffcmd.cmd
    ffcmd.run()
    return cmd

def deduplicate_frames(input_path : str,
                      output_path : str,
                      threshold : int):
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
        global_options="-y")
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
    filter = f"select='gt(scene\,{threshold})',metadata=print:file=-"

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
