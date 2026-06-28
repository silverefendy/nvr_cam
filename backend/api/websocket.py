"""
WebSocket connection manager for real-time events to dashboard.
"""
import json
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from backend.core.logging import get_logger

logger = get_logger(__name__, service="websocket")


class ConnectionManager:
    """Manager for all active WebSocket connections."""
    
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        """Accept and register a new WebSocket connection."""
        await ws.accept()
        self.active.add(ws)
        logger.info(f"WebSocket connected. Total active: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        """Remove a WebSocket connection."""
        self.active.discard(ws)
        logger.info(f"WebSocket disconnected. Total active: {len(self.active)}")

    async def broadcast(self, event_type: str, data: dict):
        """Send event to all connected clients."""
        message = json.dumps({"type": event_type, "data": data})
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                dead.add(ws)
        self.active -= dead

    async def send_personal(self, ws: WebSocket, event_type: str, data: dict):
        """Send event to a specific client."""
        message = json.dumps({"type": event_type, "data": data})
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            self.disconnect(ws)
