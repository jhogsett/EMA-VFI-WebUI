"""Create the Gradio UI elements"""
from typing import Callable
import gradio as gr
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_log import SimpleLog
from interpolate_engine import InterpolateEngine
from tabs.frame_interpolation_ui import FrameInterpolation
from tabs.frame_search_ui import FrameSearch
from tabs.video_inflation_ui import VideoInflation
from tabs.resynthesize_video_ui import ResynthesizeVideo
from tabs.frame_restoration_ui import FrameRestoration
from tabs.video_blender_ui import VideoBlender
from tabs.mp4_to_png_ui import MP4toPNG
from tabs.png_to_mp4_ui import PNGtoMP4
from tabs.gif_to_png_ui import GIFtoPNG
from tabs.png_to_gif_ui import PNGtoGIF
from tabs.resequence_files_ui import ResequenceFiles
from tabs.change_fps_ui import ChangeFPS
from tabs.options_ui import Options
from tabs.resources_ui import Resources
from tabs.upscale_frames_ui import UpscaleFrames
from tabs.gif_to_mp4_ui import GIFtoMP4
from tabs.log_viewer import LogViewer
from tabs.simplify_png_files_ui import SimplifyPngFiles
from tabs.dedupe_frames_ui import DedupeFrames

def create_ui(config : SimpleConfig,
              engine : InterpolateEngine,
              log : SimpleLog,
              restart_fn : Callable):
    """Construct the Gradio Blocks UI"""

    app_header = gr.HTML(SimpleIcons.APP_SYMBOL + "EMA-VFI Web UI", elem_id="appheading")
    sep = '  •  '
    footer = (SimpleIcons.COPYRIGHT + ' 2023 J. Hogsett' +
        sep + '<a href="https://github.com/jhogsett/EMA-VFI-WebUI">Github</a>' +
        sep + '<a href="https://github.com/MCG-NJU/EMA-VFI">EMA-VFI</a>' +
        sep + '<a href="https://gradio.app">Gradio</a>')
    app_footer = gr.HTML(footer, elem_id="footer")

    with gr.Blocks(analytics_enabled=False,
                    title="EMA-VFI Web UI",
                    theme=config.user_interface["theme"],
                    css=config.user_interface["css_file"]) as app:
        if config.user_interface["show_header"]:
            app_header.render()
        FrameInterpolation(config, engine, log.log).render_tab()
        FrameSearch(config, engine, log.log).render_tab()
        VideoInflation(config, engine, log.log).render_tab()
        ResynthesizeVideo(config, engine, log.log).render_tab()
        FrameRestoration(config, engine, log.log).render_tab()
        VideoBlender(config, engine, log.log).render_tab()
        GIFtoMP4(config, engine, log.log).render_tab()
        with gr.Tab(SimpleIcons.WRENCH + "Tools"):
            with gr.Tab("File Conversion"):
                gr.HTML(SimpleIcons.FOLDER +
                    "Tools for common video file conversion tasks (ffmpeg.exe must be in path)",
                    elem_id="tabheading")
                MP4toPNG(config, engine, log.log).render_tab()
                PNGtoMP4(config, engine, log.log).render_tab()
                GIFtoPNG(config, engine, log.log).render_tab()
                PNGtoGIF(config, engine, log.log).render_tab()
                SimplifyPngFiles(config, engine, log.log).render_tab()
                DedupeFrames(config, engine, log.log).render_tab()
            ResequenceFiles(config, engine, log.log).render_tab()
            ChangeFPS(config, engine, log.log).render_tab()
            UpscaleFrames(config, engine, log.log).render_tab()
            with gr.Tab(SimpleIcons.APP_SYMBOL + "Application"):
                Options(config, engine, log.log, restart_fn).render_tab()
                Resources(config, engine, log.log).render_tab()
                LogViewer(config, engine, log.log, log).render_tab()
        if config.user_interface["show_header"]:
            app_footer.render()
    return app
