"""Options feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class Options(TabBase):
    """Encapsulates UI elements and events for application options"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable,
                    restart_fn : Callable):
        TabBase.__init__(self, config, engine, log_fn)
        self.restart_fn = restart_fn

    def render_tab(self):
        """Render tab into UI"""
        with gr.Tab(SimpleIcons.GEAR + "Options"):
            with gr.Row():
                restart_button = gr.Button("Restart App", variant="primary",
                    elem_id="restartbutton").style(full_width=False)
        restart_button.click(self.restart_fn,
            _js="function(){setTimeout(function(){window.location.reload()},2000);return[]}")
