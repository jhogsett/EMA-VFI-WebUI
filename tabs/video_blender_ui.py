"""Video Blender feature UI and event handlers"""
import os
import shutil
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.image_utils import create_gif
from webui_utils.file_utils import get_files, create_directory, locate_frame_file, \
    duplicate_directory
from webui_utils.auto_increment import AutoIncrementDirectory, AutoIncrementFilename
from webui_utils.video_utils import PNGtoMP4, QUALITY_SMALLER_SIZE, MP4toPNG
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from interpolate import Interpolate
from interpolation_target import TargetInterpolate
from deep_interpolate import DeepInterpolate
from interpolate_series import InterpolateSeries
from resequence_files import ResequenceFiles
from restore_frames import RestoreFrames
from video_blender import VideoBlenderState, VideoBlenderProjects
from tabs.tab_base import TabBase
from simplify_png_files import SimplifyPngFiles

class VideoBlender(TabBase):
    """Encapsulates UI elements and events for the Video Blender Feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.video_blender_state = None
        self.video_blender_projects = VideoBlenderProjects(
            self.config.blender_settings["projects_file"])
        self.video_blender_tabs = None
        self.new_project_name = None
        self.new_project_path = None
        self.new_project_frame_rate = None
        self.step1_enabled = None
        self.step1_input = None
        self.step2_enabled = None
        self.step2_input = None
        self.step3_enabled = None
        self.step3_input = None
        self.step4_enabled = None

    TAB_PROJECT_SETTINGS = 0
    TAB_FRAME_CHOOSER = 1
    TAB_FRAME_FIXER = 2
    TAB_VIDEO_PREVIEW = 3
    TAB_NEW_PROJECT = 4
    TAB_RESET_PROJECT = 5

    def render_tab(self):
        """Render tab into UI"""
        skip_frames = self.config.blender_settings["skip_frames"]
        frame_rate = self.config.blender_settings["frame_rate"]
        max_frame_rate = self.config.blender_settings["max_frame_rate"]
        # with gr.Tab("Video Blender"):
        with gr.Tabs() as tabs_video_blender:
            self.video_blender_tabs = tabs_video_blender

            ### PROJECT SETTINGS
            with gr.Tab(SimpleIcons.NOTEBOOK + "Project Settings", id=self.TAB_PROJECT_SETTINGS):
                with gr.Row():
                    with gr.Column(scale=3, variant="compact"):
                        with gr.Row():
                            input_project_name = gr.Textbox(label="Project Name", max_lines=1)
                    with gr.Column(scale=3, variant="compact", elem_id="mainhighlightdim"):
                        with gr.Row():
                            choices = self.video_blender_projects.get_project_names()
                            projects_dropdown = gr.Dropdown(label=SimpleIcons.PROP_SYMBOL +
                                " Saved Projects", choices=choices, value=choices[0])
                            save_project_button = gr.Button(SimpleIcons.PROP_SYMBOL +
                                " Save", scale=0)
                with gr.Row():
                    input_main_path = gr.Textbox(label="Project Main Path", max_lines=1,
                                                    placeholder="Root path for the project")
                    input_project_frame_rate = gr.Slider(value=frame_rate, minimum=1,
                                        maximum=max_frame_rate, step=0.01, label="Frame Rate")
                with gr.Row():
                    input_project_path = gr.Textbox(label="Project Frames Path", max_lines=1,
                        placeholder="Path to frame PNG files for video being restored")
                with gr.Row():
                    input_path1 = gr.Textbox(label="Original / Video #1 Frames Path",
                                max_lines=1, placeholder="Path to original or video #1 PNG files")
                with gr.Row():
                    input_path2 = gr.Textbox(label="Alternate / Video #2 Frames Path",
                                max_lines=1, placeholder="Path to alternate or video #2 PNG files")
                load_button = gr.Button("Open Video Blender Project " +
                    SimpleIcons.ROCKET, variant="primary")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_blender_project_settings.render()

            ### FRAME CHOOSER
            with gr.Tab(SimpleIcons.CONTROLS + "Frame Chooser", id=self.TAB_FRAME_CHOOSER):
                with gr.Row():
                    with gr.Column():
                        output_prev_frame = gr.Image(sources=["upload"], label="Previous Frame",
                            interactive=False, type="filepath", elem_id="sideimage", height=300)
                    with gr.Column():
                        output_curr_frame = gr.Image(sources=["upload"], show_label=False,
                            interactive=False, type="filepath", elem_id="actionimage", height=300)
                    with gr.Column():
                        output_next_frame = gr.Image(sources=["upload"], label="Next Frame",
                            interactive=False, type="filepath", elem_id="sideimage", height=300)
                with gr.Row():
                    with gr.Column():
                        gr.Row()
                        with gr.Row(variant="panel", elem_id="highlightbutton"):
                            fix_frames_count = gr.Number(label="FIX ADJACENT DAMAGED FRAMES: " +
                                SimpleIcons.ONE + " Go to the first damaged frame " +
                                SimpleIcons.TWO + " Set count of damaged frames " +
                                SimpleIcons.THREE + " Click Go To Frame Fixer", value=0,
                                precision=0)
                            with gr.Row():
                                fix_frames_last_before = gr.Number(
                                    label="Last Frame Before Damage", value=0, precision=0,
                                    interactive=False)
                                fix_frames_first_after = gr.Number(
                                    label="First Frame After Damage", value=0, precision=0,
                                    interactive=False)
                            fix_frames_button = gr.Button("Go To " + SimpleIcons.HAMMER
                                                                + " Frame Fixer")
                        with gr.Row():
                            preview_video = gr.Button("Go To "  + SimpleIcons.TELEVISION
                                                            + " Video Preview")

                    with gr.Column():
                        with gr.Tabs():
                            with gr.Tab(label="Repair / Path 2 Frame"):
                                output_img_path2 = gr.Image(sources=["upload"], show_label=False,
                                    interactive=False, type="filepath", height=300)
                            with gr.Tab(label="Original / Path 1 Frame"):
                                output_img_path1 = gr.Image(sources=["upload"], show_label=False,
                                    interactive=False, type="filepath", height=300)

                    with gr.Column():
                        gr.Row()
                        use_path_1_button = gr.Button("Use Path 1 Frame | Next >",
                            variant="primary", elem_id="actionbutton")
                        use_path_2_button = gr.Button("Use Path 2 Frame | Next >",
                            variant="primary", elem_id="actionbutton")
                        with gr.Row():
                            prev_frame_button = gr.Button("< Prev Frame",
                                variant="primary")
                            next_frame_button = gr.Button("Next Frame >",
                                variant="primary")
                        with gr.Row():
                            prev_xframes_button = gr.Button(f"<< {skip_frames}")
                            next_xframes_button = gr.Button(f"{skip_frames} >>")
                        input_text_frame = gr.Number(value=0, precision=0,
                            label="Frame Number")

                if self.config.user_interface["show_header"]:
                    with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                        WebuiTips.video_blender_frame_chooser.render()

            ### FRAME FIXER
            with gr.Tab(SimpleIcons.HAMMER + "Frame Fixer", id=self.TAB_FRAME_FIXER):
                with gr.Row():
                    with gr.Column():
                        with gr.Row():
                            project_path_ff = gr.Textbox(label="Video Blender Project Path",
                                                        max_lines=1,
                                                        placeholder="Path to video frame PNG files")
                        with gr.Row():
                            input_clean_before_ff = gr.Number(
                                label="Last clean frame BEFORE damaged ones", value=0,
                                precision=0)
                            input_clean_after_ff = gr.Number(
                                label="First clean frame AFTER damaged ones", value=0,
                                precision=0)
                        with gr.Row():
                            preview_button_ff = gr.Button(value="Preview Fixed Frames",
                                variant="primary", elem_id="highlightbutton")
                    with gr.Column():
                        preview_image_ff = gr.Image(sources=["upload"], type="filepath",
                            label="Fixed Frames Preview", interactive=False,
                            elem_id="highlightoutput", height=300)
                        fixed_path_ff = gr.Textbox(label="Path to Restored Frames", max_lines=1,
                                                   interactive=False)
                        use_fixed_button_ff = gr.Button(value="Apply Fixed Frames",
                            elem_id="actionbutton")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_blender_frame_fixer.render()

            ### VIDEO PREVIEW
            with gr.Tab(SimpleIcons.TELEVISION + "Video Preview", id=self.TAB_VIDEO_PREVIEW):
                with gr.Row():
                    gr.Column(scale=1)
                    with gr.Column():
                        video_preview = gr.Video(label="Preview", interactive=False,
                            include_audio=False, width=800, container=True, scale=8)
                    gr.Column(scale=1)
                preview_path = gr.Textbox(label="Path to PNG Sequence", max_lines=1,
                    placeholder="Path on this server to the PNG files to be converted")
                with gr.Row():
                    render_video = gr.Button("Render Video", variant="primary")
                    input_frame_rate = gr.Slider(value=frame_rate, minimum=1,
                                        maximum=max_frame_rate, step=0.01, label="Frame Rate")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_blender_video_preview.render()

            ### NEW PROJECT
            with gr.Tab(SimpleIcons.SEEDLING + "New Project", id=self.TAB_NEW_PROJECT):
                with gr.Row():
                    with gr.Column(variant="compact"):
                        gr.HTML("Define New Project")
                        with gr.Row(variant="panel"):
                            with gr.Column(scale=1):
                                new_project_name = gr.Textbox(label="New Project Name", max_lines=1,
                                    placeholder="Name for the new project")
                            with gr.Column(scale=12):
                                new_project_path = gr.Textbox(label="New Project Path", max_lines=1,
                                    placeholder="Path on this server for the new project")
                            with gr.Column(scale=1):
                                new_project_frame_rate = gr.Slider(value=frame_rate, minimum=1,
                                        maximum=max_frame_rate, step=0.01, label="Frame Rate")
                with gr.Row():
                    with gr.Column(variant="compact"):
                        gr.HTML("Check Applicable Setup Steps")
                        with gr.Row(variant="panel"):
                            with gr.Column(scale=1):
                                step1_enabled = gr.Checkbox(value=True,
                                            label=SimpleIcons.ONE + " Split MP4 to PNG Frames Set")
                            with gr.Column(scale=12):
                                with gr.Row():
                                    step1_input = gr.Textbox(label="MP4 Path", max_lines=1,
                                        interactive=True,
                                        placeholder="Path on this server to the source MP4 file")
                        with gr.Row(variant="panel"):
                            with gr.Column(scale=1):
                                step2_enabled = gr.Checkbox(value=True,
                                        label=SimpleIcons.TWO + " Resynthesize Repair Frames Set")
                            with gr.Column(scale=12):
                                step2_input = gr.Textbox(label="n/a", max_lines=1,
                                    interactive=False,
                                    placeholder="Repair frames set will be automatically created")
                        with gr.Row(variant="panel"):
                            with gr.Column(scale=1):
                                step3_enabled = gr.Checkbox(value=True,
                                        label=SimpleIcons.THREE + " Init Restored Set from Source")
                            with gr.Column(scale=12):
                                step3_input = gr.Textbox(label="n/a", max_lines=1,
                                    interactive=False,
                                    placeholder="Restored frames set will be automatically created")
                        with gr.Row(variant="panel"):
                            with gr.Column(scale=1):
                                step4_enabled = gr.Checkbox(value=True,
                                        label=SimpleIcons.FOUR + " Sync Frame Numbers Across Sets")
                            with gr.Column(scale=12):
                                gr.Textbox(visible=False, max_lines=1)
                gr.Markdown("*Progress can be tracked in the console*")
                new_project_button = gr.Button("Create New Project " + SimpleIcons.SLOW_SYMBOL,
                                                variant="primary")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_blender_new_project.render()

            ### RESET PROJECT
            with gr.Tab(SimpleIcons.RECYCLE + "Reset Project", id=self.TAB_RESET_PROJECT):
                with gr.Row():
                    choices = self.video_blender_projects.get_project_names()
                    reset_project_dropdown = gr.Dropdown(label=SimpleIcons.PROP_SYMBOL +
                        " Projects", choices=choices, value=choices[0])
                gr.Markdown(
            "*Reset Project uses the New Project tab to selectively revert parts of a project*")
                with gr.Row():
                    reset_project_button = gr.Button("Reset Project", variant="primary")
                with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                    WebuiTips.video_blender_reset_project.render()

        projects_dropdown.change(self.video_blender_choose_project,
            inputs=[projects_dropdown],
            outputs=[input_project_name, input_project_path, input_path1,
                input_path2, input_main_path, input_project_frame_rate],
            show_progress=False)

        save_project_button.click(self.video_blender_save_project,
            inputs=[input_project_name, input_project_path, input_path1, input_path2,
                    input_main_path, input_project_frame_rate],
            outputs=[projects_dropdown, reset_project_dropdown],
            show_progress=False)

        load_button.click(self.video_blender_load,
            inputs=[input_project_path, input_path1, input_path2, input_main_path,
                input_project_frame_rate],
            outputs=[tabs_video_blender, input_text_frame, output_img_path1,
                output_prev_frame, output_curr_frame, output_next_frame,
                output_img_path2, fix_frames_count],
            show_progress=False)

        prev_frame_button.click(self.video_blender_prev_frame,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        next_frame_button.click(self.video_blender_next_frame,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        input_text_frame.submit(self.video_blender_goto_frame,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        input_text_frame.change(self.video_blender_goto_frame2,
            inputs=[input_text_frame],
            outputs=[output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        use_path_1_button.click(self.video_blender_use_path1,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        use_path_2_button.click(self.video_blender_use_path2,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        prev_xframes_button.click(self.video_blender_skip_prev,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        next_xframes_button.click(self.video_blender_skip_next,
            inputs=[input_text_frame],
            outputs=[input_text_frame, output_img_path1, output_prev_frame,
                output_curr_frame, output_next_frame, output_img_path2, fix_frames_count],
            show_progress=False)

        preview_video.click(self.video_blender_preview_video,
            inputs=input_project_path, outputs=[tabs_video_blender, preview_path])

        fix_frames_count.change(self.video_blender_compute_fix_frames,
                                inputs=[input_text_frame, fix_frames_count],
                                outputs=[fix_frames_last_before, fix_frames_first_after,
                                         fix_frames_count],
                                show_progress=False)

        fix_frames_button.click(self.video_blender_fix_frames,
            inputs=[input_project_path, fix_frames_count, fix_frames_last_before,
                    fix_frames_first_after],
            outputs=[tabs_video_blender, project_path_ff, input_clean_before_ff,
                input_clean_after_ff, fixed_path_ff])

        preview_button_ff.click(self.video_blender_preview_fixed,
            inputs=[project_path_ff, input_clean_before_ff, input_clean_after_ff],
            outputs=[preview_image_ff, fixed_path_ff])

        use_fixed_button_ff.click(self.video_blender_use_fixed,
            inputs=[project_path_ff, fixed_path_ff, input_clean_before_ff],
            outputs=[tabs_video_blender, fixed_path_ff, input_text_frame, output_img_path1,
                output_prev_frame,output_curr_frame, output_next_frame,
                output_img_path2, fix_frames_count, preview_image_ff, fixed_path_ff])

        render_video.click(self.video_blender_render_preview,
            inputs=[preview_path, input_frame_rate], outputs=[video_preview])

        step1_enabled.change(self.video_blender_new_project_ui_switch_1,
            inputs=[step1_enabled, step2_enabled, step3_enabled, step4_enabled],
            outputs=[step1_input, step2_input, step3_input], show_progress=False)

        step2_enabled.change(self.video_blender_new_project_ui_switch_2,
            inputs=[step1_enabled, step2_enabled, step3_enabled, step4_enabled],
            outputs=[step1_input, step2_input, step3_input], show_progress=False)

        step3_enabled.change(self.video_blender_new_project_ui_switch_3,
            inputs=[step1_enabled, step2_enabled, step3_enabled, step4_enabled],
            outputs=[step1_input, step2_input, step3_input], show_progress=False)

        new_project_button.click(self.video_blender_new_project,
            inputs=[new_project_name, new_project_path, step1_enabled, step2_enabled, step3_enabled,
                step4_enabled, step1_input, step2_input, step3_input, new_project_frame_rate],
            outputs=[projects_dropdown, reset_project_dropdown], show_progress=False)

        reset_project_button.click(self.video_blender_reset_project,
            inputs=reset_project_dropdown,
            outputs=[tabs_video_blender, new_project_name, new_project_path, step1_enabled,
                step1_input, step2_enabled, step2_input, step3_enabled, step3_input, step4_enabled,
                new_project_frame_rate],
            show_progress=False)

        self.video_blender_tabs = tabs_video_blender
        self.new_project_name = new_project_name
        self.new_project_path = new_project_path
        self.new_project_frame_rate = new_project_frame_rate
        self.step1_enabled = step1_enabled
        self.step1_input = step1_input
        self.step2_enabled = step2_enabled
        self.step2_input = step2_input
        self.step3_enabled = step3_enabled
        self.step3_input = step3_input
        self.step4_enabled = step4_enabled

    def video_blender_load(self, project_path, frames_path1, frames_path2, main_path, fps):
        """Open Project button handler"""
        self.video_blender_state = VideoBlenderState(project_path, frames_path1, frames_path2,
                                                     main_path, fps)
        return gr.update(selected=1), 0, *self.video_blender_state.goto_frame(0), 0

    def video_blender_save_project(self,
                                    project_name : str,
                                    project_path : str,
                                    frames1_path : str,
                                    frames2_path : str,
                                    main_path : str,
                                    fps : str):
        """Save Project button handler"""
        self.video_blender_projects.save_project(project_name, project_path, frames1_path,
            frames2_path, main_path, fps)
        return gr.update(choices=self.video_blender_projects.get_project_names(),
                         value=project_name), \
                gr.update(choices=self.video_blender_projects.get_project_names())

    def video_blender_choose_project(self, project_name):
        """Load Project button handler"""
        if project_name:
            dictobj = self.video_blender_projects.load_project(project_name)
            if dictobj:
                return dictobj["project_name"], \
                    dictobj["project_path"], \
                    dictobj["frames1_path"], \
                    dictobj["frames2_path"], \
                    dictobj["main_path"], \
                    dictobj["fps"]
        return

    def video_blender_prev_frame(self, frame : str):
        "Previous Frame button handler"
        frame = int(frame)
        frame -= 1
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_next_frame(self, frame : str):
        """Next Frame button handler"""
        frame = int(frame)
        frame += 1
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_goto_frame(self, frame : str):
        """Go button handler"""
        frame = int(frame)
        frame = 0 if frame < 0 else frame
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_goto_frame2(self, frame : str):
        """Frame count change handler"""
        frame = int(frame)
        frame = 0 if frame < 0 else frame
        return *self.video_blender_state.goto_frame(frame), 0

    def video_blender_skip_next(self, frame : str):
        """Skip Next button handler"""
        frame = int(frame) + int(self.config.blender_settings["skip_frames"])
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_skip_prev(self, frame : str):
        """Skip Previous button handler"""
        frame = int(frame) - int(self.config.blender_settings["skip_frames"])
        frame = 0 if frame < 0 else frame
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_use_path1(self, frame : str):
        """Use Path 1 Frame button handler"""
        frame = int(frame)
        to_filepath = self.video_blender_state.get_frame_file(VideoBlenderState.PROJECT_PATH,
            frame)
        from_filepath = self.video_blender_state.get_frame_file(VideoBlenderState.FRAMES1_PATH,
            frame)
        self.log(f"copying {from_filepath} to {to_filepath}")
        shutil.copy(from_filepath, to_filepath)
        description = f"source_file: {from_filepath}"
        self.video_blender_state.record_event(VideoBlenderState.EVENT_TYPE_USE_PATH1_FRAME, frame,
                                              frame, description)
        frame += 1
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_use_path2(self, frame : str):
        """Use Path 2 Frame button handler"""
        frame = int(frame)
        to_filepath = self.video_blender_state.get_frame_file(VideoBlenderState.PROJECT_PATH,
            frame)
        from_filepath = self.video_blender_state.get_frame_file(VideoBlenderState.FRAMES2_PATH,
            frame)
        self.log(f"copying {from_filepath} to {to_filepath}")
        shutil.copy(from_filepath, to_filepath)
        description = f"source_file: {from_filepath}"
        self.video_blender_state.record_event(VideoBlenderState.EVENT_TYPE_USE_PATH2_FRAME, frame,
                                              frame, description)
        frame += 1
        return frame, *self.video_blender_state.goto_frame(frame), 0

    def video_blender_compute_fix_frames(self, frame : str, damage_count : str):
        if damage_count > 0:
            last_clean_before = frame - 1
            if last_clean_before < 0:
                last_clean_before += (-last_clean_before)
            first_clean_after = last_clean_before + damage_count + 1
            return last_clean_before, first_clean_after, damage_count
        return 0, 0, 0

    def video_blender_fix_frames(self, project_path : str, damage_count: int,
                                 last_frame_before : int, first_frame_after : int):
        """Fix Frames button handler"""
        if damage_count > 0:
            return gr.update(selected=2), project_path, last_frame_before, first_frame_after, None
        return gr.update(selected=1), None, 0, 0, None

    def video_blender_preview_fixed(self,
                                    project_path : str,
                                    before_frame : int,
                                    after_frame : int):
        """Preview Fixed Frames button handler"""
        if project_path and after_frame > before_frame:
            interpolater = Interpolate(self.engine.model, self.log)
            target_interpolater = TargetInterpolate(interpolater, self.log)
            use_time_step = self.config.engine_settings["use_time_step"]
            frame_restorer = RestoreFrames(interpolater, target_interpolater, use_time_step,
                                           self.log)

            base_output_path = os.path.join(self.video_blender_state.main_path, "frame_fixer")
            create_directory(base_output_path)
            output_path, run_index = AutoIncrementDirectory(base_output_path).next_directory("run")
            output_basename = "fixed_frames"

            before_file = locate_frame_file(project_path, before_frame)
            after_file = locate_frame_file(project_path, after_frame)
            num_frames = (after_frame - before_frame) - 1
            search_depth = int(self.config.blender_settings["frame_fixer_depth"])

            self.log(f"beginning frame fixes at {output_path}")
            frame_restorer.restore_frames(before_file, after_file, num_frames, search_depth,
                output_path, output_basename)
            output_paths = frame_restorer.output_paths

            preview_gif = os.path.join(output_path, output_basename + str(run_index) + ".gif")
            self.log(f"creating preview file {preview_gif}")
            duration = self.config.blender_settings["gif_duration"] / len(output_paths)
            create_gif(output_paths, preview_gif, duration=duration)

            return gr.Image.update(value=preview_gif), gr.Text.update(value=output_path,
                visible=True)

    def video_blender_use_fixed(self,
                                project_path : str,
                                fixed_frames_path : str,
                                before_frame : int):
        """Apply Fixed Frames button handler"""
        if fixed_frames_path:
            fixed_frames = sorted(get_files(fixed_frames_path, "png"))
            frame = before_frame + 1
            for file in fixed_frames:
                project_file = locate_frame_file(project_path, frame)
                self.log(f"copying {file} to {project_file}")
                shutil.copy(file, project_file)
                frame += 1
            first_frame = before_frame + 1
            last_frame = before_frame + len(fixed_frames)
            description = f"source_path: {fixed_frames_path}"
            self.video_blender_state.record_event(VideoBlenderState.EVENT_TYPE_APPLY_FIXED_FRAMES,
                                                  first_frame, last_frame, description)
            return gr.update(selected=1), None, before_frame + 1, \
                *self.video_blender_state.goto_frame(before_frame + 1), 0, None, None
        return gr.update(selected=2), None, before_frame + 1, \
            *self.video_blender_state.goto_frame(before_frame + 1), 0, None, None

    def video_blender_preview_video(self, input_path : str):
        """Preview Video button handler"""
        return gr.update(selected=3), input_path

    def video_blender_render_preview(self, input_path : str, frame_rate : int):
        """Render Video button handler"""
        if input_path:
            output_filepath, _ = AutoIncrementFilename(self.config.directories["working"],
                "mp4").next_filename("video_preview", "mp4")
            global_options = self.config.ffmpeg_settings["global_options"]
            PNGtoMP4(input_path, None, float(frame_rate), output_filepath,
                crf=QUALITY_SMALLER_SIZE, global_options=global_options)
            return output_filepath

    def video_blender_new_project_ui_switch_1(self,
                                            step1_enabled,
                                            step2_enabled,
                                            step3_enabled,
                                            step4_enabled):
        return self.video_blender_new_project_ui_switch_shared(step1_enabled,
                                                               step2_enabled,
                                                               step3_enabled,
                                                               step4_enabled)
    def video_blender_new_project_ui_switch_2(self,
                                            step1_enabled,
                                            step2_enabled,
                                            step3_enabled,
                                            step4_enabled):
        return self.video_blender_new_project_ui_switch_shared(step1_enabled,
                                                               step2_enabled,
                                                               step3_enabled,
                                                               step4_enabled)
    def video_blender_new_project_ui_switch_3(self,
                                            step1_enabled,
                                            step2_enabled,
                                            step3_enabled,
                                            step4_enabled):
        return self.video_blender_new_project_ui_switch_shared(step1_enabled,
                                                               step2_enabled,
                                                               step3_enabled,
                                                               step4_enabled)

    def video_blender_new_project_ui_switch_shared(self,
                                            step1_enabled,
                                            step2_enabled,
                                            step3_enabled,
                                            step4_enabled):
        step1_path_enabled_mp4 = step1_enabled
        step1_path_enabled_png = not step1_enabled
        step2_path_enabled = not step2_enabled
        step3_path_enabled = not step3_enabled
        _ = step4_enabled

        step1_path_label = "MP4 Path" if step1_path_enabled_mp4 else "Source Frames Path"
        step1_path_placeholder = "Path on this server to the source MP4 file"\
            if step1_path_enabled_mp4 else "Path on this server to the source PNG frame files"

        step2_path_label = "Repair Frames Path" if step2_path_enabled else "n/a"
        step2_path_placeholder = "Path on this server to the repair frames"\
            if step2_path_enabled else "Repair frames set will be automatically created"

        step3_path_label = "Project Frames Path" if step3_path_enabled else "n/a"
        step3_path_placeholder = "Path on this server to the project restored frames"\
            if step3_path_enabled else "Restored frames set will be automatically created"

        return gr.update(interactive=step1_path_enabled_mp4 or step1_path_enabled_png,
                         label=step1_path_label, placeholder=step1_path_placeholder),\
            gr.update(interactive=step2_path_enabled, label=step2_path_label,
                      placeholder=step2_path_placeholder),\
            gr.update(interactive=step3_path_enabled, label=step3_path_label,
                      placeholder=step3_path_placeholder)

    def video_blender_new_project_can_proceed(self,
                                              new_project_name,
                                              new_project_path,
                                              step1_enabled,
                                              step2_enabled,
                                              step3_enabled,
                                              step4_enabled,
                                              step1_path,
                                              step2_path,
                                              step3_path):

        basic_can_proceed = new_project_name and new_project_path
        step1_can_proceed = True if step1_path else False
        step2_can_proceed = step2_enabled or step2_path
        step3_can_proceed = step3_enabled or step3_path
        step4_can_proceed = True
        can_proceed = [basic_can_proceed, step1_can_proceed, step2_can_proceed, step3_can_proceed,
                       step4_can_proceed]
        return any(can_proceed) and all(can_proceed)

    def video_blender_new_project(self,
                                  new_project_name,
                                  new_project_path,
                                  step1_enabled,
                                  step2_enabled,
                                  step3_enabled,
                                  step4_enabled,
                                  step1_path,
                                  step2_path,
                                  step3_path,
                                  step1_frame_rate):
        if self.video_blender_new_project_can_proceed(new_project_name, new_project_path,
                step1_enabled, step2_enabled, step3_enabled, step4_enabled, step1_path, step2_path,
                step3_path):

            self.log(f"creating project base directory {new_project_path}")
            create_directory(new_project_path)

            if step1_enabled:
                source_frames_path = os.path.join(new_project_path, "SOURCE")
                self.log(f"creating source frames directory {source_frames_path}")
                create_directory(source_frames_path)
            else:
                source_frames_path = step1_path
                self.log(f"using custom source frames directory {source_frames_path}")

            if step2_enabled:
                resynth_frames_path = os.path.join(new_project_path, "RESYNTH")
                self.log(f"creating repair frames directory {resynth_frames_path}")
                create_directory(resynth_frames_path)
            else:
                resynth_frames_path = step2_path
                self.log(f"using custom repair frames directory {resynth_frames_path}")

            if step3_enabled:
                restored_frames_path = os.path.join(new_project_path, "RESTORED")
                self.log(f"creating restored frames directory {restored_frames_path}")
                create_directory(restored_frames_path)
            else:
                restored_frames_path = step3_path
                self.log(f"using custom restored frames directory {restored_frames_path}")

            if step1_enabled:
                output_pattern = "source_frame%09d.png"
                self.log(f"using FFmpeg to create PNG frames from input video {step1_path}")
                deinterlace = False # TODO
                global_options = self.config.ffmpeg_settings["global_options"]
                ffmpeg_cmd = MP4toPNG(step1_path, output_pattern, float(step1_frame_rate),
                        source_frames_path, deinterlace=deinterlace, global_options=global_options)
                self.log(ffmpeg_cmd)
            else:
                self.log(f"skipping creating PNG frames, using frames from {source_frames_path}")

            if step2_enabled:
                interpolater = Interpolate(self.engine.model, self.log)
                use_time_step = self.config.engine_settings["use_time_step"]
                deep_interpolater = DeepInterpolate(interpolater, use_time_step, self.log)
                series_interpolater = InterpolateSeries(deep_interpolater, self.log)
                output_basename = "repair_frame"
                file_list = get_files(source_frames_path, extension="png")
                self.log(f"beginning series of frame recreations at {resynth_frames_path}")
                series_interpolater.interpolate_series(file_list, resynth_frames_path, 1,
                                                       output_basename, offset=2)
                self.log(f"auto-resequencing recreated frames at {resynth_frames_path}")
                ResequenceFiles(resynth_frames_path, "png", "repair_frame", 1, 1, 1, 0, -1, True,
                    self.log).resequence()
            else:
                self.log(
                    f"skipping creating repair frames, using frames from {resynth_frames_path}")

            if step2_enabled:
                # If repair frames were synthesized, there are now two extra frames in the
                # source set not present in the repair set: the outermost frames.
                # Copy the first and last frames from the source set to the repair set
                # to keep frames aligned
                source_files = sorted(get_files(source_frames_path, "png"))
                num_files = len(source_files)
                lower_outer_frame = source_files[0]
                upper_outer_frame = source_files[-1]
                num_width = len(str(num_files))
                lower_frame = 0
                upper_frame = num_files
                lower_filename = f"repair_frame{str(lower_frame).zfill(num_width)}.png"
                upper_filename = f"repair_frame{str(upper_frame).zfill(num_width)}.png"
                lower_filepath = os.path.join(resynth_frames_path, lower_filename)
                upper_filepath = os.path.join(resynth_frames_path, upper_filename)
                self.log(
            f"duplicating source frame {lower_outer_frame} to {lower_filepath} for frame syncing")
                shutil.copy(lower_outer_frame, lower_filepath)
                self.log(
            f"duplicating source frame {upper_outer_frame} to {upper_filepath} for frame syncing")
                shutil.copy(upper_outer_frame, upper_filepath)

            if self.config.blender_settings["clean_frames"]:
                self.log(f"cleaning source files in {source_frames_path}")
                SimplifyPngFiles(source_frames_path, self.log).simplify()

                self.log(f"cleaning resynthesized files in {resynth_frames_path}")
                SimplifyPngFiles(resynth_frames_path, self.log).simplify()

            if step3_enabled:
                self.log(
                f"duplicating source frames from {source_frames_path} to {restored_frames_path}")
                duplicate_directory(source_frames_path, restored_frames_path)
            else:
                self.log(
                f"skipping creation of restored frames, using frames from {restored_frames_path}")

            if step4_enabled:
                self.log("synchronizing frame sets")

                self.log(f"resequencing source files in {source_frames_path}")
                ResequenceFiles(source_frames_path, "png", "source_frame", 0, 1, 1, 0, -1, True,
                    self.log).resequence()

                self.log(f"resequencing restored files in {restored_frames_path}")
                ResequenceFiles(restored_frames_path, "png", "source_frame", 0, 1, 1, 0, -1, True,
                    self.log).resequence()

                self.log(f"resequencing resynthesized files in {resynth_frames_path}")
                ResequenceFiles(resynth_frames_path, "png", "repair_frame", 0, 1, 1, 0, -1, True,
                    self.log).resequence()
            else:
                self.log("skipping synchronization of frame sets")

            self.log(f"saving new project {new_project_name}")
            self.video_blender_projects.save_project(new_project_name, restored_frames_path,
                                                     source_frames_path, resynth_frames_path,
                                                     new_project_path, step1_frame_rate)

        return gr.update(choices=self.video_blender_projects.get_project_names()), \
            gr.update(choices=self.video_blender_projects.get_project_names())

    def video_blender_reset_project(self, project_name : str):
        if project_name:
            dictobj = self.video_blender_projects.load_project(project_name)
            if dictobj:
                return gr.update(selected=4), \
                    dictobj["project_name"], \
                    dictobj["main_path"], \
                    False, \
                    dictobj["frames1_path"], \
                    False, \
                    dictobj["frames2_path"], \
                    True, \
                    dictobj["project_path"], \
                    True, \
                    dictobj["fps"]
