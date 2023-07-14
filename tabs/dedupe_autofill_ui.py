"""Auto-Fill Duplicate Frames feature UI and event handlers"""
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

class AutofillFrames(TabBase):
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
        max_precision = self.config.deduplicate_settings["max_precision"]
        default_precision = self.config.deduplicate_settings["default_precision"]
        max_max_dupes = self.config.deduplicate_settings["max_max_dupes"]
        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Auto-Fill Duplicate Frames"):
            gr.Markdown(SimpleIcons.BANDAGE +\
                        "Detect and fill duplicate frames with interpolated replacements")
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
                        label="Maximum Group Size to Auto-Fill (0 = no limit, 1 = no auto-fill)")
            with gr.Row():
                precision = gr.Slider(value=default_precision, minimum=1, maximum=max_precision,
                    step=1, label="Search Precision")
            gr.Markdown("*Progress can be tracked in the console*")
            dedupe_button = gr.Button("Deduplicate Frames " + SimpleIcons.SLOW_SYMBOL,
                                        variant="primary")
            with gr.Row():
                output_text = gr.Textbox(label="Result", interactive=False, visible=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.autofill_duplicates.render()
        dedupe_button.click(self.autofill_dupe_frames, inputs=[input_path_text, output_path_text,
                                                               threshold, max_dupes, precision],
                                                        outputs=output_text)

    def autofill_dupe_frames(self,
                        input_path : str,
                        output_path : str,
                        threshold : int,
                        max_dupes : int,
                        depth : int):
        """Deduplicate Frames button handler"""
        if input_path:
            try:
                if not output_path:
                    base_output_path = self.config.directories["output_deduplication"]
                    output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

                interpolater = Interpolate(self.engine.model, self.log)
                target_interpolater = TargetInterpolate(interpolater, self.log)
                use_time_step = self.config.engine_settings["use_time_step"]
                frame_restorer = RestoreFrames(interpolater, target_interpolater, use_time_step,
                                               self.log)

                message, auto_filled_files = DeduplicateFrames(frame_restorer,
                                                               input_path,
                                                               output_path,
                                                               threshold,
                                                               max_dupes,
                                                               depth,
                                                               self.log).invoke_autofill(
                                                                suppress_output=True)
                report = self.create_autofill_report(input_path,
                                                     output_path,
                                                     threshold,
                                                     max_dupes,
                                                     depth,
                                                     message,
                                                     auto_filled_files)

                report_filepath, _ = AutoIncrementFilename(output_path, "txt").next_filename(
                                                                        "autofill-report", "txt")
                with open(report_filepath, "w", encoding="UTF-8") as file:
                    file.write(report)
                return gr.update(value=message, visible=True)

            except RuntimeError as error:
                message = \
f"""Error deduplicating frames:
{error}"""
                return gr.update(value=message, visible=True)

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

