"""Merge Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from merge_frames import MergeFrames as _MergeFrames

class MergeFrames(TabBase):
    """Encapsulates UI elements and events for the Split Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Merge Frames"):
            gr.Markdown(
                SimpleIcons.CONV_SYMBOL + "Recombine previously split PNG sequences")
            input_path = gr.Text(max_lines=1, label="Split Groups Base Path",
                placeholder="Path on this server to the split file group directories")
            output_path = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to store the recombined PNG files")
            with gr.Row():
                num_groups = gr.Number(value=-1,
                                       label="Number of Split Groups (-1 for auto-detect)")
                split_type = gr.Radio(value="Precise", label="Split Type",
                                      choices=["Precise", "Resynthesis", "Inflation"],
                        info="Choose the Split Type used when splitting the frames")
                action_type = gr.Radio(value="Combine", label="Files Action",
                                       choices=["Combine", "Revert"],
            info="Choose 'Combine' if groups were processed, 'revert' to undo a previous split")
            delete = gr.Checkbox(value=False, label="Delete groups after successful merge")
            merge_button = gr.Button("Merge Frames", variant="primary")
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.mp4_to_png.render()
        merge_button.click(self.merge_frames,
            inputs=[input_path, output_path, num_groups, split_type, action_type, delete])

    def merge_frames(self,
                        input_path : str,
                        output_path : str,
                        num_groups : int,
                        split_type : str,
                        action_type : str,
                        delete : bool):
        """Split button handler"""
        if input_path and output_path:
            _MergeFrames(
                input_path,
                output_path,
                "png",
                split_type.lower(),
                num_groups,
                action_type.lower(),
                delete,
                False, self.log).merge()