**GIF to MP4** - Recover the Original Video from Animated GIF or Low-FPS Movie

## Uses
- Recover the Original Video from an Animated GIF
- Create a High-Def version of a Low-Res / Low-FPS Video
- Recover the original video from a timelapse video
- Easily create a slow-motion video in one-click

## Important

Two third-party packages are required to use this feature:
* FFmpeg for file conversion [free download](https://ffmpeg.org/download.html)
    - `ffmpeg.exe` and `ffprobe.exe` must be available on the system path
* Real-ESRGAN for frame restoration/upscaling [see wiki page](https://github.com/jhogsett/EMA-VFI-WebUI/wiki/Installing-Real-ESRGAN-Add-On)
    - The `realesrgan` directory must be copied to the `EMA-VFI-WebUI` directory

## How it works

1. Set _Input Frame Size Upscale Factor_ to choose a _zoom factor_
    - Choose a value to set the enlargement size of the frame
    - The default is 4.0, with a range of 1.0 to 8.0
    - _Tip: Frames will have noise removed even if set to a 1.0 zoom factor_
1. Set _Input Frame Rate Upscale Factor_ to choose an _inflation factor_
    - Choose a value to set the FPS increase for the video
    - The default is 4, the range is from 1 to 8
1. Choose a _Frame Processing Order_
    - _Rate First, then Size_ is faster and requires less VRAM
        - Larger images take longer to interpolate
    - _Size First, then Rate_ is slower, but may produce higher quality
        - Motion flow might be tracked better at the original frame rate
1. Set _MP4 File_ to a path and filename on this server for the converted MP4 file
    - Leave blank to use a default .mp4 filename in the same location
    - It will use the original name an include conversion details
1. Choose the video _MP4 Frame Rate_
1. Set _Quality_ to the required video quality
    - The range is 17-28 (17 is near-lossless)
    - Lower numbers = better quality with a higher file size
    - This value is passed to `ffmpeg.exe` as the `-crf` parameter
    - The range of quality values can be changed in `config.yaml`
1. Choose _Individual File_ or _Batch Processing_
    - For Individual File, Set _GIF File_ to a GIF, MP4 or other video file on this server
    - For Batch Processing, Set _Path to GIF Files_ to a directory on this server with GIF, MP4 and other video files
    - This feature has been tested with _GIF_, _MP4_ and _MPG_ files
1. Click _Convert_
1. _GIF to MP4_ is run to create a set of PNG frame files
1. _Video Inflation_ is run to create filler frames to increase FPS
1. _Upscale Frames_ is run to use Real-ESRGAN to clean and enlarge frames
1. _PNG to MP4_ is run to create the output MP4 video

## Notes

- This process could be slow, perhaps many hours long!
- Progress is shown in the console using a standard progress bar
- The browser window does NOT need to be left open
