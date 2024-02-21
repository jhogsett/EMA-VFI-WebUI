"""Strip Scenes feature UI and event handlers"""
import os
import shutil
import re
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.file_utils import get_directories, get_files, split_filepath
from webui_utils.mtqdm import Mtqdm
from webui_tips import WebuiTips
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class StripScenes(TabBase):
    """Encapsulates UI elements and events for the Strip Scenes feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab("Strip Scenes"):
            gr.Markdown(
                SimpleIcons.VULCAN_HAND + "Strip scenes marked using sliced content")
            gr.Markdown(
        "**Mark scenes by placing files from the _Slice Video_ feature in the scene directory**")
            input_path = gr.Text(max_lines=1, label="Frames Groups Path",
                placeholder="Path on this server to the Frame Groups to be stripped")
            gr.Markdown(
        "**⚠️ Caution: Back up important content before using this feature**")
            action = gr.Radio(value="Keep Marked Content", label="Action",
                              choices=["Keep Marked Content", "Delete Marked Content"])
            strip_scenes = gr.Button("Strip Scenes", variant="primary")
            with gr.Accordion(SimpleIcons.TIPS_SYMBOL + " Guide", open=False):
                WebuiTips.strip_scenes.render()

        strip_scenes.click(self.strip_scenes, inputs=[input_path, action])

    # TODO move non-UI logic
    def strip_scenes(self,
                        input_path : str,
                        action : str):
        """Split Scenes button handler"""
        regex = "(.*)\[(\d*)-(\d*)\](.*)"
        if input_path:
            marked_scenes = set()
            markers = get_files(input_path)
            self.log(f"found {len(markers)} marker files in {input_path}")
            with Mtqdm().open_bar(total=len(markers), desc="Markers") as marker_bar:
                for marker in markers:
                    _, filename, ext = split_filepath(marker)
                    match = re.search(regex, filename + ext)
                    if match:
                        groups = match.groups()
                        if groups and len(groups) >= 3:
                            try:
                                first = groups[1]
                                last = groups[2]
                                self.log(f"found scene marker file {marker}")
                                group_name = f"{first}-{last}"
                                group_path = os.path.join(input_path, group_name)
                                if os.path.exists(group_path):
                                    self.log(f"marked scene {group_path} was found")
                                    marked_scenes.add(group_path)
                                else:
                                    self.log(
                                    f"marked scene {group_path} was not found, ignoring")
                            except ValueError:
                                self.log(
                                f"unable to parse scene from marker file {marker}, ignoring")

                    else:
                        self.log(f"unable to parse regex from marker file {marker}, ignoring")
                    Mtqdm().update_bar(marker_bar)
            self.log(f"marked scenes: {marked_scenes}")

            if marked_scenes:
                self.log(f"processing scenes for {len(marked_scenes)} markers")
                delete_list = []
                if action.startswith("K"):
                    # keep the marked scenes
                    scenes = get_directories(input_path)
                    scenes = [os.path.join(input_path, scene) for scene in scenes]
                    scene_set = set(scenes)
                    delete_list = scene_set - marked_scenes
                else:
                    # delete the marked scenes
                    delete_list = list(marked_scenes)

                with Mtqdm().open_bar(total=len(delete_list), desc="Scenes") as bar:
                    for delete_path in delete_list:
                        shutil.rmtree(delete_path)
                        Mtqdm().update_bar(bar)
            else:
                self.log(f"no markers found, no scenes will be stripped")
