"""Frame Search feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from tabs.tab_base import TabBase

class FrameSearch(TabBase):
    """Encapsulates UI elements and events for the Frame Search feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        max_splits = self.config.search_settings["max_splits"]
        default_splits = self.config.search_settings["default_splits"]
        with gr.Tab("Frame Search"):
            gr.HTML(SimpleIcons.MAGNIFIER +
                "Search for an arbitrarily precise timed frame and return the closest match",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    img1_input_fs = gr.Image(type="filepath", label="Before Frame", tool=None)
                    img2_input_fs = gr.Image(type="filepath", label="After Frame", tool=None)
                    with gr.Row():
                        splits_input_fs = gr.Slider(value=default_splits, minimum=1,
                                            maximum=max_splits, step=1, label="Search Precision")
                        min_input_text_fs = gr.Text(placeholder="0.0-1.0",
                            label="Lower Bound")
                        max_input_text_fs = gr.Text(placeholder="0.0-1.0",
                            label="Upper Bound")
                with gr.Column():
                    img_output_fs = gr.Image(type="filepath", label="Found Frame",
                        interactive=False, elem_id="mainoutput")
                    file_output_fs = gr.File(type="file", file_count="multiple",
                        label="Download", visible=False)
            search_button_fs = gr.Button("Search", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.frame_search.render()
        search_button_fs.click(self.frame_search,
            inputs=[img1_input_fs, img2_input_fs, splits_input_fs,
                min_input_text_fs, max_input_text_fs],
            outputs=[img_output_fs, file_output_fs])

    def frame_search(self,
                    img_before_file : str,
                    img_after_file : str,
                    num_splits : float,
                    min_target : float,
                    max_target : float):
        """Search button handler"""
        if img_before_file and img_after_file and min_target and max_target:
            base_output_path = self.config.directories["output_search"]
            use_time_step = self.config.engine_settings["use_time_step"]
            create_directory(base_output_path)
            output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")
            output_basename = "frame"

            if use_time_step:
                # use the time step feature of the model to reach the midpoint of the target range
                interpolater = Interpolate(self.engine.model, self.log)
                midpoint = float(min_target) + (float(max_target) - float(min_target)) / 2.0
                img_new = os.path.join(output_path, f"{output_basename}@{midpoint}.png")
                interpolater.create_between_frame(img_before_file, img_after_file, img_new,
                                                  midpoint)
                output_paths = interpolater.output_paths
            else:
                # use binary search interpolation to reach the target range
                interpolater = Interpolate(self.engine.model, self.log)
                target_interpolater = TargetInterpolate(interpolater, self.log)

                self.log(f"beginning targeted interpolations at {output_path}")
                target_interpolater.split_frames(img_before_file, img_after_file, num_splits,
                    float(min_target), float(max_target), output_path, output_basename)
                output_paths = target_interpolater.output_paths
            return gr.Image.update(value=output_paths[0]), gr.File.update(value=output_paths,
                visible=True)
