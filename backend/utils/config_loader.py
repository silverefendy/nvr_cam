"""
Load konfigurasi dari YAML files.
"""
import yaml
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


@lru_cache
def load_cameras() -> list[dict]:
    with open(CONFIG_DIR / "cameras.yaml") as f:
        return yaml.safe_load(f)["cameras"]


@lru_cache
def load_system_config() -> dict:
    with open(CONFIG_DIR / "system.yaml") as f:
        return yaml.safe_load(f)


@lru_cache
def load_storage_config() -> list[dict]:
    with open(CONFIG_DIR / "storage.yaml") as f:
        return yaml.safe_load(f)["drives"]
