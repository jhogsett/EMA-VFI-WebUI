"""Slice Video feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from slice_video import SliceVideo as _SliceVideo

class SliceVideo(TabBase):
    """Encapsulates UI elements and events for the Slice Video feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.slice_settings["frame_rate"]
        max_frame_rate = self.config.slice_settings["max_frame_rate"]
        minimum_crf = self.config.slice_settings["minimum_crf"]
        maximum_crf = self.config.slice_settings["maximum_crf"]
        default_crf = self.config.slice_settings["default_crf"]
        maximum_gif_fps = self.config.slice_settings["maximum_gif_fps"]
        default_gif_fps = self.config.slice_settings["default_gif_fps"]
        def_scale_factor = self.config.slice_settings["def_scale_factor"]
        max_scale_factor = self.config.slice_settings["max_scale_factor"]
        with gr.Tab("Slice Video"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Summarize a split group into various formats")
            with gr.Row():
                input_path = gr.Text(max_lines=1, label="Input Media Path",
                    placeholder="Path on this server to the media file to be split")
                input_frame_rate = gr.Slider(minimum=1, maximum=max_frame_rate, value=frame_rate,
                    step=0.01, label="Input Media Frame Rate",
                    info="This must be set precisely for accurate frame cuts")
            with gr.Row():
                group_path = gr.Text(max_lines=1, label="Split Groups Path",
                    placeholder="Path on this server containing the indexed file groups",
                    info="Choose a directory that was creating using Split Frames or Split Scenes")
            with gr.Row():
                output_path = gr.Text(max_lines=1, label="Output Path",
                    placeholder="Path on this server to store summary content",
                info="Leave blank to store the sliced content directoy in the group directories")
                output_scale = gr.Slider(minimum=0.0, maximum=max_scale_factor,
                    step=0.05, value=def_scale_factor, label="Output Scale Factor",
                    info="Output frames will be downscaled by this factor")
                edge_trim = gr.Checkbox(value=False, label="Edge Trim",
                                info="Remove outer frames for resynthesized content")
            with gr.Row():
                slice_type = gr.Radio(value="mp4", choices=["mp4", "gif", "wav", "mp3", "jpg"],
                            label="Slice Type", info="See the guide for details about each type")
                mp4_quality = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                    step=1, value=default_crf, label="MP4 Quality (lower=better)")
                gif_frame_rate = gr.Slider(minimum=1, maximum=maximum_gif_fps,
                                    value=default_gif_fps, step=0.01, label="Output GIF Frame Rate")
            gr.Markdown("*Progress can be tracked in the console*")
            slice_video = gr.Button("Slice Video " + SimpleIcons.SLOW_SYMBOL, variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.slice_video.render()

        slice_video.click(self.slice_video, inputs=[input_path, input_frame_rate, group_path,
                    output_path, output_scale, slice_type, mp4_quality, gif_frame_rate, edge_trim])

    def slice_video(self,
                        input_path : str,
                        input_fps : float,
                        group_path : str,
                        output_path : str,
                        output_scale : float,
                        slice_type : str,
                        mp4_quality : int,
                        gif_frame_rate : int,
                        edge_trim : bool):
        """Slice Video button handler"""
        if input_path and group_path:
            # if compensating for video resynthesis, set edge trim to "1"
            # to leave out the (now missing) outer frames when slicing
            trim = 1 if edge_trim else 0
            _SliceVideo(input_path,
                        input_fps,
                        group_path,
                        output_path,
                        output_scale,
                        slice_type,
                        mp4_quality,
                        gif_frame_rate,
                        trim,
                        self.log).slice()
