"""Video Remixer feature UI and event handlers"""
import os
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown, style_report, dummy_args
from webui_utils.file_utils import get_files, create_directory, get_directories, split_filepath, \
    is_safe_path, duplicate_directory, move_files, remove_directories
from webui_utils.video_utils import details_from_group_name, split_color_alpha, join_color_alpha
from webui_utils.jot import Jot
from webui_utils.auto_increment import AutoIncrementFilename
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from video_remixer import VideoRemixerState
from webui_utils.mtqdm import Mtqdm
from webui_utils.session import Session
from ffmpy import FFRuntimeError
from resequence_files import ResequenceFiles
from .video_blender_ui import VideoBlender
from video_remixer_processor import VideoRemixerProcessor
from video_remixer_project import VideoRemixerProject
from video_remixer_reports import VideoRemixerReports
import cv2
from webui_utils.image_utils import get_average_lightness
from typing import Literal

class VideoRemixer(TabBase):
    """Encapsulates UI elements and events for the Video Remixer Feature"""
    def __init__(self,
                 config : SimpleConfig,
                 engine : InterpolateEngine,
                 log_fn : Callable,
                 main_tabs : any,
                 video_blender : VideoBlender):
        TabBase.__init__(self, config, engine, log_fn)
        self.main_tabs = main_tabs
        self.video_blender = video_blender
        self.state = None
        self.processor = None
        self.marked_scene = None
        self.export_cut_scene_name = None

    TAB_REMIX_HOME = 0
    TAB_REMIX_SETTINGS = 1
    TAB_SET_UP_PROJECT = 2
    TAB_CHOOSE_SCENES = 3
    TAB_COMPILE_SCENES = 4
    TAB_PROC_REMIX = 5
    TAB_SAVE_REMIX = 6
    TAB_REMIX_EXTRA = 7

    TAB_EXTRA_DROP_PROCESSED = 0
    TAB_EXTRA_CHOOSE_RANGE = 1
    TAB_EXTRA_SPLIT_SCENE = 2
    TAB_EXTRA_EXPORT_SCENES = 3
    TAB_EXTRA_CLEANSE_SCENES = 4
    TAB_EXTRA_MANAGE_STORAGE = 5
    TAB_EXTRA_MERGE_SCENES = 6
    TAB_EXTRA_VIDEO_BLEND_SCENE = 7
    TAB_EXTRA_BULK_PROCESSING = 8

    TAB_EXTRA_MERGE_RANGE = 0
    TAB_EXTRA_MERGE_COALESCE = 1

    TAB00_DEFAULT_MESSAGE = "Click New Project to: Inspect Video and Count Frames (can take a minute or more)"
    TAB01_DEFAULT_MESSAGE = "Click Open Project to: Resume Editing an Existing Project"
    TAB1_DEFAULT_MESSAGE = "Click Next to: Save Project Settings and Choose Thumbnail Type"
    TAB2_DEFAULT_MESSAGE = "Click Set Up Project to: Create Scenes and Thumbnails (can take from minutes to hours)"
    TAB4_DEFAULT_MESSAGE = "Click Compile Scenes to: Assemble Kept Scenes for Processing (can take a few seconds)"
    TAB5_DEFAULT_MESSAGE = "Click Process Remix to: Perform all Processing Steps (can take from hours to days)"
    TAB60_DEFAULT_MESSAGE = "Click Save Remix to: Combine Processed Content with Audio Clips and Save Remix Video"
    TAB61_DEFAULT_MESSAGE = "Click Save Custom Remix to: Apply Custom Options and save Custom Remix Video"
    TAB62_DEFAULT_MESSAGE = "Click Save Marked Remix to: Apply Marking Options and save Marked Remix Video"
    TAB63_DEFAULT_MESSAGE = "Click Save Labeled Remix to: Add Label and save Remix Video"

    APP_TAB_VIDEO_BLENDER=4
    APP_TAB_VIDEO_REMIXER=5

    # cross ref from project progress to the tab ID to return to on re-opening
    PROGRESS_STEPS = {
        "home" : TAB_REMIX_SETTINGS,
        "settings" : TAB_REMIX_SETTINGS,
        "setup" : TAB_SET_UP_PROJECT,
        "choose" : TAB_CHOOSE_SCENES,
        "compile" : TAB_COMPILE_SCENES,
        "process" : TAB_PROC_REMIX,
        "save" : TAB_SAVE_REMIX
    }

    # TODO this is a processing concern
    CLEANSE_SCENES_PATH = "cleansed_scenes"
    CLEANSE_SCENES_FACTOR = 4.0

    GAP = " " * 5
    FONTS_ROOT = "fonts"

    def render_tab(self):
        """Render tab into UI"""
        def_project_fps = self.config.remixer_settings["def_project_fps"]
        max_project_fps = self.config.remixer_settings["max_project_fps"]
        minimum_crf = self.config.remixer_settings["minimum_crf"]
        maximum_crf = self.config.remixer_settings["maximum_crf"]
        default_crf = self.config.remixer_settings["default_crf"]
        max_thumb_size = self.config.remixer_settings["max_thumb_size"]
        def_min_frames = self.config.remixer_settings["min_frames_per_scene"]
        marked_ffmpeg_video = self.config.remixer_settings["marked_ffmpeg_video"]
        marked_ffmpeg_audio = self.config.remixer_settings["marked_ffmpeg_audio"]
        default_label_font_size = self.config.remixer_settings["marked_font_size"]
        default_label_font_color = self.config.remixer_settings["marked_font_color"]
        default_label_font_file = self.config.remixer_settings["marked_font_file"]
        default_label_draw_box = self.config.remixer_settings["marked_draw_box"]
        default_label_box_color = self.config.remixer_settings["marked_box_color"]
        default_label_border_size = self.config.remixer_settings["marked_border_size"]
        default_label_position_v = self.config.remixer_settings["marked_position_v"]
        default_label_position_h = self.config.remixer_settings["marked_position_h"]
        default_label_draw_shadow = self.config.remixer_settings["marked_draw_shadow"]
        default_label_shadow_color = self.config.remixer_settings["marked_shadow_color"]
        default_label_shadow_size = self.config.remixer_settings["marked_shadow_size"]
        custom_ffmpeg_video = self.config.remixer_settings["custom_ffmpeg_video"]
        custom_ffmpeg_audio = self.config.remixer_settings["custom_ffmpeg_audio"]
        _, default_label_font_file, _ = split_filepath(default_label_font_file)
        default_label_font_color, default_label_font_alpha = split_color_alpha(default_label_font_color)
        default_label_shadow_color, default_label_shadow_alpha = split_color_alpha(default_label_shadow_color)
        default_label_box_color, default_label_box_alpha = split_color_alpha(default_label_box_color)

        gr.Markdown(
            SimpleIcons.MOVIE + "Restore & Remix Videos with Audio")
        with gr.Tabs() as tabs_video_remixer:

            ### NEW PROJECT
            with gr.Tab(SimpleIcons.ONE + " Remix Home", id=self.TAB_REMIX_HOME):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**Input a video to get started remixing**")
                        with gr.Row():
                            video_path = gr.Textbox(label="Video Path", max_lines=1,
                                placeholder="Path on this server to the video to be remixed")
                        with gr.Row():
                            message_box00 = gr.Markdown(
                                format_markdown(self.TAB00_DEFAULT_MESSAGE))
                        gr.Markdown(format_markdown("Progress can be tracked in the console",
                                                    color="none", italic=True, bold=False))
                        next_button00 = gr.Button(value="New Project > " +
                            SimpleIcons.SLOW_SYMBOL, variant="primary", elem_id="actionbutton")
                    with gr.Column():
                        gr.Markdown("**Open an existing Video Remixer project**")
                        with gr.Row():
                            project_load_path = gr.Textbox(label="Project Path", max_lines=1,
            placeholder="Path on this server to the Video Remixer project directory or file",
                                value=lambda : Session().get("last-video-remixer-project"))
                        with gr.Row():
                            message_box01 = gr.Markdown(
                                value=format_markdown(self.TAB01_DEFAULT_MESSAGE))
                        gr.Markdown(format_markdown(
                            "The last used tab will be shown after loading project",
                            color="none", italic=True, bold=False))
                        next_button01 = gr.Button(value="Open Project >",
                                                variant="primary")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_home.render()

            ### REMIX SETTINGS
            with gr.Tab(SimpleIcons.TWO + " Remix Settings", id=self.TAB_REMIX_SETTINGS):
                gr.Markdown("**Confirm Remixer Settings**")
                with gr.Row(variant="panel"):
                    video_info1 = gr.Markdown("Video Details")

                with gr.Row():
                    with gr.Column():
                        with gr.Row():
                            project_path = gr.Textbox(label="Set Project Path", max_lines=1,
                                        placeholder="Path on this server to store project data")
                        with gr.Row():
                            split_type = gr.Radio(label="Split Type", value="Scene",
                                                    choices=["Scene", "Break", "Time", "None"])
                        with gr.Tabs():
                            with gr.Tab("Scene Settings"):
                                scene_threshold = gr.Slider(value=0.6, minimum=0.0, maximum=1.0,
                                                step=0.01, label="Scene Detection Threshold",
                            info="Value between 0.0 and 1.0 (higher = fewer scenes detected)")
                            with gr.Tab("Break Settings"):
                                with gr.Row():
                                    break_duration = gr.Slider(value=2.0, minimum=0.0,
                                                                maximum=30.0, step=0.25,
                                                                label="Break Minimum Duration",
                                                        info="Choose a duration in seconds")
                                    break_ratio = gr.Slider(value=0.98, minimum=0.0,
                                                            maximum=1.0, step=0.01,
                                                            label="Break Black Frame Ratio",
                                                    info="Choose a value between 0.0 and 1.0")
                            with gr.Tab("Time Settings"):
                                split_time = gr.Number(value=60, precision=0,
                                                        label="Scene Split Seconds",
                                                        info="Seconds for each split scene")
                    with gr.Column():
                        with gr.Row():
                            project_fps = gr.Slider(label="Remix Frame Rate",
                                                    value=def_project_fps,
                                                    minimum=1.0, maximum=max_project_fps,
                                                    step=0.01)
                            deinterlace = gr.Checkbox(
                                label="Deinterlace Source Video")
                        with gr.Row():
                            resize_w = gr.Number(1920, label="Resize Width", precision=0)
                            resize_h = gr.Number(1080, label="Resize Height", precision=0)
                        with gr.Row():
                            crop_w = gr.Number(1920, label="Crop Width", precision=0)
                            crop_h = gr.Number(1080, label="Crop Height", precision=0)
                        with gr.Accordion(label="More Options", open=False):
                            with gr.Row(variant="compact"):
                                reuse_prev_settings = gr.Button(value="Reuse Last-Used Settings", size="sm", scale=1)
                                use_saved_settings = gr.Button(value="Use Memorized Settings", size="sm", scale=1)
                                save_settings = gr.Button(value="Remember These Settings", size="sm", scale=1)
                            with gr.Row(variant="compact"):
                                crop_offset_x = gr.Number(label="Crop X Offset (-1: center)", value=-1, container=False, scale=1)
                                crop_offset_y = gr.Number(label="Crop Y Offset (-1: center)", value=-1, container=False, scale=1)
                                frame_format = gr.Radio(choices=["png", "jpg"], value="png", label="Frame Format", container=False, scale=2)

                message_box1 = gr.Markdown(value=format_markdown(self.TAB1_DEFAULT_MESSAGE))
                with gr.Row():
                    back_button1 = gr.Button(value="< Back", variant="secondary", scale=0)
                    next_button1 = gr.Button(value="Next >", variant="primary",
                                            elem_id="actionbutton")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_settings.render()

            ## SET UP PROJECT
            with gr.Tab(SimpleIcons.THREE + " Set Up Project", id=self.TAB_SET_UP_PROJECT):
                gr.Markdown("**Ready to Set Up Video Remixer Project**")
                with gr.Row(variant="panel"):
                    project_info2 = gr.Markdown("Project Details")
                with gr.Row():
                    thumbnail_type = gr.Radio(choices=["GIF", "JPG"], value="GIF",
                                                label="Thumbnail Type",
                        info="Choose 'GIF' for whole scene animation, 'JPG' for mid-scene image")
                    min_frames_per_scene = gr.Number(label="Minimum Frames Per Scene",
                                precision=0, value=def_min_frames,
                    info="Consolidates very small scenes info the next (0 to disable)")
                with gr.Row():
                    skip_detection = gr.Checkbox(value=False, label="Recreate Thumbnails Only",
                info="Remake thumbnails with existing scenes if present, skipping project setup")
                with gr.Accordion(label="More Options", open=False):
                    # with gr.Row(variant="compact"):
                    remove_source = gr.Checkbox(value=False, label="Don't Keep Source Frames",
                        info="Speed up project creation by moving source frames to scenes directories")

                with gr.Row():
                    message_box2 = gr.Markdown(value=format_markdown(self.TAB2_DEFAULT_MESSAGE))
                gr.Markdown(format_markdown(
                    "Progress can be tracked in the console",
                    color="none", italic=True, bold=False))

                with gr.Row():
                    back_button2 = gr.Button(value="< Back", variant="secondary", scale=0)
                    next_button2 = gr.Button(value="Set Up Project " + SimpleIcons.SLOW_SYMBOL,
                                            variant="primary", elem_id="actionbutton")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_setup.render()

            ## CHOOSE SCENES
            with gr.Tab(SimpleIcons.FOUR + " Choose Scenes", id=self.TAB_CHOOSE_SCENES):
                with gr.Row():
                    scene_name = gr.Text(label="Scene Name", max_lines=1, interactive=False,
                                         scale=1)
                    scene_info = gr.Text(label="Scene Details", max_lines=1, interactive=False,
                                         scale=1)
                    with gr.Column(scale=2):
                        with gr.Row():
                            scene_state = gr.Radio(label="Choose", value=None,
                                choices=[VideoRemixerState.KEEP_MARK, VideoRemixerState.DROP_MARK])
                            with gr.Column(variant="compact", elem_id="mainhighlightdim"):
                                scene_index = gr.Number(label="Scene Index", precision=0)
                with gr.Row():
                    with gr.Column():
                        scene_image = gr.Image(type="filepath", interactive=False,
                                                height=max_thumb_size)
                    with gr.Column():
                        keep_next = gr.Button(value="Keep Scene | Next >", variant="primary",
                                            elem_id="actionbutton")
                        drop_next = gr.Button(value="Drop Scene | Next >", variant="primary",
                                            elem_id="actionbutton")
                        with gr.Row():
                            prev_scene = gr.Button(value="< Prev Scene", variant="primary")
                            next_scene = gr.Button(value="Next Scene >", variant="primary")
                        with gr.Row():
                            prev_keep = gr.Button(value="< Prev Keep", variant="secondary")
                            next_keep = gr.Button(value="Next Keep >", variant="secondary")
                        with gr.Row():
                            first_scene = gr.Button(value="<< First Scene",
                                                        variant="secondary")
                            last_scene = gr.Button(value="Last Scene >>",
                                                        variant="secondary")

                        with gr.Row():
                                split_scene_button = gr.Button(
                                    value="Split Scene " + SimpleIcons.AXE,
                                    variant="secondary", elem_id="highlightbutton")
                                choose_range_button = gr.Button(
                                    value="Choose Scene Range " + SimpleIcons.HEART_HANDS,
                                    variant="secondary", elem_id="highlightbutton")
                        with gr.Row(variant="panel", equal_height=False):
                            with gr.Accordion(label="Properties", open=False):
                                with gr.Row():
                                    set_scene_label = gr.Textbox(placeholder="Scene Label",
                                                                 max_lines=1, show_label=False,
                                                                 min_width=100, scale=3,
                                                                 container=False)
                                    save_scene_label = gr.Button(value="Set", size="sm", scale=0,
                                                                 min_width=40)
                                    prev_labeled_scene = gr.Button("<", size="sm", min_width=20,
                                                                   scale=0)
                                    next_labeled_scene = gr.Button(">", size="sm", min_width=20,
                                                                   scale=0)
                                with gr.Row():
                                    auto_label_scenes = gr.Button(value="+ Sort Keys", size="sm", min_width=60)
                                    auto_title_scenes = gr.Button(value="+ Titles", size="sm", min_width=60)
                                    reset_scene_labels = gr.Button(value="Reset", size="sm", min_width=60)
                                with gr.Row():
                                    add_2x_slomo = gr.Button(value="+ 2X Slo Mo", size="sm", min_width=60, elem_id="highlightbutton")
                                    add_4x_slomo = gr.Button(value="+ 4X Slo Mo", size="sm", min_width=60, elem_id="highlightbutton")
                                    add_8x_slomo = gr.Button(value="+ 8X Slo Mo", size="sm", min_width=60, elem_id="highlightbutton")
                            with gr.Accordion(label="Danger Zone", open=False):
                                with gr.Row():
                                    keep_all_button = gr.Button(value="Keep All Scenes",
                                                            variant="stop", size="sm", min_width=80)
                                    drop_all_button = gr.Button(value="Drop All Scenes",
                                                            variant="stop", size="sm", min_width=80)
                                with gr.Row():
                                    invert_choices_button = gr.Button(value="Invert Scene Choices",
                                                            variant="stop", size="sm", min_width=80)
                                    drop_processed_button = gr.Button(value="Drop Processed Scene",
                                                            variant="stop", size="sm", min_width=80)
                                with gr.Row():
                                    mark_scene = gr.Button(value="Mark Scene",
                                                    variant="secondary", size="sm", min_width=80)
                                    merge_scenes_button = gr.Button(value="Merge Scenes",
                                                            variant="stop", size="sm", min_width=80)
                with gr.Row():
                    back_button3 = gr.Button(value="< Back", variant="secondary", scale=0)
                    next_button3 = gr.Button(value="Done Choosing Scenes", variant="primary",
                                            elem_id="actionbutton")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_choose.render()

            ## COMPILE SCENES
            with gr.Tab(SimpleIcons.FIVE + " Compile Scenes", id=self.TAB_COMPILE_SCENES):
                with gr.Row(variant="panel"):
                    project_info4 = gr.Markdown("Chosen Scene Details")
                with gr.Row():
                    message_box4 = gr.Markdown(value=format_markdown(self.TAB4_DEFAULT_MESSAGE))
                with gr.Row():
                    back_button4 = gr.Button(value="< Back", variant="secondary", scale=0)
                    next_button4 = gr.Button(value="Compile Scenes", variant="primary",
                                            elem_id="actionbutton")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_compile.render()

            ## PROCESS REMIX
            with gr.Tab(SimpleIcons.SIX + " Process Remix", id=self.TAB_PROC_REMIX):
                gr.Markdown("**Ready to Process Content for Remix Video**")

                with gr.Row():
                    resize = gr.Checkbox(label="Resize / Crop Frames", value=True, scale=7)
                    with gr.Column(variant="compact", scale=5):
                        gr.Markdown(format_markdown(
                            "Resize and Crop Frames according to project settings\r\n"+
                            "- Adjust aspect ratio\r\n" +
                            "- Remove unwanted letterboxes or pillarboxes",
                            color="more", bold_heading_only=True))

                with gr.Row():
                    resynthesize = gr.Checkbox(label="Resynthesize Frames",value=True, scale=1)
                    resynth_option = gr.Radio(label="Resynthesis Type", value="Clean", scale=6,
                                        choices=["Clean", "Scrub", "Replace"], info="Clean: Fastest, Scrub: Best, Replace: Deepest")
                    with gr.Column(variant="compact", scale=5):
                        gr.Markdown(format_markdown(
                            "Recreate Frames using Interpolation of adjacent frames\r\n" +
                            "- Remove grime and single-frame noise\r\n" +
                            "- Reduce sprocket shake in film-to-digital content",
                            color="more", bold_heading_only=True))

                with gr.Row():
                    inflate = gr.Checkbox(label="Inflate New Frames",value=True, scale=1)
                    inflate_by_option = gr.Radio(label="Inflate By", value="2X", scale=3,
                                                choices=["2X", "4X", "8X", "16X"], info="Adds 1, 3, 7 or 15 Between Frames")
                    inflate_slow_option = gr.Radio(label="Slow Motion", value="No",
                                                   choices=["No", "Audio", "Silent"],
                                                   scale=3, info="Audio: Pitch and FPS adjusted, Silent: No FPS adjustment")
                    with gr.Column(variant="compact", scale=5):
                        gr.Markdown(format_markdown(
                        "Insert Between-Frames using Interpolation of existing frames\r\n" +
                        "- Double the frame rate for smooth motion\r\n" +
                        "- Increase content realness and presence",
                        color="more", bold_heading_only=True))

                with gr.Row():
                    upscale = gr.Checkbox(label="Upscale Frames", value=True, scale=1)
                    upscale_option = gr.Radio(label="Upscale By", value="2X", scale=6,
                                                choices=["1X", "2X", "3X", "4X"], info="Option '1X' Cleans Frames Without Enlarging")
                    with gr.Column(variant="compact", scale=5):
                        gr.Markdown(format_markdown(
                            "Clean and Enlarge frames using Real-ESRGAN 4x+ upscaler\r\n" +
                            "- Remove grime, noise, and digital artifacts\r\n" +
                            "- Enlarge frames according to upscaling settings",
                            color="more", bold_heading_only=True))

                with gr.Row():
                    process_all = gr.Checkbox(label="Select All", value=True, scale=7)
                    with gr.Column(variant="compact", scale=5):
                        gr.Markdown(format_markdown(
                            "Deselect All Steps to use original source content for remix video",
                            color="more", bold=True))
                message_box5 = gr.Markdown(value=format_markdown(self.TAB5_DEFAULT_MESSAGE))
                gr.Markdown(
                    format_markdown(
                        "Progress can be tracked in the console", color="none", italic=True,
                        bold=False))

                with gr.Row():
                    with gr.Column(scale=7):
                        with gr.Row():
                            back_button5 = gr.Button(value="< Back", variant="secondary", scale=0)
                            next_button5 = gr.Button(value="Process Remix " +
                                        SimpleIcons.SLOW_SYMBOL, variant="primary",
                                        elem_id="actionbutton")
                    with gr.Column(scale=5):
                        with gr.Accordion(label="Advanced Options", open=False):
                            with gr.Row(variant="compact"):
                                auto_save_remix = gr.Checkbox(label="Save default video", container=False, min_width=120)
                                keep_scene_videos = gr.Checkbox(label="Keep scene videos", container=False, min_width=120)
                                auto_delete_remix = gr.Checkbox(label="Delete project content", container=False, min_width=120)
                            with gr.Row(variant="compact"):
                                auto_coalesce_remix = gr.Checkbox(label="Coalesce kept scenes (not for Resynthesis or Inflation)", container=False, min_width=120)
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_processing.render()

            ## SAVE REMIX
            with gr.Tab(SimpleIcons.FINISH_FLAG + " Save Remix", id=self.TAB_SAVE_REMIX):
                gr.Markdown("**Ready to Finalize Scenes and Save Remixed Video**")
                with gr.Row(variant="panel"):
                    summary_info6 = gr.Markdown("Remix video source content")
                with gr.Tabs():
                    ### CREATE MP4 REMIX
                    with gr.Tab(label="Create MP4 Remix"):
                        quality_slider = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                            step=1, value=default_crf, label="Video Quality",
                            info="Lower values mean higher video quality")
                        output_filepath = gr.Textbox(label="Output Filepath", max_lines=1,
                                info="Enter a path and filename for the remixed video")
                        with gr.Accordion("Advanced Options", open=False):
                            with gr.Row(variant="compact", equal_height=False):
                                volume_60 = gr.Slider(value=0.0,
                                    label="Volume Adjustment in dB", minimum=-30.0,
                                    maximum=30.0, step=0.1, container=False)
                        with gr.Row():
                            message_box60 = gr.Markdown(
                                value=format_markdown(self.TAB60_DEFAULT_MESSAGE))
                        gr.Markdown(
                            format_markdown(
                                "Progress can be tracked in the console", color="none",
                                italic=True, bold=False))
                        with gr.Row():
                            back_button60 = gr.Button(value="< Back", variant="secondary",
                                                        scale=0)
                            next_button60 = gr.Button(
                                value="Save Remix " + SimpleIcons.SLOW_SYMBOL,
                                variant="primary", elem_id="highlightbutton")

                    ### CREATE CUSTOM REMIX
                    with gr.Tab(label="Create Custom Remix"):
                        custom_video_options = gr.Textbox(value=custom_ffmpeg_video, max_lines=1,
                            label="Custom FFmpeg Video Output Options",
                    info="Passed to FFmpeg as output video settings when converting frames to video")
                        custom_audio_options = gr.Textbox(value=custom_ffmpeg_audio, max_lines=1,
                            label="Custom FFmpeg Audio Output Options",
                    info="Passed to FFmpeg as output audio settings when combining with video")
                        output_filepath_custom = gr.Textbox(label="Output Filepath",
                                                            max_lines=1,
                                        info="Enter a path and filename for the remixed video")
                        with gr.Row():
                            message_box61 = gr.Markdown(
                                value=format_markdown(self.TAB61_DEFAULT_MESSAGE))
                        gr.Markdown(
                            format_markdown(
                                "Progress can be tracked in the console", color="none",
                                italic=True, bold=False))
                        with gr.Row():
                            back_button61 = gr.Button(value="< Back", variant="secondary",
                                                        scale=0)
                            next_button61 = gr.Button(
                                value="Save Custom Remix " + SimpleIcons.SLOW_SYMBOL,
                                variant="primary", elem_id="highlightbutton")
                        gr.Markdown(format_markdown(SimpleIcons.WARNING + "Custom Video Options are applied one time only. To delete existing clips, go to `Remix Extra`, `Manage Storage`, `Remove Selected Project Content`."))

                    ### CREATE MARKED REMIX
                    with gr.Tab(label="Create Marked Remix"):
                        marked_video_options = gr.Textbox(value=marked_ffmpeg_video, max_lines=1,
                            label="Marked FFmpeg Video Output Options",
                    info="Passed to FFmpeg as output video settings when converting frames to video")
                        marked_audio_options = gr.Textbox(value=marked_ffmpeg_audio, max_lines=1,
                            label="Marked FFmpeg Audio Output Options",
                    info="Passed to FFmpeg as output audio settings when combining with video")
                        output_filepath_marked = gr.Textbox(label="Output Filepath",
                                                            max_lines=1,
                                        info="Enter a path and filename for the remixed video")
                        with gr.Row():
                            message_box62 = gr.Markdown(value=
                                            format_markdown(self.TAB62_DEFAULT_MESSAGE))
                        gr.Markdown(
                            format_markdown(
                                "Progress can be tracked in the console", color="none",
                                italic=True, bold=False))
                        with gr.Row():
                            back_button62 = gr.Button(value="< Back", variant="secondary",
                                                        scale=0)
                            next_button62 = gr.Button(
                                value="Save Marked Remix " + SimpleIcons.SLOW_SYMBOL,
                                variant="primary", elem_id="highlightbutton")

                    ### CREATE LABELED REMIX
                    with gr.Tab(label="Create Labeled Remix"):
                        with gr.Row():
                            label_text = gr.Textbox(label="Label Text", max_lines=1, info="Scenes with set labels will override this label")
                            label_position_v = gr.Radio(choices=["Top", "Middle", "Bottom"], value=default_label_position_v, label="Label Position", info="Vertical location for the label")
                            label_position_h = gr.Radio(choices=["Left", "Center", "Right"], value=default_label_position_h, label="Label Position", info="Horizontal location for the label")
                        with gr.Row():
                            label_font_file = gr.Dropdown(choices=self._gather_fonts(), value=default_label_font_file, label="Font File", info="Font file within the /fonts directory")
                            label_font_size = gr.Slider(value=default_label_font_size, label="Font Factor", minimum=2, maximum=100, step=1, info="Size as a factor of frame width, smaller values produce larger text")
                            label_font_color = gr.ColorPicker(value=default_label_font_color, label="Font Color", info="Color for the label text")
                            label_font_alpha = gr.Slider(value=default_label_font_alpha, minimum=0.0, maximum=1.0, step=0.1, label="Font Alpha", info="Opacity for the label text")
                        with gr.Row():
                            label_draw_shadow = gr.Checkbox(value=default_label_draw_shadow, label="Drop Shadow", info="Draw a drop shadow underneath the label text")
                            label_shadow_size = gr.Slider(value=default_label_shadow_size, label="Shadow Factor", minimum=1, maximum=100, step=1, info="Shadow offset as a factor of computed font size, smaller values produce a larger offset")
                            label_shadow_color = gr.ColorPicker(value=default_label_shadow_color, label="Shadow Color", info="Color for the drop shadow text")
                            label_shadow_alpha = gr.Slider(value=default_label_shadow_alpha, minimum=0.0, maximum=1.0, step=0.1, label="Shadow Alpha", info="Opacity for the shadow text")
                        with gr.Row():
                            label_draw_box = gr.Checkbox(value=default_label_draw_box, label="Background", info="Draw a background underneath the label text")
                            label_border_size = gr.Slider(value=default_label_border_size, label="Border Factor", minimum=1, maximum=100, step=1, info="Size as a factor of computed font size, smaller values produce a larger margin")
                            label_box_color = gr.ColorPicker(value=default_label_box_color, label="Background Color", info="Color for the background rectangle")
                            label_box_alpha = gr.Slider(value=default_label_box_alpha, minimum=0.0, maximum=1.0, step=0.1, label="Box Alpha", info="Opacity for the background rectangle")
                        with gr.Row():
                            quality_slider_labeled = gr.Slider(minimum=minimum_crf,
                                maximum=maximum_crf, step=1, value=default_crf,
                                label="Video Quality",
                                info="Lower values mean higher video quality")
                            output_filepath_labeled = gr.Textbox(label="Output Filepath",
                                max_lines=1,
                                info="Enter a path and filename for the remixed video")
                        with gr.Accordion("Advanced Options", open=False):
                            with gr.Row(variant="compact", equal_height=False):
                                volume_63 = gr.Slider(value=0.0,
                                    label="Volume Adjustment in dB", minimum=-30.0,
                                    maximum=30.0, step=0.1, container=False)
                        with gr.Row():
                            message_box63 = gr.Markdown(value=format_markdown(self.TAB63_DEFAULT_MESSAGE))
                        gr.Markdown(format_markdown("Progress can be tracked in the console", color="none", italic=True, bold=False))
                        with gr.Row():
                            back_button63 = gr.Button(value="< Back", variant="secondary", scale=0)
                            next_button63 = gr.Button(
                                value="Save Labeled Remix " + SimpleIcons.SLOW_SYMBOL,
                                variant="primary", elem_id="highlightbutton")

                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_save.render()

            ## REMIX EXTRA
            with gr.Tab(SimpleIcons.COCKTAIL + " Remix Extra", id=self.TAB_REMIX_EXTRA):
                with gr.Tabs() as tabs_remix_extra:

                    # SPLIT SCENE
                    with gr.Tab(SimpleIcons.AXE + " Split Scene",
                                id=self.TAB_EXTRA_SPLIT_SCENE):
                        gr.Markdown("**_Split a Scene in two at a set point_**")
                        with gr.Row():
                            with gr.Column():
                                with gr.Row():
                                    scene_id_702 = gr.Number(value=-1,
                                                                label="Scene Index")
                                    scene_info_702 = gr.Textbox(label="Scene Details", max_lines=1,
                                                                interactive=False)
                                with gr.Row():
                                    split_percent_702 = gr.Slider(value=50.0,
                                        label="Split Position", minimum=0.0,
                                        maximum=100.0, step=0.1,
                                    info="A lower value splits earlier in the scene")
                                with gr.Row():
                                    prev_second_702 = gr.Button(value="< Second", scale=1, min_width=90)
                                    prev_frame_702 = gr.Button(value="< Frame", scale=1, min_width=90)
                                    next_frame_702 = gr.Button(value="Frame >", scale=1, min_width=90)
                                    next_second_702 = gr.Button(value="Second >", scale=1, min_width=90)
                                with gr.Row():
                                    prev_minute_702 = gr.Button(value="< Minute", scale=1, min_width=90, size="sm")
                                    goto_0_702 = gr.Button(value="< First", scale=1, min_width=90, size="sm")
                                    goto_50_702 = gr.Button(value="Middle", scale=1, min_width=90, size="sm")
                                    goto_100_702 = gr.Button(value="Last >", scale=1, min_width=90, size="sm")
                                    next_minute_702 = gr.Button(value="Minute >", scale=1, min_width=90, size="sm")
                                with gr.Row():
                                    prev_keep_702 = gr.Button(value="< Prev Keep", size="sm", variant="primary")
                                    next_keep_702 = gr.Button(value="Next Keep >", size="sm", variant="primary")
                                    prev_break_702 = gr.Button(value="< Prev Break" + SimpleIcons.SLOW_SYMBOL, size="sm", variant="primary")
                                    next_break_702 = gr.Button(value="Next Break"  + SimpleIcons.SLOW_SYMBOL + " >", size="sm", variant="primary")
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        with gr.Row(equal_height=True, variant="panel", elem_id="highlightbutton"):
                                            go_to_f_button702 = gr.Button(value="Go to Frame",
                                                                            variant="secondary",
                                                                            size="sm", min_width=120)
                                            go_to_f_702 = gr.Number(value=0, show_label=False,
                                                                    info=None,
                                                                    precision=0, container=False,
                                                                    min_width=120)
                                    with gr.Column(scale=1):
                                        with gr.Row(equal_height=True, variant="panel", elem_id="highlightbutton"):
                                            go_to_s_button702 = gr.Button(value="Go to Second",
                                                                            variant="secondary",
                                                                            size="sm", min_width=120)
                                            go_to_s_702 = gr.Number(value=0, show_label=False,
                                                                    info=None,
                                                                    precision=0, container=False,
                                                                    min_width=120)
                                with gr.Accordion("Advanced Options", open=False):
                                    with gr.Row(variant="compact", equal_height=False):
                                        use_alt_split_702 = gr.Checkbox(value=False, label="Use Secondary Split", container=False, scale=1)
                                        split_percent_alt_702 = gr.Slider(value=50.0,
                                            label="Secondary Split Position", minimum=0.0,
                                            maximum=100.0, step=0.1, container=False, scale=2,
                                            info="Earliest split is performed first")
                                    with gr.Row(variant="compact", equal_height=False):
                                        set_view_hint_702 = gr.Textbox(placeholder="View Hint such as {V:200%}",
                                                                    max_lines=1, show_label=False,
                                                                    min_width=100, container=False, scale=2)
                                        preview_view_hint_702 = gr.Button(value="Visualize View Hint",
                                                                      size="sm", min_width=40, scale=1)

                            with gr.Column():
                                preview_image702 = gr.Image(type="filepath",
                        label="Split Frame Preview", tool=None, height=max_thumb_size)
                        with gr.Row():
                            message_box702 = gr.Markdown(format_markdown(
        "Click Split Scene to: Split the scenes into Two Scenes at a set percentage"))
                        with gr.Row():
                            back_button702 = gr.Button(value="< Back", variant="secondary", scale=0)
                            split_keep_before_702 = gr.Button("Split - Keep Before",
                                                        variant="primary", elem_id="actionbutton")
                            split_keep_after_702 = gr.Button("Split - Keep After",
                                                        variant="primary", elem_id="actionbutton")
                            split_button702 = gr.Button(
                                "Split Scene", variant="primary", scale=3)

                    # MERGE SCENES
                    with gr.Tab(SimpleIcons.PACKAGE + " Merge Scenes",
                                id=self.TAB_EXTRA_MERGE_SCENES):
                        gr.Markdown("Removes unneeded splits between adjacent scenes")
                        with gr.Tabs() as tabs_merge_scenes:
                            with gr.Tab(SimpleIcons.PACKAGE + " Merge Scene Range",
                                        id=self.TAB_EXTRA_MERGE_RANGE):
                                gr.Markdown("**_Merge a range of scenes into one scene_**")
                                with gr.Row():
                                    first_scene_id_705 = gr.Number(value=-1,
                                                                label="Starting Scene Index")
                                    last_scene_id_705 = gr.Number(value=-1,
                                                                label="Ending Scene Index")
                                with gr.Row():
                                    message_box705 = gr.Markdown(
                                        format_markdown(
                        "Click Merge Scene Range to: Combine the chosen scenes into a single scene"))
                                with gr.Row():
                                    merge_button705 = gr.Button("Merge Scene Range",
                                                            variant="stop", scale=0)
                            with gr.Tab(SimpleIcons.BROOM + " Coalesce Scenes",
                                        id=self.TAB_EXTRA_MERGE_COALESCE):
                                gr.Markdown("**_Consolidate all adjacent Kept scenes_**")
                                with gr.Row():
                                    coalesce_scenes_706 = gr.Checkbox(value=False,
                                                                    label="Coalesce Kept Scenes",
                                info="Leave unchecked to see which scenes will be consolidated")
                                with gr.Row():
                                    message_box706 = gr.Markdown(
                                        format_markdown(
                                "Click Coalesce to: Consolidate all adjacent kept scenes"))
                                with gr.Row():
                                    coalesce_button706 = gr.Button("Coalesce Scenes",
                                                            variant="stop", scale=0)

                    # CHOOSE SCENE RANGE
                    with gr.Tab(SimpleIcons.HEART_HANDS + " Choose Scene Range",
                                id=self.TAB_EXTRA_CHOOSE_RANGE):
                        gr.Markdown("**_Keep or Drop a range of scenes_**")
                        with gr.Row():
                            first_scene_id_701 = gr.Number(value=-1,
                                                        label="Starting Scene Index")
                            last_scene_id_701 = gr.Number(value=-1,
                                                        label="Ending Scene Index")
                        with gr.Row():
                            scene_state_701 = gr.Radio(label="Scenes Choice",
                                                       value=None,
                                choices=[VideoRemixerState.KEEP_MARK, VideoRemixerState.DROP_MARK])
                        with gr.Row():
                            message_box701 = gr.Markdown(
                                format_markdown(
                    "Click Choose Scene Range to: Set the Scene Range to the specified state"))
                        choose_button701 = gr.Button("Choose Scene Range",
                                                variant="primary")

                    # DROP PROCESSED SCENE
                    with gr.Tab(SimpleIcons.BROKEN_HEART + " Drop Processed Scene",
                                id=self.TAB_EXTRA_DROP_PROCESSED):
                        gr.Markdown(
                    "**_Drop a scene after processing has been already been done_**")
                        scene_id_700 = gr.Number(value=-1, label="Scene Index")
                        with gr.Row():
                            message_box700 = gr.Markdown(
                                format_markdown(
                "Click Drop Scene to: Remove all Processed Content for the specified scene"))
                        drop_button700 = gr.Button(
                    "Drop Processed Scene " + SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)

                    # SCENE CLEANING
                    with gr.Tab(SimpleIcons.SOAP + " Scene Cleaning",
                                id=self.TAB_EXTRA_CLEANSE_SCENES):
                        gr.Markdown("Scene Deep Cleaning and Restoration")
                        # CLEANSE SCENES
                        with gr.Tab(SimpleIcons.SOAP + " Cleanse Scenes"):
                            gr.Markdown("**_Remove noise and artifacts from kept scenes_**")
                            with gr.Row():
                                message_box704 = gr.Markdown(
                                    format_markdown(
                            "Click Cleanse Scene to: Remove noise and artifacts from kept scenes"))
                            cleanse_button704 = gr.Button(
                            "Cleanse Scenes " + SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)

                        # EXPORT TO VIDEO BLENDER
                        with gr.Tab(SimpleIcons.MICROSCOPE + " Video Blend Scene",
                                    id=self.TAB_EXTRA_VIDEO_BLEND_SCENE):
                            gr.Markdown(
                        "**_Create a Video Blender project for advanced scene restoration_**")
                            scene_id_707 = gr.Number(value=-1, label="Scene Index")
                            with gr.Row():
                                message_box707 = gr.Markdown(
                                    format_markdown(
                    "Click Video Blend Scene to: Create a Video Blender project for the scene"))
                            export_button707 = gr.Button(
                        "Video Blend Scene", variant="stop", scale=0)

                    # EXPORT KEPT SCENES
                    with gr.Tab(SimpleIcons.HEART_EXCLAMATION + " Import/Export Scenes", id=self.TAB_EXTRA_EXPORT_SCENES):
                        with gr.Tabs():
                            with gr.Tab(SimpleIcons.HEART_EXCLAMATION + " Export Kept Scenes"):
                                gr.Markdown("**_Save Kept Scenes as a New Project_**")
                                with gr.Row():
                                    export_path_703 = gr.Textbox(label="Exported Project Root Directory", max_lines=1,
                                            info="Enter a path on this server for the root directory of the new project",
                                            value=lambda : Session().get("last-video-remixer-export-dir"))
                                    project_name_703 = gr.Textbox(label="Exported Project Name", max_lines=1,
                                            info="Enter a name for the new project")
                                with gr.Row():
                                    cut_exported_703 = gr.Checkbox(
        label="Cut Exported Scenes From Source Project (Speeds Up Export)",
        info="If checked, the exported scenes will be removed from the currently loaded project")
                                    return_703 = gr.Button(visible=False, value="Return to Current Project (Use if scenes were cut)", variant="primary")
                                with gr.Row():
                                    message_box703 = gr.Markdown(format_markdown("Click Export Project to: Save the kept scenes as a new project"))
                                export_project_703 = gr.Button("Export Project " + SimpleIcons.SLOW_SYMBOL,
                                                        variant="stop")
                                with gr.Row():
                                    result_box703 = gr.Textbox(label="New Project Path", max_lines=1, visible=False)
                                    open_result703 = gr.Button("Open New Project", visible=False, scale=0, variant="primary")
                            with gr.Tab(SimpleIcons.HEART_EXCLAMATION + " Import Scenes"):
                                gr.Markdown("**_Import Scenes Exported from the Same Source Video_**")
                                with gr.Row():
                                    import_path_7032 = gr.Textbox(label="Path to Project to Import", max_lines=1,
                                            info="Enter a path on this server to the directory containing the project to import")
                                with gr.Row():
                                    allow_overlap_7032 = gr.Checkbox(label="Allow Import of Overlapping Scene Ranges",
                                                                     info="May cause unknown effects if scenes have overlapping frames")
                                with gr.Row():
                                    message_box7032 = gr.Markdown(format_markdown("Click Import Project to: Add the project's scenes to this project"))
                                import_project_7032 = gr.Button("Import Project " + SimpleIcons.SLOW_SYMBOL,
                                                        variant="stop")

                    # MANAGE STORAGE
                    with gr.Tab(SimpleIcons.HERB +" Manage Storage", id=self.TAB_EXTRA_MANAGE_STORAGE):
                        gr.Markdown("Free Disk Space by Removing Unneeded Content")
                        with gr.Tabs():

                            with gr.Tab(SimpleIcons.RECYCLE + " Purge Processed Content"):
                                gr.Markdown(
                    "**_Move the current processed content to the purged content directory_**")
                                with gr.Row():
                                    message_box715 = gr.Markdown(
                                        format_markdown(
                                "Click Purge Processed Content to: Soft-delete processed content"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    purge_button715 = gr.Button(value="Purge Processed Content",
                                                                variant="primary", scale=0)

                            with gr.Tab(SimpleIcons.WASTE_BASKET +
                                        " Empty Purged Content"):
                                gr.Markdown(
                "**_Permanently delete content moved to the purged content directory_**")
                                with gr.Row():
                                    delete_purged_710 = gr.Checkbox(
                                        label="Permanently Delete Purged Content")
                                with gr.Row():
                                    message_box710 = gr.Markdown(
                                        format_markdown(
                    "Click Delete Purged Content to: Permanently Remove soft-deleted content"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    delete_button710 = gr.Button(
                                        value="Delete Purged Content " +
                                        SimpleIcons.SLOW_SYMBOL, variant="primary", scale=0)

                            with gr.Tab(SimpleIcons.COLLISION + " Delete All Project Content"):
                                gr.Markdown(
                                "**_Delete all processed project content (except videos)_**")
                                with gr.Row():
                                    delete_all_713 = gr.Checkbox(
                                        label="Permanently Delete All Generated Project Data")
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(
        "Deletes all created project content. **Does not delete original and remixed videos.**")
                                with gr.Row():
                                    message_box713 = gr.Markdown(
                                        format_markdown(
                "Click Delete Processed Content to: Permanently Remove all processed project content"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    delete_button713 = gr.Button(
                                        value="Delete All Project Content " +\
                                            SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)

                            with gr.Tab(SimpleIcons.MENDING_HEART + " Recover Deleted Project"):
                                gr.Markdown(
                    "**_Restore project from the original source video and project file_**")
                                with gr.Row():
                                    message_box714 = gr.Markdown(
                                        format_markdown(
                                "Click Recover Deleted Project to: Restore the currently loaded project"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    restore_button714 = gr.Button(variant="primary",
                                        value="Recover Deleted Project " +
                                        SimpleIcons.SLOW_SYMBOL, scale=0)

                            with gr.Tab(SimpleIcons.CROSSMARK +
                                        " Remove Selected Project Content"):
                                with gr.Tabs():
                                    with gr.Tab(SimpleIcons.CROSSMARK +
                                                " Remove Scene Chooser Content"):
                                        gr.Markdown(
                                "**_Delete source frame files, thumbnails and dropped scenes_**")
                                        with gr.Row():
                                            delete_source_711 = gr.Checkbox(value=True,
                                                label="Remove Source Video Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                            "Delete source video frame files used to split content into scenes.")
                                        with gr.Row():
                                            delete_dropped_711 = gr.Checkbox(
                                                label="Remove Dropped Scenes")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                    "Delete Dropped Scene files used when compiling scenes after making scene choices.")
                                        with gr.Row():
                                            delete_thumbs_711 = gr.Checkbox(label="Remove Thumbnails")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                                        "Delete Thumbnails used to display scenes in Scene Chooser.")
                                        with gr.Row():
                                            message_box711 = gr.Markdown(
                                                format_markdown(
                            "Click Delete Selected Content to: Permanently Remove the selected content"))
                                        gr.Markdown(
                                            format_markdown(
                        "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                        with gr.Row():
                                            delete_button711 = gr.Button(
                                                value="Delete Selected Content " +\
                                                SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)
                                            select_all_button711 = gr.Button(
                                                value="Select All", scale=0)
                                            select_none_button711 = gr.Button(
                                                value="Select None", scale=0)

                                    with gr.Tab(SimpleIcons.CROSSMARK +
                                                " Remove Remix Video Source Content"):
                                        gr.Markdown(
                                        "**_Clear space after final Remix Videos have been saved_**")
                                        with gr.Row():
                                            delete_kept_712 = gr.Checkbox(label="Remove Kept Scenes")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                    "Delete Kept Scene files used when compiling scenes after making scene choices.")
                                        with gr.Row():
                                            delete_resized_712 = gr.Checkbox(value=True,
                                                label="Remove Resized Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
        "Delete Resized frame files used as inputs for processing and creating remix video clips.")
                                        with gr.Row():
                                            delete_resynth_712 = gr.Checkbox(value=True,
                                                label="Remove Resynthesized Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                                            "Delete Resynthesized frame files used as inputs " +\
                                            "for processing and creating remix video clips.")
                                        with gr.Row():
                                            delete_inflated_712 = gr.Checkbox(value=True,
                                                label="Remove Inflated Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
        "Delete Inflated frame files used as inputs for processing and creating remix video clips.")
                                        with gr.Row():
                                            delete_effects_712 = gr.Checkbox(value=True,
                                                label="Remove Effects Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
        "Delete Effects frame files used as inputs for processing and creating remix video clips.")
                                        with gr.Row():
                                            delete_upscaled_712 = gr.Checkbox(value=True,
                                                label="Remove Upscaled Frames")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
        "Delete Upscaled frame files used as inputs for processing and creating remix video clips.")
                                        with gr.Row():
                                            delete_audio_712 = gr.Checkbox(label="Delete Audio Clips")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                            "Delete Audio WAV/MP3 files used as inputs for creating remix video clips.")
                                        with gr.Row():
                                            delete_video_712 = gr.Checkbox(label="Delete Video Clips")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
                                "Delete Video MP4 files used as inputs for creating remix video clips.")
                                        with gr.Row():
                                            delete_clips_712 = gr.Checkbox(
                                                label="Delete Remix Video Clips")
                                            with gr.Column(variant="compact"):
                                                gr.Markdown(
            "Delete Video+Audio MP4 files used as inputs to concatentate into the final Remix Video.")
                                        with gr.Row():
                                            message_box712 = gr.Markdown(
                                                format_markdown(
                            "Click Delete Selected Content to: Permanently Remove the selected content"))
                                        gr.Markdown(
                                            format_markdown(
                        "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                        with gr.Row():
                                            delete_button712 = gr.Button(
                                                value="Delete Selected Content " +\
                                                    SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)
                                            select_all_button712 = gr.Button(
                                                value="Select All", scale=0)
                                            select_none_button712 = gr.Button(
                                                value="Select None", scale=0)

                    # BULK PROCESSING
                    with gr.Tab(SimpleIcons.ROBOT +" Bulk Processing", id=self.TAB_EXTRA_BULK_PROCESSING):
                        gr.Markdown("Processing Across Multiple Projects")
                        with gr.Tabs():

                            with gr.Tab(SimpleIcons.FACTORY + " Create Multiple Projects"):
                                gr.Markdown(
                    "**_Create Video Remixer projects for each video in a directory_**")
                                with gr.Row():
                                    videos_path = gr.Textbox(label="Videos Path", max_lines=1,
                                placeholder="Path on this server to the videos to be remixed",
                                value=lambda : Session().get("last-bulk-create-path"))
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(
                                        format_markdown(
                        "Use the **_Remix Settings_** and **_Set Up Project_** tabs to choose project options",
                                            color="more"))
                                with gr.Row():
                                    use_native_dimensions = gr.Checkbox(label="Use Native Dimensions", value=False)
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(
                                        format_markdown(
                                    "Create projects using source video dimensions and frame rate, with no crop",
                                            color="more"))
                                with gr.Row():
                                   message_box716 = gr.Markdown(
                                        format_markdown(
                                "Click Create Projects to: Make a project for each video"))
                                gr.Markdown(
                                    format_markdown(
                                        SimpleIcons.WARNING + \
                                            " This action consumes large amounts of disk space",
                                            "warning"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    create_button716 = gr.Button(value="Create Projects",
                                                                variant="primary", scale=0)

                            with gr.Tab(SimpleIcons.MAGNIFIER + " Open Multiple Projects by State"):
                                gr.Markdown(
                                        "**_Open a project in the specified state_**")
                                with gr.Row():
                                    projects_path718 = gr.Textbox(label="Projects Path", max_lines=1,
                    placeholder="Path on this server to the Video Remixer projects to be opened",
                                value=lambda : Session().get("last-bulk-open-path"))
                                with gr.Row():
                                    project_state718 = gr.Dropdown(choices=["Settings", "Setup", "Choose", "Compile", "Process", "Save"], value="Choose", label="Project State")
                                    search_order718 = gr.Radio(choices=["First Found", "Last Found"], value="First Found", label="Search Order")
                                with gr.Row():
                                   message_box718 = gr.Markdown(
                                        format_markdown(
                            "Click Open Found Project to: Open a project in the specified state"))
                                gr.Markdown(
                                    format_markdown(
                "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                with gr.Row():
                                    open_button718 = gr.Button(value="Open Found Project",
                                                                variant="primary", scale=0)

                            with gr.Tab(SimpleIcons.TORNADO + " Process Multiple Projects"):
                                gr.Markdown(
                    "**_Perform Processing for each Video Remixer project in a directory_**")
                                with gr.Row():
                                    projects_path7170 = gr.Textbox(
                label="Projects Path", max_lines=1,
                placeholder="Path on this server to the Video Remixer projects to be processed",
                value=lambda : Session().get("last-bulk-process-path"))
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(
                                    format_markdown(
                                        "Use the **_Process Remix_** tab to choose processing options",
                                        color="more"))
                                with gr.Row():
                                    project_state7170 = gr.Radio(
                                    choices=["All found projects", "Projects in state: Process"],
                                    value="All found projects", label="Project State")
                                    gr.Column(variant="compact")

                                with gr.Row():
                                    message_box7170 = gr.Markdown(format_markdown(
                                "Click Process Projects to: Process Remix Video for each project"))
                                with gr.Row():
                                    gr.Markdown(
                    format_markdown(
                        SimpleIcons.WARNING + " This action may take a very long time to complete",
                        "warning"))
                                with gr.Row():
                                    gr.Markdown(
                                        format_markdown("Progress can be tracked in the console",
                                            color="none", italic=True, bold=False))
                                with gr.Row():
                                    process_button7170 = gr.Button(value="Process Projects",
                                                                    variant="primary",
                                                                           scale=0)

                            with gr.Tab(SimpleIcons.ROBOT + " Perform Bulk Actions"):
                                with gr.Row():
                                    process_thumbnails_7171 = gr.Checkbox(value=False,
                                        label="Recreate Thumbnails")
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(format_markdown(
                                    "Recreate Thumbnails for projects per the Set Up Project tab.",
                                            color="more"))
                                with gr.Row():
                                    process_delete_7171 = gr.Checkbox(value=False, label=
                                                                      "Delete Processed Content")
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(format_markdown(
                                            "Delete all processed project content (except videos)",
                                            color="more"))
                                with gr.Row():
                                    process_recover_7171 = gr.Checkbox(value=False,
                                        label="Recover Deleted Project")
                                    with gr.Column(variant="compact"):
                                        gr.Markdown(format_markdown(
                                "Restore project from the original source video and project file.",
                                            color="more"))
                                with gr.Row():
                                    projects_path7171 = gr.Textbox(
                    label="Projects Path", max_lines=1,
                    placeholder="Path on this server to the Video Remixer projects to be processed",
                    value=lambda : Session().get("last-bulk-action-path"))
                                    project_state7171 = gr.Dropdown(
                    choices=["Any", "Settings", "Setup", "Choose", "Compile", "Process", "Save"],
                    value="Any", label="Project State")
                                with gr.Row():
                                    message_box7171 = gr.Markdown(format_markdown(
                    "Click Process Projects to: Perform the selection actions for each project"))
                                with gr.Row():
                                    gr.Markdown(
                    format_markdown(
                        SimpleIcons.WARNING + " This action may take a very long time to complete",
                        "warning"))
                                with gr.Row():
                                    gr.Markdown(
                    format_markdown("Progress can be tracked in the console",
                        color="none", italic=True, bold=False))
                                with gr.Row():
                                    process_button7171 = gr.Button(value="Process Projects",
                                                                    variant="primary",
                                                                    scale=0)

                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_remixer_extra.render()

        next_button00.click(self.next_button00,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box00, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h, crop_offset_x, crop_offset_y,
                                    project_fps])

        next_button01.click(self.next_button01,
                           inputs=project_load_path,
                           outputs=[tabs_video_remixer, message_box01, video_info1, project_path,
                                project_fps, deinterlace, split_type, split_time, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                crop_offset_x, crop_offset_y, frame_format, project_info2, thumbnail_type,
                                min_frames_per_scene, scene_index, scene_name, scene_image,
                                scene_state, scene_info, set_scene_label, project_info4, resize,
                                resynthesize, resynth_option, inflate, inflate_by_option, inflate_slow_option,
                                upscale, upscale_option, summary_info6, output_filepath, quality_slider, volume_60])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                crop_offset_x, crop_offset_y, frame_format, deinterlace, split_time],
                           outputs=[tabs_video_remixer, message_box1, project_info2, message_box2,
                                project_load_path])

        back_button1.click(self.back_button1, outputs=tabs_video_remixer)

        reuse_prev_settings.click(self.reuse_prev_settings,
                                  outputs=[project_fps, split_type, scene_threshold,
                                           break_duration, break_ratio, resize_w, resize_h,
                                           crop_w, crop_h, crop_offset_x, crop_offset_y,
                                           frame_format, deinterlace, split_time])

        use_saved_settings.click(self.use_saved_settings,
                                  outputs=[project_fps, split_type, scene_threshold,
                                           break_duration, break_ratio, resize_w, resize_h,
                                           crop_w, crop_h, crop_offset_x, crop_offset_y,
                                           frame_format, deinterlace, split_time])

        save_settings.click(self.save_settings,
                                  inputs=[project_fps, split_type, scene_threshold,
                                           break_duration, break_ratio, resize_w, resize_h,
                                           crop_w, crop_h, crop_offset_x, crop_offset_y,
                                           frame_format, deinterlace, split_time])

        next_button2.click(self.next_button2,
                           inputs=[thumbnail_type, min_frames_per_scene, skip_detection,
                                   remove_source],
                           outputs=[tabs_video_remixer, message_box2, scene_index, scene_name,
                                    scene_image, scene_state, scene_info, set_scene_label])

        back_button2.click(self.back_button2, outputs=tabs_video_remixer)

        thumbnail_type.input(self.thumb_change, inputs=thumbnail_type, show_progress=False)

        scene_state.change(self.scene_state_button, show_progress=False,
                            inputs=[scene_name, scene_state],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        scene_index.submit(self.go_to_frame, inputs=scene_index,
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        keep_next.click(self.keep_next, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        drop_next.click(self.drop_next, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        next_scene.click(self.next_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        prev_scene.click(self.prev_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        next_keep.click(self.next_keep, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        prev_keep.click(self.prev_keep, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        first_scene.click(self.first_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        last_scene.click(self.last_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        split_scene_button.click(self.split_scene_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, scene_id_702,
                     split_percent_702, preview_image702, scene_info_702])

        choose_range_button.click(self.choose_range_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, first_scene_id_701, last_scene_id_701])

        set_scene_label.submit(self.submit_scene_label, inputs=[scene_index, set_scene_label],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        save_scene_label.click(self.click_scene_label, inputs=[scene_index, set_scene_label],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        prev_labeled_scene.click(self.prev_labeled_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        next_labeled_scene.click(self.next_labeled_scene, show_progress=False,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        auto_label_scenes.click(self.auto_label_scenes,
                                outputs=[scene_index, scene_name, scene_image, scene_state,
                                         scene_info, set_scene_label])

        auto_title_scenes.click(self.auto_title_scenes,
                                outputs=[scene_index, scene_name, scene_image, scene_state,
                                         scene_info, set_scene_label])

        reset_scene_labels.click(self.reset_scene_labels,
                                outputs=[scene_index, scene_name, scene_image, scene_state,
                                        scene_info, set_scene_label])

        add_2x_slomo.click(self.add_2x_slomo, inputs=scene_index,
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        add_4x_slomo.click(self.add_4x_slomo, inputs=scene_index,
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        add_8x_slomo.click(self.add_8x_slomo, inputs=scene_index,
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        keep_all_button.click(self.keep_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        drop_all_button.click(self.drop_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        invert_choices_button.click(self.invert_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_name],
                            outputs=[scene_index, scene_name, scene_image, scene_state,
                                     scene_info, set_scene_label])

        drop_processed_button.click(self.drop_processed_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, scene_id_700])

        mark_scene.click(self.mark_scene, inputs=[scene_index, scene_name])

        merge_scenes_button.click(self.merge_scenes_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, tabs_merge_scenes,
                     first_scene_id_705, last_scene_id_705])

        next_button3.click(self.next_button3,
                           outputs=[tabs_video_remixer, project_info4])

        back_button3.click(self.back_button3, outputs=tabs_video_remixer)

        next_button4.click(self.next_button4,
                           outputs=[tabs_video_remixer, message_box4, message_box5])

        back_button4.click(self.back_button4, outputs=tabs_video_remixer)

        next_button5.click(self.next_button5,
                    inputs=[resynthesize, inflate, resize, upscale, upscale_option,
                            inflate_by_option, inflate_slow_option, resynth_option,
                            auto_save_remix, auto_delete_remix, auto_coalesce_remix,
                            keep_scene_videos, quality_slider, volume_60],
                    outputs=[tabs_video_remixer, message_box5, summary_info6, output_filepath,
                             output_filepath_custom, output_filepath_marked, output_filepath_labeled,
                             message_box60, message_box61, message_box62, message_box63])

        back_button5.click(self.back_button5, outputs=tabs_video_remixer)

        process_all.change(self.process_all_changed, inputs=process_all,
                           outputs=[resynthesize, inflate, resize, upscale],
                           show_progress=False)

        next_button60.click(self.next_button60,
                            inputs=[output_filepath, quality_slider, volume_60],
                           outputs=message_box60)

        back_button60.click(self.back_button60, outputs=tabs_video_remixer)

        next_button61.click(self.next_button61,
                        inputs=[custom_video_options, custom_audio_options, output_filepath_custom],
                        outputs=message_box61)

        back_button61.click(self.back_button61, outputs=tabs_video_remixer)

        next_button62.click(self.next_button62,
                        inputs=[marked_video_options, marked_audio_options, output_filepath_marked],
                        outputs=message_box62)

        back_button62.click(self.back_button62, outputs=tabs_video_remixer)

        next_button63.click(self.next_button63,
                        inputs=[label_text, label_font_size, label_font_color, label_font_alpha,
                                label_font_file, label_draw_shadow, label_shadow_color,
                                label_shadow_alpha, label_shadow_size, label_draw_box,
                                label_box_color, label_box_alpha, label_border_size,
                                label_position_v, label_position_h, output_filepath_labeled,
                                quality_slider_labeled, volume_63],
                        outputs=message_box63)

        back_button63.click(self.back_button63, outputs=tabs_video_remixer)

        drop_button700.click(self.drop_button700, inputs=scene_id_700, outputs=message_box700)

        choose_button701.click(self.choose_button701,
                               inputs=[first_scene_id_701, last_scene_id_701, scene_state_701],
                               outputs=[tabs_video_remixer, message_box701, scene_index,
                                        scene_name, scene_image, scene_state, scene_info,
                                        set_scene_label])

        scene_id_702.input(self.update_preview_scene_id, inputs=[scene_id_702, split_percent_702],
                                outputs=[preview_image702, scene_info_702], show_progress=True)

        split_percent_702.change(self.update_preview_split_percent,
                                inputs=[scene_id_702, split_percent_702],
                                outputs=[preview_image702, scene_info_702], show_progress=False)

        split_percent_alt_702.change(self.update_preview_split_percent_alt,
                                inputs=[scene_id_702, split_percent_alt_702],
                                outputs=[preview_image702, scene_info_702],
                                show_progress=False)

        goto_0_702.click(self.goto_0_702, outputs=split_percent_702, show_progress=False)

        prev_minute_702.click(self.prev_minute_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        goto_50_702.click(self.goto_50_702, outputs=split_percent_702, show_progress=False)

        next_minute_702.click(self.next_minute_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        goto_100_702.click(self.goto_100_702, outputs=split_percent_702, show_progress=False)

        prev_second_702.click(self.prev_second_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        prev_frame_702.click(self.prev_frame_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        next_frame_702.click(self.next_frame_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        next_second_702.click(self.next_second_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        go_to_s_button702.click(self.go_to_s_click702,
                                inputs=[scene_id_702, split_percent_702, go_to_s_702],
                                outputs=split_percent_702, show_progress=False)

        go_to_s_702.submit(self.go_to_s_submit702,
                                inputs=[scene_id_702, split_percent_702, go_to_s_702],
                                outputs=split_percent_702, show_progress=False)

        go_to_f_button702.click(self.go_to_f_click702,
                                inputs=[scene_id_702, split_percent_702, go_to_f_702],
                                outputs=split_percent_702, show_progress=False)

        go_to_f_702.submit(self.go_to_f_submit702,
                                inputs=[scene_id_702, split_percent_702, go_to_f_702],
                                outputs=split_percent_702, show_progress=False)


        use_alt_split_702.change(self.use_alt_split_change,
                                inputs=[use_alt_split_702, split_percent_702, split_percent_alt_702],
                                outputs=[split_percent_702, split_percent_alt_702],
                                show_progress=False)

        prev_keep_702.click(self.prev_keep_702,
                                inputs=[scene_id_702, split_percent_702],
                                outputs=[scene_id_702, preview_image702, scene_info_702],
                                show_progress=True)

        next_keep_702.click(self.next_keep_702,
                                inputs=[scene_id_702, split_percent_702],
                                outputs=[scene_id_702, preview_image702, scene_info_702],
                                show_progress=True)

        prev_break_702.click(self.prev_break_702,
                                inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=True)

        next_break_702.click(self.next_break_702,
                                inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=True)

        set_view_hint_702.submit(self.set_view_hint_702,
                                 inputs=[scene_id_702, split_percent_702, set_view_hint_702],
                                 outputs=[preview_image702, scene_info_702], show_progress=False)

        preview_view_hint_702.click(self.preview_view_hint_702,
                                    inputs=[scene_id_702, split_percent_702, set_view_hint_702],
                                    outputs=[preview_image702, scene_info_702], show_progress=False)

        split_keep_before_702.click(self.split_keep_before_702,
                                inputs=[scene_id_702, split_percent_702, use_alt_split_702,
                                    split_percent_alt_702],
                                outputs=[tabs_video_remixer, message_box702, use_alt_split_702,
                                            split_percent_alt_702, scene_index, scene_name,
                                            scene_image, scene_state, scene_info, set_scene_label])

        split_keep_after_702.click(self.split_keep_after_702,
                                inputs=[scene_id_702, split_percent_702, use_alt_split_702,
                                    split_percent_alt_702],
                                outputs=[tabs_video_remixer, message_box702, use_alt_split_702,
                                            split_percent_alt_702, scene_index, scene_name,
                                            scene_image, scene_state, scene_info, set_scene_label])

        split_button702.click(self.split_button702,
                              inputs=[scene_id_702, split_percent_702, use_alt_split_702,
                                      split_percent_alt_702],
                              outputs=[tabs_video_remixer, message_box702, use_alt_split_702,
                                       split_percent_alt_702, scene_index, scene_name,
                                       scene_image, scene_state, scene_info, set_scene_label])

        back_button702.click(self.back_button702, outputs=tabs_video_remixer)

        export_project_703.click(self.export_project_703,
                                 inputs=[export_path_703, project_name_703, cut_exported_703],
                                 outputs=[message_box703, result_box703, open_result703, return_703])

        return_703.click(self.return_703,
                         outputs=[tabs_video_remixer, scene_index, scene_name, scene_image,
                                  scene_state, scene_info, set_scene_label])

        open_result703.click(self.open_result703, inputs=result_box703,
                                outputs=[tabs_video_remixer, project_load_path, message_box01])

        import_project_7032.click(self.import_project_7032,
                                  inputs=[import_path_7032, allow_overlap_7032],
                                  outputs=[tabs_video_remixer, message_box7032, scene_index,
                                             scene_name, scene_image, scene_state, scene_info,
                                             set_scene_label])

        cleanse_button704.click(self.cleanse_button704, outputs=message_box704)

        merge_button705.click(self.merge_button705,
                               inputs=[first_scene_id_705, last_scene_id_705],
                               outputs=[tabs_video_remixer, message_box705, scene_index,
                                        scene_name, scene_image, scene_state, scene_info,
                                        set_scene_label])

        coalesce_button706.click(self.coalesce_button706, inputs=coalesce_scenes_706,
                               outputs=[tabs_video_remixer, message_box706, scene_index,
                                        scene_name, scene_image, scene_state, scene_info,
                                        set_scene_label])

        export_button707.click(self.export_button707,
                               inputs=scene_id_707,
                               outputs=[message_box707,
                                        self.main_tabs,
                                        self.video_blender.video_blender_tabs,
                                        self.video_blender.new_project_name,
                                        self.video_blender.new_project_path,
                                        self.video_blender.new_project_frame_rate,
                                        self.video_blender.step1_enabled,
                                        self.video_blender.step1_input,
                                        self.video_blender.step2_enabled,
                                        self.video_blender.step2_input,
                                        self.video_blender.step3_enabled,
                                        self.video_blender.step3_input,
                                        self.video_blender.step4_enabled])

        delete_button710.click(self.delete_button710,
                               inputs=delete_purged_710,
                               outputs=message_box710)

        delete_button711.click(self.delete_button711,
                               inputs=[delete_source_711, delete_dropped_711, delete_thumbs_711],
                               outputs=message_box711)

        select_all_button711.click(self.select_all_button711, show_progress=False,
                                outputs=[delete_source_711, delete_dropped_711, delete_thumbs_711])

        select_none_button711.click(self.select_none_button711, show_progress=False,
                                outputs=[delete_source_711, delete_dropped_711, delete_thumbs_711])

        delete_button712.click(self.delete_button712,
                               inputs=[delete_kept_712, delete_resized_712, delete_resynth_712,
                                       delete_inflated_712, delete_effects_712, delete_upscaled_712, delete_audio_712,
                                       delete_video_712, delete_clips_712],
                                outputs=message_box712)

        select_all_button712.click(self.select_all_button712, show_progress=False,
                                outputs=[delete_kept_712, delete_resized_712, delete_resynth_712,
                                         delete_inflated_712, delete_upscaled_712, delete_audio_712,
                                         delete_video_712, delete_clips_712])

        select_none_button712.click(self.select_none_button712, show_progress=False,
                                outputs=[delete_kept_712, delete_resized_712, delete_resynth_712,
                                         delete_inflated_712, delete_upscaled_712,
                                         delete_audio_712, delete_video_712, delete_clips_712])

        delete_button713.click(self.delete_button713, inputs=delete_all_713, outputs=message_box713)

        restore_button714.click(self.restore_button714, outputs=[tabs_video_remixer, message_box714,
                                    scene_index, scene_name, scene_image, scene_state, scene_info,
                                    set_scene_label])

        purge_button715.click(self.purge_button715, outputs=[tabs_video_remixer, message_box715])

        create_button716.click(self.create_button716,
                            inputs=[videos_path, use_native_dimensions, project_fps, split_type,
                                    scene_threshold, break_duration, break_ratio, resize_w, resize_h,
                                    crop_w, crop_h, crop_offset_x, crop_offset_y, frame_format,
                                    deinterlace, split_time, thumbnail_type, min_frames_per_scene,
                                    remove_source],
                            outputs=message_box716)

        process_button7170.click(self.process_button7170,
                            inputs=[projects_path7170, project_state7170, resynthesize, inflate,
                                    resize, upscale, upscale_option, inflate_by_option,
                                    inflate_slow_option, resynth_option, auto_save_remix,
                                    auto_delete_remix, auto_coalesce_remix, keep_scene_videos,
                                    quality_slider, volume_60],
                            outputs=message_box7170)

        process_button7171.click(self.process_button7171,
                            inputs=[projects_path7171, project_state7171, process_thumbnails_7171,
                                    process_delete_7171, process_recover_7171, thumbnail_type],
                            outputs=message_box7171)

        open_button718.click(self.open_button718,
                             inputs=[projects_path718, project_state718, search_order718],
                             outputs=[message_box718, tabs_video_remixer, project_load_path,
                                      message_box01])

    def _gather_fonts(self):
        fonts = get_files(self.FONTS_ROOT, "ttf")
        result = []
        for font in fonts:
            _, filename, _ = split_filepath(font)
            result.append(filename)
        return sorted(result)

    ### REMIX HOME EVENT HANDLERS

    # User has clicked New Project > from Remix Home
    def _next_button00(self, video_path):
        try:
            self.state = VideoRemixerState.new_project(self.config.remixer_settings,
                                                       self.config.ffmpeg_settings["global_options"],
                                                       self.log)

            self.processor = VideoRemixerProcessor(self.state,
                                                   self.engine,
                                                   self.config.engine_settings,
                                                   self.config.realesrgan_settings,
                                                   self.config.ffmpeg_settings["global_options"],
                                                   self.log)

            self.state.ingest.ingest_video(video_path)

            self.state.video_info1 = VideoRemixerReports(self.state, self.log).ingested_video_report()

            return True, None
        except ValueError as error:
            return False, str(error)

    def next_button00(self, video_path):
        empty_args = dummy_args(9)
        if not video_path:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   format_markdown("Enter a path to a video on this server to get started", "warning"), \
                   *empty_args

        if not os.path.exists(video_path):
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   format_markdown(f"File '{video_path}' was not found", "error"), \
                   *empty_args

        success, message = self._next_button00(video_path)
        if not success:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   format_markdown(str(message), "error"), \
                   *empty_args

        # don't save yet, user may change project path next
        self.state.save_progress("settings", save_project=False)

        return gr.update(selected=self.TAB_REMIX_SETTINGS), \
            format_markdown(self.TAB00_DEFAULT_MESSAGE), \
            self.state.video_info1, \
            self.state.project_path, \
            self.state.resize_w, \
            self.state.resize_h, \
            self.state.crop_w, \
            self.state.crop_h, \
            self.state.crop_offset_x, \
            self.state.crop_offset_y, \
            self.state.project_fps

    # User has clicked Open Project > from Remix Home
    def _next_button01(self, project_path):
        try:
            project_file = VideoRemixerProject.determine_project_filepath(project_path)
        except ValueError as error:
            self.log(f"error determining project filepath from '{project_path}': {error}")
            raise error

        try:
            remixer_settings = self.config.remixer_settings
            global_options = self.config.ffmpeg_settings["global_options"]
            self.state = VideoRemixerProject.load(project_file, remixer_settings, global_options,
                                                  self.log)
        except ValueError as error:
            self.log(f"error loading project from '{project_path}': {error}")
            raise error

        if self.state.project_ported(project_file):
            try:
                self.state = VideoRemixerProject.load_ported(self.state.project_path, project_file,
                                                             remixer_settings, global_options,
                                                             self.log)
            except ValueError as error:
                self.log(f"error opening ported project from '{project_file}': {error}")
                raise error

        self.processor = VideoRemixerProcessor(self.state,
                                               self.engine,
                                               self.config.engine_settings,
                                               self.config.realesrgan_settings,
                                               global_options,
                                               self.log)

        return self.state.project.post_load_integrity_check()

    def next_button01(self, project_path):
        empty_args = dummy_args(38)
        if not project_path:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   format_markdown("Enter a path to a Video Remixer project directory on this server to get started", "warning"), \
                   *empty_args

        if not os.path.exists(project_path):
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   format_markdown(f"Directory '{project_path}' was not found", "error"), \
                   *empty_args

        messages = self._next_button01(project_path)

        if messages:
            message_text = format_markdown(messages, "warning")
        else:
            message_text = format_markdown(self.TAB01_DEFAULT_MESSAGE)
        return_to_tab = self._get_progress_tab()
        scene_details = self.scene_chooser_details(self.state.tryattr("current_scene", 0))

        Session().set("last-video-remixer-project", project_path)
        self.state.invalidate_split_scene_cache()

        return gr.update(selected=return_to_tab), \
            message_text, \
            self.state.tryattr("video_info1"), \
            self.state.tryattr("project_path"), \
            self.state.tryattr("project_fps", self.config.remixer_settings["def_project_fps"]), \
            self.state.tryattr("deinterlace", self.state.project.SAFETY_DEFAULTS["deinterlace"]), \
            self.state.tryattr("split_type", self.state.project.SAFETY_DEFAULTS["split_type"]), \
            self.state.tryattr("split_time", self.state.project.SAFETY_DEFAULTS["split_time"]), \
            self.state.tryattr("scene_threshold", self.state.project.SAFETY_DEFAULTS["scene_threshold"]), \
            self.state.tryattr("break_duration", self.state.project.SAFETY_DEFAULTS["break_duration"]), \
            self.state.tryattr("break_ratio", self.state.project.SAFETY_DEFAULTS["break_ratio"]), \
            self.state.tryattr("resize_w"), \
            self.state.tryattr("resize_h"), \
            self.state.tryattr("crop_w"), \
            self.state.tryattr("crop_h"), \
            self.state.tryattr("crop_offset_x", self.state.project.SAFETY_DEFAULTS["crop_offsets"]), \
            self.state.tryattr("crop_offset_y", self.state.project.SAFETY_DEFAULTS["crop_offsets"]), \
            self.state.tryattr("frame_format", self.state.project.SAFETY_DEFAULTS["frame_format"]), \
            self.state.tryattr("project_info2"), \
            self.state.tryattr("thumbnail_type", self.state.project.SAFETY_DEFAULTS["thumbnail_type"]), \
            self.state.tryattr("min_frames_per_scene", self.state.project.SAFETY_DEFAULTS["min_frames_per_scene"]), \
            *scene_details, \
            self.state.tryattr("project_info4"), \
            self.state.tryattr("resize", self.state.project.SAFETY_DEFAULTS["resize"]), \
            self.state.tryattr("resynthesize", self.state.project.SAFETY_DEFAULTS["resynthesize"]), \
            self.state.tryattr("resynth_option", self.state.project.SAFETY_DEFAULTS["resynth_option"]), \
            self.state.tryattr("inflate", self.state.project.SAFETY_DEFAULTS["inflate"]), \
            self.state.tryattr("inflate_by_option", self.state.project.SAFETY_DEFAULTS["inflate_by_option"]), \
            self.state.tryattr("inflate_slow_option", self.state.project.SAFETY_DEFAULTS["inflate_slow_option"]), \
            self.state.tryattr("upscale", self.state.project.SAFETY_DEFAULTS["upscale"]), \
            self.state.tryattr("upscale_option", self.state.project.SAFETY_DEFAULTS["upscale_option"]), \
            self.state.tryattr("summary_info6"), \
            self.state.tryattr("output_filepath"), \
            self.state.tryattr("output_quality", self.state.project.SAFETY_DEFAULTS["output_quality"]), \
            self.state.tryattr("output_volume", self.state.project.SAFETY_DEFAULTS["output_volume"])

    def _get_progress_tab(self) -> int:
        try:
            progress = self.state.progress[:-1] \
                if self.state.progress[-1] == self.state.STICKY_PROGRESS \
                else self.state.progress
            return self.PROGRESS_STEPS[progress]
        except:
            return self.PROGRESS_STEPS["home"]

    ### REMIX SETTINGS EVENT HANDLERS
    def _next_button1(self,
                      project_path,
                      project_fps,
                      split_type,
                      scene_threshold,
                      break_duration,
                      break_ratio,
                      resize_w,
                      resize_h,
                      crop_w,
                      crop_h,
                      crop_offset_x,
                      crop_offset_y,
                      frame_format,
                      deinterlace,
                      split_time):

        # this is first project write
        self.state.project_path = project_path
        self.log(f"creating project path {project_path}")
        create_directory(project_path)

        self.state.project_fps = project_fps
        self.state.split_type = split_type
        self.state.scene_threshold = scene_threshold
        self.state.break_duration = break_duration
        self.state.break_ratio = break_ratio
        self.state.resize_w = int(resize_w)
        self.state.resize_h = int(resize_h)
        self.state.crop_w = int(crop_w)
        self.state.crop_h = int(crop_h)
        self.state.crop_offset_x = int(crop_offset_x)
        self.state.crop_offset_y = int(crop_offset_y)
        self.state.frame_format = frame_format
        self.state.split_time = split_time
        self.state.deinterlace = deinterlace
        self.state.processed_content_invalid = True
        self.state.project_info2 =  VideoRemixerReports(self.state, self.log).project_settings_report()

        # this is the first time project progress advances
        # user will expect to return to the setup tab on reopening
        self.log(f"saving new project at {self.state.project.project_filepath()}")
        self.state.save_progress("setup")

    def next_button1(self,
                     project_path,
                     project_fps,
                     split_type,
                     scene_threshold,
                     break_duration,
                     break_ratio,
                     resize_w,
                     resize_h,
                     crop_w,
                     crop_h,
                     crop_offset_x,
                     crop_offset_y,
                     frame_format,
                     deinterlace,
                     split_time):
        empty_args = dummy_args(3)
        # self.state.project_path = project_path

        if not is_safe_path(project_path):
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(f"The project path is not valid", "warning"),\
                *empty_args

        # this prevents updating existing project settings
        # if os.path.exists(project_path):
        #     return gr.update(selected=self.TAB_REMIX_SETTINGS), \
        #         format_markdown(f"The project path is already in use", "warning"),\
        #         *empty_args

        if resize_h < 1 or resize_w < 1 or crop_h < 1 or crop_w < 1:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(f"Resize/Crop values should be >= 1", "warning"),\
                *empty_args

        if crop_h > resize_h or crop_w > resize_w:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(f"Crop values should be <= Resize values", "warning"),\
                *empty_args

        if crop_offset_x < -1 or \
           crop_offset_x > resize_w - crop_w or \
           crop_offset_y < -1 or \
           crop_offset_y > resize_h - crop_h:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(f"Crop Offset values should be >= -1 and <= (Resize - Crop)",
                                "warning"),\
                *empty_args

        if split_time < 1:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(f"Scene Split Seconds should be >= 1", "warning"),\
                *empty_args

        # if redoing this step to save settings and the deinterlace option changed,
        # the source frames will need to be rendered again from the source video
        # if the video is processed again on the next tab
        self.state.source_frames_invalid = deinterlace != self.state.deinterlace

        try:
            self._next_button1(project_path,
                               project_fps,
                               split_type,
                               scene_threshold,
                               break_duration,
                               break_ratio,
                               resize_w,
                               resize_h,
                               crop_w,
                               crop_h,
                               crop_offset_x,
                               crop_offset_y,
                               frame_format,
                               deinterlace,
                               split_time)

            Session().set("last-video-remixer-project", project_path)

            # memorize these settings
            self.save_named_settings("last-video-remixer-settings", self.state)

            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                format_markdown(self.TAB1_DEFAULT_MESSAGE), \
                self.state.project_info2, \
                format_markdown(self.TAB2_DEFAULT_MESSAGE), \
                project_path

        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                format_markdown(str(error), "error"), \
                *empty_args

    def back_button1(self):
        return gr.update(selected=self.TAB_REMIX_HOME)

    # SAVED SETTINGS

    def save_named_settings(self, name, state : VideoRemixerState):
        settings = {}
        settings["project_fps"] = state.project_fps
        settings["split_type"] = state.split_type
        settings["scene_threshold"] = state.scene_threshold
        settings["break_duration"] = state.break_duration
        settings["break_ratio"] = state.break_ratio
        settings["resize_w"] = state.resize_w
        settings["resize_h"] = state.resize_h
        settings["crop_w"] = state.crop_w
        settings["crop_h"] = state.crop_h
        settings["crop_offset_x"] = state.crop_offset_x
        settings["crop_offset_y"] = state.crop_offset_y
        settings["frame_format"] = state.frame_format
        settings["deinterlace"] = state.deinterlace
        settings["split_time"] = state.split_time
        Session().set(name, settings)

    def use_named_settings(self, name, ignore_missing=True):
        settings = Session().get(name)
        if settings:
            try:
                return \
                    settings["project_fps"], \
                    settings["split_type"], \
                    settings["scene_threshold"], \
                    settings["break_duration"], \
                    settings["break_ratio"], \
                    settings["resize_w"], \
                    settings["resize_h"], \
                    settings["crop_w"], \
                    settings["crop_h"], \
                    settings["crop_offset_x"], \
                    settings["crop_offset_y"], \
                    settings["frame_format"], \
                    settings["deinterlace"], \
                    settings["split_time"]
            except Exception as error:
                self.log(f"error accessing saved settings {name}: {error}")
        if ignore_missing:
            return self.use_default_settings()
        else:
            raise ValueError(f"saved settings {name} not found")

    def use_default_settings(self):
        return \
            self.config.remixer_settings["def_project_fps"], \
            self.state.SAFETY_DEFAULTS["split_type"], \
            self.state.SAFETY_DEFAULTS["scene_threshold"], \
            self.state.SAFETY_DEFAULTS["break_duration"], \
            self.state.SAFETY_DEFAULTS["break_ratio"], \
            self.state.SAFETY_DEFAULTS["resize_w"], \
            self.state.SAFETY_DEFAULTS["resize_h"], \
            self.state.SAFETY_DEFAULTS["crop_w"], \
            self.state.SAFETY_DEFAULTS["crop_h"], \
            self.state.SAFETY_DEFAULTS["crop_offsets"], \
            self.state.SAFETY_DEFAULTS["crop_offsets"], \
            self.state.SAFETY_DEFAULTS["frame_format"], \
            self.state.SAFETY_DEFAULTS["deinterlace"], \
            self.state.SAFETY_DEFAULTS["split_time"]

    def reuse_prev_settings(self):
        return self.use_named_settings("last-video-remixer-settings")

    def use_saved_settings(self, ignore_errors=True):
        return self.use_named_settings("saved-video-remixer-settings", ignore_errors)

    def save_settings(self, project_fps, split_type, scene_threshold, break_duration, break_ratio,
                      resize_w, resize_h, crop_w, crop_h, crop_offset_x, crop_offset_y,
                      frame_format, deinterlace, split_time):
        state = VideoRemixerState(None, None, self.log)
        state.project_fps = project_fps
        state.split_type = split_type
        state.scene_threshold = scene_threshold
        state.break_duration = break_duration
        state.break_ratio = break_ratio
        state.resize_w = resize_w
        state.resize_h = resize_h
        state.crop_w = crop_w
        state.crop_h = crop_h
        state.crop_offset_x = crop_offset_x
        state.crop_offset_y = crop_offset_y
        state.frame_format = frame_format
        state.deinterlace = deinterlace
        state.split_time = split_time
        self.save_named_settings("saved-video-remixer-settings", state)

    ### SET UP PROJECT EVENT HANDLERS

    # User has clicked Set Up Project from Set Up Project
    def _next_button2(self, thumbnail_type, min_frames_per_scene, skip_detection, remove_source):
        self.state.thumbnail_type = thumbnail_type
        self.state.min_frames_per_scene = min_frames_per_scene
        self.state.save()

        # TODO this enormous conditional is messy
        # TODO some logic should be moved to ingest class
        if not skip_detection or not self.state.ingest.scenes_present():
            try:
                self.log(f"copying video from {self.state.source_video} to project path")
                self.state.ingest.save_original_video(prevent_overwrite=True)
            except ValueError as error:
                # ignore, don't copy the file a second time if the user is restarting here
                self.log(f"ignoring: {error}")

            self.state.save()

            try:
                self.log(f"creating source audio from {self.state.source_video}")
                source_audio_crf = self.config.remixer_settings["source_audio_crf"]
                self.state.ingest.create_source_audio(source_audio_crf, prevent_overwrite=True)
            except ValueError as error:
                self.log(f"ignoring: {error}")

            self.state.save()

            # user may be redoing project set up
            # settings changes could affect already-processed content
            self.log("resetting project on rendering for project settings")
            self.state.project.reset_at_project_settings()

            # split video into frames, avoid doing again if redoing setup
            # unless the source frames were flagged invalid in the previous step
            self.log("splitting source video into frames")
            prevent_overwrite = not self.state.source_frames_invalid
            ffcmd = self.state.ingest.render_source_frames(prevent_overwrite=prevent_overwrite)
            if not ffcmd:
                self.log("rendering source frames skipped")
            else:
                self.state.save()
                self.log(f"FFmpeg command: {ffcmd}")

            self.state.scenes_path = os.path.join(self.state.project_path,
                                                  VideoRemixerState.SCENES_PATH)
            self.state.dropped_scenes_path = os.path.join(self.state.project_path,
                                                          VideoRemixerState.DROPPED_SCENES_PATH)
            self.log(f"creating scenes directory {self.state.scenes_path}")
            create_directory(self.state.scenes_path)
            self.log(f"creating dropped scenes directory {self.state.dropped_scenes_path}")
            create_directory(self.state.dropped_scenes_path)

            self.state.save()

            # split frames into scenes
            error = self.state.ingest.split_scenes(prevent_overwrite=False, move_files=remove_source)
            if error:
                raise ValueError(f"There was an error splitting the source video: {error}")

            self.state.save()

            if self.state.min_frames_per_scene > 0:
                self.state.ingest.consolidate_scenes()
                self.state.save()

            self.state.scene_names = sorted(get_directories(self.state.scenes_path))

            try:
                self.log("enhance source video info with extra data including frame dimensions")
                self.state.ingest.enhance_video_info(ignore_errors=False)
                self.state.save()
            except ValueError as error:
                raise ValueError(f"There was an error retrieving source frame dimensions: {error}")

            if remove_source:
                self.log(f"removing source frames from {self.state.frames_path}")
                remove_directories([self.state.frames_path])

            # if there's only one scene, assume it should be kept to save some time
            if len(self.state.scene_names) < 2:
                self.state.keep_all_scenes()
            else:
                self.state.drop_all_scenes()

            self.state.current_scene = 0
            self.state.save()

        try:
            self.state.ingest.create_thumbnails()
        except ValueError as error:
            raise ValueError(f"There was an error creating thumbnails from the source video: {error}")

        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))
        self.state.save()

        # thumbnails may be being recreated
        # clear cache to avoid display problems with cached thumbnails
        self.state.invalidate_split_scene_cache()

        self.state.clips_path = os.path.join(self.state.project_path, self.state.CLIPS_PATH)
        self.log(f"creating clips directory {self.state.clips_path}")
        create_directory(self.state.clips_path)

        # user will expect to return to scene chooser on reopening
        self.state.save_progress("choose")

    def next_button2(self, thumbnail_type, min_frames_per_scene, skip_detection, remove_source):
        empty_args = dummy_args(6)

        if not self.state.project_path:
            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                   format_markdown(f"Project settings have not yet been saved on the previous tab", "error"), \
                   *empty_args

        try:
            self._next_button2(thumbnail_type, min_frames_per_scene, skip_detection, remove_source)
        except ValueError as error:
            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                format_markdown(f"There was an error setting up the project: {error}", "error"), \
                *empty_args

        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
               format_markdown(self.TAB2_DEFAULT_MESSAGE), \
               *self.scene_chooser_details(self.state.current_scene)

    def back_button2(self):
        return gr.update(selected=self.TAB_REMIX_SETTINGS)

    def thumb_change(self, thumbnail_type):
        if self.state:
            self.state.thumbnail_type = thumbnail_type
            if self.state.project_path:
                self.log(f"Saving project after hot-setting thumbnail type to {thumbnail_type}")
                self.state.save()

    ### SCENE CHOOSER EVENT HANDLERS

    # User has clicked on the Keep or Drop radio button
    def scene_state_button(self, scene_name, scene_state):
        if scene_name:
            self.state.scene_states[scene_name] = scene_state
            self.state.save()
        return self.scene_chooser_details(self.state.current_scene)

    def go_to_frame(self, scene_index):
        try:
            scene_index = int(scene_index)
        except:
            scene_index = 0
        if scene_index < 0:
            scene_index = 0
        else:
            last_scene = len(self.state.scene_names) - 1
            if scene_index > last_scene:
                scene_index = last_scene
        self.state.current_scene = scene_index
        return self.scene_chooser_details(self.state.current_scene)

    def keep_next(self, scene_index, scene_name):
        self.state.scene_states[scene_name] = self.state.KEEP_MARK
        self.state.save()
        return self.next_scene(scene_index, scene_name)

    def drop_next(self, scene_index, scene_name):
        self.state.scene_states[scene_name] = self.state.DROP_MARK
        self.state.save()
        return self.next_scene(scene_index, scene_name)

    def next_scene(self, scene_index, scene_name):
        if scene_index < len(self.state.scene_names)-1:
            scene_index += 1
            self.state.current_scene = scene_index
        return self.scene_chooser_details(self.state.current_scene)

    def prev_scene(self, scene_index, scene_name):
        if scene_index > 0:
            scene_index -= 1
            self.state.current_scene = scene_index
        return self.scene_chooser_details(self.state.current_scene)

    def scan_for_keep(self, range):
        for index in range:
            scene_name = self.state.scene_names[index]
            if self.state.scene_states[scene_name] == self.state.KEEP_MARK:
                self.state.current_scene = index
                break
        return self.scene_chooser_details(self.state.current_scene)

    def next_keep(self, scene_index, scene_name):
        return self.scan_for_keep(range(scene_index+1, len(self.state.scene_names)))

    def prev_keep(self, scene_index, scene_name):
        return self.scan_for_keep(range(scene_index-1, -1, -1))

    def first_scene(self, scene_index, scene_name):
        self.state.current_scene = 0
        return self.scene_chooser_details(self.state.current_scene)

    def last_scene(self, scene_index, scene_name):
        self.state.current_scene = len(self.state.scene_names) - 1
        return self.scene_chooser_details(self.state.current_scene)

    def split_scene_shortcut(self, scene_index):
        default_percent = 50.0
        scene_index = int(scene_index)
        display_frame = self.state.compute_preview_frame(scene_index, default_percent)
        _, _, _, _, scene_info, _ = self.state.scene_chooser_details(scene_index, self.GAP)
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_SPLIT_SCENE), \
            scene_index, \
            default_percent, \
            display_frame, \
            scene_info

    def choose_range_shortcut(self, scene_index):
        scene_index, alt_scene = self.get_marked_pair(scene_index)
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_CHOOSE_RANGE), \
            scene_index, alt_scene

    # SCENE LABELS

    def save_scene_label(self, scene_index, scene_label):
        if scene_label:
            self.state.set_scene_label(scene_index, scene_label)
        else:
            self.state.clear_scene_label(scene_index)
        self.state.save()
        return self.scene_chooser_details(self.state.current_scene)

    def click_scene_label(self, scene_index, scene_label):
        return self.save_scene_label(scene_index, scene_label)

    def submit_scene_label(self, scene_index, scene_label):
        return self.save_scene_label(scene_index, scene_label)

    def scan_for_label(self, range):
        for index in range:
            scene_name = self.state.scene_names[index]
            if scene_name in self.state.scene_labels:
                self.state.current_scene = index
                break
        return self.scene_chooser_details(self.state.current_scene)

    def next_labeled_scene(self, scene_index, scene_name):
        return self.scan_for_label(range(scene_index+1, len(self.state.scene_names)))

    def prev_labeled_scene(self, scene_index, scene_name):
        return self.scan_for_label(range(scene_index-1, -1, -1))

    # TODO move
    # add sorting marks to each scene label, removing existing ones first
    def auto_label_scenes(self):
        num_scenes = len(self.state.scene_names)
        num_width = len(str(num_scenes))
        # remove existing sort marks
        for scene_index in range(len(self.state.scene_names)):
            scene_name = self.state.scene_names[scene_index]
            scene_label = self.state.scene_labels.get(scene_name)
            _, hint_mark, title = self.state.split_label(scene_label)
            formatted_label = self.state.compose_label(None, hint_mark, title)
            self.state.set_scene_label(scene_index, formatted_label)
        for scene_index in range(len(self.state.scene_names)):
            scene_name = self.state.scene_names[scene_index]
            scene_label = self.state.scene_labels.get(scene_name)
            _, hint_mark, title = self.state.split_label(scene_label)
            sort_mark = str(scene_index).zfill(num_width)
            formatted_label = self.state.compose_label(sort_mark, hint_mark, title)
            self.state.set_scene_label(scene_index, formatted_label)
        self.state.clean_scene_labels()
        return self.scene_chooser_details(self.state.current_scene)

    # TODO more inspired default title, move
    # add a default title to each scene label, if not already set
    def auto_title_scenes(self):
        for scene_index in range(len(self.state.scene_names)):
            scene_name = self.state.scene_names[scene_index]
            title = self.state.scene_title(scene_name)
            scene_label = self.state.scene_labels.get(scene_name)
            sort_mark, hint_mark, existing_title = self.state.split_label(scene_label)
            if not existing_title:
                formatted_label = self.state.compose_label(sort_mark, hint_mark, title)
                self.state.set_scene_label(scene_index, formatted_label)
        self.state.clean_scene_labels()
        return self.scene_chooser_details(self.state.current_scene)

    def reset_scene_labels(self):
        self.state.clear_all_scene_labels()
        return self.scene_chooser_details(self.state.current_scene)

    def add_2x_slomo(self, scene_index):
        self.state.add_slomo(scene_index, "I:2A")
        return self.scene_chooser_details(self.state.current_scene)

    def add_4x_slomo(self, scene_index):
        self.state.add_slomo(scene_index, "I:4A")
        return self.scene_chooser_details(self.state.current_scene)

    def add_8x_slomo(self, scene_index):
        self.state.add_slomo(scene_index, "I:8A")
        return self.scene_chooser_details(self.state.current_scene)

    # DANGER ZONE

    def keep_all_scenes(self, scene_index, scene_name):
        self.state.keep_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_all_scenes(self, scene_index, scene_name):
        self.state.drop_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def invert_all_scenes(self, scene_index, scene_name):
        self.state.invert_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_processed_shortcut(self, scene_index):
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_DROP_PROCESSED), \
            scene_index

    def merge_scenes_shortcut(self, scene_index):
        scene_index, alt_scene = self.get_marked_pair(scene_index)
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_MERGE_SCENES), \
            gr.update(selected=self.TAB_EXTRA_MERGE_RANGE), \
            scene_index, alt_scene

    def mark_scene(self, scene_index, scene_name):
        self.marked_scene = scene_index

    def unmark_scene(self):
        self.marked_scene = None

    def get_marked_pair(self, scene_index):
        if self.marked_scene != None:
            alt_scene = self.marked_scene
        else:
            alt_scene = scene_index + 1
            if alt_scene >= len(self.state.scene_names):
                alt_scene = scene_index
        if alt_scene < scene_index:
            alt_scene, scene_index = scene_index, alt_scene
        self.unmark_scene()
        return scene_index, alt_scene

    # given scene name such as [042-420] compute details to display in Scene Chooser
    def scene_chooser_details(self, scene_index):
        if not self.state.thumbnails:
            self.log(f"thumbnails don't exist yet in scene_chooser_details()")
            return dummy_args(6)
        try:
            return self.state.scene_chooser_details(scene_index, self.GAP)
        except ValueError as error:
            self.log(error)
            return dummy_args(6)

    # User has clicked Done Choosing Scenes from Scene Chooser
    def next_button3(self):
        if not self.state.project_path:
            return gr.update(selected=self.TAB_CHOOSE_SCENES), self.state.project_info4

        self.state.project_info4 = VideoRemixerReports(self.state, self.log).chosen_scenes_report()

        # user will expect to return to the compilation tab on reopening
        self.state.save_progress("compile")

        return gr.update(selected=self.TAB_COMPILE_SCENES), self.state.project_info4

    def back_button3(self):
        return gr.update(selected=self.TAB_SET_UP_PROJECT)

    ### COMPILE SCENES EVENT HANDLERS

    # User has clicked Compile Scenes from Compile Scenes
    def next_button4(self):
        if not self.state.project_path:
            return gr.update(selected=self.TAB_COMPILE_SCENES), \
                   format_markdown(f"The project has not yet been set up from the Set Up Project tab.", "error"), \
                   None

        self.log("moving dropped scenes to dropped scenes directory")
        self.state.recompile_scenes()

        # scene choice changes are what invalidate previously made audio clips,
        # so clear them now along with dependent remix content
        self.log("purging now-stale remix content")
        self.state.clean_remix_content(purge_from="audio_clips")

        # TODO reconcile with the line above
        # Compiling scenes implies a last state before processing,
        # and the user may expect that all content will be processed
        self.state.processed_content_invalid = True

        # user will expect to return to the processing tab on reopening
        self.state.save_progress("process")

        return gr.update(selected=self.TAB_PROC_REMIX),  \
               format_markdown(self.TAB4_DEFAULT_MESSAGE), \
               format_markdown(self.TAB5_DEFAULT_MESSAGE)

    def back_button4(self):
        return gr.update(selected=self.TAB_CHOOSE_SCENES)

    ### PROCESS REMIX EVENT HANDLERS

    # User has clicked Process Remix from Process Remix
    def _next_button5(self,
                      resynthesize,
                      inflate,
                      resize,
                      upscale,
                      upscale_option,
                      inflate_by_option,
                      inflate_slow_option,
                      resynth_option,
                      auto_save_remix,
                      auto_delete_remix,
                      auto_coalesce_remix,
                      keep_scene_videos,
                      quality,
                      volume):
        if not self.state.project_path or not self.state.scenes_path:
            raise ValueError("The project has not yet been set up from the Set Up Project tab.")

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            raise ValueError("At least one scene must be set to 'Keep' before processing can proceed")

        errors = self.state.ensure_project_dir_permissions()
        if errors:
            raise ValueError("\r\n".join(errors))

        messages = []
        if auto_coalesce_remix:
            messages += self.force_coalesce_kept_scenes()

            # get the new coalesced kept scens
            kept_scenes = self.state.kept_scenes()

        self.state.resize = resize

        self.state.resynthesize = resynthesize
        resynth_option_changed = False
        if self.state.resynth_option != None and \
                self.state.resynth_option != resynth_option:
            resynth_option_changed = True
        self.state.resynth_option = resynth_option

        self.state.inflate = inflate
        inflate_option_changed = False
        if self.state.inflate_by_option != None and \
                self.state.inflate_by_option != inflate_by_option:
            inflate_option_changed = True
        self.state.inflate_by_option = inflate_by_option
        # this affects only later audio processing so change detection isn't needed
        self.state.inflate_slow_option = inflate_slow_option

        self.state.upscale = upscale
        upscale_option_changed = False
        if self.state.upscale_option != None and self.state.upscale_option != upscale_option:
            upscale_option_changed = True
        self.state.upscale_option = upscale_option

        self.processor.prepare_process_remix(resynth_option_changed,
                                             inflate_option_changed,
                                             upscale_option_changed)

        self.processor.process_remix(kept_scenes)

        remix_report = VideoRemixerReports(self.state, self.log).generate_remix_report(
                                self.processor.processed_content_complete(self.state.RESIZE_STEP),
                                self.processor.processed_content_complete(self.state.RESYNTH_STEP),
                                self.processor.processed_content_complete(self.state.INFLATE_STEP),
                                self.processor.processed_content_complete(self.state.EFFECTS_STEP),
                                self.processor.processed_content_complete(self.state.UPSCALE_STEP))

        styled_report = style_report("Content Ready for Remix Video:", remix_report, color="info")
        self.state.summary_info6 = styled_report

        self.state.output_filepath = self.state.default_remix_filepath()
        self.state.save()

        # user will expect to return to the save remix tab on reopening
        self.state.save_progress("save")

        if auto_save_remix:
            # messages = []
            messages += self.processor.get_processing_messages(raw=True)
            try:
                self.save_mp4_video(self.state.output_filepath, quality=quality, volume=volume)
                messages.append(f"Remixed video {self.state.output_filepath} is complete.")
            except ValueError as error:
                raise ValueError(f"An error occurred while saving default video: {error}")

            if keep_scene_videos:
                scene_files = get_files(self.state.clips_path)
                if scene_files:
                    try:
                        scene_filenames = []
                        for scene_file in scene_files:
                            _, filename, ext = split_filepath(scene_file)
                            scene_filenames.append(filename + ext)
                        self.state.purge_files(self.state.project_path, scene_filenames)
                        move_files(self.state.clips_path, self.state.project_path)
                        for file in scene_files:
                            messages.append(f"Scene video {file} moved to {self.state.project_path}")
                    except Exception as error:
                        messages.append(f"An error occurred while keeping scene videos: {error}")

            if auto_delete_remix:
                try:
                    message = self.delete_all_project_content()
                    messages.append(message)
                except ValueError as error:
                    raise ValueError(f"An error occurred while deleting project content: {error}")

            return "\r\n".join(messages)
        else:
            messages += self.processor.get_processing_messages(raw=True)
            return "\r\n".join(messages)

    def next_button5(self,
                     resynthesize,
                     inflate,
                     resize,
                     upscale,
                     upscale_option,
                     inflate_by_option,
                     inflate_slow_option,
                     resynth_option,
                     auto_save_remix,
                     auto_delete_remix,
                     auto_coalesce_remix,
                     keep_scene_videos,
                     quality,
                     volume):
        empty_args = dummy_args(9)

        try:
            messages = self._next_button5(resynthesize,
                                         inflate,
                                         resize,
                                         upscale,
                                         upscale_option,
                                         inflate_by_option,
                                         inflate_slow_option,
                                         resynth_option,
                                         auto_save_remix,
                                         auto_delete_remix,
                                         auto_coalesce_remix,
                                         keep_scene_videos,
                                         quality,
                                         volume)
        except ValueError as error:
            return gr.update(selected=self.TAB_PROC_REMIX), \
                format_markdown(str(error), "error"), \
                *empty_args

        if auto_save_remix:
            return gr.update(selected=self.TAB_PROC_REMIX), \
                format_markdown(messages), \
                *empty_args

        else:
            output_filepath_custom = self.state.default_remix_filepath("CUSTOM")
            output_filepath_marked = self.state.default_remix_filepath("MARKED")
            output_filepath_labeled = self.state.default_remix_filepath("LABELED")

            message = messages or self.TAB5_DEFAULT_MESSAGE
            return gr.update(selected=self.TAB_SAVE_REMIX), \
                    format_markdown(message), \
                    self.state.summary_info6, \
                    self.state.output_filepath, \
                    output_filepath_custom, \
                    output_filepath_marked, \
                    output_filepath_labeled, \
                    format_markdown(self.TAB60_DEFAULT_MESSAGE), \
                    format_markdown(self.TAB61_DEFAULT_MESSAGE), \
                    format_markdown(self.TAB62_DEFAULT_MESSAGE), \
                    format_markdown(self.TAB63_DEFAULT_MESSAGE)

    def back_button5(self):
        return gr.update(selected=self.TAB_COMPILE_SCENES)

    def process_all_changed(self, process_all : bool):
        return process_all, process_all, process_all, process_all

    ### SAVE REMIX EVENT HANDLERS

    def next_button60(self, output_filepath, quality, volume):
        if not self.state.project_path:
            return format_markdown(
                "The project has not yet been set up from the Set Up Project tab.", "error")

        try:
            self.save_mp4_video(output_filepath, quality, volume)
            return format_markdown(f"Remixed video {output_filepath} is complete.", "highlight")
        except ValueError as error:
            return format_markdown(str(error), "error")

    def next_button61(self, custom_video_options, custom_audio_options, output_filepath):
        if not self.state.project_path:
            return format_markdown(
                "The project has not yet been set up from the Set Up Project tab.", "error")

        try:
            kept_scenes = self.processor.prepare_save_remix(output_filepath,
                                                            invalidate_video_clips=False)
            self.processor.save_custom_remix(output_filepath, kept_scenes, custom_video_options,
                                             custom_audio_options)
            return format_markdown(f"Remixed custom video {output_filepath} is complete.",
                                   "highlight")
        except ValueError as error:
            return format_markdown(str(error), "error")

    def next_button62(self, marked_video_options, marked_audio_options, output_filepath):
        if not self.state.project_path:
            return format_markdown(
                "The project has not yet been set up from the Set Up Project tab.", "error")

        try:
            kept_scenes = self.processor.prepare_save_remix(output_filepath)
            draw_text_options = {}
            draw_text_options["font_size"] = self.config.remixer_settings["marked_font_size"]
            draw_text_options["font_color"] = self.config.remixer_settings["marked_font_color"]
            draw_text_options["font_file"] = self.config.remixer_settings["marked_font_file"]
            draw_text_options["draw_box"] = self.config.remixer_settings["marked_draw_box"]
            draw_text_options["box_color"] = self.config.remixer_settings["marked_box_color"]
            draw_text_options["border_size"] = self.config.remixer_settings["marked_border_size"]
            draw_text_options["label_position_v"] = self.config.remixer_settings["marked_position_v"]
            draw_text_options["label_position_h"] = self.config.remixer_settings["marked_position_h"]
            draw_text_options["draw_shadow"] = self.config.remixer_settings["marked_draw_shadow"]
            draw_text_options["shadow_color"] = self.config.remixer_settings["marked_shadow_color"]
            draw_text_options["shadow_size"] = self.config.remixer_settings["marked_shadow_size"]

            # account for upscaling
            upscale_factor = self.processor.upscale_factor_from_options()
            draw_text_options["crop_width"] = self.state.crop_w * upscale_factor
            draw_text_options["crop_height"] = self.state.crop_h * upscale_factor

            # create labels
            labels = []
            kept_scenes = self.state.kept_scenes()
            for scene_name in kept_scenes:
                labels.append(self.state.scene_marker(scene_name))
            draw_text_options["labels"] = labels

            self.processor.save_custom_remix(output_filepath, kept_scenes, marked_video_options,
                                             marked_audio_options, draw_text_options)
            return format_markdown(f"Remixed marked video {output_filepath} is complete.",
                                   "highlight")
        except ValueError as error:
            return format_markdown(str(error), "error")

    def next_button63(self,
                      label_text,
                      label_font_size,
                      label_font_color,
                      label_font_alpha,
                      label_font_file,
                      label_draw_shadow,
                      label_shadow_color,
                      label_shadow_alpha,
                      label_shadow_size,
                      label_draw_box,
                      label_box_color,
                      label_box_alpha,
                      label_border_size,
                      label_position_v,
                      label_position_h,
                      output_filepath,
                      quality,
                      volume):
        if not self.state.project_path:
            return format_markdown("The project has not yet been set up from the Set Up Project tab.", "error")

        if not label_font_file:
           return format_markdown("The Font File must not be blank", "warning")
        font_path = os.path.join(self.FONTS_ROOT, label_font_file + ".ttf")
        if not os.path.exists(font_path):
           return format_markdown(f"The Font File {os.path.abspath(font_path)} was not found", "error")
        # FFmpeg requires forward slashes in font file path
        label_font_file = font_path.replace(r"\\", "/").replace("\\", "/")

        label_font_color = join_color_alpha(label_font_color, label_font_alpha)
        label_shadow_color = join_color_alpha(label_shadow_color, label_shadow_alpha)
        label_box_color = join_color_alpha(label_box_color, label_box_alpha)

        try:
            kept_scenes = self.processor.prepare_save_remix(output_filepath)
            draw_text_options = {}
            draw_text_options["font_size"] = label_font_size
            draw_text_options["font_color"] = label_font_color
            draw_text_options["font_file"] = label_font_file
            draw_text_options["draw_box"] = label_draw_box
            draw_text_options["box_color"] = label_box_color
            draw_text_options["border_size"] = label_border_size
            draw_text_options["label_position_v"] = label_position_v
            draw_text_options["label_position_h"] = label_position_h
            draw_text_options["draw_shadow"] = label_draw_shadow
            draw_text_options["shadow_color"] = label_shadow_color
            draw_text_options["shadow_size"] = label_shadow_size

            # account for upscaling
            upscale_factor = self.processor.upscale_factor_from_options()
            draw_text_options["crop_width"] = self.state.crop_w * upscale_factor
            draw_text_options["crop_height"] = self.state.crop_h * upscale_factor

            labels = []
            title = None
            kept_scenes = self.state.kept_scenes()
            for scene_name in kept_scenes:
                scene_label = self.state.scene_labels.get(scene_name)
                if scene_label:
                    _, _, title = self.state.split_label(scene_label)
                title = title or label_text
                labels.append(title)
            draw_text_options["labels"] = labels

            labeled_video_options = self.config.remixer_settings["labeled_ffmpeg_video"]
            labeled_audio_options = self.config.remixer_settings["labeled_ffmpeg_audio"]
            labeled_video_options = labeled_video_options.replace("<CRF>", str(quality))
            self.log(f"using labeled video options: {labeled_video_options}")
            self.log(f"using labeled audeo options: {labeled_audio_options}")

            try:
                self.processor.save_custom_remix(output_filepath, kept_scenes,
                                                 labeled_video_options, labeled_audio_options,
                                                 draw_text_options, use_scene_sorting=True,
                                                 volume=volume)
                return format_markdown(
                    f"Remixed labeled video {output_filepath} is complete.", "highlight")
            except FFRuntimeError as error:
                return format_markdown(f"Error: {error}.", "error")

        except ValueError as error:
            return format_markdown(str(error), "error")

    def back_button60(self):
        return gr.update(selected=self.TAB_PROC_REMIX)

    def back_button61(self):
        return gr.update(selected=self.TAB_PROC_REMIX)

    def back_button62(self):
        return gr.update(selected=self.TAB_PROC_REMIX)

    def back_button63(self):
        return gr.update(selected=self.TAB_PROC_REMIX)

    ### REMIX EXTRA HANDLERS

    def drop_button700(self, scene_index):
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(scene_index, (int, float)):
            return format_markdown(f"Please enter a Scene Index to get started", "warning")

        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            return format_markdown(f"Please enter a Scene Index from 0 to {last_scene}", "warning")

        removed = self.state.force_drop_processed_scene(scene_index)

        self.state.save()
        removed = "\r\n".join(removed)
        return format_markdown(f"Removed:\r\n{removed}")

    def choose_button701(self, first_scene_index, last_scene_index, scene_state):
        empty_args = dummy_args(6)
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(first_scene_index, (int, float)) \
                or not isinstance(last_scene_index, (int, float)):
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown("Please enter Scene Indexes to get started", "warning"), \
                *empty_args

        first_scene_index = int(first_scene_index)
        last_scene_index = int(last_scene_index)
        if first_scene_index < 0 \
                or first_scene_index > last_scene \
                or last_scene_index < 0 \
                or last_scene_index > last_scene:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(
                    f"Please enter valid Scene Indexes between 0 and {last_scene} to get started",
                    "warning"), \
                *empty_args

        if first_scene_index >= last_scene_index:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(
                    f"'Ending Scene Index' must be higher than 'Starting Scene Index'",
                    "warning"), \
                *empty_args

        if scene_state not in [VideoRemixerState.KEEP_MARK, VideoRemixerState.DROP_MARK]:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown("Please make a Scenes Choice to get started", "warning"), \
                *empty_args

        self.state.choose_scene_range(first_scene_index, last_scene_index, scene_state)
        self.state.current_scene = first_scene_index

        first_scene_name = self.state.scene_names[first_scene_index]
        last_scene_name = self.state.scene_names[last_scene_index]
        message = f"Scenes {first_scene_name} through {last_scene_name} set to '{scene_state}'"
        self.log(f"saving project after {message}")
        self.state.save()

        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
            format_markdown(message), \
            *self.scene_chooser_details(self.state.current_scene)

    def split_button702(self, scene_index, split_percent, use_alt_split, split_percent_alt):
        return self._split_scene(scene_index, split_percent, False, False, use_alt_split, split_percent_alt)

    def split_keep_before_702(self, scene_index, split_percent, use_alt_split, split_percent_alt):
        return self._split_scene(scene_index, split_percent, True, False, use_alt_split, split_percent_alt)

    def split_keep_after_702(self, scene_index, split_percent, use_alt_split, split_percent_alt):
        return self._split_scene(scene_index, split_percent, False, True, use_alt_split, split_percent_alt)

    def use_alt_split_change(self, use_alt_split, split_percent, split_percent_alt):
        if use_alt_split:
            return split_percent, split_percent
        else:
            return split_percent_alt, split_percent_alt

    def find_break_frame_type(self, frame_file) -> Literal["break", "skip", "find"]:
        find_break_stride = self.config.remixer_settings["find_break_stride"]
        find_break_threshold = self.config.remixer_settings["find_break_threshold"]
        skip_break_threshold = self.config.remixer_settings["skip_break_threshold"]
        l = get_average_lightness(frame_file, find_break_stride)

        break_type : str
        if l <= find_break_threshold:
            break_type = "break"
        elif l <= skip_break_threshold:
            break_type = "skip"
        else:
            break_type = "find"

        return break_type, l

    def compute_split_from_frame(self, frame_index, num_frames):
        return 100.0 * (frame_index * 1.0 / num_frames)

    def next_break_702(self, scene_index, split_percent):
        scene_index = int(scene_index)
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1
        if scene_index < 0 or scene_index > last_scene:
            return split_percent

        scene_name = self.state.scene_names[scene_index]
        _, num_frames, _, _, split_frame = self.state.compute_scene_split(scene_name, split_percent)

        last_frame = num_frames - 1
        last_starting_search_frame = last_frame - 1
        if split_frame > last_starting_search_frame:
            return split_percent
        starting_search_frame = split_frame + 1
        search_frame_index : int = starting_search_frame
        fallback_found_frame = split_frame
        fallback_value = 256

        frame_files = self.state.get_split_scene_cache(scene_index)

        frame_file = frame_files[search_frame_index]
        frame_type, value = self.find_break_frame_type(frame_file)
        if frame_type == "skip":
            # skip frames until either a break frame or a find frame
            for search_frame_index in range(search_frame_index + 1, last_frame + 1):
                frame_file = frame_files[search_frame_index]
                frame_type, value = self.find_break_frame_type(frame_file)
                if frame_type == "break" or frame_type == "find":
                    break

        if search_frame_index > last_starting_search_frame:
            return self.compute_split_from_frame(fallback_found_frame, num_frames)

        if frame_type != "break":
            for search_frame_index in range(search_frame_index + 1, last_frame + 1):
                frame_file = frame_files[search_frame_index]
                frame_type, value = self.find_break_frame_type(frame_file)
                if value < fallback_value:
                    fallback_found_frame = search_frame_index
                    fallback_value = value
                if frame_type == "break":
                    break

        if frame_type == "break": # and search_frame_index != starting_search_frame:
            return self.compute_split_from_frame(search_frame_index, num_frames)

        return self.compute_split_from_frame(fallback_found_frame, num_frames)

    def prev_break_702(self, scene_index, split_percent):
        scene_index = int(scene_index)
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1
        if scene_index < 0 or scene_index > last_scene:
            return split_percent

        scene_name = self.state.scene_names[scene_index]
        _, num_frames, _, _, split_frame = self.state.compute_scene_split(scene_name, split_percent)

        last_frame = 0
        last_starting_search_frame = last_frame + 1
        if split_frame - 1 < last_starting_search_frame:
            return split_percent
        starting_search_frame = split_frame - 2 # split frame is after the split, now going in rev.
        search_frame_index : int = starting_search_frame
        fallback_found_frame = split_frame
        fallback_value = 256

        frame_files = self.state.get_split_scene_cache(scene_index)

        frame_file = frame_files[starting_search_frame]
        frame_type, value = self.find_break_frame_type(frame_file)
        if frame_type == "skip":
            # skip frames until either a break frame or a find frame
            for search_frame_index in range(search_frame_index - 1, last_frame - 1, -1):
                frame_file = frame_files[search_frame_index]
                frame_type, value = self.find_break_frame_type(frame_file)
                if frame_type == "break" or frame_type == "find":
                    break

        if search_frame_index < last_starting_search_frame:
            return self.compute_split_from_frame(fallback_found_frame, num_frames)

        if frame_type != "break":
            for search_frame_index in range(search_frame_index - 1, last_frame - 1, -1):
                frame_file = frame_files[search_frame_index]
                frame_type, value = self.find_break_frame_type(frame_file)
                if value < fallback_value:
                    fallback_found_frame = search_frame_index
                    fallback_value = value
                if frame_type == "break":
                    break

        if frame_type == "break":
            return self.compute_split_from_frame(search_frame_index, num_frames)

        return self.compute_split_from_frame(fallback_found_frame, num_frames)

    def prev_keep_702(self, scene_index, split_percent):
        scene_index = int(scene_index)
        scene_index, _, _, _, _, _ = self.scan_for_keep(range(scene_index-1, -1, -1))
        return scene_index, *self.update_preview(scene_index, split_percent)

    def next_keep_702(self, scene_index, split_percent):
        scene_index = int(scene_index)
        scene_index, _, _, _, _, _ = self.scan_for_keep(range(scene_index+1, len(self.state.scene_names)))
        return scene_index, *self.update_preview(scene_index, split_percent)

    def back_button702(self):
        return gr.update(selected=self.TAB_CHOOSE_SCENES)

    def update_preview_scene_id(self, scene_index, split_percent):
        return self.update_preview(scene_index, split_percent)

    def update_preview_split_percent(self, scene_index, split_percent):
        return self.update_preview(scene_index, split_percent)

    def update_preview_split_percent_alt(self, scene_index, split_percent):
        display_frame, scene_info = self.update_preview(scene_index, split_percent)
        return display_frame, scene_info

    def goto_0_702(self):
        return 0

    def goto_50_702(self):
        return 50

    def goto_100_702(self):
        return 100

    def prev_minute_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, False, by_minute=True)

    def prev_second_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, False, by_second=True)

    def prev_frame_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, False)

    def next_frame_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, True, )

    def next_second_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, True, by_second=True)

    def next_minute_702(self, scene_index, split_percent):
        return self.state.compute_advance_702(scene_index, split_percent, True, by_minute=True)

    def go_to_s_button702(self, scene_index, split_percent, go_to_second):
        return self.state.compute_advance_702(scene_index, split_percent, False, by_exact_second=True,
                                        exact_second=go_to_second)

    def go_to_s_click702(self, scene_index, split_percent, go_to_second):
        return self.go_to_s_button702(scene_index, split_percent, go_to_second)

    def go_to_s_submit702(self, scene_index, split_percent, go_to_second):
        return self.go_to_s_button702(scene_index, split_percent, go_to_second)

    def go_to_f_button702(self, scene_index, split_percent, go_to_frame):
        return self.state.compute_advance_702(scene_index, split_percent, False, by_exact_frame=True,
                                        exact_frame=go_to_frame)

    def go_to_f_click702(self, scene_index, split_percent, go_to_frame):
        return self.go_to_f_button702(scene_index, split_percent, go_to_frame)

    def go_to_f_submit702(self, scene_index, split_percent, go_to_frame):
        return self.go_to_f_button702(scene_index, split_percent, go_to_frame)


    def set_view_hint_702(self, scene_index, split_percent, view_hint):
        return self.update_view_hint_preview(scene_index, split_percent, view_hint)

    def preview_view_hint_702(self, scene_index, split_percent, view_hint):
        return self.update_view_hint_preview(scene_index, split_percent, view_hint)

    def update_view_hint_preview(self, scene_index, split_percent, view_hint):
        if not isinstance(scene_index, (int, float)):
            return dummy_args(2)
        scene_index = int(scene_index)
        if scene_index < 0 or scene_index >= len(self.state.scene_names):
            return dummy_args(2)

        _, _, _, _, scene_info, _ = self.state.scene_chooser_details(scene_index, self.GAP)
        display_frame = self.state.compute_preview_frame(scene_index, split_percent)

        content_width = self.state.video_details["content_width"]
        content_height = self.state.video_details["content_height"]
        main_resize_w, main_resize_h, main_crop_w, main_crop_h, main_offset_x, main_offset_y = \
            self.processor.setup_resize_hint(content_width, content_height, False)

        block_hint = None
        block_hint_open = f"{self.state.EFFECTS_BLOCK_HINT}{self.state.HINT_MARKER}".upper()
        view_hint = view_hint.upper()
        block_type = self.processor.BLOCK_TYPE_PIXELATED

        if view_hint.startswith(block_hint_open):
            block_hint = view_hint[len(block_hint_open):]
        else:
            block_hint = f"{block_type}{view_hint}"

        if block_hint:
            self.log(f"update_view_hint_preview() using block hint {block_hint}")

            _, _, ext = split_filepath(display_frame, include_extension_dot=False)
            preview_filepath, _ = AutoIncrementFilename(self.config.directories["working"], ext)\
                .next_filename("view_hint_preview", ext)

            image = cv2.imread(display_frame)
            handled, image = self.processor.process_block_hint(block_hint, image, main_resize_w, main_resize_h, main_offset_x, main_offset_y, main_crop_w, main_crop_h)

            if handled:
                cv2.imwrite(preview_filepath, image)
                return preview_filepath, scene_info

        return display_frame, scene_info

    def update_preview(self, scene_index, split_percent):
        if not isinstance(scene_index, (int, float)):
            return dummy_args(2)
        scene_index = int(scene_index)
        if scene_index < 0 or scene_index >= len(self.state.scene_names):
            return dummy_args(2)

        display_frame = self.state.compute_preview_frame(scene_index, split_percent)
        _, _, _, _, scene_info, _ = self.state.scene_chooser_details(scene_index, self.GAP)
        return display_frame, scene_info

    def _split_scene(self, scene_index, split_percent, keep_before, keep_after, use_alt_split, split_percent_alt):
        empty_args = dummy_args(6)

        errors = self.state.ensure_project_dir_permissions()
        if errors:
            message = "\r\n".join(errors)
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(message, "error"), \
                use_alt_split, split_percent_alt, \
                *empty_args

        backup_split_scenes = self.config.remixer_settings["backup_split_scenes"]

        first_split = split_percent
        first_keep_before = keep_before
        first_keep_after = keep_after

        second_split = split_percent_alt
        second_keep_before = False
        second_keep_after = False

        if split_percent_alt == split_percent:
            use_alt_split = False

        if use_alt_split and split_percent_alt < split_percent:
            first_split = split_percent_alt
            second_split = split_percent

        if use_alt_split:
            # scale the secondary split, given the pecentage refers to the original whole range
            scene_name = self.state.scene_names[int(scene_index)]
            first_index, last_index, _ = details_from_group_name(scene_name)
            frame_count = (last_index - first_index) + 1
            remainder_frame_count = frame_count * ((100.0 - first_split) / 100.0)
            secondary_remainder_frame_count = frame_count * ((100.0 - second_split) / 100.0)
            secondary_frame_count = remainder_frame_count - secondary_remainder_frame_count
            second_split = (secondary_frame_count / remainder_frame_count) * 100.0

        if keep_before or keep_after:
            second_keep_before = first_keep_after
            second_keep_after = first_keep_before

        try:
            messages = []
            messages.append(self.state.split_scene(scene_index, first_split, first_keep_before,
                                                   first_keep_after, backup_split_scenes))

            if use_alt_split:
                messages.append(self.state.split_scene(scene_index + 1, second_split,
                                                       second_keep_before, second_keep_after, False))

            self.state.save()

            return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                format_markdown("\r\n".join(messages)), \
                False, 50.0, \
                *self.scene_chooser_details(self.state.current_scene)

        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(f"Unable to split scene: {error}", "warning"), \
                use_alt_split, split_percent_alt, \
                *empty_args

    def export_project_703(self,
                           new_project_path : str,
                           new_project_name : str,
                           cut_exported : bool):
        empty_args = dummy_args(3, gr.update(visible=False))
        if not new_project_path:
            return format_markdown("Please enter a Project Path for the new project", "warning"), \
                *empty_args
        if not is_safe_path(new_project_path):
            return format_markdown("The entered Project Path is not valid", "warning"), *empty_args
        if not new_project_name:
            return format_markdown("Please enter a Project Name for the new project", "warning"), \
                *empty_args

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return format_markdown("No kept scenes were found", "warning"), *empty_args

        # remember the current scene name so it can be returned to after the scene indexes change
        self.export_cut_scene_name = self.state.scene_names[self.state.current_scene]

        new_project_name = new_project_name.strip()
        full_new_project_path = os.path.join(new_project_path, new_project_name)
        try:
            self.state.project.export_project(new_project_path,
                                              new_project_name,
                                              kept_scenes,
                                              cut_exported)
            Session().set("last-video-remixer-export-dir", new_project_path)
            return format_markdown(f"Kept scenes saved as new project: {full_new_project_path} "), \
                gr.update(visible=True, value=full_new_project_path), \
                gr.update(visible=True), \
                gr.update(visible=cut_exported)

        except ValueError as error:
            return format_markdown(str(error), "error"), *empty_args

    def return_703(self):
        if self.export_cut_scene_name in self.state.scene_names:
            self.state.current_scene = self.state.scene_names.index(self.export_cut_scene_name)
        else:
            self.state.current_scene = 0
        self.state.save()
        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                    *self.scene_chooser_details(self.state.current_scene)

    def open_result703(self, new_project_path):
        return gr.update(selected=self.TAB_REMIX_HOME), \
            new_project_path, \
            format_markdown(self.TAB01_DEFAULT_MESSAGE)

    def import_project_7032(self, import_path : str, allow_overlap : bool):
        empty_args = dummy_args(6)

        if not os.path.exists(import_path):
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                    format_markdown(f"Directory '{import_path}' was not found", "error"), \
                    *empty_args
        try:
            self.state.project.import_project(import_path, allow_overlap)
        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                    format_markdown(str(error), "error"), \
                    *empty_args

        message = format_markdown("Project successfully imported")
        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                    message, \
                    *self.scene_chooser_details(self.state.current_scene)

    # TODO move
    def cleanse_button704(self):
        kept_scenes = self.state.kept_scenes()
        if len(kept_scenes) < 1:
            return format_markdown("No kept scenes were found", "warning")

        self.state.uncompile_scenes()

        # the native dimensions of the on-disk frame files are needed
        # older project.yaml files won't have this data
        try:
            self.state.ingest.enhance_video_info(ignore_errors=False)
        except ValueError as error:
            return format_markdown(f"Error: {error}", "error")

        working_path = os.path.join(self.state.project_path, self.CLEANSE_SCENES_PATH)
        if os.path.exists(working_path):
            self.log(f"purging previous working directory {working_path}")
            purge_path = self.state.purge_paths([working_path])
            if purge_path:
                self.state.project.copy_project_file(purge_path)
        self.log(f"creating working directory {working_path}")
        create_directory(working_path)

        upscale_path = os.path.join(working_path, "upscaled")
        downsample_path = os.path.join(working_path, "downsampled")
        self.log(f"creating upscale directory {working_path}")
        create_directory(upscale_path)
        self.log(f"creating downsample directory {working_path}")
        create_directory(downsample_path)

        content_width = self.state.video_details["source_width"]
        content_height = self.state.video_details["source_height"]
        scale_type = self.config.remixer_settings["scale_type_down"]

        upscaler = self.processor.get_upscaler(size= content_width * content_height)
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Cleansing") as bar:
            for scene_name in kept_scenes:
                scene_path = os.path.join(self.state.scenes_path, scene_name)
                upscale_scene_path = os.path.join(upscale_path, scene_name)
                create_directory(upscale_scene_path)
                self.processor.upscale_scene(upscaler, scene_path, upscale_scene_path,
                                         self.CLEANSE_SCENES_FACTOR, downscale_type=scale_type)

                downsample_scene_path = os.path.join(downsample_path, scene_name)
                create_directory(downsample_scene_path)
                self.processor.resize_scene(upscale_scene_path,
                                            downsample_scene_path,
                                            content_width,
                                            content_height,
                                            int(self.state.crop_w),
                                            int(self.state.crop_h),
                                            -1,
                                            -1,
                                            scale_type,
                                            crop_type="none")
                Mtqdm().update_bar(bar)

        self.log("purging scenes before replacing with cleansed scenes")
        scene_paths = []
        for scene_name in kept_scenes:
            scene_path = os.path.join(self.state.scenes_path, scene_name)
            scene_paths.append(scene_path)
        self.state.purge_paths(scene_paths)

        with Mtqdm().open_bar(total=len(kept_scenes), desc="Replacing") as bar:
            for scene_name in kept_scenes:
                downsample_scene_path = os.path.join(downsample_path, scene_name)
                shutil.move(downsample_scene_path, self.state.scenes_path)
                Mtqdm().update_bar(bar)

        try:
            shutil.rmtree(working_path)
        except OSError as error:
            self.log(f"Error removing path '{working_path}' ignored: {error}")

        self.state.invalidate_split_scene_cache()
        return format_markdown("Kept scenes replaced with cleaned versions")

    # TODO move
    def merge_scenes(self, first_scene_index, last_scene_index):
        """Merge the specified scenes. Returns the new scene name. Raises ValueError and RuntimeError."""
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if first_scene_index < 0 \
                or first_scene_index > last_scene \
                or last_scene_index < 0 \
                or last_scene_index > last_scene:
            raise ValueError(f"Scene indexes must be in the range 0 to {last_scene}: {first_scene_index}, {last_scene_index}")

        if first_scene_index >= last_scene_index:
            raise ValueError(f"Last scene index must be higher than first scene index: {first_scene_index}, {last_scene_index}")

        selected_count = (last_scene_index - first_scene_index) + 1
        if selected_count < 2:
            raise ValueError(f"There must be at least two scenes to merge: {first_scene_index}, {last_scene_index}")

        # make a list of the selected scene names
        selected_scene_names = []
        for index, scene_name in enumerate(self.state.scene_names):
            if index >= first_scene_index and index <= last_scene_index:
                selected_scene_names.append(scene_name)
        self.log(f"there are {len(selected_scene_names)} to merge")

        # check to see that the scene names are contiguous since they are the timing source for slicing audio
        first_index, _, _ = details_from_group_name(selected_scene_names[0])
        next_first_index = first_index
        for scene_name in selected_scene_names:
            first_index, last_index, _ = details_from_group_name(scene_name)
            if first_index != next_first_index:
                raise ValueError(f"Scenes to be merged must be contiguous. Scene name: {scene_name}, expected first index {next_first_index}")
            next_first_index = last_index + 1

        self.state.uncompile_scenes()

        # resequence the files within the selected scenes contiguously
        ResequenceFiles(self.state.scenes_path,
                        self.state.frame_format,
                        "merged_frame",
                        0, 1,
                        1, 0,
                        -1,
                        True,
                        self.log).resequence_groups(selected_scene_names)

        # consolidate all the files into the first scene
        first_scene_name = selected_scene_names[0]
        with Mtqdm().open_bar(total=len(selected_scene_names)-1, desc="Consolidating Frames") as bar:
            for scene_name in selected_scene_names[1:]:
                from_path = os.path.join(self.state.scenes_path, scene_name)
                to_path = os.path.join(self.state.scenes_path, first_scene_name)
                move_files(from_path, to_path)
                Mtqdm().update_bar(bar)

        # compute the new consolidated scene name
        last_scene_name = selected_scene_names[-1]
        first_index, _, _ = details_from_group_name(first_scene_name)
        _, last_index, num_width = details_from_group_name(last_scene_name)
        first_index = str(first_index).zfill(num_width)
        last_index = str(last_index).zfill(num_width)
        new_scene_name = f"{first_index}-{last_index}"
        self.log(f"new scene name {new_scene_name}")

        # rename the consolidated scene directory
        original_scene_path = os.path.join(self.state.scenes_path, first_scene_name)
        new_scene_path = os.path.join(self.state.scenes_path, new_scene_name)
        os.replace(original_scene_path, new_scene_path)

        # delete the obsolete empty scene directories
        for scene_name in selected_scene_names[1:]:
            path = os.path.join(self.state.scenes_path, scene_name)
            files = get_files(path)
            if len(files) != 0:
                raise RuntimeError(f"path '{path}' is expected to have zero files")
            self.log(f"removing path {path}")
            shutil.rmtree(path)

        # delete the affected thumbnails
        thumbnail_files = sorted(get_files(self.state.thumbnail_path))
        for index, thumbnail_file in enumerate(thumbnail_files):
            if index < first_scene_index:
                continue
            if index > last_scene_index:
                break
            os.remove(thumbnail_file)

        # set the new scene name
        self.state.scene_names[first_scene_index] = new_scene_name

        scene_state = self.state.scene_states[first_scene_name]
        del self.state.scene_states[first_scene_name]
        self.state.scene_states[new_scene_name] = scene_state

        # delete the obsolete scene names and states
        for scene_name in selected_scene_names[1:]:
            self.state.scene_names.remove(scene_name)
            del self.state.scene_states[scene_name]
        self.state.scene_names = sorted(self.state.scene_names)

        self.state.current_scene = first_scene_index

        # create a new thumbnail for the consolidated scene
        self.state.ingest.create_thumbnail(new_scene_name)
        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))

        self.state.save()

        return new_scene_name

    def merge_button705(self, first_scene_index, last_scene_index):
        empty_args = dummy_args(6)
        if not isinstance(first_scene_index, (int, float)) \
                or not isinstance(last_scene_index, (int, float)):
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown("Please enter Scene Indexes to get started", "warning"), \
                *empty_args
        first_scene_index = int(first_scene_index)
        last_scene_index = int(last_scene_index)

        try:
            new_scene_name = self.merge_scenes(first_scene_index, last_scene_index)
            message = f"Scenes merged into new scene {new_scene_name}"
            self.state.invalidate_split_scene_cache()

            return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                format_markdown(message), \
                *self.scene_chooser_details(self.state.current_scene)
        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(f"Error: {error}", "warning"), \
                *empty_args

    # TODO move
    def get_coalesce_merge_pairs(self):
        kept_scenes = self.state.kept_scenes()
        if len(kept_scenes) < 2:
            raise ValueError("There must be at least two kept scenes to merge")

        merge_pairs = []
        capture_mode = False
        first_merge_scene = None
        last_merge_scene = None

        for index, this_scene_name in enumerate(kept_scenes[:-1]):
            next_scene_name = kept_scenes[index + 1]
            _, this_last_frame_index, _ = details_from_group_name(this_scene_name)
            next_first_frame_index, _, _ = details_from_group_name(next_scene_name)
            mergeable = next_first_frame_index == this_last_frame_index + 1

            if not capture_mode:
                if mergeable:
                    # mergeable pair, record initial bounds and start capturing
                    first_merge_scene = this_scene_name
                    last_merge_scene = next_scene_name
                    capture_mode = True
            else:
                if mergeable:
                    # extend current bounds
                    last_merge_scene = next_scene_name
                else:
                    # not mergeable, end capture mode and save merge pair
                    merge_pairs.append([first_merge_scene, last_merge_scene])
                    capture_mode = False

        if capture_mode:
            merge_pairs.append([first_merge_scene, last_merge_scene])

        return merge_pairs

    def coalesce_merge_pairs_report(self, merge_pairs):
        messages = []
        if merge_pairs:
            for merge_pair in merge_pairs:
                first_index = self.state.scene_names.index(merge_pair[0])
                last_index = self.state.scene_names.index(merge_pair[1])
                message_line = []
                for index in range(first_index, last_index + 1):
                    scene_name = self.state.scene_names[index]
                    message_line.append(scene_name)
                first_scene_name = self.state.scene_names[first_index]
                last_scene_name = self.state.scene_names[last_index]
                first_frame_index, _, num_width = details_from_group_name(first_scene_name)
                _, last_frame_index, _ = details_from_group_name(last_scene_name)
                new_scene_name = f"{str(first_frame_index).zfill(num_width)}-{str(last_frame_index).zfill(num_width)}"
                messages.append(f"{','.join(message_line)} -> {new_scene_name}")
        else:
            messages.append("None")
        return messages

    def coalesce_merge_pairs(self, merge_pairs):
        with Mtqdm().open_bar(total=len(merge_pairs), desc="Coalescing Scenes") as bar:
            for merge_pair in merge_pairs:
                first_index = self.state.scene_names.index(merge_pair[0])
                last_index = self.state.scene_names.index(merge_pair[1])
                try:
                    self.merge_scenes(first_index, last_index)
                except ValueError as error:
                    self.log(f"Error in coalesce_merge_pairs: {error}")
                    Mtqdm().update_bar(bar)
                    raise
                Mtqdm().update_bar(bar)

    def force_coalesce_kept_scenes(self):
        messages = []
        try:
            merge_pairs = self.get_coalesce_merge_pairs()
            if merge_pairs:
                messages.append("Scenes have been consolidated:")
                messages += self.coalesce_merge_pairs_report(merge_pairs)
                self.coalesce_merge_pairs(merge_pairs)
        except ValueError as error:
            self.log(f"Error in force_coalesce_kept_scenes: {error}")
            raise
        return messages

    def coalesce_button706(self, coalesce_scenes):
        empty_args = dummy_args(6)

        messages = []
        if coalesce_scenes:
            messages.append("Scenes have been consolidated:")
        else:
            messages.append("Scenes to be consolidated:")

        merge_pairs = []
        try:
            merge_pairs = self.get_coalesce_merge_pairs()
        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown(str(error), "warning"), \
                *empty_args

        messages += self.coalesce_merge_pairs_report(merge_pairs)

        if coalesce_scenes:
            if not merge_pairs:
                return gr.update(selected=self.TAB_REMIX_EXTRA), \
                    format_markdown("No scenes were found to coalesce", "warning"), \
                    *empty_args

            return_to_scene_index = self.state.scene_names.index(merge_pairs[0][0])

            try:
                self.coalesce_merge_pairs(merge_pairs)
            except ValueError as error:
                return gr.update(selected=self.TAB_REMIX_EXTRA), \
                    format_markdown(f"Error: {error}", "error"), \
                    *empty_args

            self.state.current_scene = return_to_scene_index
            self.state.invalidate_split_scene_cache()

            return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                format_markdown("\r\n".join(messages)), \
                *self.scene_chooser_details(self.state.current_scene)
        else:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                format_markdown("\r\n".join(messages)), \
                *empty_args

    def export_button707(self, scene_index):
        empty_args = dummy_args(10)
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(scene_index, (int, float)):
            return format_markdown(f"Please enter a Scene Index to get started", "warning"), \
                gr.update(selected=self.APP_TAB_VIDEO_REMIXER), \
                gr.update(selected=VideoBlender.TAB_NEW_PROJECT), \
                *empty_args

        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            return format_markdown(f"Please enter a Scene Index from 0 to {last_scene}",
                                   "warning"), \
                gr.update(selected=self.APP_TAB_VIDEO_REMIXER), \
                gr.update(selected=VideoBlender.TAB_NEW_PROJECT), \
                *empty_args

        _, filename, _ = split_filepath(self.state.project_path)
        scene_name = self.state.scene_names[scene_index]
        vb_project_name = f"{filename} {scene_name}"
        vb_project_path_name = f"vb_project {scene_name}"
        vb_project_path = os.path.join(self.state.project_path, vb_project_path_name)

        if os.path.exists(vb_project_path):
            return format_markdown(f"Video Blender project already exists",
                                   "warning"), \
                gr.update(selected=self.APP_TAB_VIDEO_REMIXER), \
                gr.update(selected=VideoBlender.TAB_NEW_PROJECT), \
                *empty_args

        self.log(f"creating video blender project directory {vb_project_path}")
        create_directory(vb_project_path)

        scene_path = os.path.join(self.state.scenes_path, scene_name)
        original_frames_path = os.path.join(vb_project_path, "original_frames")
        self.log(f"duplicating files from {scene_path} to {original_frames_path}")
        duplicate_directory(scene_path, original_frames_path)

        return format_markdown(f"Ready to continue on Video Blender New Project tab"), \
            gr.update(selected=self.APP_TAB_VIDEO_BLENDER), \
            gr.update(selected=VideoBlender.TAB_NEW_PROJECT), \
            vb_project_name, \
            vb_project_path, \
            self.state.project_fps, \
            False, \
            original_frames_path, \
            True, \
            None, \
            False, \
            scene_path, \
            True

    def delete_button710(self, delete_purged):
        if self.state.project_path:
            if delete_purged:
                removed = self.state.delete_purged_content()
                return format_markdown(f"Removed: {removed}")
            else:
                return format_markdown(f"Removed: None")
        else:
            return format_markdown("There is no loaded project.", "error")

    def delete_button711(self, delete_source, delete_dropped, delete_thumbs):
        if self.state.project_path:
            removed = []
            if delete_source:
                removed.append(self.state.delete_path(self.state.frames_path))
            if delete_dropped:
                removed.append(self.state.delete_path(self.state.dropped_scenes_path))
            if delete_thumbs:
                removed.append(self.state.delete_path(self.state.thumbnail_path))
            removed = [_ for _ in removed if _]
            if removed:
                removed_str = "\r\n".join(removed)
                message = f"Removed:\r\n{removed_str}"
            else:
                message = f"Removed: None"
            return format_markdown(message)
        else:
            return format_markdown("There is no loaded project.", "error")

    def select_all_button711(self):
        return True, True, True

    def select_none_button711(self):
        return False, False, False

    def delete_button712(self,
                         delete_kept,
                         delete_resized,
                         delete_resynth,
                         delete_inflated,
                         delete_effects,
                         delete_upscaled,
                         delete_audio,
                         delete_video,
                         delete_clips):
        if self.state.project_path:
            removed = []
            if delete_kept:
                removed.append(self.state.delete_path(self.state.scenes_path))
            if delete_resized:
                removed.append(self.state.delete_path(self.state.resize_path))
            if delete_resynth:
                removed.append(self.state.delete_path(self.state.resynthesis_path))
            if delete_inflated:
                removed.append(self.state.delete_path(self.state.inflation_path))
            if delete_effects:
                removed.append(self.state.delete_path(self.state.effects_path))
            if delete_upscaled:
                removed.append(self.state.delete_path(self.state.upscale_path))
            if delete_audio:
                removed.append(self.state.delete_path(self.state.audio_clips_path))
            if delete_video:
                removed.append(self.state.delete_path(self.state.video_clips_path))
            if delete_clips:
                removed.append(self.state.delete_path(self.state.clips_path))
            removed = [_ for _ in removed if _]
            if removed:
                removed_str = "\r\n".join(removed)
                message = f"Removed:\r\n{removed_str}"
            else:
                message = f"Removed: None"
            return format_markdown(message)
        else:
            return format_markdown("There is no loaded project.", "error")

    def select_all_button712(self):
        return True, True, True, True, True, True, True, True

    def select_none_button712(self):
        return False, False, False, False, False, False, False, False

    def delete_all_project_content(self):
        message = None
        removed = []
        removed.append(self.state.delete_purged_content())
        removed.append(self.state.delete_path(self.state.frames_path))
        removed.append(self.state.delete_path(self.state.dropped_scenes_path))
        removed.append(self.state.delete_path(self.state.thumbnail_path))
        removed.append(self.state.delete_path(self.state.scenes_path))
        removed.append(self.state.delete_path(self.state.resize_path))
        removed.append(self.state.delete_path(self.state.resynthesis_path))
        removed.append(self.state.delete_path(self.state.inflation_path))
        removed.append(self.state.delete_path(self.state.effects_path))
        removed.append(self.state.delete_path(self.state.upscale_path))
        removed.append(self.state.delete_path(self.state.audio_clips_path))
        removed.append(self.state.delete_path(self.state.video_clips_path))
        removed.append(self.state.delete_path(self.state.clips_path))
        removed = [_ for _ in removed if _]
        if removed:
            removed_str = "\r\n".join(removed)
            message = f"Removed:\r\n{removed_str}"
        else:
            message = f"Removed: None"
        return message

    def delete_button713(self, delete_all):
        if self.state.project_path:
            message = None
            if delete_all:
                message = self.delete_all_project_content()
            return format_markdown(message)
        else:
            return format_markdown("There is no loaded project.", "error")

    def restore_button714(self):
        if self.state.project_path:
            message = self.state.project.recover_project()
            return gr.update(selected=self.TAB_CHOOSE_SCENES), \
                format_markdown(message), \
                *self.scene_chooser_details(self.state.current_scene)
        else:
            message = format_markdown("There is no loaded project.", "error")
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                message

    def purge_button715(self):
        if self.state.project_path:
            purge_root = self.state.purge_processed_content()

            # user will expect to return to the processing tab on reopening
            self.state.save_progress("process")
            self.state.processed_content_invalid = True

            if purge_root:
                message = format_markdown(
                    f"Processed content purged, and project file backed up, to {purge_root}")
                return gr.update(selected=self.TAB_PROC_REMIX), \
                    message
            else:
                message = format_markdown("No processed content was found to purge", "warning")
                return gr.update(selected=self.TAB_REMIX_EXTRA), \
                    message
        else:
            message = format_markdown("There is no loaded project.", "error")
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                message

    def save_mp4_video(self, output_filepath, quality=None, volume=None):
        self.state.output_filepath = output_filepath
        self.state.output_quality = quality or self.config.remixer_settings["default_crf"]
        self.state.output_volume = volume or 0.0

        self.state.save()

        kept_scenes = self.processor.prepare_save_remix(output_filepath)
        self.processor.save_remix(kept_scenes)

    def create_button716(self,
                         videos_path,
                         use_native_dimensions,
                         project_fps,
                         split_type,
                         scene_threshold,
                         break_duration,
                         break_ratio,
                         resize_w,
                         resize_h,
                         crop_w,
                         crop_h,
                         crop_offset_x,
                         crop_offset_y,
                         frame_format,
                         deinterlace,
                         split_time,
                         thumbnail_type,
                         min_frames_per_scene,
                         remove_source):
        messages = []
        if not videos_path:
            return format_markdown(
                "Enter a path to a directory of videos on this server to get started", "warning")

        if not os.path.exists(videos_path):
            return format_markdown(f"Directory '{videos_path}' was not found", "error")

        file_types = ",".join(self.config.remixer_settings["file_types"])
        file_list = sorted(get_files(videos_path, file_types))
        num_files = len(file_list)

        if num_files < 1:
            return format_markdown(
        f"Directory '{videos_path}' was not found to contain files of these types: {file_types}",
                "error")

        Session().set("last-bulk-create-path", videos_path)

        with Mtqdm().open_bar(total=num_files, desc="Create Projects") as bar:
            for file in file_list:
                try:
                    success, message = self._next_button00(file)
                    if not success:
                        messages.append(message)
                        continue

                    if use_native_dimensions:
                        self._next_button1(self.state.project_path,
                                           self.state.project_fps,
                                           split_type,
                                           scene_threshold,
                                           break_duration,
                                           break_ratio,
                                           self.state.resize_w,
                                           self.state.resize_h,
                                           self.state.resize_w,
                                           self.state.resize_h,
                                           -1,
                                           -1,
                                           frame_format,
                                           deinterlace,
                                           split_time)
                    else:
                        self._next_button1(self.state.project_path,
                                           project_fps,
                                           split_type,
                                           scene_threshold,
                                           break_duration,
                                           break_ratio,
                                           resize_w,
                                           resize_h,
                                           crop_w,
                                           crop_h,
                                           crop_offset_x,
                                           crop_offset_y,
                                           frame_format,
                                           deinterlace,
                                           split_time)

                    self._next_button2(thumbnail_type, min_frames_per_scene, False, remove_source)

                except ValueError as error:
                    messages.append(str(error))

                Mtqdm().update_bar(bar)

        if messages:
            return format_markdown("\r\n".join(messages), "warning")
        else:
            return format_markdown(f"{len(file_list)} files processed")

    def process_button7170(self,
                          projects_path,
                          project_state,
                          resynthesize,
                          inflate,
                          resize,
                          upscale,
                          upscale_option,
                          inflate_by_option,
                          inflate_slow_option,
                          resynth_option,
                          auto_save_remix,
                          auto_delete_remix,
                          auto_coalesce_remix,
                          keep_scene_videos,
                          quality,
                          volume):
        messages = []
        if not projects_path:
            return format_markdown(
            "Enter a path to a directory of Video Remixer projects on this server to get started",
            "warning")

        if not os.path.exists(projects_path):
            return format_markdown(f"Directory '{projects_path}' was not found", "error")

        dir_list = sorted(get_directories(projects_path))
        num_dirs = len(dir_list)

        if num_dirs < 1:
            return format_markdown(
                f"Directory '{projects_path}' was not found to contain Video Remixer projects",
                "error")

        all_projects = project_state.startswith("A")
        Session().set("last-bulk-process-path", projects_path)

        with Mtqdm().open_bar(total=num_dirs, desc="Process Projects") as bar:
            for dir in dir_list:
                try:
                    project_path = os.path.join(projects_path, dir)

                    try:
                        VideoRemixerProject.determine_project_filepath(project_path)
                    except ValueError:
                        self.log(f"skipping non project directory {project_path}")
                        Mtqdm().update_bar(bar)
                        continue

                    message = self._next_button01(project_path)
                    if message:
                        messages.append(message)

                    if not all_projects:
                        if not self.state.progress.startswith("process"):
                            Mtqdm().update_bar(bar)
                            continue

                    if len(self.state.kept_scenes()) < 1:
                        self.state.keep_all_scenes()

                    message = self._next_button5(resynthesize,
                                                 inflate,
                                                 resize,
                                                 upscale,
                                                 upscale_option,
                                                 inflate_by_option,
                                                 inflate_slow_option,
                                                 resynth_option,
                                                 auto_save_remix,
                                                 auto_delete_remix,
                                                 auto_coalesce_remix,
                                                 keep_scene_videos,
                                                 quality,
                                                 volume)
                    if message:
                        messages.append(message)

                except ValueError as error:
                    messages.append(str(error))

                Mtqdm().update_bar(bar)

        if messages:
            return format_markdown("\r\n".join(messages))
        else:
            return format_markdown(f"{len(dir_list)} projects processed")

    def process_button7171(self,
                            projects_path : str,
                            project_state : str,
                            process_thumbnails : bool,
                            process_delete : bool,
                            process_recover : bool,
                            thumbnail_type : str):
        messages = []
        if not projects_path:
            return format_markdown(
            "Enter a path to a directory of Video Remixer projects on this server to get started",
            "warning")

        if not os.path.exists(projects_path):
            return format_markdown(f"Directory '{projects_path}' was not found", "error")

        dir_list = sorted(get_directories(projects_path))
        num_dirs = len(dir_list)

        if num_dirs < 1:
            return format_markdown(
                f"Directory '{projects_path}' was not found to contain Video Remixer projects",
                "error")

        selected_state = project_state.lower()
        all_projects = selected_state.startswith("a")
        Session().set("last-bulk-action-path", projects_path)

        with Mtqdm().open_bar(total=num_dirs, desc="Process Projects") as bar:
            for dir in dir_list:
                try:
                    project_path = os.path.join(projects_path, dir)

                    try:
                        VideoRemixerProject.determine_project_filepath(project_path)
                    except ValueError:
                        self.log(f"skipping non project directory {project_path}")
                        Mtqdm().update_bar(bar)
                        continue

                    messages.append(self._next_button01(project_path))

                    if not all_projects:
                        project_state = self.state.progress[:-1] \
                            if self.state.progress[-1] == self.state.STICKY_PROGRESS \
                            else self.state.progress
                        if not project_state == selected_state:
                            Mtqdm().update_bar(bar)
                            continue

                    if process_thumbnails:
                        try:
                            self._next_button2(thumbnail_type, 0, True, False)
                            messages.append(f"Thumbnails recreated for {project_path}")
                        except ValueError as error:
                            messages.append(str(error))

                    if process_delete:
                        try:
                            messages.append(self.delete_all_project_content())
                        except ValueError as error:
                            messages.append(str(error))

                    if process_recover:
                        try:
                            messages.append(self.state.project.recover_project())
                        except ValueError as error:
                            messages.append(str(error))

                except ValueError as error:
                    messages.append(str(error))

                Mtqdm().update_bar(bar)

        if messages:
            return format_markdown("\r\n".join(messages))
        else:
            return format_markdown(f"{len(dir_list)} projects processed")

    def open_button718(self, projects_path, project_state, search_order718 : str):
        empty_args = dummy_args(2)
        if not projects_path:
            return format_markdown(
            "Enter a path to a directory of Video Remixer projects on this server to get started",
                "warning"), \
            gr.update(selected=self.TAB_REMIX_EXTRA), \
            *empty_args

        if not os.path.exists(projects_path):
            return format_markdown(f"Directory '{projects_path}' was not found", "error"), \
            gr.update(selected=self.TAB_REMIX_EXTRA), \
            *empty_args

        last_first = search_order718.startswith("L")
        dir_list = sorted(get_directories(projects_path), reverse=last_first)
        num_dirs = len(dir_list)

        if num_dirs < 1:
            return format_markdown(
                f"Directory '{projects_path}' was not found to contain Video Remixer projects",
                "error"), \
            gr.update(selected=self.TAB_REMIX_EXTRA), \
            *empty_args

        Session().set("last-bulk-open-path", projects_path)

        messages = []
        index = 0
        with Mtqdm().open_bar(total=num_dirs, desc="Search Projects") as bar:
            for dir in dir_list:
                index += 1
                try:
                    project_path = os.path.join(projects_path, dir)

                    try:
                        VideoRemixerProject.determine_project_filepath(project_path)
                    except ValueError:
                        self.log(f"skipping non project directory {project_path}")
                        Mtqdm().update_bar(bar)
                        messages.append(f"Directory {index}/{num_dirs} {project_path} is not a project")
                        continue

                    _messages = self._next_button01(project_path)
                    self.log(_messages)
                    Mtqdm().update_bar(bar)
                    messages.append(f"Project {index}/{num_dirs} {project_path} state: {self.state.progress}")

                    if self.state.progress.startswith(project_state.lower()):
                        # messages.append(f"Project {index} {project_path} state: {self.state.progress}")
                        return format_markdown("\r\n".join(messages)), \
                            gr.update(selected=self.TAB_REMIX_HOME), \
                            project_path, \
                            format_markdown(self.TAB01_DEFAULT_MESSAGE)
                    # else:
                    #     messages.append(f"Found project {index} {project_path}")


                except ValueError as error:
                    return format_markdown(f"An error occurred while searching projects: {error}",
                                           "error"), \
                    gr.update(selected=self.TAB_REMIX_EXTRA), \
                    *empty_args

        messages.append(f"A project was not found with the state {project_state}")
        return format_markdown("\r\n".join(messages)), \
            gr.update(selected=self.TAB_REMIX_EXTRA), \
            *empty_args
