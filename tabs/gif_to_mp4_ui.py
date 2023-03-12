"""Change FPS feature UI and event handlers"""
import os
import math
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import create_directory, get_files, split_filepath
from webui_utils.auto_increment import AutoIncrementDirectory
from webui_utils.video_utils import GIFtoPNG, PNGtoMP4
from webui_utils.simple_utils import is_power_of_two
from webui_tips import WebuiTips
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

    def render_tab(self):
        """Render tab into UI"""
        frame_rate = self.config.png_to_mp4_settings["frame_rate"]
        minimum_crf = self.config.png_to_mp4_settings["minimum_crf"]
        maximum_crf = self.config.png_to_mp4_settings["maximum_crf"]
        default_crf = self.config.png_to_mp4_settings["default_crf"]
        with gr.Tab(SimpleIcons.GEMSTONE + "GIF to MP4"):
            gr.HTML(SimpleIcons.PLAY +
                "Turn an Animated GIF Into a MP4 video (must have FFmpeg & Real-ESRGAN)",
                elem_id="tabheading")
            with gr.Row():
                with gr.Column():
                    upscale_input = gr.Slider(value=4.0, minimum=1.0, maximum=8.0, step=0.05,
                        label="Input Frame Size Upscale Factor")
                    inflation_input = gr.Slider(value=4.0, minimum=1.0, maximum=16.0, step=1.0,
                        label="Input Frame Rate Upscale Factor")
                    order_input = gr.Radio(value="Rate First, then Size (Faster)",
            choices=["Rate First, then Size (Faster)", "Size First, then Rate (May be smoother)"],
                        label="Frame Processing Order")
                with gr.Column():
                    output_path_text = gr.Text(max_lines=1, label="MP4 File",
                        placeholder="Path on this server for the converted MP4 file, " +
                            "leave blank for an MP4 in the same location")
                    input_frame_rate = gr.Slider(minimum=1, maximum=240, value=frame_rate,
                        step=1, label="MP4 Frame Rate")
                    quality_slider = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                        step=1, value=default_crf, label="Quality (lower=better)")
            with gr.Row():
                with gr.Tabs():
                    with gr.Tab(label="Individual File"):
                        input_path_text = gr.Text(max_lines=1,
                            label="GIF File (MP4 and others work too)",
                        placeholder="Path on this server to the GIF or MP4 file to be converted")
                        gr.Markdown("*Progress can be tracked in the console*")
                        convert_button = gr.Button("Convert " + SimpleIcons.SLOW_SYMBOL,
                                                   variant="primary")
                    with gr.Tab(label="Batch Processing"):
                        input_path_text_batch = gr.Text(max_lines=1,
                            label="Path to GIF Files (MP4 and others work too)",
                placeholder="Path on this server to the set of GIF or MP4 files to be converted")
                        gr.Markdown("*Progress can be tracked in the console*")
                        convert_button_batch = gr.Button("Convert Batch " + SimpleIcons.SLOW_SYMBOL,
                                                         variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.gif_to_mp4.render()
        convert_button.click(self.convert, inputs=[input_path_text, output_path_text,
            upscale_input, inflation_input, order_input, input_frame_rate, quality_slider])
        convert_button_batch.click(self.convert_batch, inputs=[input_path_text_batch,
            output_path_text, upscale_input, inflation_input, order_input, input_frame_rate,
            quality_slider])

    def convert(self, *args):
        """Convert button handler"""
        self._convert(*args)

    def convert_batch(self,
                input_filepath : str,
                output_filepath : str,
                upscaling : float,
                inflation : float,
                order : str,
                frame_rate : int,
                quality : int):
        """Convert Batch button handler"""

        file_types = ",".join(self.config.gif_to_mp4_settings["file_types"])
        self.log(f"beginning GIF-to-MP4 batch processing at {input_filepath}")
        file_list = get_files(input_filepath, file_types)
        self.log(f"GIF-to-MP4 batch processing found {len(file_list)} files")
        for filepath in file_list:
            self._convert(filepath, output_filepath, upscaling, inflation, order, frame_rate,
                          quality)

    def _convert(self,
                input_filepath : str,
                output_filepath : str,
                upscaling : float,
                inflation : float,
                order : str,
                frame_rate : int,
                quality : int):
        """Convert base handler"""
        if input_filepath:
            working_path, run_index = AutoIncrementDirectory(
                self.config.directories["output_gif_to_mp4"]).next_directory("run")
            precision = self.config.gif_to_mp4_settings["resampling_precision"]
            size_first = True if order[0] == "S" else False

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

            if not output_filepath:
                path, filename, _ = split_filepath(input_filepath)
                filename = f"{filename}-up{upscaling}-in{inflation}.mp4"
                output_filepath = os.path.join(path, filename)

            self.convert_png_frames_to_mp4(frames_path, output_filepath, frame_rate, quality)

    def convert_gif_to_png_frames(self, gif_path : str, png_path : str):
        """Use GIFtoPNG to convert to a PNG sequence"""
        self.log(f"converting {gif_path} to PNG sequence in {png_path}")
        GIFtoPNG(gif_path, png_path)

    def upscale_png_frames_to_path(self,
                                input_path : str,
                                output_path : str,
                                upscale_factor : float):
        """Use UpscaleSeries to enlarge and clean frames"""
        self.log(
        f"upscaling frames in {input_path} with a factor of {upscale_factor} to {output_path}")
        model_name = self.config.realesrgan_settings["model_name"]
        gpu_ips = self.config.gpu_ids
        fp32 = self.config.realesrgan_settings["fp32"]
        if self.config.gif_to_mp4_settings["use_tiling"]:
            tiling = self.config.realesrgan_settings["tiling"]
            tile_pad = self.config.realesrgan_settings["tile_pad"]
        else:
            tiling = 0
            tile_pad = 0
        upscaler = UpscaleSeries(model_name, gpu_ips, fp32, tiling, tile_pad, self.log)
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
        series_resampler = ResampleSeries(target_interpolater, self.log)
        series_resampler.resample_series(input_path, output_path, 1, inflate_factor, precision,
            f"resampledX{inflate_factor}")

    def inflate_using_series_interpolation(self,
                                input_path : str,
                                output_path : str,
                                inflate_factor: int):
        interpolater = Interpolate(self.engine.model, self.log)
        deep_interpolater = DeepInterpolate(interpolater, self.log)
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
        _ResequenceFiles(output_path, "png", f"resampledX{inflate_factor}", 0, 1, -1, True,
                self.log).resequence()

    def convert_png_frames_to_mp4(self, input_path, output_filepath, frame_rate, quality):
        """Use PNGtoMP4 to assemble to final video"""
        self.log(f"creating {output_filepath} from frames in {input_path}")
        PNGtoMP4(input_path, "auto", frame_rate, output_filepath, quality)
