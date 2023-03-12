**Video Blender Frame Fixer** - Fix bad frames in place

## How To Use

1. Set _Video Blender Project Path_ to a directory on this server containing the PNG frames files that need fixing
    - This is pre-filled with the current project path if the _Fix Frames_ button is used
1. Set _Last clean frame BEFORE damaged ones_ to the frame number of a clean frame befor the bad ones
    - This is pre-filled with the current frame number if the _Fix Frames_ button is used
1. Set _First clean frame AFTER damaged ones_ to the frame number of a clean frame after the bad ones
1. Click _Preview Fixed Frames_
1. A set of high-precision replacement frames are made using _Frame Search_
    - The search precision is set via the config setting `blender_settings.frame_fixer_depth`
1. An animated GIF is shown with the replacement frames
1. If the frames are acceptable, click _Apply Fixed Frames_
    - The replacement frames are copied over the project frames
    - The _Frame Chooser_ tab is displayed

## Important

- _Last clean frame BEFORE damaged ones_ MUST be the last clean frame before the set of damaged ones
- _First clean frame AFTER damaged ones_ MUST be the first clean frame after the set of damaged ones
- Frames may not be fixable if there's a scene change, motion is too fast, or the clean frames are too far apart
