"""Resequence Files feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_core.simple_config import SimpleConfig
from webui_core.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from webui_core.interpolate_engine import InterpolateEngine
from webui_core.resequence_files import ResequenceFiles as _ResequenceFiles
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
                            label="Starting Frame Number (usually 0)")
                        input_step_text = gr.Text(value="1", max_lines=1,
                            label="Frame Number Step (usually 1)")
                        input_zerofill_text = gr.Text(value="-1", max_lines=1,
                            label="Frame Number Padding (-1 for auto detect)")
                    with gr.Row():
                        input_stride = gr.Text(value="1", max_lines=1,
                            label="Sampling Stride (usually 1)")
                        input_offset = gr.Text(value="0", max_lines=1,
                            label="Sampling Offset (usually 0)")
                    with gr.Row():
                        input_rename_check = gr.Checkbox(value=False,
                            label="Rename instead of duplicate files")
                    resequence_button = gr.Button("Resequence Files", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resequence_files.render()
        resequence_button.click(self.resequence_files,
            inputs=[input_path_text2, input_filetype_text, input_newname_text,
                input_start_text, input_step_text, input_stride, input_offset, input_zerofill_text,
                input_rename_check])

    def resequence_files(self,
                        input_path : str,
                        input_filetype : str,
                        input_newname : str,
                        input_start : str,
                        input_step : str,
                        input_stride : str,
                        input_offset : str,
                        input_zerofill : str,
                        input_rename_check : bool):
        """Resequence Button handler"""
        if input_path and input_filetype and input_newname and input_start and input_step \
                and input_zerofill:
            _ResequenceFiles(input_path, input_filetype, input_newname, int(input_start),
                int(input_step), int(input_stride), int(input_offset), int(input_zerofill),
                input_rename_check, self.log).resequence()
