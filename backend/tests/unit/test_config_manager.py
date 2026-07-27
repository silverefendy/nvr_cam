"""Unit test for ConfigManager."""
import pytest
from unittest.mock import patch, MagicMock
from backend.utils.config_manager import config_manager


class FakeAsyncSessionContext:
    def __init__(self, db):
        self.db = db
    async def __aenter__(self):
        return self.db
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_get_cameras_hits_db():
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    async def fake_execute(*args, **kwargs):
        return mock_result
    mock_db.execute = fake_execute

    with patch("backend.db.base.AsyncSessionLocal", return_value=FakeAsyncSessionContext(mock_db)):
        cameras = await config_manager.get_cameras()
        assert isinstance(cameras, list)


@pytest.mark.asyncio
async def test_get_system_config_hits_db():
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    async def fake_execute(*args, **kwargs):
        return mock_result
    mock_db.execute = fake_execute

    with patch("backend.db.base.AsyncSessionLocal", return_value=FakeAsyncSessionContext(mock_db)):
        config = await config_manager.get_system_config()
        assert isinstance(config, dict)
