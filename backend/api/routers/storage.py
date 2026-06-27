"""Router: /api/v1/storage — Status dan manajemen storage."""
import shutil
from fastapi import APIRouter, Depends
from backend.api.middleware.auth import get_current_user, require_role
from backend.api.schemas.storage import StorageStatus, DriveStatus
from backend.db.models.user import User

router = APIRouter(tags=["storage"])


@router.get("", response_model=StorageStatus)
async def get_storage_status(_: User = Depends(get_current_user)):
    """Ringkasan kapasitas semua drive yang terdaftar."""
    # TODO: baca dari config untuk daftar drive, lalu shutil.disk_usage per drive
    drives = []
    total_used = 0.0
    total_free = 0.0
    total_size = 0.0
    return StorageStatus(drives=drives, total_tb=total_size/1024, used_tb=total_used/1024, free_tb=total_free/1024, estimated_days_remaining=0)


@router.post("/cleanup")
async def manual_cleanup(_: User = Depends(require_role("admin"))):
    """Trigger manual cleanup — hapus file terlama yang tidak diprotect."""
    # TODO: panggil StorageManager.cleanup()
    return {"status": "cleanup triggered"}
