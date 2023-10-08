**Video Assembler** - Create video from a set of video clips with audio

## How It Works
1. Choose _Individual Path_ or _Batch Processing_
    - If **Individual Path**
        - Set _Video Clips Path_ to a path on this server to the video clips to be combined
        - Set _Combined Video Path_ to a path and filename on this server for the combined video
            - _Tip: Leave this field blank to use the_ Video Clips Path _name for the video_
    - If **Batch Processing**
        - Set _Video Clip Directories Path_ to a directory on this server containing directories of video clips to be combined
            - Note: The containing directory name will be used as the output filename
1. Click _Assemble Video_ or _Assemble Batch_
1. The clips will be assembled into one or more videos

## Important
- The video clip files in a directory should be all of the same type

## Notes
- Uses the FFmpeg _concat demuxer_ to assemble the video from the provided clips in **filename order**
- The first found clip specifies the video output format
- Combining clips of different dimensions and frame rates seems to work
    - _Tip: Combining clips of different types appears to not work_