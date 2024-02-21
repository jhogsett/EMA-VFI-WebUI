"""Change FPS feature UI and event handlers"""
import os
import math
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files, split_filepath, is_safe_path
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.video_utils import GIFtoPNG, PNGtoMP4, get_essential_video_details, combine_videos
from webui_utils.simple_utils import is_power_of_two, format_markdown
from webui_tips import WebuiTips
from webui_utils.mtqdm import Mtqdm
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resample_series import ResampleSeries
from resequence_files import ResequenceFiles as _ResequenceFiles
from upscale_series import UpscaleSeries
from tabs.tab_base import TabBase

class GIFtoMP4(TabBase):
    """Encapsulates UI elements and events for the GIF to MP4 feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    DEFAULT_MESSAGE_SINGLE = "Click Convert to: Create a MP4 video for the specified GIF/video"
    DEFAULT_MESSAGE_BATCH = "Click Convert Batch to: Create MP4 videos for GIF files/videos at the input path"

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.gif_to_mp4_settings["frame_rate"]
        max_frame_rate = self.config.gif_to_mp4_settings["max_frame_rate"]
        minimum_crf = self.config.gif_to_mp4_settings["minimum_crf"]
        maximum_crf = self.config.gif_to_mp4_settings["maximum_crf"]
        default_crf = self.config.gif_to_mp4_settings["default_crf"]
        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "GIF to MP4"):
            gr.HTML(SimpleIcons.PLAY +
                "Turn an Animated GIF Into a MP4 video",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    upscale_input = gr.Slider(value=4.0, minimum=1.0, maximum=8.0, step=0.05,
                        label="Input Frame Size Upscale Factor")
                    inflation_input = gr.Slider(value=4.0, minimum=1.0, maximum=16.0, step=1.0,
                        label="Input Frame Rate Inflation Factor")
                    order_input = gr.Radio(value="Inflate Rate, then Upscale Size",
            choices=["Inflate Rate, then Upscale Size", "Upscale Size, then Inflate Rate"],
                        label="Processing Sequence",
                        info="Upscaling size first may be faster with a high inflation factor")
                with gr.Column():
                    input_frame_rate = gr.Slider(minimum=1, maximum=max_frame_rate,
                                            value=frame_rate, step=0.01, label="MP4 Frame Rate")
                    quality_slider = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                        step=1, value=default_crf, label="Quality (lower=better)")
                    min_duration = gr.Number(value=10, precision=0, label="Minimum Video Duration (seconds)",
                                            info="Loop video if needed")
            with gr.Row():
                with gr.Tabs():
                    with gr.Tab(label="Individual File"):
                        input_path_text = gr.Text(max_lines=1,
                            label="GIF File (MP4 and others work too)",
                        placeholder="Path on this server to the GIF or MP4 file to be converted")
                        output_path_text = gr.Text(max_lines=1, label="MP4 File",
                            placeholder="Path on this server for the converted video, " +
                                "leave blank to save to the input path")
                        message_box_single = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_SINGLE))
                        gr.Markdown("*Progress can be tracked in the console*")
                        convert_button = gr.Button("Convert " + SimpleIcons.SLOW_SYMBOL,
                                                   variant="primary")
                    with gr.Tab(label="Batch Processing"):
                        input_path_text_batch = gr.Text(max_lines=1,
                            label="Path to GIF Files (MP4 and others work too)",
                placeholder="Path on this server to the set of GIF or MP4 files to be converted")
                        output_path_text_batch = gr.Text(max_lines=1, label="Output Path",
                            placeholder="Path on this server for the converted videos, " +
                                "leave blank to save to the input path")
                        message_box_batch = gr.Markdown(format_markdown(self.DEFAULT_MESSAGE_BATCH))
                        gr.Markdown("*Progress can be tracked in the console*")
                        convert_button_batch = gr.Button("Convert Batch " + SimpleIcons.SLOW_SYMBOL,
                                                         variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.gif_to_mp4.render()

        convert_button.click(self.convert,
                             inputs=[input_path_text, output_path_text,upscale_input,
                                     inflation_input, order_input, input_frame_rate,
                                     quality_slider, min_duration],
                            outputs=message_box_single)

        convert_button_batch.click(self.convert_batch_gm,
                                   inputs=[input_path_text_batch, output_path_text_batch,
                                           upscale_input, inflation_input, order_input,
                                           input_frame_rate, quality_slider, min_duration],
                                    outputs=message_box_batch)

    def convert(self,
                input_path : str,
                output_path : str,
                upscaling : float,
                inflation : float,
                order : str,
                frame_rate : float,
                quality : int,
                min_duration : int):
        """Convert button handler"""
        if not input_path:
            return format_markdown("Please enter an input path to begin", "warning")
        if not os.path.exists(input_path):
            return format_markdown(f"The input path {input_path} was not found", "error")
        if not is_safe_path(input_path):
            return format_markdown(f"The input path {input_path} is not valid", "error")
        if output_path and not is_safe_path(output_path):
            return format_markdown(f"The output path {output_path} is not valid", "error")

        filename = None
        if output_path:
            path, filename, ext = split_filepath(output_path)
            if ext:
                # if a filename was specified, use it and adjust the output path
                output_path = path
                filename = filename + ext
            create_directory(output_path)

        with Mtqdm().open_bar(total=1, desc="Converting") as bar:
            try:
                created_file = self._convert(input_path,
                                             output_path,
                                             filename,
                                             upscaling,
                                             inflation,
                                             order,
                                             frame_rate,
                                             quality,
                                             min_duration)
            except ValueError as error:
                return format_markdown(f"Error: {error}", "error")
            finally:
                Mtqdm().update_bar(bar)

        return format_markdown(f"The video {created_file} has been created")

    def convert_batch_gm(self,
                input_path : str,
                output_path : str,
                upscaling : float,
                inflation : float,
                order : str,
                frame_rate : float,
                quality : int,
                min_duration : int):
        """Convert Batch button handler"""
        if not input_path:
            return format_markdown("Please enter an input path to begin", "warning")
        if not os.path.exists(input_path):
            return format_markdown(f"The input path {input_path} was not found", "error")
        if not is_safe_path(input_path):
            return format_markdown(f"The input path {input_path} is not valid", "error")

        if output_path:
            if not is_safe_path(output_path):
                return format_markdown(f"The output path {output_path} is not valid", "error")

            _, _, ext = split_filepath(output_path)
            if ext:
                return format_markdown("The output path must specify a directory", "warning")

            create_directory(output_path)

        file_types = ",".join(self.config.gif_to_mp4_settings["file_types"])
        self.log(f"beginning GIF-to-MP4 batch processing at {input_path}")
        file_list = get_files(input_path, file_types)
        self.log(f"GIF-to-MP4 batch processing found {len(file_list)} files")

        num_files = len(file_list)
        if num_files == 0:
            return format_markdown("No processable files at the input path", "warning")

        errors = []
        with Mtqdm().open_bar(total=len(file_list), desc="Converting") as bar:
            for filepath in file_list:
                try:
                    self._convert(filepath,
                                  output_path,
                                  None,
                                  upscaling,
                                  inflation,
                                  order,
                                  frame_rate,
                                  quality,
                                  min_duration)
                except Exception as error:
                    errors.append(str(error))
                Mtqdm().update_bar(bar)

        if errors:
            message = "\r\n".join(errors)
            return format_markdown(f"Errors during processing:\r\n{message}", "error")

        return format_markdown(f"Videos have been created at {output_path or input_path}")

    def _convert(self,
                input_filepath : str,
                output_path : str,
                output_filename : str,
                upscaling : float,
                inflation : float,
                order : str,
                frame_rate : float,
                quality : int,
                min_duration : int):
        """Convert base handler"""
        working_path, _ = AutoIncrementDirectory(
            self.config.directories["output_gif_to_mp4"]).next_directory("run")
        precision = self.config.gif_to_mp4_settings["resampling_precision"]
        size_first = order[0].lower() == "u"
        if size_first:
            self.log("upscaling size first, then inflating rate")
        else:
            self.log("inflating rate first, the upscaling size")

        frames_path = os.path.join(working_path, "1-gif_to_png")
        create_directory(frames_path)
        self.convert_gif_to_png_frames(input_filepath, frames_path)

        if size_first:
            upscaled_path = os.path.join(working_path, "2-png_to_upscaled")
            create_directory(upscaled_path)
            self.upscale_png_frames_to_path(frames_path, upscaled_path, upscaling)

            inflated_path = os.path.join(working_path, "3-upscaled_to_inflated")
            create_directory(inflated_path)
            self.inflate_png_frames_to_path(upscaled_path, inflated_path, inflation, precision)
            frames_path = inflated_path
        else:
            inflated_path = os.path.join(working_path, "2-png_to_inflated")
            create_directory(inflated_path)
            self.inflate_png_frames_to_path(frames_path, inflated_path, inflation, precision)

            upscaled_path = os.path.join(working_path, "3-inflated_to_upscaled")
            create_directory(upscaled_path)
            self.upscale_png_frames_to_path(inflated_path, upscaled_path, upscaling)
            frames_path = upscaled_path

        path, filename, _ = split_filepath(input_filepath)
        if not output_filename:
            output_filename = f"{filename}-up{upscaling}-in{inflation}.mp4"
        if not output_path:
            output_path = path
        output_filepath = os.path.join(output_path, output_filename)

        self.convert_png_frames_to_mp4(frames_path, output_filepath, frame_rate, quality)

        if min_duration > 0:
            video_details = get_essential_video_details(output_filepath)
            duration = video_details["duration_float"]
            self.log(f"converted video duration is {duration} seconds")
            if duration < min_duration:
                self.log(f"looping video to meet minimum duration of {min_duration} seconds")

                loop_filepath = os.path.join(output_path, "LOOP-" + output_filename)
                self.log(f"loop_filepath is {loop_filepath}")
                os.replace(output_filepath, loop_filepath)

                loop_times = math.ceil(min_duration / duration)
                self.log(f"looping {loop_times} times")

                loop_list = [loop_filepath for n in range(loop_times)]
                global_options = self.config.ffmpeg_settings["global_options"]
                combine_videos(loop_list, output_filepath, global_options=global_options)
                os.remove(loop_filepath)

        return output_filepath

    def convert_gif_to_png_frames(self, gif_path : str, png_path : str):
        """Use GIFtoPNG to convert to a PNG sequence"""
        self.log(f"converting {gif_path} to PNG sequence in {png_path}")
        start_number = 0 # TODO
        global_options = self.config.ffmpeg_settings["global_options"]
        try:
            GIFtoPNG(gif_path, png_path, start_number=start_number, global_options=global_options)
        except Exception as error:
            message = f"Error using GIFtoPNG with gif_path={gif_path} png_path={png_path}"
            self.log(f"{message}: {error}")
            raise ValueError(message)

    def upscale_png_frames_to_path(self,
                                input_path : str,
                                output_path : str,
                                upscale_factor : float):
        """Use UpscaleSeries to enlarge and clean frames"""
        self.log(
        f"upscaling frames in {input_path} with a factor of {upscale_factor} to {output_path}")
        model_name = self.config.realesrgan_settings["model_name"]
        gpu_ids = self.config.engine_settings["gpu_ids"]
        fp32 = self.config.realesrgan_settings["fp32"]
        if self.config.gif_to_mp4_settings["use_tiling"]:
            tiling = self.config.realesrgan_settings["tiling"]
            tile_pad = self.config.realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        upscaler = UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, self.log)
        output_basename = "upscaled_frames"
        file_list = get_files(input_path, extension="png")
        upscaler.upscale_series(file_list, output_path, upscale_factor, output_basename, "png")

    def inflate_using_noop(self,
                            input_path : str,
                            output_path : str):
        for file in get_files(input_path):
            _, filename, ext = split_filepath(file)
            output_filepath = os.path.join(output_path, filename + ext)
            self.log(f"copying {file} to {output_filepath}")
            shutil.copy(file, output_filepath)

    def inflate_using_resampling(self,
                                input_path : str,
                                output_path : str,
                                inflate_factor: int,
                                precision : int):
        interpolater = Interpolate(self.engine.model, self.log)
        target_interpolater = TargetInterpolate(interpolater, self.log)
        use_time_step = self.config.engine_settings["use_time_step"]
        series_resampler = ResampleSeries(interpolater, target_interpolater, use_time_step,
                                          self.log)
        series_resampler.resample_series(input_path, output_path, 1, inflate_factor, precision,
            f"resampledX{inflate_factor}", False)

    def inflate_using_series_interpolation(self,
                                input_path : str,
                                output_path : str,
                                inflate_factor: int):
        interpolater = Interpolate(self.engine.model, self.log)
        use_time_step = self.config.engine_settings["use_time_step"]
        deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
        series_interpolater = InterpolateSeries(deep_interpolater, self.log)

        file_list = get_files(input_path)
        splits = int(math.log2(inflate_factor))
        series_interpolater.interpolate_series(file_list, output_path, splits,
            f"inflatedX{inflate_factor}")

    def inflate_png_frames_to_path(self,
                                input_path : str,
                                output_path : str,
                                inflate_factor: int,
                                precision : int):
        """Use Inflate frames using a selected technique"""
        self.log(
        f"inflating frames in {input_path} with a factor of {inflate_factor} to {output_path}")

        if inflate_factor < 2:
            self.log("using no-op inflation")
            self.inflate_using_noop(input_path, output_path)
        elif is_power_of_two(inflate_factor):
            self.log("using series interpolation inflation")
            self.inflate_using_series_interpolation(input_path, output_path, inflate_factor)
        else:
            self.log("using resampling inflation")
            self.inflate_using_resampling(input_path, output_path, inflate_factor, precision)

        self.log(f"auto-resequencing sampled frames at {output_path}")
        _ResequenceFiles(output_path, "png", f"resampledX{inflate_factor}", 0, 1, 1, 0, -1, True,
                self.log).resequence()

    def convert_png_frames_to_mp4(self, input_path, output_filepath, frame_rate, quality):
        """Use PNGtoMP4 to assemble to final video"""
        self.log(f"creating {output_filepath} from frames in {input_path}")
        global_options = self.config.ffmpeg_settings["global_options"]
        PNGtoMP4(input_path, None, frame_rate, output_filepath, crf=quality,
                 global_options=global_options)
