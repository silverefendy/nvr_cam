"""Integration test for orphan metadata cleanup."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# Register all models first to prevent relationship mapping errors
from backend.db.models import *
from backend.db.models.camera_group import CameraGroup

from backend.services.storage.cleanup import cleanup_orphan_metadata
from backend.db.models.recording import Recording
from backend.db.models.motion_event import MotionEvent


@pytest.mark.asyncio
async def test_cleanup_orphan_metadata():
    rec1 = Recording(id=1, file_path="/fake/existing/path.mp4")
    rec2 = Recording(id=2, file_path="/fake/nonexistent/path.mp4")

    event1 = MotionEvent(id=1, snapshot_path="/fake/existing/snapshot.jpg")
    event2 = MotionEvent(id=2, snapshot_path="/fake/nonexistent/snapshot.jpg")

    mock_db = MagicMock()

    async def mock_execute(query):
        query_str = str(query)
        mock_result = MagicMock()
        if "recordings" in query_str:
            mock_result.scalars.return_value.all.return_value = [rec1, rec2]
        else:
            mock_result.scalars.return_value.all.return_value = [event1, event2]
        return mock_result

    mock_db.execute = mock_execute
    mock_db.delete = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    def mock_exists(self):
        return "existing" in str(self)

    with patch.object(Path, "exists", mock_exists):
        await cleanup_orphan_metadata(mock_db)

    deleted_args = [call.args[0] for call in mock_db.delete.mock_calls]
    assert rec2 in deleted_args
    assert event2 in deleted_args
    assert rec1 not in deleted_args
    assert event1 not in deleted_args
