import io
import uuid
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.app import app
from backend.core.config import DEFAULT_DB_PASSWORD, DEFAULT_JWT_SECRET, Settings
from backend.core.security import create_access_token
from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.user_repo import UserRepository


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _fake_db():
    yield SimpleNamespace()


def _user(role: str = "viewer"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        username=f"{role}-user",
        role=role,
        is_active=True,
    )


def test_production_rejects_default_secrets():
    with pytest.raises(RuntimeError, match="DB_PASSWORD"):
        Settings(
            app_env="production",
            db_password=DEFAULT_DB_PASSWORD,
            jwt_secret="safe-secret-value-with-enough-randomness",
            cors_allow_origins="https://nvr.example.com",
        )

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings(
            app_env="production",
            db_password="safe-db-password",
            jwt_secret=DEFAULT_JWT_SECRET,
            cors_allow_origins="https://nvr.example.com",
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(RuntimeError, match="CORS_ALLOW_ORIGINS"):
        Settings(
            app_env="production",
            db_password="safe-db-password",
            jwt_secret="safe-secret-value-with-enough-randomness",
            cors_allow_origins="*",
        )


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_playback_requires_token():
    async with _client() as client:
        response = await client.get("/api/v1/recordings/1/play")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_playback_rejects_invalid_token():
    async with _client() as client:
        response = await client.get("/api/v1/recordings/1/play?token=invalid.token")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_playback_accepts_valid_query_token(monkeypatch, tmp_path):
    current_user = _user()
    token = create_access_token(current_user.id)
    video = tmp_path / "recording.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 2048)

    async def fake_get_user_by_id(self, user_id):
        return current_user

    async def fake_get_recording_by_id(self, recording_id):
        return SimpleNamespace(
            id=recording_id,
            file_path=str(video),
            started_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(UserRepository, "get_by_id", fake_get_user_by_id)
    monkeypatch.setattr(RecordingRepository, "get_by_id", fake_get_recording_by_id)

    async with _client() as client:
        response = await client.get(f"/api/v1/recordings/1/play?token={token}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")


@pytest.mark.asyncio
async def test_config_restore_requires_auth():
    backup = io.BytesIO()
    with zipfile.ZipFile(backup, "w") as zipf:
        zipf.writestr("system.yaml", "app:\n  name: test\n")

    async with _client() as client:
        response = await client.post(
            "/api/v1/config/restore",
            files={"file": ("backup.zip", backup.getvalue(), "application/zip")},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_config_restore_requires_admin(monkeypatch):
    token = create_access_token(uuid.uuid4())

    async def fake_get_user_by_id(self, user_id):
        return _user("viewer")

    monkeypatch.setattr(UserRepository, "get_by_id", fake_get_user_by_id)

    async with _client() as client:
        response = await client.post(
            "/api/v1/config/restore",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("backup.zip", b"not-a-zip", "application/zip")},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_config_restore_rejects_zip_slip(monkeypatch):
    token = create_access_token(uuid.uuid4())
    backup = io.BytesIO()
    with zipfile.ZipFile(backup, "w") as zipf:
        zipf.writestr("../system.yaml", "bad: true\n")

    async def fake_get_user_by_id(self, user_id):
        return _user("admin")

    monkeypatch.setattr(UserRepository, "get_by_id", fake_get_user_by_id)

    async with _client() as client:
        response = await client.post(
            "/api/v1/config/restore",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("backup.zip", backup.getvalue(), "application/zip")},
        )

    assert response.status_code == 400
