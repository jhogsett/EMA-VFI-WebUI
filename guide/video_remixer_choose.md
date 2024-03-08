**Video Remixer Scene Chooser** - Step through scenes choosing which to keep

## Main Action Buttons (Green)
_Keep Scene | Next_ and _Drop Scene | Next_
- Set the _Next_ or _Drop_ Status, then
- **Save the project**, then
- Advance to the next scene

## Action Radio Buttons
- Set the _Next_ or _Drop_ Status, then
- **Save the project**

## When Done Choosing Scenes
Click the _Done Choosing Scenes_ button when all _Keep_ or _Drop_ selections have been made
- This will save your choices and take you to the _Compile Scenes_ tab

## Scene Navigation Buttons (Orange)
_Prev Scene_ and _Next Scene_
- Go to the previous or next scene

## Other Navigation Buttons
_Prev Keep_ and _Next Keep_
- Go to the previous or next scene marked **_Keep_**

_First Scene_ and _Last Scene_
- Go to the first or last scene in the project

## Shortcut Buttons (Purple)
_Split Scene_
- Opens the _Scene Splitter_ tab to scrub through a scene and optionally split it

_Choose Scene Range_
- Opens the _Choose Scene Range_ tab to set a series of scenes to _Keep_ or _Drop_

## Properties Accordion
_Scene Label_
- Enter a scene label and press _Enter_ or click _Set_ to save it with the scene
- _Tip:_ Use the < and > buttons to navigate to labeled scenes

### About Scene Labels
- Labels can be used to add a scene title
  - The entered scene title will appear in the video when using the _Labeled Remix_ feature
  - The entered title will also be used as the basis for the scene remix clip, making it easier to find and reuse individual scene clips
- Labels can be used to rearrange scene order in the remix video
  - When a label starts with a value inside parentheses, the value will be used to arrange the clips in sorted order
  - _Tip:_ use the _+ Sort Keys_ button to automatically add a sorting mark to each scene
- Labels can be used to add _Processing Hints_
  - Use the _+ 2X Slo Mo_, _+ 4X Slo Mo_ or _+ 8X Slo Mo_ buttons to add a _Processing Hint_ to the scene label that adds audio pitch-adjusted slow motion

_Tip: See below for more details on_ Processing Hints

_+ Sort Keys_
- Automatically adds a sorting mark to each scene

_+ Title_
- Automatically adds a default title to each scene

_Reset_
- Clears the contents of all scene labels

_+ 2X Slo Mo_, _+ 4X Slo Mo_ and _+ 8X Slo Mo_
- Add a _processing hint_ to the scene label to enable 2X, 4X or 8X audio slow motion with pitch adjustment processing

The _Keep All Scenes_ and _Drop All Scenes_ buttons (inside the _Danger Zone_ accordion)
- **Destructively** _Keep_ or _Drop_ all scenes (there is no undo)
- Save the project

The _Split Scene_ and _Drop Processed Scene_ buttons (inside the _Danger Zone_ accordion)
- Shortcuts that take you to the corresponding _Remix Extra_ tabs with pre-filled scene IDs

## Danger Zone Accordion

_Keep All Scenes_ and _Drop All Scenes_
- Sets **_all_** scenes to _Keep_ or _Drop_

_Invert Scene Choices_
- Changes all scene keep/drop statues to the opposite state
- _Tips:_
  - Use this feature, then use the _Next Keep_ button to navigate through all dropped scenes
  - Use this feature, then create a _Marked_ remix video, to watch and check or accidentally left out footage

_Drop Processed Scene_
- Opens the _Drop Processed Scenes_ tab to drop a scene, including its processed content, to save the remix video without that the dropped scene, avoiding reprocessing the whole video

_Mark Scene_
- Remembers the current scene ID to make it easier to use features that require entering a scene ID range
- This can be used with the _Merge Scene Range_ and _Choose Scene Range_ features
  1. Go to the first scene of the range and click _Mark Scene_
  1. Go to the last scene of the range, then click either of these shortcut buttons
    - Merge Scenes
    - Choose Scene Range

_Merge Scenes_
- Shortcut that takes you to the Remix Extra _Merge Scenes_ tab

## Processing Hints

Resize:
- `{R:x/y}` zoom into quadrant `x` of `y` sized grid
  - Example:
  - `{R:1/4}` zoom into upper left quadrant of 2x2 grid
  - `{R:5/9}` zoom into center quadrant of 3x3 grid (like a telephone keypad)
- `{R:z%}` zoom in the center at `z` percent
  - Example:
  - `{R:200%}` zoom in at 200%

Resynthesize:
- `{Y:type}` enable resynthesis of `type`
  - Types:
  - `C` clean (first past only of two pass resynth)
  - `S` scrub (two pass resynth)
  - `R` replace (one pass resynth)
  - `N` no resynthesis

Inflation:
- `{I:nt}` inflate amount `n` with type `y`
  - Amounts: `1`, `2`, `4`, `8`, `16`
    - `1` means don't inflate
  - Types:
  - `A` slow motion with audio pitch adjust
  - `S` slow motion with silent audio
  - `N` no slow motion (can be omitted)

Upscale:
- `{U:_}` upscale at 1X for clean-up
  - `_` reserved for future use

## Important
- `ffmpeg.exe` must be available on the system path
