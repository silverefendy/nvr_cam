"""Unit test for Storage Auto-Purge."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import shutil

# Register all models first to prevent relationship mapping errors
from backend.db.models import *
from backend.db.models.camera_group import CameraGroup

from backend.services.storage.manager import StorageManager
from backend.db.models.recording import Recording


@pytest.mark.asyncio
async def test_auto_purge_storage():
    # Setup mock manager with one camera and drive
    mgr = StorageManager({"cam_01": "/mnt/driveE"})

    # Create mock database objects
    rec1 = Recording(id=1, camera_id="cam_01", file_path="/mnt/driveE/cam_01/1.mp4", is_protected=False)
    rec2 = Recording(id=2, camera_id="cam_01", file_path="/mnt/driveE/cam_01/2.mp4", is_protected=False)

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [rec1, rec2]

    async def fake_execute(*args, **kwargs):
        return mock_result
    mock_db.execute = fake_execute
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    # Mock disk_usage: first call simulates 95% usage, second call simulates 75% usage (after delete)
    mock_usages = [
        shutil._ntuple_diskusage(100, 95, 5), # 95% used -> triggers purge (>10 threshold)
        shutil._ntuple_diskusage(100, 75, 25), # 75% used -> stops purge (<=80 threshold)
    ]
    usage_iter = iter(mock_usages)

    def mock_disk_usage(path):
        return next(usage_iter)

    # Mock Path.exists to return True (drive and files exist)
    def mock_path_exists(self):
        return True

    with patch("shutil.disk_usage", mock_disk_usage), \
         patch.object(Path, "exists", mock_path_exists), \
         patch.object(Path, "stat") as mock_stat, \
         patch.object(Path, "unlink") as mock_unlink, \
         patch("backend.services.storage.manager.config_manager.get_system_config", AsyncMock(return_value={"storage": {"threshold_pct": 10.0, "safe_threshold_pct": 80.0}})), \
         patch("backend.services.storage.manager.cleanup_orphan_metadata", new_callable=AsyncMock) as mock_cleanup:

        mock_stat.return_value.st_size = 1000

        await mgr.auto_purge_storage(mock_db)

        # Verify both rec1 and rec2 were deleted in the first batch of 10
        assert mock_db.delete.call_count == 2
        mock_db.delete.assert_any_call(rec1)
        mock_db.delete.assert_any_call(rec2)
        assert mock_unlink.call_count == 2
        mock_cleanup.assert_called_once_with(mock_db)
