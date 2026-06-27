"""Router: /api/v1/system — Health check, log, monitoring."""
import psutil, time
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from backend.api.middleware.auth import get_current_user
from backend.api.schemas.system import SystemHealth, ServiceStatus
from backend.db.models.user import User

router = APIRouter(tags=["system"])
_start_time = time.time()


@router.get("/health", response_model=SystemHealth)
async def health_check(_: User = Depends(get_current_user)):
    """Status realtime server: CPU, RAM, disk, services."""
    ram = psutil.virtual_memory()
    services = [
        ServiceStatus(name="cctv-recorder", status="running", uptime_s=None),
        ServiceStatus(name="cctv-motion", status="running", uptime_s=None),
        ServiceStatus(name="cctv-encoder", status="running", uptime_s=None),
    ]
    return SystemHealth(
        cpu_pct=psutil.cpu_percent(interval=0.1),
        ram_pct=ram.percent,
        ram_used_gb=ram.used / (1024**3),
        ram_total_gb=ram.total / (1024**3),
        uptime_s=int(time.time() - _start_time),
        services=services,
        camera_online=0,   # TODO: dari RecordingManager
        camera_offline=0,
        camera_total=0,
    )


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket untuk real-time event stream ke dashboard."""
    await websocket.accept()
    try:
        while True:
            # TODO: broadcast motion events, camera status changes
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
