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
from tabs.resize_frames_ui import ResizeFrames
from tabs.dedupe_report_ui import DuplicateFramesReport
from tabs.dedupe_autofill_ui import AutofillFrames
from tabs.dedupe_tuning_ui import DuplicateTuning
from tabs.video_details_ui import VideoDetails
from tabs.split_frames_ui import SplitFrames
from tabs.merge_frames_ui import MergeFrames
from tabs.split_scenes_ui import SplitScenes
from tabs.slice_video_ui import SliceVideo
from tabs.strip_scenes_ui import StripScenes
from tabs.video_remixer_ui import VideoRemixer
from tabs.video_assembler_ui import VideoAssembler
from tabs.transpose_png_files_ui import TransposePngFiles
from tabs.enhance_frames_ui import EnhanceFrames

APP_TAB_INTERPOLATE_FRAMES=0
APP_TAB_INTERPOLATE_VIDEO=1
APP_TAB_FILM_RESTORATION=2
APP_TAB_VIDEO_RENOVATION=3
APP_TAB_VIDEO_BLENDER=4
APP_TAB_VIDEO_REMIXER=5
APP_TAB_TOOLS=6

def create_ui(config : SimpleConfig,
              engine : InterpolateEngine,
              log : SimpleLog,
              restart_fn : Callable):
    """Construct the Gradio Blocks UI"""

    app_header = gr.HTML(SimpleIcons.APP_SYMBOL + "EMA-VFI Web UI", elem_id="appheading")
    sep = '  •  '
    footer = (SimpleIcons.COPYRIGHT + ' 2024 J. Hogsett' +
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

        with gr.Tabs() as main_tabs:
            with gr.Tab("Interpolate Frames", id=APP_TAB_INTERPOLATE_FRAMES):
                FrameInterpolation(config, engine, log.log).render_tab()
                FrameSearch(config, engine, log.log).render_tab()

            with gr.Tab("Interpolate Video", id=APP_TAB_INTERPOLATE_VIDEO):
                VideoInflation(config, engine, log.log).render_tab()
                ResynthesizeVideo(config, engine, log.log).render_tab()

            with gr.Tab("Film Restoration", id=APP_TAB_FILM_RESTORATION):
                FrameRestoration(config, engine, log.log).render_tab()
                UpscaleFrames(config, engine, log.log).render_tab()

            with gr.Tab("Video Renovation", id=APP_TAB_VIDEO_RENOVATION):
                with gr.Tab("Deduplication"):
                    gr.HTML(SimpleIcons.SCISSORS + "Detect & Replace Duplicate Frames",
                            elem_id="tabheading")
                    DuplicateFramesReport(config, engine, log.log).render_tab()
                    DuplicateTuning(config, engine, log.log).render_tab()
                    DedupeFrames(config, engine, log.log).render_tab()
                    AutofillFrames(config, engine, log.log).render_tab()

                with gr.Tab("Split & Merge"):
                    gr.HTML(SimpleIcons.SPLIT_MERGE_SYMBOL +
                            "Split, Merge & Process PNG Frame Groups",
                            elem_id="tabheading")
                    SplitFrames(config, engine, log.log).render_tab()
                    MergeFrames(config, engine, log.log).render_tab()
                    SplitScenes(config, engine, log.log).render_tab()
                    SliceVideo(config, engine, log.log).render_tab()
                    StripScenes(config, engine, log.log).render_tab()

            with gr.Tab("Video Blender", id=APP_TAB_VIDEO_BLENDER):
                video_blender = VideoBlender(config, engine, log.log)
                video_blender.render_tab()

            with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Video Remixer", id=APP_TAB_VIDEO_REMIXER):
                VideoRemixer(config, engine, log.log, main_tabs, video_blender).render_tab()

            with gr.Tab(SimpleIcons.LABCOAT + "Tools", id=APP_TAB_TOOLS):
                VideoDetails(config, engine, log.log).render_tab()
                ResequenceFiles(config, engine, log.log).render_tab()
                ResizeFrames(config, engine, log.log).render_tab()
                with gr.Tab("File Conversion"):
                    gr.HTML(SimpleIcons.HAMMER_WRENCH +
                        "Tools for common video file conversion tasks",
                        elem_id="tabheading")
                    MP4toPNG(config, engine, log.log).render_tab()
                    PNGtoMP4(config, engine, log.log).render_tab()
                    GIFtoPNG(config, engine, log.log).render_tab()
                    PNGtoGIF(config, engine, log.log).render_tab()
                    TransposePngFiles(config, engine, log.log).render_tab()
                    SimplifyPngFiles(config, engine, log.log).render_tab()
                    VideoAssembler(config, engine, log.log).render_tab()
                ChangeFPS(config, engine, log.log).render_tab()
                EnhanceFrames(config, engine, log.log).render_tab()
                GIFtoMP4(config, engine, log.log).render_tab()
                with gr.Tab(SimpleIcons.GEAR + "Application"):
                    LogViewer(config, engine, log.log, log).render_tab()
                    Resources(config, engine, log.log).render_tab()
                    Options(config, engine, log.log, restart_fn).render_tab()

        if config.user_interface["show_header"]:
            app_footer.render()
    return app
