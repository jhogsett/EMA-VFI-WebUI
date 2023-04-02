"""Simplify PNG files feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory
from webui_utils.video_utils import GIFtoPNG as _GIFtoPNG
# from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from simplify_png_files import SimplifyPngFiles as _SimplifyPngFiles

class SimplifyPngFiles(TabBase):
    """Encapsulates UI elements and events for the Simplify PNG files feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Clean PNG Files"):
            gr.Markdown(SimpleIcons.SPONGE + "Clean _Ancillary Chunks_ from PNG files")
            input_path_text = gr.Text(max_lines=1, label="PNG files path",
                placeholder="Path on this server to the PNG files to be cleaned")
            with gr.Row():
                clean_button = gr.Button("Clean", variant="primary")
                # output_info_text_gp = gr.Textbox(label="Details", interactive=False)
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.gif_to_png.render()
        clean_button.click(self.clean_png_files, inputs=input_path_text, show_progress=False)

    def clean_png_files(self, input_path : str):
        """Clean button handler"""
        if input_path:
            _SimplifyPngFiles(input_path, self.log_fn).simplify()
