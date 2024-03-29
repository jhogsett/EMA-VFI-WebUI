"""Create Gradio markdown elements for guide markdown documents"""
import os
import gradio as gr

class WebuiTips:
    """Encapsulate logic to turn .md docs into Gradio markdown"""
    tips_path = "./guide"

    @classmethod
    def set_tips_path(cls, tips_path : str):
        """Point to the location of the tips directory"""
        cls.tips_path = tips_path

    @staticmethod
    def load_markdown(path : str, name : str):
        """Load a .md file and return it"""
        filepath = os.path.join(path, name + ".md")
        markdown = ""
        with open(filepath, encoding="utf-8") as file:
            markdown = file.read()
        return markdown

    frame_interpolation = gr.Markdown(load_markdown(tips_path, "frame_interpolation"))
    frame_search = gr.Markdown(load_markdown(tips_path, "frame_search"))
    video_inflation = gr.Markdown(load_markdown(tips_path, "video_inflation"))
    resynthesize_video = gr.Markdown(load_markdown(tips_path, "resynthesize_video"))
    frame_restoration = gr.Markdown(load_markdown(tips_path, "frame_restoration"))
    video_blender_project_settings = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_project_settings"))
    video_blender_frame_chooser = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_frame_chooser"))
    video_blender_frame_fixer = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_frame_fixer"))
    video_blender_video_preview = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_video_preview"))
    video_blender_new_project = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_new_project"))
    video_blender_reset_project = gr.Markdown(load_markdown(
        tips_path,
        "video_blender_reset_project"))
    mp4_to_png = gr.Markdown(load_markdown(tips_path, "mp4_to_png"))
    png_to_mp4 = gr.Markdown(load_markdown(tips_path, "png_to_mp4"))
    gif_to_png = gr.Markdown(load_markdown(tips_path, "gif_to_png"))
    png_to_gif = gr.Markdown(load_markdown(tips_path, "png_to_gif"))
    resequence_files = gr.Markdown(load_markdown(tips_path, "resequence_files"))
    change_fps = gr.Markdown(load_markdown(tips_path, "change_fps"))
    gif_to_mp4 = gr.Markdown(load_markdown(tips_path, "gif_to_mp4"))
    upscale_frames = gr.Markdown(load_markdown(tips_path, "upscale_frames"))
    simplify_png_files = gr.Markdown(load_markdown(tips_path, "simplify_png_files"))
    deduplicate_frames = gr.Markdown(load_markdown(tips_path, "deduplicate_frames"))
    resize_frames = gr.Markdown(load_markdown(tips_path, "resize_frames"))
    duplicates_report = gr.Markdown(load_markdown(tips_path, "duplicates_report"))
    autofill_duplicates = gr.Markdown(load_markdown(tips_path, "autofill_duplicates"))
    video_details = gr.Markdown(load_markdown(tips_path, "video_details"))
    split_frames = gr.Markdown(load_markdown(tips_path, "split_frames"))
    merge_frames = gr.Markdown(load_markdown(tips_path, "merge_frames"))
    deduplicate_tuning = gr.Markdown(load_markdown(tips_path, "deduplicate_tuning"))
    split_scenes = gr.Markdown(load_markdown(tips_path, "split_scenes"))
    slice_video = gr.Markdown(load_markdown(tips_path, "slice_video"))
    strip_scenes = gr.Markdown(load_markdown(tips_path, "strip_scenes"))
    video_remixer_home = gr.Markdown(load_markdown(tips_path, "video_remixer_home"))
    video_remixer_settings = gr.Markdown(load_markdown(tips_path, "video_remixer_settings"))
    video_remixer_setup = gr.Markdown(load_markdown(tips_path, "video_remixer_setup"))
    video_remixer_choose = gr.Markdown(load_markdown(tips_path, "video_remixer_choose"))
    video_remixer_compile = gr.Markdown(load_markdown(tips_path, "video_remixer_compile"))
    video_remixer_processing = gr.Markdown(load_markdown(tips_path, "video_remixer_processing"))
    video_remixer_home = gr.Markdown(load_markdown(tips_path, "video_remixer_home"))
    video_remixer_save = gr.Markdown(load_markdown(tips_path, "video_remixer_save"))
    video_remixer_extra = gr.Markdown(load_markdown(tips_path, "video_remixer_extra"))
    video_assembler = gr.Markdown(load_markdown(tips_path, "video_assembler"))
    transpose_png_files = gr.Markdown(load_markdown(tips_path, "transpose_png_files"))
    enhance_frames =  gr.Markdown(load_markdown(tips_path, "enhance_frames"))
