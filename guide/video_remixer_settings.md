**Video Remixer Settings** - Choose content options for project set up

## How To Use
1. Set _Project Path_ to a path on your server for project data to be stored
    - **Important** - Video frame data can consume large amounts of disk space
    - _Tip: A default path is offered based on the original video location_
1. Choose a _Remix Frame Rate_
    - For best results, this should probably be related to the source (double, half, etc.)
    - _Tip: Broadcast content is typically based on a multiple of 29.97 FPS_
1. Leave _Deinterlace Source Video_ unchecked
    - If remixing broadcast content, use deinterlacing to remove interlacing artifacts
1. Choose a _Split Type_
    - **_Scene_**
        - Split by scene using FFmpeg scene detection
        - Set _Scene Detection Threshold_ to a value 0.0 to 1.0 to set sensitivity
            - A higher value means fewer found scenes
    - **_Break_**
        - Split by breaks using FFmpeg break detection
        - Set _Break Minimum Duration_ for the minimum break duration in seconds
        - Set _Break Black Frame Ratio_ to a value 0.0 to 1.0 for the ratio of black pixels to count as break frame
    - **_Minute_**
        - Split by minute, as calculated based on the source video frame rate
1. Set **_Resize_** and **_Crop_** Settings
    - **Important**
        - When using the _Aspect Ratio_ feature later, _Resize_ and _Crop_ settings must be set properly.
    - **Recommendations**
        - If a correction is needed, _Video Details_ might show something like this:
            ```
            Display Size: 853x480
            Aspect Ratio: 16:9
            Content Size: 704x480
            ```
            - _Display Size_ The content should be expanded to this size for display
            - _Aspect Ratio_ The content should be cropped to this shape for display
            - _Content Size_ This is the native size of the video content
        - Given the above example, the _Resize_ and _Crop_ settings should be set to:
            - _Resize W x H_: `852 x 480`
            - _Crop W x H_: `852 x 480`
        - Explanation
            - The content should be displayed at `853 x 480`, so resize the original `704 x 480` content
            - Use the _even_ value `852 x 480` instead
                - some encoders can't handle odd dimensions
                - a dropped pixel isn't noticeable
        - Letterboxed Content
            - For **4:3** or similar content with _letterboxing_ like television broadcasts, the settings may need to be like these:
            - _Crop W x H_: `720 x 480`
            - _Crop W x H_: `640 x 480`
1. Click _Next_
    - The settings will be confirmed on the next page before any processing starts

## More Options Accordion
1. Click _More Options_ to access additional project setup options
    - Click _Reuse Last-Used Settings_ to load the settings from the last created project
        - Useful when processing a series of similar content such as TV programs
    - Click _Use Memorized Setting_ to load the settings that were previously _remembered_
    - Click _Remember These Settings_ to save the settings for later use
    - Set _Crop X Offset_ and _Crop Y Offset_, useful for:
        - Removing letter/pillar boxes
        - Fixing incorrectly centered content
        - Isolating part of a scene
    - Leave _Frame Format_ set to _png_ or choose _jpg_
        - _jpg_ requires less storage space than _png_
        - _Tip:_ Use _jpg_ for **_4K_** and higher content

## Important
- `ffmpeg.exe` must be available on the system path
