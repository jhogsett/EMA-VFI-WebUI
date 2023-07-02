"""PNG Sequence to GIF feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, split_filepath
from webui_utils.video_utils import PNGtoGIF as _PNGtoGIF
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class PNGtoGIF(TabBase):
    """Encapsulates UI elements and events for the PNG Sequence to GIF feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.png_to_gif_settings["frame_rate"]
        max_frame_rate = self.config.png_to_gif_settings["max_frame_rate"]
        with gr.Tab("PNG Sequence to GIF"):
            gr.Markdown(SimpleIcons.CONV_SYMBOL + "Convert a PNG sequence to a GIF")
            with gr.Row():
                input_path_text_pg = gr.Text(max_lines=1, label="PNG Files Path",
                    placeholder="Path on this server to the PNG files to be converted")
                output_path_text_pg = gr.Text(max_lines=1, label="GIF File",
                    placeholder="Path and filename on this server for the converted GIF file")
            with gr.Row():
                input_pattern_text_pg = gr.Text(max_lines=1,
                    label="Input Filename Pattern (leave blank for auto-detect)",
                    placeholder="Example: 'pngsequence%09d.png'")
                framerate_pg = gr.Slider(value=frame_rate, minimum=1, maximum=max_frame_rate,
                                         step=0.01, label="GIF Frame Rate")
            with gr.Row():
                convert_button_pg = gr.Button("Convert", variant="primary")
                output_info_text_pg = gr.Textbox(label="Details", interactive=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.png_to_gif.render()
        convert_button_pg.click(self.convert_png_to_gif,
            inputs=[input_path_text_pg, input_pattern_text_pg, output_path_text_pg,
                framerate_pg], outputs=output_info_text_pg)

    def convert_png_to_gif(self,
                        input_path : str,
                        input_pattern : str,
                        output_filepath : str,
                        frame_rate : float):
        """Convert button handler"""
        if input_path and output_filepath:
            directory, _, _ = split_filepath(output_filepath)
            create_directory(directory)
            ffmpeg_cmd = _PNGtoGIF(input_path, input_pattern, output_filepath, frame_rate)
            return gr.update(value=ffmpeg_cmd, visible=True)
