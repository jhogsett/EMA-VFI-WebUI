"""Auto-Fill Duplicate Frames feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from deduplicate_frames import DeduplicateFrames
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from restore_frames import RestoreFrames
from webui_utils.auto_increment import AutoIncrementDirectory, AutoIncrementFilename
from webui_utils.video_utils import determine_input_format
from webui_utils.file_utils import create_directory, is_safe_path, get_directories
from webui_utils.simple_utils import format_markdown
from webui_utils.mtqdm import Mtqdm

class AutofillFrames(TabBase):
    """Encapsulates UI elements and events for the Deduplicate Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Deduplicate Frames to: Detect and replace duplicate frames"
    DEFAULT_MESSAGE_BATCH = \
        "Click Deduplicate Batch to: Detect and replace duplicate frames for each batch directory"

    def render_tab(self):
        """Render tab into UI"""
        min_threshold = self.config.deduplicate_settings["min_threshold"]
        max_threshold = self.config.deduplicate_settings["max_threshold"]
        default_threshold = self.config.deduplicate_settings["default_threshold"]
        threshold_step = self.config.deduplicate_settings["threshold_step"]
        def_max_dupes = self.config.deduplicate_settings["max_dupes_per_group"]
        max_precision = self.config.deduplicate_settings["max_precision"]
        default_precision = self.config.deduplicate_settings["default_precision"]
        max_max_dupes = self.config.deduplicate_settings["max_max_dupes"]
        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Auto-Fill Duplicate Frames"):
            gr.Markdown(SimpleIcons.BANDAGE +\
                        "Detect and fill duplicate frames with interpolated replacements")
            with gr.Row():
                threshold = gr.Slider(value=default_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step, label="Detection Threshold")
                max_dupes = gr.Slider(value=def_max_dupes, minimum=0, maximum=max_max_dupes, step=1,
                        label="Maximum Group Size to Auto-Fill (0 = no limit, 1 = no auto-fill)")
            with gr.Row():
                precision = gr.Slider(value=default_precision, minimum=1, maximum=max_precision,
                    step=1, label="Search Precision")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    with gr.Row():
                        input_path_text = gr.Text(max_lines=1, label="Input Path",
                            placeholder="Path on this server to the PNG files to be deduplicated")
                    with gr.Row():
                        output_path_text = gr.Text(max_lines=1, label="Output Path",
                            placeholder="Path on this server for the deduplicated PNG files")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    gr.Markdown("*Progress can be tracked in the console*")
                    dedupe_button = gr.Button("Deduplicate Frames " + SimpleIcons.SLOW_SYMBOL,
                                              variant="primary")
                with gr.Tab(label="Batch Processing"):
                    with gr.Row():
                        input_path_batch = gr.Text(max_lines=1, label="Input Path",
                            placeholder="Path on this server to the frame groups to be deduplicated")
                    with gr.Row():
                        output_path_batch = gr.Text(max_lines=1, label="Output Path",
                            placeholder="Path on this server for the deduplicated PNG files")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    gr.Markdown("*Progress can be tracked in the console*")
                    dedupe_batch = gr.Button("Deduplicate Batch " + SimpleIcons.SLOW_SYMBOL,
                                             variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.autofill_duplicates.render()

        dedupe_button.click(self.autofill_dupe_frames, inputs=[input_path_text, output_path_text,
                                                               threshold, max_dupes, precision],
                                                       outputs=message_box_single)

        dedupe_batch.click(self.autofill_dupe_batch, inputs=[input_path_batch, output_path_batch,
                                                               threshold, max_dupes, precision],
                                                       outputs=message_box_batch)

    def autofill_dupe_batch(self,
                        input_path : str,
                        output_path : str,
                        threshold : int,
                        max_dupes : int,
                        depth : int):
        if not input_path:
            return format_markdown("Please enter an input path to begin", "warning")
        if not os.path.exists(input_path):
            return format_markdown(f"The input path {input_path} was not found", "error")
        if not is_safe_path(input_path):
            return format_markdown(f"The input path {input_path} is not valid", "error")
        if not output_path:
            return format_markdown("Please enter an output path to begin", "warning")
        if not is_safe_path(output_path):
            return format_markdown(f"The output path {output_path} is not valid", "error")
        if threshold < 0:
            return format_markdown("Please enter a value >= zero for Threshold", "warning")
        if max_dupes < 0:
            return format_markdown("Please enter a value >= zero for Maximum Group Size", "warning")
        if depth < 1:
            return format_markdown("Please enter a value >= one for Search Precision", "warning")

        self.log(f"creating group output path {output_path}")
        create_directory(output_path)

        group_names = get_directories(input_path)
        if not group_names:
            return format_markdown(f"No directories were found at the input path {input_path}",
                                   "error")

        self.log(f"beginning batch Deduplication Auto-Fill processing with input_path={input_path}" +\
                    f" output_path={output_path}")
        self.log(f"found {len(group_names)} groups to process")

        errors = []
        with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
            for group_name in group_names:
                group_input_path = os.path.join(input_path, group_name)
                group_output_path = os.path.join(output_path, group_name)
                try:
                    self.autofill_dupe_frames(group_input_path, group_output_path, threshold,
                                              max_dupes, depth, interactive=False)
                except ValueError as error:
                    errors.append(f"Error handling directory {group_name}: " + str(error))
                Mtqdm().update_bar(bar)
        if errors:
            message = "\r\n".join(errors)
            return format_markdown(message, "error")
        else:
            message = f"Batch processed deduplicated frames saved to {os.path.abspath(output_path)}"
            return format_markdown(message)

    def autofill_dupe_frames(self,
                        input_path : str,
                        output_path : str,
                        threshold : int,
                        max_dupes : int,
                        depth : int,
                        interactive : bool=True):
        """Deduplicate Frames button handler"""

        if not input_path:
            if interactive:
                return format_markdown("Please enter an input path to begin", "warning")
            else:
                raise ValueError("The input path is empty")
        if not os.path.exists(input_path):
            message = f"The input path {input_path} was not found"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)
        if not is_safe_path(input_path):
            message = f"The input path {input_path} is not valid"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)

        if not output_path:
            if interactive:
                return format_markdown("Please enter an output path to begin", "warning")
            else:
                raise ValueError("The output path is empty")
        if not is_safe_path(output_path):
            message = f"The output path {output_path} is not valid"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)

        if threshold < 0:
            if interactive:
                return format_markdown("Please enter a value >= zero for Threshold", "warning")
            else:
                raise ValueError("Threshold must be >= 0")
        if max_dupes < 0:
            if interactive:
                return format_markdown("Please enter a value >= zero for Maximum Group Size",
                                       "warning")
            else:
                raise ValueError("Maximum Groups Size must be >= 0")
        if depth < 1:
            if interactive:
                return format_markdown("Please enter a value >= one for Search Precision", "warning")
            else:
                raise ValueError("Search Precision must be >= 1")

        try:
            if not output_path:
                base_output_path = self.config.directories["output_deduplication"]
                output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

            type = determine_input_format(input_path)
            interpolater = Interpolate(self.engine.model, self.log, type=type)
            target_interpolater = TargetInterpolate(interpolater, self.log, type=type)
            use_time_step = self.config.engine_settings["use_time_step"]
            frame_restorer = RestoreFrames(interpolater, target_interpolater, use_time_step,
                                            self.log, type=type)
            message, auto_filled_files, _ = DeduplicateFrames(frame_restorer,
                                                                input_path,
                                                                output_path,
                                                                threshold,
                                                                max_dupes,
                                                                depth,
                                                                self.log,
                                                                type=type).invoke_autofill(
                                                                    suppress_output=True)
            report = self.create_autofill_report(input_path,
                                                    output_path,
                                                    threshold,
                                                    max_dupes,
                                                    depth,
                                                    message,
                                                    auto_filled_files)
            report_name = "autofill-report"
            report_path = os.path.join(output_path, report_name)
            create_directory(report_path)
            report_filepath, _ = AutoIncrementFilename(report_path, "txt").next_filename(
                                                                                    report_name,
                                                                                    "txt")
            with open(report_filepath, "w", encoding="UTF-8") as file:
                file.write(report)
            if interactive:
                return gr.update(value=message, visible=True)
            else:
                self.log(message)

        except Exception as error:
            message = \
f"""Error deduplicating frames:
{error}"""
            if interactive:
                return gr.update(value=message, visible=True)
            else:
                raise ValueError(message)

    def create_autofill_report(self, input_path : str, output_path : str, threshold : int,
                    max_dupes : int, depth : int, message : str, auto_filled_files : list) -> str:
        report = []
        report.append("[Auto-filled Frames Report]")
        report.append(f"input path: {input_path}")
        report.append(f"output path: {output_path}")
        report.append(f"threshold: {threshold}")
        report.append(f"max group: {max_dupes}")
        report.append(f"search precision: {depth}")
        report.append(f"message: {message}")
        report.append("")
        report.append("[Auto-Filled Files]")
        report += auto_filled_files
        return "\r\n".join(report)

