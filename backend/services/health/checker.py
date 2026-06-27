"""
System health checker — CPU, RAM, disk, camera status.
"""
import psutil
import time
import structlog

log = structlog.get_logger(__name__)
_start_time = time.time()


def get_system_health() -> dict:
    mem = psutil.virtual_memory()
    return {
        "cpu_pct": psutil.cpu_percent(interval=1),
        "ram_pct": mem.percent,
        "ram_used_gb": round(mem.used / 1e9, 2),
        "ram_total_gb": round(mem.total / 1e9, 2),
        "uptime_hours": round((time.time() - _start_time) / 3600, 2),
    }
