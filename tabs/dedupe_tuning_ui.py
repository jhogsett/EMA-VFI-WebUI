"""Duplicate Tuning feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.video_utils import get_duplicate_frames_report
# from webui_tips import WebuiTips
from webui_utils.auto_increment import AutoIncrementDirectory
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from deduplicate_frames import DeduplicateFrames

class DuplicateTuning(TabBase):
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
        threshold_step = self.config.deduplicate_settings["threshold_step"]
        min_tuning_step = self.config.deduplicate_settings["min_tuning_step"]
        max_tuning_step = self.config.deduplicate_settings["max_tuning_step"]
        tuning_step_step = self.config.deduplicate_settings["tuning_step_step"]
        default_tuning_step = self.config.deduplicate_settings["default_tuning_step"]
        def_max_dupes = self.config.deduplicate_settings["max_dupes_per_group"]
        max_max_dupes = self.config.deduplicate_settings["max_max_dupes"]
        max_rows = self.config.deduplicate_settings["max_tuning_rows"]
        with gr.Tab("Duplicate Threshold Tuning"):
            gr.Markdown(SimpleIcons.STETHOSCOPE +\
                "Detect duplicates across a series of Detection Thresholds")
            with gr.Row():
                input_path_text = gr.Text(max_lines=1, label="Input PNG Files Path",
                    placeholder="Path on this server to the PNG files to be reported on")
            with gr.Row():
                tune_min = gr.Slider(value=min_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step,
                    label="Starting Detection Threshold")
                tune_max = gr.Slider(value=max_threshold, minimum=min_threshold,
                    maximum=max_threshold, step=threshold_step,
                    label="Ending Detection Threshold")
                tune_step = gr.Slider(value=default_tuning_step, minimum=min_tuning_step,
                    maximum=max_tuning_step, step=tuning_step_step,
                    label="Detection Threshold Increase Step")
            with gr.Row():
                max_dupes = gr.Slider(value=def_max_dupes, minimum=0, maximum=max_max_dupes, step=1,
                    label="Maximum Duplicates Per Group (0 = no limit, 1 = no duplicates allowed)")
            with gr.Row():
                report_button = gr.Button("Create Report", variant="primary")
            with gr.Row():
                file_output = gr.File(type="file", file_count="multiple", label="Download",
                                      visible=False)
                error_output = gr.Text(max_lines=1, label="Error", visible=False)
            with gr.Row():
                output_frame = gr.DataFrame(value=None, max_rows=max_rows, interactive=False,
                                            label="Tuning Report")
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.duplicates_report.render()
        report_button.click(self.create_report,
                inputs=[input_path_text, max_dupes, tune_min, tune_max, tune_step],
                outputs=[file_output, output_frame, error_output])

    def create_report(self,
                        input_path : str,
                        max_dupes : int,
                        min_threshold : int,
                        max_threshold : int,
                        threshold_step : int):
        """Create Report button handler"""
        if input_path and max_threshold > min_threshold and threshold_step:
            base_output_path = self.config.directories["output_deduplication"]
            output_path, run_index = AutoIncrementDirectory(base_output_path).next_directory(
                "run")
            output_basename = "duplicate_tuning_report"
            output_filepath = os.path.join(output_path, output_basename + ".csv")
            self.log(f"creating duplicate tuning report at {output_filepath}")
            try:
                tuning_data = DeduplicateFrames(None,
                                            input_path,
                                            output_filepath,
                                            0,
                                            max_dupes,
                                            None,
                                            self.log,
                                            tune_min=min_threshold,
                                            tune_max=max_threshold,
                                            tune_step=threshold_step).invoke_tuning(
                    suppress_output=True)
                report = str(tuning_data)
                return gr.update(value=[output_filepath], visible=True), \
                    gr.update(value=output_filepath, visible=True), \
                    gr.update(value=None, visible=False)

            except RuntimeError as error:
                message = str(error)
                return gr.update(value=None, visible=False),\
                    gr.update(value=None, visible=False), \
                    gr.update(value=message, visible=True)
        else:
            message =\
            "To proceed, ensure: an input path was entered, threshold max > min, threshold step > 0"
            return gr.update(value=None, visible=False),\
                gr.update(value=None, visible=False), \
                gr.update(value=message, visible=True)
