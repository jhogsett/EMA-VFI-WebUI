"""Upscale Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.ui_utils import update_splits_info
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
                with gr.Column():
                    input_path_text = gr.Text(max_lines=1,
    placeholder="Path on this server to the frame PNG files (also upscales JPG, GIF, BMP files)",
                        label="Input Path")
                    output_path_text = gr.Text(max_lines=1,
                placeholder="Where to place the upscaled frames, leave blank save to input path",
                        label="Output Path")
                    with gr.Row():
                        scale_input = gr.Slider(value=4.0, minimum=1.0, maximum=8.0, step=0.05,
                            label="Frame Upscale Factor")
                        use_tiling = gr.Radio(label="Use Tiling",
                        choices=[
                            "Auto (Tile If Needed)",
                            "No (Best Quality)",
                            "Yes (For Large Files or Low VRAM)"],
                        value="Auto (Tile If Needed)")
            gr.Markdown("*Progress can be tracked in the console*")
            upscale_button = gr.Button("Upscale Frames " + SimpleIcons.SLOW_SYMBOL,
                                       variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.upscale_frames.render()
        upscale_button.click(self.upscale_frames,
            inputs=[input_path_text, output_path_text, scale_input, use_tiling])

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
                    upscaler = UpscaleSeries(model_name, gpu_ips, fp32, tiling, tile_pad, self.log)
                    output_dict = upscaler.upscale_series(file_list, output_path, upscale_factor,
                                                        output_basename, output_type)
                    file_list = [key for key in output_dict.keys() if output_dict[key] == None]
                    if file_list:
                        self.log(f"unable to upscale files:\n{file_list}")

