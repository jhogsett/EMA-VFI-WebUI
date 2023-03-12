**Video Blender Frame Chooser** - Step through a video, replacing bad frames

## Important
The green buttons copy files!
- Clicking copies a frame PNG file from the corresponding directory to the project path
- Undo by going back and choosing the other path
- The remaining buttons do not alter the project

## How To Use
- Click the _Next Frame >_ and _< Prev Frame_ buttons to step through the video one frame at a time
- Click the green _Use Path N Frame | Next >_ buttons to copy a frame from either path to the project path, then step to the next frame
- Input a _Frame Number_ and click _Go_, or press ENTER, to move to that frame
- Click the _100 >_ and _< 100_ buttons to move forward or back 100 frames
    - The skip count is set by the config setting `blender_settings.skip_frames`
- Click _Fix Frames_ to restore one or more bad frames in place
    - You wil be taken to the _Frame Fixer_ tab
    - The _Last clean frame BEFORE damaged ones_ box will be pre-filled with the current frame number
- Click _Preview Video_ to watch a preview video of the current project

## High-Speed Navigation
The _Frame Number_ box can be used to quickly navigate through frames
- **FAST**
    - Click to place the text caret
    - Press and Hold the **&uarr;** **&darr;** keyboard keys to navigate at the repeat rate
    - _Tip: Adjust your keyboard settings to set keyboard_ **repeat rate** _to the_ **max** _and_ **repeat delay** _to the_ **min**
- **FASTEST**
    - Use the embedded **&varr;** control buttons
    - Click and Hold the control buttons to navigate at the fastest possible rate
    - _Tip: Both buttons can be used while holding the mouse button_