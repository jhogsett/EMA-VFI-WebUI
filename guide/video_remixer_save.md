**Video Remixer Save Remix** - Create processed scene clips and assemble remixed video

The _Processed Content_ box shows a summary of the processing just completed for your information.

## How To Use
1. Choose _Video Quality_
    - Lower values mean higher quality videos
    - This is passed to _FFmpeg_ as the `-crf` MP4 quality parameter
1. Enter an _Output Filepath_
1. Click _Save Remix_
    - The previously processed video and audio clips are merged
    - The final video is concatenated from the clips (without re-encoding)

## Important
- `ffmpeg.exe` must be available on the system path
