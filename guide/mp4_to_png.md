**MP4 to PNG Sequence** - Use FFmpeg to convert MP4 video to set of PNG frame files

## How It Works
1. Set _MP4 File_ to the path and filename of a MP4 file on this server for conversion
1. Set _PNG Files Path_ to a path on this server for the converted PNG files
1. Set _Output Filename Pattern_ to a _pattern_ for the new filenames
    - The pattern should be a base filename + frame index specifier + and filetype
    - The frame index specifier should be based on the video frame count for proper sorting
    - Examples:
        - `image%03d.png` allows for output filenames `image000.png` through `image999.png`
        - `image%05d.png` allows for output filenames `image00000.png` through `image99999.png`
1. Set _Frame Rate_ to the source video FPS to avoid repeated or dropped frames
    - _Tip: The_ Video Details _feature can be used to get the frame rate for a media file_
1. Typically, leave _Deinterlace Frames_ unchecked
    - Check _Deinterlace Frames_ if converting interlaced content
        - Examples: _Over-the-Air_ content, _480i_ & _1080i_ content
        - Deinterlacing removes the _combing effect_ that can occur when converting interlaced content
1. Click _Convert_
1. `ffmpeg.exe` is used to perform the conversion
1. The _Details_ box shows the `ffmpeg.exe` command line used

## Important
- If _Deinterlace Frames_ is checked, the actual FPS of the converted frames will be doubled
    - For example, a 30 FPS _interlaced_ video will be converted to PNG frames as a 60 FPS _progressive_ video, doubling the frame count
- `ffmpeg.exe` must be available on the system path
- The _Video Preview_ tab on the _Video Blender_ page can be used to watch a preview video of a set of PNG files
