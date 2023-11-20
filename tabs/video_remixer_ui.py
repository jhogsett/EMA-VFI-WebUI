"""Video Remixer feature UI and event handlers"""
import os
import shutil
import math
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import format_markdown, style_report
from webui_utils.file_utils import get_files, create_directory, get_directories, split_filepath, \
    is_safe_path, duplicate_directory
from webui_utils.video_utils import details_from_group_name
from webui_utils.jot import Jot
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from video_remixer import VideoRemixerState
from webui_utils.mtqdm import Mtqdm
from webui_utils.session import Session
from ffmpy import FFRuntimeError

class VideoRemixer(TabBase):
    """Encapsulates UI elements and events for the Video Remixer Feature"""
    def __init__(self,
                 config : SimpleConfig,
                 engine : InterpolateEngine,
                 log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.new_project()

    # TODO this only runs at app start-up
    def new_project(self):
        self.state = VideoRemixerState()
        self.state.set_project_ui_defaults(self.config.remixer_settings["def_project_fps"])
        self.invalidate_split_scene_cache()

    TAB_REMIX_HOME = 0
    TAB_REMIX_SETTINGS = 1
    TAB_SET_UP_PROJECT = 2
    TAB_CHOOSE_SCENES = 3
    TAB_COMPILE_SCENES = 4
    TAB_PROC_OPTIONS = 5
    TAB_SAVE_REMIX = 6
    TAB_REMIX_EXTRA = 7

    TAB_EXTRA_DROP_PROCESSED = 0
    TAB_EXTRA_CHOOSE_RANGE = 1
    TAB_EXTRA_SPLIT_SCENE = 2
    TAB_EXTRA_EXPORT_SCENES = 3
    TAB_EXTRA_CLEANSE_SCENES = 4
    TAB_EXTRA_MANAGE_STORAGE = 5

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
        default_label_at_top = self.config.remixer_settings["marked_at_top"]

        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Video Remixer"):
            gr.Markdown(
                SimpleIcons.MOVIE + "Restore & Remix Videos with Audio")
            with gr.Tabs() as tabs_video_remixer:

                ### NEW PROJECT
                with gr.Tab(SimpleIcons.ONE + " Remix Home", id=self.TAB_REMIX_HOME):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**Input a video to get started remixing**")
                            with gr.Row():
                                video_path = gr.Textbox(label="Video Path",
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
                                project_load_path = gr.Textbox(label="Project Path",
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
                                project_path = gr.Textbox(label="Set Project Path",
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
                                resize_w = gr.Number(label="Resize Width")
                                resize_h = gr.Number(label="Resize Height")
                            with gr.Row():
                                crop_w = gr.Number(label="Crop Width")
                                crop_h = gr.Number(label="Crop Height")
                            with gr.Accordion(label="More Settings", open=False):
                                with gr.Row():
                                    crop_offset_x = gr.Number(label="Crop X Ofset", value=-1, info="Set to -1 for auto-centering")
                                    crop_offset_y = gr.Number(label="Crop Y Offset", value=-1, info="Set to -1 for auto-centering")

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
                        scene_label = gr.Text(label="Scene Name", interactive=False, scale=1)
                        scene_info = gr.Text(label="Scene Details", interactive=False, scale=1)
                        with gr.Column(scale=2):
                            with gr.Row():
                                scene_state = gr.Radio(label="Choose", value=None,
                                                    choices=["Keep", "Drop"])
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
                                        variant="secondary")
                                    choose_range_button = gr.Button(
                                        value="Choose Scene Range " + SimpleIcons.HEART_HANDS,
                                        variant="secondary")
                            with gr.Accordion(label="Danger Zone", open=False):
                                with gr.Row():
                                    keep_all_button = gr.Button(value="Keep All Scenes",
                                                                variant="stop")
                                    drop_all_button = gr.Button(value="Drop All Scenes",
                                                                variant="stop")
                                with gr.Row():
                                    invert_choices_button = gr.Button(value="Invert Scene Choices",
                                                                variant="stop")
                                    drop_processed_button = gr.Button(value="Drop Processed Scene",
                                                                variant="stop")
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
                with gr.Tab(SimpleIcons.SIX + " Process Remix", id=self.TAB_PROC_OPTIONS):
                    gr.Markdown("**Ready to Process Content for Remix Video**")

                    with gr.Row():
                        resize = gr.Checkbox(label="Resize / Crop Frames", value=True)
                        with gr.Column(variant="compact"):
                            gr.Markdown(format_markdown(
                                "Resize and Crop Frames according to project settings\r\n"+
                                "- Adjust aspect ratio\r\n" +
                                "- Remove unwanted letterboxes or pillarboxes",
                                color="more", bold_heading_only=True))

                    with gr.Row():
                        resynthesize = gr.Checkbox(label="Resynthesize Frames",value=True)
                        with gr.Column(variant="compact"):
                            gr.Markdown(format_markdown(
                                "Recreate Frames using Interpolation of adjacent frames\r\n" +
                                "- Remove grime and single-frame noise\r\n" +
                                "- Reduce sprocket shake in film-to-digital content",
                                color="more", bold_heading_only=True))

                    with gr.Row():
                        inflate = gr.Checkbox(label="Inflate New Frames",value=True)
                        with gr.Column(variant="compact"):
                            gr.Markdown(format_markdown(
                            "Insert Between-Frames using Interpolation of existing frames\r\n" +
                            "- Double the frame rate for smooth motion\r\n" +
                            "- Increase content realness and presence",
                            color="more", bold_heading_only=True))

                    with gr.Row():
                        upscale = gr.Checkbox(label="Upscale Frames", value=True, scale=1)
                        upscale_option = gr.Radio(label="Upscale By", value="2X", scale=1,
                                                  choices=["1X", "2X", "4X"])
                        with gr.Column(variant="compact", scale=2):
                            gr.Markdown(format_markdown(
                                "Clean and Enlarge frames using Real-ESRGAN 4x+ upscaler\r\n" +
                                "- Remove grime, noise, and digital artifacts\r\n" +
                                "- Enlarge frames according to upscaling settings",
                                color="more", bold_heading_only=True))

                    with gr.Row():
                        process_all = gr.Checkbox(label="Select All", value=True)
                        with gr.Column(variant="compact"):
                            gr.Markdown(format_markdown(
                                "Deselect All Steps to use original source content for remix video",
                                color="more", bold=True))

                    message_box5 = gr.Markdown(value=format_markdown(self.TAB5_DEFAULT_MESSAGE))
                    gr.Markdown(
                        format_markdown(
                            "Progress can be tracked in the console", color="none", italic=True,
                            bold=False))

                    with gr.Row():
                        back_button5 = gr.Button(value="< Back", variant="secondary", scale=0)
                        next_button5 = gr.Button(value="Process Remix " +
                                    SimpleIcons.SLOW_SYMBOL, variant="primary",
                                    elem_id="actionbutton")
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
                            custom_video_options = gr.Textbox(
                                label="Custom FFmpeg Video Output Options",
                        info="Passed to FFmpeg as output video settings when converting PNG frames")
                            custom_audio_options = gr.Textbox(
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

                        ### CREATE MARKED REMIX
                        with gr.Tab(label="Create Marked Remix"):
                            marked_video_options = gr.Textbox(value=marked_ffmpeg_video,
                                label="Marked FFmpeg Video Output Options",
                        info="Passed to FFmpeg as output video settings when converting PNG frames")
                            marked_audio_options = gr.Textbox(value=marked_ffmpeg_audio,
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
                                label_text = gr.Textbox(label="Label Text", max_lines=1, placeholder="Leave blank to use same label as Marked Remix tab")
                                label_at_top = gr.Checkbox(value=default_label_at_top, label="Label at Top", info="Whether to place the label at the top or at the bottom")
                            with gr.Row():
                                label_font_file = gr.Textbox(value=default_label_font_file, label="Font File", max_lines=1, info="Font file within the application directory")
                                label_font_size = gr.Number(value=default_label_font_size, label="Font Factor", info="Size as a factor of frame width, smaller values produce larger text")
                                label_font_color = gr.Textbox(value=default_label_font_color, label="Font Color", max_lines=1, info="Font color and opacity in FFmpeg 'drawtext' filter format")
                            with gr.Row():
                                label_draw_box = gr.Checkbox(value=default_label_draw_box, label="Background", info="Draw a background underneath the label text")
                                label_border_size = gr.Number(value=default_label_border_size, label="Border Factor", info="Size as a factor of computed font size, smaller values produce a large margin")
                                label_box_color = gr.Textbox(value=default_label_box_color, label="Background Color", max_lines=1, info="Background color and opacity in FFmpeg 'drawtext' filter format")
                            with gr.Row():
                                quality_slider_labeled = gr.Slider(minimum=minimum_crf,
                                    maximum=maximum_crf, step=1, value=default_crf,
                                    label="Video Quality",
                                    info="Lower values mean higher video quality")
                                output_filepath_labeled = gr.Textbox(label="Output Filepath",
                                    max_lines=1,
                                    info="Enter a path and filename for the remixed video")
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

                        # Split Scene
                        with gr.Tab(SimpleIcons.AXE + " Split Scene",
                                    id=self.TAB_EXTRA_SPLIT_SCENE):
                            gr.Markdown("**_Split a Scene in two at a set point_**")
                            with gr.Row():
                                with gr.Column():
                                    with gr.Row():
                                        scene_id_702 = gr.Number(value=-1,
                                                                    label="Scene Index")
                                        scene_info_702 = gr.Text(label="Scene Details",
                                                                    interactive=False)
                                    with gr.Row():
                                        split_percent_702 = gr.Slider(value=50.0,
                                            label="Split Position", minimum=0.0,
                                            maximum=100.0, step=0.1,
                                        info="A lower value splits earlier in the scene")
                                    with gr.Row():
                                        prev_second_702 = gr.Button(value="< 1 second", scale=0)
                                        prev_frame_702 = gr.Button(value="< 1 frame", scale=0)
                                        next_frame_702 = gr.Button(value="1 frame >", scale=0)
                                        next_second_702 = gr.Button(value="1 second >", scale=0)
                                with gr.Column():
                                    preview_image702 = gr.Image(type="filepath",
                            label="Split Frame Preview", tool=None, height=max_thumb_size)
                            with gr.Row():
                                message_box702 = gr.Markdown(format_markdown(
            "Click Split Scene to: Split the scenes into Two Scenes at a set percentage"))
                            split_button702 = gr.Button(
                                "Split Scene " + SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)

                        # Choose Scene Range
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
                                                            choices=["Keep", "Drop"])
                            with gr.Row():
                                message_box701 = gr.Markdown(
                                    format_markdown(
                        "Click Choose Scene Range to: Set the Scene Range to the specified state"))
                            choose_button701 = gr.Button("Choose Scene Range",
                                                    variant="stop", scale=0)

                        # Cleanse Scenes
                        with gr.Tab(SimpleIcons.SOAP + " Cleanse Scenes",
                                    id=self.TAB_EXTRA_CLEANSE_SCENES):
                            gr.Markdown("**_Remove noise and artifacts from kept scenes_**")
                            with gr.Row():
                                message_box704 = gr.Markdown(
                                    format_markdown(
                            "Click Cleanse Scene to: Remove noise and artifacts from kept scenes"))
                            cleanse_button704 = gr.Button(
                            "Cleanse Scenes " + SimpleIcons.SLOW_SYMBOL, variant="stop", scale=0)

                        # Drop Processed Scene
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

                        # Export Kept Scenes
                        with gr.Tab(SimpleIcons.HEART_EXCLAMATION + " Export Kept Scenes", id=self.TAB_EXTRA_EXPORT_SCENES):
                            gr.Markdown("**_Save Kept Scenes as a New Project_**")
                            with gr.Row():
                                export_path_703 = gr.Textbox(label="Exported Project Root Directory", max_lines=1,
                                        info="Enter a path on this server for the root directory of the new project")
                                project_name_703 = gr.Textbox(label="Exported Project Name", max_lines=1,
                                        info="Enter a name for the new project")
                            with gr.Row():
                                message_box703 = gr.Markdown(format_markdown("Click Export Project to: Save the kept scenes as a new project"))
                            export_project_703 = gr.Button("Export Project " + SimpleIcons.SLOW_SYMBOL,
                                                    variant="stop", scale=0)
                            with gr.Row():
                                result_box703 = gr.Textbox(label="New Project Path", max_lines=1, visible=False)
                                open_result703 = gr.Button("Open New Project", visible=False, scale=0)

                        with gr.Tab(SimpleIcons.HERB +" Manage Storage",
                                    id=self.TAB_EXTRA_MANAGE_STORAGE):
                            gr.Markdown("Free Disk Space by Removing Unneeded Content")
                            with gr.Tabs():
                                with gr.Tab(SimpleIcons.WASTE_BASKET +
                                            " Remove Soft-Deleted Content"):
                                    gr.Markdown(
                    "**_Delete content set aside when remix processing selections are changed_**")
                                    with gr.Row():
                                        delete_purged_710 = gr.Checkbox(
                                            label="Permanently Delete Purged Content")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
                                "Delete the contents of the 'purged_content' project directory.")
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
                                            SimpleIcons.SLOW_SYMBOL, variant="stop")
                                        select_all_button710 = gr.Button(
                                            value="Select All", scale=0)
                                        select_none_button710 = gr.Button(
                                            value="Select None", scale=0)

                                with gr.Tab(SimpleIcons.CROSSMARK +
                                            " Remove Scene Chooser Content"):
                                    gr.Markdown(
                            "**_Delete source PNG frame files, thumbnails and dropped scenes_**")
                                    with gr.Row():
                                        delete_source_711 = gr.Checkbox(
                                            label="Remove Source Video Frames")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
                        "Delete source video PNG frame files used to split content into scenes.")
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
                                                SimpleIcons.SLOW_SYMBOL, variant="stop")
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
                                        delete_resized_712 = gr.Checkbox(
                                            label="Remove Resized Frames")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
    "Delete Resized PNG frame files used as inputs for processing and creating remix video clips.")
                                    with gr.Row():
                                        delete_resynth_712 = gr.Checkbox(
                                            label="Remove Resynthesized Frames")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
                                        "Delete Resynthesized PNG frame files used as inputs " +\
                                        "for processing and creating remix video clips.")
                                    with gr.Row():
                                        delete_inflated_712 = gr.Checkbox(
                                            label="Remove Inflated Frames")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
    "Delete Inflated PNG frame files used as inputs for processing and creating remix video clips.")
                                    with gr.Row():
                                        delete_upscaled_712 = gr.Checkbox(
                                            label="Remove Upscaled Frames")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
    "Delete Upscaled PNG frame files used as inputs for processing and creating remix video clips.")
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
                                                SimpleIcons.SLOW_SYMBOL, variant="stop")
                                        select_all_button712 = gr.Button(
                                            value="Select All", scale=0)
                                        select_none_button712 = gr.Button(
                                            value="Select None", scale=0)

                                with gr.Tab(SimpleIcons.COLLISION + " Remove All Processed Content"):
                                    gr.Markdown(
                                    "**_Delete all processed project content (except videos)_**")
                                    with gr.Row():
                                        delete_all_713 = gr.Checkbox(
                                            label="Permanently Delete Processed Content")
                                        with gr.Column(variant="compact"):
                                            gr.Markdown(
            "Deletes all created project content. **Does not delete original and remixed videos.**")
                                    with gr.Row():
                                        message_box713 = gr.Markdown(
                                            format_markdown(
                    "Click Delete Processed Content to: Permanently Remove all processed content"))
                                    gr.Markdown(
                                        format_markdown(
                    "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                    with gr.Row():
                                        delete_button713 = gr.Button(
                                            value="Delete Processed Content " +\
                                                SimpleIcons.SLOW_SYMBOL, variant="stop")

                                with gr.Tab(SimpleIcons.MENDING_HEART + " Recover Project"):
                                    gr.Markdown(
                        "**_Restore a project from the original source video and project file_**")
                                    with gr.Row():
                                        message_box714 = gr.Markdown(
                                            format_markdown(
                                    "Click Recover Project to: Restore the currently loaded project"))
                                    gr.Markdown(
                                        format_markdown(
                    "Progress can be tracked in the console", color="none", italic=True, bold=False))
                                    with gr.Row():
                                        restore_button714 = gr.Button(
                                            value="Recover Project " +
                                            SimpleIcons.SLOW_SYMBOL, variant="stop")

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
                                crop_offset_x, crop_offset_y, project_info2, thumbnail_type,
                                min_frames_per_scene, scene_index, scene_label, scene_image,
                                scene_state, scene_info, project_info4, resize, resynthesize,
                                inflate, upscale, upscale_option, summary_info6, output_filepath])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                crop_offset_x, crop_offset_y, deinterlace, split_time],
                           outputs=[tabs_video_remixer, message_box1, project_info2, message_box2,
                                project_load_path])

        back_button1.click(self.back_button1, outputs=tabs_video_remixer)

        next_button2.click(self.next_button2,
                           inputs=[thumbnail_type, min_frames_per_scene, skip_detection],
                           outputs=[tabs_video_remixer, message_box2, scene_index, scene_label,
                                    scene_image, scene_state, scene_info])

        back_button2.click(self.back_button2, outputs=tabs_video_remixer)

        thumbnail_type.change(self.thumb_change, inputs=thumbnail_type, show_progress=False)

        scene_state.change(self.scene_state_button, show_progress=False,
                            inputs=[scene_index, scene_label, scene_state],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        scene_index.submit(self.go_to_frame, inputs=scene_index,
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        keep_next.click(self.keep_next, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        drop_next.click(self.drop_next, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        next_scene.click(self.next_scene, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        prev_scene.click(self.prev_scene, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        next_keep.click(self.next_keep, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        prev_keep.click(self.prev_keep, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        first_scene.click(self.first_scene, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        last_scene.click(self.last_scene, show_progress=False,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        split_scene_button.click(self.split_scene_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, scene_id_702,
                     split_percent_702, preview_image702])

        choose_range_button.click(self.choose_range_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, first_scene_id_701, last_scene_id_701])

        keep_all_button.click(self.keep_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        drop_all_button.click(self.drop_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        invert_choices_button.click(self.invert_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        drop_processed_button.click(self.drop_processed_shortcut, inputs=scene_index,
            outputs=[tabs_video_remixer, tabs_remix_extra, scene_id_700])

        next_button3.click(self.next_button3,
                           outputs=[tabs_video_remixer, project_info4])

        back_button3.click(self.back_button3, outputs=tabs_video_remixer)

        next_button4.click(self.next_button4,
                           outputs=[tabs_video_remixer, message_box4, message_box5])

        back_button4.click(self.back_button4, outputs=tabs_video_remixer)

        next_button5.click(self.next_button5,
                    inputs=[resynthesize, inflate, resize, upscale, upscale_option],
                    outputs=[tabs_video_remixer, message_box5, summary_info6, output_filepath,
                             output_filepath_custom, output_filepath_marked, output_filepath_labeled,
                             message_box60, message_box61, message_box62, message_box63])

        back_button5.click(self.back_button5, outputs=tabs_video_remixer)

        process_all.change(self.process_all_changed, inputs=process_all,
                           outputs=[resynthesize, inflate, resize, upscale],
                           show_progress=False)

        next_button60.click(self.next_button60, inputs=[output_filepath, quality_slider],
                           outputs=message_box60)

        back_button60.click(self.back_button6, outputs=tabs_video_remixer)

        next_button61.click(self.next_button61,
                        inputs=[custom_video_options, custom_audio_options, output_filepath_custom],
                        outputs=message_box61)

        back_button61.click(self.back_button6, outputs=tabs_video_remixer)

        next_button62.click(self.next_button62,
                        inputs=[marked_video_options, marked_audio_options, output_filepath_marked],
                        outputs=message_box62)

        back_button62.click(self.back_button6, outputs=tabs_video_remixer)

        next_button63.click(self.next_button63,
                        inputs=[label_text, label_font_size, label_font_color, label_font_file,
                                label_draw_box, label_box_color, label_border_size, label_at_top,
                                output_filepath_labeled, quality_slider_labeled],
                        outputs=message_box63)

        back_button63.click(self.back_button6, outputs=tabs_video_remixer)

        drop_button700.click(self.drop_button700, inputs=scene_id_700, outputs=message_box700)

        choose_button701.click(self.choose_button701,
                               inputs=[first_scene_id_701, last_scene_id_701, scene_state_701],
                               outputs=[tabs_video_remixer, message_box701, scene_index,
                                        scene_label, scene_image, scene_state, scene_info])

        scene_id_702.change(self.preview_button702, inputs=[scene_id_702, split_percent_702],
                                outputs=[preview_image702, scene_info_702], show_progress=False)

        split_percent_702.change(self.preview_button702, inputs=[scene_id_702, split_percent_702],
                                outputs=[preview_image702, scene_info_702], show_progress=False)

        split_percent_702.change(self.preview_button702, inputs=[scene_id_702, split_percent_702],
                                outputs=[preview_image702, scene_info_702], show_progress=False)

        prev_second_702.click(self.prev_second_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        prev_frame_702.click(self.prev_frame_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        next_frame_702.click(self.next_frame_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        next_second_702.click(self.next_second_702, inputs=[scene_id_702, split_percent_702],
                                outputs=split_percent_702, show_progress=False)

        split_button702.click(self.split_button702, inputs=[scene_id_702, split_percent_702],
                              outputs=[tabs_video_remixer, message_box702, scene_index, scene_label,
                                       scene_image, scene_state, scene_info])

        export_project_703.click(self.export_project_703,
                                 inputs=[export_path_703, project_name_703],
                                 outputs=[message_box703, result_box703, open_result703])

        open_result703.click(self.open_result703, inputs=result_box703,
                                outputs=[tabs_video_remixer, project_load_path, message_box01])

        cleanse_button704.click(self.cleanse_button704, outputs=message_box704)

        delete_button710.click(self.delete_button710,
                               inputs=delete_purged_710,
                               outputs=message_box710)
        select_all_button710.click(self.select_all_button710, show_progress=False,
                                outputs=[delete_purged_710])
        select_none_button710.click(self.select_none_button710, show_progress=False,
                                outputs=[delete_purged_710])

        delete_button711.click(self.delete_button711,
                               inputs=[delete_source_711, delete_dropped_711, delete_thumbs_711],
                               outputs=message_box711)
        select_all_button711.click(self.select_all_button711, show_progress=False,
                                outputs=[delete_source_711, delete_dropped_711, delete_thumbs_711])
        select_none_button711.click(self.select_none_button711, show_progress=False,
                                outputs=[delete_source_711, delete_dropped_711, delete_thumbs_711])

        delete_button712.click(self.delete_button712,
                               inputs=[delete_kept_712, delete_resized_712, delete_resynth_712,
                                       delete_inflated_712, delete_upscaled_712, delete_audio_712,
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
                                    scene_index, scene_label, scene_image, scene_state, scene_info])

    ### UTILITY FUNCTIONS

    def empty_args(self, num):
        return [None for _ in range(num)]

    def noop_args(self, num):
        return [gr.update(visible=True) for _ in range(num)]

    ### REMIX HOME EVENT HANDLERS

    # User has clicked New Project > from Remix Home
    def next_button00(self, video_path):
        empty_args = self.empty_args(7)
        if not video_path:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown("Enter a path to a video on this server to get started", "warning")), \
                   *empty_args

        if not os.path.exists(video_path):
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown(f"File '{video_path}' was not found", "error")), \
                   *empty_args

        self.new_project()
        try:
            self.state.ingest_video(video_path)
            self.state.video_info1 = self.state.ingested_video_report()
        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown(str(error), "error")), \
                   *empty_args

        # don't save yet, user may change project path next
        self.state.save_progress("settings", save_project=False)

        return gr.update(selected=self.TAB_REMIX_SETTINGS), \
            gr.update(value=format_markdown(self.TAB00_DEFAULT_MESSAGE)), \
            gr.update(value=self.state.video_info1), \
            self.state.project_path, \
            self.state.resize_w, \
            self.state.resize_h, \
            self.state.crop_w, \
            self.state.crop_h, \
            self.state.crop_offset_x, \
            self.state.crop_offset_y, \
            self.state.project_fps

    # User has clicked Open Project > from Remix Home
    def next_button01(self, project_path):
        empty_args = self.empty_args(31)
        if not project_path:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown("Enter a path to a Video Remixer project directory on this server to get started", "warning")), \
                   *empty_args

        if not os.path.exists(project_path):
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown(f"Directory '{project_path}' was not found", "error")), \
                   *empty_args

        try:
            project_file = VideoRemixerState.determine_project_filepath(project_path)
        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown(str(error), "error")), \
                   *empty_args

        try:
            self.state = VideoRemixerState.load(project_file, self.log)
        except ValueError as error:
            self.log(f"error opening project: {error}")
            return gr.update(selected=self.TAB_REMIX_HOME), \
                   gr.update(value=format_markdown(str(error), "error")), \
                   *empty_args

        if self.state.project_ported(project_file):
            try:
                self.state = VideoRemixerState.load_ported(self.state.project_path, project_file, self.log)
            except ValueError as error:
                self.log(f"error opening ported project at {project_file}: {error}")
                return gr.update(selected=self.TAB_REMIX_HOME), \
                    gr.update(value=format_markdown(str(error), "error")), \
                   *empty_args

        messages = self.state.post_load_integrity_check()
        if messages:
            message_text = format_markdown(messages, "warning")
        else:
            message_text = format_markdown(self.TAB01_DEFAULT_MESSAGE)
        return_to_tab = self.state.get_progress_tab()
        scene_details = self.scene_chooser_details(self.state.tryattr("current_scene"))

        Session().set("last-video-remixer-project", project_path)
        self.invalidate_split_scene_cache()

        return gr.update(selected=return_to_tab), \
            gr.update(value=message_text), \
            self.state.tryattr("video_info1"), \
            self.state.tryattr("project_path"), \
            self.state.tryattr("project_fps", self.config.remixer_settings["def_project_fps"]), \
            self.state.tryattr("deinterlace", self.state.UI_SAFETY_DEFAULTS["deinterlace"]), \
            self.state.tryattr("split_type", self.state.UI_SAFETY_DEFAULTS["split_type"]), \
            self.state.tryattr("split_time", self.state.UI_SAFETY_DEFAULTS["split_time"]), \
            self.state.tryattr("scene_threshold", \
                               self.state.UI_SAFETY_DEFAULTS["scene_threshold"]), \
            self.state.tryattr("break_duration", self.state.UI_SAFETY_DEFAULTS["break_duration"]), \
            self.state.tryattr("break_ratio", self.state.UI_SAFETY_DEFAULTS["break_ratio"]), \
            self.state.tryattr("resize_w"), \
            self.state.tryattr("resize_h"), \
            self.state.tryattr("crop_w"), \
            self.state.tryattr("crop_h"), \
            self.state.tryattr("crop_offset_x", self.state.UI_SAFETY_DEFAULTS["crop_offsets"]), \
            self.state.tryattr("crop_offset_y", self.state.UI_SAFETY_DEFAULTS["crop_offsets"]), \
            self.state.tryattr("project_info2"), \
            self.state.tryattr("thumbnail_type", self.state.UI_SAFETY_DEFAULTS["thumbnail_type"]), \
            self.state.tryattr("min_frames_per_scene", \
                               self.state.UI_SAFETY_DEFAULTS["min_frames_per_scene"]), \
            *scene_details, \
            self.state.tryattr("project_info4"), \
            self.state.tryattr("resize", self.state.UI_SAFETY_DEFAULTS["resize"]), \
            self.state.tryattr("resynthesize", self.state.UI_SAFETY_DEFAULTS["resynthesize"]), \
            self.state.tryattr("inflate", self.state.UI_SAFETY_DEFAULTS["inflate"]), \
            self.state.tryattr("upscale", self.state.UI_SAFETY_DEFAULTS["upscale"]), \
            self.state.tryattr("upscale_option", self.state.UI_SAFETY_DEFAULTS["upscale_option"]), \
            self.state.tryattr("summary_info6"), \
            self.state.tryattr("output_filepath")

    ### REMIX SETTINGS EVENT HANDLERS

    # User has clicked Next > from Remix Settings
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
                     deinterlace,
                     split_time):
        self.state.project_path = project_path

        if not is_safe_path(project_path):
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                gr.update(value=format_markdown(f"The project path is not valid", "warning")),\
                *self.empty_args(3)

        if split_time < 1:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                gr.update(value=format_markdown(f"Scene Split Seconds should be >= 1", "warning")),\
                *self.empty_args(3)

        # TODO validate the other entries

        try:
            # this is first project write
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
            self.state.deinterlace = deinterlace
            self.state.split_time = split_time
            self.state.project_info2 = self.state.project_settings_report()
            self.state.processed_content_invalid = True

            # this is the first time project progress advances
            # user will expect to return to the setup tab on reopening
            self.log(f"saving new project at {self.state.project_filepath()}")
            self.state.save_progress("setup")

            Session().set("last-video-remixer-project", project_path)

            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                gr.update(value=format_markdown(self.TAB1_DEFAULT_MESSAGE)), \
                self.state.project_info2, \
                gr.update(value=format_markdown(self.TAB2_DEFAULT_MESSAGE)), \
                project_path

        except ValueError as error:
            return gr.update(selected=self.TAB_REMIX_SETTINGS), \
                gr.update(value=format_markdown(str(error), "error")), \
                *self.noop_args(3)

    def back_button1(self):
        return gr.update(selected=self.TAB_REMIX_HOME)

    ### SET UP PROJECT EVENT HANDLERS

    # User has clicked Set Up Project from Set Up Project
    def next_button2(self, thumbnail_type, min_frames_per_scene, skip_detection):
        global_options = self.config.ffmpeg_settings["global_options"]
        source_audio_crf = self.config.remixer_settings["source_audio_crf"]

        if not self.state.project_path:
            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                   gr.update(value=format_markdown(f"Project settings have not yet been saved on the previous tab", "error")), \
                   *self.empty_args(5)

        self.state.thumbnail_type = thumbnail_type
        self.state.min_frames_per_scene = min_frames_per_scene
        self.log("saving after setting thumbnail type and min frames per scene")
        self.state.save()

        # TODO this enormous conditional is messy
        if not skip_detection or not self.state.scenes_present():
            try:
                self.log(f"copying video from {self.state.source_video} to project path")
                self.state.save_original_video(prevent_overwrite=True)
            except ValueError as error:
                # ignore, don't copy the file a second time if the user is restarting here
                self.log(f"ignoring: {error}")

            self.log("saving project after ensuring video is in project path")
            self.state.save()

            try:
                self.log(f"creating source audio from {self.state.source_video}")
                self.state.create_source_audio(
                    source_audio_crf, global_options, prevent_overwrite=True)
            except ValueError as error:
                # ignore, don't create the file a second time if the user is restarting here
                self.log(f"ignoring: {error}")

            self.log("saving project after creating audio source")
            self.state.save()

            # user may be redoing project set up
            # settings changes could affect already-processed content
            self.log("resetting project on rendering for project settings")
            self.state.reset_at_project_settings()

            # split video into raw PNG frames, avoid doing again if redoing setup
            self.log("splitting source video into PNG frames")
            ffcmd = self.state.render_source_frames(global_options=global_options,
                                                    prevent_overwrite=True)
            if not ffcmd:
                self.log("rendering source frames skipped")
            else:
                self.log("saving project after converting video to PNG frames")
                self.state.save()
                self.log(f"FFmpeg command: {ffcmd}")

            self.state.scenes_path = os.path.join(self.state.project_path, "SCENES")
            self.state.dropped_scenes_path = os.path.join(self.state.project_path, "DROPPED_SCENES")
            self.log(f"creating scenes directory {self.state.scenes_path}")
            create_directory(self.state.scenes_path)
            self.log(f"creating dropped scenes directory {self.state.dropped_scenes_path}")
            create_directory(self.state.dropped_scenes_path)

            self.log("saving project after establishing scene paths")
            self.state.save()

            # split frames into scenes
            self.log(f"about to split scenes by {self.state.split_type}")
            error = self.state.split_scenes(self.log, prevent_overwrite=False)
            if error:
                return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                    gr.update(value=format_markdown(f"There was an error splitting the source video: {error}", "error")), \
                    *self.empty_args(5)
            self.log("saving project after splitting into scenes")
            self.state.save()

            if self.state.min_frames_per_scene > 0:
                self.log(f"about to consolidate scenes with too few frames")
                self.state.consolidate_scenes(self.log)
                self.log("saving project after consolidating scenes")
                self.state.save()

            self.state.scene_names = sorted(get_directories(self.state.scenes_path))

            try:
                self.log("enhance source video info with extra data including frame dimensions")
                self.state.enhance_video_info(self.log, ignore_errors=False)
                self.state.save()
            except ValueError as error:
                return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                    gr.update(value=format_markdown(f"There was an error retrieving source frame dimensions: {error}", "error")), \
                    *self.empty_args(5)

            # if there's only one scene, assume it should be kept to save some time
            if len(self.state.scene_names) < 2:
                self.state.keep_all_scenes()
            else:
                self.state.drop_all_scenes()

            self.state.current_scene = 0
            self.log("saving project after establishing scene names")
            self.state.save()

        self.log(f"about to create thumbnails of type {self.state.thumbnail_type}")
        try:
            self.state.create_thumbnails(self.log, global_options, self.config.remixer_settings)
        except ValueError as error:
            return gr.update(selected=self.TAB_SET_UP_PROJECT), \
                   gr.update(value=format_markdown(f"There was an error creating thumbnails from the source video: {error}", "error")), \
                   *self.empty_args(5)

        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))
        self.log("saving project after creating scene thumbnails")
        self.state.save()

        # TODO this is fine as part of project setup but does it belong here?
        self.state.clips_path = os.path.join(self.state.project_path, "CLIPS")
        self.log(f"creating clips directory {self.state.clips_path}")
        create_directory(self.state.clips_path)

        # user will expect to return to scene chooser on reopening
        self.log("saving project after setting up scene selection states")
        self.state.save_progress("choose")

        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
               gr.update(value=format_markdown(self.TAB2_DEFAULT_MESSAGE)), \
               *self.scene_chooser_details(self.state.current_scene)

    def back_button2(self):
        return gr.update(selected=self.TAB_REMIX_SETTINGS)

    def thumb_change(self, thumbnail_type):
        self.state.thumbnail_type = thumbnail_type
        if self.state.project_path:
            self.log(f"Saving project after hot-setting thumbnail type to {thumbnail_type}")
            self.state.save()

    ### SCENE CHOOSER EVENT HANDLERS

    # User has clicked on the Keep or Drop radio button
    def scene_state_button(self, scene_index, scene_label, scene_state):
        self.state.scene_states[scene_label] = scene_state
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

    def keep_next(self, scene_index, scene_label):
        self.state.scene_states[scene_label] = "Keep"
        self.state.save()
        return self.next_scene(scene_index, scene_label)

    def drop_next(self, scene_index, scene_label):
        self.state.scene_states[scene_label] = "Drop"
        self.state.save()
        return self.next_scene(scene_index, scene_label)

    def next_scene(self, scene_index, scene_label):
        if scene_index < len(self.state.scene_names)-1:
            scene_index += 1
            self.state.current_scene = scene_index
        return self.scene_chooser_details(self.state.current_scene)

    def prev_scene(self, scene_index, scene_label):
        if scene_index > 0:
            scene_index -= 1
            self.state.current_scene = scene_index
        return self.scene_chooser_details(self.state.current_scene)

    def next_keep(self, scene_index, scene_label):
        for index in range(scene_index+1, len(self.state.scene_names)):
            scene_name = self.state.scene_names[index]
            if self.state.scene_states[scene_name] == "Keep":
                self.state.current_scene = index
                break
        return self.scene_chooser_details(self.state.current_scene)

    def prev_keep(self, scene_index, scene_label):
        for index in range(scene_index-1, -1, -1):
            scene_name = self.state.scene_names[index]
            if self.state.scene_states[scene_name] == "Keep":
                self.state.current_scene = index
                break
        return self.scene_chooser_details(self.state.current_scene)

    def first_scene(self, scene_index, scene_label):
        self.state.current_scene = 0
        return self.scene_chooser_details(self.state.current_scene)

    def last_scene(self, scene_index, scene_label):
        self.state.current_scene = len(self.state.scene_names) - 1
        return self.scene_chooser_details(self.state.current_scene)

    def split_scene_shortcut(self, scene_index):
        default_percent = 50.0
        scene_index = int(scene_index)
        display_frame = self.compute_preview_frame(scene_index, default_percent)
        _, _, _, scene_info = self.state.scene_chooser_details(scene_index)
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_SPLIT_SCENE), \
            scene_index, \
            default_percent, \
            display_frame, \
            scene_info

    def choose_range_shortcut(self, scene_index):
        return gr.update(selected=self.TAB_REMIX_EXTRA), \
            gr.update(selected=self.TAB_EXTRA_CHOOSE_RANGE), \
            scene_index, \
            scene_index

    def keep_all_scenes(self, scene_index, scene_label):
        self.state.keep_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_all_scenes(self, scene_index, scene_label):
        self.state.drop_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def invert_all_scenes(self, scene_index, scene_label):
        self.state.invert_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_processed_shortcut(self, scene_index):
        return gr.update(selected=7), \
            gr.update(selected=self.TAB_EXTRA_DROP_PROCESSED), \
            scene_index


    # given scene name such as [042-420] compute details to display in Scene Chooser
    def scene_chooser_details(self, scene_index):
        if not self.state.thumbnails:
            self.log(f"thumbnails don't exist yet in scene_chooser_details()")
            return self.empty_args(5)
        try:
            scene_name, thumbnail_path, scene_state, scene_info = \
                self.state.scene_chooser_details(scene_index)
            return scene_index, scene_name, thumbnail_path, scene_state, scene_info
        except ValueError as error:
            self.log(error)
            return self.empty_args(5)

    # User has clicked Done Choosing Scenes from Scene Chooser
    def next_button3(self):
        if not self.state.project_path:
            return gr.update(selected=self.TAB_CHOOSE_SCENES), self.state.project_info4

        self.state.project_info4 = self.state.chosen_scenes_report()

        # user will expect to return to the compilation tab on reopening
        self.log("saving project after displaying scene choices")
        self.state.save_progress("compile")

        return gr.update(selected=self.TAB_COMPILE_SCENES), self.state.project_info4

    def back_button3(self):
        return gr.update(selected=self.TAB_SET_UP_PROJECT)

    ### COMPILE SCENES EVENT HANDLERS

    # User has clicked Compile Scenes from Compile Scenes
    def next_button4(self):
        if not self.state.project_path:
            return gr.update(selected=self.TAB_COMPILE_SCENES), \
                   gr.update(value=format_markdown(f"The project has not yet been set up from the Set Up Project tab.", "error")), \
                   *self.empty_args(5)

        self.log("moving dropped scenes to dropped scenes directory")
        self.state.recompile_scenes()

        # scene choice changes are what invalidate previously made audio clips,
        # so clear them now along with dependent remix content
        self.log("purging now-stale remix content")
        self.state.clean_remix_content(purge_from="audio_clips")

        # user will expect to return to the processing tab on reopening
        self.log("saving project after compiling scenes")
        self.state.save_progress("process")

        return gr.update(selected=self.TAB_PROC_OPTIONS),  \
               gr.update(value=format_markdown(self.TAB4_DEFAULT_MESSAGE)), \
               gr.update(value=format_markdown(self.TAB5_DEFAULT_MESSAGE))

    def back_button4(self):
        return gr.update(selected=self.TAB_CHOOSE_SCENES)

    ### PROCESS REMIX EVENT HANDLERS

    # User has clicked Process Remix from Process Remix
    def next_button5(self, resynthesize, inflate, resize, upscale, upscale_option):
        noop_args = self.noop_args(9)
        if not self.state.project_path or not self.state.scenes_path:
            return gr.update(selected=self.TAB_PROC_OPTIONS), \
                   gr.update(value=format_markdown(
                    "The project has not yet been set up from the Set Up Project tab.", "error")), \
                   *noop_args

        self.state.resynthesize = resynthesize
        self.state.inflate = inflate
        self.state.resize = resize
        self.state.upscale = upscale
        upscale_option_changed = False
        if self.state.upscale_option != None and self.state.upscale_option != upscale_option:
            upscale_option_changed = True
        self.state.upscale_option = upscale_option
        self.state.setup_processing_paths()
        self.log("saving project after storing processing choices")
        self.state.save()

        # user may have changed scene choices and skipped compiling scenes
        self.state.recompile_scenes()

        jot = Jot()
        kept_scenes = self.state.kept_scenes()
        if kept_scenes:
            if self.state.processed_content_invalid:
                self.log("setup options changed, purging all processed content")
                self.state.purge_processed_content(purge_from=self.state.RESIZE_STEP)
                self.state.processed_content_invalid = False
            else:
                self.log("purging stale content")
                self.state.purge_stale_processed_content(upscale_option_changed)
                self.log("purging incomplete content")
                self.state.purge_incomplete_processed_content()
            self.log("saving project after purging stale and incomplete content")
            self.state.save()

            if not self.state.resize \
                and not self.state.resynthesize \
                and not self.state.inflate \
                and not self.state.upscale:
                jot.down(f"Original source scenes in {self.state.scenes_path}")

            if self.state.resize:
                if not self.state.processed_content_complete(self.state.RESIZE_STEP):
                    self.log("about to resize scenes")
                    self.state.resize_scenes(self.log,
                                             kept_scenes,
                                             self.config.remixer_settings)
                    self.log("saving project after resizing frames")
                    self.state.save()
                jot.down(f"Resized/cropped scenes in {self.state.resize_path}")

            if self.state.resynthesize:
                if not self.state.processed_content_complete(self.state.RESYNTH_STEP):
                    two_pass_resynth = self.config.remixer_settings["resynth_type"] == 2
                    self.state.resynthesize_scenes(self.log,
                                                kept_scenes,
                                                self.engine,
                                                self.config.engine_settings,
                                                two_pass=two_pass_resynth)
                    self.log("saving project after resynthesizing frames")
                    self.state.save()
                jot.down(f"Resynthesized scenes in {self.state.resynthesis_path}")

            if self.state.inflate:
                if not self.state.processed_content_complete(self.state.INFLATE_STEP):
                    self.state.inflate_scenes(self.log,
                                                kept_scenes,
                                                self.engine,
                                                self.config.engine_settings)
                    self.log("saving project after inflating frames")
                    self.state.save()
                jot.down(f"Inflated scenes in {self.state.inflation_path}")

            if self.state.upscale:
                if not self.state.processed_content_complete(self.state.UPSCALE_STEP):
                    self.state.upscale_scenes(self.log,
                                            kept_scenes,
                                            self.config.realesrgan_settings,
                                            self.config.remixer_settings)
                    self.log("saving project after upscaling frames")
                    self.state.save()
                jot.down(f"Upscaled scenes in {self.state.upscale_path}")

            styled_report = style_report("Content Ready for Remix Video:", jot.lines, color="more")
            self.state.summary_info6 = styled_report

            self.state.output_filepath = self.state.default_remix_filepath()
            output_filepath_custom = self.state.default_remix_filepath("CUSTOM")
            output_filepath_marked = self.state.default_remix_filepath("MARKED")
            output_filepath_labeled = self.state.default_remix_filepath("LABELED")
            self.state.save()

            # user will expect to return to the save remix tab on reopening
            self.log("saving project after completing processing steps")
            self.state.save_progress("save")

            return gr.update(selected=self.TAB_SAVE_REMIX), \
                   gr.update(value=format_markdown(self.TAB5_DEFAULT_MESSAGE)), \
                   styled_report, \
                   self.state.output_filepath, \
                   output_filepath_custom, \
                   output_filepath_marked, \
                   output_filepath_labeled, \
                   gr.update(value=format_markdown(self.TAB60_DEFAULT_MESSAGE)), \
                   gr.update(value=format_markdown(self.TAB61_DEFAULT_MESSAGE)), \
                   gr.update(value=format_markdown(self.TAB62_DEFAULT_MESSAGE)), \
                   gr.update(value=format_markdown(self.TAB63_DEFAULT_MESSAGE))
        else:
            return gr.update(selected=self.TAB_PROC_OPTIONS), \
                   gr.update(value=format_markdown("At least one scene must be set to 'Keep' before processing can proceed", "error")), \
                   *noop_args

    def back_button5(self):
        return gr.update(selected=self.TAB_COMPILE_SCENES)

    def process_all_changed(self, process_all : bool):
        return gr.update(value=process_all), \
            gr.update(value=process_all), \
            gr.update(value=process_all), \
            gr.update(value=process_all)

    ### SAVE REMIX EVENT HANDLERS

    def prepare_save_remix(self, output_filepath):
        if not output_filepath:
            raise ValueError("Enter a path for the remixed video to proceed")

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes were found")

        self.log("about to check and drop empty scenes")
        self.state.drop_empty_processed_scenes(kept_scenes)
        self.log("saving after dropping empty scenes")
        self.state.save()

        # get this again in case scenes have been auto-dropped
        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            raise ValueError("No kept scenes after removing empties")

        global_options = self.config.ffmpeg_settings["global_options"]

        # create audio clips only if they do not already exist
        # this depends on the audio clips being purged at the time the scene selection are compiled
        if self.state.video_details["has_audio"] and not \
                self.state.processed_content_complete(self.state.AUDIO_STEP):
            self.log("about to create audio clips")
            audio_format = self.config.remixer_settings["audio_format"]
            self.state.create_audio_clips(self.log, global_options, audio_format=audio_format)
            self.log("saving project after creating audio clips")
            self.state.save()

        # always recreate video and scene clips
        self.state.clean_remix_content(purge_from="video_clips")
        return global_options, kept_scenes

    def save_remix(self, global_options, kept_scenes):
        self.log(f"about to create video clips")
        self.state.create_video_clips(self.log, kept_scenes, global_options)
        self.log("saving project after creating video clips")
        self.state.save()

        self.log("about to create scene clips")
        self.state.create_scene_clips(kept_scenes, global_options)
        self.log("saving project after creating scene clips")
        self.state.save()

        if not self.state.clips:
            return gr.update(value="No processed video clips were found", visible=True)

        self.log("about to create remix viedeo")
        ffcmd = self.state.create_remix_video(global_options, self.state.output_filepath)
        self.log(f"FFmpeg command: {ffcmd}")
        self.log("saving project after creating remix video")
        self.state.save()

    def save_custom_remix(self,
                          output_filepath,
                          global_options,
                          kept_scenes,
                          custom_video_options,
                          custom_audio_options,
                          draw_text_options=None):
        _, _, output_ext = split_filepath(output_filepath)
        output_ext = output_ext[1:]

        self.log(f"about to create custom video clips")
        self.state.create_custom_video_clips(self.log, kept_scenes, global_options,
                                             custom_video_options=custom_video_options,
                                             custom_ext=output_ext,
                                             draw_text_options=draw_text_options)
        self.log("saving project after creating custom video clips")
        self.state.save()

        self.log("about to create custom scene clips")
        self.state.create_custom_scene_clips(kept_scenes, global_options,
                                             custom_audio_options=custom_audio_options,
                                             custom_ext=output_ext)
        self.log("saving project after creating custom scene clips")
        self.state.save()

        if not self.state.clips:
            raise ValueError("No processed video clips were found")

        self.log("about to create remix viedeo")
        ffcmd = self.state.create_remix_video(global_options, output_filepath)
        self.log(f"FFmpeg command: {ffcmd}")
        self.log("saving project after creating remix video")
        self.state.save()

    # User has clicked Save Remix from Save Remix
    def next_button60(self, output_filepath, quality):
        if not self.state.project_path:
            return gr.update(value=format_markdown(
                    "The project has not yet been set up from the Set Up Project tab.", "error"))

        self.state.output_filepath = output_filepath
        self.state.output_quality = quality
        self.log("saving after storing remix output choices")
        self.state.save()

        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            self.save_remix(global_options, kept_scenes)
            return gr.update(value=format_markdown(f"Remixed video {output_filepath} is complete.", "highlight"))

        except ValueError as error:
            return gr.update(value=format_markdown(str(error), "error"))

    # User has clicked Save Custom Remix from Save Remix
    def next_button61(self, custom_video_options, custom_audio_options, output_filepath):
        if not self.state.project_path:
            return gr.update(value=format_markdown(
                    "The project has not yet been set up from the Set Up Project tab.", "error"))
        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            self.save_custom_remix(output_filepath, global_options, kept_scenes,
                                   custom_video_options, custom_audio_options)
            return gr.update(value=format_markdown(f"Remixed custom video {output_filepath} is complete.", "highlight"))
        except ValueError as error:
            return gr.update(value=format_markdown(str(error), "error"))

    # User has clicked Save Marked Remix from Save Remix
    def next_button62(self, marked_video_options, marked_audio_options, output_filepath):
        if not self.state.project_path:
            return gr.update(value=format_markdown(
                    "The project has not yet been set up from the Set Up Project tab.", "error"))
        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            draw_text_options = {}
            draw_text_options["font_size"] = self.config.remixer_settings["marked_font_size"]
            draw_text_options["font_color"] = self.config.remixer_settings["marked_font_color"]
            draw_text_options["font_file"] = self.config.remixer_settings["marked_font_file"]
            draw_text_options["draw_box"] = self.config.remixer_settings["marked_draw_box"]
            draw_text_options["box_color"] = self.config.remixer_settings["marked_box_color"]
            draw_text_options["border_size"] = self.config.remixer_settings["marked_border_size"]
            draw_text_options["marked_at_top"] = self.config.remixer_settings["marked_at_top"]

            # account for upscaling
            upscale_factor = 1
            if self.state.upscale:
                if self.state.upscale_option == "2X":
                    upscale_factor = 2
                elif self.state.upscale_option == "4X":
                    upscale_factor = 4
            draw_text_options["crop_width"] = self.state.crop_w * upscale_factor
            draw_text_options["crop_height"] = self.state.crop_h * upscale_factor

            self.save_custom_remix(output_filepath, global_options, kept_scenes,
                                   marked_video_options, marked_audio_options, draw_text_options)
            return gr.update(value=format_markdown(f"Remixed marked video {output_filepath} is complete.", "highlight"))
        except ValueError as error:
            return gr.update(value=format_markdown(str(error), "error"))

    # User has clicked Save Labeled Remix from Save Remix
    def next_button63(self,
                      label_text,
                      label_font_size,
                      label_font_color,
                      label_font_file,
                      label_draw_box,
                      label_box_color,
                      label_border_size,
                      label_at_top,
                      output_filepath,
                      quality):
        if not self.state.project_path:
            return gr.update(value=format_markdown(
                "The project has not yet been set up from the Set Up Project tab.", "error"))
        if label_font_size <= 0.0:
            return gr.update(value=format_markdown(
                "The Font Factor must be > 0", "warning"))
        if not label_font_file:
           return gr.update(value=format_markdown(
                "The Font File must not be blank", "warning"))
        if not os.path.exists(label_font_file):
           return gr.update(value=format_markdown(
                f"The Font File {os.path.abspath(label_font_file)} was not found", "error"))
        if not label_font_file:
           return gr.update(value=format_markdown(
                "The Font File must not be blank", "warning"))
        if not label_font_color:
           return gr.update(value=format_markdown(
                "The Font Color must not be blank", "warning"))
        if label_draw_box:
            if (label_border_size <= 0.0):
                return gr.update(value=format_markdown(
                    "The Border Factor must be > 0", "warning"))
        if not label_box_color:
           return gr.update(value=format_markdown(
                "The Background Color must not be blank", "warning"))
        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            draw_text_options = {}
            draw_text_options["font_size"] = label_font_size
            draw_text_options["font_color"] = label_font_color
            draw_text_options["font_file"] = label_font_file
            draw_text_options["draw_box"] = label_draw_box
            draw_text_options["box_color"] = label_box_color
            draw_text_options["border_size"] = label_border_size
            draw_text_options["marked_at_top"] = label_at_top
            draw_text_options["label"] = label_text

            labeled_video_options = self.config.remixer_settings["labeled_ffmpeg_video"]
            labeled_audio_options = self.config.remixer_settings["labeled_ffmpeg_audio"]
            labeled_video_options = labeled_video_options.replace("<CRF>", str(quality))
            self.log(f"using labeled video options: {labeled_video_options}")
            self.log(f"using labeled audeo options: {labeled_audio_options}")

            # account for upscaling
            upscale_factor = 1
            if self.state.upscale:
                if self.state.upscale_option == "2X":
                    upscale_factor = 2
                elif self.state.upscale_option == "4X":
                    upscale_factor = 4
            draw_text_options["crop_width"] = self.state.crop_w * upscale_factor
            draw_text_options["crop_height"] = self.state.crop_h * upscale_factor

            try:
                self.save_custom_remix(output_filepath, global_options, kept_scenes,
                                    labeled_video_options, labeled_audio_options, draw_text_options)
                return gr.update(value=format_markdown(f"Remixed labeled video {output_filepath} is complete.", "highlight"))
            except FFRuntimeError as error:
                return gr.update(value=format_markdown(f"Error: {error}.", "error"))

        except ValueError as error:
            return gr.update(value=format_markdown(str(error), "error"))

    def back_button6(self):
        return gr.update(selected=self.TAB_PROC_OPTIONS)

    def drop_button700(self, scene_index):
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(scene_index, (int, float)):
            return gr.update(value=format_markdown(f"Please enter a Scene Index to get started", "warning"))

        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            return gr.update(value=format_markdown(f"Please enter a Scene Index from 0 to {last_scene}", "warning"))

        removed = self.state.force_drop_processed_scene(scene_index)

        # audio clips aren't cleaned each time a remix is saved
        # clean now to ensure the dropped scene audio clip is removed
        self.state.clean_remix_content(purge_from="audio_clips")

        self.log(f"removed files: {removed}")
        self.log(
            f"saving project after using force_drop_processed_scene for scene index {scene_index}")
        self.state.save()
        removed = "\r\n".join(removed)
        return gr.update(value=format_markdown(f"Removed:\r\n{removed}"))

    def choose_button701(self, first_scene_index, last_scene_index, scene_state):
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(first_scene_index, (int, float)) \
                or not isinstance(last_scene_index, (int, float)):
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
    gr.update(value=format_markdown("Please enter Scene Indexes to get started", "warning")), \
                *self.empty_args(5)

        first_scene_index = int(first_scene_index)
        last_scene_index = int(last_scene_index)
        if first_scene_index < 0 \
                or first_scene_index > last_scene \
                or last_scene_index < 0 \
                or last_scene_index > last_scene:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown(f"Please enter valid Scene Indexes between 0 and {last_scene} to get started", "warning")), \
                *self.empty_args(5)

        if first_scene_index >= last_scene_index:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown(f"'Ending Scene Index' must be higher than 'Starting Scene Index'", "warning")), \
                *self.empty_args(5)

        if scene_state not in ["Keep", "Drop"]:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
    gr.update(value=format_markdown("Please make a Scenes Choice to get started", "warning")), \
                *self.empty_args(5)

        for scene_index in range(first_scene_index, last_scene_index + 1):
            scene_name = self.state.scene_names[scene_index]
            self.state.scene_states[scene_name] = scene_state

        self.state.current_scene = first_scene_index

        first_scene_name = self.state.scene_names[first_scene_index]
        last_scene_name = self.state.scene_names[last_scene_index]
        message = f"Scenes {first_scene_name} through {last_scene_name} set to '{scene_state}'"
        self.log(f"saving project after {message}")
        self.state.save()

        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
            gr.update(value=format_markdown(message)), \
            *self.scene_chooser_details(self.state.current_scene)

    def compute_scene_split(self, scene_index : int, split_percent : float):
        scene_name = self.state.scene_names[scene_index]
        split_percent = 0.0 if isinstance(split_percent, type(None)) else split_percent
        split_point = split_percent / 100.0
        first_frame, last_frame, num_width = details_from_group_name(scene_name)
        num_frames = (last_frame - first_frame) + 1
        split_frame = math.ceil(num_frames * split_point)

        # ensure at least one frame remains in the lower scene
        split_frame = 1 if split_frame == 0 else split_frame

        # ensure at least one frame remains in the upper scene
        split_frame = num_frames-1 if split_frame >= num_frames else split_frame

        return scene_name, num_width, num_frames, first_frame, last_frame, split_frame

    def valid_split_scene_cache(self, scene_index):
        if self.split_scene_cache and self.split_scene_cached_index == scene_index:
            return self.split_scene_cache
        else:
            return None

    def fill_split_scene_cache(self, scene_index, data):
        self.split_scene_cache = data
        self.split_scene_cached_index = scene_index

    def invalidate_split_scene_cache(self):
        self.split_scene_cache = []
        self.split_scene_cached_index = -1

    def split_button702(self, scene_index, split_percent):
        global_options = self.config.ffmpeg_settings["global_options"]

        if not isinstance(scene_index, (int, float)):
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown("Please enter a Scene Index to get started", "warning")), \
                *self.empty_args(5)

        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1
        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown(f"Please enter a Scene Index from 0 to {last_scene}", "warning")), \
                *self.empty_args(5)

        scene_name, num_width, num_frames, first_frame, last_frame, split_frame \
            = self.compute_scene_split(scene_index, split_percent)

        if num_frames < 2:
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown("Scene must have at least two frames to be split", "error")), \
                *self.empty_args(5)

        self.log(f"setting split frame to {split_frame}")

        new_lower_first_frame = first_frame
        new_lower_last_frame = first_frame + (split_frame - 1)
        new_lower_scene_name = VideoRemixerState.encode_scene_label(num_width,
                                                new_lower_first_frame, new_lower_last_frame, 0, 0)
        self.log(f"new lower scene name: {new_lower_scene_name}")

        new_upper_first_frame = first_frame + split_frame
        new_upper_last_frame = last_frame
        new_upper_scene_name = VideoRemixerState.encode_scene_label(num_width,
                                                new_upper_first_frame, new_upper_last_frame, 0, 0)
        self.log(f"new upper scene name: {new_upper_scene_name}")

        original_scene_path = os.path.join(self.state.scenes_path, scene_name)
        new_lower_scene_path = os.path.join(self.state.scenes_path, new_lower_scene_name)
        new_upper_scene_path = os.path.join(self.state.scenes_path, new_upper_scene_name)
        self.log(f"new lower scene path: {new_lower_scene_path}")
        self.log(f"new upper scene path: {new_upper_scene_path}")

        self.state.uncompile_scenes()

        frame_files = sorted(get_files(original_scene_path))
        num_frame_files = len(frame_files)
        if num_frame_files != num_frames:
            message = f"Mismatch between expected frames ({num_frames}) and found frames " + \
                f"({num_frame_files}) in scene path '{original_scene_path}'"
            return gr.update(selected=self.TAB_REMIX_EXTRA), \
                gr.update(value=format_markdown(message, "error")), \
                    *self.empty_args(5)

        messages = Jot()

        self.log(f"about to create directory '{new_upper_scene_path}'")
        create_directory(new_upper_scene_path)
        messages.add(f"Created directory {new_upper_scene_path}")

        move_count = 0
        for index, frame_file in enumerate(frame_files):
            if index < split_frame:
                continue
            frame_path = os.path.join(original_scene_path, frame_file)
            _, filename, ext = split_filepath(frame_path)
            new_frame_path = os.path.join(new_upper_scene_path, filename + ext)

            self.log(f"about to move '{frame_path}' to '{new_frame_path}'")
            shutil.move(frame_path, new_frame_path)
            move_count += 1
        messages.add(f"Moved {move_count} frames to {new_upper_scene_path}")

        self.log(f"about to rename '{original_scene_path}' to '{new_lower_scene_path}'")
        os.replace(original_scene_path, new_lower_scene_path)
        messages.add(f"Renamed {original_scene_path} to {new_lower_scene_path}")

        self.log(f"about to rename scene name '{scene_name}' to '{new_lower_scene_name}'")
        self.state.scene_names[scene_index] = new_lower_scene_name
        self.log(f"about to add new scene name '{new_upper_scene_name}'")
        self.state.scene_names.append(new_upper_scene_name)
        self.log(f"sorting scene names")
        self.state.scene_names = sorted(self.state.scene_names)

        scene_state = self.state.scene_states[scene_name]
        self.log(f"about to delete the original scene state for scene '{scene_name}'")
        del self.state.scene_states[scene_name]
        self.log(f"adding scene state for new lower scene '{new_lower_scene_name}'")
        self.state.scene_states[new_lower_scene_name] = scene_state
        messages.add(f"Set scene {new_lower_scene_name} to {scene_state}")
        self.log(f"adding scene state for new upper scene '{new_upper_scene_name}'")
        self.state.scene_states[new_upper_scene_name] = scene_state
        messages.add(f"Set scene {new_upper_scene_name} to {scene_state}")
        self.state.current_scene = scene_index

        thumbnail_file = self.state.thumbnails[scene_index]
        self.log(f"about to delete original thumbnail file '{thumbnail_file}'")
        os.remove(thumbnail_file)
        messages.add(f"Deleted thumbnail {thumbnail_file}")
        self.log(f"about to create thumbnail for new lower scene {new_lower_scene_name}")
        self.state.create_thumbnail(new_lower_scene_name, self.log, global_options,
                                    self.config.remixer_settings)
        messages.add(f"Created thumbnail for scene {new_lower_scene_name}")
        self.log(f"about to create thumbnail for new upper scene {new_upper_scene_name}")
        self.state.create_thumbnail(new_upper_scene_name, self.log, global_options,
                                    self.config.remixer_settings)
        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))
        messages.add(f"Created thumbnail for scene {new_upper_scene_name}")

        self.log("saving project after completing scene split")
        self.state.save()

        self.log("invalidating scene split cache after splitting")
        self.invalidate_split_scene_cache()

        report = messages.report()
        self.log(report)

        message = f"Scene split into new scenes {new_lower_scene_name} and {new_upper_scene_name}"
        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
            gr.update(value=format_markdown(message)), \
            *self.scene_chooser_details(self.state.current_scene)

    def compute_preview_frame(self, scene_index, split_percent):
        scene_index = int(scene_index)
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1
        if scene_index < 0 or scene_index > last_scene:
            return None

        scene_name, _, num_frames, _, _, split_frame = self.compute_scene_split(scene_index, split_percent)
        original_scene_path = os.path.join(self.state.scenes_path, scene_name)
        frame_files = self.valid_split_scene_cache(scene_index)
        if not frame_files:
            # optimize to uncompile only the first time it's needed
            self.state.uncompile_scenes()

            frame_files = sorted(get_files(original_scene_path))
            self.fill_split_scene_cache(scene_index, frame_files)

        num_frame_files = len(frame_files)
        if num_frame_files != num_frames:
            self.log(f"compute_preview_frame(): expected {num_frame_files} frame files but found {num_frames} for scene index {scene_index} - returning None")
            return None
        return frame_files[split_frame]

    def preview_button702(self, scene_index, split_percent):
        if not isinstance(scene_index, (int, float)):
            return self.empty_args(2)
        scene_index = int(scene_index)
        if scene_index < 0 or scene_index >= len(self.state.scene_names):
            return self.empty_args(2)

        display_frame = self.compute_preview_frame(scene_index, split_percent)
        _, _, _, scene_info = self.state.scene_chooser_details(scene_index)
        return display_frame, scene_info

    def compute_advance_702(self, scene_index, split_percent, by_frame : bool, by_next : bool):
        if not isinstance(scene_index, (int, float)):
            return self.empty_args(2)

        scene_index = int(scene_index)
        scene_name = self.state.scene_names[scene_index]
        first_frame, last_frame, _ = details_from_group_name(scene_name)
        num_frames = (last_frame - first_frame) + 1
        split_percent_frame = num_frames * split_percent / 100.0

        if by_frame:
            new_split_frame = split_percent_frame + 1 if by_next else split_percent_frame - 1
        else:
            frames_1s = self.state.project_fps
            new_split_frame = split_percent_frame + frames_1s if by_next \
                else split_percent_frame - frames_1s

        new_split_frame = 0 if new_split_frame < 0 else new_split_frame
        new_split_frame = num_frames if new_split_frame > num_frames else new_split_frame

        new_split_percent = new_split_frame / num_frames
        return new_split_percent * 100.0

    def prev_second_702(self, scene_index, split_percent):
        return self.compute_advance_702(scene_index, split_percent, by_frame=False, by_next=False)

    def prev_frame_702(self, scene_index, split_percent):
        return self.compute_advance_702(scene_index, split_percent, by_frame=True, by_next=False)

    def next_frame_702(self, scene_index, split_percent):
        return self.compute_advance_702(scene_index, split_percent, by_frame=True, by_next=True)

    def next_second_702(self, scene_index, split_percent):
        return self.compute_advance_702(scene_index, split_percent, by_frame=False, by_next=True)

    def export_project_703(self, new_project_path, new_project_name):
        empty_args = [gr.update(visible=False), gr.update(visible=False)]
        if not new_project_path:
            return gr.update(value=format_markdown("Please enter a Project Path for the new project", "warning")), *empty_args
        if not is_safe_path(new_project_path):
            return gr.update(value=format_markdown("The entered Project Path is not valid", "warning")), *empty_args
        if not new_project_name:
            return gr.update(value=format_markdown("Please enter a Project Name for the new project", "warning")), *empty_args

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return gr.update(value=format_markdown("No kept scenes were found", "warning")), *empty_args

        full_new_project_path = os.path.join(new_project_path, new_project_name)
        try:
            create_directory(full_new_project_path)
            new_profile_filepath = self.state.copy_project_file(full_new_project_path)

            # load the copied project file
            new_state = VideoRemixerState.load(new_profile_filepath, self.log)

            # update project paths to the new one
            new_state = VideoRemixerState.load_ported(new_state.project_path, new_profile_filepath, self.log, save_original=False)

            # ensure the project directories exist
            new_state.post_load_integrity_check()

            # copy the source video
            with Mtqdm().open_bar(total=1, desc="Copying") as bar:
                Mtqdm().message(bar, "Copying source video - no ETA")
                shutil.copy(self.state.source_video, new_state.source_video)
                Mtqdm().update_bar(bar)

            # copy the source audio (if not using the source video as audio source)
            if self.state.source_audio != self.state.source_video:
                with Mtqdm().open_bar(total=1, desc="Copying") as bar:
                    Mtqdm().message(bar, "Copying source audio - no ETA")
                    shutil.copy(self.state.source_audio, new_state.source_audio)
                    Mtqdm().update_bar(bar)

            # ensure scenes path contains all / only kept scenes
            self.state.recompile_scenes()

            # prepare to rebuild scene_states dict, and scene_names, thumbnails lists
            # in the new project
            new_state.scene_states = {}
            new_state.scene_names = []
            new_state.thumbnails = []

            with Mtqdm().open_bar(total=len(kept_scenes), desc="Exporting") as bar:
                for index, scene_name in enumerate(self.state.scene_names):
                    state = self.state.scene_states[scene_name]
                    if state == "Keep":
                        scene_name = self.state.scene_names[index]
                        new_state.scene_states[scene_name] = "Keep"

                        new_state.scene_names.append(scene_name)
                        scene_dir = os.path.join(self.state.scenes_path, scene_name)
                        new_scene_dir = os.path.join(new_state.scenes_path, scene_name)
                        duplicate_directory(scene_dir, new_scene_dir)

                        scene_thumbnail = self.state.thumbnails[index]
                        _, filename, ext = split_filepath(scene_thumbnail)
                        new_thumbnail = os.path.join(new_state.thumbnail_path, filename + ext)
                        new_state.thumbnails.append(new_thumbnail)
                        shutil.copy(scene_thumbnail, new_thumbnail)
                        Mtqdm().update_bar(bar)

            # reset some things
            new_state.current_scene = 0
            new_state.audio_clips = []
            new_state.clips = []
            new_state.processed_content_invalid = False
            new_state.progress = "choose"

            new_state.save()

            return gr.update(value=format_markdown(f"Kept scenes saved as new project: {full_new_project_path} ")), \
                gr.update(visible=True, value=full_new_project_path), \
                gr.update(visible=True)

        except ValueError as error:
            return gr.update(value=format_markdown(str(error), "error")), *empty_args

    def open_result703(self, new_project_path):
        return gr.update(selected=self.TAB_REMIX_HOME), \
            gr.update(value=new_project_path), \
            gr.update(value=format_markdown(self.TAB01_DEFAULT_MESSAGE))

    CLEANSE_SCENES_PATH = "cleansed_scenes"
    CLEANSE_SCENES_FACTOR = 4.0

    def cleanse_button704(self):
        kept_scenes = self.state.kept_scenes()
        if len(kept_scenes) < 1:
            return gr.update(value=format_markdown("No kept scenes were found", "warning"))
        self.state.uncompile_scenes()

        working_path = os.path.join(self.state.project_path, self.CLEANSE_SCENES_PATH)
        if os.path.exists(working_path):
            self.log(f"purging previous working directory {working_path}")
            purge_path = self.state.purge_paths([working_path])
            if purge_path:
                self.state.copy_project_file(purge_path)
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

        upscaler = self.state.get_upscaler(self.log, self.config.realesrgan_settings, self.config.remixer_settings)
        with Mtqdm().open_bar(total=len(kept_scenes), desc="Cleansing") as bar:
            for scene_name in kept_scenes:
                scene_path = os.path.join(self.state.scenes_path, scene_name)
                upscale_scene_path = os.path.join(upscale_path, scene_name)
                create_directory(upscale_scene_path)
                self.state.upscale_scene(upscaler, scene_path, upscale_scene_path, self.CLEANSE_SCENES_FACTOR)

                downsample_scene_path = os.path.join(downsample_path, scene_name)
                create_directory(downsample_scene_path)
                self.state.resize_scene(self.log,
                                        upscale_scene_path,
                                        downsample_scene_path,
                                        content_width,
                                        content_height,
                                        scale_type)
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

        shutil.rmtree(working_path)
        self.invalidate_split_scene_cache()
        return gr.update(value=format_markdown("Kept scenes replaced with cleaned versions"))


    def delete_button710(self, delete_purged):
        if delete_purged:
            self.log("about to remove content from 'purged_content' directory")
            removed = self.state.delete_purged_content()
            return gr.update(value=format_markdown(f"Removed: {removed}"))
        else:
            return gr.update(value=format_markdown(f"Removed: None"))

    def select_all_button710(self):
        return gr.update(value=True)

    def select_none_button710(self):
        return gr.update(value=False)

    def delete_button711(self, delete_source, delete_dropped, delete_thumbs):
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
        return gr.update(value=format_markdown(message))

    def select_all_button711(self):
        return gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True)

    def select_none_button711(self):
        return gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False)

    def delete_button712(self,
                         delete_kept,
                         delete_resized,
                         delete_resynth,
                         delete_inflated,
                         delete_upscaled,
                         delete_audio,
                         delete_video,
                         delete_clips):
        removed = []
        if delete_kept:
            removed.append(self.state.delete_path(self.state.scenes_path))
        if delete_resized:
            removed.append(self.state.delete_path(self.state.resize_path))
        if delete_resynth:
            removed.append(self.state.delete_path(self.state.resynthesis_path))
        if delete_inflated:
            removed.append(self.state.delete_path(self.state.inflation_path))
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
        return gr.update(value=format_markdown(message))

    def select_all_button712(self):
        return gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True)

    def select_none_button712(self):
        return gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False)

    def delete_button713(self, delete_all):
        removed = []
        if delete_all:
            removed.append(self.state.delete_purged_content())
            removed.append(self.state.delete_path(self.state.frames_path))
            removed.append(self.state.delete_path(self.state.dropped_scenes_path))
            removed.append(self.state.delete_path(self.state.thumbnail_path))
            removed.append(self.state.delete_path(self.state.scenes_path))
            removed.append(self.state.delete_path(self.state.resize_path))
            removed.append(self.state.delete_path(self.state.resynthesis_path))
            removed.append(self.state.delete_path(self.state.inflation_path))
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
        return gr.update(value=format_markdown(message))

    def restore_button714(self):
        global_options = self.config.ffmpeg_settings["global_options"]
        self.state.recover_project(global_options=global_options,
                                   remixer_settings=self.config.remixer_settings,
                                   log_fn=self.log)
        message = f"Project recovered"
        return gr.update(selected=self.TAB_CHOOSE_SCENES), \
            gr.update(value=format_markdown(message)), \
            *self.scene_chooser_details(self.state.current_scene)
