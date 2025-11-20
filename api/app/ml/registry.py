# registry.py

import os

BASE = os.path.join(os.path.dirname(__file__), "models")

def list_models():
    files = os.listdir(BASE)
    models = [f.replace(".pt", "") for f in files if f.endswith(".pt")]
    return models
