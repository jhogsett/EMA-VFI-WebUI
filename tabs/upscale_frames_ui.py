"""Upscale Frames feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown
from webui_utils.file_utils import create_directory, get_files, get_directories, is_safe_path
# from webui_utils.ui_utils import update_splits_info
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from upscale_series import UpscaleSeries
from tabs.tab_base import TabBase

class UpscaleFrames(TabBase):
    """Encapsulates UI elements and events for the Upscale Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : any,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Upscale Frames to: Create cleansed and enlarged frames"
    DEFAULT_MESSAGE_BATCH = "Click Upscale Batch to: Create cleansed and enlarged frames for each batch directory"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Upscale Frames"):
            gr.HTML(SimpleIcons.INCREASING + "Use Real-ESRGAN to Enlarge and Denoise Frames",
                elem_id="tabheading")
            with gr.Row():
                with gr.Row():
                    scale_input = gr.Slider(value=4.0, minimum=1.0, maximum=8.0, step=0.05,
                        label="Frame Upscale Factor")
                    use_tiling = gr.Radio(label="Use Tiling",
                    choices=[
                        "Auto (Tile If Needed)",
                        "No (Best Quality)",
                        "Yes (For Large Files or Low VRAM)"],
                    value="Auto (Tile If Needed)")

            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path_text = gr.Text(max_lines=1, label="Input Path",
                                        placeholder="Path on this server to the frame PNG files",
                                        info="Also works with other formats like JPG, GIF, BMP")
                    output_path_text = gr.Text(max_lines=1, label="Output Path",
                                        placeholder="Where to place the upscaled frames",
                                        info="Leave blank save to Input Path")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    gr.Markdown("*Progress can be tracked in the console*")
                    upscale_button = gr.Button("Upscale Frames " + SimpleIcons.SLOW_SYMBOL,
                                            variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="Input Path",
                                        placeholder="Path on this server to the PNG frame groups")
                    output_path_batch = gr.Text(max_lines=1, label="Output Path",
                                        placeholder="Where to place the upscaled frame groups")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    gr.Markdown("*Progress can be tracked in the console*")
                    upscale_batch = gr.Button("Upscale Batch " + SimpleIcons.SLOW_SYMBOL,
                                            variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.upscale_frames.render()

        upscale_button.click(self.upscale_frames,
            inputs=[input_path_text, output_path_text, scale_input, use_tiling],
            outputs=message_box_single)

        upscale_batch.click(self.upscale_batch,
            inputs=[input_path_batch, output_path_batch, scale_input, use_tiling],
            outputs=message_box_batch)

    def upscale_batch(self,
                       input_path : str,
                       output_path : str | None,
                       upscale_factor : float,
                       use_tiling : str):
        """Upscale Frames button handler"""
        if not input_path or not output_path:
            return gr.update(value=format_markdown(
                "Please enter an input path and output path to begin", "warning"))
        if not os.path.exists(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} was not found", "error"))
        if not is_safe_path(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} is not valid", "error"))
        if not is_safe_path(output_path):
            return gr.update(value=format_markdown(
                f"The output path {output_path} is not valid", "error"))

        group_names = get_directories(input_path)
        if not group_names:
            return gr.update(value=format_markdown(
                f"No directories were found at the input path {input_path}", "error"))

        self.log(f"beginning batch UpscaleFrames processing with input_path={input_path}" +\
                    f" output_path={output_path}")
        self.log(f"found {len(group_names)} groups to process")

        self.log(f"creating group output path {output_path}")
        create_directory(output_path)

        errors = []
        with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
            for group_name in group_names:
                group_input_path = os.path.join(input_path, group_name)
                group_output_path = os.path.join(output_path, group_name)

                try:
                    self.upscale_frames(group_input_path,
                                        group_output_path,
                                        upscale_factor,
                                        use_tiling,
                                        interactive=False)
                except ValueError as error:
                    errors.append(f"Error handling directory {group_name}: " + str(error))
                Mtqdm().update_bar(bar)
        if errors:
            message = "\r\n".join(errors)
            return gr.update(value=format_markdown(message, "error"))
        else:
            message = f"Batch processed upscaled frames saved to {os.path.abspath(output_path)}"
            return gr.update(value=format_markdown(message))

    def upscale_frames(self,
                       input_path : str,
                       output_path : str | None,
                       upscale_factor : float,
                       use_tiling : str,
                       interactive : bool=True):
        """Upscale Frames button handler"""
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

        model_name = self.config.realesrgan_settings["model_name"]
        gpu_ids = self.config.realesrgan_settings["gpu_ids"]
        fp32 = self.config.realesrgan_settings["fp32"]

        if use_tiling.startswith("Yes"):
            tiling = self.config.realesrgan_settings["tiling"]
            tile_pad = self.config.realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        upscaler = UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, self.log)

        if output_path:
            if not is_safe_path(output_path):
                message = f"The output path {output_path} is not valid"
                if interactive:
                    return gr.update(value=format_markdown(message, "error"))
                else:
                    raise ValueError(f"The output path {input_path} is not valid")
            self.log(f"creating output path {output_path}")
            create_directory(output_path)
            output_basename = "upscaled_frames"
            output_type = "png"
        else:
            output_path = input_path
            output_basename = None
            output_type = None

        image_extensions = self.config.upscale_settings["file_types"]
        file_list = get_files(input_path, image_extensions)

        self.log(f"beginning series of upscaling of {image_extensions} files at {output_path}")
        output_dict = upscaler.upscale_series(file_list, output_path, upscale_factor,
                                                output_basename, output_type)

        if use_tiling.startswith("Auto"):
            file_list = [key for key in output_dict.keys() if output_dict[key] == None]
            if file_list:
                self.log(
            f"redoing upscaling with tiling for {len(file_list)} failed files at {output_path}")

                tiling = self.config.realesrgan_settings["tiling"]
                tile_pad = self.config.realesrgan_settings["tile_pad"]
                upscaler = UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, self.log)
                output_dict = upscaler.upscale_series(file_list, output_path, upscale_factor,
                                                    output_basename, output_type)

                file_list = [key for key in output_dict.keys() if output_dict[key] == None]
                if file_list:
                    self.log(f"unable to upscale files:\n{file_list}")

        message = f"Upscaled frames saved to {os.path.abspath(output_path)}"
        if interactive:
            return gr.update(value=format_markdown(message))
        else:
            self.log(message)