**Change FPS** - Use _Frame Search_ to change frame rate by _Inserting_ and _Removing_ frames

## Uses
- Convert a video from any FPS to any FPS
- Create slow-motion video at any slow-down rate
- Create time-lapse video at any speed-up rate

## How it works
1. Set _Starting FPS_ to the frame rate of the video being converted
1. Set _Ending FPS_ to the frame rate for the converted video frames
    - The lowest-common-multiple _Super-Sampling_ frame rate is computed
    - This rate is the smallest that's evenly divisible by both rates
        - The super-sample rate shows in the `Lowest Common FPS` box
    - A _Super-Sampling Set_ of frames will be computed at the higher common frame rate
        - If needed, _Filler Frames_ will be interpolated to inflate the original video's frame rate to the super-sample rate
            - The fill count shows in the `Filled Frames per Input Frame` box
        - If needed, the super-sample set is _Sampled_ to achieve the final frame rate
            - The sample rate shows in the `Output Frames Sample Rate` box
1. Set _Search Precision_ to the depth of search needed for accuracy
    - High precision yields precise frame timing, but takes a long time
    - Less precision is faster, with possible imprecise frame timing
    - The target search times and predicted matches are shown in the`Frame Search Times` and `Predicted Matches` box
1. Leave _Duplicate frames to fill_ unchecked except in special cases
    - If checked, the _before_ frame of the Frame Search pair of frames will be duplicated instead of using interpolation to find frame at a precise frame
    - _Tip: This will add filler frames very quickly, but very imprecisely_
1. Choose _Individual Path_ or _Batch Processing_
    - If **Individual Path**
        - Set _Input Path_ to a directory on this server containing video frame PNG files for conversion
        - Set _Output Path_ to a directory on this server for the converted PNG files
            - Output Path can be left blank to use the default folder
            - The default folder is set by the `config.directories.output_fps_change` setting
    - If **Batch Processing**
        - Set _Input Path_ to a directory on this server containing PNG frame groups to be converted
        - Set _Output Path_ to a directory on this server for the converted PNG frame groups
1. Click _Convert_ or _Convert Batch_
1. When complete, files are resequenced to have a fixed-width frame index
    - Filenames include a reference to their new resampled FPS

## Important
- This process could be slow, perhaps many hours long!
- Progress is shown in the console using a standard progress bar
- The browser window does NOT need to be left open
- Some combinations of Starting FPS / Ending FPS may be impractical
    - A warning is displayed if the `Filled Frames per Input Frame` exceeds 100
  - Check the _Frame Search Times_ and _Predicted Matched_ fields
