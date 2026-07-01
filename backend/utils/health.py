"""
System health check utilities.
"""
import psutil
import time
from pathlib import Path
from typing import Optional


def get_cpu_percent(interval: float = 1.0) -> float:
    """Get CPU usage percentage."""
    return psutil.cpu_percent(interval=interval)


def get_ram_percent() -> float:
    """Get RAM usage percentage."""
    return psutil.virtual_memory().percent


def get_ram_details() -> dict:
    """Get detailed RAM usage."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / (1024**3),
        "used_gb": mem.used / (1024**3),
        "free_gb": mem.available / (1024**3),
        "percent": mem.percent
    }


def get_disk_summary(drive_paths: list[str] = None) -> dict:
    """Get aggregated disk usage for specified drives."""
    if drive_paths is None:
        # Default to common mount points
        drive_paths = ["/"]
    
    total_gb = 0
    used_gb = 0
    free_gb = 0
    
    for path in drive_paths:
        if Path(path).exists():
            try:
                usage = psutil.disk_usage(path)
                total_gb += usage.total / (1024**3)
                used_gb += usage.used / (1024**3)
                free_gb += usage.free / (1024**3)
            except Exception:
                pass
    
    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "free_pct": (free_gb / total_gb * 100) if total_gb > 0 else 0
    }


def check_service_status(service_name: str) -> bool:
    """Check if a systemd service is active."""
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def get_uptime() -> float:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
        return uptime_seconds
    except Exception:
        # Fallback to process uptime
        return time.time() - psutil.boot_time()


def get_service_uptime(service_name: str) -> float | None:
    """Get uptime of a specific systemd service in seconds."""
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "show", service_name, "--property=ActiveEnterTimestamp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            timestamp_str = result.stdout.split("=", 1)[1].strip()
            from datetime import datetime
            # Parse systemd timestamp format
            timestamp = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S %Z")
            return (datetime.now() - timestamp).total_seconds()
    except Exception:
        pass
    return None


def get_disk_status(drive_paths: list[str] = None) -> list[dict]:
    """Get detailed disk status for each drive."""
    if drive_paths is None:
        # Default to common mount points
        if Path("/").exists():
            drive_paths = ["/"]
        else:
            # Windows fallback
            drive_paths = [str(Path.home().anchor)]
    
    drives = []
    for path in drive_paths:
        if Path(path).exists():
            try:
                usage = psutil.disk_usage(path)
                drives.append({
                    "path": path,
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "free_pct": (usage.free / usage.total * 100) if usage.total > 0 else 0,
                    "used_pct": (usage.used / usage.total * 100) if usage.total > 0 else 0,
                })
            except Exception:
                pass
    
    return drives


def get_camera_status(recording_manager: Optional[object] = None) -> dict:
    """Get camera status from RecordingManager."""
    if recording_manager is None:
        return {
            "online": 0,
            "offline": 0,
            "total": 0,
            "status": "unavailable"
        }
    
    try:
        status = recording_manager.get_status()
        online_count = recording_manager.get_online_count()
        offline_count = recording_manager.get_offline_count()
        
        return {
            "online": online_count,
            "offline": offline_count,
            "total": online_count + offline_count,
            "status": "available",
            "details": status
        }
    except Exception:
        return {
            "online": 0,
            "offline": 0,
            "total": 0,
            "status": "error"
        }
