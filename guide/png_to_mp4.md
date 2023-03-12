**PNG Sequence to MP4** - Use FFMpeg to convert a video PNG sequence to MP4

## How It Works
1. Set _PNG Files Path_ to a path on this server to the PNG files being converted
1. Set _MP4 File_ to a path and filename on this server for the converted MP4 file
1. Set _Input Name Pattern_ according to the format of the input PNG filenames
    - The PNG files should all have the same base filename + a fixed-width frame index starting at 0
    - Examples:
        - For files named `image000.png` through `image999.png` the pattern should be `image%03d.png`
        - For files named `image00000.png` through `image99999.png` the pattern should be `image%05d.png`
    - The special pattern "auto" can be used to detect the pattern if the files conform to the above format
1. Set _Frame Rate_ to the required video FPS
1. Set _Quality_ to the required video quality
    - The range is 17-28 (17 is near-lossless)
    - Lower numbers = better quality with a higher file size
    - This value is passed to `ffmpeg.exe` as the `-crf` parameter
    - The range of quality values can be changed in `config.yaml`
1. Click _Convert_
1. `ffmpeg.exe` is used to perform the conversion
1. The _Details_ box shows the `ffmpeg.exe` command line used

## Important
- `ffmpeg.exe` must be available on the system path
- The produced video will not have an audio stream
- _Resequence Files_ can be used to renumber a PNG sequence
- The _Video Preview_ tab on the _Video Blender_ page can be used to watch a preview video of a set of PNG files
