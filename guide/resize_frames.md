**Resize Frames** - Use `OpenCV` to Reduce, Enlarge and Crop Frames

## Uses
- Increase or decrease the size of video frames
- Fix issues with Aspect Ratio
- Reduce image blur prior to using _Upscale Frames_ to enlarge using _Real-ESRGAN_
- Crop out VHS tape noise in a digitized video

## How It Works
1. Set _Scaling Type_ to one of the available types:
    - **area** `cv2.INTER_AREA` (best quality reducing)
    - **cubic** `cv2.INTER_CUBIC` (better quality than linear)
    - **lanczos** `cv2.INTER_LANCZOS4` (best quality enlarging)
    - **linear** `cv2.INTER_LINEAR` (fast, good at enlarging)
    - **nearest** `cv2.INTER_NEAREST` (fastest, lower quality)
    - **none** - disable resizing
1. Set _Scale Width_ and _Scale Height_ to the resizing dimensions for the frames
1. Set _Cropping Type_ to one of the available types:
    - **crop** - enable cropping
    - **none** - disable cropping
1. Set _Crop Width_ and _Crop Height_ to the cropping dimensions for the frames
    - Keep the default values of `-1` to match the resizing values
1. Set _Crop X Offset_ and _Crop Y Offset_ to the cropping origin for the frames
    - Keep the default values of `-1` to automatically center the cropped portion
1. Choose _Individual Path_ or _Batch Processing_
    - If **Individual Path**
        - Set _Input Path_ to a directory on this server to the PNG files to be resized
        - Set _Output Path_ to a directory on this server for the resized PNG files
    - If **Batch Processing**
        - Set _Input Path_ to a directory on this server containing PNG frame groups to be resized
        - Set _Output Path_ to a directory on this server for the resized PNG frame groups
1. Click _Resize Frames_ or _Resize Batch_
1. When complete, the output path(s) will contain a new set of frames
- Progress can be tracked in the console

## Important
- If cropping only, the original image dimensions **must be** entered into the _Scale Width_ and _Scale Height_ fields for automatic centering to work
- Cropping is performed after resizing
