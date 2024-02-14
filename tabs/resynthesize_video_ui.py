"""Resynthesize Video feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown
from webui_utils.file_utils import create_directory, get_files, get_directories, is_safe_path, \
    remove_directories
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from tabs.tab_base import TabBase

class ResynthesizeVideo(TabBase):
    """Encapsulates UI elements and events for the Resynthesize Video feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Resynthesize Video to: Create interpolated replacement frames"
    DEFAULT_MESSAGE_BATCH = \
    "Click Resynthesize Batch to: Create interpolated replacement frames for each batch directory"

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Resynthesize Video"):
            gr.HTML(SimpleIcons.TWO_HEARTS +
                "Interpolate replacement frames from an entire video for use in movie restoration",
                elem_id="tabheading")
            resynth_type = gr.Radio(choices=["One Pass", "Two Pass"], value="One Pass",
                                    label="Resynthesis Type",
            info="One Pass Resynthesis is faster, Two Pass Resynthesis is better with fast motion")
            with gr.Tabs():
                with gr.Tab(label="Individual Path"):
                    with gr.Row():
                        input_path_text = gr.Text(max_lines=1, label="Input Path",
                        placeholder="Path on this server to the frame PNG files to resynthesize")
                        output_path_text = gr.Text(max_lines=1, label="Output Path",
                            placeholder="Where to place the resynthesized PNG frames",
                            info="Leave blank to use default path")
                    message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                    gr.Markdown("*Progress can be tracked in the console*")
                    resynthesize_button = gr.Button("Resynthesize Video " +
                                                       SimpleIcons.SLOW_SYMBOL, variant="primary")
                with gr.Tab(label="Batch Processing"):
                    with gr.Row():
                        input_path_batch = gr.Text(max_lines=1,
                            placeholder="Path on this server to the frame groups to resynthesize",
                            label="Input Path")
                        output_path_batch = gr.Text(max_lines=1,
                            placeholder="Where to place the resynthesized frame groups",
                            label="Output Path")
                    message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                    gr.Markdown("*Progress can be tracked in the console*")
                    resynthesize_batch = gr.Button("Resynthesize Batch " +
                                                       SimpleIcons.SLOW_SYMBOL, variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.resynthesize_video.render()

        resynthesize_button.click(self.resynthesize_video,
            inputs=[input_path_text, output_path_text, resynth_type],
            outputs=message_box_single)

        resynthesize_batch.click(self.resynthesize_batch,
            inputs=[input_path_batch, output_path_batch, resynth_type],
            outputs=message_box_batch)

    def resynthesize_batch(self, input_path : str, output_path : str | None, resynth_type : str):
        """Resynthesize Video button handler"""
        if not input_path:
            return format_markdown("Please enter an input path to begin", "warning")
        if not os.path.exists(input_path):
            return format_markdown(f"The input path {input_path} was not found", "error")
        if not is_safe_path(input_path):
            return format_markdown(f"The input path {input_path} is not valid", "error")

        group_names = get_directories(input_path)
        if not group_names:
            return format_markdown(f"No directories were found at the input path {input_path}",
                                   "error")

        self.log(f"beginning batch ResynthesizeVideo processing with input_path={input_path}" +\
                    f" output_path={output_path}")
        self.log(f"found {len(group_names)} groups to process")

        if output_path:
            if not is_safe_path(output_path):
                return format_markdown(f"The output path {output_path} is not valid", "error")
            self.log(f"creating group output path {output_path}")
            create_directory(output_path)
        else:
            base_output_path = self.config.directories["output_resynthesis"]
            output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

        errors = []
        with Mtqdm().open_bar(total=len(group_names), desc="Frame Group") as bar:
            for group_name in group_names:
                group_input_path = os.path.join(input_path, group_name)
                group_output_path = os.path.join(output_path, group_name)
                try:
                    self.resynthesize_video(group_input_path, group_output_path,
                                            resynth_type=resynth_type, interactive=False)
                except ValueError as error:
                    errors.append(f"Error handling directory {group_name}: " + str(error))
                Mtqdm().update_bar(bar)
        if errors:
            message = "\r\n".join(errors)
            return format_markdown(message, "error")
        else:
            message = f"Batch processed resynthesized frames saved to {os.path.abspath(output_path)}"
            return format_markdown(message)

    def one_pass_resynthesis(self, input_path, output_path, output_basename, engine):
        file_list = sorted(get_files(input_path, extension="png"))
        self.log(f"beginning series of frame recreations at {output_path}")
        engine.interpolate_series(file_list, output_path, 1, "interframe", offset=2)

        self.log(f"auto-resequencing recreated frames at {output_path}")
        ResequenceFiles(output_path, "png", "resynthesized_frame", 1, 1, 1, 0, -1, True,
                        self.log).resequence()

    def two_pass_resynthesis(self, input_path, output_path, output_basename, engine):
        interframes_path1 = os.path.join(output_path, "interframes-pass1")
        interframes_path2 = os.path.join(output_path, "interframes-pass2")
        interframes_path3 = os.path.join(output_path, "interframes-final")
        create_directory(interframes_path1)
        create_directory(interframes_path2)
        create_directory(interframes_path3)

        with Mtqdm().open_bar(total=2, desc="Two-Pass Resynthesis") as bar:
            file_list = sorted(get_files(input_path, extension="png"))
            self.log(f"beginning pass #1 of series of frame recreations at {interframes_path1}")
            engine.interpolate_series(file_list, interframes_path1, 1, "interframe")

            self.log(f"selecting odd interframes only at {interframes_path1}")
            ResequenceFiles(interframes_path1,
                            "png",
                            "odd_interframe",
                            1, 1, # start, step
                            2, 1, # stride, offset
                            -1,   # auto-zero fill
                            False, # rename
                            self.log,
                            output_path=interframes_path2).resequence()
            Mtqdm().update_bar(bar)

            file_list = sorted(get_files(interframes_path2, extension="png"))
            self.log(f"beginning pass #2 of series of frame recreations at {interframes_path2}")
            engine.interpolate_series(file_list, interframes_path3, 1, "interframe")

            self.log(f"selecting odd interframes only at {interframes_path3}")
            ResequenceFiles(interframes_path3,
                            "png",
                            output_basename,
                            1, 1, # start, step
                            2, 1, # stride, offset
                            -1,   # auto-zero fill
                            False, # rename
                            self.log,
                            output_path=output_path).resequence()
            Mtqdm().update_bar(bar)
            remove_directories([interframes_path1, interframes_path2, interframes_path3])

    def resynthesize_video(self, input_path : str, output_path : str | None, resynth_type : str,
                           interactive : bool=True):
        """Resynthesize Video button handler"""
        if not input_path:
            if interactive:
                return format_markdown("Please enter an input path to begin", "warning")
            else:
                raise ValueError(f"The input path is empty")
        if not os.path.exists(input_path):
            message = f"The input path {input_path} was not found"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)
        if not is_safe_path(input_path):
            message = f"The input path {input_path} is not valid"
            if interactive:
                return format_markdown(message, "error")
            else:
                raise ValueError(message)

        if output_path:
            if not is_safe_path(output_path):
                message = f"The output path {output_path} is not valid"
                if interactive:
                    return format_markdown(message, "error")
                else:
                    raise ValueError(f"The output path {input_path} is not valid")
            self.log(f"creating output path {output_path}")
            create_directory(output_path)
        else:
            base_output_path = self.config.directories["output_resynthesis"]
            output_path, _ = AutoIncrementDirectory(base_output_path).next_directory("run")

        interpolater = Interpolate(self.engine.model, self.log)
        use_time_step = self.config.engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
        series_interpolater = InterpolateSeries(deep_interpolater, self.log)
        output_basename = "resynthesized_frames"

        if resynth_type.lower().startswith("one"):
            self.one_pass_resynthesis(input_path, output_path, output_basename, series_interpolater)
        else:
            self.two_pass_resynthesis(input_path, output_path, output_basename, series_interpolater)

        message = f"Resynthesized frames saved to {os.path.abspath(output_path)}"
        if interactive:
            return format_markdown(message)
        else:
            self.log(message)
