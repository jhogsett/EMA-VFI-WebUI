"""Enhance Frames feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories, is_safe_path, create_directory
from webui_utils.mtqdm import Mtqdm
from webui_utils.simple_utils import format_markdown
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from image_enhancement import ImageEnhancement

class EnhanceFrames(TabBase):
    """Encapsulates UI elements and events for the Enhance Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Enhance to: Enhance the frames at the input path"
    DEFAULT_MESSAGE_BATCH = \
        "Click Enhance Batch to: Enhance the frames in each directory at the input path"

    def render_tab(self):
        """Render tab into UI"""
        threshold_min = self.config.enhance_images_settings["threshold_min"]
        threshold_max = self.config.enhance_images_settings["threshold_max"]
        threshold_step = self.config.enhance_images_settings["threshold_step"]
        threshold_default = self.config.enhance_images_settings["threshold_default"]
        with gr.Tab("Enhance Frames"):
            gr.Markdown(SimpleIcons.SPARKLES + "Auto-Correct Contrast for PNG Files",
                elem_id="tabheading")
            clip_threshold = gr.Slider(minimum=threshold_min,
                                       maximum=threshold_max,
                                       value=threshold_default,
                                       step=threshold_step,
                                       label="Correction Threshold",
                                    info="A larger value produces more intense auto-correction")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    with gr.Row():
                        input_path = gr.Text(max_lines=1, label="Input Path for PNG Files",
                            placeholder="Path on this server to the PNG files to be enhanced")
                        output_path = gr.Text(max_lines=1, label="Output Path for PNG Files",
                            placeholder="Path on this server to place the enhanced PNG files")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    gr.Markdown("*Progress can be tracked in the console*")
                    enhance_button = gr.Button("Enhance", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    with gr.Row():
                        input_path_batch = gr.Text(max_lines=1, label="Input Path for PNG File Groups",
                            placeholder="Path on this server to the PNG file group directories to be enhanced")
                        output_path_batch = gr.Text(max_lines=1, label="Output Path for PNG File Groups",
                            placeholder="Path on this server to place the enhanced PNG file group directories")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    gr.Markdown("*Progress can be tracked in the console*")
                    enhance_batch = gr.Button("Enhance Batch", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.enhance_frames.render()

        enhance_button.click(self.enhance_png_files,
                             inputs=[input_path, output_path, clip_threshold],
                             outputs=message_box_single)

        enhance_batch.click(self.enhance_png_batch,
                            inputs=[input_path_batch, output_path_batch, clip_threshold],
                             outputs=message_box_batch)

    def enhance_png_batch(self, input_path : str, output_path : str, clip_threshold : float):
        """Clean Batch button handler"""
        if not input_path or not output_path:
            return format_markdown("Please enter an input path and output path to begin", "warning")
        if not os.path.exists(input_path):
            return format_markdown(f"The input path {input_path} was not found", "error")
        if not is_safe_path(input_path):
            return format_markdown(f"The input path {input_path} is not valid", "error")
        if not is_safe_path(output_path):
            return format_markdown(f"The output path {output_path} is not valid", "error")
        create_directory(output_path)

        self.log(f"beginning batch Enhance Image processing with input_path={input_path}")
        group_names = get_directories(input_path)
        self.log(f"found {len(group_names)} groups to process")

        if not group_names:
            return format_markdown(f"No directories found in the input path {input_path}", "warning")

        with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
            for group_name in group_names:
                group_input_path = os.path.join(input_path, group_name)
                group_output_path = os.path.join(output_path, group_name)
                self.enhance_png_files(group_input_path, group_output_path, clip_threshold,
                                        interactive=False)
                Mtqdm().update_bar(bar)

        return format_markdown(f"Input directories processed to {output_path}")

    def enhance_png_files(self,
                          input_path : str,
                          output_path : str,
                          clip_threshold : float,
                          interactive=True):
        """Clean button handler"""
        if not input_path or not output_path:
            message = "Please enter an input path and output path to begin"
            if interactive:
                return format_markdown(message, "warning")
            else:
                raise ValueError(message)
        if not os.path.exists(input_path):
            message = f"The input path {input_path} was not found"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)
        if not is_safe_path(input_path):
            message = f"The input path {input_path} is not valid"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)
        if not is_safe_path(output_path):
            message = f"The output path {output_path} is not valid"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)
        create_directory(output_path)

        ImageEnhancement(input_path, output_path, clip_threshold, self.log_fn).enhance()

        if interactive:
            return format_markdown(f"Enhanced images saved to {output_path}")
