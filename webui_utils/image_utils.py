"""Functions for dealing with images"""
import os
from .file_utils import is_safe_path
from PIL import Image

def create_gif(images : list, filepath : str, duration : int | float= 1000):
    """Create a GIF from one or more images
       Animated GIF created if more than one image
       Duration is for one frame if animated
    """
    if not isinstance(images, list):
        raise ValueError("'images' must be a list")
    if len(images) < 1:
        raise ValueError("'images' must be a non-empty list")
    for image in images:
        if not isinstance(image, str):
            raise ValueError("'images' must be a list of strings")
        if not is_safe_path(image):
            raise ValueError("'images' contains an illegal path")
        if not os.path.exists(image):
            raise ValueError(f"image file '{image}' does not exist")
    if not isinstance(filepath, str):
        raise ValueError("'filepath' must be a string")
    if not is_safe_path(filepath):
        raise ValueError("'filepath' must be a safe path")
    if not isinstance(duration, (int, float)):
        raise ValueError("'duration' must be an int or float")
    images = [Image.open(image) for image in images]
    if len(images) == 1:
        images[0].save(filepath)
    else:
        images[0].save(filepath, save_all=True, append_images=images[1:],
            optimize=False, duration=duration, loop=0)

def gif_frame_count(filepath : str):
    """Get the number of frames of a GIF file"""
    if not isinstance(filepath, str):
        raise ValueError("'filepath' must be a string")
    if not is_safe_path(filepath):
        raise ValueError("'filepath' must be a legal path")
    if not os.path.exists(filepath):
        raise ValueError(f"file '{filepath}' does not exist")
    gif = Image.open(filepath)
    if gif:
        return gif.n_frames
