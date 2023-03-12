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
1. Set _Starting Sequence Number_ or accept the default of 0
    - A different value might be useful if inserting a PNG sequence into another
1. Set _Integer Step_ or accept the default the default of 1
    - This sets the increment between the added frame index numbers
1. Set _Number Padding_ or accept the default of -1
    - This set the width of the added frame index numbers
    - If set to -1, the width is determined based on the number of files
1. Leave _Rename instead of duplicate files_ unchecked to keep a copy of the original files
    - The original files can be handy for tracking down a source frame
1. Click _Resequence Files_

## Important
1. Ensure the only files present in the input path are the ones to be resequenced
