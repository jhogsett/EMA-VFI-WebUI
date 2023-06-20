**Media File Details** - Report at-a-glance details about any media file

## How It Works
1. Set _Media Files Path_ to a path on this server to the media file to inspect
1. Leave _Count Frames_ checked to ensure the frame count can be displayed
    - Uncheck _Count Frames_ for large media files
        - FFprobe scans the entire file counting frames, which can take some time
    - _Tip: Some media types store the frame count and don't need counting_
1. Click _Get Details_
1. Important video stream details are displayed
    - Frame Rate _(seconds)_
    - Dimensions _(width X height)_
    - Duration _(hh::mm::ss)_
    - Frame Count _(frames)_
    - File Size _(bytes)_
1. Additional details about the media file are displayed in the_Details_ box

## Note
- If FFProbe encounters an error while processing the request, details will be displayed in the _Details_ box

## Important
- `ffprobe.exe` must be available on the system path
