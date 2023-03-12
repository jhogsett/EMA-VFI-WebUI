**Frame Search** - Use AI to interpolate _between_ frames at precise times

## Uses
* Create a _between frame_ at a precise time between two frames
* Recreate a frame that can't easily be created with _Frame Interpolation_
    - See _Frame Restoration_ for automatic recreation of adjacent frames

## How It Works
1. Drag and drop, or click to upload _Before Frame_ and _After Frame_ PNG files
1. Choose a _Lower Bound_ and _Upper Bound_ for the search
    - The values must be between 0.0 and 1.0
1. Set _Search Precision_ per the desired timing accuracy
    - Low is faster but can lead to a poorly-timed frame
    - High produces near-perfect results but takes longer
1. Click _Search_
1. The _Found Frame_ panel will show the new frame
1. The _Download_ box gives access to
    - The found frame PNG file

## Understanding Frame Search
Frame Search _finds_ frames at precise times through a binary search process
- A series of time divisions are made, splitting the remaining time toward the search target
- A new interpolated _work frame_ is created each time
- The last work frame is returned when the search target is found, of if the search depth is reached

**Example** Shallow Search for 2/3:
- Search precision is 3, search range is 0.666666666 to 0.666666668
    - Split #1 creates a work frame at 0.5
    - Split #2 creates a work frame at 0.75
    - Split #3 creates a work frame at 0.625
- The frame produced at 0.625 is returned as the closest match

**Example** High Precision Search for 2/3:
- Search Precision is 10, search range is 0.666666666 to 0.666666668
    - Work frames are created at:
    - 0.5, 0.75, 0.625, 0.6875, 0.65625, 0.671875, 0.6640625, 0.66796875, 0.666015625 and 0.6669921875
- The frame produced at 0.6669921875 is returned as the closest match

**Example** Deep Search for 2/3:
- Search Precision is 60, search range is 0.66666666666666666666 to 0.66666666666666666668
- The frame produced at 0.66666666666666662965923251249478198587894439697265625 is returned
