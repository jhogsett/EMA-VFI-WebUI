**Resequence Files** - Renumber PNG files with a fixed-width frame index

## Uses
- Prepare a PNG sequence for import into video editing software
- Rearrange a set of files for insertion into another set
- Split a set of deinterlaced frames into _Even_ and _Odd_ sets

## How It Works
1. Set _File Type_ to `png` or any other file extension
    - This used to locate the original set of files, and name the new files
    - **_A wildcard such as_** `*` **_will not work here_**
1. Set _Base Filename_ or accept the default
    - This is used ahead of the file index number for new renumbered filenames
    - **⚠️ Important: use a name other than the current name of the files**
1. Leave _Rename files in place_ checked to copy the renumbered files to the output path
    - Check to rename the original files in the input path instead of copying
1. Set _Starting File Number_ or accept the default of `0`
    - A different value might be useful if inserting a PNG sequence into another
1. Set _File Number Step_ or accept the default the default of `1`
    - This sets the increment between the added file index numbers
1. Leave _File Number Padding_ blank to automatically detect the padding width
    - If needed, set a specific padding width
    - _Tip: It is necessary for proper sorting that all files have the same padding
1. Leave _Samping Stride_ set to `1` and _Sampling Offset_ set to `0`
    - These are used for special purposes, for example:
        - To select only **_even_** frames:
            - set _Sampling Stride_ to `2` and set _Sampling Offset_ to `0`
        - To select only **_odd_** frames:
            - set _Sampling Stride_ to `2` and set _Sampling Offset_ to `1`
        - _Tip: selecting_ even _or_ odd _frames might be useful when dealing with deinterlaced content_
1. Leave _Reverse Sampling_ unchecked
    - Check if the files/batch file groups should be sampled in reverse order
1. Choose _Individual Path_ or _Batch Processing_
    - If **Individual Path**
        - Set _Input Path_ to a path on this server to the PNG files being resequenced
    - If **Batch Processing**
        - Set _Input Path_ to a directory on this server containing PNG frame groups to be resequenced
        - Check _Use contiguous frame indexes across groups_ to use a single increasing frame index across all groups
1. Click _Resequence Files_ or _Resequence Batch_
- Progress can be checked in the console

## ⚠️ Important
1.  **Make a backup copy of the original files before using _Rename instead of duplicate files_ due to the danger of losing the original content**
1. Ensure _Base Filename_ is set to a different name than the source files
1. Ensure the only files present in the input path are the ones to be resequenced
1. Files are taken in  Python `sorted()` order
