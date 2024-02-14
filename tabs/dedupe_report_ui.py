"""Duplicate Frames Report feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from webui_utils.auto_increment import AutoIncrementDirectory
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from deduplicate_frames import DeduplicateFrames

class DuplicateFramesReport(TabBase):
    """Encapsulates UI elements and events for the Duplicate Frames Report feature"""
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
        max_lines = self.config.deduplicate_settings["max_lines"]
        max_max_dupes = self.config.deduplicate_settings["max_max_dupes"]
        with gr.Tab("Duplicate Frames Report"):
            gr.Markdown(SimpleIcons.DOCUMENT + "Detect and report duplicate PNG frame files")
            with gr.Row():
                input_path_text = gr.Text(max_lines=1, label="Input PNG Files Path",
                    placeholder="Path on this server to the PNG files to be reported on")
            with gr.Row():
                threshold = gr.Slider(value=default_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step, label="Detection Threshold")
                max_dupes = gr.Slider(value=def_max_dupes, minimum=0, maximum=max_max_dupes, step=1,
                    label="Maximum Duplicates Per Group (0 = no limit, 1 = no duplicates allowed)")
            with gr.Row():
                report_button = gr.Button("Create Report", variant="primary")
            with gr.Row():
                file_output = gr.File(type="file", file_count="multiple", label="Download",
                                      visible=False)
            with gr.Row():
                output_text = gr.Textbox(label="Report", max_lines=max_lines, interactive=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.duplicates_report.render()
        report_button.click(self.create_report, inputs=[input_path_text, threshold, max_dupes],
                            outputs=[file_output, output_text])

    def create_report(self,
                        input_path : str,
                        threshold : int,
                        max_dupes : int):
        """Create Report button handler"""
        if input_path:
            try:
                report = DeduplicateFrames(None,
                                            input_path,
                                            None,
                                            threshold,
                                            max_dupes,
                                            None,
                                            self.log).invoke_report(suppress_output=True)

                base_output_path = self.config.directories["output_deduplication"]
                output_path, run_index = AutoIncrementDirectory(base_output_path).next_directory(
                    "run")
                output_basename = "duplicate_frames_report"
                self.log(f"creating duplicate frames report at {output_path}")

                info_file = os.path.join(output_path, output_basename + str(run_index) + ".txt")
                with open(info_file, "w", encoding="UTF-8") as file:
                    file.write(report)
                return gr.update(value=[info_file], visible=True), \
                       gr.update(value=report, visible=True)

            except RuntimeError as error:
                message = \
f"""Error creating report:
{error}"""
                return gr.update(value=None, visible=False), \
                       gr.update(value=message, visible=True)
