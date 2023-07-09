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
from split_scenes import SplitScenes
from split_frames import SplitFrames
from slice_video import SliceVideo
from video_remixer import VideoRemixerState

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
        self.state = VideoRemixerState()

    def render_tab(self):
        """Render tab into UI"""
        def_project_fps = self.config.remixer_settings["def_project_fps"]
        max_project_fps = self.config.remixer_settings["max_project_fps"]
        with gr.Tab("Video Remixer"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Restore & Remix Videos with Audio")
            with gr.Tabs() as tabs_video_remixer:

                ### NEW PROJECT
                with gr.Tab("New Project", id=0):
                    gr.Markdown("**Input a video to get started remixing**")
                    with gr.Row():
                        video_path = gr.Textbox(label="Video Path",
                                    placeholder="Path on this server to the video to be remixed")
                    with gr.Row():
                        message_box0 = gr.Textbox(
                value="About to inspect video and count frames ... this could take a minute ...",
                                    show_label=False, visible=True, interactive=False)
                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button0 = gr.Button(value="Next > " + SimpleIcons.SLOW_SYMBOL,
                                             variant="primary")

                ### REMIX SETTINGS
                with gr.Tab("Remix Settings", id=1):
                    gr.Markdown("**Confirm Remixer Settings**")
                    video_info1 = gr.Textbox(label="Video Details")
                    with gr.Row():
                        project_path = gr.Textbox(label="Project Path",
                                            placeholder="Path on this server to store project data")
                        project_fps = gr.Slider(label="Remix Frame Rate", value=def_project_fps,
                                                minimum=1.0, maximum=max_project_fps, step=0.01)

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

                    message_box1 = gr.Textbox(show_label=False, interactive=False)
                    next_button1 = gr.Button(value="Next >", variant="primary")

                ## SET UP PROJECT
                with gr.Tab("Set Up Project", id=2):
                    gr.Markdown("**Ready to Set Up Video Remixer Project**")
                    with gr.Row():
                        project_info2 = gr.Textbox(label="Project Details")
                    with gr.Row():
                        message_box2 = gr.Textbox(
    value="About to split video info scenes and create thumbnails ... this could take a while ...",
                                    show_label=False, visible=True, interactive=False)

                    gr.Markdown("*Progress can be tracked in the console*")
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
                    message_box4 = gr.Textbox(value="About to (strip scenes)",
                                              show_label=False, interactive=False)

                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button4 = gr.Button(value="Compile Chosen Scenes " +
                                             SimpleIcons.SLOW_SYMBOL, variant="primary")

                ## REMIX OPTIONS
                with gr.Tab("Procesing Options", id=5):
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

                    message_box5 = gr.Textbox(value="About to ... take hours or days",
                                              show_label=False, interactive=False)

                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button5 = gr.Button(value="Remix Video " +
                                             SimpleIcons.SLOW_SYMBOL, variant="primary")

                ## REMIX SUMMARY
                with gr.Tab("Remix Final", id=6):
                    gr.Markdown("**Remixed Video Ready**")
                    summary_info6 = gr.Textbox(label="Scene Details", interactive=False)

        next_button0.click(self.next_button0,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box0, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold, break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h],
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
                self.state.source_video = video_path
                path, _, _ = split_filepath(video_path)
                self.state.project_path = path

                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "FFmpeg in use ...")
                    try:
                        video_details = get_essential_video_details(video_path)
                        self.state.video_details = video_details
                    except RuntimeError as error:
                        message = f"Error getting video details for '{video_path}': {error}"
                        return gr.update(selected=0), gr.update(visible=True, value=message), None, None, None, None, None, None
                    finally:
                        Mtqdm().message(bar)
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

                project_path = os.path.join(path, "REMIX")
                resize_w = video_details['display_width']
                resize_h = video_details['display_height']
                crop_w, crop_h = resize_w, resize_h
                return gr.update(selected=1), gr.update(visible=True), gr.update(value=message), project_path, resize_w, resize_h, crop_w, crop_h

            else:
                message = f"File {video_path} was not found"
                return gr.update(selected=0), gr.update(visible=True, value=message), None, None, None, None, None, None

        return gr.update(selected=0), gr.update(visible=True, value="Enter a path to a video on this server to get started"), None, None, None, None, None, None

    def next_button1(self, project_path, project_fps, split_type, scene_threshold, break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h):
        # validate entries
        self.state.project_path = project_path
        self.state.project_fps = project_fps
        self.state.split_type = split_type
        self.state.scene_threshold = scene_threshold
        self.state.break_duration = break_duration
        self.state.break_ratio = break_ratio
        self.state.resize_w = int(resize_w)
        self.state.resize_h = int(resize_h)
        self.state.crop_w = int(crop_w)
        self.state.crop_h = int(crop_h)

        report, sep = [], ""
        report.append(f"Project Path: {self.state.project_path}")
        report.append(f"Project Frame Rate: {self.state.project_fps}")
        report.append(f"Resize To: {self.state.resize_w}x{self.state.resize_h}")
        report.append(f"Crop To: {self.state.crop_w}x{self.state.crop_h}")
        report.append(f"Scene Split Type: {self.state.split_type}")
        if self.state.split_type == "scene":
            report.append(f"Scene Detection Threshold: {self.state.scene_threshold}")
        elif self.state.split_type == "break":
            report.append(f"Break Minimum Duration: {self.state.break_duration}")
            report.append(f"Break Black Frame Ratio: {self.state.break_duration}")
        else:
            self.state.frames_per_minute = int(float(self.state.project_fps) * 60)
            report.append(f"Frames per Minute: {self.state.frames_per_minute}")
        report.append(sep)

        report.append(f"Source Video: {self.state.source_video}")
        report.append(f"Duration: {self.state.video_details['duration']}")
        report.append(f"Frame Rate: {self.state.video_details['frame_rate']}")
        report.append(f"File Size: {self.state.video_details['file_size']}")
        report.append(f"Frame Count: {self.state.video_details['frame_count']}")
        message = "\r\n".join(report)
        return gr.update(selected=2), gr.update(visible=True), message

    def next_button2(self):
        # create project directory
        self.log(f"creating project path {self.state.project_path}")
        create_directory(self.state.project_path)

        # copy video to project directory
        _, filename, ext = split_filepath(self.state.source_video)
        video_filename = filename + ext
        project_video_path = os.path.join(self.state.project_path, video_filename)
        if not os.path.exists(project_video_path):
            self.log(f"copying video from {self.state.source_video} to project path")
            with Mtqdm().open_bar(total=1, desc="Copying") as bar:
                Mtqdm().message(bar, "Copying source video to project path ...")
                shutil.copy(self.state.source_video, project_video_path)
                self.state.source_video = project_video_path
                Mtqdm().message(bar)
                Mtqdm().update_bar(bar)

        # split video into raw PNG frames
        video_path = self.state.source_video
        index_width = self.state.video_details["index_width"]
        self.state.output_pattern = f"source_%0{index_width}d.png"
        frame_rate = self.state.project_fps
        self.state.frames_path = os.path.join(self.state.project_path, "SOURCE")
        self.log(f"creating frames directory {self.state.frames_path}")
        create_directory(self.state.frames_path)
        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "FFmpeg in use ...")
            self.log(f"calling MP4toPNG with input path={video_path}" +\
        f" pattern={self.state.output_pattern} frame rate={frame_rate} frames path={self.state.frames_path})")
            ffmpeg_cmd = MP4toPNG(video_path, self.state.output_pattern, frame_rate, self.state.frames_path)
            self.log(f"FFmpeg command: {ffmpeg_cmd}")
            Mtqdm().message(bar)
            Mtqdm().update_bar(bar)

        # split frames into scenes
        self.state.scenes_path = os.path.join(self.state.project_path, "SCENES")
        self.log(f"creating scenes directory {self.state.scenes_path}")
        create_directory(self.state.scenes_path)
        if self.state.split_type == "Scene":
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                SplitScenes(self.state.frames_path,
                            self.state.scenes_path,
                            "png",
                            "scene",
                            self.state.scene_threshold,
                            0.0,
                            0.0,
                            self.log).split()
                Mtqdm().message(bar)
                Mtqdm().update_bar(bar)
        elif self.state.split_type == "Break":
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                SplitScenes(self.state.frames_path,
                            self.state.scenes_path,
                            "png",
                            "break",
                            0.0,
                            self.state.break_duration,
                            self.state.break_ratio,
                            self.log).split()
                Mtqdm().message(bar)
                Mtqdm().update_bar(bar)
        else:
            # split by minute
            SplitFrames(
                self.state.frames_path,
                self.state.scenes_path,
                "png",
                "precise",
                0,
                self.state.frames_per_minute,
                "copy",
                False,
                self.log).split()

        # create animated gif thumbnails
        gif_fps = self.config.remixer_settings["default_gif_fps"]
        gif_factor = self.config.remixer_settings["gif_factor"]
        gif_end_delay = self.config.remixer_settings["gif_end_delay"]
        thumb_scale = self.config.remixer_settings["thumb_scale"]
        max_thumb_size = self.config.remixer_settings["max_thumb_size"]

        video_w = self.state.video_details['display_width']
        video_h = self.state.video_details['display_height']
        max_frame_dimension = video_w if video_w > video_h else video_h
        thumb_size = max_frame_dimension * thumb_scale
        if thumb_size > max_thumb_size:
            thumb_scale = max_thumb_size / max_frame_dimension

        source_fps = float(self.state.video_details['frame_rate'])
        self.thumbnail_path = os.path.join(self.state.project_path, "THUMBNAILS")
        self.log(f"creating thumbnails directory {self.thumbnail_path}")
        create_directory(self.thumbnail_path)
        SliceVideo(self.state.source_video,
                    source_fps,
                    self.state.scenes_path,
                    self.thumbnail_path,
                    thumb_scale,
                    "gif",
                    0,
                    gif_factor,
                    0,
                    False,
                    gif_fps,
                    gif_end_delay,
                    self.log).slice()

        # initial selection is established (all or none copied GIFs)
        # ?VideoRemixerProject is created?
        # VideoRemixerState is initialized
        # if there's a problem, message_box2 (is revealed and) message displayed
        # otherwise
        # - updates for scene chooser from VideoRemixerState for scene #0:
        #   - scene_image, scene_state
        #   - set tab id=3


        return gr.update(selected=3), "messag1", "[123-456]", None, "Keep"

    def keep_next(self, scene_label, scene_state):
        return "[000-123]", None, "Keep"

    def drop_next(self, scene_label, scene_state):
        return "[456-789]", None, "Keep"

    def next_scene(self, scene_label, scene_state):
        return "[456-789]", None, "Keep"

    def prev_scene(self, scene_label, scene_state):
        return "[000-123]", None, "Keep"

    def next_button3(self   ):
        return gr.update(selected=4), "info"

    def next_button4(self):
        # performs a strip scenes operation
        # then update tab ID to 5

        return gr.update(selected=5), "info"

    def next_button5(self, resynthesize, inflate, resize, upscale, upscale_option, assemble, keep_scene_clips):
        # do all the things
        return gr.update(selected=6), "messag2", "info"
