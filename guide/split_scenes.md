**Split Scenes** - Split PNG frames by scene changes or breaks

## Uses
- Split a long video for processing by individual scenes
- Detect and remove commercial content
- Use _Resynthesize Video_ avoiding interpolations across scene changes

## How It Works
1. Set _PNG Files Path_ to a path on this server to the PNG files to be split
1. Set _Scenes Base Path_ to a path on this server to store the new sub-directories
    - _Tip: this can be the same path as_ PNG files Path
1. Choose whether to _Split by Scene_ or _Split by Break_
    - **Split by Scene**
        - separates frames into groups based on detected scene changes
    - **Split by Break**
        - separates frames into groups based on detected breaks (fades to black)
1. If splitting by **_Scene_**:
    - Choose a _Detection Threshold_
        - A _higher_ value detects _fewer_ scene changes
        - The best value will require experimentation
1. If splitting by **_Break_**:
    - Choose a _Minimum Duration_ in _seconds_
        - Breaks of at least this duration will be detected
    - Choose a _Black Frame Ratio_
        - Frames with at least this ratio of _black_ vs. _non-black_ pixels will be detected as break frames
1. Click _Split Scenes_ or _Split Breaks_
    - Progress can be tracked in the console

## Notes
1. The _Merge Frames_ feature can be used to recombine frames that were split by scene or break
    - Use the Split Type _Precise_ and the Files Action _Combine_
1. Ensure the only files present in the PNG Files Path are the ones to be split
1. Files are taken in  Python `sorted()` order
