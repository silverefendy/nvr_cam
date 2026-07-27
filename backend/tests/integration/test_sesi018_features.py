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


def _user(role: str = "viewer"):
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
async def test_camera_groups_list_unauthenticated():
    async with _client() as client:
        resp = await client.get("/api/v1/camera-groups")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_camera_groups_create_requires_admin(monkeypatch):
    token = create_access_token(uuid.uuid4())
    async def fake_get_user_by_id(self, user_id):
        return _user("viewer")
    monkeypatch.setattr(UserRepository, "get_by_id", fake_get_user_by_id)

    async with _client() as client:
        resp = await client.post("/api/v1/camera-groups", headers={"Authorization": f"Bearer {token}"}, json={"name": "Test Group"})
    assert resp.status_code == 403
