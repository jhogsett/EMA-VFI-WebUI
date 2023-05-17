"""Class to manage simple logging to the console"""

class SimpleLog:
    """Collect log message and optionally print to the console"""
    def __init__(self, verbose : bool):
        self.verbose = verbose
        self.messages = []

    def log(self, message : str) -> None:
        """Add a new log message"""
        self.messages.append(message)
        if self.verbose:
            print(message)

    def reset(self):
        self.messages = []
        self.log("log messages cleared")
