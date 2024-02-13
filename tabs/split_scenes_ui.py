"""Split Scenes feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from split_scenes import SplitScenes as _SplitScenes

class SplitScenes(TabBase):
    """Encapsulates UI elements and events for the Split Scenes feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Split Scenes"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Split PNG sequences by detected scene")
            input_path = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to the PNG files to be split")
            output_path = gr.Text(max_lines=1, label="Scenes Base Path",
                placeholder="Path on this server to store the scene directories")

            with gr.Row():
                with gr.Tabs():
                    with gr.Tab(label="Split by Scene"):
                        with gr.Row():
                            scene_threshold = gr.Slider(value=0.6, minimum=0.0, maximum=1.0,
                                                        step=0.01, label="Detection Threshold",
                                info="Value between 0.0 and 1.0 (higher = fewer scenes detected)")
                        gr.Markdown("*Progress can be tracked in the console*")
                        split_scenes = gr.Button("Split Scenes " + SimpleIcons.SLOW_SYMBOL,
                                                   variant="primary")
                    with gr.Tab(label="Split by Break"):
                        with gr.Row():
                            break_duration = gr.Slider(value=2.0, minimum=0.0, maximum=30.0,
                                                       step=0.25, label="Minimum Duration",
                                                       info="Choose a duration in seconds")
                            break_ratio = gr.Slider(value=0.98, minimum=0.0, maximum=1.0, step=0.01,
                            label="Black Frame Ratio", info="Choose a value between 0.0 and 1.0")
                        gr.Markdown("*Progress can be tracked in the console*")
                        split_breaks = gr.Button("Split Breaks " + SimpleIcons.SLOW_SYMBOL,
                                                   variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.split_scenes.render()

        split_scenes.click(self.split_scenes, inputs=[input_path, output_path, scene_threshold])

        split_breaks.click(self.split_breaks, inputs=[input_path, output_path, break_duration,
                                                      break_ratio])

    def split_scenes(self,
                        input_path : str,
                        output_path : str,
                        scene_threshold : float):
        """Split Scenes button handler"""
        if input_path and output_path:
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                _SplitScenes(
                    input_path,
                    output_path,
                    "png",
                    "scene",
                    float(scene_threshold),
                    0.0,
                    0.0,
                    self.log).split()
                Mtqdm().update_bar(bar)

    def split_breaks(self,
                        input_path : str,
                        output_path : str,
                        break_duration : float,
                        break_ratio : float):
        """Split Breaks button handler"""
        if input_path and output_path:
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                _SplitScenes(
                    input_path,
                    output_path,
                    "png",
                    "break",
                    0.0,
                    float(break_duration),
                    float(break_ratio),
                    self.log).split()
                Mtqdm().update_bar(bar)
