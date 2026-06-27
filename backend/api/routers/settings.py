"""Router: /api/v1/settings — Pengaturan global sistem."""
from fastapi import APIRouter, Depends
from backend.api.middleware.auth import require_role
from backend.db.models.user import User

router = APIRouter(tags=["settings"])


@router.get("")
async def get_settings(_: User = Depends(require_role("admin"))):
    """Ambil semua pengaturan sistem dari tabel settings."""
    # TODO: query tabel settings di DB
    return {"storage_threshold_pct": 10, "hls_segment_duration": 2}


@router.put("")
async def update_settings(body: dict, _: User = Depends(require_role("admin"))):
    """Update pengaturan sistem."""
    # TODO: upsert ke tabel settings
    return {"status": "updated"}
