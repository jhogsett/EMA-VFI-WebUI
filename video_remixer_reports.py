"""Video Remixer Reporting"""
from typing import Callable, TYPE_CHECKING
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_utils import seconds_to_hmsf, format_table
from webui_utils.video_utils import details_from_group_name
from webui_utils.jot import Jot

if TYPE_CHECKING:
    from video_remixer import VideoRemixerState

class VideoRemixerReports():
    def __init__(self, state : "VideoRemixerState", log_fn : Callable):
        self.state = state
        self.log_fn = log_fn

    def log(self, message):
        if self.log_fn:
            self.log_fn(message)

    ## Exports -----------------------

    def ingested_video_report(self):
        title = f"Ingested Video Report: {self.state.source_video}"
        header_row = [
            "Frame Rate",
            "Duration",
            "Display Size",
            "Aspect Ratio",
            "Content Size",
            "Frame Count",
            "File Size",
            "Has Audio"]
        data_rows = [[
            self.state.video_details['frame_rate'],
            self.state.video_details['duration'],
            self.state.video_details['display_dimensions'],
            self.state.video_details['display_aspect_ratio'],
            self.state.video_details['content_dimensions'],
            self.state.video_details['frame_count_show'],
            self.state.video_details['file_size'],
            SimpleIcons.YES_SYMBOL if self.state.video_details['has_audio'] else SimpleIcons.NO_SYMBOL]]
        return format_table(header_row, data_rows, color="more", title=title)

    def project_settings_report(self):
        title = f"Project Path: {self.state.project_path}"
        if self.state.split_type == "Scene":
            header_row, data_rows = self._project_settings_report_scene()
        elif self.state.split_type == "Break":
            header_row, data_rows = self._project_settings_report_break()
        elif self.state.split_type == "Time":
            header_row, data_rows = self._project_settings_report_time()
        else: # "None"
            header_row, data_rows = self._project_settings_report_none()
        return format_table(header_row, data_rows, color="more", title=title)

    def chosen_scenes_report(self):
        header_row = [
            "Scene Choices",
            "Scenes",
            "Frames",
            "Time"]
        all_scenes = len(self.state.scene_names)
        all_frames = self.scene_frames("all")
        all_time = self.scene_frames_time(all_frames)
        keep_scenes = len(self.state.kept_scenes())
        keep_frames = self.scene_frames("keep")
        keep_time = self.scene_frames_time(keep_frames)
        drop_scenes = len(self.state.dropped_scenes())
        drop_frames = self.scene_frames("drop")
        drop_time = self.scene_frames_time(drop_frames)
        data_rows = [
            [
                "Keep " + SimpleIcons.HEART,
                f"{keep_scenes:,d}",
                f"{keep_frames:,d}",
                f"+{keep_time}"],
            [
                "Drop",
                f"{drop_scenes:,d}",
                f"{drop_frames:,d}",
                f"+{drop_time}"],
            [
                "Total",
                f"{all_scenes:,d}",
                f"{all_frames:,d}",
                f"+{all_time}"]]
        return format_table(header_row, data_rows, color="more")

    def generate_remix_report(self, resize, resynthesize, inflate, upscale):
        report = Jot()

        if not resize \
            and not resynthesize \
            and not inflate \
            and not upscale:
            report.add(f"Original source scenes in {self.state.scenes_path}")

        if resize:
            report.add(f"Resized/cropped scenes in {self.state.resize_path}")

        if resynthesize:
            report.add(f"Resynthesized scenes in {self.state.resynthesis_path}")

        if inflate:
            report.add(f"Inflated scenes in {self.state.inflation_path}")

        if upscale:
            report.add(f"Upscaled scenes in {self.state.upscale_path}")

        return report.lines

    ## Internal ----------------------

    def _project_settings_report_scene(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Scene Detection Threshold"]
        data_rows = [[
            f"{float(self.state.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.state.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.state.resize_w} x {self.state.resize_h}",
            f"{self.state.crop_w} x {self.state.crop_h}",
            f"{self.state.crop_offset_x} x {self.state.crop_offset_y}",
            self.state.split_type,
            self.state.scene_threshold]]
        return header_row, data_rows

    def _project_settings_report_break(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Minimum Duration",
            "Black Ratio"]
        data_rows = [[
            f"{float(self.state.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.state.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.state.resize_w} x {self.state.resize_h}",
            f"{self.state.crop_w} x {self.state.crop_h}",
            f"{self.state.crop_offset_x} x {self.state.crop_offset_y}",
            self.state.split_type,
            f"{self.state.break_duration}s",
            self.state.break_ratio]]
        return header_row, data_rows

    def _project_settings_report_time(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type",
            "Split Time",
            "Split Frames"]
        self.state.split_frames = self.state.calc_split_frames(self.state.project_fps, self.state.split_time)
        data_rows = [[
            f"{float(self.state.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.state.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.state.resize_w} x {self.state.resize_h}",
            f"{self.state.crop_w} x {self.state.crop_h}",
            f"{self.state.crop_offset_x} x {self.state.crop_offset_y}",
            self.state.split_type,
            f"{self.state.split_time}s",
            self.state.split_frames]]
        return header_row, data_rows

    def _project_settings_report_none(self):
        header_row = [
            "Frame Rate",
            "Deinterlace",
            "Resize To",
            "Crop To",
            "Crop Offset",
            "Split Type"]
        data_rows = [[
            f"{float(self.state.project_fps):.2f}",
            SimpleIcons.YES_SYMBOL if self.state.deinterlace else SimpleIcons.NO_SYMBOL,
            f"{self.state.resize_w} x {self.state.resize_h}",
            f"{self.state.crop_w} x {self.state.crop_h}",
            f"{self.state.crop_offset_x} x {self.state.crop_offset_y}",
            self.state.split_type]]
        return header_row, data_rows

    def scene_frames(self, type : str="all") -> int:
        if type.lower() == "keep":
            scenes = self.state.kept_scenes()
        elif type.lower() == "drop":
            scenes = self.state.dropped_scenes()
        else:
            scenes = self.state.scene_names
        accum = 0
        for scene in scenes:
            first, last, _ = details_from_group_name(scene)
            accum += (last - first) + 1
        return accum

    def scene_frames_time(self, frames : int) -> str:
        return seconds_to_hmsf(frames / self.state.project_fps, self.state.project_fps)
