"""Assemble Video feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.video_utils import combine_videos
from webui_utils.file_utils import get_files, get_directories, split_filepath
from webui_utils.simple_utils import format_markdown
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class VideoAssembler(TabBase):
    """Encapsulates UI elements and events for the Assemble Video feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Assemble Video to: Combine video clips into a single video file (can take from seconds to minutes)"
    DEFAULT_MESSAGE_BATCH = "Click Assemble Batch to: Combine video clips in batch directories (can take from minutes to hours)"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Video Assembler"):
            gr.Markdown(
                SimpleIcons.CINEMA + "Combine multiple video clips into a single video",
                elem_id="tabheading")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    input_path = gr.Text(max_lines=1, label="Video Clips Path",
                        info="Path on this server to the video clips to be combined")
                    output_path = gr.Text(max_lines=1, label="Combined Video Path",
                        info="Path and fileame on this server for the combined video",
                        placeholder="Leave blank to use input path name as default")
                    message_box = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    gr.Markdown("*Progress can be tracked in the console*")
                    assemble_button = gr.Button("Assemble Video " + SimpleIcons.SLOW_SYMBOL, variant="primary")

                with gr.Tab(label="Batch Processing"):
                    input_path_batch = gr.Text(max_lines=1, label="Video Clip Directories Path",
                placeholder="Path on this server to the directories of video clips to be combined")
                    message_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    gr.Markdown("*Progress can be tracked in the console*")
                    assemble_batch = gr.Button("Assemble Batch " + SimpleIcons.SLOW_SYMBOL, variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.video_assembler.render()
        assemble_button.click(self.assemble_clips, inputs=[input_path, output_path], outputs=message_box)
        assemble_batch.click(self.assemble_batch, inputs=input_path_batch, outputs=message_batch)

    def assemble_batch(self, input_path : str):
        """Clean Batch button handler"""
        if not input_path:
            return format_markdown(
                "Enter a path to directories of video clips on this server to get started",
                "warning")

        if not os.path.exists(input_path):
            return format_markdown(f"Input path {input_path} was not found", "error")

        path_names = sorted(get_directories(input_path))
        if not path_names:
            return format_markdown(f"Input path {input_path} does not contain video clip directories", "error")

        self.log(f"beginning batch combine video clips processing with input_path={input_path}")
        self.log(f"found {len(path_names)} groups to process")

        warnings = []
        with Mtqdm().open_bar(total=len(path_names), desc="Assembling Batch") as bar:
            for path_name in path_names:
                clips_input_path = os.path.join(input_path, path_name)
                clips = get_files(clips_input_path)

                if not clips:
                    message = f"Directory {clips_input_path} is empty - skipping"
                    self.log(message)
                    warnings.append(message)
                    Mtqdm().update_bar(bar)
                    continue

                default_path = input_path
                default_filename = path_name
                first_clip = clips[0]
                _, _, default_ext = split_filepath(first_clip)
                output_filepath = os.path.join(default_path, default_filename + default_ext)

                try:
                    self.assemble_clips(clips_input_path, output_filepath, interactive=False)
                except ValueError as error:
                    return format_markdown(f"Error: {str(error)}", "error")

                Mtqdm().update_bar(bar)
        if warnings:
            warnings = "\r\n".join(warnings)
            return format_markdown(warnings, "warning")
        else:
            return format_markdown(self.DEFAULT_MESSAGE_BATCH)

    def assemble_clips(self, input_path : str, output_filepath : str="", interactive=True):
        """Assemble Video button handler"""
        if not input_path:
            if interactive:
                return format_markdown("Enter a path to video clips on this server to get started",
                                       "warning")
            else:
                raise ValueError("'input_path' must be provided")

        if not os.path.exists(input_path):
            if interactive:
                return format_markdown(f"Input path {input_path} was not found", "error")
            else:
                raise ValueError(f"input_path {input_path} not found")

        paths = sorted(get_files(input_path))
        if not paths:
            if interactive:
                return format_markdown(f"Input path {input_path} does not contain video clips",
                                       "error")
            else:
                raise ValueError(f"input_path {input_path} is empty")

        global_options = self.config.ffmpeg_settings["global_options"]
        if not output_filepath:
            _, default_filename, _ = split_filepath(input_path)
            _, _, default_ext = split_filepath(paths[0])
            output_filepath = os.path.join(input_path, default_filename + default_ext)

        with Mtqdm().open_bar(total=1, desc="Assembling Clips") as bar:
            try:
                ffcmd = combine_videos(paths,
                                    output_filepath,
                                    global_options=global_options)
            except ValueError as error:
                if interactive:
                    return format_markdown(f"Error: {str(error)}", "error")
                else:
                    raise error

            self.log(f"assemble_clips ffcmd={ffcmd}")
            Mtqdm().update_bar(bar)

        if interactive:
            return format_markdown(self.DEFAULT_MESSAGE_SINGLE)
