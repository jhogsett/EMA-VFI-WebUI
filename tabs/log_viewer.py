"""Log Viewer feature UI and event handlers"""
from typing import Callable
import gradio as gr
from webui_utils.simple_config import SimpleConfig
from webui_utils.simple_icons import SimpleIcons
from webui_utils.simple_log import SimpleLog
from interpolate_engine import InterpolateEngine
from tabs.tab_base import TabBase

class LogViewer(TabBase):
    """Encapsulates UI elements and events for the Log Viewer feature"""
    def __init__(self,
                    config : SimpleConfig,
                    engine : InterpolateEngine,
                    log_fn : Callable,
                    log_obj : SimpleLog):
        TabBase.__init__(self, config, engine, log_fn)
        self.log_obj = log_obj

    def render_tab(self):
        """Render tab into UI"""
        max_lines = self.config.logviewer_settings["max_lines"]
        with gr.Tab(SimpleIcons.SCROLL + "Log Viewer"):
            with gr.Row():
                log_text = gr.Textbox(max_lines=max_lines, placeholder="Press Refresh Log", label="Log",
                                      interactive=False, elem_id="logviewer")
            with gr.Row():
                refresh_button = gr.Button(value="Refresh Log", variant="primary").style(
                    full_width=False)
                sort_order = gr.Radio(choices=["Oldest First", "Newest First"],
                                      value="Oldest First", label="Sort Order")
                clear_button = gr.Button(value="Clear Log").style(full_width=False)

        refresh_button.click(self.refresh_log_text, inputs=sort_order, outputs=log_text)
        clear_button.click(self.clear_log_text, outputs=log_text)

    def refresh_log_text(self, sort_order : str):
        messages = self.log_obj.messages
        newest_first = sort_order[0] == "N"
        if newest_first:
            messages = list(reversed(messages))
        return "\n".join(messages)

    def clear_log_text(self):
        self.log_obj.reset()
        return self.refresh_log_text("Oldest First")
