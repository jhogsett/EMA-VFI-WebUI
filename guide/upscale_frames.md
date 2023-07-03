**Upscale Frames** - Use _Real-ESRGAN_ to Enlarge and Clean Frames

## Uses
- Increase the size of video frames
- Clean up dirty/deteriorated frames
- Can be used to clean frames without upscaling

## Important
Real-ESRGAN must be installed locally to use
1. See the _Resources_ tab or go to [Real ESRGAN Github](https://github.com/xinntao/Real-ESRGAN) to access Real-ESRGAN repository
1. Clone their repo to its own directory and follow their instructions for local setup
1. Copy the `realesrgan` directory to your `EMA-VFI-WebUI` directory
* The _Real-ESRGAN 4x+_ model (65MB) will automatically download on first use

## How It Works
1. Set _Frame Upscale Factor_ for the desired amount of frame enlargement
    - The factor can be set between 1.0 and 8.0 in 0.05 steps
    - Real-ESRGAN will perform upscaling when _factor_ is > 1.0
        - _Tip: It will remove dirt and noise even when not upscaling_
1. Choose whether or not to use _Tiling_
    - select _Auto_ to ensure all files are processed
        - Files will be processed first for the best possible quality
        - Files that fail to process will be redone using _tiling_ (see _Yes_ option below)
    - Select _No_ for the best quality.
        - Entire images will be upscaled at once
        - Files that cannot be processed due to VRAM limitations will be skipped
    - Select _Yes_ if upscaling large images, or running into low VRAM conditions
        - Images will be upscaled in blocks then stiched together
        - Tiling _Size_ and _Padding_ (in pixels) are set using the config settings:
            - `realesrgan_settings:tiling` and `realesrgan_settings:tile_pad`
1. Choose _Individual Path_ or _Batch Processing_
    - If **Individual Path**
        - Set _Input Path_ to a directory on this server to the PNG files to be upscaled
            - JPG, GIF and BMP files will also be upscaled if found in the path
            - _Tip: the config setting_ `upscale_settings:file_types` _specifies the searched types_
        - Set _Output Path_ to a directory on this server for the upscaled PNG files
            - If Output Path is set, upscaled files are saved as sequentially indexed PNG files with a fixed filename
            - When Output Path is left empty, upscaled files are saved to the input path using the original filename and format, and marked with the outscale amount.
    - If **Batch Processing**
        - Set _Input Path_ to a directory on this server containing PNG frame groups to be upscaled
        - Set _Output Path_ to a directory on this server for the upscaled PNG frame groups

1. Click _Upscale Frames_ or _Upscale Batch_
- Progress can be checked in the console

1. _Real-ESRGAN_ is used on each frame in the input path
    - Frames are cleaned up, and enlarged if necessary
    - The new frames are copied to the output path
1. When complete, the output path will contain a new set of frames
