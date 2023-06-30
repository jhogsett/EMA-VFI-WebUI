**Clean PNG Files** - Remove Interfering PNG Chunks

## Why It's Needed

* PNG files sometimes include optional _data chunks_ that can interfere with use in _Video Blender_ or video editing software
    * _Examples:_
    * Display color calibration data
    * Display aspect ratio data
* When using PNG from different workflows, non-matching frames can cause confusion
    * Frames to appear not to match when using _Frame Chooser_
    * Frames have different shapes when using sofware such as _Premiere Pro_
* PNG files are rewritten inluding only the essential RGB color data

## How It Works
1. Set _PNG files path_ to the path on this server containing the PNG files
1. Click _Clean_
1. Each PNG file will be rewritten excluding optional data
    - Tip: As a bonus, the PNG files usually have a smaller file size