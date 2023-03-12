"""Base class for UI tabs"""
from typing import Callable
from webui_utils.simple_config import SimpleConfig
from interpolate_engine import InterpolateEngine

class TabBase():
    """Shared UI tab methods"""
    def __init__(self,
                config : SimpleConfig,
                engine : InterpolateEngine,
                log_fn : Callable):
        self.engine = engine
        self.config = config
        self.log_fn = log_fn

    def log(self, message : str):
        """Logging"""
        self.log_fn(message)
