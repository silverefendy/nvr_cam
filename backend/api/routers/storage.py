"""Router: /api/v1/storage — Status dan manajemen storage."""
import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from backend.api.middleware.auth import get_current_user, require_role
from backend.api.schemas.storage import DriveStatus
from backend.db.models.user import User

router = APIRouter(tags=["storage"])


@router.get("")
async def get_storage_status(request: Request, _: User = Depends(get_current_user)):
    """Ringkasan kapasitas semua drive yang terdaftar."""
    # Get storage manager from app state
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"drives": [], "total_tb": 0, "used_tb": 0, "free_tb": 0, "estimated_days_remaining": 0}
    
    # Get all drive statuses
    drive_statuses = storage_manager.get_all_drives_status()
    
    # Load camera mapping from config
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "storage.yaml"
    camera_map = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        for drive in config.get("drives", []):
            camera_map[drive["path"]] = drive.get("cameras", [])
    
    # Add camera lists to drive statuses
    drives = []
    total_tb = 0
    used_tb = 0
    free_tb = 0
    
    for status in drive_statuses:
        cameras = camera_map.get(status["path"], [])
        drives.append(DriveStatus(
            mount=status["path"],
            label=Path(status["path"]).name,
            total_gb=status["total_gb"],
            used_gb=status["used_gb"],
            free_gb=status["free_gb"],
            free_pct=status["free_pct"],
            cameras=cameras
        ))
        total_tb += status["total_gb"] / 1024
        used_tb += status["used_gb"] / 1024
        free_tb += status["free_gb"] / 1024
    
    # Estimate days remaining (rough calculation: assuming 1TB/day usage)
    estimated_days = int(free_tb / 1) if free_tb > 0 else 0
    
    return {
        "drives": drives,
        "total_tb": round(total_tb, 2),
        "used_tb": round(used_tb, 2),
        "free_tb": round(free_tb, 2),
        "estimated_days_remaining": estimated_days
    }


@router.post("/cleanup")
async def manual_cleanup(request: Request, _: User = Depends(require_role("admin"))):
    """Trigger manual cleanup — hapus file terlama yang tidak diprotect."""
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"status": "error", "message": "Storage manager not available"}
    
    # Trigger cleanup for all drives
    drives = set(storage_manager.camera_drive_map.values())
    for drive in drives:
        cameras_on_drive = [
            cam_id for cam_id, cam_drive in storage_manager.camera_drive_map.items()
            if cam_drive == drive
        ]
        for cam_id in cameras_on_drive:
            storage_manager.check_and_clean(drive, cam_id)
    
    return {"status": "cleanup triggered"}
