"""Resequence Files feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown
from webui_utils.file_utils import get_directories, get_files, create_directory, is_safe_path, split_filepath
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

    DEFAULT_MESSAGE_SINGLE = "Click Resequence Files to: Assign new numbered filenames"
    DEFAULT_MESSAGE_BATCH = "Click Resequence Batch to: Assign new numbered filenames for each batch directory"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Resequence Files "):
            gr.HTML(SimpleIcons.NUMBERS +
                    "Rename a PNG sequence for import into video editing software",
                elem_id="tabheading")
            with gr.Row():
                input_filetype = gr.Text(value="png", max_lines=1,
                    info="Type of files to renumber such as png", label="File Type")
                input_newname = gr.Text(value="pngsequence", max_lines=1,
                    info="Base filename for renumbered files",
                    label="Base Filename")
                input_rename = gr.Checkbox(value=False,
                    label="Rename files in place (don't copy files)",
                    info="Resequences input path files only, ignoring output path")
            with gr.Row():
                input_start = gr.Number(value=0, precision=0, minimum=0,
                    label="Starting File Number",
                    info="Beginning number for renumbered files, usually 0")
                input_step = gr.Number(value=1, precision=0, minimum=1,
                    label="File Number Step", info="Sequential renumbering increment, usually 1")
                input_zerofill = gr.Text(value=None, max_lines=1,
                    label="File Number Padding", placeholder="(leave blank for auto detection)",
                    info="Sequential file number padding width (for sorting)")
            with gr.Row():
                input_stride = gr.Number(value=1, precision=0, minimum=1,
                    label="Sampling Stride",
                    info="Takes one file for each sample group of this size")
                input_offset = gr.Number(value=0, precision=0, minimum=0,
                    label="Sampling Offset",
                    info="Take this file positioned within the sample group")
                input_reverse = gr.Checkbox(value=False,
                    label="Reverse Sampling",
                    info="Resequences files in the opposite direction")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    with gr.Row():
                        input_path = gr.Text(max_lines=1,
                            placeholder="Path on this server to the files to be resequenced",
                            label="Input Path")
                        output_path = gr.Text(max_lines=1,
                            placeholder="Path on this server to the files to be resequenced",
                            label="Output Path (leave blank to use input path)")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    resequence_button = gr.Button("Resequence Files", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    with gr.Row():
                        input_path_batch = gr.Text(max_lines=1,
                            placeholder="Path on this server to the file groups to be resequenced",
                            label="Input Path")
                        output_path_batch = gr.Text(max_lines=1,
                            placeholder="Path on this server to the files to be resequenced",
                            label="Output Path (leave blank to use input path)")
                    input_batch_contiguous = gr.Checkbox(value=False,
                        label="Use contiguous renumbering across file groups")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    resequence_batch = gr.Button("Resequence Batch", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resequence_files.render()

        resequence_button.click(self.resequence_files,
            inputs=[input_path, output_path, input_filetype, input_newname,
                input_start, input_step, input_stride, input_offset, input_zerofill,
                input_rename, input_reverse],
            outputs=message_box_single)

        resequence_batch.click(self.resequence_batch,
            inputs=[input_path_batch, output_path_batch, input_filetype, input_newname,
                input_start, input_step, input_stride, input_offset, input_zerofill,
                input_rename, input_reverse, input_batch_contiguous],
            outputs=message_box_batch)

    def resequence_batch(self,
                        input_path : str,
                        output_path : str,
                        input_filetype : str,
                        input_newname : str,
                        input_start : str,
                        input_step : str,
                        input_stride : str,
                        input_offset : str,
                        input_zerofill : str,
                        input_rename : bool,
                        input_reverse : bool,
                        input_batch_contiguous : bool):
        """Resequence Button handler"""
        if not input_path:
            return gr.update(value=format_markdown(
                "Please enter an input path to begin", "warning"))
        if not os.path.exists(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} was not found", "error"))
        if not is_safe_path(input_path):
            return gr.update(value=format_markdown(
                f"The input path {input_path} is not valid", "error"))

        output_path = output_path or input_path
        if not is_safe_path(output_path):
            return gr.update(value=format_markdown(
                f"The input path {output_path} is not valid", "error"))

        self.log(f"beginning batch ResequenceFiles processing with input_path={input_path} " +\
                 f"and output_path={output_path}")

        if output_path != input_path and not input_rename:
            self.log(f"creating group output path {output_path}")
            create_directory(output_path)

        group_names = sorted(get_directories(input_path), reverse=input_reverse)
        self.log(f"found {len(group_names)} groups to process")

        for group_name in group_names:
            check_path = input_path if input_rename else output_path
            group_check_path = os.path.join(check_path, group_name)
            try:
                self._check_for_name_clash(group_check_path, input_filetype, input_newname)
            except ValueError as error:
                return gr.update(value=format_markdown(
                    f"Error: {error}", "error"))

        errors = []
        if group_names:
            with Mtqdm().open_bar(total=len(group_names), desc="File Group") as bar:
                running_start = int(input_start)
                for group_name in group_names:
                    group_input_path = os.path.join(input_path, group_name)
                    group_output_path = os.path.join(output_path, group_name)

                    try:
                        if input_batch_contiguous:
                            group_start = running_start
                            group_files = get_files(group_input_path, input_filetype)
                            running_start += len(group_files)
                        else:
                            group_start = int(input_start)
                        self.resequence_files(group_input_path,
                                                group_output_path,
                                                input_filetype,
                                                input_newname,
                                                group_start,
                                                input_step,
                                                input_stride,
                                                input_offset,
                                                input_zerofill,
                                                input_rename,
                                                input_reverse,
                                                interactive=False)
                    except ValueError as error:
                        errors.append(f"Error handling directory {group_name}: " + str(error))
                    Mtqdm().update_bar(bar)
        if errors:
            message = "\r\n".join(errors)
            return gr.update(value=format_markdown(message, "error"))
        else:
            message = f"Batch processed resequenced files saved to {os.path.abspath(output_path)}"
            return gr.update(value=format_markdown(message))

    def _check_for_name_clash(self, path, filetype, base_filename):
        files = get_files(path, filetype)
        file : str
        for file in files:
            _, filename, _ = split_filepath(file)
            if filename.startswith(base_filename):
                message = f"Existing files were found in {path} with the base filename {base_filename}"
                raise ValueError(message)

    def resequence_files(self,
                        input_path : str,
                        output_path : str,
                        input_filetype : str,
                        input_newname : str,
                        input_start : str,
                        input_step : str,
                        input_stride : str,
                        input_offset : str,
                        input_zerofill : str,
                        input_rename : bool,
                        input_reverse : bool,
                        interactive : bool=True):
        """Resequence Button handler"""
        if not input_path:
            if interactive:
                return gr.update(value=format_markdown("Please enter an input path to begin", "warning"))
            else:
                raise ValueError(f"The input path is empty")
        if not os.path.exists(input_path):
            message = f"The input path {input_path} was not found"
            if interactive:
                return gr.update(value=format_markdown(message, "error"))
            else:
                raise ValueError(message)
        if not is_safe_path(input_path):
            message = f"The input path {input_path} is not valid"
            if interactive:
                return gr.update(value=format_markdown(message, "error"))
            else:
                raise ValueError(message)
        output_path = output_path or input_path
        if not is_safe_path(output_path):
            return gr.update(value=format_markdown(
                f"The input path {output_path} is not valid", "error"))

        if not input_filetype:
            if interactive:
                return gr.update(value=format_markdown("Please enter the file type to begin", "warning"))
            else:
                raise ValueError(f"The file type is empty")
        if not input_newname:
            if interactive:
                return gr.update(value=format_markdown("Please enter the base filename to begin", "warning"))
            else:
                raise ValueError(f"The base filename is empty")
        input_start = int(input_start)
        input_step = int(input_step)
        if input_step == 0:
            if interactive:
                return gr.update(value=format_markdown("Please enter a non-zero file number step to begin", "warning"))
            else:
                raise ValueError(f"The file number step is zero")
        input_stride = int(input_stride)
        if input_stride == 0:
            if interactive:
                return gr.update(value=format_markdown("Please enter a non-zero sampling stride to begin", "warning"))
            else:
                raise ValueError(f"The sampling stride is zero")
        input_offset = int(input_offset)
        input_zerofill = input_zerofill or _ResequenceFiles.ZERO_FILL_AUTO_DETECT

        if output_path != input_path and not input_rename:
            self.log(f"creating group output path {output_path}")
            create_directory(output_path)

        check_path = input_path if input_rename else output_path
        try:
            self._check_for_name_clash(check_path, input_filetype, input_newname)
            _ResequenceFiles(input_path, input_filetype, input_newname, int(input_start),
                int(input_step), int(input_stride), int(input_offset), int(input_zerofill),
                input_rename, self.log, output_path=output_path, reverse=input_reverse).resequence()
        except ValueError as error:
            message = f"Error: {error}"
            if interactive:
                return gr.update(value=format_markdown(message, "error"))
            else:
                self.log(message)
                raise error

        message = f"Resequenced files saved to {os.path.abspath(output_path)}"
        if interactive:
            return gr.update(value=format_markdown(message))
        else:
            self.log(message)
