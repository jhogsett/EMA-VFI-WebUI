"""Resequence Files feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from resequence_files import ResequenceFiles as _ResequenceFiles
from tabs.tab_base import TabBase

class ResequenceFiles(TabBase):
    """Encapsulates UI elements and events for the Resequence Files feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Resequence Files "):
            gr.HTML(SimpleIcons.NUMBERS + "Rename a PNG sequence for import into video editing software",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    input_path_text2 = gr.Text(max_lines=1,
                        placeholder="Path on this server to the files to be resequenced",
                        label="Input Path")
                    with gr.Row():
                        input_filetype_text = gr.Text(value="png", max_lines=1,
                            placeholder="File type such as png", label="File Type")
                        input_newname_text = gr.Text(value="pngsequence", max_lines=1,
                            placeholder="Base filename for the resequenced files",
                            label="Base Filename")
                    with gr.Row():
                        input_start_text = gr.Text(value="0", max_lines=1,
                            placeholder="Starting integer for the sequence",
                            label="Starting Sequence Number")
                        input_step_text = gr.Text(value="1", max_lines=1,
                            placeholder="Integer step for the sequentially numbered files",
                            label="Integer Step")
                        input_zerofill_text = gr.Text(value="-1", max_lines=1,
                            placeholder="Padding with for sequential numbers, -1=auto",
                            label="Number Padding")
                    with gr.Row():
                        input_rename_check = gr.Checkbox(value=False,
                            label="Rename instead of duplicate files")
                    resequence_button = gr.Button("Resequence Files", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resequence_files.render()
        resequence_button.click(self.resequence_files,
            inputs=[input_path_text2, input_filetype_text, input_newname_text,
                input_start_text, input_step_text, input_zerofill_text,
                input_rename_check])

    def resequence_files(self,
                        input_path : str,
                        input_filetype : str,
                        input_newname : str,
                        input_start : str,
                        input_step : str,
                        input_zerofill : str,
                        input_rename_check : bool):
        """Resequence Button handler"""
        if input_path and input_filetype and input_newname and input_start and input_step \
                and input_zerofill:
            _ResequenceFiles(input_path, input_filetype, input_newname, int(input_start),
                int(input_step), int(input_zerofill), input_rename_check, self.log).resequence()
