**Slice Video** - Summarize a group of scenes info various formats

## Uses
- create small .MP4 preview videos for each scene
- extract .WAV files for reassembling a video with sound
- create animated .GIF thumbnails for each scene
- extract scene audio to .MP3 files for listening later
- make .JPG thumbnails representing each scene

## How It Works
1. Set _Input Media Path_ to a path on this server to the video file to be sliced
    - _Tip: Other media formats such as .MOV, .WMV and .M4A should work also_
1. Adjust _Input Media Frame Rate_ to the frame rate of the video to be sliced
    - **Note:** The frame rate must be set precisely for accurate frame-based slicing
    - _Tip: The_ Video Details _feature can be used to determine the exact frame rate of a media file_
1. Set _Split Groups Path_ to a path on this server containing the scene directories
    - Sub-directories previously created using either the _Split Frames_ or _Split Scenes_ features
1. Set _Output Path_ to the path on this server to store the new sliced files
    - Leave blank to store the sliced files within the original scene directories
1. Adjust _Output Scale Factor_ as necessary
    - _Tip: Sliced files can grow large - a small size is recommended_
1. Choose a _Slice Type_
    - _See below for a table of Slice Types and descriptions_
1. Choose a _MP4 Quality_
    - A lower value means a higher quality video
    - _This applies only when the_ `mp4` _slice type is used_
1. Choose an _Output GIF Frame Rate_
    - A higher value means a higher quality GIF and a large file size
    - _This applies only when the_ `gif` _slice type is used_
1. Click _Slice Video_
    - Progress can be tracked in the console

| Slice Types | Description | Details |
|:-|:-|:-|
| **mp4** | create a .MP4 video with sound for each scene | The _Output Scale Factor_ sets the size of the video relative to the source |
| **gif** | create an animated .GIF for each scene | The _Output GIF Frame Rate_ sets the frame rate of the .GIF when viewed. Infinite looping is enabled. |
| **wav** | create .WAV audio files for each scene | This is recommended if reassembling a video with audio |
| **mp3** | create .MP3 audio files for each scene | This is recommend for listening purposes |
| **jpg** | create .JPG thumbnail images from the middle frame of each scene | The _Output Scale Factor_ sets the size of the thumbnail relative to the source |

## Notes
1. Animated .GIF files can be very large
1. The _Split Frames_ and _Split Scenes_ features can be used to create split groups/scenes
    - _Tip: use the_ `precise` _split type, since accurate frame indexes are required_
