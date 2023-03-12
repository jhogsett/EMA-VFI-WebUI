**Frame Restoration** - Use _Frame Search_ to recreate adjacent damaged frames

## Uses

- Recreate several adjacent _damaged_ or _missing_ frames

## How it works

1. Drag and drop, or click to upload _Frame Before Replacement Frames_ and _Frame After Replacement Frames_ PNG files
1. Set _Frames to Restore_ to the exact number of needed replacement frames for accurate timing
    - _Frame Search Times_ shows the fractional search times for the recreated frames
1. Set _Search Precision_ per the desired timing accuracy
    - Low is faster but can lead to repeated or poorly-timed frames
    - High produces near-perfect results but takes a long time
    - _Frame Search Times_ shows a warning if Search Precision is set too low
1. _Predicted Matches_ shows estimates for the frame times based on _Frames to Restore_ and _Search Precision_
    - Actual found frames may differ from predictions
1. Click _Restore Frames_
1. The _Animated Preview_ panel will show a GIF of the original and restored frames
1. The _Download_ box gives access to
    - Animated GIF
    - ZIP of restored frames
    - TXT report

## Important

- Provide only CLEAN frames adjacent to the damaged ones

## Understanding Frame Restoration

**Example:** _Recreating 2 Missing Frames:_
- B is the last good frame _before_, and A is the first good frame _after_ the missing frames
    - `B---?---?---A`
- Replacement frame X is 1/3 of the way between frames A and D
    - `B---X-------A`
- Replacement frame Y is 2/3 of the way between frames A and D
    - `B-------Y---A`
- _Frame Search_ divides down to _precisely_ timed frames
    - In this case, reaching _precisely_ 1/3 and 2/3 is not possible
    - _Search Precision_ is used to trade off time for the accuracy

