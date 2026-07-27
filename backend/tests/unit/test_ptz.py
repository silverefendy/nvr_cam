"""Unit test for PTZ controls."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.camera.ptz import PTZController

# Make sure all models are registered
from backend.db.models import *
from backend.db.models.camera_group import CameraGroup
from backend.db.models.camera import Camera


class FakeAsyncSessionContext:
    def __init__(self, db):
        self.db = db
    async def __aenter__(self):
        return self.db
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_ptz_move_and_stop():
    mock_db = MagicMock()
    mock_camera = Camera(id="cam_01", name="Test PTZ", rtsp_main="rtsp://admin:pass@192.168.1.100:554/stream", config_json={"ptz_enabled": True})

    mock_db.get = AsyncMock(return_value=mock_camera)

    # Mock ONVIFCamera (synchronous library)
    mock_onvif = MagicMock()
    mock_onvif.update_xaddrs = MagicMock()

    mock_ptz = MagicMock()
    mock_onvif.create_ptz_service = MagicMock(return_value=mock_ptz)

    mock_media = MagicMock()
    mock_profile = MagicMock()
    mock_profile.token = "ProfileToken_1"
    mock_media.GetProfiles = MagicMock(return_value=[mock_profile])
    mock_onvif.create_media_service = MagicMock(return_value=mock_media)

    # Mock ContinuousMove and Stop
    mock_ptz.GetStatus = MagicMock()
    mock_ptz.GetStatus.return_value.Position.PanTilt.x = 0.0
    mock_ptz.GetStatus.return_value.Position.PanTilt.y = 0.0
    mock_ptz.GetStatus.return_value.Position.Zoom.x = 0.0
    mock_ptz.create_type = MagicMock()
    mock_ptz.ContinuousMove = MagicMock()
    mock_ptz.Stop = MagicMock()

    with patch("backend.services.camera.ptz.AsyncSessionLocal", return_value=FakeAsyncSessionContext(mock_db)), \
         patch("backend.services.camera.ptz.ONVIFCamera", return_value=mock_onvif):

        # Test move
        await PTZController.move("cam_01", "up", 0.5)
        mock_ptz.ContinuousMove.assert_called_once()

        # Test stop
        await PTZController.stop("cam_01")
        mock_ptz.Stop.assert_called_once()
