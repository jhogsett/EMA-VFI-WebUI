"""Transform PNG files feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories
from webui_utils.video_utils import determine_input_format
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from transpose_png_files import TransposePngFiles as _TransposePngFiles

class TransposePngFiles(TabBase):
    """Encapsulates UI elements and events for the Transpose PNG files feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    UI_TYPES_TO_INTERNAL = {
        "Rotate 90° Right" : "cw90",
        "Rotate 90° Left" : "ccw90",
        "Rotate 180°" : "rot180",
        "Flip Left-Right" : "fliph",
        "Flip Top-Bottom" : "flipv",
        "Transpose" : "transp",
        "Transverse" : "transv"
    }
    DEFAULT_UI_TYPE = list(UI_TYPES_TO_INTERNAL.keys())[0]

    @staticmethod
    def ui_types() -> str:
        return list(TransposePngFiles.UI_TYPES_TO_INTERNAL.keys())

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Transpose PNG Files"):
            gr.Markdown(SimpleIcons.RIGHT_DOWN_ARROW + "Rotate / Flip PNG Frames",
                elem_id="tabheading")
            input_type = gr.Radio(label="Transpose Type", choices=TransposePngFiles.ui_types(),
                                  value=TransposePngFiles.DEFAULT_UI_TYPE)
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path_text = gr.Text(max_lines=1, label="PNG Files Path",
                        placeholder="Path on this server to the PNG files to be transposed")
                    gr.Markdown("*Progress can be tracked in the console*")
                    transpose_button = gr.Button("Transpose", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="PNG File Groups Path",
                        placeholder="Path on this server to the PNG file groups to be transposed")
                    gr.Markdown("*Progress can be tracked in the console*")
                    transpose_batch = gr.Button("Transpose Batch", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.transpose_png_files.render()
        transpose_button.click(self.transpose_png_files, inputs=[input_path_text, input_type],
                               show_progress=False)
        transpose_batch.click(self.transpose_png_batch, inputs=[input_path_batch, input_type],
                              show_progress=False)

    def transpose_png_batch(self, input_path : str, input_type : str):
        """Transpose Batch button handler"""
        if input_path:
            self.log(f"beginning batch TransposePngFiles processing with input_path={input_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)
                        self.transpose_png_files(group_input_path, input_type)
                        Mtqdm().update_bar(bar)

    def transpose_png_files(self, input_path : str, input_type : str):
        """Transpose button handler"""
        if input_path:
            type = determine_input_format(input_path)
            input_type = TransposePngFiles.UI_TYPES_TO_INTERNAL[input_type]
            _TransposePngFiles(input_path, input_type, self.log_fn).transpose(type=type)
