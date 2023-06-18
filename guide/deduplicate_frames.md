**Deduplicate Frames** - Detect and remove duplicate PNG frame files

## How It Works
1. Set _Input PNG Files Path_ to a path on this server for the PNG files being deduplicated
1. Set _Output PNG Files Path_ to a path on this server to store the deduplicated PNG files
    - Output PNG File Path can be left blank to use the default folder
    - _Tip: The default folder is set by the_ `config.directories.output_deduplication` _setting_
1. Set _Detect Threshold_ to specify the sensitivity to frame differences
    - A lower value finds fewer duplicates; a higher value finds more
    - This value requires experimentation. See _More Details_ below.
1. Set _Maximum Duplicates Per Group_ to limit consecutive found duplicate frames
    - This can help to find a suitable upper limit for _Detect Threshold_
    - Values:
        - Set to `0` to not limit the number of consecutive duplicates
        - Set to `1` to prevent duplicates altogether
        - Set to any other value to limit the consecutive duplicates
    - _Tip: in most cases, actual duplicates will be limited to several frames only_
1. Click _Deduplicate Frames_
1. The _Details_ box shows the result of the operation, or any errors encountered

## Important
- **Note!** If the frames in the output path are to be fed to FFmpeg or video editing software, use _Resequence Files_ to remove gaps in the numbering sequence
- `ffmpeg.exe` must be available on the system path
- The _Video Preview_ tab on the _Video Blender_ page can be used to watch a preview video of a set of PNG files
- The values for the _Threshold_ slider can be changed in the `config.yaml` file section `deduplicate_settings`

## More Details ##
- The FFmpeg _mpdecimate_ video filter is used to detect and remove duplicates
    - The _hi_ and _lo_ mpdecimate parameters are set to the specified theshold
    - the _frac_ mpdecimate parameter is set to `1`
- Example: a 30 FPS video with 24 FPS real frames (20% duplicated frames)
    - With _Threshold_ set to the minimum `0`, 1 frame was removed
    - When set to maximum `25000`, all frames except 1 were removed
    - When set to the default `2500`, 20% of the frames were removed
