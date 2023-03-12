"""PNG Sequence to MP4 feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, split_filepath
from webui_utils.video_utils import PNGtoMP4 as _PNGtoMP4
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class PNGtoMP4(TabBase):
    """Encapsulates UI elements and events for the PNG Sequence to MP4 feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.png_to_mp4_settings["frame_rate"]
        minimum_crf = self.config.png_to_mp4_settings["minimum_crf"]
        maximum_crf = self.config.png_to_mp4_settings["maximum_crf"]
        default_crf = self.config.png_to_mp4_settings["default_crf"]
        with gr.Tab("PNG Sequence to MP4"):
            gr.Markdown(SimpleIcons.CONV_SYMBOL + "Convert a PNG sequence to a MP4")
            input_path_text_pm = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to the PNG files to be converted")
            output_path_text_pm = gr.Text(max_lines=1, label="MP4 File",
                placeholder="Path and filename on this server for the converted MP4 file")
            with gr.Row():
                input_pattern_text_pm = gr.Text(max_lines=1, label="Input Filename Pattern",
                    placeholder="Pattern like image%03d.png (auto=automatic pattern)")
                input_frame_rate_pm = gr.Slider(minimum=1, maximum=60, value=frame_rate,
                    step=1, label="Frame Rate")
                quality_slider_pm = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                    step=1, value=default_crf, label="Quality (lower=better)")
            with gr.Row():
                convert_button_pm = gr.Button("Convert", variant="primary")
                output_info_text_pm = gr.Textbox(label="Details", interactive=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.png_to_mp4.render()
        convert_button_pm.click(self.convert_png_to_mp4,
            inputs=[input_path_text_pm, input_pattern_text_pm, input_frame_rate_pm,
            output_path_text_pm, quality_slider_pm], outputs=output_info_text_pm)

    def convert_png_to_mp4(self,
                        input_path : str,
                        input_pattern : str,
                        frame_rate : int,
                        output_filepath: str,
                        quality : str):
        """Convert button handler"""
        if input_path and input_pattern and output_filepath:
            directory, _, _ = split_filepath(output_filepath)
            create_directory(directory)
            ffmpeg_cmd = _PNGtoMP4(input_path, input_pattern, int(frame_rate), output_filepath,
                crf=quality)
            return gr.update(value=ffmpeg_cmd, visible=True)
