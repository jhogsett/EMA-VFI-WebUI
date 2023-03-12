"""UI Functions"""
from .simple_utils import max_steps, restored_frame_fractions, restored_frame_predictions, \
    fps_change_details

def update_splits_info(num_splits : float):
    """Given a count of splits/search depth/search precision, compute the count of work steps"""
    # can be called directly by a Gradio event handler with one float input and one text output
    return str(max_steps(num_splits))

def update_info_fr(num_frames : int, num_splits : int):
    """Update info displayed on the Frame Restoration page"""
    # can be called directly by a Gradio event handler with one float input and two text outputs
    fractions = restored_frame_fractions(num_frames)
    predictions = restored_frame_predictions(num_frames, num_splits)
    return fractions, predictions

def update_info_fc(starting_fps : int, ending_fps : int, precision : int):
    """Update info displayed on the Change FPS page"""
    # can be called directly by a Gradio event handler with three float inputs and specific outputs
    return fps_change_details(starting_fps, ending_fps, precision)

def create_report(info_file : str,
                img_before_file : str,
                img_after_file : str,
                num_splits : int,
                output_path : str, output_paths : list):
    """Create a simple text report for an interpolation and save to a file"""
    report = f"""before file: {img_before_file}
after file: {img_after_file}
number of splits: {num_splits}
output path: {output_path}
frames:
""" + "\n".join(output_paths)
    with open(info_file, 'w', encoding='utf-8') as file:
        file.write(report)
