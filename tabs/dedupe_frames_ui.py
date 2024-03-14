"""Deduplicate Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from deduplicate_frames import DeduplicateFrames
from webui_utils.auto_increment import AutoIncrementDirectory, AutoIncrementFilename
from webui_utils.video_utils import determine_input_format

class DedupeFrames(TabBase):
    """Encapsulates UI elements and events for the Deduplicate Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        min_threshold = self.config.deduplicate_settings["min_threshold"]
        max_threshold = self.config.deduplicate_settings["max_threshold"]
        default_threshold = self.config.deduplicate_settings["default_threshold"]
        threshold_step = self.config.deduplicate_settings["threshold_step"]
        def_max_dupes = self.config.deduplicate_settings["max_dupes_per_group"]
        max_max_dupes = self.config.deduplicate_settings["max_max_dupes"]
        # add max dupes; use new detect code
        with gr.Tab("Remove Duplicate Frames"):
            gr.Markdown(SimpleIcons.DEDUPE_SYMBOL + "Detect and remove duplicate PNG frame files")
            with gr.Row():
                input_path_text = gr.Text(max_lines=1, label="Input PNG Files Path",
                    placeholder="Path on this server to the PNG files to be deduplicated")
            with gr.Row():
                output_path_text = gr.Text(max_lines=1, label="Output PNG Files Path",
                    placeholder="Path on this server for the deduplicated PNG files," +
                                " leave blank to use default path")
            with gr.Row():
                threshold = gr.Slider(value=default_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step, label="Detection Threshold")
                max_dupes = gr.Slider(value=def_max_dupes, minimum=0, maximum=max_max_dupes, step=1,
                        label="Maximum Group Size to Delete (0 = no limit, 1 = no delete)")
            with gr.Row():
                dedupe_button = gr.Button("Deduplicate Frames", variant="primary")
            with gr.Row():
                output_text = gr.Textbox(label="Result", interactive=False, visible=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.deduplicate_frames.render()
        dedupe_button.click(self.dedupe_frames, inputs=[input_path_text, output_path_text,
                                                        threshold, max_dupes], outputs=output_text)

    def dedupe_frames(self,
                        input_path : str,
                        output_path : str,
                        threshold : int,
                        max_dupes : int):
        """Deduplicate Frames button handler"""
        if input_path:
            try:
                if not output_path:
                    base_output_path = self.config.directories["output_deduplication"]
                    output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

                type = determine_input_format(input_path)
                # repurpose max_dupes for delete to mean: skip delete on groups larger than this size
                ignore_over_size = max_dupes
                max_dupes = 0
                message, _, _, deleted_files, _ = DeduplicateFrames(None,
                                                                    input_path,
                                                                    output_path,
                                                                    threshold,
                                                                    max_dupes,
                                                                    None,
                                                                    self.log,
                                                                    type=type).invoke_delete(
                                                                        suppress_output=True,
                                                            max_size_for_delete=ignore_over_size)
                report = self.create_delete_report(input_path,
                                                     output_path,
                                                     threshold,
                                                     ignore_over_size,
                                                     message,
                                                     deleted_files)
                report_filepath, _ = AutoIncrementFilename(output_path, "txt").next_filename(
                                                                        "remove-report", "txt")
                with open(report_filepath, "w", encoding="UTF-8") as file:
                    file.write(report)
                return gr.update(value=message, visible=True)

            except RuntimeError as error:
                message = \
f"""Error deduplicating frames:
{error}"""
                return gr.update(value=message, visible=True)

    def create_delete_report(self, input_path : str, output_path : str, threshold : int,
                    max_dupes : int, message : str, deleted_files : list) -> str:
        report = []
        report.append("[Removed Frames Report]")
        report.append(f"input path: {input_path}")
        report.append(f"output path: {output_path}")
        report.append(f"threshold: {threshold}")
        report.append(f"max group: {max_dupes}")
        report.append(f"message: {message}")
        report.append("")
        report.append("[Removed Files]")
        report += deleted_files
        return "\r\n".join(report)

