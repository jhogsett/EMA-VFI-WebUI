"""Split Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from split_frames import SplitFrames as _SplitFrames

class SplitFrames(TabBase):
    """Encapsulates UI elements and events for the Split Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Split Frames"):
            gr.Markdown(
                SimpleIcons.CONV_SYMBOL + "Split large PNG sequences into processible chunks")
            input_path = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to the PNG files to be split")
            output_path = gr.Text(max_lines=1, label="Split Groups Base Path",
                placeholder="Path on this server to store the split file group directories")
            with gr.Row():
                num_groups = gr.Slider(value=10, minimum=1, maximum=1000,
                                       label="Number of Split Groups")
                split_type = gr.Radio(value="precise", label="Split Type",
                                      choices=["precise", "resynthesis", "inflation"],
                        info="Choose 'precise' unless the group files will be further processed")
                action_type = gr.Radio(value="copy", label="Disposition", choices=["copy", "move"],
                        info="Choose 'move' to delete the source files after splitting")
            with gr.Row():
                split_button = gr.Button("Split Frames", variant="primary")
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.mp4_to_png.render()
        split_button.click(self.split_frames,
            inputs=[input_path, output_path, num_groups, split_type, action_type])

    def split_frames(self,
                        input_path : str,
                        output_path : str,
                        num_groups : int,
                        split_type : str,
                        action_type : str):
        """Split button handler"""
        if input_path and output_path:
            _SplitFrames(
                input_path,
                output_path,
                "png",
                split_type,
                num_groups,
                action_type,
                False, self.log).split()