**Split Frames** - Split a large set of PNG frames into sub-directories

## Uses
- Break up a large processing job into manageable chunks
- Transport a large sets of files faster with less file overhead
- Split raw content for easier preselection review

## How It Works
1. Set _PNG Files Path_ to a path on this server to the PNG files to be split
1. Set _Split Groups Base Path_ to a path on this server to store the new sub-directories
    - _Tip: this can be the same path as_ PNG files Path
1. Set _Number of Split Groups_ to the desired number of new sub-directories
1. Leave _Maximum Files Per Group_ set to `0`
    - If needed, set to a value to have the split group count computed automatically
    - _Tip: set to `1800` to split a 30 FPS video into 1-minute groups_
1. Choose _Split Type_
    - **Precise** splits files among the new sub-directories without duplicates
    - **Resynthesis** creates groups of files that can be processed independently using _Resynthesize Video_ and then recombined
    - **Inflation** creates groups of files that can be processed independently using _Video Inflation_ and then recombined
    - _Tip: The_ Merge Frames _feature can be used to recombine files split using_ Split Frames
1. Choose _Files Action_
    - **Copy** copies the files to the new sub-directories
    - **Move** copies the files and then deletes the original files on success
1. Click _Split Frames_
    - Progress can be tracked in the console

## Split Type Details
- **Precise**
    - Copies the only the files needed to split up the original files, without adding any additional files
        - Useful in cases where processing won't increase or decrease the frame count
    - Files retain their original filenames
- **Resynthesize**
    - Copies files necessary to use _Resynthesize Video_ separately on each group and then recombine with the other groups after processing
        - For each group, the _beginning_ and _ending_ frames from neighboring groups are borrowed to support resynthesis
        - The excess frames are removed during the resynthesis process, requiring no special handling to recombine the processed files
    - Each group of files is renumbered to have a starting frame #0
- **Inflation**
    - Copies files necessary to use _Video Inflation_ separately on each group and then recombine the results for all groups
        - Each group shares common _keyframes_ with its neighboring groups to support the inflation process
        - The shared _keyframes_ are kept after the inflation process, and duplicates are automatically removed when recombining using _Merge Frames_
    - Each group of files is renumbered to have a starting frame #0

## ⚠️ Important
1.  **Make a backup copy of the original files before using _Move_ due to the danger of losing the original content**
1. The _Merge Frames_ feature can be used to undo the a split or combine groups after processing
1. Ensure the only files present in the PNG Files Path are the ones to be split
1. Files are taken in  Python `sorted()` order
