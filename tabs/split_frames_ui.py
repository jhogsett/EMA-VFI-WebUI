"""Split Frames feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from split_frames import SplitFrames as _SplitFrames
from webui_utils.auto_increment import AutoIncrementFilename

class SplitFrames(TabBase):
    """Encapsulates UI elements and events for the Split Frames feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Split Frames"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Split large PNG sequences into processable chunks")
            input_path = gr.Text(max_lines=1, label="PNG Files Path",
                placeholder="Path on this server to the PNG files to be split")
            output_path = gr.Text(max_lines=1, label="Split Groups Base Path",
                placeholder="Path on this server to store the split file group directories")
            with gr.Row():
                num_groups = gr.Slider(value=10, minimum=2, maximum=1000,
                                       label="Number of Split Groups")
                max_files = gr.Number(value=0, label="Maximum Files Per Group (0 = no limit)",
                        precision=0, info="If set, group count set automatically")
            with gr.Row():
                split_type = gr.Radio(value="Precise", label="Split Type",
                                      choices=["Precise", "Resynthesis", "Inflation"],
            info="Choose 'Resynthesis' or 'Inflation' if split groups will be processed further")
                action_type = gr.Radio(value="Copy", label="Files Action", choices=["Copy", "Move"],
                        info="Choose 'Move' to delete source files after successful split")
            split_button = gr.Button("Split Frames", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.split_frames.render()
        split_button.click(self.split_frames,
            inputs=[input_path, output_path, num_groups, max_files, split_type, action_type])

    def split_frames(self,
                        input_path : str,
                        output_path : str,
                        num_groups : int,
                        max_files : int,
                        split_type : str,
                        action_type : str):
        """Split button handler"""
        if input_path and output_path:
            group_paths = _SplitFrames(
                input_path,
                output_path,
                "png",
                split_type.lower(),
                num_groups,
                max_files,
                action_type.lower(),
                False, self.log).split()

            report = self.create_split_report(input_path,
                                              output_path,
                                              split_type,
                                              num_groups,
                                              max_files,
                                              action_type,
                                              group_paths)

            report_filepath, _ = AutoIncrementFilename(output_path, "txt").next_filename(
                                                                    "split-frames-report", "txt")
            with open(report_filepath, "w", encoding="UTF-8") as file:
                file.write(report)

    def create_split_report(self,
                            input_path : str,
                            output_path : str,
                            split_type : str,
                            num_groups : str,
                            max_files : str,
                            action_type,
                            group_paths):
        report = []
        report.append("[Split Frames Report]")
        report.append(f"input path: {input_path}")
        report.append(f"output path: {output_path}")
        report.append(f"split type: {split_type}")
        report.append(f"num groups: {num_groups}")
        report.append(f"max files: {max_files}")
        report.append(f"action type: {action_type}")
        report.append("")
        report.append("[Split Group Directories]")
        report += group_paths
        return "\r\n".join(report)
