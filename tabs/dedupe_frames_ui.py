"""Deduplicate Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, split_filepath
from webui_utils.video_utils import deduplicate_frames
from webui_tips import WebuiTips
from webui_utils.auto_increment import AutoIncrementDirectory
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class DedupeFrames(TabBase):
    """Encapsulates UI elements and events for the Deduplicate Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        min_threshold = self.config.deduplicate_settings["min_threshold"]
        max_threshold = self.config.deduplicate_settings["max_threshold"]
        default_threshold = self.config.deduplicate_settings["default_threshold"]
        threshold_step = self.config.deduplicate_settings["threshold_step"]
        with gr.Tab("Deduplicate Frames"):
            gr.Markdown(SimpleIcons.CONV_SYMBOL + "Detect and remove duplicate PNG frame files")
            with gr.Row():
                input_path_text = gr.Text(max_lines=1, label="Input PNG Files Path",
                    placeholder="Path on this server to the PNG files to be deduplicated")
            with gr.Row():
                output_path_text = gr.Text(max_lines=1, label="Output PNG Files Path",
                    placeholder="Path on this server for the deduplicates PNG files," +
                                " leave blank to use default path")
            with gr.Row():
                threshold = gr.Slider(value=default_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step, label="Detection Threshold")
            with gr.Row():
                convert_button = gr.Button("Convert", variant="primary")
                output_info_text = gr.Textbox(label="Details", interactive=False)
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.png_to_gif.render()
        convert_button.click(self.dedupe_frames, inputs=[input_path_text, output_path_text,
                                                         threshold], outputs=output_info_text)

    def dedupe_frames(self,
                        input_path : str,
                        output_path : str,
                        threshold : int):
        """Convert button handler"""
        if input_path:
            if output_path:
                create_directory(output_path)
            else:
                base_output_path = self.config.directories["output_deduplication"]
                output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")
            ffmpeg_cmd = deduplicate_frames(input_path, output_path, threshold)
            return gr.update(value=ffmpeg_cmd, visible=True)
