"""Video Remixer feature UI and event handlers"""
import os
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf
from webui_utils.file_utils import get_files, create_directory, split_filepath, get_directories, \
    remove_directories
from webui_utils.video_utils import MP4toPNG, get_essential_video_details, PNGtoMP4, \
    combine_video_audio, combine_videos, details_from_group_name
from webui_utils.mtqdm import Mtqdm
from webui_utils.jot import Jot
# from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from tabs.tab_base import TabBase
from split_scenes import SplitScenes
from split_frames import SplitFrames
from slice_video import SliceVideo
from video_remixer import VideoRemixerState
from resize_frames import ResizeFrames
from upscale_series import UpscaleSeries

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

        # set project settings UI defaults in case the project is reopened
        # otherwise some UI elements get set to None on reopened new projects
        self.state.project_fps = self.config.remixer_settings["def_project_fps"]
        self.state.split_type = "Scene"
        self.state.scene_threshold = 0.6
        self.state.break_duration = 2.0
        self.state.break_ratio = 0.98
        self.state.thumbnail_type = "JPG"
        self.state.resynthesize = True
        self.state.inflate = True
        self.state.resize = True
        self.state.upscale = True
        self.state.upscale_option = "2X"

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
                                                        SimpleIcons.SLOW_SYMBOL, variant="primary")
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

                ### REMIX SETTINGS
                with gr.Tab("Remix Settings", id=1):
                    gr.Markdown("**Confirm Remixer Settings**")
                    video_info1 = gr.Textbox(label="Video Details", lines=6)
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
                    next_button1 = gr.Button(value="Next >", variant="primary")

                ## SET UP PROJECT
                with gr.Tab("Set Up Project", id=2):
                    gr.Markdown("**Ready to Set Up Video Remixer Project**")
                    with gr.Row():
                        project_info2 = gr.Textbox(label="Project Details", lines=6,
                                                   interactive=False)
                    with gr.Row():
                        thumbnail_type = gr.Radio(choices=["GIF", "JPG"], value="JPG",
                                                  label="Thumbnail Type",
                                    info="Choose 'GIF' for whole-scene animations (slow to render)")
                    with gr.Row():
                        message_box2 = gr.Textbox(
        value="Next: Create Scenes, Thumbnails and Audio Clips (takes from minutes to hours)",
                                    show_label=False, visible=True, interactive=False)

                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button2 = gr.Button(value="Set Up Project " + SimpleIcons.SLOW_SYMBOL,
                                             variant="primary")

                ## CHOOSE SCENES
                with gr.Tab("Choose Scenes", id=3):
                    with gr.Row():
                        with gr.Column():
                            with gr.Row():
                                scene_label = gr.Text(label="Scene", interactive=False)
                                scene_info = gr.Text(label="Scene Details", interactive=False)
                        with gr.Column():
                            scene_state = gr.Radio(label="Scene selection", value=None,
                                                choices=["Keep", "Drop"])
                    with gr.Row():
                        with gr.Column():
                            scene_image = gr.Image(type="filepath", interactive=False).style(height=max_thumb_size)
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
                            gr.Box()
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

                    next_button3 = gr.Button(value="Done Choosing Scenes", variant="primary")

                ## COMPILE SCENES
                with gr.Tab("Compile Scenes", id=4):
                    with gr.Row():
                        project_info4 = gr.Textbox(label="Chosen Scene Details", lines=6)
                    with gr.Row():
                        message_box4 = gr.Textbox(show_label=False, interactive=False,
                                        value="Next: Compile 'Keep' and 'Drop' scenes")
                    next_button4 = gr.Button(value="Compile Scenes", variant="primary")

                ## PROCESSING OPTIONS
                with gr.Tab("Procesing Options", id=5):
                    gr.Markdown("**Ready to Process Original Content into Remix Content**")
                    with gr.Row():
                        resize = gr.Checkbox(label="Fix Aspect Ratio",value=True,
                                             info="Adjust for proper display")
                    with gr.Row():
                        resynthesize = gr.Checkbox(label="Resynthesize Frames",value=True,
                                                   info="Remove grain and stabilize motion")
                    with gr.Row():
                        inflate = gr.Checkbox(label="Inflate New Frames",value=True,
                                              info="Create smooth motion")
                    with gr.Row():
                        upscale = gr.Checkbox(label="Upscale Frames", value=True,
                                              info="Use Real-ESRGAN to Enlarge Video")
                        upscale_option = gr.Radio(label="Upscale By", value="2X",
                                                  choices=["2X", "4X"])
                    message_box5 = gr.Textbox(
                        value="Next: Perform all Processing Steps (takes from hours to days)",
                                              show_label=False, interactive=False)
                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button5 = gr.Button(value="Process Remix " +
                                             SimpleIcons.SLOW_SYMBOL, variant="primary")

                ## REMIX VIDEOS
                with gr.Tab("Save Remix", id=6):
                    gr.Markdown("**Ready to Finalize Scenes and Merge Remixed Video**")
                    with gr.Row():
                        summary_info6 = gr.Textbox(label="Processed Content", lines=6,
                                                interactive=False)
                    quality_slider = gr.Slider(minimum=minimum_crf, maximum=maximum_crf,
                        step=1, value=default_crf, label="Video Quality",
                        info="Lower values mean higher video quality")
                    output_filepath = gr.Textbox(label="Output Filepath", max_lines=1,
                               info="Enter a path and filename for the remixed video")
                    with gr.Row():
                        message_box6 = gr.Textbox(value=None, show_label=False, interactive=False)
                    gr.Markdown("*Progress can be tracked in the console*")
                    next_button6 = gr.Button(value="Process Remix " + SimpleIcons.SLOW_SYMBOL,
                                             variant="primary")

        next_button00.click(self.next_button00,
                           inputs=video_path,
                           outputs=[tabs_video_remixer, message_box00, video_info1, project_path,
                                    resize_w, resize_h, crop_w, crop_h])

        next_button01.click(self.next_button01,
                           inputs=project_load_path,
                           outputs=[tabs_video_remixer, message_box01, video_info1, project_path,
                                project_fps, deinterlace, split_type, scene_threshold,
                                break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h,
                                project_info2, thumbnail_type, scene_label, scene_image,
                                scene_state, scene_info, project_info4, resize, resynthesize,
                                inflate, upscale, upscale_option, summary_info6])

        next_button1.click(self.next_button1,
                           inputs=[project_path, project_fps, split_type, scene_threshold,
                    break_duration, break_ratio, resize_w, resize_h, crop_w, crop_h, deinterlace],
                           outputs=[tabs_video_remixer, message_box1, project_info2, message_box2])

        next_button2.click(self.next_button2, inputs=thumbnail_type,
                           outputs=[tabs_video_remixer, message_box2, scene_label, scene_image,
                                    scene_state, scene_info])

        scene_state.change(self.scene_state_button, show_progress=False,
                            inputs=[scene_label, scene_state],
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        keep_next.click(self.keep_next, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        drop_next.click(self.drop_next, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        next_scene.click(self.next_scene, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        prev_scene.click(self.prev_scene, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        next_keep.click(self.next_keep, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        prev_keep.click(self.prev_keep, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        keep_all_button.click(self.keep_all_scenes, show_progress=True,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        drop_all_button.click(self.drop_all_scenes, show_progress=True,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        first_scene.click(self.first_scene, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        last_scene.click(self.last_scene, show_progress=False,
                            inputs=scene_label,
                            outputs=[scene_label, scene_image, scene_state, scene_info])

        next_button3.click(self.next_button3,
                           outputs=[tabs_video_remixer, project_info4])

        next_button4.click(self.next_button4,
                           outputs=[tabs_video_remixer, message_box4, message_box5])

        next_button5.click(self.next_button5,
                    inputs=[resynthesize, inflate, resize, upscale, upscale_option],
                    outputs=[tabs_video_remixer, message_box5, summary_info6, output_filepath])

        next_button6.click(self.next_button6, inputs=[output_filepath, quality_slider],
                           outputs=message_box6)

    def next_button00(self, video_path):
        self.new_project()
        if video_path:
            if os.path.exists(video_path):
                self.state.source_video = video_path
                path, filename, _ = split_filepath(video_path)

                with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                    Mtqdm().message(bar, "FFmpeg in use ...")
                    try:
                        video_details = get_essential_video_details(video_path)
                        self.state.video_details = video_details
                    except RuntimeError as error:
                        return gr.update(selected=0), gr.update(visible=True, value=error), \
                            None, None, None, None, None, None
                    finally:
                        Mtqdm().update_bar(bar)

                with Jot() as jot:
                    jot.down(f"Source Video: {video_details['source_video']}")
                    jot.down(f"Frame Rate: {video_details['frame_rate']}")
                    jot.down(f"Duration: {video_details['duration']}")
                    jot.down(f"Display Size: {video_details['display_dimensions']}")
                    jot.down(f"Aspect Ratio: {video_details['display_aspect_ratio']}")
                    jot.down(f"Content Size: {video_details['content_dimensions']}")
                    jot.down(f"Frame Count: {video_details['frame_count']}")
                    jot.down(f"File Size: {video_details['file_size']}")
                    jot.down(f"Has Audio: {True if video_details['has_audio'] else False}")
                self.state.video_info1 = jot

                project_path = os.path.join(path, f"REMIX-{filename}")
                resize_w = video_details['display_width']
                resize_h = video_details['display_height']
                crop_w, crop_h = resize_w, resize_h

                self.state.project_path = project_path
                self.state.resize_w = resize_w
                self.state.resize_h = resize_h
                self.state.crop_w = crop_w
                self.state.crop_h = crop_h

                # advancing to the next tab displays information about the source video only
                # user may decide not to proceed after seeing it
                # therefore it is too early to save project advancement
                # self.state.save_progress("settings")

                return gr.update(selected=1), gr.update(visible=True), gr.update(value=jot), \
                    project_path, resize_w, resize_h, crop_w, crop_h
            else:
                message = f"File {video_path} was not found"
                return gr.update(selected=0), gr.update(visible=True, value=message), \
                    None, None, None, None, None, None

        return gr.update(selected=0), gr.update(visible=True,
            value="Enter a path to a video on this server to get started"), \
                None, None, None, None, None, None

    def next_button01(self, project_path):
        if project_path:
            if os.path.exists(project_path):
                if os.path.isdir(project_path):
                    project_file = os.path.join(project_path, VideoRemixerState.DEF_FILENAME)
                else:
                    project_file = project_path
                    project_path, _, _ = split_filepath(project_path)
                if os.path.exists(project_file):
                    try:
                        self.state = VideoRemixerState.load(project_file)
                    except ValueError as error:
                        self.log(f"error opening project: {error}")
                        return gr.update(selected=0), \
                            gr.update(visible=True, value=error), *[None for n in range(25)]

                    if self.state.project_path != project_path:
                        message = f"Project must be opened from original project path {self.state.project_path}"
                        return gr.update(selected=0), \
                            gr.update(visible=True, value=message), *[None for n in range(25)]

                    return_to_tab = self.state.get_progress_tab()
                    scene_details = self.scene_chooser_details(self.state.current_scene)
                    return gr.update(selected=return_to_tab), \
                        gr.update(visible=True), \
                        self.state.video_info1, \
                        self.state.project_path, \
                        self.state.project_fps, \
                        self.state.deinterlace, \
                        self.state.split_type, \
                        self.state.scene_threshold, \
                        self.state.break_duration, \
                        self.state.break_ratio, \
                        self.state.resize_w, \
                        self.state.resize_h, \
                        self.state.crop_w, \
                        self.state.crop_h, \
                        self.state.project_info2, \
                        self.state.thumbnail_type, \
                        *scene_details, \
                        self.state.project_info4, \
                        self.state.resize, \
                        self.state.resynthesize, \
                        self.state.inflate, \
                        self.state.upscale, \
                        self.state.upscale_option, \
                        self.state.summary_info6
                else:
                    message = f"Project file {project_file} was not found"
                    return gr.update(selected=0), \
                        gr.update(visible=True, value=message), *[None for n in range(25)]
            else:
                message = f"Directory {project_path} was not found"
                return gr.update(selected=0), \
                    gr.update(visible=True, value=message), *[None for n in range(25)]
        else:
            message = \
                "Enter a path to a Video Remixer project directory on this server to get started"
            return gr.update(selected=0), \
                gr.update(visible=True, value=message), *[None for n in range(25)]

    def next_button1(self, project_path, project_fps, split_type, scene_threshold, break_duration, \
                     break_ratio, resize_w, resize_h, crop_w, crop_h, deinterlace):
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
        self.state.deinterlace = deinterlace

        report, sep = [], ""
        report.append(f"Project Path: {self.state.project_path}")
        report.append(f"Project Frame Rate: {self.state.project_fps}")
        report.append(f"Deinterlace Source: {self.state.deinterlace}")
        report.append(f"Resize To: {self.state.resize_w}x{self.state.resize_h}")
        report.append(f"Crop To: {self.state.crop_w}x{self.state.crop_h}")
        report.append(f"Scene Split Type: {self.state.split_type}")
        if self.state.split_type == "Scene":
            report.append(f"Scene Detection Threshold: {self.state.scene_threshold}")
        elif self.state.split_type == "Break":
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
        self.state.project_info2 = message

        # user will expect to return to the setup tab on reopening
        self.log(f"saving new project at {self.state.project_filepath()}")
        self.state.save_progress("setup")

        return gr.update(selected=2), gr.update(visible=True), message, \
            "Next: Create Scenes, Thumbnails and Audio Clips (takes from minutes to hours)"

    def next_button2(self, thumbnail_type):
        self.state.thumbnail_type = thumbnail_type
        self.log(f"saving new project at {self.state.project_filepath()}")
        self.state.save()

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
                Mtqdm().update_bar(bar)

        self.log("saving project after ensuring video is in project path")
        self.state.save()

        # user may be redoing this, so clear things that may exist and interfere
        self.log("removing derivatives of previous project settings")
        remove_directories([
            self.state.frames_path,
            self.state.scenes_path,
            self.state.dropped_scenes_path,
            self.state.thumbnail_path,
            self.state.clips_path,
            self.state.resize_path,
            self.state.resynthesis_path,
            self.state.inflation_path,
            self.state.upscale_path])
        self.state.thumbnails = []

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
                f" pattern={self.state.output_pattern} frame rate={frame_rate}" +\
                f" frames path={self.state.frames_path} deinterlace={self.state.deinterlace})")
            global_options = self.config.ffmpeg_settings["global_options"]
            ffmpeg_cmd = MP4toPNG(video_path, self.state.output_pattern, frame_rate,
        self.state.frames_path, deinterlace=self.state.deinterlace, global_options=global_options)
            self.log(f"FFmpeg command: {ffmpeg_cmd}")
            Mtqdm().update_bar(bar)

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

        # split frames into scenes
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
                Mtqdm().update_bar(bar)
        elif self.state.split_type == "Break":
            with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
                Mtqdm().message(bar, "FFmpeg in use ...")
                SplitScenes(self.state.frames_path,
                            self.state.scenes_path,
                            "png",
                            "break",
                            0.0,
                            float(self.state.break_duration),
                            float(self.state.break_ratio),
                            self.log).split()
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

        self.log("saving project after splitting into scenes")
        self.state.save()

        self.state.scene_names = sorted(get_directories(self.state.scenes_path))
        self.state.drop_all_scenes()
        self.state.current_scene = self.state.scene_names[0]
        self.log("saving project after establishing scene names")
        self.state.save()

        # self.log("checking for zero-length scenes")
        # bad_scenes = self.state.check_for_bad_scenes()
        # if bad_scenes:
        #     bad_scenes = "\r\n".join(bad_scenes)
        #     self.log(f"zero-length scenes found: " + bad_scenes)
        #     message = SimpleIcons.WARNING + \
        #         f" WARNING: Zero-length scenes found - adjust split settings: " + bad_scenes
        #     return gr.update(selected=2), gr.update(visible=True, value=message), \
        #         None, None, None, None

        if self.state.thumbnail_type == "JPG":
            # create jpeg thumbnails
            thumb_scale = self.config.remixer_settings["thumb_scale"]
            max_thumb_size = self.config.remixer_settings["max_thumb_size"]
            video_w = self.state.video_details['display_width']
            video_h = self.state.video_details['display_height']

            max_frame_dimension = video_w if video_w > video_h else video_h
            thumb_size = max_frame_dimension * thumb_scale
            if thumb_size > max_thumb_size:
                thumb_scale = max_thumb_size / max_frame_dimension

            self.state.thumbnail_path = os.path.join(self.state.project_path, "THUMBNAILS")
            self.log(f"creating thumbnails directory {self.state.thumbnail_path}")
            create_directory(self.state.thumbnail_path)

            global_options = self.config.ffmpeg_settings["global_options"]
            self.log(f"creating JPG thumbnails")
            SliceVideo(self.state.source_video,
                        self.state.project_fps,
                        self.state.scenes_path,
                        self.state.thumbnail_path,
                        thumb_scale,
                        "jpg",
                        0,
                        1,
                        0,
                        False,
                        0.0,
                        0.0,
                        self.log,
                        global_options=global_options).slice()
        elif self.state.thumbnail_type == "GIF":
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
            self.state.thumbnail_path = os.path.join(self.state.project_path, "THUMBNAILS")
            self.log(f"creating thumbnails directory {self.state.thumbnail_path}")
            create_directory(self.state.thumbnail_path)
            global_options = self.config.ffmpeg_settings["global_options"]
            self.log(f"creating animated GIF thumbnails")
            SliceVideo(self.state.source_video,
                        self.state.project_fps,
                        self.state.scenes_path,
                        self.state.thumbnail_path,
                        thumb_scale,
                        "gif",
                        0,
                        gif_factor,
                        0,
                        False,
                        gif_fps,
                        gif_end_delay,
                        self.log,
                        global_options=global_options).slice()
        else:
            raise ValueError(f"thumbnail type '{self.state.thumbnail_type}' is not implemented")

        self.state.thumbnails = sorted(get_files(self.state.thumbnail_path))
        self.log("saving project after creating scene thumbnails")
        self.state.save()

        self.state.clips_path = os.path.join(self.state.project_path, "CLIPS")
        self.log(f"creating clips directory {self.state.clips_path}")
        create_directory(self.state.clips_path)

        # user will expect to return to scene chooser on reopening
        self.log("saving project after setting up scene selection states")
        self.state.save_progress("choose")

        return gr.update(selected=3), gr.update(visible=True), \
            *self.scene_chooser_details(self.state.current_scene)

    def scene_state_button(self, scene_label, scene_state):
        self.state.scene_states[scene_label] = scene_state
        self.state.save()
        return self.scene_chooser_details(self.state.current_scene)

    def keep_next(self, scene_label):
        self.state.scene_states[scene_label] = "Keep"
        self.state.save()
        return self.next_scene(scene_label)

    def drop_next(self, scene_label):
        self.state.scene_states[scene_label] = "Drop"
        self.state.save()
        return self.next_scene(scene_label)

    def next_scene(self, scene_label):
        scene_index = self.state.scene_names.index(scene_label)
        if scene_index < len(self.state.scene_names)-1:
            scene_index += 1
            self.state.current_scene = self.state.scene_names[scene_index]
        return self.scene_chooser_details(self.state.current_scene)

    def prev_scene(self, scene_label):
        scene_index = self.state.scene_names.index(scene_label)
        if scene_index > 0:
            scene_index -= 1
            self.state.current_scene = self.state.scene_names[scene_index]
        return self.scene_chooser_details(self.state.current_scene)

    def next_keep(self, scene_label):
        scene_index = self.state.scene_names.index(scene_label)
        for index in range(scene_index+1, len(self.state.scene_names)):
            scene_name = self.state.scene_names[index]
            if self.state.scene_states[scene_name] == "Keep":
                self.state.current_scene = scene_name
                break
        return self.scene_chooser_details(self.state.current_scene)

    def prev_keep(self, scene_label):
        scene_index = self.state.scene_names.index(scene_label)
        for index in range(scene_index-1, -1, -1):
            scene_name = self.state.scene_names[index]
            if self.state.scene_states[scene_name] == "Keep":
                self.state.current_scene = scene_name
                break
        return self.scene_chooser_details(self.state.current_scene)

    def keep_all_scenes(self, scene_label):
        self.state.keep_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def drop_all_scenes(self, scene_label):
        self.state.drop_all_scenes()
        return self.scene_chooser_details(self.state.current_scene)

    def first_scene(self, scene_label):
        self.state.current_scene = self.state.scene_names[0]
        return self.scene_chooser_details(self.state.current_scene)

    def last_scene(self, scene_label):
        self.state.current_scene = self.state.scene_names[-1]
        return self.scene_chooser_details(self.state.current_scene)

    def scene_chooser_details(self, scene_name):
        if self.state.thumbnails:
            try:
                scene_index = self.state.scene_names.index(scene_name)
                thumbnail_path = self.state.thumbnails[scene_index]
                scene_state = self.state.scene_states[scene_name]

                scene_position = f"{scene_index+1}/{len(self.state.scene_names)}"
                first_index, last_index, _ = details_from_group_name(scene_name)
                scene_start = seconds_to_hmsf(first_index / self.state.project_fps,
                                            self.state.project_fps)
                scene_duration = seconds_to_hmsf((last_index - first_index) / self.state.project_fps,
                                                self.state.project_fps)
                sep = "      "
                scene_info = f"{scene_position}{sep}Time: {scene_start}{sep}Span: {scene_duration}"
                return scene_name, thumbnail_path, scene_state, scene_info
            except ValueError as error:
                self.log(f"value error using scene_chooser_details(): {error}")
                return None, None, None, None
            except IndexError as error:
                self.log(f"index error using scene_chooser_details(): {error}")
                return None, None, None, None
        else:
            self.log(f"thumbnails don't exist yet in scene_chooser_details()")
            return None, None, None, None

    def next_button3(self):
        with Jot() as jot:
            all_scenes = len(self.state.scene_names)
            all_frames = self.state.scene_frames("all")
            all_time = self.state.scene_frames_time(all_frames)
            keep_scenes = len(self.state.kept_scenes())
            keep_frames = self.state.scene_frames("keep")
            keep_time = self.state.scene_frames_time(keep_frames)
            drop_scenes = len(self.state.dropped_scenes())
            drop_frames = self.state.scene_frames("drop")
            drop_time = self.state.scene_frames_time(drop_frames)

            jot.down(f"SOURCE: Scenes: {all_scenes:,d} Frames: {all_frames:,d} Length: {all_time}")
            jot.down()
            jot.down(f"KEEP: Scenes: {keep_scenes:,d} Frames: {keep_frames:,d} Length: {keep_time}")
            jot.down()
            jot.down(f"DROP: Scenes: {drop_scenes:,d} Frames: {drop_frames:,d} Length: {drop_time}")
        self.state.project_info4 = jot

        # user will expect to return to the compilation tab on reopening
        self.log("saving project after displaying scene choices")
        self.state.save_progress("compile")

        return gr.update(selected=4), jot

    def next_button4(self):
        self.log("moving previously dropped scenes back to scenes directory")
        dropped_dirs = get_directories(self.state.dropped_scenes_path)
        for dir in dropped_dirs:
            current_path = os.path.join(self.state.dropped_scenes_path, dir)
            undropped_path = os.path.join(self.state.scenes_path, dir)
            self.log(f"moving directory {current_path} to {undropped_path}")
            shutil.move(current_path, undropped_path)

        self.log("moving dropped scenes to dropped scenes directory")
        dropped_scenes = self.state.dropped_scenes()
        for dir in dropped_scenes:
            current_path = os.path.join(self.state.scenes_path, dir)
            dropped_path = os.path.join(self.state.dropped_scenes_path, dir)
            self.log(f"moving directory {current_path} to {dropped_path}")
            shutil.move(current_path, dropped_path)

        # user will expect to return to the processing tab on reopening
        self.log("saving project after compiling scenes")
        self.state.save_progress("process")

        return gr.update(selected=5), gr.update(visible=True), \
            "Next: Perform all Processing Steps (takes from hours to days)"

    def next_button5(self, resynthesize, inflate, resize, upscale, upscale_option):
        self.state.resynthesize = resynthesize
        self.state.inflate = inflate
        self.state.resize = resize
        self.state.upscale = upscale
        self.state.upscale_option = upscale_option

        self.log("saving project after storing processing choices")
        self.state.save()

        jot = Jot()
        kept_scenes = self.state.kept_scenes()
        if kept_scenes:
            # need to remove anything that was created previously based on these settings
            self.log("removing processed files from previous processing choices")
            remove_directories([
                self.state.clips_path,
                self.state.resize_path,
                self.state.resynthesis_path,
                self.state.inflation_path,
                self.state.upscale_path])

            if self.state.video_details["has_audio"]:
                self.state.audio_clips_path = os.path.join(self.state.clips_path, "AUDIO")
                self.log(f"creating audio clips directory {self.state.audio_clips_path}")
                create_directory(self.state.audio_clips_path)
                global_options = self.config.ffmpeg_settings["global_options"]

                self.log(f"creating audio clips")
                edge_trim = 1 if self.state.resynthesize else 0
                SliceVideo(self.state.source_video,
                            self.state.project_fps,
                            self.state.scenes_path,
                            self.state.audio_clips_path,
                            0.0,
                            "wav",
                            0,
                            1,
                            edge_trim,
                            False,
                            0.0,
                            0.0,
                            self.log,
                            global_options=global_options).slice()
                self.state.audio_clips = sorted(get_files(self.state.audio_clips_path))
                jot.down(f"Audio clips created in {self.state.audio_clips_path}")
                self.log("saving project after creating audio clips")
                self.state.save()

            if self.state.resize:
                scenes_base_path = self.state.scenes_path
                self.state.resize_path = os.path.join(self.state.project_path, "SCENES-RC")
                self.log(f"creating resized scenes directory {self.state.resize_path}")
                create_directory(self.state.resize_path)

                self.log(f"resize processing with input_path={scenes_base_path}" +\
                        f" output_path={self.state.resize_path}")

                with Mtqdm().open_bar(total=len(kept_scenes), desc="Resize") as bar:
                    for scene_name in kept_scenes:
                        scene_input_path = os.path.join(scenes_base_path, scene_name)
                        scene_output_path = os.path.join(self.state.resize_path, scene_name)

                        self.log(f"creating output directory {scene_output_path}")
                        create_directory(scene_output_path)

                        if self.state.resize_w == self.state.video_details["content_width"] and \
                                self.state.resize_h == self.state.video_details["content_height"]:
                            scale_type = "none"
                        else:
                            scale_type = self.config.remixer_settings["scale_type"]

                        if self.state.crop_w == self.state.resize_w and \
                                self.state.crop_h == self.state.resize_h:
                            crop_type = "none"
                        else:
                            crop_type = "crop"
                        crop_offset = -1

                        self.log(f"initializing ResizeFrames with input_path={scene_input_path}" +\
                                f" output_path={scene_output_path}"+\
                                f" scale_type={scale_type}" +\
                                f" scale_width={self.state.resize_w}"+\
                                f" scale_height={self.state.resize_h}" +\
                                f" crop_type={crop_type} crop_width={self.state.crop_w}" +\
                                f" crop_height={self.state.crop_h} crop_offset_x={crop_offset}" +\
                                f" crop_offset_y={crop_offset}")
                        ResizeFrames(scene_input_path,
                                    scene_output_path,
                                    int(self.state.resize_w),
                                    int(self.state.resize_h),
                                    scale_type,
                                    self.log,
                                    crop_type=crop_type,
                                    crop_width=self.state.crop_w,
                                    crop_height=self.state.crop_h,
                                    crop_offset_x=crop_offset,
                                    crop_offset_y=crop_offset).resize()
                        Mtqdm().update_bar(bar)

                jot.down(f"Resized scenes created in {self.state.resize_path}")
                self.log("saving project after resizing frames")
                self.state.save()

            if self.state.resynthesize:
                interpolater = Interpolate(self.engine.model, self.log)
                use_time_step = self.config.engine_settings["use_time_step"]
                deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
                series_interpolater = InterpolateSeries(deep_interpolater, self.log)

                if self.state.resize:
                    scenes_base_path = self.state.resize_path
                else:
                    scenes_base_path = self.state.scenes_path

                self.state.resynthesis_path = os.path.join(self.state.project_path, "SCENES-RE")
                self.log(f"creating resynthesized scenes directory {self.state.resynthesis_path}")
                create_directory(self.state.resynthesis_path)

                self.log(f"resynthesize processing with input_path={scenes_base_path}" +\
                        f" output_path={self.state.resynthesis_path}")

                with Mtqdm().open_bar(total=len(kept_scenes), desc="Resynth") as bar:
                    for scene_name in kept_scenes:
                        scene_input_path = os.path.join(scenes_base_path, scene_name)
                        scene_output_path = os.path.join(self.state.resynthesis_path, scene_name)

                        self.log(f"creating output directory {scene_output_path}")
                        create_directory(scene_output_path)

                        output_basename = "resynthesized_frames"
                        file_list = sorted(get_files(scene_input_path, extension="png"))

                        self.log(f"beginning series of frame recreations at {scene_output_path}")
                        series_interpolater.interpolate_series(file_list,
                                                               scene_output_path,
                                                               1,
                                                               output_basename,
                                                               offset=2)

                        self.log(f"auto-resequencing recreated frames at {scene_output_path}")
                        ResequenceFiles(scene_output_path,
                                        "png",
                                        "resynthesized_frame",
                                        1,
                                        1,
                                        1,
                                        0,
                                        -1,
                                        True,
                                        self.log).resequence()
                        Mtqdm().update_bar(bar)

                jot.down(f"Resynthesized scenes created in {self.state.resynthesis_path}")
                self.log("saving project after resynthesizing frames")
                self.state.save()

            if self.state.inflate:
                interpolater = Interpolate(self.engine.model, self.log)
                use_time_step = self.config.engine_settings["use_time_step"]
                deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
                series_interpolater = InterpolateSeries(deep_interpolater, self.log)

                if self.state.resynthesize:
                    scenes_base_path = self.state.resynthesis_path
                elif self.state.resize:
                    scenes_base_path = self.state.resize_path
                else:
                    scenes_base_path = self.state.scenes_path

                self.state.inflation_path = os.path.join(self.state.project_path, "SCENES-IN")
                self.log(f"creating inflated scenes directory {self.state.inflation_path}")
                create_directory(self.state.inflation_path)

                self.log(f"inflation processing with input_path={scenes_base_path}" +\
                        f" output_path={self.state.inflation_path}")

                with Mtqdm().open_bar(total=len(kept_scenes), desc="Inflate") as bar:
                    for scene_name in kept_scenes:
                        scene_input_path = os.path.join(scenes_base_path, scene_name)
                        scene_output_path = os.path.join(self.state.inflation_path, scene_name)

                        self.log(f"creating output directory {scene_output_path}")
                        create_directory(scene_output_path)

                        output_basename = "interpolated_frames"
                        file_list = sorted(get_files(scene_input_path, extension="png"))
                        self.log(f"beginning series of deep interpolations at {scene_output_path}")
                        series_interpolater.interpolate_series(file_list, scene_output_path, 1,
                            output_basename)

                        self.log(f"auto-resequencing recreated frames at {scene_output_path}")
                        ResequenceFiles(scene_output_path,
                                        "png",
                                        "inflated_frame",
                                        1,
                                        1,
                                        1,
                                        0,
                                        -1,
                                        True,
                                        self.log).resequence()
                        Mtqdm().update_bar(bar)

                jot.down(f"Inflated scenes created in {self.state.inflation_path}")
                self.log("saving project after inflating frames")
                self.state.save()

            if self.state.upscale:
                if self.state.inflate:
                    scenes_base_path = self.state.inflation_path
                elif self.state.resynthesize:
                    scenes_base_path = self.state.resynthesis_path
                elif self.state.resize:
                    scenes_base_path = self.state.resize_path
                else:
                    scenes_base_path = self.state.scenes_path

                suffix = self.state.upscale_option
                self.state.upscale_path = os.path.join(self.state.project_path,
                                                       "SCENES-UP" + suffix)
                self.log(f"creating upscaled scenes directory {self.state.upscale_path}")
                create_directory(self.state.upscale_path)

                self.log(f"upscale processing with input_path={scenes_base_path}" +\
                        f" output_path={self.state.upscale_path}")

                model_name = self.config.realesrgan_settings["model_name"]
                gpu_ids = self.config.realesrgan_settings["gpu_ids"]
                fp32 = self.config.realesrgan_settings["fp32"]
                use_tiling = self.config.remixer_settings["use_tiling"]

                if use_tiling:
                    tiling = self.config.realesrgan_settings["tiling"]
                    tile_pad = self.config.realesrgan_settings["tile_pad"]
                else:
                    tiling = 0
                    tile_pad = 0
                upscaler = UpscaleSeries(model_name, gpu_ids, fp32, tiling, tile_pad, self.log)
                upscale_factor = 2.0 if self.state.upscale_option == "2X" else 4.0
                with Mtqdm().open_bar(total=len(kept_scenes), desc="Upscale") as bar:
                    for scene_name in kept_scenes:
                        scene_input_path = os.path.join(scenes_base_path, scene_name)
                        scene_output_path = os.path.join(self.state.upscale_path, scene_name)

                        self.log(f"creating output directory {scene_output_path}")
                        create_directory(scene_output_path)

                        file_list = sorted(get_files(scene_input_path))
                        output_basename = "upscaled_frames"

                        self.log(f"beginning series of upscaling at {scene_output_path}")
                        upscaler.upscale_series(file_list, scene_output_path, upscale_factor,
                                                            output_basename, "png")
                        Mtqdm().update_bar(bar)

                jot.down(f"Upscaled scenes created in {self.state.upscale_path}")
                self.log("saving project after upscaling frames")
                self.state.save()

            self.state.summary_info6 = jot

            _, filename, _ = split_filepath(self.state.source_video)
            output_filepath = os.path.join(self.state.project_path, f"{filename}-remixed.mp4")
            self.state.summary_info6 = jot

            # user will expect to return to the save remix tab on reopening
            self.log("saving project after completing processing steps")
            self.state.save_progress("save")

            return gr.update(selected=6), gr.update(visible=True), jot, output_filepath
        else:
            return gr.update(selected=5), \
                    gr.update(
                value="At least one scene must be set to 'Keep' before processing can proceed"), \
                    None

    def next_button6(self, output_filepath, quality):
        kept_scenes = self.state.kept_scenes()
        if output_filepath:
            if kept_scenes:
                self.state.video_clips_path = os.path.join(self.state.clips_path, "VIDEO")
                self.log(f"creating video clips directory {self.state.video_clips_path}")
                create_directory(self.state.video_clips_path)

                if self.state.upscale:
                    scenes_base_path = self.state.upscale_path
                elif self.state.inflate:
                    scenes_base_path = self.state.inflation_path
                elif self.state.resynthesize:
                    scenes_base_path = self.state.resynthesis_path
                elif self.state.resize:
                    scenes_base_path = self.state.resize_path
                else:
                    scenes_base_path = self.state.scenes_path

                self.log(f"creating processed video clips")
                video_clip_fps = \
                    2 * self.state.project_fps if self.state.inflate else self.state.project_fps

                with Mtqdm().open_bar(total=len(kept_scenes), desc="Video Clips") as bar:
                    for scene_name in kept_scenes:
                        scene_input_path = os.path.join(scenes_base_path, scene_name)
                        scene_output_filepath = os.path.join(self.state.video_clips_path,
                                                            f"{scene_name}.mp4")

                        self.log(f"about to resequence files in {scene_input_path}")
                        ResequenceFiles(scene_input_path,
                                        "png",
                                        "processed_frame",
                                        1,
                                        1,
                                        1,
                                        0,
                                        -1,
                                        True,
                                        self.log).resequence()
                        self.log(f"about to use PNGtoMP4 with input_path={scene_input_path}" +\
                                f" fps={video_clip_fps} output_filepath={scene_output_filepath}")
                        global_options = self.config.ffmpeg_settings["global_options"]
                        ffcmd = PNGtoMP4(scene_input_path, None, video_clip_fps,
                                scene_output_filepath, crf=quality, global_options=global_options)
                        self.log(f"FFMpeg command: {ffcmd}")
                        Mtqdm().update_bar(bar)

                self.state.video_clips = sorted(get_files(self.state.video_clips_path))
                # jot.down(f"Processed video clips created in {self.state.video_clips_path}")
                self.log("saving project after creating video clips")
                self.state.save()

                if self.state.video_details["has_audio"]:
                    self.log(f"merging processed video clips and audio clips")
                    with Mtqdm().open_bar(total=len(kept_scenes), desc="Merge Clips") as bar:
                        for index, scene_name in enumerate(kept_scenes):
                            scene_video_path = self.state.video_clips[index]
                            scene_audio_path = self.state.audio_clips[index]
                            scene_output_filepath = os.path.join(self.state.clips_path,
                                                                f"{scene_name}.mp4")

                            self.log(
                            f"about to use combine_video_audio with video_path={scene_video_path} " +\
                            f"audio_path={scene_audio_path} output_filepath={scene_output_filepath}")
                            global_options = self.config.ffmpeg_settings["global_options"]
                            ffcmd = combine_video_audio(scene_video_path, scene_audio_path,
                                                scene_output_filepath, global_options=global_options)
                            self.log(f"FFmpeg command {ffcmd}")
                            Mtqdm().update_bar(bar)

                if self.state.video_details["has_audio"]:
                    self.state.clips = sorted(get_files(self.state.clips_path))
                else:
                    self.state.clips = sorted(get_files(self.state.video_clips_path))
                self.log("saving project after creating merged clips")
                self.state.save()

                if self.state.clips:
                    with Mtqdm().open_bar(total=1, desc="Remixing Video") as bar:
                        Mtqdm().message(bar, "FFmpeg in use ...")
                        self.log(f"about to use combine_videos with output_path={output_filepath} " +\
                                f"and input_paths={self.state.clips}")
                        global_options = self.config.ffmpeg_settings["global_options"]
                        ffcmd = combine_videos(self.state.clips, output_filepath,
                                               global_options=global_options)
                        self.log(f"FFmpeg command {ffcmd}")
                        Mtqdm().update_bar(bar)

                    return gr.update(value=f"Remixed video {output_filepath} is complete.",
                                        visible=True)
            else:
                return gr.update(value="No processed video clips were found", visible=True)
        else:
            return gr.update(value="Enter a path for the remixed video to proceed", visible=True)
