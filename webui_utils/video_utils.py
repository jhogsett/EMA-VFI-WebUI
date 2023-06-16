"""Functions for dealing with video using FFmpeg"""
import os
import glob
import subprocess
import json
from fractions import Fraction
from ffmpy import FFmpeg, FFprobe
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
            start_number : int = 0):
    """Encapsulate logic for the MP4 to PNG Sequence feature"""
    pattern = filename_pattern or determine_output_pattern(input_path)
    ffcmd = FFmpeg(inputs= {input_path : None},
        outputs={os.path.join(output_path, pattern) :
            f"-filter:v fps={frame_rate} -start_number {start_number}"},
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
    print(ffcmd.cmd)
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8").strip()
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

def get_video_details(input_path : str) -> dict:
    """Use FFprobe to get streams and format information for a video"""
    # ffprobe.exe -v quiet -show_format -show_streams -count_frames -of json file.mp4
    ffcmd = FFprobe(inputs= {input_path : "-show_format -show_streams -count_frames -of json"},
                    global_options="-v quiet")
    result = ffcmd.run(stdout=subprocess.PIPE)
    stdout = result[0].decode("UTF-8").strip()
    return json.loads(stdout)

def get_duplicate_frames(input_path : str, threshold : int) -> dict:
    """Use FFmpeg to get a list of duplicate frames without making changes
       returns an array of True/False values with all duplicate frame positions set True
    """
    # ffmpeg -i file.mp4 -vf mpdecimate=hi=5000:lo=5000:frac=1 -loglevel debug -f null -
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

    # each False (non-dupe) preceding a True (dupe) should be marked as
    # dulicate to mark it as part of a group of duplicate frames
    group_map = is_dupe_map.copy()
    for index, is_dupe in enumerate(is_dupe_map):
        print(f"index: {index} is_dupe: {is_dupe}")
        if index < len(is_dupe_map)-1:
            # print(f"index {index} < {len(is_dupe_map)-1}")
            if not is_dupe and is_dupe_map[index+1]:
                print(f"index {index} not is_dupe ({not is_dupe}) and is_dupe_map[{index+1}] ({is_dupe_map[index+1]})")
                group_map[index] = True
    return group_map

def get_duplicate_frames_report(input_path : str, threshold : int) -> str:
    duplicate_frames = get_duplicate_frames(input_path, threshold)
    filenames = sorted(glob.glob(os.path.join(input_path, "*.png")))
    if len(duplicate_frames) != len(filenames):
        raise ValueError(
    f"frame count mismatch FFmpeg ({len(duplicate_frames)}) vs Python ({len(filenames)})")
    is_inside_group = duplicate_frames[0]
    group_number = 1 if is_inside_group else 0
    result = []
    separator = ""
    for index, entry in enumerate(duplicate_frames):
        if entry: # is duplicate
            if is_inside_group: # continue in group
                pass
            else: # start duplicate group
                is_inside_group = True
                group_number += 1
                result.append(f"Duplicate Frame Group #{group_number}")
            result.append(f"Frame #{index} : {filenames[index]}")
        else: # not duplicate
            if is_inside_group: # leave group
                is_inside_group = False
                result.append(separator)
            else: # continue not in group
                pass
    return "\r\n".join(result)
