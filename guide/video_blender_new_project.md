**Video Blender New Project** - Automated set up of a new Video Blender project

## How To Use

1. Set _New Project Name_ to a unique name for the project
1. Set _New Project Path_ to a directory to contain the project files
1. Set _Frame Rate_ to the frame rate of the video being restored
1. Ensure _Split MP4 to PNG Frames Set_ is **checked**
1. Set _MP4 Path_ to a path on this server to the MP4 file
    - This step creates a set of _source frames_ from the source video
    - _Tip: other file types will work such as:_ `.mpg`, `.mov`, _and_ `.wmv`
1. Ensure _Resynthesize Repair Frames Set_ is **checked**
    - This step creates an interpolated set of _repair frames_ that can be used for restoring damaged frames
1. Ensure _Init Restored Set from Source_ is **checked**
    - This step creates a set of _working frames_ that are modified by _Frame Chooser_ and _Frame Fixer_
    - These frames become the final restored video
1. Ensure _Sync Frame Numbers Across Sets_ is **checked**
    - This step ensures that frame numbers shown in the _Frame Chooser_ UI match the frame indexes of the source PNG frame files on disk
    - Also the _Clean PNG Files_ feature is used to simplify the PNG frame files
1. Click _Create New Project_
1. When done, return to the _Project Settings_ tab to open the new project

## Note
- This process could be slow, perhaps many hours long!
- Progress is shown in the console using standard progress bars
- The browser window does NOT need to be left open

## Important
- `ffmpeg.exe` must be available on the system path
