"""Resynthesize Video feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown
from webui_utils.file_utils import create_directory, get_files, get_directories, is_safe_path
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.ui_utils import update_splits_info
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from tabs.tab_base import TabBase

class VideoInflation(TabBase):
    """Encapsulates UI elements and events for the Video Inflation feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Inflate Video to: Insert the specified number of interpolated frames"
    DEFAULT_MESSAGE_BATCH = "Click Inflate Batch to: Insert the specified number of interpolated frames for each batch directory"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Video Inflation"):
            gr.HTML(SimpleIcons.BALLOON +
                "Double the number of video frames to any depth for super slow motion",
                elem_id="tabheading")
            with gr.Row():
                splits_input = gr.Slider(value=1, minimum=1, maximum=10, step=1,
                    label="Split Count")
                info_output = gr.Textbox(value="1",
                    label="Interpolations per Frame", max_lines=1, interactive=False)
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path_text = gr.Text(max_lines=1, label="Input Path",
                        placeholder="Path on this server to the frame PNG files")
                    output_path_text = gr.Text(max_lines=1, label="Output Path",
                        placeholder="Where to place the generated frames",
                        info="Leave blank to use default path")
                    gr.Markdown("*Progress can be tracked in the console*")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    interpolate_button = gr.Button("Inflate Video " + SimpleIcons.SLOW_SYMBOL,
                        variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1,
                        placeholder="Path on this server to the frame groups to inflate",
                        label="Input Path")
                    output_path_batch = gr.Text(max_lines=1,
                        placeholder="Where to place the inflated frame groups",
                        label="Output Path")
                    gr.Markdown("*Progress can be tracked in the console*")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    interpolate_batch = gr.Button("Inflate Batch " + SimpleIcons.SLOW_SYMBOL,
                        variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.video_inflation.render()

        splits_input.change(update_splits_info,
            inputs=splits_input, outputs=info_output, show_progress=False)

        interpolate_button.click(self.video_inflation,
            inputs=[input_path_text, output_path_text, splits_input],
            outputs=message_box_single)

        interpolate_batch.click(self.batch_inflation,
            inputs=[input_path_batch, output_path_batch, splits_input],
            outputs=message_box_batch)

    def batch_inflation(self, input_path : str, output_path : str | None, num_splits : float):
        """Inflate Video button handler"""
        if not input_path:
            return gr.update(value=format_markdown(
                "Please enter an input path to begin", "warning"))
        if not os.path.exists(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} was not found", "error"))
        if not is_safe_path(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} is not valid", "error"))

        group_names = get_directories(input_path)
        if not group_names:
            return gr.update(value=format_markdown(
                f"No directories were found at the input path {input_path}", "error"))

        self.log(f"beginning batch VideoInflation processing with input_path={input_path}" +\
                    f" output_path={output_path}")
        self.log(f"found {len(group_names)} groups to process")

        if output_path:
            if not is_safe_path(output_path):
                return gr.update(value=format_markdown(
                    f"The output path {output_path} is not valid", "error"))
            self.log(f"creating group output path {output_path}")
            create_directory(output_path)
        else:
            base_output_path = self.config.directories["output_inflation"]
            output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

        errors = []
        with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
            for group_name in group_names:
                group_input_path = os.path.join(input_path, group_name)
                group_output_path = os.path.join(output_path, group_name)
                try:
                    self.video_inflation(group_input_path, group_output_path, num_splits, interactive=False)
                except ValueError as error:
                    errors.append(f"Error handling directory {group_name}: " + str(error))
                Mtqdm().update_bar(bar)
        if errors:
            message = "\r\n".join(errors)
            return gr.update(value=format_markdown(message, "error"))
        else:
            message = f"Batch processed inflated frames saved to {os.path.abspath(output_path)}"
            return gr.update(value=format_markdown(message))

    def video_inflation(self, input_path : str, output_path : str | None, num_splits : float, interactive : bool=True):
        """Inflate Video button handler"""
        if not input_path:
            if interactive:
                return gr.update(value=format_markdown("Please enter an input path to begin", "warning"))
            else:
                raise ValueError(f"The input path is empty")
        if not os.path.exists(input_path):
            message = f"The input path {input_path} was not found"
            if interactive:
                return gr.update(value=format_markdown(message, "error"))
            else:
                raise ValueError(message)
        if not is_safe_path(input_path):
            message = f"The input path {input_path} is not valid"
            if interactive:
                return gr.update(value=format_markdown(message, "error"))
            else:
                raise ValueError(message)

        if output_path:
            if not is_safe_path(output_path):
                message = f"The output path {output_path} is not valid"
                if interactive:
                    return gr.update(value=format_markdown(message, "error"))
                else:
                    raise ValueError(f"The output path {input_path} is not valid")
            self.log(f"creating output path {output_path}")
            create_directory(output_path)
        else:
            base_output_path = self.config.directories["output_inflation"]
            output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

        interpolater = Interpolate(self.engine.model, self.log)
        use_time_step = self.config.engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
        series_interpolater = InterpolateSeries(deep_interpolater, self.log)

        output_basename = "interpolated_frames"
        file_list = get_files(input_path, extension="png")
        self.log(f"beginning series of deep interpolations at {output_path}")
        series_interpolater.interpolate_series(file_list, output_path, num_splits,
            output_basename)

        message = f"Inflated frames saved to {os.path.abspath(output_path)}"
        if interactive:
            return gr.update(value=format_markdown(message))
        else:
            self.log(message)
