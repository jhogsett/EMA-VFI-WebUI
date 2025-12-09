# EMA-VFI-WebUI Development Guide

## Project Overview

**EMA-VFI-WebUI** is a Gradio-based web application for AI-powered video frame interpolation and movie restoration. It wraps the EMA-VFI deep learning model with an extensive toolkit for video processing workflows including frame interpolation, deduplication, upscaling, and project-based restoration.

### Core Architecture

- **Gradio UI Layer** (`webui.py`, `create_ui.py`, `tabs/*_ui.py`): Tab-based interface with restart capability
- **Interpolation Engine** (`interpolate_engine.py`): Singleton wrapper for EMA-VFI model with CUDA support
- **Processing Modules** (`interpolate.py`, `deep_interpolate.py`, etc.): Frame manipulation logic
- **Utilities** (`webui_utils/*`): Reusable helpers for video/image processing, FFmpeg operations, config management
- **Video Blender** (`video_blender.py`, `video_blender_*.py`): Project-based restoration with CSV metadata
- **Video Remixer** (`video_remixer.py`, `video_remixer_*.py`): Complex state-managed video processing pipeline

### Key Dependencies

The project relies on **external EMA-VFI files** that must be copied from the original [MCG-NJU/EMA-VFI](https://github.com/MCG-NJU/EMA-VFI) repo:
- `config.py`, `dataset.py`, `Trainer.py` (root directory)
- `benchmark/`, `ckpt/`, `model/` (directories)

Additional dependencies: Real-ESRGAN (for upscaling), FFmpeg (system PATH required), CUDA/PyTorch for GPU inference.

## Development Workflows

### Running the Application

```powershell
# Launch WebUI (standard method)
python webui.py

# Or use batch files
webui.bat  # Calls python webui.py
go.bat     # Activates conda env + launches UI

# Command-line tools (all have --help)
python interpolate.py --img_before images/0.png --img_after images/2.png
python deep_interpolate.py --depth 3 --output_path output/
```

### Testing

Tests use **pytest** in `webui_utils/test_*.py`:
```powershell
# Run specific test file
pytest webui_utils/test_file_utils.py -v

# Run all tests
pytest webui_utils/ -v
```

### Linting

Pylint is configured via `.pylintrc` to **disable all C/R/W messages** (only errors reported). CI runs on pull requests:
```powershell
pylint $(git ls-files '*.py')
```

Common patterns: `# pylint: disable=import-error` for external deps, `# pylint: disable=invalid-name` for FFmpeg wrapper functions (e.g., `PNGtoMP4`).

## Critical Patterns & Conventions

### 1. Singleton Pattern for Shared Resources

**InterpolateEngine** and **SimpleConfig** use `__new__` singletons to ensure single model/config instance:
```python
def __new__(cls, model : str, gpu_ids : str, use_time_step : bool=False):
    if not hasattr(cls, 'instance'):
        cls.instance = super(InterpolateEngine, cls).__new__(cls)
        cls.instance.init(model, gpu_ids, use_time_step)
    return cls.instance
```

**Mtqdm** (progress bar manager) also uses singleton pattern for coordinating nested progress bars with auto-coloring.

### 2. Tab-Based UI Architecture

All UI tabs inherit from `TabBase` and implement `render_tab()`:
```python
class MyFeature(TabBase):
    def __init__(self, config, engine, log_fn):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        with gr.Tab("Feature Name"):
            # Gradio components here
```

Tabs are assembled in `create_ui.py` with grouped organization (Interpolate Frames, Film Restoration, etc.).

### 3. Configuration Management

`config.yaml` centralizes all settings (directories, defaults, feature flags). Access via:
```python
config = SimpleConfig("config.yaml").config_obj()
output_path = config.directories["output_interpolation"]
fps = config.blender_settings["frame_rate"]
```

`config-local.yaml` overrides for local dev (gitignored). `session.yaml` stores UI convenience data (e.g., recently-used paths) to streamline workflows between runs - use `Session` class from `webui_utils/session.py` to persist user preferences.

### 4. FFmpeg Wrapper Patterns

`webui_utils/video_utils.py` provides high-level wrappers using `ffmpy`:
```python
from webui_utils.video_utils import PNGtoMP4, MP4toPNG, get_frame_count

# PNG sequence → MP4
PNGtoMP4(input_path="frames/", filename_pattern="frame%05d.png",
         frame_rate=30.0, output_filepath="output.mp4", crf=23)

# Extract video details
details = details_from_group_name("my_video.mp4")  # Returns dict with fps, resolution, etc.
```

All FFmpeg operations use `global_options` from config for consistent error handling (`-hide_banner -loglevel error`).

### 5. Progress Tracking with Mtqdm

For long-running operations, use the **Mtqdm singleton** for nested, auto-colored progress bars:
```python
from webui_utils.mtqdm import Mtqdm

with Mtqdm().open_bar(total=100, desc="Processing") as bar:
    for i in range(100):
        # ... work ...
        Mtqdm().update_bar(bar)
```

Supports up to 9 nested levels with customizable color palettes (default/alt/subdued/custom).

### 6. Project-Based Workflows

**Video Blender** uses CSV project files (`video_blender_projects.csv`):
```python
projects = VideoBlenderProjects("video_blender_projects.csv")
projects.add_project(name, project_path, frames1_path, frames2_path, main_path, fps)
```

**Video Remixer** maintains complex state in `VideoRemixerState` with nested projects, ingest pipeline, and scene management.

### 7. Command-Line + UI Dual Interface

Most features have both:
- Standalone script with `if __name__ == '__main__'` and argparse (e.g., `interpolate.py`)
- UI tab wrapper (e.g., `tabs/frame_interpolation_ui.py`)

Always implement core logic in a class that both can use.

### 8. File Naming Conventions

- **Zero-padded sequences**: `frame%05d.png` (width determined by frame count)
- **Sortable float indices**: Use `sortable_float_index()` from `simple_utils.py` for intermediate frames
- **Type hints**: Modern Python 3.10+ syntax (`str | None`, `Callable | None`)

## Common Gotchas

1. **EMA-VFI imports**: Code uses `sys.path.append('.')` and comments `# pylint: disable=import-error` for EMA-VFI deps
2. **Model loading**: `InterpolateEngine` appends `"_t"` to model name if `use_time_step=True` (e.g., `"ours_t"`)
3. **Directory safety**: Always use `is_safe_path()` before destructive operations (prevents deleting system dirs)
4. **Frame indices**: 0-based internally, 1-based in UI displays
5. **Gradio version**: Pinned to `3.36.1` (not latest) for stability
6. **Windows paths**: Code assumes Windows development environment (see `go.bat` conda activation)

## Key Files Reference

- `interpolate.py`: Single/multi-frame interpolation
- `deep_interpolate.py`: Recursive interpolation (2^N frames)
- `webui_utils/file_utils.py`: Path manipulation, safe operations, zip creation
- `webui_utils/image_utils.py`: PIL/cv2 helpers, GIF operations
- `webui_utils/simple_utils.py`: Time formatting, sample indices, sortable floats
- `webui_utils/auto_increment.py`: Auto-incrementing directory names
- `tabs/tab_base.py`: Base class for all UI tabs
- `video_blender.py`: Project/path management for restoration workflows

## Adding New Features

1. Create core logic class in root (e.g., `my_feature.py`) with `if __name__ == '__main__'` CLI
2. Create UI tab in `tabs/my_feature_ui.py` inheriting `TabBase`
3. Add tab to `create_ui.py` imports and render in appropriate `gr.Tab()` group
4. Add settings to `config.yaml` if needed (use `my_feature_settings:` section)
5. Add output directory to `config.yaml` `directories:` section
6. Write pytest tests in `webui_utils/test_my_feature.py` if adding utility functions
