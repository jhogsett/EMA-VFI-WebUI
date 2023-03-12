**Video Blender** - Easy-to-use Movie Restoration Interface

## Uses
- Restore a movie, replacing damaged frames with resynthesized replacements
- Fix defective or missing frames in-place
- See a preview video of a restoration in progress

## Project Setup
- Set up a project with three directories, all with PNG files (only) with the same _file count, dimensions_ and _starting sequence number_
- In the _Original / Video #1 Frames Path_ place the _original PNG files_ from the video being restored
- In the _Project Frames Path_, start with a copy of the  _original PNG files_ as a baseline set of movie frames
    - Files in this path will be overwritten during the restoration process
- In the _Alternate / Video #2 Frames Path_ place a set of _replacement PNG files_ to use for restoring frames
    - Replacement frames can be created using _Resynthesize Video_

## Important
- All paths must have _corresponding filenames, sequence numbers and PNG dimensions_!
    - If _Resynthesize Video_ was used to create a set of replacement frames, there will not be a frame #0 file
        - Copy the frame #0 file from the original video path to the restoration video path to ensure frame synchronization among the three frame sets
    - _Resequence Files_ can be used to rename a set of PNG files
- For _Video Preview_ to work properly:
    - The files in each directory must have the **same base filename and numbering sequence**
    - `ffmpeg.exe` must be available on the _system path_

## Project Management
- To save a settings for a project:
    - After filling out all project fields, click _Save_
    - A new row will be added to the projects file `./video_blender_projects.csv`
    - To see the new project in the dropdown list:
    - Restart the application via the Tools page, or from the console
- To load settings for a project
    - Choose a project by name from the_Saved Project Settings_ DropDown
    - Click _Load_
    - Click _Open Video Blender Project_ to load the project and go to _Frame Chooser_

## General Use
- This tool can also be used to selectively mix frames from up to three movies
- _Video Preview_ can be used to watch a preview video for a set of PNG files
