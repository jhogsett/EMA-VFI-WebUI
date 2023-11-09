"""Application Session Data Handler"""
import os
import yaml
from yaml import Loader, YAMLError

class Session():
    def __init__(self, path : str="session.yaml"):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="UTF-8") as file:
                self.data : dict = yaml.load(file, Loader=Loader)
        else:
            self.data = {}

    def save(self):
        with open(self.path, "w", encoding="UTF-8") as file:
            yaml.dump(self.data, file, width=1024)

    def set(self, key : str, value : str):
        self.data[key] = value
        self.save()

    def get(self, key : str, default_value : str | None = None):
        return self.data.get(key, default_value)
