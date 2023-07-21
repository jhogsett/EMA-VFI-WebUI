**Video Remixer Processing Options** - Choose processing options for the remixed video

## How To Use
1. Check _Fix Aspect Ratio_ to apply the _Resize_ and _Crop_ settings from the _Remix Settings_ tab
1. Check _Resynthesize Frames_ to replace all source frames with AI-interpolated _likely_ replacements
    - Note: This causes the first and last frames from each scene to be lost since there are not two adjacent frames for interpolation
    - When resynthesis is used, the WAV audio clips are shortened to match
1. Check _Inflate New Frames_ to insert AI-interpolated _likely_ frames between all real frames
    - This causes the effective frame rate of the remix video to double
    - When inflation used, this is taken into aacount for creating the final video clips
1. Check _Upscale Frames_ to use AI to clean and enlarge frames
    - Choose whether to upscale by _1X_, _2X_ or _4X_
    - Upscaling at 1X will cleanse the frames without enlarging
    - Upscaling at 2X or 4X will cleanse the frames and double or quadruple the frame size
1. Click _Process Remix_ to kick off the processing
- Progress can be tracked in the console

## ⚠️Important⚠️
- **THIS PROCESS COULD BE SLOW, POSSIBLY MANY HOURS OR DAYS!!!**
- The browser window does NOT need to be left open
    - The project can be reopened later to resume where you left off
- `ffmpeg.exe` must be available on the system path
