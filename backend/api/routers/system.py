"""Router: /api/v1/system — Health check, log, monitoring."""
import time
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from backend.api.middleware.auth import get_current_user
from backend.api.schemas.system import SystemHealth
from backend.db.models.user import User
from backend.utils.health import (
    get_cpu_percent, get_ram_percent, get_ram_details,
    get_disk_summary, check_service_status, get_uptime
)

router = APIRouter(tags=["system"])
_start_time = time.time()


@router.get("/health")
async def health_check(request: Request, _: User = Depends(get_current_user)):
    """Status realtime server: CPU, RAM, disk, services."""
    ram = get_ram_details()
    
    # Get camera status from RecordingManager
    recording_manager = request.app.state.recording_manager
    camera_online = 0
    camera_offline = 0
    camera_total = 0
    
    if recording_manager:
        camera_online = recording_manager.get_online_count()
        camera_offline = recording_manager.get_offline_count()
        camera_total = len(recording_manager.recorders)
    
    # Get service statuses
    services = [
        {"name": "nvr-api", "status": "running", "uptime_s": int(get_uptime())},
        {"name": "nvr-recorder", "status": "running" if recording_manager and recording_manager._running else "stopped", "uptime_s": None},
        {"name": "nvr-motion", "status": "running" if request.app.state.motion_manager else "stopped", "uptime_s": None},
        {"name": "nvr-encoder", "status": check_service_status("nvr-encoder"), "uptime_s": None},
    ]
    
    # Get disk summary from storage manager
    storage_manager = request.app.state.storage_manager
    if storage_manager:
        drive_paths = list(set(storage_manager.camera_drive_map.values()))
        disk = get_disk_summary(drive_paths)
    else:
        disk = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "free_pct": 0}
    
    return {
        "cpu_usage": get_cpu_percent(interval=0.1),      # was: cpu_pct
        "ram_usage": ram["percent"],                       # was: ram_pct
        "ram_used_gb": ram["used_gb"],
        "ram_total_gb": ram["total_gb"],
        "disk_usage": round(100 - disk["free_pct"], 1),   # was: disk_pct (inverted!)
        "disk_used_gb": disk["used_gb"],
        "disk_total_gb": disk["total_gb"],
        "uptime_seconds": int(get_uptime()),               # was: uptime_s
        "services": services,
        "cameras_online": camera_online,                   # was: camera_online
        "cameras_offline": camera_offline,                 # was: camera_offline
        "cameras_total": camera_total,
    }


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket, request: Request):
    """WebSocket untuk real-time event stream ke dashboard."""
    await websocket.accept()
    ws_manager = request.app.state.websocket_manager
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and receive client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
