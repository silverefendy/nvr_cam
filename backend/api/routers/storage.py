"""Router: /api/v1/storage — Status, statistik per kamera, manajemen storage."""
import shutil
import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from backend.api.middleware.auth import get_current_user, require_role
from backend.api.schemas.storage import DriveStatus
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.user import User

router = APIRouter(tags=["storage"])


async def _get_effective_drives(request: Request) -> list[str]:
    """
    Dapatkan daftar drive yang efektif: gabungan dari storage_manager
    dan storage_drive dari semua kamera aktif di DB.
    
    Ini memastikan kamera yang ditambah setelah startup tetap terdeteksi,
    meskipun storage_manager.camera_drive_map belum di-update.
    """
    drives = set()
    
    # Dari storage_manager jika aktif
    storage_manager = request.app.state.storage_manager
    if storage_manager:
        drives.update(storage_manager.camera_drive_map.values())
    
    # Dari DB — tangkap drive kamera yang ditambah setelah startup
    try:
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            cameras = await repo.get_active_cameras()
            for cam in cameras:
                if cam.storage_drive:
                    drives.add(cam.storage_drive)
                    # Sync ke storage_manager jika belum terdaftar
                    if storage_manager and cam.id not in storage_manager.camera_drive_map:
                        storage_manager.camera_drive_map[cam.id] = cam.storage_drive
    except Exception:
        pass
    
    return list(drives)


async def _storage_status_response(request: Request):
    """Logika utama untuk endpoint status storage."""
    storage_manager = request.app.state.storage_manager
    
    # Dapatkan drive yang efektif (termasuk kamera baru yang ditambah setelah startup)
    effective_drives = await _get_effective_drives(request)
    
    if not effective_drives:
        return {
            "drives": [],
            "total_tb": 0,
            "used_tb": 0,
            "free_tb": 0,
            "estimated_days_remaining": 0,
            "threshold_pct": storage_manager.threshold_pct if storage_manager else 10,
            "_warning": "Belum ada kamera dengan storage drive yang dikonfigurasi.",
        }

    missing_drives = [d for d in effective_drives if not Path(d).exists()]
    drives = []
    total_tb = 0
    used_tb = 0
    free_tb = 0

    for drive_path in effective_drives:
        p = Path(drive_path)
        if not p.exists():
            continue
        try:
            usage = shutil.disk_usage(drive_path)
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            free_pct = (usage.free / usage.total) * 100

            # Cari kamera yang ada di drive ini (dari storage_manager map)
            cameras_on_drive = []
            if storage_manager:
                cameras_on_drive = [
                    cam_id for cam_id, d in storage_manager.camera_drive_map.items()
                    if d == drive_path
                ]

            drives.append(DriveStatus(
                path=drive_path,
                total_gb=total_gb,
                used_gb=used_gb,
                free_gb=free_gb,
                free_pct=free_pct,
                cameras=cameras_on_drive,
            ))
            total_tb += total_gb / 1024
            used_tb += used_gb / 1024
            free_tb += free_gb / 1024
        except Exception:
            continue

    estimated_days = int(free_tb / 1) if free_tb > 0 else 0

    result = {
        "drives": drives,
        "total_tb": round(total_tb, 2),
        "used_tb": round(used_tb, 2),
        "free_tb": round(free_tb, 2),
        "estimated_days_remaining": estimated_days,
        "threshold_pct": storage_manager.threshold_pct if storage_manager else 10,
    }

    if missing_drives:
        result["_missing_drives"] = missing_drives
        result["_warning"] = (
            f"Drive berikut tidak ditemukan di server: {missing_drives}. "
            "Pastikan drive sudah di-mount dan path sesuai."
        )

    return result


@router.get("")
async def get_storage_status(request: Request, _: User = Depends(get_current_user)):
    """Ringkasan kapasitas semua drive yang terdaftar."""
    return await _storage_status_response(request)


@router.get("/status")
async def get_storage_status_alias(request: Request, _: User = Depends(get_current_user)):
    """Alias /status → sama dengan GET /api/v1/storage (kompatibilitas frontend)."""
    return await _storage_status_response(request)


@router.get("/debug")
async def get_storage_debug(request: Request, _: User = Depends(require_role("admin"))):
    """
    Debug endpoint — tampilkan info lengkap storage manager.
    Berguna saat storage page tidak menampilkan data.
    """
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"error": "storage_manager is None — backend belum diinisialisasi dengan benar"}

    effective_drives = await _get_effective_drives(request)
    drive_info = []
    for d in effective_drives:
        p = Path(d)
        info = {"path": d, "exists": p.exists()}
        if p.exists():
            usage = shutil.disk_usage(d)
            info["total_gb"] = round(usage.total / (1024**3), 2)
            info["free_gb"] = round(usage.free / (1024**3), 2)
        drive_info.append(info)

    return {
        "camera_drive_map": storage_manager.camera_drive_map,
        "effective_drives": effective_drives,
        "threshold_pct": storage_manager.threshold_pct,
        "drives": drive_info,
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
    # Sync dulu agar kamera baru terdaftar
    await _get_effective_drives(request)
    return storage_manager.get_stats_by_camera()


@router.get("/schedule")
async def get_cleanup_schedule(request: Request, _: User = Depends(get_current_user)):
    """
    Ambil konfigurasi jadwal cleanup terjadwal (F-09).
    """
    schedule = getattr(request.app.state, "cleanup_schedule", None)
    if schedule is None:
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

    # Sync drive map dulu
    await _get_effective_drives(request)

    drives = set(storage_manager.camera_drive_map.values())
    for drive in drives:
        cameras_on_drive = [
            cam_id for cam_id, cam_drive in storage_manager.camera_drive_map.items()
            if cam_drive == drive
        ]
        for cam_id in cameras_on_drive:
            storage_manager.check_and_clean(drive, cam_id)

    return {"status": "cleanup triggered"}
