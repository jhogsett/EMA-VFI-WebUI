"""EMA-VFI-WebUI Application"""
import os
import shutil
import time
import signal
import argparse
from typing import Callable
from interpolate_engine import InterpolateEngine
from webui_utils.simple_log import SimpleLog
from webui_utils.simple_config import SimpleConfig
from webui_utils.file_utils import create_directories, is_safe_path
from webui_utils.color_out import ColorOut
from webui_utils.mtqdm import Mtqdm
from create_ui import create_ui
from webui_tips import WebuiTips

def main():
    """Run the application"""
    parser = argparse.ArgumentParser(description='EMA-VFI Web UI')
    parser.add_argument("--config_path", type=str, default="config.yaml",
        help="path to config YAML file")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()
    log = SimpleLog(args.verbose)
    config = SimpleConfig(args.config_path).config_obj()
    clean_working_directory(config.directories["working"])
    create_directories(config.directories)
    WebUI(config, log).start()

class WebUI:
    """Top-Level application logic"""
    def __init__(self,
                    config : SimpleConfig,
                    log : SimpleLog):
        self.config = config
        self.log = log
        self.restart = False
        self.prevent_inbrowser = False

    def start(self):
        """Create the UI and start the event loop"""
        Mtqdm().set_use_color(self.config.user_interface["mtqdm_use_color"])
        Mtqdm().set_palette(self.config.user_interface["mtqdm_palette"])
        WebuiTips.set_tips_path(self.config.user_interface["tips_path"])
        model = self.config.engine_settings["model"]
        gpu_ids = self.config.engine_settings["gpu_ids"]
        use_time_step = self.config.engine_settings["use_time_step"]
        engine = InterpolateEngine(model, gpu_ids, use_time_step=use_time_step)
        while True:
            print()
            if self.config.user_interface["mtqdm_use_color"]:
                print("\x1b[40m\x1b[38;2;0;0;0m▐\x1b[38;2;255;255;255m▄▄▄\x1b[38;2;255;255;0m▄▄▄\x1b[38;2;0;255;255m▄▄▄\x1b[38;2;0;255;0m▄▄▄\x1b[38;2;255;0;255m▄▄▄\x1b[38;2;255;0;0m▄▄▄\x1b[38;2;0;0;255m▄▄▄\x1b[38;2;0;0;0m▌\x1b[0m")
                print("\x1b[40m\x1b[38;2;0;0;0m▐\x1b[38;2;255;255;255m███\x1b[97m EMA-VFI WEBUI \x1b[38;2;0;0;255m███\x1b[38;2;0;0;0m▌\x1b[0m")
                print("\x1b[40m\x1b[38;2;0;0;0m▐\x1b[38;2;255;255;255m▀▀▀\x1b[38;2;255;255;0m▀▀▀\x1b[38;2;0;255;255m▀▀▀\x1b[38;2;0;255;0m▀▀▀\x1b[38;2;255;0;255m▀▀▀\x1b[38;2;255;0;0m▀▀▀\x1b[38;2;0;0;255m▀▀▀\x1b[38;2;0;0;0m▌\x1b[0m")
            else:
                print(" ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄")
                print(" ███ EMA-VFI WEBUI ███")
                print(" ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀")
            print()
            app = create_ui(self.config, engine, self.log, self.restart_app)
            app.launch(inbrowser = self.config.app_settings["auto_launch_browser"] and not self.prevent_inbrowser,
                        server_name = self.config.app_settings["server_name"],
                        server_port = self.config.app_settings["server_port"],
                        prevent_thread_lock=True, quiet=True)
            # after initial launch, disable inbrowser for subsequent restarts
            self.prevent_inbrowser = True
            self.wait_on_server(app)
            print()
            ColorOut("Restarting ...", "yellow")

    def restart_app(self):
        """Signal to the event loop to restart the application"""
        self.restart = True

    def wait_on_server(self, app):
        """Restart application if signal is set"""
        while True:
            time.sleep(0.5)
            if self.restart:
                self.restart = False
                time.sleep(0.5)
                app.close()
                time.sleep(0.5)
                break

def clean_working_directory(working_directory):
    if os.path.exists(working_directory) and is_safe_path(working_directory):
        shutil.rmtree(working_directory, ignore_errors=True)

def sigint_handler(sig, frame):
    """Make the program just exit at ctrl+c without waiting for anything"""
    ColorOut(f'Interrupted with signal {sig} in {frame}', "red")
    os._exit(0) #pylint: disable=protected-access
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    main()
