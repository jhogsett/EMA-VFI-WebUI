**Resynthesize Video** - Use _Frame Interpolation_ to synthesize replacement frames for an entire movie

## Uses

- Create a set of replacement frames for use in movie restoration
- _Video Blender_ can be used to selectively replace frames from a restoration set

## How It Works
1. Set _Input Path_ to a directory on this server to the PNG files to be resynthesized
1. Set _Output Path_ to a directory on this server for the resynthesized PNG files
    - Output Path can be left blank to use the default folder
    - The default folder is set by the `config.directories.output_resynthesis` setting
1. Click _Resynthesize Video_
1. _Frame Interpolation_ is done using frames adjacent to each frame to interpolate replacements
    - The first and last frame cannot be replaced
1. When complete, the output path will contain a new set of frames

## How To Use Replacement Frames
1. Replacement frames can be used with _Video Blender_ to restore a movie
    1. The original and restoration frames are provided

## Important
- This process could be slow, perhaps many hours long!
- Progress is shown in the console using a standard progress bar
- The browser window does NOT need to be left open
- When using a restoration frame set with _Video Blender_ it's important to remove frame #0 from the original set of frames
    - It's not possible to create a replacement for the first and last frames of the original video
    - To keep the sets of PNG files synchronized while restoring a film, make sure original frame #0 is not present

## Why this works
- A video may have a single damaged frame between two clean ones
- Examples: a bad splice, a video glitch, a double-exposed frame due to frame rate mismatch, etc.
- AI excels at detecting motion in all parts of a scene, and will very accurately create a new clean replacement frame

## Sometimes it doesn't work
- Replacement frames cannot be resynthesized without two CLEAN adjacent original frames
    - _Frame Restoration_ can be used to recover an arbitrary number of adjacent damaged frames
- Transitions between scenes will not produce usable resynthesized frames
