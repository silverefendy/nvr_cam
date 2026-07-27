"""
System health checker — CPU, RAM, disk, camera status.
"""
import psutil
import time
import structlog
import asyncio
from datetime import datetime, timezone
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
from backend.utils.config_manager import config_manager
from backend.services.recorder.manager import RecordingManager
from backend.services.notifier.dispatcher import NotificationDispatcher

log = structlog.get_logger(__name__)
_start_time = time.time()

# To track offline duration: {camera_id: offline_since_datetime}
_offline_tracker = {}


def get_system_health() -> dict:
    mem = psutil.virtual_memory()
    return {
        "cpu_pct": psutil.cpu_percent(interval=1),
        "ram_pct": mem.percent,
        "ram_used_gb": round(mem.used / 1e9, 2),
        "ram_total_gb": round(mem.total / 1e9, 2),
        "uptime_hours": round((time.time() - _start_time) / 3600, 2),
    }


async def run_camera_health_check():
    """
    Checks if active cameras' RTSP streams are disconnected.
    If a camera has been offline for > N minutes (default 5), sends an alert.
    """
    log.info("health.camera_check_start")

    # 1. Load config
    sys_config = await config_manager.get_system_config()
    limit_minutes = float(sys_config.get("general", {}).get("offline_alert_minutes", 5.0))

    # 2. Get active cameras from DB
    async with AsyncSessionLocal() as db:
        repo = CameraRepository(db)
        cameras = await repo.get_active_cameras()

        # 3. Get recording manager status
        rm = RecordingManager.get_instance()
        now = datetime.now(timezone.utc)

        # Initialize dispatcher
        dispatcher = NotificationDispatcher()
        await dispatcher.start()

        for cam in cameras:
            is_alive = rm.get_status(cam.id)

            if not is_alive:
                if cam.id not in _offline_tracker:
                    _offline_tracker[cam.id] = now
                    log.warning("health.camera_offline_detected", camera=cam.name, id=cam.id)
                else:
                    offline_duration = (now - _offline_tracker[cam.id]).total_seconds() / 60.0
                    log.info("health.camera_offline_status", camera=cam.name, duration_min=round(offline_duration, 1))

                    if offline_duration >= limit_minutes:
                        alerted_key = f"{cam.id}_alerted"
                        if not _offline_tracker.get(alerted_key, False):
                            ip = (cam.config_json or {}).get("ip_address") or "Unknown IP"
                            timestamp_str = now.isoformat()
                            msg = (
                                f"⚠️ Kamera OFFLINE:\n"
                                f"Nama: {cam.name}\n"
                                f"IP: {ip}\n"
                                f"Durasi Offline: {offline_duration:.1f} menit\n"
                                f"Waktu: {timestamp_str}"
                            )
                            try:
                                if dispatcher._telegram:
                                    await dispatcher._telegram.send_text(msg)
                                    log.info("health.alert_sent", camera=cam.name)
                                _offline_tracker[alerted_key] = True
                            except Exception as alert_err:
                                log.error("health.alert_failed", error=str(alert_err))
            else:
                if cam.id in _offline_tracker:
                    log.info("health.camera_recovered", camera=cam.name, id=cam.id)
                    _offline_tracker.pop(cam.id, None)
                    _offline_tracker.pop(f"{cam.id}_alerted", None)


async def _health_checker_loop():
    """Background task loop that runs the camera health check every 60 seconds."""
    await asyncio.sleep(15)  # Wait for services to initialize
    while True:
        try:
            await run_camera_health_check()
        except Exception as e:
            log.error("health.checker_loop_error", error=str(e))
        await asyncio.sleep(60)


def start_health_checker():
    """Starts the health checker background worker task."""
    asyncio.create_task(_health_checker_loop())
