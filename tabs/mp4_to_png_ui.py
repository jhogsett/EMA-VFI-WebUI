"""GIF to PNG Sequence feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory
from webui_utils.video_utils import MP4toPNG as _MP4toPNG
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class MP4toPNG(TabBase):
    """Encapsulates UI elements and events for the MP4 to PNG Sequence feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.mp4_to_png_settings["frame_rate"]
        max_frame_rate = self.config.mp4_to_png_settings["max_frame_rate"]
        with gr.Tab("MP4 to PNG Sequence"):
            gr.Markdown(SimpleIcons.CONV_SYMBOL + "Convert Video Media to a PNG sequence")
            input_path_text_mp = gr.Text(max_lines=1, label="MP4 File (MOV and others work too)",
                placeholder="Path on this server to the media file to be converted")
            output_path_text_mp = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to a directory for the converted PNG files")
            with gr.Row():
                output_pattern_text_mp = gr.Text(max_lines=1,
                    label="Output Filename Pattern (leave blank for auto-detection)",
                    placeholder="Example: 'pngsequence%09d.png'")
                input_frame_rate_mp = gr.Slider(minimum=1, maximum=max_frame_rate, value=frame_rate,
                    step=0.01, label="Frame Rate")
            with gr.Row():
                deinterlace = gr.Checkbox(value=False, label="Deinterlace Frames",
                            info="Removes the 'combing' effect present in some broadcast content")
            with gr.Row():
                convert_button_mp = gr.Button("Convert", variant="primary")
                output_info_text_mp = gr.Textbox(label="Details", interactive=False)
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.mp4_to_png.render()
        convert_button_mp.click(self.convert_mp4_to_png,
            inputs=[input_path_text_mp, output_pattern_text_mp, input_frame_rate_mp,
                output_path_text_mp, deinterlace], outputs=output_info_text_mp)

    def convert_mp4_to_png(self,
                        input_filepath : str,
                        output_pattern : str,
                        frame_rate : int,
                        output_path : str,
                        deinterlace : bool):
        """Convert button handler"""
        if input_filepath and output_path:
            create_directory(output_path)
            self.log("using MP4toPNG (may cause long delay while counting frames)")
            global_options = self.config.ffmpeg_settings["global_options"]
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                ffmpeg_cmd = _MP4toPNG(input_filepath,
                                    output_pattern,
                                    float(frame_rate),
                                    output_path,
                                    deinterlace=deinterlace,
                                    global_options=global_options)
                Mtqdm().update_bar(bar)
            return gr.update(value=ffmpeg_cmd, visible=True)
