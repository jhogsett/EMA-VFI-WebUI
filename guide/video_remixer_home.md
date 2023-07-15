**Video Remixer Home** - Create or Load a Video Remixer Project

## Create a project
1. Set _Video Path_ to the path on this server to a video to remix
    - _Tip: This can be a format FFmpeg understands such as MP4, MPG, MOV, WMV, AVI etc._
1. Click _New Project_
1. The video will have its properties inspected
1. You will be taken to the _Remix Settings_ tab

## Open a project
1. Set _Project Path_ to the path on this server to a _Video Remixer_ project
    - This can be the path to the project directory or its `project.yaml` file
1. Click _Open Project_
1. You will be taken to your last saved activity

## Notes
- The video propery inspection process can be lengthy!
    - Videos without frame count metadata require scanning the whole file to count
- Progress is shown in the console using standard progress bars
- The browser window does NOT need to be left open
    - The project can be opened later and resumed where you left off

## Important
- `ffmpeg.exe` must be available on the system path
