"""Enhance Frames feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories
from webui_utils.mtqdm import Mtqdm
# from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from image_enhancement import ImageEnhancement

class EnhanceImages(TabBase):
    """Encapsulates UI elements and events for the Enhance Images feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Enhance Images"):
            gr.Markdown(SimpleIcons.SPARKLES + "Auto-Correct Contrast for PNG Files",
                elem_id="tabheading")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path = gr.Text(max_lines=1, label="Input Path for PNG Files",
                        placeholder="Path on this server to the PNG files to be enhanced")
                    output_path = gr.Text(max_lines=1, label="Output Path for PNG Files",
                        placeholder="Path on this server to place the enhanced PNG files")
                    gr.Markdown("*Progress can be tracked in the console*")
                    enhance_button = gr.Button("Enhance", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="Input Path for PNG File Groups",
                        placeholder="Path on this server to the PNG file group directories to be enhanced")
                    output_path_batch = gr.Text(max_lines=1, label="Output Path for PNG File Groups",
                        placeholder="Path on this server to place the enhanced PNG file group directories")
                    gr.Markdown("*Progress can be tracked in the console*")
                    enhance_batch = gr.Button("Enhance Batch", variant="primary")
            clip_threshold = gr.Slider(minimum=1.0, maximum=10.0, value=2.0, label="Clip Threshold",
                                       info="A larger value produces more intense image enhancement")
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.simplify_png_files.render()

        enhance_button.click(self.enhance_png_files, show_progress=False,
                             inputs=[input_path, output_path, clip_threshold])
        enhance_batch.click(self.enhance_png_batch, show_progress=False,
                            inputs=[input_path_batch, output_path_batch, clip_threshold])

    def enhance_png_batch(self, input_path : str, output_path : str, clip_threshold : float):
        """Clean Batch button handler"""
        if input_path and output_path:
            self.log(f"beginning batch Enhance Image processing with input_path={input_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)
                        group_output_path = os.path.join(output_path, group_name)
                        self.enhance_png_files(group_input_path, group_output_path, clip_threshold)
                        Mtqdm().update_bar(bar)

    def enhance_png_files(self, input_path : str, output_path : str, clip_threshold : float):
        """Clean button handler"""
        if input_path and output_path:
            ImageEnhancement(input_path, output_path, clip_threshold, self.log_fn).enhance()
