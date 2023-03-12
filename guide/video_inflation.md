**Video Inflation** - Use _Frame Interpolation_ to increase FPS for super-slow motion video

## Uses
- Create a _super-slow-motion_ video
- Recover real-time video from a timelapse video or GIF
- make discrete motion continuous

## How It Works
1. Set _Input Path_ to a directory on this server to the PNG files to be inflated
1. Set _Output Path_ to a directory on this server for the inflated PNG files
    - Output Path can be left blank to use the default folder
    - The default folder is set by the `config.directories.output_inflation` setting
1. Set _Split Count_ for the number of new _between_ frames
    - The count of interpolated frames is computed by this formula:
        - F=2**S-1, where
        - F is the count of interpolated frames
        - S is the split count
1. Click _Inflate Video_
1. _Frame Interpolation_ is done between each pair of frames
    - New frames are created according to the split count
    - The original and new frames are copied to the output path
1. When complete, the output path will contain a new set of frames

## Important
- This process could be slow, perhaps many hours long!
- Progress is shown in the console using a standard progress bar
- The browser window does NOT need to be left open
- There currently isn't an automatic way to resume a stalled inflation
    - Suggestion:
        - Set aside the rendered frames from the _input path_
        - Re-run the inflation
        - Use the _Resequence Files_ tool to rename the the two sets of rendered frames so they can be recombined
