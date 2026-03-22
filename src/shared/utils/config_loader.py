"""
config_loader.py

Single source of truth for config file paths.
Works both locally and in Lambda.
"""

import os
import json

def get_config_path(filename: str) -> str:
    """
    Returns the correct path to a config file.
    
    Locally:  reads CONFIG_PATH env var or falls back to config/ at project root
    Lambda:   reads CONFIG_PATH env var → /var/task/config
    """
    config_dir = os.environ.get(
        "CONFIG_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "config")
    )
    return os.path.abspath(os.path.join(config_dir, filename))


def load_json(filename: str) -> dict:
    """
    Loads and returns a JSON config file.
    """
    path = get_config_path(filename)
    with open(path, "r") as f:
        return json.load(f)