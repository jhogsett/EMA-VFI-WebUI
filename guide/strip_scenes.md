**Strip Scenes** - Easily remove unwanted scenes from a video

⚠️ Warning! This feature can permanently delete large numbers of files!

## Used For
- Stripping unwanted scenes from a video
- Works in conjunction with the _Split Scenes_ and _Slice Video_ features

## How To Create _Markers_ and _Mark Content_
1. Use the _Split Scenes_ feature to split a video by _scene_ or by _break_
1. Use the _Slice Video_ feature to create summary content for each scene
    - Any of the summary types will work as _marker_ files:
        - JPG thumbnails _(recommended)_
        - MP4, GIF clips
        - WAV, MP3 audio files
1. Use an external tool to review the summary content
1. To **mark** a scene:
    - Place a copy of the desired summary content in the **Frames Group Path**
    - _Notes:_
        - This can be to either to mark for **keeping** or mark for **deletion**
        - The files must retain the `[first-last]` frame group notation in the filename
        - The named frame group must exist

## How It Works
1. Set _Frame Groups Path_ to a path on this server containing the Scene directories
    - This should be a path that has had _marker_ files placed
1. Choose whether to _Keep Marked Content_ or _Delete Marked Content_
    - **Keep Marked Content** is useful when most scenes should be deleted
    - **Delete Marked Content** is useful when most scenes should be kept
1. Click _Strip Scenes_
- Progress can be tracked in the console

## Notes
1. Ensure the only files present in the Frame Groups path are the marker files
1. Directories and files are taken in  Python `sorted()` order
