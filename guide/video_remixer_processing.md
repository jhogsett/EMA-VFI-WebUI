**Video Remixer Process Remix** - Choose processing options and process remix content

## How To Use
1. Check _Resize / Crop Frames_ to apply the _Resize_ and _Crop_ settings from the _Remix Settings_ tab
1. Check _Resynthesize Frames_ to replace all source frames with AI-interpolated replacements
    - Choose the Resynthesis type:
    - **_Clean_** Two-Pass Resynthesis, First Pass Only
        - Clean frames by replacing each with an interpolated frame in a single pass
        - Fast deep-cleaning method, but not perfectly aligned with audio
    - **_Scrub_** Two-Pass Resynthesis, Both Passes
        - Clean frames by replacing each with an interpolated frame in two passes
        - Best deep-cleaning method, with perfect audio alignment
    - **_Replace_** One-Pass Resynthesis
        - Clean frames by completely replacing with interpolations from adjacent frames
        - Deepest cleaning method, but does not handle fast-moving content well
1. Check _Inflate New Frames_ to insert AI-interpolated frames between all real frames
    - Choose whether to inflate by _2X_, _4X_, _8X_ or _16X_
        - The choices will insert 1, 3, 7 or 15 new frames between existing frames
    - Choose whether to produce a slow-motion video
        - **_No_** Create a real-time video
            - Adjust the output FPS to compensate for the inserted frames
        - **_Audio_** Create a slow-motion video with audio
            - Adjust the output FPS and audio pitch to compensate for the new frames
        - **_Silent_** Create a slow-motion video without audio
            - Use silence instead of pitch-compensated audio
1. Check _Upscale Frames_ to use AI to clean and enlarge frames
    - Choose whether to upscale by _1X_, _2X_, _3X_ or _4X_
    - Upscaling at 1X will cleanse the frames without enlarging
    - Upscaling at 2X - 4X will cleanse the frames and double, triple or quadruple the frame size
1. Click _Process Remix_ to kick off the processing
- Progress can be tracked in the console

## Advanced Options Accordion
- Check _Automatically save default MP4 video_ to:
  - Save the Remix Video using default MP4 settings as seen on the _Save MP4 Remix_ tab
- Check _Delete processed content after saving_ to:
  - Automatically purged all generated project content after saving the Remix Video

## Note
- Content may be _purged_ (soft-deleted) when clicking _Process Remix_
    - Previous process content not currently needed is set aside
- Purged content my be recovered from the `purged_content` project directory

## ⚠️Important⚠️
- **THIS PROCESS COULD BE SLOW, POSSIBLY MANY HOURS OR DAYS!!!**
- The browser window does NOT need to be left open
    - The project can be reopened later to resume where you left off
- `ffmpeg.exe` must be available on the system path
