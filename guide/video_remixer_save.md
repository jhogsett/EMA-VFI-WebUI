**Video Remixer Save Remix** - Merge audio with processed content and create remixed video

The _Processed Content_ box shows a summary of the completed processing.

## How To Use
1. Choose _Create MP4 Remix, Create Custom Remix_, _Create Marked Remix_ or _Create Labeled Remix_
    - If **Create MP4 Remix**
        - Choose _Video Quality_
            - Lower values mean higher quality videos
            - This is passed to _FFmpeg_ as the `-crf` MP4 quality parameter
        - Enter an _Output Filepath_ for the remix video
            - _Tip: a default is chosen based on the chosen processing options_
    - If **Create Custom Remix**
        - Enter _Custom FFmpeg Video Output options_
            - The entered value is used when creating video clips from the processed PNG frames files
            - It's passed to FFMpeg as options for the video-only output files
        - Enter _Custom FFmpeg Audio Output options_
            - The entered value is used when combining video clips with original WAV audio
            - It's passed to FFMpeg as options for the audio+video output files
        - **_Tip: See below for custom remix examples_**
        - Enter an _Output Filepath_ for the remix video
    - If **Create Marked Remix**
        - Leave _Marked FFmpeg Video Output options_ set _as_is_
            - Optionally, customize the FFmpeg _drawtext_ filter settings
                - For example, to move the text to the bottom,
                    - Change: `y=(text_h*1)`
                    - To: `y=h-(text_h*2)`
            - The entered value is used when creating video clips from the processed PNG frames files
            - It's passed to FFMpeg as options for the video-only output files
        - Leave _Marked FFmpeg Audio Output options_
            - Optionally, customize the FFmpeg audio output settings
            - The entered value is used when combining video clips with original WAV audio
            - It's passed to FFMpeg as options for the audio+video output files
    - If **Create Labeled Remix**
        - Enter the _Label Text_
        - Leave the remaining options set _as-is_
            - Optionally, customize the label settings:
            - Uncheck _Label at Top_ to place the label at the bottom
            - Set _Font File_ to a font file within the application's root folder
                - The font must be one supported by the installed version of FFmpeg
                - Font files outside of the appplication root folder are not supported
            - Set _Font Factor_ to the size of the label text
                - Smaller values produce larger text
                - Font size is computed as _image width_ / _font factor_
            - Set _Font Color_ to the color and opacity of the label text
                - Color can be specified in any format recognized by the FFmpeg _drawtext_ filter
                - Examples:
                    - `CornflowerBlue`
                    - `#32CD32`
                    - `random`
                - Opacity can optionally be set:
                    - `white@0.9`
                    - `0x9400D3@0x4f`
                    - `#FA8072AA`
            - Leave _Background_ checked to draw a box underneath the label text
            - Set _Border Factor_ to the size of the margin between the text and the background
                - Smaller values produce larger margins
                - Margin size is computed as _computed font size_ / _border factor_
            - Set _Border Color_ to the color and opacity of the label text
                - Color can be specified in any format recognized by the FFmpeg _drawtext_ filter
1. Click _Save Remix, Save Custom Remix_, _Save Marked Remix_ or _Save Labeled Remix_
    - The previously processed video and audio clips are merged
    - Note: The final video is concatenated from the clips without being re-encoding for the highest quality

## Important
- `ffmpeg.exe` must be available on the system path

## Custom Remix Examples
_Disclaimer: these are proofs of concept, but not necessarily great recommendations for quality videos!_

| Output Type | Custom Video Output | Custom Audio Output | Filename | Results |
| :- | :- | :- | :- | :- |
| MP4 | `-c:v libx264 -crf 32` | `-c:a aac` | video.mp4 | Options used for standard MP4 remix output |
| MPG | (left blank) | `-codec: a mp3` | video.mpg | Video with sound played great |
| MPEG-PS | `-c:v mpeg2video -pix_fmt yuv422p -bf 2 -b:v 10M -maxrate 10M -minrate 10M -s 640x480 -aspect 4:3` | `-c:a pcm_s16be -f vob` | video.vob | Video+sound played great (with VLC)* |
| WMV | (left blank) | (left blank) | video.wmv | Video+sound played but was very low quality** |
| AVI | (left blank) | (left blank) | video.avi | Video+sound played but was very low quality** |

_* The console showed many buffer underrun errors while concatenating into remix video_

_** Likely there are 'quality' command line switches that would fix this_

