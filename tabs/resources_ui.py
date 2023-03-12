"""Resynthesize Video feature UI and event handlers"""
from typing import Callable
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

    def render_tab(self):
        """Render page into UI"""
        with gr.Tab(SimpleIcons.GLOBE + "Resources"):
            self.link_item("linkcontainer", "FFmpeg (Free Download)", "Download FFmpeg",
                "https://ffmpeg.org/download.html")
            self.link_item("linkcontainer2", "Real-ESRGAN Image/Video Restoration (Github)",
                "Practical Algorithms for General Image/Video Restoration",
                "https://github.com/xinntao/Real-ESRGAN")
            self.link_item("linkcontainer", "Adobe AI-Based Speech Enhancement (Free)",
                "Adobe Podcast (Beta) Enhance Speech", "https://podcast.adobe.com/enhance")
            self.link_item("linkcontainer2", "Coqui TTS (Python)",
                "Advanced Text-to-Speech generation", "https://pypi.org/project/TTS/")
            self.link_item("linkcontainer", "Motion Array (Royalty-Free Content)",
                "The All-in-One Video &amp; Filmmakers Platform", "https://motionarray.com/")
            self.link_item("linkcontainer2", "",
                "",
                "")
            self.link_item("linkcontainer", "",
                "",
                "")
            self.link_item("linkcontainer2", "",
                "",
                "")

    def link_item(self, container_id : str, title : str, label : str, url : str):
        """Construct a resource entry row"""
        with gr.Row(variant="panel", elem_id=container_id) as row:
            gr.HTML(f"""
<div id="{container_id}">
    <p id="linkitem">
        {SimpleIcons.GLOBE}{title} -
        <a href="{url}" target="_blank">{label}</a>
    </p>
</div>""")
        return row
