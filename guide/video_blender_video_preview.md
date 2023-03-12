**Video Blender Video Preview** - Preview the current movie restoration

## How To Use

1. Set _Path to PNG Sequence_ to a directory on this server containing the PNG frames files to preview
    - This is pre-filled with the current project path if the _Preview Video_ button is used
1. Set _Frame Rate_ to movie's FPS
1. Click _Render Preview_
1. A MP4 video is created and loaded into the video player


## Important
- `ffmpeg.exe` must be available on the system path
- Preview videos are rendered in the directory set by the config setting `directories:working`
    - The directory is NOT automatically purged

## Tip
- This tab can be used to render and watch a preview video for any directory of video frame PNG files
- **Requirements:**
    - The files must be video frame PNG files with the same dimensions
    - The filenames must all confirm to the same requirements:
        - Have the same starting base filename
        - Followed by a frame index integer, all zero-filled to the same width
        - Example: `FRAME001.png` through `FRAME420.png`
        - There must be no other PNG files in the same directory
