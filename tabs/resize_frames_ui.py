"""Resize Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.ui_utils import update_splits_info
# from webui_tips import WebuiTips
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
            gr.HTML(SimpleIcons.PINCHING_HAND + " Use OpenCV 'Resize' to Enlarge or Reduce Frames",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    input_path_text = gr.Text(max_lines=1,
                        placeholder="Path on this server to the frame PNG files",
                        label="Input Path")
                    output_path_text = gr.Text(max_lines=1,
                        placeholder="Where to place the resized frames",
                        label="Output Path")
                    with gr.Row():
                        new_width = gr.Number(value=None,
                        label="New Width")
                        new_height = gr.Number(value=None,
                        label="New Height")
                    with gr.Row():
                        scale_type = gr.Radio(value="lanczos",
                            choices=["area", "cubic", "lanczos", "linear", "nearest"],
                            label="Scaling Type")
            gr.Markdown("*Progress can be tracked in the console*")
            resize_button = gr.Button("Resize Frames " + SimpleIcons.SLOW_SYMBOL,
                                       variant="primary")
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.upscale_frames.render()
        resize_button.click(self.resize_frames,
            inputs=[input_path_text, output_path_text, new_width, new_height, scale_type])

    def resize_frames(self,
                       input_path : str,
                       output_path : str,
                       new_width : int,
                       new_height : int,
                       scale_type : str):
        """Resize Frames button handler"""
        if input_path and output_path:
            self.log(f"initializing ResizeFrames with input_path={input_path} output_path={output_path} new_width={new_width} new_height={new_height} scaling_type={scale_type}")
            _ResizeFrames(input_path,
                         output_path,
                         int(new_width),
                         int(new_height),
                         scale_type,
                         self.log).resize()
