"""Upscale Frames feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files, get_directories
# from webui_utils.auto_increment import AutoIncrementDirectory
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

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Upscale Frames"):
            gr.HTML(SimpleIcons.INCREASING + "Use Real-ESRGAN to Enlarge and Denoise Frames",
                elem_id="tabheading")
            with gr.Row():
                # with gr.Column():
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
                    gr.Markdown("*Progress can be tracked in the console*")
                    upscale_button = gr.Button("Upscale Frames " + SimpleIcons.SLOW_SYMBOL,
                                            variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="Input Path",
                                        placeholder="Path on this server to the PNG frame groups")
                    output_path_batch = gr.Text(max_lines=1, label="Output Path",
                                        placeholder="Where to place the upscaled frame groups")
                    gr.Markdown("*Progress can be tracked in the console*")
                    upscale_batch = gr.Button("Upscale Batch " + SimpleIcons.SLOW_SYMBOL,
                                            variant="primary")

            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.upscale_frames.render()
        upscale_button.click(self.upscale_frames,
            inputs=[input_path_text, output_path_text, scale_input, use_tiling])
        upscale_batch.click(self.upscale_batch,
            inputs=[input_path_batch, output_path_batch, scale_input, use_tiling])

    def upscale_batch(self,
                       input_path : str,
                       output_path : str | None,
                       upscale_factor : float,
                       use_tiling : str):
        """Upscale Frames button handler"""
        if input_path and output_path:
            self.log(f"beginning batch UpscaleFrames processing with input_path={input_path}" +\
                     f" output_path={output_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                self.log(f"creating group output path {output_path}")
                create_directory(output_path)

                with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)
                        group_output_path = os.path.join(output_path, group_name)

                        self.upscale_frames(group_input_path,
                                            group_output_path,
                                            upscale_factor,
                                            use_tiling)
                        Mtqdm().update_bar(bar)

    def upscale_frames(self,
                       input_path : str,
                       output_path : str | None,
                       upscale_factor : float,
                       use_tiling : str):
        """Upscale Frames button handler"""
        if input_path:
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

