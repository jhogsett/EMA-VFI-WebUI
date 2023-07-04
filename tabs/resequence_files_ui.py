"""Resequence Files feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories, get_files
from webui_utils.mtqdm import Mtqdm
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
            gr.HTML(SimpleIcons.NUMBERS +
                    "Rename a PNG sequence for import into video editing software",
                elem_id="tabheading")
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
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path_text2 = gr.Text(max_lines=1,
                        placeholder="Path on this server to the files to be resequenced",
                        label="Input Path")
                    resequence_button = gr.Button("Resequence Files", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1,
                        placeholder="Path on this server to the file groups to be resequenced",
                        label="Input Path")
                    input_batch_contiguous = gr.Checkbox(value=False,
                        label="Use contiguous frame indexes across groups")
                    resequence_batch = gr.Button("Resequence Batch", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resequence_files.render()
        resequence_button.click(self.resequence_files,
            inputs=[input_path_text2, input_filetype_text, input_newname_text,
                input_start_text, input_step_text, input_stride, input_offset, input_zerofill_text,
                input_rename_check])
        resequence_batch.click(self.resequence_batch,
            inputs=[input_path_batch, input_filetype_text, input_newname_text,
                input_start_text, input_step_text, input_stride, input_offset, input_zerofill_text,
                input_rename_check, input_batch_contiguous])

    def resequence_batch(self,
                        input_path : str,
                        input_filetype : str,
                        input_newname : str,
                        input_start : str,
                        input_step : str,
                        input_stride : str,
                        input_offset : str,
                        input_zerofill : str,
                        input_rename_check : bool,
                        input_batch_contiguous : bool):
        """Resequence Button handler"""
        if input_path:
            self.log(f"beginning batch ResequenceFiles processing with input_path={input_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                with Mtqdm().open_bar(total=len(group_names), desc="File Group") as bar:
                    running_start = int(input_start)
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)

                        if input_batch_contiguous:
                            group_start = running_start
                            group_files = get_files(group_input_path, input_filetype)
                            running_start += len(group_files)
                        else:
                            group_start = int(input_start)

                        self.resequence_files(group_input_path,
                                              input_filetype,
                                              input_newname,
                                              group_start,
                                              input_step,
                                              input_stride,
                                              input_offset,
                                              input_zerofill,
                                              input_rename_check)
                        Mtqdm().update_bar(bar)

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
        if input_path and input_filetype and input_newname and input_start != ""\
            and input_step != 0 and input_zerofill:

            _ResequenceFiles(input_path, input_filetype, input_newname, int(input_start),
                int(input_step), int(input_stride), int(input_offset), int(input_zerofill),
                input_rename_check, self.log).resequence()
