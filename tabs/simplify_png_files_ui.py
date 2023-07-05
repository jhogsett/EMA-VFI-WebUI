"""Simplify PNG files feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
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
            gr.Markdown(SimpleIcons.SPONGE + "Remove Interfering Non-Essential Data",
                elem_id="tabheading")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path_text = gr.Text(max_lines=1, label="PNG Files Path",
                        placeholder="Path on this server to the PNG files to be cleaned")
                    gr.Markdown("*Progress can be tracked in the console*")
                    clean_button = gr.Button("Clean", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="PNG File Groups Path",
                        placeholder="Path on this server to the PNG file groups to be cleaned")
                    gr.Markdown("*Progress can be tracked in the console*")
                    clean_batch = gr.Button("Clean Batch", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.simplify_png_files.render()
        clean_button.click(self.clean_png_files, inputs=input_path_text, show_progress=False)
        clean_batch.click(self.clean_png_batch, inputs=input_path_batch, show_progress=False)

    def clean_png_batch(self, input_path : str):
        """Clean Batch button handler"""
        if input_path:
            self.log(f"beginning batch SimplfyPngFiles processing with input_path={input_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)
                        self.clean_png_files(group_input_path)
                        Mtqdm().update_bar(bar)

    def clean_png_files(self, input_path : str):
        """Clean button handler"""
        if input_path:
            _SimplifyPngFiles(input_path, self.log_fn).simplify()
