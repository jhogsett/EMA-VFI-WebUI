"""Resize Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.ui_utils import update_splits_info
from webui_tips import WebuiTips
from resize_frames import ResizeFrames as _ResizeFrames
from tabs.tab_base import TabBase

class ResizeFrames(TabBase):
    """Encapsulates UI elements and events for the Resize Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : any,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Resize Frames"):
            gr.Markdown(SimpleIcons.PINCHING_HAND +\
                        " Reduce, Enlarge and Crop Frames",
                elem_id="tabheading")
            with gr.Row():
                input_path_text = gr.Text(max_lines=1,
                    placeholder="Path on this server to the frame PNG files",
                    label="Input Path")
                output_path_text = gr.Text(max_lines=1,
                    placeholder="Where to place the resized frames",
                    label="Output Path")
            with gr.Box():
                with gr.Row():
                    with gr.Column():
                        scale_type = gr.Radio(value="lanczos",
                            choices=["area", "cubic", "lanczos", "linear", "nearest", "none"],
                            label="Scaling Type",
                            info = "Choose 'area' for best reducing, 'lanczos' for best enlarging")
                    with gr.Column():
                        with gr.Row():
                            scale_width = gr.Number(value=None, label="Scale Width")
                            scale_height = gr.Number(value=None, label="Scale Height")
            with gr.Box():
                with gr.Row():
                    with gr.Column():
                        crop_type = gr.Radio(value="none",
                            choices=["crop", "none"],
                            label="Cropping Type",
                            info = "Choose 'crop' to crop the resized image, 'none' for no cropping")
                    with gr.Column():
                        with gr.Row():
                            crop_width = gr.Number(value=-1, label="Crop Width",
                                                info="Use -1 for scale width")
                            crop_height = gr.Number(value=-1, label="Crop Height",
                                                    info="Use -1 for scale height")
                            crop_offset_x = gr.Number(value=-1, label="Crop X Offset",
                                                    info="Use -1 for auto-centering")
                            crop_offset_y = gr.Number(value=-1, label="Crop Y Offset",
                                                    info="Use -1 for auto-centering")
            gr.Markdown("*Progress can be tracked in the console*")
            resize_button = gr.Button("Resize Frames " + SimpleIcons.SLOW_SYMBOL,
                                       variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resize_frames.render()
        resize_button.click(self.resize_frames,
            inputs=[input_path_text, output_path_text, scale_type, scale_width, scale_height,
                    crop_type, crop_width, crop_height, crop_offset_x, crop_offset_y])

    def resize_frames(self,
                       input_path : str,
                       output_path : str,
                       scale_type : str,
                       scale_width : int,
                       scale_height : int,
                       crop_type : str,
                       crop_width : int,
                       crop_height : int,
                       crop_offset_x : int,
                       crop_offset_y : int):
        """Resize Frames button handler"""
        if input_path and output_path:
            self.log(f"initializing ResizeFrames with input_path={input_path}" +\
                     f" output_path={output_path} scale_type={scale_type}" +\
                    f" scale_width={scale_width} scale_height={scale_height}" +\
                    f" crop_type={crop_type} crop_width={crop_width}" +\
                    f" crop_height={crop_height} crop_offset_x={crop_offset_x}" +\
                    f" crop_offset_y={crop_offset_y}"
                    )
            _ResizeFrames(input_path,
                         output_path,
                         int(scale_width),
                         int(scale_height),
                         scale_type,
                         self.log,
                         crop_type=crop_type,
                         crop_width=crop_width,
                         crop_height=crop_height,
                         crop_offset_x=crop_offset_x,
                         crop_offset_y=crop_offset_y).resize()
