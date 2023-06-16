**Resize Frames** - Use `OpenCV Resize` to Enlarge or Reduce Frames

## Uses
- Increase or decrease the size of video frames
- Modify Aspect Ratio
- Reduce image blur prior to using _Upscale Frames_ to enlarge using _Real-ESRGAN_

## How It Works
1. Set _Input Path_ to a directory on this server to the PNG files to be resized
1. Set _Output Path_ to a directory on this server for the resized PNG files
1. Set _New Width_ and _New Height_ to the dimensions for the new PNG frames
1. Set _Scaling Type_ to one of the available types:
    - **area** `cv2.INTER_AREA` (best quality reducing)
    - **cubic** `cv2.INTER_CUBIC` (better quality than linear)
    - **lanczos** `cv2.INTER_LANCZOS4` (best quality enlarging)
    - **linear** `cv2.INTER_LINEAR` (fast, good at enlarging)
    - **nearest** `cv2.INTER_NEAREST` (fastest, lower quality)
1. Click _Resize Frames_
1. When complete, the output path will contain a new set of frames
