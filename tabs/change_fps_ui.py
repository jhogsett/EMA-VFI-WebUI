"""Change FPS feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.simple_utils import fps_change_details, is_power_of_two, power_of_two_precision
from webui_utils.ui_utils import update_info_fc
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from resample_series import ResampleSeries
from resequence_files import ResequenceFiles as _ResequenceFiles
from tabs.tab_base import TabBase

class ChangeFPS(TabBase):
    """Encapsulates UI elements and events for the Change FPS feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        max_fps = self.config.fps_change_settings["maximum_fps"]
        starting_fps = self.config.fps_change_settings["starting_fps"]
        ending_fps = self.config.fps_change_settings["ending_fps"]
        max_precision = self.config.fps_change_settings["max_precision"]
        precision = self.config.fps_change_settings["default_precision"]
        lowest_common_rate, filled, sampled, fractions, predictions\
            = fps_change_details(starting_fps, ending_fps, precision)
        with gr.Tab("Change FPS"):
            gr.HTML(SimpleIcons.FILM +
                "Change the frame rate for a set of PNG video frames using frame search",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    with gr.Row():
                        input_path_text_fc = gr.Text(max_lines=1, label="Input Path",
                        placeholder="Path on this server to the PNG frame files to be converted")
                        output_path_text_fc = gr.Text(max_lines=1, label="Output Path",
                            placeholder="Path on this server for the converted frame files, " +
                                "leave blank to use default path")
                    with gr.Row():
                        starting_fps_fc = gr.Slider(value=starting_fps, minimum=1, maximum=max_fps,
                            step=1, label="Starting FPS")
                        ending_fps_fc = gr.Slider(value=ending_fps, minimum=1, maximum=max_fps,
                            step=1, label="Ending FPS")
                        output_lcm_text_fc = gr.Text(value=lowest_common_rate, max_lines=1,
                            label="Lowest Common FPS", interactive=False)
                        output_filler_text_fc = gr.Text(value=filled, max_lines=1,
                            label="Filled Frames per Input Frame", interactive=False)
                        output_sampled_text_fc = gr.Text(value=sampled, max_lines=1,
                            label="Output Frames Sample Rate", interactive=False)
                    with gr.Row():
                        precision_fc = gr.Slider(value=precision, minimum=1, maximum=max_precision,
                            step=1, label="Precision")
                        times_output_fc = gr.Textbox(value=fractions, label="Frame Search Times",
                            max_lines=8, interactive=False)
                        predictions_output_fc = gr.Textbox(value=predictions,
                            label="Predicted Matches", max_lines=8, interactive=False)
            gr.Markdown("*Progress can be tracked in the console*")
            convert_button_fc = gr.Button("Convert " + SimpleIcons.SLOW_SYMBOL, variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.change_fps.render()
        starting_fps_fc.change(update_info_fc,
            inputs=[starting_fps_fc, ending_fps_fc, precision_fc],
            outputs=[output_lcm_text_fc, output_filler_text_fc, output_sampled_text_fc,
                times_output_fc, predictions_output_fc], show_progress=False)
        ending_fps_fc.change(update_info_fc, inputs=[starting_fps_fc, ending_fps_fc, precision_fc],
            outputs=[output_lcm_text_fc, output_filler_text_fc, output_sampled_text_fc,
                times_output_fc, predictions_output_fc], show_progress=False)
        precision_fc.change(update_info_fc, inputs=[starting_fps_fc, ending_fps_fc, precision_fc],
            outputs=[output_lcm_text_fc, output_filler_text_fc, output_sampled_text_fc,
                times_output_fc, predictions_output_fc], show_progress=False)
        convert_button_fc.click(self.convert_fc, inputs=[input_path_text_fc, output_path_text_fc,
            starting_fps_fc, ending_fps_fc, precision_fc])

    def convert_fc(self,
                    input_path : str,
                    output_path : str,
                    starting_fps : int,
                    ending_fps : int,
                    precision : int):
        """Change FPS convert button handler"""
        if input_path:
            interpolater = Interpolate(self.engine.model, self.log)
            target_interpolater = TargetInterpolate(interpolater, self.log)
            series_resampler = ResampleSeries(target_interpolater, self.log)
            if output_path:
                base_output_path = output_path
                create_directory(base_output_path)
            else:
                base_output_path, _ = AutoIncrementDirectory(
                    self.config.directories["output_fps_change"]).next_directory("run")

            # when the fill-factor is a power of two, override the user value for precision
            # because the computed value will always be the most efficient
            _, filled, _, _, _ = fps_change_details(starting_fps, ending_fps, precision)
            expansion = filled + 1
            if is_power_of_two(expansion):
                new_precision = power_of_two_precision(expansion)
                self.log(
                f"overriding user precision {precision} with efficient precision {new_precision}")
                precision = new_precision

            series_resampler.resample_series(input_path, base_output_path, starting_fps,
                ending_fps, precision, f"resampled@{starting_fps}")

            self.log(f"auto-resequencing sampled frames at {output_path}")
            _ResequenceFiles(base_output_path, "png", f"resampled@{ending_fps}fps", 0, 1, -1, True,
                 self.log).resequence()
