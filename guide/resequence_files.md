**Resequence Files** - Renumber PNG files with a fixed-width frame index

## Uses
- Prepare a PNG sequence for import into video editing software
- Rearrange a set of PNG frames for insertion into another set

## How It Works
1. Set _Input Path_ to a path on this server to the PNG files being resequenced
1. Set _File Type_ to `png` or another necessary value
    - This used to locate the original set of files, and name the new files
    - A wildcard such as `*` will not work here
1. Set _Base Filename_ or accept the default
    - This is used ahead of the frame index number for new filenames
    - **⚠️ Important: use a name other than the current name of the files**
1. Set _Starting Frame Number_ or accept the default of `0`
    - A different value might be useful if inserting a PNG sequence into another
1. Set _Frame Number Step_ or accept the default the default of `1`
    - This sets the increment between the added frame index numbers
1. Set _Frame Number Padding_ or accept the default of `-1`
    - This set the width of the added frame index numbers
    - If set to `-1`, the width is determined based on the number of files
1. Leave _Samping Stride_ set to `1` and _Sampling Offset_ set to `0`
    - These are used for special purposes, for example:
        - To select only _even_ frames:
            - set _Sampling Stride_ to `2`
        - To select only _odd_ frames:
            - set _Sampling Stride_ to `2`
            - set _Sampling Offset_ to `1`
        - _Tip: selecting_ even _or_ odd _frames can be useful if using de-interlaced content_
1. Leave _Rename instead of duplicate files_ unchecked to keep a copy of the original files
    - The original files can be handy for tracking down a source frame
1. Click _Resequence Files_

## ⚠️ Important
1.  **Make a backup copy of the original files before using _Rename instead of duplicate files_ due to the danger of losing the original content**
1. Ensure _Base Filename_ is set to a different name than the source files
1. Ensure the only files present in the input path are the ones to be resequenced
1. Files are taken in  Python `sorted()` order
