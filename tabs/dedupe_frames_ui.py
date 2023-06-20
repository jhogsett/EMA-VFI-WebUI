"""Deduplicate Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, split_filepath
from webui_utils.video_utils import deduplicate_frames
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from deduplicate_frames import DeduplicateFrames
from webui_utils.auto_increment import AutoIncrementDirectory

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
                    label="Maximum Duplicates Per Group (0 = no limit, 1 = no duplicates allowed)")
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
                message, _, _ = DeduplicateFrames(None,
                                            input_path,
                                            output_path,
                                            threshold,
                                            max_dupes,
                                            None,
                                            self.log).invoke_delete(suppress_output=True)
                return gr.update(value=message, visible=True)

            except RuntimeError as error:
                message = \
f"""Error deduplicating frames:
{error}"""
                return gr.update(value=message, visible=True)
