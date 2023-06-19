"""Video Details feature UI and event handlers"""
import os
from fractions import Fraction
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hms
from webui_utils.video_utils import get_video_details
# from webui_tips import WebuiTips
from webui_utils.auto_increment import AutoIncrementDirectory
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class VideoDetails(TabBase):
    """Encapsulates UI elements and events for the Video Details feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Video Details"):
            gr.Markdown(SimpleIcons.EYES + "Show internal details for a media file")
            with gr.Row():
                input_file = gr.Text(max_lines=1, label="Media File",
                    placeholder="Path on this server to the media file to inspect")
            with gr.Row():
                report_button = gr.Button("Get Details", variant="primary")
            with gr.Row():
                output_text = gr.Textbox(label="Report", interactive=False)
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.duplicates_report.render()
        report_button.click(self.create_report, inputs=input_file, outputs=output_text)

    def clean_dict(self, dict):
        cleaned = {}
        for k, v in dict.items():
            if v:
                cleaned[k] = v
        return cleaned

    def create_report(self, input_path : str):
        """Create Report button handler"""
        if input_path:
            if os.path.exists(input_path):
                self.log(f"calling get_video_details for {input_path}")
                data = get_video_details(input_path)
                self.log("received details:")
                self.log(str(data))

                format = {}
                format_data = data["format"]
                format["filename"] = format_data.get("filename")
                format["duration"] = seconds_to_hms(float(format_data.get("duration", 0)))
                format["size"] = f"{int(format_data.get('size', 0)):,d}"
                format["bit_rate"] = f"{int(format_data.get('bit_rate', 0)):,d}"
                format["format_name"] = format_data.get("format_long_name")
                format = self.clean_dict(format)

                streams = []
                streams_data = data["streams"]
                for stream_data in streams_data:
                    stream = {}
                    avg_frame_rate = stream_data.get("avg_frame_rate")
                    if avg_frame_rate:
                        try:
                            stream["frame_rate"] = f"{float(Fraction(avg_frame_rate)):0.2f}"
                        except ZeroDivisionError:
                            pass
                    stream["duration"] = seconds_to_hms(float(stream_data.get("duration", 0)))
                    stream["width"] = stream_data.get("width")
                    stream["height"] = stream_data.get("height")
                    stream["frame_count"] = stream_data.get("nb_read_frames")
                    stream["bit_rate"] = f"{int(stream_data.get('bit_rate', 0)):,d}"
                    stream["codec_name"] = stream_data.get("codec_name")
                    stream["pix_fmt"] = stream_data.get("pix_fmt")
                    stream["sample_rate"] = stream_data.get("sample_rate")
                    stream["channels"] = stream_data.get("channels")
                    stream["channel_layout"] = stream_data.get("channel_layout")
                    stream = self.clean_dict(stream)

                    index = stream_data.get("index")
                    codec_type = stream_data.get("codec_type")
                    stream_name = f"#{index} {codec_type}"
                    streams.append({stream_name : stream})

                separator = ""
                report = []
                report.append("[Format]")
                for k, v in format.items():
                    report.append(f"{k}: {v}")
                report.append(separator)

                for stream in streams:
                    stream_name = list(stream.keys())[0]
                    stream_data = list(stream.values())[0]
                    report.append(f"[Stream {stream_name}]")
                    for k, v in stream_data.items():
                        report.append(f"{k}: {v}")
                    report.append(separator)
                return gr.update(value="\r\n".join(report))
            else:
                return gr.update(value=f"media file {input_path} not found")
        else:
            return gr.update(value="media file path must be supplied")
