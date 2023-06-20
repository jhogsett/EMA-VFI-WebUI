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
            gr.Markdown(SimpleIcons.WHITE_QUESTION + "Show internal details for a media file")
            with gr.Row():
                input_file = gr.Text(max_lines=1, label="Media File",
                    placeholder="Path on this server to the media file to inspect")
            with gr.Row():
                frame_rate = gr.Text(max_lines=1, label="Frame Rate")
                dimensions = gr.Text(max_lines=1, label="Dimensions")
                duration = gr.Text(max_lines=1, label="Duration")
                frame_count = gr.Text(max_lines=1, label="Frame Count")
                file_size = gr.Text(max_lines=1, label="File Size")
            count_frames = gr.Checkbox(value=True, label="Count Frames (Slower)",
                info="Scans file counting frames; required for media without frame count metadata")
            report_button = gr.Button("Get Details", variant="primary")
            output_text = gr.Textbox(label="Details", interactive=False)
            # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
            #     WebuiTips.duplicates_report.render()
        report_button.click(self.create_report, inputs=[input_file, count_frames],
                    outputs=[output_text, frame_rate, duration, dimensions, frame_count, file_size])

    def clean_dict(self, dict):
        cleaned = {}
        for k, v in dict.items():
            if v:
                cleaned[k] = v
        return cleaned

    def get_frac_str_as_float(self, fraction_string : str) -> float:
        try:
            return float(Fraction(fraction_string))
        except ZeroDivisionError:
            return 0.0

    def create_report(self, input_path : str, count_frames : bool):
        """Create Report button handler"""
        if input_path:
            if os.path.exists(input_path):
                separator = ""
                report = []

                self.log(f"calling get_video_details for {input_path}")
                data = get_video_details(input_path, count_frames=count_frames)
                self.log("received details:")
                self.log(str(data))

                error_data = data.get("error")
                if error_data:
                    report.append("ERROR: FFprobe returned an error processing the media file")
                    report.append(separator)
                    report.append("FFprobe command:")
                    report.append(error_data["ffprobe_cmd"])
                    report.append(separator)
                    report.append("Console output:")
                    report.append(error_data["console_output"])
                    return gr.update(value="\r\n".join(report)), None, None, None, None, None

                format = {}
                format_data = data["format"]
                format["filename"] = format_data.get("filename")
                format["duration"] = seconds_to_hms(float(format_data.get("duration", 0)))
                file_size = f"{int(format_data.get('size', 0)):,d}"
                format["size"] = file_size
                format["bit_rate"] = f"{int(format_data.get('bit_rate', 0)):,d}"
                format["format_name"] = format_data.get("format_long_name")
                format = self.clean_dict(format)

                warning = "Unknown"
                video_summary = {}
                streams = []
                streams_data = data["streams"]
                for stream_data in streams_data:
                    index = stream_data.get("index")
                    codec_type = stream_data.get("codec_type")
                    stream = {}

                    avg_frame_rate = stream_data.get("avg_frame_rate")
                    avg_frame_rate = self.get_frac_str_as_float(avg_frame_rate)
                    r_frame_rate = stream_data.get("r_frame_rate")
                    r_frame_rate = self.get_frac_str_as_float(r_frame_rate)
                    frame_rate = avg_frame_rate or r_frame_rate

                    frame_rate = f"{frame_rate:0.2f}" if frame_rate else warning
                    stream["frame_rate"] = frame_rate

                    duration = seconds_to_hms(float(stream_data.get("duration", 0)))
                    stream["duration"] = duration
                    stream["width"] = stream_data.get("width")
                    stream["height"] = stream_data.get("height")

                    frame_count = stream_data.get("nb_read_frames") or stream_data.get("nb_frames")
                    frame_count = f"{int(frame_count):,d}" if frame_count else warning

                    stream["frame_count"] = frame_count
                    stream["bit_rate"] = f"{int(stream_data.get('bit_rate', 0)):,d}"
                    stream["codec_name"] = stream_data.get("codec_name")
                    stream["pix_fmt"] = stream_data.get("pix_fmt")
                    stream["sample_rate"] = stream_data.get("sample_rate")
                    stream["channels"] = stream_data.get("channels")
                    stream["channel_layout"] = stream_data.get("channel_layout")

                    # capture video details from the first found video stream
                    if not video_summary and codec_type == "video":
                        video_summary["frame_rate"] = frame_rate
                        video_summary["duration"] = duration[:duration.find(".")]
                        video_summary["dimensions"] =\
                            f"{stream_data.get('width')}x{stream_data.get('height')}"
                        video_summary["frame_count"] = frame_count
                        video_summary["file_size"] = file_size

                    stream = self.clean_dict(stream)
                    stream_name = f"#{index} {codec_type}"
                    streams.append({stream_name : stream})

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

                return gr.update(value="\r\n".join(report)),\
                                 video_summary.get("frame_rate"),\
                                 video_summary.get("duration"),\
                                 video_summary.get("dimensions"),\
                                 video_summary.get("frame_count"),\
                                 video_summary.get("file_size")
            else:
                return gr.update(value=f"media file {input_path} not found"), None, None, None,\
                                                                            None, None
        else:
            return gr.update(value="media file path must be supplied"), None, None, None, None, None
