"""Video Remixer feature UI and event handlers"""
import os
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_files, create_directory, get_directories, split_filepath
from webui_utils.jot import Jot
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from video_remixer import VideoRemixerState

class VideoRemixer(TabBase):
    """Encapsulates UI elements and events for the Video Remixer Feature"""
    def __init__(self,
                 config : SimpleConfig,
                 engine : InterpolateEngine,
                 log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.new_project()

    def new_project(self):
        self.state = VideoRemixerState()
        self.state.set_project_ui_defaults(self.config.remixer_settings["def_project_fps"])

    def render_tab(self):
        """Render tab into UI"""
        def_project_fps = self.config.remixer_settings["def_project_fps"]
        max_project_fps = self.config.remixer_settings["max_project_fps"]
        minimum_crf = self.config.remixer_settings["minimum_crf"]
        maximum_crf = self.config.remixer_settings["maximum_crf"]
        default_crf = self.config.remixer_settings["default_crf"]
        max_thumb_size = self.config.remixer_settings["max_thumb_size"]

        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Video Remixer"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Restore & Remix Videos with Audio")
            with gr.Tabs() as tabs_video_remixer:

                ### NEW PROJECT
                with gr.Tab("Remix Home", id=0):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**Input a video to get started remixing**")
                            with gr.Row():
                                video_path = gr.Textbox(label="Video Path",
                                    placeholder="Path on this server to the video to be remixed")
                            with gr.Row():
                                message_box00 = gr.Textbox(
                        value="Next: Inspect Video and Count Frames (takes a minute or more)",
                                            show_label=False, visible=True, interactive=False)
                            gr.Markdown("*Progress can be tracked in the console*")
                            next_button00 = gr.Button(value="New Project > " +
                                SimpleIcons.SLOW_SYMBOL, variant="primary", elem_id="actionbutton")
                        with gr.Column():
                            gr.Markdown("**Open an existing Video Remixer project**")
                            with gr.Row():
                                project_load_path = gr.Textbox(label="Project Path",
                placeholder="Path on this server to the Video Remixer project directory or file")
                            with gr.Row():
                                message_box01 = gr.Textbox(value=None,
                                            show_label=False, visible=True, interactive=False)
                            gr.Markdown("*The Scene Chooser will be shown after loading project*")
                            next_button01 = gr.Button(value="Open Project >",
                                                    variant="primary")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_home.render()

                ### REMIX SETTINGS
                with gr.Tab("Remix Settings", id=1):
                    gr.Markdown("**Confirm Remixer Settings**")
                    with gr.Box():
                        video_info1 = gr.Markdown("Video Details")
                    with gr.Row():
                        project_path = gr.Textbox(label="Project Path",
                                            placeholder="Path on this server to store project data")
                    with gr.Row():
                        project_fps = gr.Slider(label="Remix Frame Rate", value=def_project_fps,
                                                minimum=1.0, maximum=max_project_fps, step=0.01)
                        deinterlace = gr.Checkbox(label="Deinterlace Soure Video")
                    with gr.Row():
                        split_type = gr.Radio(label="Split Type", value="Scene",
                                                    choices=["Scene", "Break", "Minute"])
                        scene_threshold = gr.Slider(value=0.6, minimum=0.0, maximum=1.0,
                                                    step=0.01, label="Scene Detection Threshold",
                                info="Value between 0.0 and 1.0 (higher = fewer scenes detected)")
                        break_duration = gr.Slider(value=2.0, minimum=0.0, maximum=30.0,
                                                    step=0.25, label="Break Minimum Duration",
                                                    info="Choose a duration in seconds")
                        break_ratio = gr.Slider(value=0.98, minimum=0.0, maximum=1.0, step=0.01,
                                                    label="Break Black Frame Ratio",
                                                    info="Choose a value between 0.0 and 1.0")
                    with gr.Row():
                        resize_w = gr.Number(label="Resize Width")
                        resize_h = gr.Number(label="Resize Height")
                        crop_w = gr.Number(label="Crop Width")
                        crop_h = gr.Number(label="Crop Height")

                    message_box1 = gr.Textbox(show_label=False, interactive=False,
                                            value="Next: Confirm Project Setup (no processing yet)")
                    with gr.Row():
                        back_button1 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button1 = gr.Button(value="Next >", variant="primary",
                                                elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_settings.render()

                ## SET UP PROJECT
                with gr.Tab("Set Up Project", id=2):
                    gr.Markdown("**Ready to Set Up Video Remixer Project**")
                    with gr.Box():
                        project_info2 = gr.Markdown("Project Details")
                    with gr.Row():
                        thumbnail_type = gr.Radio(choices=["GIF", "JPG"], value="JPG",
                                                  label="Thumbnail Type",
                                    info="Choose 'GIF' for whole-scene animations (slow to render)")
                    with gr.Row():
                        message_box2 = gr.Textbox(
        value="Next: Create Scenes, Thumbnails and Audio Clips (takes from minutes to hours)",
                                    show_label=False, visible=True, interactive=False)

                    gr.Markdown("*Progress can be tracked in the console*")
                    with gr.Row():
                        back_button2 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button2 = gr.Button(value="Set Up Project " + SimpleIcons.SLOW_SYMBOL,
                                                variant="primary", elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_setup.render()

                ## CHOOSE SCENES
                with gr.Tab("Choose Scenes", id=3):
                    with gr.Row():
                        with gr.Column():
                            with gr.Row():
                                scene_label = gr.Text(label="Scene Name", interactive=False)
                                scene_info = gr.Text(label="Scene Details", interactive=False)
                        with gr.Column():
                            with gr.Row():
                                scene_state = gr.Radio(label="Choose", value=None,
                                                    choices=["Keep", "Drop"])
                                scene_index = gr.Number(label="Scene Index", precision=0)
                    with gr.Row():
                        with gr.Column():
                            scene_image = gr.Image(type="filepath", interactive=False).style(
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
                            with gr.Accordion(label="Danger Zone", open=False):
                                with gr.Row():
                                    keep_all_button = gr.Button(value="Keep All Scenes",
                                                                variant="stop")
                                    drop_all_button = gr.Button(value="Drop All Scenes",
                                                                variant="stop")
                    with gr.Row():
                        back_button3 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button3 = gr.Button(value="Done Choosing Scenes", variant="primary",
                                                elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_choose.render()

                ## COMPILE SCENES
                with gr.Tab("Compile Scenes", id=4):
                    with gr.Box():
                        project_info4 = gr.Markdown("Chosen Scene Details")
                    with gr.Row():
                        message_box4 = gr.Textbox(show_label=False, interactive=False,
                                        value="Next: Compile 'Keep' and 'Drop' scenes")
                    with gr.Row():
                        back_button4 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button4 = gr.Button(value="Compile Scenes", variant="primary",
                                                elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_compile.render()

                ## PROCESSING OPTIONS
                with gr.Tab("Procesing Options", id=5):
                    gr.Markdown("**Ready to Process Content for Remix Video**")
                    with gr.Row():
                        resize = gr.Checkbox(label="Fix Aspect Ratio", value=True)
                        with gr.Box():
                            gr.Markdown("Frames are resized then cropped according to project settings")
                    with gr.Row():
                        resynthesize = gr.Checkbox(label="Resynthesize Frames",value=True)
                        with gr.Box():
                            gr.Markdown("Frames are recreated by AI interpolation of neighboring frames\r\n- Scene outermost frames are lost during resynthesis\r\n- Audio clips are adjusted to compensate for lost frames")
                    with gr.Row():
                        inflate = gr.Checkbox(label="Inflate New Frames",value=True)
                        with gr.Box():
                            gr.Markdown("New frames are inserted by AI interpolation for smooth motion\r\n- Project FPS is doubled when inflation is used\r\n- Audio clips do not need adjusting for inflation")
                    with gr.Row():
                        upscale = gr.Checkbox(label="Upscale Frames", value=True)
                        upscale_option = gr.Radio(label="Upscale By", value="2X",
                                                  choices=["2X", "4X"])
                        with gr.Box():
                            gr.Markdown("Frames are cleansed and enlarged using AI - Real-ESRGAN 4x+\r\n")
                    message_box5 = gr.Textbox(
                        value="Next: Perform all Processing Steps (takes from hours to days)",
                                              show_label=False, interactive=False)
                    gr.Markdown(SimpleIcons.WARNING + " Make backups if redoing this step. Processed content may be purged based on the above settings.\r\n*Progress can be tracked in the console*")
                    with gr.Row():
                        back_button5 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button5 = gr.Button(value="Process Remix " +
                                    SimpleIcons.SLOW_SYMBOL, variant="primary",
                                    elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_processing.render()

                ## REMIX VIDEOS
                with gr.Tab("Save Remix", id=6):
                    gr.Markdown("**Ready to Finalize Scenes and Save Remixed Video**")
                    with gr.Row():
                        summary_info6 = gr.Textbox(label="Processed Content", lines=6,
                                                interactive=False)
                    with gr.Tabs():
                        with gr.Tab(label="Create MP4 Remix"):
                            quality_slider = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                                step=1, value=default_crf, label="Video Quality",
                                info="Lower values mean higher video quality")
                            output_filepath = gr.Textbox(label="Output Filepath", max_lines=1,
                                    info="Enter a path and filename for the remixed video")
                            with gr.Row():
                                message_box60 = gr.Textbox(value=None, show_label=False,
                                                          interactive=False)
                            gr.Markdown("*Progress can be tracked in the console*")
                            with gr.Row():
                                back_button60 = gr.Button(value="< Back", variant="secondary").\
                                    style(full_width=False)
                                next_button60 = gr.Button(
                                    value="Save Remix " + SimpleIcons.SLOW_SYMBOL,
                                    variant="primary", elem_id="highlightbutton")
                        with gr.Tab(label="Create Custom Remix"):
                            custom_video_options = gr.Textbox(
                                label="Custom FFmpeg Video Output Options",
                        info="Passed to FFmpeg as output video settings when converting PNG frames")
                            custom_audio_options = gr.Textbox(
                                label="Custom FFmpeg Audio Output Options",
                        info="Passed to FFmpeg as output audio settings when combining with video")
                            output_filepath_custom = gr.Textbox(label="Output Filepath", max_lines=1,
                                    info="Enter a path and filename for the remixed video")
                            with gr.Row():
                                message_box61 = gr.Textbox(value=None, show_label=False,
                                                          interactive=False)
                            gr.Markdown("*Progress can be tracked in the console*")
                            with gr.Row():
                                back_button61 = gr.Button(value="< Back", variant="secondary").\
                                    style(full_width=False)
                                next_button61 = gr.Button(
                                    value="Save Custom Remix " + SimpleIcons.SLOW_SYMBOL,
                                    variant="primary", elem_id="highlightbutton")

                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_save.render()

        next_button00.click(self.next_button00,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box00, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h])

        next_button01.click(self.next_button01,
                           inputs=project_load_path,
                           outputs=[tabs_video_remixer, message_box01, video_info1, project_path,
                                project_fps, deinterlace, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                project_info2, thumbnail_type, scene_index, scene_label, scene_image,
                                scene_state, scene_info, project_info4, resize,
                                resynthesize, inflate, upscale, upscale_option, summary_info6,
                                output_filepath])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold,
                    break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h, deinterlace],
                           outputs=[tabs_video_remixer, message_box1, project_info2, message_box2])

        back_button1.click(self.back_button1, outputs=tabs_video_remixer)

        next_button2.click(self.next_button2, inputs=thumbnail_type,
                           outputs=[tabs_video_remixer, message_box2, scene_index, scene_label,
                                    scene_image, scene_state, scene_info])

        back_button2.click(self.back_button2, outputs=tabs_video_remixer)

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

        keep_all_button.click(self.keep_all_scenes, show_progress=True,
                            inputs=[scene_index, scene_label],
                            outputs=[scene_index, scene_label, scene_image, scene_state,
                                     scene_info])

        drop_all_button.click(self.drop_all_scenes, show_progress=True,
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

        next_button3.click(self.next_button3,
                           outputs=[tabs_video_remixer, project_info4])

        back_button3.click(self.back_button3, outputs=tabs_video_remixer)

        next_button4.click(self.next_button4,
                           outputs=[tabs_video_remixer, message_box4, message_box5])

        back_button4.click(self.back_button4, outputs=tabs_video_remixer)

        next_button5.click(self.next_button5,
                    inputs=[resynthesize, inflate, resize, upscale, upscale_option],
                    outputs=[tabs_video_remixer, message_box5, summary_info6, output_filepath])

        back_button5.click(self.back_button5, outputs=tabs_video_remixer)

        next_button60.click(self.next_button60, inputs=[output_filepath, quality_slider],
                           outputs=message_box60)

        back_button60.click(self.back_button6, outputs=tabs_video_remixer)

        next_button61.click(self.next_button61,
                        inputs=[custom_video_options, custom_audio_options, output_filepath_custom],
                        outputs=message_box61)

        back_button61.click(self.back_button6, outputs=tabs_video_remixer)

    def empty_args(self, num):
        return [None for _ in range(num)]

    ### REMIX HOME EVENT HANDLERS

    # User has clicked New Project > from Remix Home
    def next_button00(self, video_path):
        if not video_path:
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value="Enter a path to a video on this server to get started"), \
                   *self.empty_args(6)

        if not os.path.exists(video_path):
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=f"File {video_path} was not found"), \
                   *self.empty_args(6)

        self.new_project()
        try:
            self.state.ingest_video(video_path)
            self.state.video_info1 = self.state.ingested_video_report()
        except ValueError as error:
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=error), \
                   *self.empty_args(6)

        # don't save yet, user may change project path next
        self.state.save_progress("settings", save_project=False)

        return gr.update(selected=1), \
            gr.update(visible=True), \
            gr.update(value=self.state.video_info1), \
            self.state.project_path, \
            self.state.resize_w, \
            self.state.resize_h, \
            self.state.crop_w, \
            self.state.crop_h

    # User has clicked Open Project > from Remix Home
    def next_button01(self, project_path):
        if not project_path:
            return gr.update(selected=0), \
                   gr.update(visible=True,
        value="Enter a path to a Video Remixer project directory on this server to get started"), \
                   *self.empty_args(26)

        if not os.path.exists(project_path):
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=f"Directory {project_path} was not found"), \
                   *self.empty_args(26)

        try:
            project_file = self.state.determine_project_filepath(project_path)
        except ValueError as error:
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=error), \
                   *self.empty_args(26)

        try:
            self.state = VideoRemixerState.load(project_file)
        except ValueError as error:
            self.log(f"error opening project: {error}")
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=error), \
                   *self.empty_args(26)

        entered_path, _, _ = split_filepath(project_file)
        if self.state.project_path != entered_path:
            return gr.update(selected=0), \
                   gr.update(visible=True,
        value=f"Portability will be added later, for now open from: '{self.state.project_path}'"), \
                   *self.empty_args(26)

        return_to_tab = self.state.get_progress_tab()
        scene_details = self.scene_chooser_details(self.state.tryattr("current_scene"))

        return gr.update(selected=return_to_tab), \
            gr.update(visible=True), \
            self.state.tryattr("video_info1"), \
            self.state.tryattr("project_path"), \
            self.state.tryattr("project_fps", self.config.remixer_settings["def_project_fps"]), \
            self.state.tryattr("deinterlace", self.state.UI_SAFETY_DEFAULTS["deinterlace"]), \
            self.state.tryattr("split_type", self.state.UI_SAFETY_DEFAULTS["split_type"]), \
            self.state.tryattr("scene_threshold", self.state.UI_SAFETY_DEFAULTS["scene_threshold"]), \
            self.state.tryattr("break_duration", self.state.UI_SAFETY_DEFAULTS["break_duration"]), \
            self.state.tryattr("break_ratio", self.state.UI_SAFETY_DEFAULTS["break_ratio"]), \
            self.state.tryattr("resize_w"), \
            self.state.tryattr("resize_h"), \
            self.state.tryattr("crop_w"), \
            self.state.tryattr("crop_h"), \
            self.state.tryattr("project_info2"), \
            self.state.tryattr("thumbnail_type", self.state.UI_SAFETY_DEFAULTS["thumbnail_type"]), \
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
    def next_button1(self, project_path, project_fps, split_type, scene_threshold, break_duration, \
                     break_ratio, resize_w, resize_h, crop_w, crop_h, deinterlace):
        self.state.project_path = project_path

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
        self.state.deinterlace = deinterlace
        self.state.project_info2 = self.state.project_settings_report()

        # this is the first time project progress advances
        # user will expect to return to the setup tab on reopening
        self.log(f"saving new project at {self.state.project_filepath()}")
        self.state.save_progress("setup")

        return gr.update(selected=2), \
               gr.update(visible=True), \
               self.state.project_info2, \
              "Next: Create Scenes, Thumbnails and Audio Clips (takes from minutes to hours)"

    def back_button1(self):
        return gr.update(selected=0)

    ### REMIX SETUP EVENT HANDLERS

    # User has clicked Set Up Project from Set Up Project
    def next_button2(self, thumbnail_type):
        global_options = self.config.ffmpeg_settings["global_options"]

        self.state.thumbnail_type = thumbnail_type
        self.log("saving after setting thumbnail type")
        self.state.save()

        try:
            self.log(f"copying video from {self.state.source_video} to project path")
            self.state.save_original_video(prevent_overwrite=True)
        except ValueError as error:
            # ignore, don't copy the file a second time if the user is restarting here
            self.log(f"ignoring: {error}")

        self.log("saving project after ensuring video is in project path")
        self.state.save()

        # user may be redoing project set up
        # settings changes could affect already-processed content
        self.log("resetting project on rendering for project settings")
        self.state.reset_at_project_settings()

        # split video into raw PNG frames
        self.log("splitting source video into PNG frames")
        global_options = self.config.ffmpeg_settings["global_options"]
        ffcmd = self.state.render_source_frames(global_options=global_options)
        self.log(f"FFmpeg command: {ffcmd}")

        self.log("saving project after converting video to PNG frames")
        self.state.save()

        self.state.scenes_path = os.path.join(self.state.project_path, "SCENES")
        self.state.dropped_scenes_path = os.path.join(self.state.project_path, "DROPPED_SCENES")
        self.log(f"creating scenes directory {self.state.scenes_path}")
        create_directory(self.state.scenes_path)
        self.log(f"creating dropped scenes directory {self.state.dropped_scenes_path}")
        create_directory(self.state.dropped_scenes_path)

        self.log("saving project after establishing scene paths")
        self.state.save()

        self.log(f"about to split scenes by {self.state.split_type}")
        error = self.state.split_scenes(self.log)
        if error:
            return gr.update(selected=2), \
                   gr.update(visible=True,
                             value=f"There was an error splitting the source video: {error}"), \
                   *self.empty_args(6)
        self.log("saving project after splitting into scenes")
        self.state.save()

        self.state.scene_names = sorted(get_directories(self.state.scenes_path))
        self.state.drop_all_scenes()
        self.state.current_scene = 0
        self.log("saving project after establishing scene names")
        self.state.save()

        # TODO put in a check for a bad splits - zero scenes, missing scenes

        self.log(f"about to create thumbnails of type {self.state.thumbnail_type}")
        try:
            self.state.create_thumbnails(self.log, global_options, self.config.remixer_settings)
        except ValueError as error:
            return gr.update(selected=2), \
                   gr.update(visible=True,
                    value=f"There was an error creating thumbnails from source video: {error}"), \
                   *self.empty_args(6)

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

        return gr.update(selected=3), \
               gr.update(visible=True), \
               *self.scene_chooser_details(self.state.current_scene)

    def back_button2(self):
        return gr.update(selected=1)

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

    def keep_all_scenes(self, scene_index, scene_label):
        self.state.keep_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_all_scenes(self, scene_index, scene_label):
        self.state.drop_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def first_scene(self, scene_index, scene_label):
        self.state.current_scene = 0
        return self.scene_chooser_details(self.state.current_scene)

    def last_scene(self, scene_index, scene_label):
        self.state.current_scene = len(self.state.scene_names) - 1
        return self.scene_chooser_details(self.state.current_scene)

    # given scene name such as [042-420] compute details to display in Scene Chooser
    def scene_chooser_details(self, scene_index):
        if not self.state.thumbnails:
            self.log(f"thumbnails don't exist yet in scene_chooser_details()")
            return self.empty_args(6)
        try:
            scene_name, thumbnail_path, scene_state, scene_info = \
                self.state.scene_chooser_details(scene_index)
            return scene_index, scene_name, thumbnail_path, scene_state, scene_info
        except ValueError as error:
            self.log(error)
            return self.empty_args(6)

    # User has clicked Done Choosing Scenes from Scene Chooser
    def next_button3(self):
        self.state.project_info4 = self.state.chosen_scenes_report()

        # user will expect to return to the compilation tab on reopening
        self.log("saving project after displaying scene choices")
        self.state.save_progress("compile")

        return gr.update(selected=4), self.state.project_info4

    def back_button3(self):
        return gr.update(selected=2)

    ### COMPILE SCENES EVENT HANDLERS

    # User has clicked Compile Scenes from Compile Scenes
    def next_button4(self):
        self.log("moving previously dropped scenes back to scenes directory")
        self.state.uncompile_scenes()

        self.log("moving dropped scenes to dropped scenes directory")
        self.state.compile_scenes()

        # user will expect to return to the processing tab on reopening
        self.log("saving project after compiling scenes")
        self.state.save_progress("process")

        return gr.update(selected=5),  \
               gr.update(visible=True), \
               "Next: Perform all Processing Steps (takes from hours to days)"

    def back_button4(self):
        return gr.update(selected=3)

    ### PROCESSING OPTIONS EVENT HANDLERS

    # User has clicked Process Remix from Processing Options
    def next_button5(self, resynthesize, inflate, resize, upscale, upscale_option):
        self.state.resynthesize = resynthesize
        self.state.inflate = inflate
        self.state.resize = resize
        self.state.upscale = upscale
        upscale_option_changed = False
        if self.state.upscale_option != None and self.state.upscale_option != upscale_option:
            upscale_option_changed = True
        self.state.upscale_option = upscale_option
        self.log("saving project after storing processing choices")
        self.state.save()

        jot = Jot()
        kept_scenes = self.state.kept_scenes()
        if kept_scenes:
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
                jot.down(f"Using original source content in {self.state.frames_path}")

            if self.state.resize:
                if self.state.processed_content_present(self.state.RESIZE_STEP):
                    jot.down(f"Using processed resized scenes in {self.state.resize_path}")
                else:
                    self.log("about to resize scenes")
                    self.state.resize_scenes(self.log,
                                             kept_scenes,
                                             self.config.remixer_settings)
                    self.log("saving project after resizing frames")
                    self.state.save()
                    jot.down(f"Resized scenes created in {self.state.resize_path}")

            if self.state.resynthesize:
                if self.state.processed_content_present(self.state.RESYNTH_STEP):
                    jot.down(f"Using processed resynthesized scenes in {self.state.resynthesis_path}")
                else:
                    self.state.resynthesize_scenes(self.log,
                                                kept_scenes,
                                                self.engine,
                                                self.config.engine_settings)
                    self.log("saving project after resynthesizing frames")
                    self.state.save()
                    jot.down(f"Resynthesized scenes created in {self.state.resynthesis_path}")

            if self.state.inflate:
                if self.state.processed_content_present(self.state.INFLATE_STEP):
                    jot.down(f"Using processed inflated scenes in {self.state.inflation_path}")
                else:
                    self.state.inflate_scenes(self.log,
                                                kept_scenes,
                                                self.engine,
                                                self.config.engine_settings)
                    self.log("saving project after inflating frames")
                    self.state.save()
                    jot.down(f"Inflated scenes created in {self.state.inflation_path}")

            if self.state.upscale:
                if self.state.processed_content_present(self.state.UPSCALE_STEP):
                    jot.down(f"Using processed upscaled scenes in {self.state.upscale_path}")
                else:
                    self.state.upscale_scenes(self.log,
                                            kept_scenes,
                                            self.config.realesrgan_settings,
                                            self.config.remixer_settings)
                    self.log("saving project after upscaling frames")
                    self.state.save()
                    jot.down(f"Upscaled scenes created in {self.state.upscale_path}")

            self.state.summary_info6 = jot
            self.state.output_filepath = self.state.default_remix_filepath()
            self.state.save()

            # user will expect to return to the save remix tab on reopening
            self.log("saving project after completing processing steps")
            self.state.save_progress("save")

            return gr.update(selected=6), \
                   gr.update(visible=True), \
                   jot, \
                   self.state.output_filepath
        else:
            return gr.update(selected=5), \
                   gr.update(
                value="At least one scene must be set to 'Keep' before processing can proceed"), \
                   None, None

    def back_button5(self):
        return gr.update(selected=4)

    ### SAVE REMIX EVENT HANDLERS

    # User has clicked Save Remix from Save Remix
    def next_button60(self, output_filepath, quality):
        global_options = self.config.ffmpeg_settings["global_options"]

        if not output_filepath:
            return gr.update(value="Enter a path for the remixed video to proceed", visible=True)

        self.state.output_filepath = output_filepath
        self.state.output_quality = quality
        self.log("saving after storing remix output choices")
        self.state.save()

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return gr.update(value="No kept scenes were found", visible=True)

        self.log("about to check and drop empty scenes")
        self.state.drop_empty_processed_scenes(kept_scenes)
        self.log("saving after dropping empty scenes")
        self.state.save()

        # get this again in case scenes have been auto-dropped
        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return gr.update(value="No kept scenes were found", visible=True)

        if self.state.video_details["has_audio"] and not self.state.processed_content_present("audio"):
            self.log("about to create audio clips")
            self.state.create_audio_clips(self.log, global_options)
            self.log("saving project after creating audio clips")
            self.state.save()

        # always recreate video and scene clips
        self.state.purge_remix_content(purge_from="video_clips")

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

        return gr.update(value=f"Remixed video {output_filepath} is complete.",
                         visible=True)

    # User has clicked Save Custom Remix from Save Remix
    def next_button61(self, custom_video_options, custom_audio_options, output_filepath):
        global_options = self.config.ffmpeg_settings["global_options"]

        if not output_filepath:
            return gr.update(value="Enter a path for the remixed video to proceed", visible=True)

        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return gr.update(value="No kept scenes were found", visible=True)

        self.log("about to check and drop empty scenes")
        self.state.drop_empty_processed_scenes(kept_scenes)
        self.log("saving after dropping empty scenes")
        self.state.save()

        # get this again in case scenes have been auto-dropped
        kept_scenes = self.state.kept_scenes()
        if not kept_scenes:
            return gr.update(value="No kept scenes were found", visible=True)

        if self.state.video_details["has_audio"] and not self.state.processed_content_present("audio"):
            self.log("about to create audio clips")
            self.state.create_audio_clips(self.log, global_options)
            self.log("saving project after creating audio clips")
            self.state.save()

        # grab file type of output file for use in creating scene videos and remix clips
        _, _, output_ext = split_filepath(output_filepath)
        output_ext = output_ext[1:]

        # always recreate video and scene clips
        self.state.purge_remix_content(purge_from="video_clips")

        self.log(f"about to create video clips")
        self.state.create_custom_video_clips(self.log, kept_scenes, global_options,
                                             custom_video_options=custom_video_options,
                                             custom_ext=output_ext)
        self.log("saving project after creating video clips")
        self.state.save()

        self.log("about to create scene clips")
        self.state.create_custom_scene_clips(kept_scenes, global_options,
                                             custom_audio_options=custom_audio_options,
                                             custom_ext=output_ext)
        self.log("saving project after creating scene clips")
        self.state.save()

        if not self.state.clips:
            return gr.update(value="No processed video clips were found", visible=True)

        self.log("about to create remix viedeo")
        ffcmd = self.state.create_remix_video(global_options, output_filepath)
        self.log(f"FFmpeg command: {ffcmd}")
        self.log("saving project after creating remix video")
        self.state.save()

        return gr.update(value=f"Remixed video {output_filepath} is complete.",
                         visible=True)

    def back_button6(self):
        return gr.update(selected=5)
