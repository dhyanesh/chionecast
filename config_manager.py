"""
config_manager.py - Persistent configuration manager for CHIONECAST.
Manages user preferences in ~/.config/chionecast/config.json.
Allows independent configuration of themes, displayed metrics, rotation, and intervals.
"""

import os
import json
from dataclasses import dataclass, asdict, field
from typing import Optional

CONFIG_DIR = os.path.expanduser("~/.config/chionecast")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SYSTEM_CONFIG_FILE = "/etc/chionecast/config.json"


@dataclass
class AppConfig:
    rotate: int = 180
    brightness: int = 8
    theme: str = "reactor"
    interval: float = 1.0
    primary_metric: str = "cpu"       # 'cpu', 'gpu', 'ram', 'vram'
    secondary_metric: str = "gpu"     # 'cpu', 'gpu', 'ram', 'vram'
    aux_metric: str = "ram"           # 'ram', 'vram', 'none'
    temp_unit: str = "C"              # 'C', 'F'
    custom_bg: Optional[str] = None


def get_config_path() -> str:
    """
    Returns path to the active configuration file.
    """
    return CONFIG_FILE


def load_config(override_path: Optional[str] = None) -> AppConfig:
    """
    Loads configuration from user home directory (~/.config/chionecast/config.json)
    or system directory (/etc/chionecast/config.json), falling back to defaults.
    """
    path = override_path or CONFIG_FILE
    if not os.path.isfile(path) and os.path.isfile(SYSTEM_CONFIG_FILE):
        path = SYSTEM_CONFIG_FILE

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter known fields
            valid_keys = {k for k in AppConfig.__dataclass_fields__}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return AppConfig(**filtered)
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}. Using defaults.")

    return AppConfig()


def save_config(config: AppConfig, target_path: Optional[str] = None) -> str:
    """
    Saves configuration to ~/.config/chionecast/config.json.
    """
    path = target_path or CONFIG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2)
    return path


def print_config(config: AppConfig):
    """
    Prints a formatted summary of the active configuration.
    """
    print("=== Active CHIONECAST Configuration ===")
    print(f"  Config File:       {get_config_path()}")
    print(f"  Theme:             {config.theme}")
    print(f"  Rotation:          {config.rotate}°")
    print(f"  Brightness:        {config.brightness} / 8")
    print(f"  Refresh Interval:  {config.interval}s")
    print(f"  Primary Metric:    {config.primary_metric.upper()}")
    print(f"  Secondary Metric:  {config.secondary_metric.upper()}")
    print(f"  Auxiliary Metric:  {config.aux_metric.upper()}")
    print(f"  Temperature Unit:  °{config.temp_unit.upper()}")
    if config.custom_bg:
        print(f"  Custom Background: {config.custom_bg}")
    print("=======================================")
