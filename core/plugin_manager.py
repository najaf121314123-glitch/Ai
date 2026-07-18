import os
import json

class PluginManager:
    def __init__(self):
        self.plugins = {}
    
    def load(self, path):
        for folder in os.listdir(path):
            manifest = os.path.join(path, folder, "manifest.json")
            if os.path.exists(manifest):
                with open(manifest) as f:
                    data = json.load(f)
                    print(f"Loaded plugin: {data['name']}")
