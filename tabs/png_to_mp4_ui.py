"""PNG Sequence to MP4 feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, split_filepath, get_directories
from webui_utils.video_utils import PNGtoMP4 as _PNGtoMP4
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class PNGtoMP4(TabBase):
    """Encapsulates UI elements and events for the PNG Sequence to MP4 feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.png_to_mp4_settings["frame_rate"]
        max_frame_rate = self.config.png_to_mp4_settings["max_frame_rate"]
        minimum_crf = self.config.png_to_mp4_settings["minimum_crf"]
        maximum_crf = self.config.png_to_mp4_settings["maximum_crf"]
        default_crf = self.config.png_to_mp4_settings["default_crf"]
        with gr.Tab("PNG Sequence to MP4"):
            gr.Markdown(SimpleIcons.CONV_SYMBOL + "Convert a PNG sequence to a MP4")
            with gr.Row():
                input_pattern_text_pm = gr.Text(max_lines=1,
                    label="Input Filename Pattern (leave blank for auto-detection)",
                    placeholder="Example: 'pngsequence%09d.png'")
                input_frame_rate_pm = gr.Slider(value=frame_rate, minimum=1, maximum=max_frame_rate,
                    step=0.01, label="Frame Rate")
                quality_slider_pm = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                    step=1, value=default_crf, label="Quality (lower=better)")

            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    with gr.Row():
                        input_path_text_pm = gr.Text(max_lines=1, label="PNG Files Path",
                            placeholder="Path on this server to the PNG files to be converted")
                        output_path_text_pm = gr.Text(max_lines=1, label="MP4 File",
                            placeholder="Path and filename on this server for the converted MP4 file")
                    convert_button_pm = gr.Button("Convert", variant="primary")
                with gr.Tab(label="Batch Processing"):
                    with gr.Row():
                        input_path_batch = gr.Text(max_lines=1,
                            placeholder="Path on this server to the frame groups to convert",
                            label="Input Path")
                        output_path_batch = gr.Text(max_lines=1,
                            placeholder="Where to place the converted MP4 files",
                            label="Output Path")
                    convert_batch = gr.Button("Convert Batch", variant="primary")

            output_info_text_pm = gr.Textbox(label="Details", interactive=False, visible=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.png_to_mp4.render()

        convert_button_pm.click(self.convert_png_to_mp4,
            inputs=[input_path_text_pm, input_pattern_text_pm, input_frame_rate_pm,
            output_path_text_pm, quality_slider_pm], outputs=output_info_text_pm)

        convert_batch.click(self.batch_png_to_mp4,
            inputs=[input_path_batch, input_pattern_text_pm, input_frame_rate_pm,
            output_path_batch, quality_slider_pm], outputs=output_info_text_pm)

    def batch_png_to_mp4(self,
                        input_path : str,
                        input_pattern : str,
                        frame_rate : float,
                        output_path: str,
                        quality : str):
        """Convert button handler"""
        if input_path and output_path:
            create_directory(output_path)
            self.log(f"beginning batch PNGtoMP4 processing with input_path={input_path}" +\
                     f" output_path={output_path}")
            group_names = get_directories(input_path)
            self.log(f"found {len(group_names)} groups to process")

            if group_names:
                with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
                    for group_name in group_names:
                        group_input_path = os.path.join(input_path, group_name)
                        group_output_file = os.path.join(output_path, f"{group_name}.mp4")
                        global_options = self.config.ffmpeg_settings["global_options"]

                        ffmpeg_cmd = _PNGtoMP4(
                            group_input_path,
                            None,
                            float(frame_rate),
                            group_output_file,
                            crf=quality,
                            global_options=global_options)
                        self.log(f"FFmpeg command: '{ffmpeg_cmd}'")
                        Mtqdm().update_bar(bar)
                message = f"Processed {len(group_names)} frame groups found in {input_path}"
                return gr.update(value=message, visible=True)
        else:
            message = \
            "Enter an input path to the PNG frames, and an output path for the MP4 files to proceed"
            return gr.update(value=message, visible=True)

    def convert_png_to_mp4(self,
                        input_path : str,
                        input_pattern : str,
                        frame_rate : float,
                        output_filepath: str,
                        quality : str):
        """Convert button handler"""
        if input_path and output_filepath:
            directory, _, _ = split_filepath(output_filepath)
            create_directory(directory)
            global_options = self.config.ffmpeg_settings["global_options"]
            ffmpeg_cmd = _PNGtoMP4(input_path, input_pattern, float(frame_rate), output_filepath,
                crf=quality, global_options=global_options)
            return gr.update(value=ffmpeg_cmd, visible=True)
        else:
            message = "Enter an input path to the PNG frames, and an output path for the MP4 file to proceed"
            return gr.update(value=message, visible=True)
