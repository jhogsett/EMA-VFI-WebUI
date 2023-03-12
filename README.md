<!-- [![Pylint](https://github.com/jhogsett/VFIformer-WebUI/actions/workflows/pylint.yml/badge.svg)](https://github.com/jhogsett/VFIformer-WebUI/actions/workflows/pylint.yml) -->
![pybadge](https://img.shields.io/badge/Python-3.10.9-4380b0)
![ptbadge](https://img.shields.io/badge/Torch-1.13.1-ee4b28)
![nvbadge](https://img.shields.io/badge/Cuda-11.7-76b900)

# EMA-VFI-WebUI - AI-Based Movie Restoration


<!-- ![Screenshot 2023-03-06 154321](https://user-images.githubusercontent.com/825994/223291544-8f75dcc2-a14e-4d46-8d44-c40c4c2abe4b.png)

| Example - Interpolated Frames |
|:--:|
| ![example](https://user-images.githubusercontent.com/825994/217553208-8b482d9a-4567-4af4-918d-a5938f709215.gif) |

| Example - Video Inflation (YouTube) |
|:--:|
| [Demo of 32X Video Inflation with marked original frames](https://youtu.be/rOiALIN805w) |

| Example - GIF to MP4 (frame size X2, frame rate X4) | Example - Original GIF |
|:--:|:--:|
| https://user-images.githubusercontent.com/825994/220932548-d40b54b5-811b-4637-8adc-6bf26fdcc52b.mp4 | ![http_t0 tagstat com_image03_0_21c475648484948484881505552](https://user-images.githubusercontent.com/825994/220933026-3fe6bf25-8be7-490e-a90b-85a151e6b156.gif) |-->

| 📽️ EMA-VFI-WebUI Features | &nbsp; |
|:--|:--|
| **➗ [Frame Interpolation](https://github.com/jhogsett/VFIformer-WebUI/wiki/Frame-Interpolation)** | _Restore Missing Frames, Reveal Hidden Motion_ |
| **🔎 [Frame Search](https://github.com/jhogsett/VFIformer-WebUI/wiki/Frame-Search)** | _Synthesize_ Between _Frames At Precise Times_ |
| **🎈 [Video Inflation](https://github.com/jhogsett/VFIformer-WebUI/wiki/Video-Inflation)** | _Create Super Slow-Motion_ |
| **💕 [Resynthesize Video](https://github.com/jhogsett/VFIformer-WebUI/wiki/Resynthesize-Video)** | _Create a Complete Set of Replacement Frames_ |
| **🪄 [Frame Restoration](https://github.com/jhogsett/VFIformer-WebUI/wiki/Frame-Restoration)** | _Restore Adjacent Missing / Damaged Frames_ |
| **🔬 [Video Blender](https://github.com/jhogsett/VFIformer-WebUI/wiki/Video-Blender)** | _Project-Based Movie Restoration_ |
| **📁 [File Conversion](https://github.com/jhogsett/VFIformer-WebUI/wiki/Tools)** | _Convert between PNG Sequences and Videos_ |
| **🔢 [Resequence Files](https://github.com/jhogsett/VFIformer-WebUI/wiki/Resequence-Files)** | _Renumber for Import into Video Editing Software_ |
| **🎞️ [Change FPS](https://github.com/jhogsett/VFIformer-WebUI/wiki/Change-FPS)** | _Convert any FPS to any other FPS_ |
| **💎 [GIF to MP4](https://github.com/jhogsett/VFIformer-WebUI/wiki/GIF-to-MP4)** | _Convert Animated GIF to MP4 in one click_ |
| **📈 [Upscale Frames](https://github.com/jhogsett/VFIformer-WebUI/wiki/Upscale-Frames)** | _Use_ Real-ESRGAN _to Enlarge and Clean Frames_ |

# Set Up For Use

1. Get EMA-VFI working on your local system
- See their repo at [https://github.com/MCG-NJU/EMA-VFI](https://github.com/MCG-NJU/EMA-VFI)
- I run locally with:
  - Anaconda 23.1.0
  - Python 3.10.9
  - Torch 1.13.1
  - Cuda 11.7
  - NVIDIA RTX 3090
  - Windows 11
2. Clone this repo in a separate directory and copy all directories/files on top of your *working* EMA-VFI installation
- This code makes no changes to their original code (but borrows some) and causes no conflicts with it
- It shouldn't introduce any additional requirements over what EMA-VFI, Gradio-App and Real-ESRGAN need
3. If it's set up properly, the following command should write a new file `images/image1.png` using default settings

`python interpolate.py`

# Alternate Set Up / Development

1. Get EMA-VFI working on your local system
- See their repo at [https://github.com/MCG-NJU/EMA-VFI](https://github.com/MCG-NJU/EMA-VFI)
- I run locally with:
  - Anaconda 23.1.0
  - Python 3.10.9
  - Torch 1.13.1
  - Cuda 11.7
  - NVIDIA RTX 3090
  - Windows 11
2. Clone this repo to a directory in which you intend to use the app and/or develop on it
3. Copy the following directories and files from your *working* EMA-VFI installation to this directory:
- `benchmark`
- `ckpt`
- `model`
- `config.py`
- `dataset.py`
- `Trainer.py`
4. If it's set up properly, the following command should write a new file `images/image1.png`

`python interpolate.py`

# Real-ESRGAN Add-On Set Up

The _GIF to MP4_ feature uses _Real-ESRGAN_ to clean and upscale frames

1. Get _Real-ESRGAN_ working on your local system
- See their repo at [https://github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
2. Clone their repo to its own directory and follow their instructions for local setup
3. Copy the `realesrgan` directory to your `EMA-VFI-WebUI` directory
* The _Real-ESRGAN 4x+_ model (65MB) will automatically download on first use

# FFmpeg Set Up

A few features rely on FFmpeg being available on the system path

[Download FFmpeg](https://ffmpeg.org/download.html)

# Starting Web UI Application

The application can be started in any of these ways:
- `webui.bat`
- `python webui.py`
  - _Command line arguments_
    - `--config_path path` path to alternate configuration file, default `config.yaml`
    - `--verbose` enables verbose output to the console, default False

# Using Web UI

[Wiki - Quick Start Guide](https://github.com/jhogsett/VFIformer-WebUI/wiki/Quick-Start-Guide)

## All Features

[Wiki - Home](https://github.com/jhogsett/VFIformer-WebUI/wiki)

# Command Line Tools

The core feature have command-line equivalents

[Wiki - Command Line Tools](https://github.com/jhogsett/VFIformer-WebUI/wiki/Command-Line-Tools)

# App Configuration

[Wiki - App Configuration](https://github.com/jhogsett/VFIformer-WebUI/wiki/App-Configuration)

# Future Ideas

- add Audio tools

<!--# My Public Uses of VFIformer

YouTube
- Feb 01 2023 "Fun with AI: De-Ticking a Ticking Clock" https://youtu.be/JhibFQvP7X0
- Jan 28 2023 "Fun with AI: Infinite Slow Motion" https://youtu.be/sKQKuYU-fcQ
- Jan 24 2023 "Fun with AI: Me as a Baby, Restoring 60 year old 8mm film" https://youtu.be/PiLv5u1PYiE
-->

# Acknowledgements

Thanks! to the EMA-VFI folks for their amazing AI frame interpolation tool
- https://github.com/MCG-NJU/EMA-VFI

Thans! to the Real-ESRGAN folks for their wonderful frame restoration/upscaling tool
- https://github.com/xinntao/Real-ESRGAN

Thanks! to the stable-diffusion-webui folks for their great UI, amazing tool, and for inspiring me to learn Gradio
- https://github.com/AUTOMATIC1111/stable-diffusion-webui

Thanks to Gradio for their easy-to-use Web UI building tool and great docs
- https://gradio.app/
- https://github.com/gradio-app/gradio

<!-- Royalty-Free Videos used for the examples
- "FunfaIr in Barcelona" https://motionarray.com/stock-video/funfair-in-barcelona-1163645/
- "Batter Misses A Pitch" https://motionarray.com/stock-video/batter-misses-a-pitch-1231021/
- "Bursting A Balloon" https://motionarray.com/stock-video/bursting-a-balloon-253645/ -->
