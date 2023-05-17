"""Resynthesize Video feature UI and event handlers"""
import os
from typing import Callable
import csv
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class Resources(TabBase):
    """Encapsulates UI elements and events for the Resources page"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.resources_path = self.config.user_interface["resources_path"]

    def render_tab(self):
        """Render page into UI"""
        with gr.Tab(SimpleIcons.GLOBE + "Resources"):
            resources = self.load_resources()
            if resources:
                row_alternation = False
                for entry in resources:
                    icon = self.get_icon(entry["icon"])
                    title = entry["title"]
                    desc = entry["link_description"]
                    url = entry["url"]
                    css = "linkcontainer2" if row_alternation else "linkcontainer"
                    row_alternation = not row_alternation
                    self.link_item(css, icon, title, desc, url)
            gr.Markdown(f"*From* `{os.path.abspath(self.resources_path)}`")

    def load_resources(self) -> dict:
       if os.path.isfile(self.resources_path):
            reader = csv.DictReader(open(self.resources_path, encoding="utf-8"))
            return list(reader)
       else:
           return None

    def get_icon(self, icon : str) -> str:
        try:
            icon = getattr(SimpleIcons, icon.upper())
        except:
            icon = SimpleIcons.GLOBE
        return icon

    def link_item(self, container_id : str, icon : str, title : str, label : str, url : str):
        """Construct a resource entry row"""
        with gr.Row(variant="panel", elem_id=container_id) as row:
            gr.HTML(f"""
<div id="{container_id}">
    <p id="linkitem">
        {icon}{title}
        <a href="{url}" target="_blank">{label}</a>
    </p>
</div>""")
        return row
