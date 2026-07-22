"""Router: /api/v1/storage — Status, statistik per kamera, manajemen storage."""
import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from backend.api.middleware.auth import get_current_user, require_role
from backend.api.schemas.storage import DriveStatus
from backend.db.models.user import User

router = APIRouter(tags=["storage"])


@router.get("")
async def get_storage_status(request: Request, _: User = Depends(get_current_user)):
    """Ringkasan kapasitas semua drive yang terdaftar."""
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"drives": [], "total_tb": 0, "used_tb": 0, "free_tb": 0, "estimated_days_remaining": 0, "threshold_pct": 10}

    drive_statuses = storage_manager.get_all_drives_status()

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "storage.yaml"
    camera_map = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        for drive in config.get("drives", []):
            camera_map[drive["path"]] = drive.get("cameras", [])

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

    estimated_days = int(free_tb / 1) if free_tb > 0 else 0

    return {
        "drives": drives,
        "total_tb": round(total_tb, 2),
        "used_tb": round(used_tb, 2),
        "free_tb": round(free_tb, 2),
        "estimated_days_remaining": estimated_days,
        "threshold_pct": storage_manager.threshold_pct,
    }


@router.get("/stats/cameras")
async def get_stats_by_camera(request: Request, _: User = Depends(get_current_user)):
    """
    Statistik penggunaan disk per kamera (F-08).
    Return: [{camera_id, drive, file_count, total_mb}]
    """
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return []
    return storage_manager.get_stats_by_camera()


@router.get("/schedule")
async def get_cleanup_schedule(request: Request, _: User = Depends(get_current_user)):
    """
    Ambil konfigurasi jadwal cleanup terjadwal (F-09).
    Dibaca dari app.state — disimpan saat app startup atau saat PUT.
    """
    schedule = getattr(request.app.state, "cleanup_schedule", None)
    if schedule is None:
        # Default: cleanup harian jam 03:00
        schedule = {
            "enabled": False,
            "cron": "0 3 * * *",
            "hour": 3,
            "minute": 0,
        }
    return schedule


@router.put("/schedule")
async def update_cleanup_schedule(
    body: dict,
    request: Request,
    _: User = Depends(require_role("admin")),
):
    """
    Update jadwal cleanup terjadwal (F-09).
    Body: {enabled: bool, hour: int, minute: int}

    Catatan: perubahan jadwal berlaku saat loop background di-restart.
    Untuk saat ini state disimpan di memory (app.state).
    Persistent config bisa ditambahkan nanti via config/cleanup.yaml.
    """
    enabled = bool(body.get("enabled", False))
    hour = int(body.get("hour", 3))
    minute = int(body.get("minute", 0))

    if not (0 <= hour <= 23):
        raise HTTPException(status_code=400, detail="hour harus 0-23")
    if not (0 <= minute <= 59):
        raise HTTPException(status_code=400, detail="minute harus 0-59")

    schedule = {
        "enabled": enabled,
        "cron": f"{minute} {hour} * * *",
        "hour": hour,
        "minute": minute,
    }
    request.app.state.cleanup_schedule = schedule

    return {"status": "ok", "schedule": schedule}


@router.post("/cleanup")
async def manual_cleanup(request: Request, _: User = Depends(require_role("admin"))):
    """Trigger manual cleanup — hapus file terlama yang tidak diprotect."""
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"status": "error", "message": "Storage manager not available"}

    drives = set(storage_manager.camera_drive_map.values())
    for drive in drives:
        cameras_on_drive = [
            cam_id for cam_id, cam_drive in storage_manager.camera_drive_map.items()
            if cam_drive == drive
        ]
        for cam_id in cameras_on_drive:
            storage_manager.check_and_clean(drive, cam_id)

    return {"status": "cleanup triggered"}
