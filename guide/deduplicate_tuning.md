**Deduplicate Threshold Tuning** - Test a range of duplicate detection thresholds

## Why Use Threshold Tuning
- Tuning allows running a series of _Duplicate Frames Reports_ with increasing detection levels
- Use it to find the best threshold for the _Auto-Fill Duplicate Frames_ feature
- For example, find the best threshold that:
    - Maximizes detecting real duplicates
    - Minimizes detecting false positives

## How It Works
1. Set _Input PNG Files Path_ to a path on this server for the PNG files being tested
1. Set _Starting Detection Threshold_ to set the lower limit on tested thresholds
1. Set _Ending Detection Threshold_ to set the upper limit on tested thresholds
1. Set _Detection Threshold Increase Step_ to the increase in detection threshold after each round
1. Set _Maximum Duplicates Per Group_ to limit consecutive found duplicate frames
    - This can help to find a suitable upper limit for _Ending Detect Threshold_
    - Values:
        - Set to `0` to not limit the number of consecutive duplicates
        - Set to `1` to prevent duplicates altogether
        - Set to any other value to limit the consecutive duplicates
    - _Tip: in most cases, duplicates will be limited to several frames only_
1. Click _Create Report_
    - The status of the tuning can be tracked in the progress bar
1. When complete, the _Download_ box will appear with a .CSV version of the report
    - _Tip: The file is ready for import into spreadsheet software_
1. The _Tuning Report_ box shows the result of the tuning series, or any error encountered

## Tuning Report Columns
- _Threshold_ - the detection threshold for the tuning round
- _dupe_percent_ - the percent of duplicates found
- _max_group_ - the size of the largest found group of duplicate frames
    - _Tip: The above columns are useful if graphing the results for analysis_
- _dupe_count_ - the count of duplicates found
- _first_dupe_ - the frame index of the first found duplicate frame

## Important
- `ffmpeg.exe` must be available on the system path
- The values for the _Threshold_ sliders can be changed in the `config.yaml` file section `deduplicate_settings`

## More Details ##
- The FFmpeg _mpdecimate_ video filter is used to detect and remove duplicates
    - The _hi_ and _lo_ mpdecimate parameters are set to the specified theshold
    - the _frac_ mpdecimate parameter is set to `1`
- Example: a 30 FPS video with 24 FPS real frames (20% duplicated frames)
    - With _Threshold_ set to the minimum `0`, 1 frame was removed
    - When set to maximum `25000`, all frames except 1 were removed
    - When set to the default `2500`, 20% of the frames were removed
