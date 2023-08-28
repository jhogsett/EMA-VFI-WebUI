"""Video Remixer feature UI and event handlers"""
import os
import shutil
import math
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_files, create_directory, get_directories, split_filepath
from webui_utils.video_utils import details_from_group_name
from webui_utils.jot import Jot
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase
from video_remixer import VideoRemixerState
from slice_video import SliceVideo

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
        def_min_frames = self.config.remixer_settings["min_frames_per_scene"]
        marked_ffmpeg_video = self.config.remixer_settings["marked_ffmpeg_video"]
        marked_ffmpeg_audio = self.config.remixer_settings["marked_ffmpeg_audio"]
        with gr.Tab(SimpleIcons.SPOTLIGHT_SYMBOL + "Video Remixer"):
            gr.Markdown(
                SimpleIcons.MOVIE + "Restore & Remix Videos with Audio")
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
                        min_frames_per_scene = gr.Number(label="Minimum Frames Per Scene",
                                    precision=0, value=def_min_frames,
                        info="consolidates very small scenes info the next (0 to disable)")
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
                with gr.Tab("Processing Options", id=5):
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
                                                  choices=["1X", "2X", "4X"])
                        with gr.Box():
                            gr.Markdown("Frames are cleansed and enlarged using AI - Real-ESRGAN 4x+\r\n")
                    message_box5 = gr.Textbox(
                        value="Next: Perform all Processing Steps (takes from hours to days)",
                                              show_label=False, interactive=False)
                    with gr.Row():
                        back_button5 = gr.Button(value="< Back", variant="secondary").\
                            style(full_width=False)
                        next_button5 = gr.Button(value="Process Remix " +
                                    SimpleIcons.SLOW_SYMBOL, variant="primary",
                                    elem_id="actionbutton")
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_processing.render()

                ## SAVE REMIX
                with gr.Tab("Save Remix", id=6):
                    gr.Markdown("**Ready to Finalize Scenes and Save Remixed Video**")
                    with gr.Row():
                        summary_info6 = gr.Textbox(label="Processed Content", lines=6,
                                                interactive=False)

                    with gr.Tabs():

                        ### CREATE MP4 REMIX
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

                        ### CREATE CUSTOM REMIX
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

                        ### CREATE MARKED REMIX
                        with gr.Tab(label="Create Marked Remix"):
                            marked_video_options = gr.Textbox(value=marked_ffmpeg_video,
                                label="Marked FFmpeg Video Output Options",
                        info="Passed to FFmpeg as output video settings when converting PNG frames")
                            marked_audio_options = gr.Textbox(value=marked_ffmpeg_audio,
                                label="Marked FFmpeg Audio Output Options",
                        info="Passed to FFmpeg as output audio settings when combining with video")
                            output_filepath_marked = gr.Textbox(label="Output Filepath", max_lines=1,
                                    info="Enter a path and filename for the remixed video")
                            with gr.Row():
                                message_box62 = gr.Textbox(value=None, show_label=False,
                                                          interactive=False)
                            gr.Markdown("*Progress can be tracked in the console*")
                            with gr.Row():
                                back_button62 = gr.Button(value="< Back", variant="secondary").\
                                    style(full_width=False)
                                next_button62 = gr.Button(
                                    value="Save Marked Remix " + SimpleIcons.SLOW_SYMBOL,
                                    variant="primary", elem_id="highlightbutton")

                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_remixer_save.render()

                ## Remix Extra
                with gr.Tab("Remix Extra", id=7):
                    with gr.Tab(label="Utilities"):
                        with gr.Tabs():
                            with gr.Tab("Drop Processed Scene"):
                                gr.Markdown("**_Drop a scene after processing has been already been done_**")
                                scene_id_700 = gr.Number(value=-1, label="Scene Index")
                                with gr.Row():
                                    message_box700 = gr.Textbox(show_label=False, interactive=False)
                                drop_button700 = gr.Button("Drop Scene", variant="stop").style(full_width=False)

                            with gr.Tab("Choose Scene Range"):
                                gr.Markdown("**_Keep or Drop a range of scenes_**")
                                with gr.Row():
                                    first_scene_id_701 = gr.Number(value=-1,
                                                                    label="Starting Scene Index")
                                    last_scene_id_701 = gr.Number(value=-1,
                                                                    label="Ending Scene Index")
                                with gr.Row():
                                    scene_state_701 = gr.Radio(label="Scenes Choice", value=None,
                                                                    choices=["Keep", "Drop"])
                                with gr.Row():
                                    message_box701 = gr.Textbox(show_label=False, interactive=False)
                                choose_button701 = gr.Button("Choose Scene Range", variant="stop").style(full_width=False)

                            with gr.Tab("Split Scene"):
                                gr.Markdown("**_Split a Scene in two_**")
                                scene_id_702 = gr.Number(value=-1, label="Scene Index")
                                with gr.Row():
                                    message_box702 = gr.Textbox(show_label=False, interactive=False)
                                split_button702 = gr.Button("Split Scene", variant="stop").style(full_width=False)

                    with gr.Tab(label="Reduce Footprint"):
                        with gr.Tabs():
                            with gr.Tab(label="Remove Soft-Deleted Content"):
                                gr.Markdown("**_Delete content set aside when remix processing selections are changed_**")
                                with gr.Row():
                                    delete_purged_710 = gr.Checkbox(label="Permanently Delete Purged Content")
                                    with gr.Box():
                                        gr.Markdown("Delete the contents of the 'purged_content' project directory.")
                                with gr.Row():
                                    message_box710 = gr.Textbox(show_label=False)
                                gr.Markdown("*Progress can be tracked in the console*")
                                with gr.Row():
                                    delete_button710 = gr.Button(value="Delete Purged Content " + SimpleIcons.SLOW_SYMBOL, variant="stop")
                                    select_all_button710 = gr.Button(value="Select All").style(full_width=False)
                                    select_none_button710 = gr.Button(value="Select None").style(full_width=False)

                            with gr.Tab(label="Remove Scene Chooser Content"):
                                gr.Markdown("**_Delete source PNG frame files, thumbnails and dropped scenes_**")
                                with gr.Row():
                                    delete_source_711 = gr.Checkbox(label="Remove Source Video Frames")
                                    with gr.Box():
                                        gr.Markdown("Delete source video PNG frame files used to split content into scenes.")
                                with gr.Row():
                                    delete_dropped_711 = gr.Checkbox(label="Remove Dropped Scenes")
                                    with gr.Box():
                                        gr.Markdown("Delete Dropped Scene files used when compiling scenes after making scene choices.")
                                with gr.Row():
                                    delete_thumbs_711 = gr.Checkbox(label="Remove Thumbnails")
                                    with gr.Box():
                                        gr.Markdown("Delete Thumbnails used to display scenes in Scene Chooser.")
                                with gr.Row():
                                    message_box711 = gr.Textbox(show_label=False)
                                gr.Markdown("*Progress can be tracked in the console*")
                                with gr.Row():
                                    delete_button711 = gr.Button(value="Delete Selected Content " + SimpleIcons.SLOW_SYMBOL, variant="stop")
                                    select_all_button711 = gr.Button(value="Select All").style(full_width=False)
                                    select_none_button711 = gr.Button(value="Select None").style(full_width=False)

                            with gr.Tab(label="Remove Remix Video Source Content"):
                                gr.Markdown("**_Clear space after final Remix Videos have been saved_**")
                                with gr.Row():
                                    delete_kept_712 = gr.Checkbox(label="Remove Kept Scenes")
                                    with gr.Box():
                                        gr.Markdown("Delete Kept Scene files used when compiling scenes after making scene choices.")
                                with gr.Row():
                                    delete_resized_712 = gr.Checkbox(label="Remove Resized Frames")
                                    with gr.Box():
                                        gr.Markdown("Delete Resized PNG frame files used as inputs for processing and creating remix video clips.")
                                with gr.Row():
                                    delete_resynth_712 = gr.Checkbox(label="Remove Resynthesized Frames")
                                    with gr.Box():
                                        gr.Markdown("Delete Resynthesized PNG frame files used as inputs for processing and creating remix video clips.")
                                with gr.Row():
                                    delete_inflated_712 = gr.Checkbox(label="Remove Inflated Frames")
                                    with gr.Box():
                                        gr.Markdown("Delete Inflated PNG frame files used as inputs for processing and creating remix video clips.")
                                with gr.Row():
                                    delete_upscaled_712 = gr.Checkbox(label="Remove Upscaled Frames")
                                    with gr.Box():
                                        gr.Markdown("Delete Upscaled PNG frame files used as inputs for processing and creating remix video clips.")
                                with gr.Row():
                                    delete_audio_712 = gr.Checkbox(label="Delete Audio Clips")
                                    with gr.Box():
                                        gr.Markdown("Delete Audio WAV/MP3 files used as inputs for creating remix video clips.")
                                with gr.Row():
                                    delete_video_712 = gr.Checkbox(label="Delete Video Clips")
                                    with gr.Box():
                                        gr.Markdown("Delete Video MP4 files used as inputs for creating remix video clips.")
                                with gr.Row():
                                    delete_clips_712 = gr.Checkbox(label="Delete Remix Video Clips")
                                    with gr.Box():
                                        gr.Markdown("Delete Video+Audio MP4 files used as inputs to concatentate into the final Remix Video.")
                                with gr.Row():
                                    message_box712 = gr.Textbox(show_label=False)
                                gr.Markdown("*Progress can be tracked in the console*")
                                with gr.Row():
                                    delete_button712 = gr.Button(value="Delete Selected Content " + SimpleIcons.SLOW_SYMBOL, variant="stop")
                                    select_all_button712 = gr.Button(value="Select All").style(full_width=False)
                                    select_none_button712 = gr.Button(value="Select None").style(full_width=False)

                            with gr.Tab(label="Remove All Processed Content"):
                                gr.Markdown("**_Delete all processed project content (except videos)_**")
                                with gr.Row():
                                    delete_all_713 = gr.Checkbox(label="Permanently Delete Processed Content")
                                    with gr.Box():
                                        gr.Markdown("Deletes all created project content. **Does not delete original and remixed videos.**")
                                with gr.Row():
                                    message_box713 = gr.Textbox(show_label=False)
                                gr.Markdown("*Progress can be tracked in the console*")
                                with gr.Row():
                                    delete_button713 = gr.Button(value="Delete Processed Content " + SimpleIcons.SLOW_SYMBOL, variant="stop")

                    # with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    #     WebuiTips.video_remixer_save.render()

        next_button00.click(self.next_button00,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box00, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h])

        next_button01.click(self.next_button01,
                           inputs=project_load_path,
                           outputs=[tabs_video_remixer, message_box01, video_info1, project_path,
                                project_fps, deinterlace, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                project_info2, thumbnail_type, min_frames_per_scene,
                                scene_index, scene_label, scene_image, scene_state, scene_info,
                                project_info4, resize, resynthesize, inflate, upscale,
                                upscale_option, summary_info6, output_filepath])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                deinterlace],
                           outputs=[tabs_video_remixer, message_box1, project_info2, message_box2,
                                project_load_path])

        back_button1.click(self.back_button1, outputs=tabs_video_remixer)

        next_button2.click(self.next_button2, inputs=[thumbnail_type, min_frames_per_scene],
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
                    outputs=[tabs_video_remixer, message_box5, summary_info6, output_filepath,
                             output_filepath_custom, output_filepath_marked, message_box60,
                             message_box61, message_box62])

        back_button5.click(self.back_button5, outputs=tabs_video_remixer)

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

        drop_button700.click(self.drop_button700, inputs=scene_id_700, outputs=message_box700)

        choose_button701.click(self.choose_button701,
                               inputs=[first_scene_id_701, last_scene_id_701, scene_state_701],
                               outputs=message_box701)

        split_button702.click(self.split_button702, inputs=scene_id_702,
                              outputs=[tabs_video_remixer, message_box702, scene_index, scene_label,
                                       scene_image, scene_state, scene_info])

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
                   *self.empty_args(28)

        if not os.path.exists(project_path):
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=f"Directory {project_path} was not found"), \
                   *self.empty_args(28)

        try:
            project_file = self.state.determine_project_filepath(project_path)
        except ValueError as error:
            return gr.update(selected=0), \
                   gr.update(visible=True,
                             value=error), \
                   *self.empty_args(28)

        try:
            self.state = VideoRemixerState.load(project_file)
        except ValueError as error:
            self.log(f"error opening project: {error}")
            error_lines = len(str(error).splitlines())
            return gr.update(selected=0), \
                   gr.update(visible=True, value=error, lines=error_lines), \
                   *self.empty_args(28)

        if self.state.project_ported(project_file):
            try:
                self.state = VideoRemixerState.load_ported(self.state.project_path, project_file)
            except ValueError as error:
                self.log(f"error opening ported project at {project_file}: {error}")
                error_lines = len(str(error).splitlines())
                return gr.update(selected=0), \
                    gr.update(visible=True, value=error, lines=error_lines), \
                    *self.empty_args(28)

        messages = self.state.post_load_integrity_check()
        messages_lines = len(messages.splitlines())

        return_to_tab = self.state.get_progress_tab()
        scene_details = self.scene_chooser_details(self.state.tryattr("current_scene"))

        return gr.update(selected=return_to_tab), \
            gr.update(value=messages, visible=True, lines=messages_lines), \
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
            self.state.tryattr("min_frames_per_scene", self.state.UI_SAFETY_DEFAULTS["min_frames_per_scene"]), \
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
              "Next: Create Scenes, Thumbnails and Audio Clips (takes from minutes to hours)", \
              project_path

    def back_button1(self):
        return gr.update(selected=0)

    ### REMIX SETUP EVENT HANDLERS

    # User has clicked Set Up Project from Set Up Project
    def next_button2(self, thumbnail_type, min_frames_per_scene):
        global_options = self.config.ffmpeg_settings["global_options"]

        self.state.thumbnail_type = thumbnail_type
        self.state.min_frames_per_scene = min_frames_per_scene
        self.log("saving after setting thumbnail type and min frames per scene")
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

        self.log(f"about to split scenes by {self.state.split_type}")
        error = self.state.split_scenes(self.log)
        if error:
            return gr.update(selected=2), \
                   gr.update(visible=True,
                             value=f"There was an error splitting the source video: {error}"), \
                   *self.empty_args(6)
        self.log("saving project after splitting into scenes")
        self.state.save()

        if self.state.min_frames_per_scene > 0:
            self.log(f"about to consolidate scenes with too few frames")
            self.state.consolidate_scenes(self.log)
            self.log("saving project after consolidating scenes")
            self.state.save()

        self.state.scene_names = sorted(get_directories(self.state.scenes_path))
        self.state.drop_all_scenes()
        self.state.current_scene = 0
        self.log("saving project after establishing scene names")
        self.state.save()

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

        # scene choice changes are what invalidate previously made audio clips,
        # so clear them now along with dependent remix content
        self.log("purging now-stale remix content")
        self.state.clean_remix_content(purge_from="audio_clips")

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
        self.state.setup_processing_paths()
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
                jot.down(f"Using original source content in {self.state.scenes_path}")

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

            self.state.summary_info6 = jot.grab()
            self.state.output_filepath = self.state.default_remix_filepath()
            output_filepath_custom = self.state.default_remix_filepath("CUSTOM")
            output_filepath_marked = self.state.default_remix_filepath("MARKED")
            self.state.save()

            # user will expect to return to the save remix tab on reopening
            self.log("saving project after completing processing steps")
            self.state.save_progress("save")

            return gr.update(selected=6), \
                   gr.update(visible=True), \
                   jot.grab(), \
                   self.state.output_filepath, \
                   output_filepath_custom, \
                   output_filepath_marked, \
                   None, None, None
        else:
            return gr.update(selected=5), \
                   gr.update(
                value="At least one scene must be set to 'Keep' before processing can proceed"), \
                   None, None, None, None, None, None, None

    def back_button5(self):
        return gr.update(selected=4)

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
        if self.state.video_details["has_audio"] and not self.state.processed_content_present("audio"):
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
                          custom_audio_options):
        _, _, output_ext = split_filepath(output_filepath)
        output_ext = output_ext[1:]

        self.log(f"about to create custom video clips")
        self.state.create_custom_video_clips(self.log, kept_scenes, global_options,
                                             custom_video_options=custom_video_options,
                                             custom_ext=output_ext)
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
        self.state.output_filepath = output_filepath
        self.state.output_quality = quality
        self.log("saving after storing remix output choices")
        self.state.save()

        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            self.save_remix(global_options, kept_scenes)
            return gr.update(value=f"Remixed video {output_filepath} is complete.",
                            visible=True)

        except ValueError as error:
            return gr.update(value=error, visible=True)

    # User has clicked Save Custom Remix from Save Remix
    def next_button61(self, custom_video_options, custom_audio_options, output_filepath):
        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            self.save_custom_remix(output_filepath, global_options, kept_scenes,
                                   custom_video_options, custom_audio_options)
            return gr.update(value=f"Remixed custom video {output_filepath} is complete.",
                            visible=True)
        except ValueError as error:
            return gr.update(value=error, visible=True)

    # User has clicked Save Marked Remix from Save Remix
    def next_button62(self, marked_video_options, marked_audio_options, output_filepath):
        try:
            global_options, kept_scenes = self.prepare_save_remix(output_filepath)
            self.save_custom_remix(output_filepath, global_options, kept_scenes,
                                   marked_video_options, marked_audio_options)
            return gr.update(value=f"Remixed marked video {output_filepath} is complete.",
                            visible=True)
        except ValueError as error:
            return gr.update(value=error, visible=True)

    def back_button6(self):
        return gr.update(selected=5)

    def drop_button700(self, scene_index):
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(scene_index, (int, float)):
            message = f"Please enter a Scene Index to get started"
            return gr.update(visible=True, value=message)

        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            message = f"Please enter a Scene Index from 0 to {last_scene}"
            return gr.update(visible=True, value=message)

        removed = self.state.force_drop_processed_scene(scene_index)
        self.log(f"removed files: {removed}")
        self.log(
            f"saving project after using force_drop_processed_scene for scene index {scene_index}")
        self.state.save()
        removed = "\r\n".join(removed)
        message = f"Removed:\r\n{removed}"
        return gr.update(visible=True, value=message)

    def choose_button701(self, first_scene_index, last_scene_index, scene_state):
        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1

        if not isinstance(first_scene_index, (int, float)) \
                or not isinstance(last_scene_index, (int, float)):
            message = "Please enter Scene Indexes to get started"
            return gr.update(visible=True, value=message)

        first_scene_index = int(first_scene_index)
        last_scene_index = int(last_scene_index)
        if first_scene_index < 0 \
                or first_scene_index > last_scene \
                or last_scene_index < 0 \
                or last_scene_index > last_scene:
            message = f"Please enter valid Scene Indexes between 0 and {last_scene} to get started"
            return gr.update(visible=True, value=message)

        if first_scene_index >= last_scene_index:
            message = f"'Ending Scene Index' must be higher than 'Starting Scene Index''"
            return gr.update(visible=True, value=message)

        if scene_state not in ["Keep", "Drop"]:
            message = "Please make a Scenes Choice to get started"
            return gr.update(visible=True, value=message)

        for scene_index in range(first_scene_index, last_scene_index + 1):
            scene_name = self.state.scene_names[scene_index]
            self.state.scene_states[scene_name] = scene_state

        first_scene_name = self.state.scene_names[first_scene_index]
        last_scene_name = self.state.scene_names[last_scene_index]

        message = f"Scenes {first_scene_name} through {last_scene_name} set to '{scene_state}'"
        self.log(f"saving project after {message}")
        self.state.save()

        return gr.update(visible=True, value=message)

    def split_button702(self, scene_index):
        global_options = self.config.ffmpeg_settings["global_options"]
        split_point = 0.5 # make variable later

        if not isinstance(scene_index, (int, float)):
            message = f"Please enter a Scene Index to get started"
            return gr.update(selected=7), gr.update(visible=True, value=message), *self.empty_args(5)

        num_scenes = len(self.state.scene_names)
        last_scene = num_scenes - 1
        scene_index = int(scene_index)
        if scene_index < 0 or scene_index > last_scene:
            message = f"Please enter a Scene Index from 0 to {last_scene}"
            return gr.update(selected=7), gr.update(visible=True, value=message), *self.empty_args(5)

        scene_name = self.state.scene_names[scene_index]
        first_frame, last_frame, num_width = details_from_group_name(scene_name)
        num_frames = (last_frame - first_frame) + 1
        if num_frames < 2:
            message = f"Scene must have at least two frames to be split"
            return gr.update(selected=7), gr.update(visible=True, value=message), *self.empty_args(5)

        # ensure the split is at least at the 50% point
        split_frame = math.ceil(num_frames * split_point)
        self.log(f"setting split frame to {split_frame}")

        new_lower_first_frame = first_frame
        new_lower_last_frame = first_frame + (split_frame - 1)
        new_lower_scene_name = VideoRemixerState.encode_scene_label(num_width, new_lower_first_frame, new_lower_last_frame, 0, 0)
        self.log(f"new lower scene name: {new_lower_scene_name}")

        new_upper_first_frame = first_frame + split_frame
        new_upper_last_frame = last_frame
        new_upper_scene_name = VideoRemixerState.encode_scene_label(num_width, new_upper_first_frame, new_upper_last_frame, 0, 0)
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
            message = f"Mismatch between expected frames ({num_frames}) and found frames ({num_frame_files}) in scene path '{original_scene_path}'"
            return gr.update(selected=7), gr.update(visible=True, value=message), *self.empty_args(5)

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
        messages.add(f"Moved {move_count} frames to {new_frame_path}")

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
        self.state.create_thumbnail(new_lower_scene_name, self.log, global_options, self.config.remixer_settings)
        messages.add(f"Created thumbnail for scene {new_lower_scene_name}")
        self.log(f"about to create thumbnail for new upper scene {new_upper_scene_name}")
        self.state.create_thumbnail(new_upper_scene_name, self.log, global_options, self.config.remixer_settings)
        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))
        messages.add(f"Created thumbnail for scene {new_upper_scene_name}")

        self.log("saving project after completing scene split")
        self.state.save()

        message = messages.report()
        return gr.update(selected=3), \
            gr.update(visible=True, value=message), \
            *self.scene_chooser_details(self.state.current_scene)

    def delete_button710(self, delete_purged):
        if delete_purged:
            self.log("about to remove content from 'purged_content' directory")
            removed = self.state.delete_purged_content()
            message = f"Removed: {removed}"
            return gr.update(visible=True, value=message)

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
        return gr.update(visible=True, value=message)

    def select_all_button711(self):
        return gr.update(value=True), \
                gr.update(value=True), \
                gr.update(value=True)

    def select_none_button711(self):
        return gr.update(value=False), \
                gr.update(value=False), \
                gr.update(value=False)

    def delete_button712(self, delete_kept, delete_resized, delete_resynth, delete_inflated, delete_upscaled, delete_audio, delete_video, delete_clips):
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
        return gr.update(visible=True, value=message)

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
        return gr.update(visible=True, value=message)
