"""File Deduplicater feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.video_utils import combine_videos
from webui_utils.file_utils import get_files, get_directories, split_filepath, directory_populated
from webui_utils.simple_utils import format_markdown
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from find_duplicate_files import FindDuplicateFiles

class FileDeduplicator(TabBase):
    """Encapsulates UI elements and events for the File Deduplicater feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_FIND = "Click Deduplicate Files to: Scan the path and find matching duplicate files (can take from minutes to hours)"
    # DEFAULT_MESSAGE_FUNNEL = "Click Assemble Batch to: Combine video clips in batch directories (can take from minutes to hours)"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("File Deduplicater"):
            gr.Markdown(
                SimpleIcons.MIRROR + "Extract duplicate files to n separate identical directory structure",
                elem_id="tabheading")
            with gr.Tabs():
                with gr.Tab(label="Deduplicate Path"):
                    with gr.Row():
                        input_path = gr.Text(max_lines=1, label="Input Path",
                            info="Path on this server to the files & directories to be deduplicated")
                        input_path2 = gr.Text(max_lines=1, label="Input Path 2",
                            info="Path on this server to optional files & directories as a read-only source of duplication")
                    with gr.Row():
                        wildcard = gr.Text(value="*.*", max_lines=1, label="Wildcard",
                            info="Set to a value such as '*.jpg' to choose only 'jpg' files")
                        recursive = gr.Checkbox(value=True, label="Include Sub-Directories",
                            info="If checked, paths are scanned recursively to find all files")
                    with gr.Row():
                        move_files = gr.Checkbox(value=False, label="Move Duplicates",
                            info="Leave unchecked to scan files only without making changes")
                        keep_type = gr.Dropdown(value="maxpathcomplex", label="Keep Filter",
                                                choices=["minpathcomplex", "maxpathcomplex"])
                    dupe_path = gr.Text(max_lines=1, label="Move To Path",
                        info="Path on this server to move the duplciate files & directories to",
                        placeholder="Leave blank to use default path")

                    message_box = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_FIND))
                    gr.Markdown("*Progress can be tracked in the console*")
                    deduplicate_button = gr.Button("Deduplicate Files " + SimpleIcons.SLOW_SYMBOL, variant="primary")

                # with gr.Tab(label="Create Duplicate Files Funnel"):

            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.video_assembler.render()
        deduplicate_button.click(self.deduplicate_files,
            inputs=[input_path, input_path2, wildcard, recursive, move_files, keep_type, dupe_path],
            outputs=message_box)

    # def assemble_batch(self, input_path : str):
    #     """Clean Batch button handler"""
    #     if not input_path:
    #         return format_markdown(
    #             "Enter a path to directories of video clips on this server to get started",
    #             "warning")

    #     if not os.path.exists(input_path):
    #         return format_markdown(f"Input path {input_path} was not found", "error")

    #     path_names = sorted(get_directories(input_path))
    #     if not path_names:
    #         return format_markdown(f"Input path {input_path} does not contain video clip directories", "error")

    #     self.log(f"beginning batch combine video clips processing with input_path={input_path}")
    #     self.log(f"found {len(path_names)} groups to process")

    #     warnings = []
    #     with Mtqdm().open_bar(total=len(path_names), desc="Assembling Batch") as bar:
    #         for path_name in path_names:
    #             clips_input_path = os.path.join(input_path, path_name)
    #             clips = get_files(clips_input_path)

    #             if not clips:
    #                 message = f"Directory {clips_input_path} is empty - skipping"
    #                 self.log(message)
    #                 warnings.append(message)
    #                 Mtqdm().update_bar(bar)
    #                 continue

    #             default_path = input_path
    #             default_filename = path_name
    #             first_clip = clips[0]
    #             _, _, default_ext = split_filepath(first_clip)
    #             output_filepath = os.path.join(default_path, default_filename + default_ext)

    #             try:
    #                 self.assemble_clips(clips_input_path, output_filepath, interactive=False)
    #             except ValueError as error:
    #                 return format_markdown(f"Error: {str(error)}", "error")

    #             Mtqdm().update_bar(bar)
    #     if warnings:
    #         warnings = "\r\n".join(warnings)
    #         return format_markdown(warnings, "warning")
    #     else:
    #         return format_markdown(self.DEFAULT_MESSAGE_BATCH)

    def deduplicate_files(self,
                          input_path : str,
                          input_path2 : str,
                          wildcard : str,
                          recursive : bool,
                          move_files : bool,
                          keep_type : str,
                          dupe_path : str,
                          interactive=True):
        """Deduplicate Files button handler"""
        if not input_path:
            if interactive:
                return format_markdown(
                    "Enter a path to files/directories on this server to get started",
                    "warning")
            else:
                raise ValueError("'input_path' must be provided")

        if not os.path.exists(input_path):
            if interactive:
                return format_markdown(f"Input path {input_path} was not found", "error")
            else:
                raise ValueError(f"input_path {input_path} not found")

        if not directory_populated(input_path):
            if interactive:
                return format_markdown(f"Files or directories not found in input path {input_path}",
                                       "error")
            else:
                raise ValueError(f"input_path {input_path} empty")

        if move_files:
            if not keep_type:
                if interactive:
                    return format_markdown(
                        "Keep Filter must be specified if Move Duplicates is checked",
                        "error")
                else:
                    raise ValueError(f"keep_type must be specified")

            if not dupe_path:
                # create default path
                path = os.path.normpath(input_path)
                root_path = path.split(os.sep)[0]
                path1_name = input_path[len(root_path)+1:]

                if input_path2:
                    path = os.path.normpath(input_path2)
                    root_path2 = path.split(os.sep)[0]
                    path2_name = input_path2[len(root_path2)+1:]

                    dupe_path = os.path.join(root_path, f"\DUPES-{path1_name}-{path2_name}")
                else:
                    dupe_path = os.path.join(root_path, f"\DUPES-{path1_name}")


        if input_path2:
            if not os.path.exists(input_path2):
                if interactive:
                    return format_markdown(f"Input path 2 {input_path2} was not found", "error")
                else:
                    raise ValueError(f"input_path {input_path} not found")

        if not wildcard:
            wildcard = "*.*"

        if dupe_path:
            if os.path.exists(dupe_path):
                if interactive:
                    return format_markdown(f"Move To Path {dupe_path} already exists", "error")
                else:
                    raise ValueError(f"dupe_path {dupe_path} exists")

        count = FindDuplicateFiles(input_path,
                                   input_path2,
                                   wildcard,
                                   recursive,
                                   dupe_path,
                                   keep_type,
                                   None,
                                   move_files,
                                   self.log_fn).find()

        if interactive:
            return format_markdown(f"{count} duplicate files extracted to {dupe_path}")
