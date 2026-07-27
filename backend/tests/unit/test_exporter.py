"""Unit test for Footage Exporter."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timezone
from pathlib import Path
from backend.services.recorder.exporter import export_footage, clean_old_exports

# Make sure all models are registered
from backend.db.models import *
from backend.db.models.camera_group import CameraGroup
from backend.db.models.recording import Recording


@pytest.mark.asyncio
async def test_export_footage():
    mock_db = MagicMock()
    rec1 = Recording(id=1, camera_id="cam_01", file_path="/mnt/driveE/cam_01/1.mp4", started_at=datetime(2026, 7, 27, 10, 0, 0, tzinfo=timezone.utc), ended_at=datetime(2026, 7, 27, 11, 0, 0, tzinfo=timezone.utc))

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [rec1]

    async def fake_execute(*args, **kwargs):
        return mock_result
    mock_db.execute = fake_execute

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec, \
         patch("backend.services.recorder.exporter.config_manager.get_system_config", AsyncMock(return_value={"general": {"temp_export_dir": "/tmp/nvr_exports"}})), \
         patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open()) as mock_file, \
         patch.object(Path, "unlink", return_value=True):

        out_path = await export_footage(mock_db, "cam_01", datetime(2026, 7, 27, 10, 15, 0, tzinfo=timezone.utc), datetime(2026, 7, 27, 10, 45, 0, tzinfo=timezone.utc))

        assert out_path is not None
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "ffmpeg" in args
        assert "-f" in args
        assert "concat" in args
