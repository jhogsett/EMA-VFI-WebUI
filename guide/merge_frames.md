**Merge Frames** - Merge a previously split set of of PNG framess

## Uses
- Recombine groups after a large processing run
- Remerge files split for transport
- Undo a previous split

## How It Works
1. Set _Split Groups Base Path_ to a path on this server to the directory containing the previously split sub-directories
1. Set _PNG Files Path_ to a path on this server to store the merged files
    - _Tip: this can be the same path as_ Split Groups Base Path
1. Leave _Number of Split Groups_ set to `-1` for auto-detection of the number of groups
    - Set a specific value to require precisely that many group sub-directories to be present
1. Choose _Split Type_
    - **Precise** merges all files found in the sub-directories
    - **Resynthesis** merges the files found in the sub-directories, taking into account the extra frames aded for _Resynthesize Video_
    - **Inflation** merges the files found in the sub-directories, taking into account the extra frames aded for _Video Inflation_
1. Choose _Files Action_
    - **Combine** merges the files **post-processing**, taking into account the _Split Type_
    - **Revert** merges the files **prior to processing**, taking itno account the _Split Type_
    - _Tip: Use Revert to_ Undo _a previous unprocessed split_
1. Click _Split Frames_
    - Progress can be tracked in the console

## Split Type Details
- **Precise**
    - _Files Action_ is _Combine_:
        - Merges all files found in the group directories
        - Files retain their original filenames
    - _Files Action_ is _Revert_:
        - Same as _Combine_
- **Resynthesize**
    - _Files Action_ is _Combine:_
        - Merges the _resynthesized_ set of files found in the group directories
        - Renumbers the files according to their original frame index
    - _Files Action_ is _Revert:_
        - Merges the _non-resynthesized_ files found in the group directories
            - Excess files added for _Resynthesize Video_ are skipped
        - Renumbers the files according to their original frame index
- **Inflation**
    - _Files Action_ is _Combine:_
        - Merges the _inflated_ set of files found in the group directories
            - The _Video Inflation_ rate is detected from the file count
            - The files are renumbered taking into account the inflation rate
            - Shared _keyframes_ added for _Video Inflation_ are skipped
    - _Files Action_ is _Revert:_
        - Merges the _non-inflated_ set of files found in the group directories
            - Shared _keyframes_ added for _Video Inflation_ are skipped
        - Renumbers the files according to their original frame index

## Important

1. The _Split Type_ **must** match the type used to split the files originally
    - _Note: an error message will be shown in the console if the wrong split type is detected_
1. Ensure the only directories files present in the Split Groups Base Path are the ones to be merged
1. Files are taken in  Python `sorted()` order
