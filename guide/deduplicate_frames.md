**Deduplicate Frames** - Use FFmpeg to detect and remove duplicate PNG frame files

## How It Works
1. Set _Input PNG Files Path_ to a path on this server for the PNG files being deduplicated
1. Set _Output PNG Files Path_ to a path on this server to stored the deduplicated PNG files
    - Output PNG File Path can be left blank to use the default folder
    - The default folder is set by the `config.directories.output_deduplication` setting
1. Set _Detect Threshold_ to specify the sensitivity to frame differences
    - A lower value removes fewer frames; a higher value removes more frames
    - This value requires experimentation. See _More Details_ below.
1. Click _Deduplicate_
1. `ffmpeg.exe` is used to perform the deduplication
1. The _Details_ box shows the `ffmpeg.exe` command line used

## More Details ##
- The FFmpeg _mpdecimate_ video filter is used to detect and remove duplicates
    - The _hi_ and _lo_ mpdecimate parameters are set to the specified theshold
    - the _frac_ mpdecimate parameter is set to `1`
- Example: a 30 FPS video with 24 FPS real frames (20% duplicated frames)
    - With _Threshold_ set to the minimum `0`, 1 frame was removed
    - When set to maximum `25000`, all frames except 1 were removed
    - When set to the default `2500`, 20% of the frames were removed

## Important
- `ffmpeg.exe` must be available on the system path
- _Resequence Files_ can be used to renumber a PNG sequence
- The _Video Preview_ tab on the _Video Blender_ page can be used to watch a preview video of a set of PNG files
- The values for the _Threshold_ slider can be changed in the `config.yaml` file section `deduplicate_settings`
