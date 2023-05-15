**Simplify PNG Files** - Remove Optional PNG Chunks

## Why It's Needed

* PNG files sometimes include optional color calibration data used by modern browsers to enhance the colors on the display device.
* When mixing and matching PNG files with and without the optional data, images can appear to not match when using _Video Blender_
* PNG files are rewritten inluding only the original RGB color data

## How It Works
1. Set _PNG files path_ to the path on this server containing the PNG files
1. Click _Clean_
1. Each PNG file will be rewritten excluding optional data
