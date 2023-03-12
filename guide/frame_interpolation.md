**Frame Interpolation** - Use AI to create one or more evenly-spaced _between frames_

## Uses

- Recreate a _damaged_ or _missing_ frame
- Reveal _hidden motion_ between frames

## How it works

1. Drag and drop, or click to upload _Before Frame_ and _After Frame_ PNG files
1. Set _Split Count_ to choose the number of new _Between Frames_
    - Each _split_ doubles the frame count
1. Click _Interpolate_
1. The _Animated Preview_ panel will show a GIF of the original and newly created frames
1. The _Download_ box gives access to
    - Animated GIF
    - ZIP of original and interpolated frames
    - TXT report

## Understanding Frame Interpolation

**Example:** _1 Split Creates 1 New Frame:_
- B is the _Before_ frame, A is the _After_ frame
    - `B-------A`
- X is the new frame, splitting the time between B and A @ 50%
    - `B---X---A`

**Example:** _3 Splits Create 7 New Frames:_
- B is the _Before_ frame, A is the _After_ frame
    - `B-------------------------------A`
- X is the frame for the first split, dividing the time between B & A @ 50%
    - `B---------------X---------------A`
- Y & Y are the frames for the second split, dividing the times between B & X and X & A @ 25% and 75%
    - `B-------Y-------X-------Y-------A`
- Z, Z, Z & Z are the frames for the third split, dividing the times between B & Y, Y & X, X & Y, Y & A @ 12.5%, 37.5%, 62.5% and 87.5%
    - `B---Z---Y---Z---X---Z---Y---Z---A`

The number of interpolated frames is computed by this formula:
- F=2**S-1, where
- F is the count of interpolated frames
- S is the split count

Tip: It can help to think of time _intervals_ instead of _frames_
- At first there's 1 time interval between the _before_ and _after_ frames
- The first split divides time into 2 intervals, creating 1 interpolated frame
- A second split divides those into 4 intervals, creating 2 interpolated frames
- A third split divides those into 8 intervals, creating 4 interpolated frames
- The resulting 8 intervals minus the original one equals 7 new intervals / frames
