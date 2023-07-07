"""Video Remixer feature UI and event handlers"""
import os
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.image_utils import create_gif
from webui_utils.file_utils import get_files, create_directory, locate_frame_file, duplicate_directory, split_filepath
from webui_utils.auto_increment import AutoIncrementDirectory, AutoIncrementFilename
from webui_utils.video_utils import PNGtoMP4, QUALITY_SMALLER_SIZE, MP4toPNG, get_video_details, decode_aspect, get_essential_video_details
from webui_utils.simple_utils import seconds_to_hms, clean_dict, get_frac_str_as_float
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from restore_frames import RestoreFrames
# from video_blender import VideoBlenderState, VideoBlenderProjects
from tabs.tab_base import TabBase
from simplify_png_files import SimplifyPngFiles

# state info
# scene paths list
# current scene

class VideoRemixer(TabBase):
    """Encapsulates UI elements and events for the Video Remixer Feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.new_project()

    def new_project(self):
        self.source_video = None
        self.video_details = {}
        self.project_path = None
        self.project_fps = None
        self.split_type = None
        self.resize_w = None
        self.resize_h = None
        self.crop_w = None
        self.crop_h = None
        self.scene_names = []
        self.scene_states = {}
        self.current_scene = None
        self.resynthesize = False
        self.inflate = False
        self.resize = False
        self.upscale = False
        self.upscale_option = None
        self.assemble = False
        self.keep_scene_clips = False


    def render_tab(self):
        """Render tab into UI"""

        # need configs
        # tab1:
        # - project fps slider settings
        def_project_fps = self.config.remixer_settings["def_project_fps"]
        max_project_fps = self.config.remixer_settings["max_project_fps"]

        with gr.Tab("Video Remixer"):

            with gr.Tabs() as tabs_video_remixer:

                ### NEW PROJECT
                with gr.Tab("New Project", id=0):
                    gr.Markdown("**Input a video to get started remixing**")
                    video_path = gr.Textbox(label="Video Path",
                                    placeholder="Path on this server to the video to be remixed")
                    message_box0 = gr.Textbox(show_label=False, visible=False, interactive=False)
                    next_button0 = gr.Button(value="Next >", variant="primary")

                ### REMIX SETTINGS
                with gr.Tab("Remix Settings", id=1):
                    video_info1 = gr.Textbox(label="Video Details")
                    with gr.Row():
                        project_path = gr.Textbox(label="Project Path",
                                            placeholder="Path on this server to store project data")
                    with gr.Row():
                        project_fps = gr.Slider(label="Remix Frame Rate", value=def_project_fps,
                                                minimum=1.0, maximum=max_project_fps, step=0.01)
                        split_type = gr.Radio(label="Split Type", value="Scene",
                                            choices=["Scene", "Break", "Minutes"])
                    with gr.Row():
                        resize_w = gr.Number(label="Resize Width")
                        resize_h = gr.Number(label="Resize Height")
                    with gr.Row():
                        crop_w = gr.Number(label="Crop Width")
                        crop_h = gr.Number(label="Crop Height")
                    message_box1 = gr.Textbox(show_label=False, visible=False, interactive=False)
                    next_button1 = gr.Button(value="Next >", variant="primary")

                ## SET UP PROJECT
                with gr.Tab("Set Up Project", id=2):
                    gr.Markdown("**Ready to Set Up Video Remixer Project**")
                    with gr.Row():
                        project_info2 = gr.Textbox(label="Project Details")
                    with gr.Row():
                        message_box2 = gr.Textbox(value="Progress can be tracked in the console",
                                                  show_label=False, interactive=False)

                    next_button2 = gr.Button(value="Set Up Project " + SimpleIcons.SLOW_SYMBOL,
                                             variant="primary")

                ## CHOOSE SCENES
                with gr.Tab("Choose Scenes", id=3):
                    with gr.Row():
                        with gr.Column():
                            scene_label = gr.Text(label="Scene", interactive=False)
                        with gr.Column():
                            scene_state = gr.Radio(label="Scene selection", value=None,
                                                choices=["Keep", "Drop"])
                    with gr.Row():
                        with gr.Column():
                            scene_image = gr.Image(type="filepath", interactive=False)
                        with gr.Column():
                            keep_next = gr.Button(value="Keep Scene | Next >", variant="primary",
                                                elem_id="actionbutton")
                            drop_next = gr.Button(value="Drop Scene | Next >", variant="primary",
                                                elem_id="actionbutton")
                            next_scene = gr.Button(value="Next Scene >", variant="secondary")
                            prev_scene = gr.Button(value="< Prev Scene", variant="secondary")

                    next_button3 = gr.Button(value="Done Choosing Scenes", variant="primary")

                ## COMPILE SCENES
                with gr.Tab("Compile Scenes", id=4):
                    project_info4 = gr.Textbox(label="Scene Details")
                    message_box4 = gr.Textbox(value="Progress can be tracked in the console",
                                              show_label=False, interactive=False)

                    next_button4 = gr.Button(value="Compile Chosen Scenes " +
                                             SimpleIcons.SLOW_SYMBOL, variant="primary")

                ## REMIX OPTIONS
                with gr.Tab("Remix Options", id=5):
                    gr.Markdown("**Ready to Process Remixed Video**")
                    with gr.Row():
                        resynthesize = gr.Checkbox(label="Resynthesize Frames",value=True,
                                                   info="Remove grain and stabilize motion")
                    with gr.Row():
                        inflate = gr.Checkbox(label="Inflate New Frames",value=True,
                                              info="Create smooth motion")
                    with gr.Row():
                        resize = gr.Checkbox(label="Fix Aspect Ratio",value=True,
                                             info="Adjust for proper display")
                    with gr.Row():
                        upscale = gr.Checkbox(label="Upscale Frames", value=True,
                                              info="Use Real-ESRGAN to Enlarge Video")
                        upscale_option = gr.Radio(label="Upscale By", value="2X",
                                                  choices=["2X", "4x"])
                    with gr.Row():
                        assemble = gr.Checkbox(label="Assemble Video", value=True,
                                               info="Merge reprocessed frames with audio")
                        keep_scene_clips = gr.Checkbox(label="Keep Scene Clips", value=True,
                                    info="Retain clips of individual scenes")

                    message_box5 = gr.Textbox(value="Progress can be tracked in the console",
                                              show_label=False, interactive=False)

                    next_button5 = gr.Button(value="Remix Video " +
                                             SimpleIcons.SLOW_SYMBOL, variant="primary")

                ## REMIX SUMMARY
                with gr.Tab("Remix Options", id=6):
                    gr.Markdown("**Remixed Video Ready**")
                    summary_info6 = gr.Textbox(label="Scene Details", interactive=False)

        next_button0.click(self.next_button0,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box0, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, resize_w, resize_h,
                                   crop_w, crop_h],
                           outputs=[tabs_video_remixer, message_box1, project_info2])

        next_button2.click(self.next_button2,
                           outputs=[tabs_video_remixer, message_box2, scene_label, scene_image,
                                    scene_state])

        keep_next.click(self.keep_next, show_progress=False,
                            inputs=[scene_label, scene_state],
                            outputs=[scene_label, scene_image, scene_state])

        drop_next.click(self.drop_next, show_progress=False,
                            inputs=[scene_label, scene_state],
                            outputs=[scene_label, scene_image, scene_state])

        next_scene.click(self.next_scene, show_progress=False,
                            inputs=[scene_label, scene_state],
                            outputs=[scene_label, scene_image, scene_state])

        prev_scene.click(self.prev_scene, show_progress=False,
                            inputs=[scene_label, scene_state],
                            outputs=[scene_label, scene_image, scene_state])

        next_button3.click(self.next_button3,
                           outputs=[tabs_video_remixer, project_info4])

        next_button4.click(self.next_button4,
                           outputs=[tabs_video_remixer, message_box4])

        next_button5.click(self.next_button5,
                           inputs=[resynthesize, inflate, resize, upscale, upscale_option,
                                   assemble, keep_scene_clips],
                           outputs=[tabs_video_remixer, message_box5, summary_info6])

    def next_button0(self, video_path):
        self.new_project()
        if video_path:
            if os.path.exists(video_path):
                self.source_video = video_path
                path, filename, ext = split_filepath(video_path)
                self.project_path = path

                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "FFmpeg in use ...")
                    try:
                        video_details = get_essential_video_details(video_path)
                    except RuntimeError as error:
                        message = f"Error getting video details for '{video_path}': {error}"
                        return gr.update(selected=0), gr.update(visible=True, value=message), None, None, None, None, None, None
                    finally:
                        Mtqdm().update_bar(bar)

                report = []
                report.append(f"Frame Rate: {video_details['frame_rate']}")
                report.append(f"Duration: {video_details['duration']}")
                report.append(f"Display Size: {video_details['display_dimensions']}")
                report.append(f"Aspect Ratio: {video_details['display_aspect_ratio']}")
                report.append(f"Content Size: {video_details['content_dimensions']}")
                report.append(f"Frame Count: {video_details['frame_count']}")
                report.append(f"File Size: {video_details['file_size']}")
                message = "\r\n".join(report)

                project_path = path
                resize_w = video_details['display_width']
                resize_h = video_details['display_height']
                crop_w, crop_h = resize_w, resize_h
                return gr.update(selected=1), gr.update(visible=False, value=None), gr.update(value=message), project_path, resize_w, resize_h, crop_w, crop_h

            else:
                message = f"File {video_path} was not found"
                return gr.update(selected=0), gr.update(visible=True, value=message), None, None, None, None, None, None




        # video path is validated
        # video info is gotten
        # if there's a problem, message_box0 is revealed and message displayed
        # otherwise fill video_info1 and move to tab id=1

        return gr.update(selected=1), "message", "info", "path", 123, 456, 789, 1011

    def next_button1(self, project_path, project_fps, split_type, resize_w, resize_h, crop_w, crop_h):
        # entries are validated
        # if there's a problem, message_box1 is revealed and message displayed
        # otherwise fill project_info2 and # set tab id=2

        return gr.update(selected=2), "message", "info"

    def next_button2(self):
        # project path is created
        # video is copied there if not already
        # video is split into PNG frames to a RAW directory
        # video is split into scenes
        # GIF thumbnails are created
        # initial selection is established (all or none copied GIFs)
        # ?VideoRemixerProject is created?
        # VideoRemixerState is initialized
        # if there's a problem, message_box2 (is revealed and) message displayed
        # otherwise
        # - updates for scene chooser from VideoRemixerState for scene #0:
        #   - scene_image, scene_state
        #   - set tab id=3


        return gr.update(selected=3), "message", "[123-456]", None, "Keep"

    def keep_next(self, scene_label, scene_state):
        return "[000-123]", None, "Keep"

    def drop_next(self, scene_label, scene_state):
        return "[456-789]", None, "Keep"

    def next_scene(self, scene_label, scene_state):
        return "[456-789]", None, "Keep"

    def prev_scene(self, scene_label, scene_state):
        return "[000-123]", None, "Keep"

    def next_button3(self):
        return gr.update(selected=4), "info"

    def next_button4(self):
        # performs a strip scenes operation
        # then update tab ID to 5

        return gr.update(selected=5), "info"

    def next_button5(self, resynthesize, inflate, resize, upscale, upscale_option, assemble, keep_scene_clips):
        # do all the things
        return gr.update(selected=6), "message", "info"
