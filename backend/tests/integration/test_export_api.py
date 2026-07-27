"""Integration test for Footage Export API."""
import pytest
from httpx import ASGITransport, AsyncClient
from backend.api.app import app
from backend.core.security import create_access_token
import uuid
from types import SimpleNamespace
from backend.db.repositories.user_repo import UserRepository
from backend.db.base import get_db

def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _user(role: str = "operator"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        username=f"{role}-user",
        role=role,
        is_active=True,
    )


@pytest.fixture(autouse=True)
def override_db():
    async def _fake_db():
        yield SimpleNamespace()
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_api_flow(monkeypatch):
    token = create_access_token(uuid.uuid4())
    async def fake_get_user_by_id(self, user_id):
        return _user("operator")
    monkeypatch.setattr(UserRepository, "get_by_id", fake_get_user_by_id)

    async with _client() as client:
        # 1. Trigger export
        resp = await client.post(
            "/api/v1/recordings/export",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "camera_id": "cam_01",
                "start_time": "2026-07-27T10:00:00Z",
                "end_time": "2026-07-27T11:00:00Z"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"

        # 2. Get export status
        job_id = data["job_id"]
        status_resp = await client.get(
            f"/api/v1/recordings/export/{job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "status" in status_data
