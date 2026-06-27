"""
WebSocket endpoint untuk real-time events ke dashboard.
"""
import asyncio
import json
from typing import set as Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

log = structlog.get_logger(__name__)
ws_router = APIRouter()

# Manager untuk semua koneksi WebSocket aktif
class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        log.info("ws.connected", total=len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        log.info("ws.disconnected", total=len(self.active))

    async def broadcast(self, event_type: str, data: dict):
        """Kirim event ke semua client yang terhubung."""
        message = json.dumps({"type": event_type, "data": data})
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()


@ws_router.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    """
    Real-time event stream.
    Client subscribe untuk mendapat update:
    - motion_detected
    - camera_status_changed
    - storage_warning
    - recording_started / recording_stopped
    """
    await manager.connect(ws)
    try:
        while True:
            # Terima pesan dari client (misal: subscribe filter kamera tertentu)
            data = await ws.receive_text()
            # TODO: handle subscription filter
    except WebSocketDisconnect:
        manager.disconnect(ws)
