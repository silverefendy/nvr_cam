"""
ConfigManager - Thread-safe YAML configuration management with atomic writes and auto-backups.
"""
import asyncio
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from backend.core.config import settings

CONFIG_DIR = Path(settings.config_dir)
BACKUP_DIR = CONFIG_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Maximum number of backups to keep
MAX_BACKUPS = 5


class ConfigManager:
    """Thread-safe configuration manager with atomic writes and auto-backups."""

    def __init__(self):
        self._lock = asyncio.Lock()

    # ── Internal helpers (unlocked — must only be called while holding self._lock) ──

    def _read_yaml_unlocked(self, filename: str) -> dict:
        """Read YAML file. Caller must already hold self._lock."""
        filepath = CONFIG_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _write_yaml_safe_unlocked(self, filename: str, data: dict) -> None:
        """Write YAML file atomically. Caller must already hold self._lock."""
        filepath = CONFIG_DIR / filename
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, filepath)

    def _create_backup_unlocked(self, filename: str) -> Path:
        """Create timestamped backup. Caller must already hold self._lock."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{filename}.{timestamp}"
        shutil.copy2(CONFIG_DIR / filename, backup_path)
        self._cleanup_backups(filename)
        return backup_path

    def _cleanup_backups(self, filename: str) -> None:
        """Keep only MAX_BACKUPS for each config file."""
        backups = sorted(BACKUP_DIR.glob(f"{filename}.*"), reverse=True)
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()

    # ── Public read helpers (acquire lock themselves) ──

    async def _read_yaml(self, filename: str) -> dict:
        """Read YAML file safely (acquires lock)."""
        async with self._lock:
            return self._read_yaml_unlocked(filename)

    # ── Camera Configuration ──

    async def get_cameras(self) -> list[dict]:
        """Get all cameras from cameras.yaml."""
        config = await self._read_yaml("cameras.yaml")
        return config.get("cameras", [])

    async def add_camera(self, camera: dict) -> None:
        """Add a new camera to cameras.yaml."""
        async with self._lock:
            self._create_backup_unlocked("cameras.yaml")
            config = self._read_yaml_unlocked("cameras.yaml")
            if "cameras" not in config:
                config["cameras"] = []
            config["cameras"].append(camera)
            self._write_yaml_safe_unlocked("cameras.yaml", config)

    async def update_camera(self, camera_id: str, data: dict) -> None:
        """Update an existing camera in cameras.yaml."""
        async with self._lock:
            self._create_backup_unlocked("cameras.yaml")
            config = self._read_yaml_unlocked("cameras.yaml")
            for i, cam in enumerate(config.get("cameras", [])):
                if cam.get("id") == camera_id:
                    config["cameras"][i] = {**cam, **data}
                    break
            else:
                raise ValueError(f"Camera not found: {camera_id}")
            self._write_yaml_safe_unlocked("cameras.yaml", config)

    async def delete_camera(self, camera_id: str) -> None:
        """Delete a camera from cameras.yaml."""
        async with self._lock:
            self._create_backup_unlocked("cameras.yaml")
            config = self._read_yaml_unlocked("cameras.yaml")
            cameras = config.get("cameras", [])
            original_count = len(cameras)
            config["cameras"] = [c for c in cameras if c.get("id") != camera_id]
            if len(config["cameras"]) == original_count:
                raise ValueError(f"Camera not found: {camera_id}")
            self._write_yaml_safe_unlocked("cameras.yaml", config)

    def validate_cameras_yaml(self, data: dict) -> list[str]:
        """Validate cameras.yaml structure. Returns list of error messages."""
        errors = []
        if "cameras" not in data:
            errors.append("Missing 'cameras' key")
            return errors
        if not isinstance(data["cameras"], list):
            errors.append("'cameras' must be a list")
            return errors
        for i, cam in enumerate(data["cameras"]):
            if not isinstance(cam, dict):
                errors.append(f"Camera {i}: must be a dict")
                continue
            required_fields = ["id", "name", "rtsp_main", "storage_drive"]
            for field in required_fields:
                if field not in cam:
                    errors.append(f"Camera {i}: missing required field '{field}'")
            if "id" in cam and not isinstance(cam["id"], str):
                errors.append(f"Camera {i}: 'id' must be a string")
        return errors

    # ── System Configuration ──

    async def get_system_config(self) -> dict:
        """Get system configuration from system.yaml."""
        return await self._read_yaml("system.yaml")

    async def update_system_config(self, data: dict) -> None:
        """Update system configuration in system.yaml."""
        async with self._lock:
            self._create_backup_unlocked("system.yaml")
            current = self._read_yaml_unlocked("system.yaml")
            merged = {**current, **data}
            self._write_yaml_safe_unlocked("system.yaml", merged)

    # ── Storage Configuration ──

    async def get_storage_config(self) -> dict:
        """Get storage configuration from storage.yaml."""
        return await self._read_yaml("storage.yaml")

    async def update_storage_config(self, data: dict) -> None:
        """Update storage configuration in storage.yaml."""
        async with self._lock:
            self._create_backup_unlocked("storage.yaml")
            self._write_yaml_safe_unlocked("storage.yaml", data)

    # ── Notification Configuration ──

    async def get_notification_config(self) -> dict:
        """Get notification configuration from .env."""
        env_file = Path(__file__).parent.parent.parent / ".env"
        config = {}
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if key.startswith(("TELEGRAM_", "EMAIL_", "NOTIFY_")):
                            config[key.lower()] = value
        return config

    async def update_notification_config(self, data: dict) -> None:
        """Update notification configuration in .env."""
        env_file = Path(__file__).parent.parent.parent / ".env"
        existing = {}
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        existing[key] = value
        for key, value in data.items():
            env_key = key.upper()
            if value is not None:
                existing[env_key] = str(value)
        with open(env_file, "w") as f:
            for key, value in existing.items():
                f.write(f"{key}={value}\n")

    # ── Backup & Restore ──

    async def backup_all(self) -> bytes:
        """Create ZIP backup of all config files."""
        async with self._lock:
            zip_buffer = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            zip_path = Path(zip_buffer.name)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for yaml_file in ["cameras.yaml", "system.yaml", "storage.yaml"]:
                    filepath = CONFIG_DIR / yaml_file
                    if filepath.exists():
                        zipf.write(filepath, yaml_file)
                env_file = Path(__file__).parent.parent.parent / ".env"
                if env_file.exists():
                    zipf.write(env_file, ".env")
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()
            zip_path.unlink()
            return zip_bytes

    async def restore_all(self, zip_bytes: bytes) -> None:
        """Restore config from ZIP backup."""
        async with self._lock:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = BACKUP_DIR / f"pre_restore_{timestamp}"
            pre_restore_backup.mkdir(exist_ok=True)
            for yaml_file in ["cameras.yaml", "system.yaml", "storage.yaml"]:
                filepath = CONFIG_DIR / yaml_file
                if filepath.exists():
                    shutil.copy2(filepath, pre_restore_backup / yaml_file)
            zip_buffer = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            zip_path = Path(zip_buffer.name)
            zip_path.write_bytes(zip_bytes)
            try:
                with zipfile.ZipFile(zip_path, "r") as zipf:
                    zipf.extractall(CONFIG_DIR)
            finally:
                zip_path.unlink()


# Global instance
config_manager = ConfigManager()
