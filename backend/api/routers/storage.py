"""Router: /api/v1/storage — Status, statistik per kamera, browse filesystem, manajemen storage."""
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from backend.api.middleware.auth import get_current_user, require_role, get_current_super_admin
from backend.api.schemas.storage import DriveStatus
from backend.db.base import AsyncSessionLocal, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.user import User
from backend.services.transcode_queue import TranscodeQueue
from backend.utils.config_manager import config_manager

router = APIRouter(tags=["storage"])

# Path mount point yang dicek saat browse — berlaku di Docker maupun native Ubuntu
_BROWSE_ROOTS = ["/mnt", "/media", "/data", "/opt/nvr_cam", "/var/lib/nvr_cam"]


class DriveCreate(BaseModel):
    path: str
    name: str | None = None


class CameraAssign(BaseModel):
    camera_ids: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_effective_drives(request: Request) -> list[str]:
    """
    Dapatkan daftar drive yang efektif: gabungan dari storage_manager
    dan storage_drive dari semua kamera aktif di DB.
    """
    drives = set()
    storage_manager = request.app.state.storage_manager
    if storage_manager:
        drives.update(storage_manager.camera_drive_map.values())

    try:
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            cameras = await repo.get_active_cameras()
            for cam in cameras:
                if cam.storage_drive:
                    drives.add(cam.storage_drive)
                    if storage_manager and cam.id not in storage_manager.camera_drive_map:
                        storage_manager.update_camera_drive(cam.id, cam.storage_drive)
    except Exception:
        pass

    return list(drives)


async def _storage_status_response(request: Request):
    storage_manager = request.app.state.storage_manager
    effective_drives = await _get_effective_drives(request)

    if not effective_drives:
        return {
            "drives": [],
            "total_tb": 0,
            "used_tb": 0,
            "free_tb": 0,
            "estimated_days_remaining": 0,
            "threshold_pct": storage_manager.threshold_pct if storage_manager else 10,
            "_warning": (
                "Belum ada drive yang dikonfigurasi. "
                "Buka halaman Storage → browse dan pilih folder, atau isi path manual di storage.yaml."
            ),
        }

    missing_drives = [d for d in effective_drives if not Path(d).exists()]
    drives = []
    total_tb = used_tb = free_tb = 0

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
            f"Drive berikut tidak ditemukan: {missing_drives}. "
            "Gunakan endpoint /api/v1/storage/browse untuk melihat path yang tersedia, "
            "lalu update storage.yaml atau assign ulang di halaman Storage."
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Browse filesystem — fitur baru
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/browse")
async def browse_filesystem(
    path: Optional[str] = None,
    _: User = Depends(require_role("admin")),
):
    """
    Browse filesystem dari dalam container/server.

    - Tanpa parameter `path`: tampilkan root mount points yang tersedia (/mnt, /media, dll)
    - Dengan `path`: list isi direktori tersebut (hanya folder)

    Digunakan dari UI Storage untuk memilih folder rekaman tanpa harus tebak path.
    """
    if path is None:
        # Tampilkan root yang tersedia + info disk jika ada
        entries = []
        for root in _BROWSE_ROOTS:
            rp = Path(root)
            if not rp.exists():
                continue
            try:
                children = [d for d in rp.iterdir() if d.is_dir()]
            except PermissionError:
                children = []

            disk_info = None
            try:
                usage = shutil.disk_usage(root)
                disk_info = {
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "free_pct": round((usage.free / usage.total) * 100, 1),
                }
            except Exception:
                pass

            entries.append({
                "path": root,
                "name": rp.name or root,
                "is_dir": True,
                "children_count": len(children),
                "disk": disk_info,
            })
        return {"path": "/", "entries": entries}

    # Validasi: hanya izinkan browse di dalam _BROWSE_ROOTS
    resolved = Path(path).resolve()
    allowed = any(
        str(resolved).startswith(str(Path(r).resolve()))
        for r in _BROWSE_ROOTS
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Akses ke path ini tidak diizinkan. Path harus di bawah: {_BROWSE_ROOTS}",
        )

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Path tidak ditemukan: {path}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Path bukan direktori: {path}")

    try:
        entries = []
        for child in sorted(resolved.iterdir()):
            if not child.is_dir():
                continue
            try:
                child_count = len([x for x in child.iterdir() if x.is_dir()])
            except PermissionError:
                child_count = 0

            disk_info = None
            try:
                usage = shutil.disk_usage(str(child))
                disk_info = {
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "free_pct": round((usage.free / usage.total) * 100, 1),
                }
            except Exception:
                pass

            entries.append({
                "path": str(child),
                "name": child.name,
                "is_dir": True,
                "children_count": child_count,
                "disk": disk_info,
            })

        # Info disk untuk direktori yang sedang di-browse
        current_disk = None
        try:
            usage = shutil.disk_usage(str(resolved))
            current_disk = {
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "free_pct": round((usage.free / usage.total) * 100, 1),
            }
        except Exception:
            pass

        parent = str(resolved.parent) if resolved.parent != resolved else None
        # Jangan expose parent di luar browse roots
        if parent and not any(
            str(Path(parent).resolve()).startswith(str(Path(r).resolve()))
            for r in _BROWSE_ROOTS
        ):
            parent = None

        return {
            "path": str(resolved),
            "parent": parent,
            "disk": current_disk,
            "entries": entries,
        }

    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Tidak ada permission baca direktori: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Status endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("")
async def get_storage_status(request: Request, _: User = Depends(get_current_user)):
    return await _storage_status_response(request)


@router.get("/status")
async def get_storage_status_alias(request: Request, _: User = Depends(get_current_user)):
    return await _storage_status_response(request)


@router.get("/debug")
async def get_storage_debug(request: Request, _: User = Depends(require_role("admin"))):
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"error": "storage_manager is None"}

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
        "browse_roots": _BROWSE_ROOTS,
    }


@router.get("/diagnostics")
async def get_storage_diagnostics(request: Request, _: User = Depends(require_role("admin"))):
    storage_manager = request.app.state.storage_manager
    recording_manager = request.app.state.recording_manager
    await _get_effective_drives(request)

    camera_drive_map = dict(storage_manager.camera_drive_map) if storage_manager else {}
    drive_paths = sorted(set(camera_drive_map.values()))
    drives = []
    for drive_path in drive_paths:
        path = Path(drive_path)
        drive = {
            "path": drive_path,
            "exists": path.exists(),
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "cameras_mapped": [
                cam_id for cam_id, mapped_drive in camera_drive_map.items()
                if mapped_drive == drive_path
            ],
        }
        if path.exists():
            usage = shutil.disk_usage(drive_path)
            drive.update({
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
            })
        drives.append(drive)

    return {
        "camera_drive_map": camera_drive_map,
        "drives": drives,
        "recording_status": recording_manager.get_recording_status() if recording_manager else {},
        "transcode_cache": TranscodeQueue.get_instance().cache_info(),
    }


@router.get("/stats/cameras")
async def get_stats_by_camera(request: Request, _: User = Depends(get_current_user)):
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return []
    await _get_effective_drives(request)
    return storage_manager.get_stats_by_camera()


@router.get("/schedule")
async def get_cleanup_schedule(request: Request, _: User = Depends(get_current_user)):
    schedule = getattr(request.app.state, "cleanup_schedule", None)
    if schedule is None:
        schedule = {"enabled": False, "cron": "0 3 * * *", "hour": 3, "minute": 0}
    return schedule


@router.put("/schedule")
async def update_cleanup_schedule(
    body: dict,
    request: Request,
    _: User = Depends(require_role("admin")),
):
    enabled = bool(body.get("enabled", False))
    hour = int(body.get("hour", 3))
    minute = int(body.get("minute", 0))
    if not (0 <= hour <= 23):
        raise HTTPException(status_code=400, detail="hour harus 0-23")
    if not (0 <= minute <= 59):
        raise HTTPException(status_code=400, detail="minute harus 0-59")
    schedule = {"enabled": enabled, "cron": f"{minute} {hour} * * *", "hour": hour, "minute": minute}
    request.app.state.cleanup_schedule = schedule
    return {"status": "ok", "schedule": schedule}


@router.post("/cleanup")
async def manual_cleanup(request: Request, _: User = Depends(require_role("admin"))):
    storage_manager = request.app.state.storage_manager
    if not storage_manager:
        return {"status": "error", "message": "Storage manager not available"}
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


# ─────────────────────────────────────────────────────────────────────────────
# Drive management (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/drives")
async def list_drives(_user: User = Depends(get_current_super_admin)):
    config = await config_manager.get_storage_config()
    drives = config.get("drives", [])
    # Enrich dengan info disk yang aktual
    enriched = []
    for d in drives:
        entry = dict(d)
        p = Path(d.get("path", ""))
        entry["exists"] = p.exists()
        if p.exists():
            try:
                usage = shutil.disk_usage(str(p))
                entry["total_gb"] = round(usage.total / (1024**3), 1)
                entry["free_gb"] = round(usage.free / (1024**3), 1)
                entry["free_pct"] = round((usage.free / usage.total) * 100, 1)
            except Exception:
                pass
        enriched.append(entry)
    return enriched


@router.post("/drives")
async def add_drive(body: DriveCreate, _user: User = Depends(get_current_super_admin)):
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path tidak ditemukan di server: {body.path}. "
                   f"Gunakan GET /api/v1/storage/browse untuk melihat path yang tersedia.",
        )
    if not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Path bukan direktori: {body.path}")

    config = await config_manager.get_storage_config()
    drives = config.get("drives", [])
    if any(d.get("path") == body.path for d in drives):
        raise HTTPException(status_code=400, detail=f"Drive {body.path} sudah terdaftar")

    drives.append({"path": body.path, "name": body.name, "cameras": []})
    config["drives"] = drives
    await config_manager.update_storage_config(config)
    return {"message": "Drive berhasil ditambahkan", "drives": drives}


@router.delete("/drives/{path_encoded}")
async def delete_drive(path_encoded: str, _user: User = Depends(get_current_super_admin)):
    path = urllib.parse.unquote(path_encoded)
    config = await config_manager.get_storage_config()
    drives = config.get("drives", [])
    new_drives = [d for d in drives if d.get("path") != path]
    if len(new_drives) == len(drives):
        raise HTTPException(status_code=404, detail=f"Drive {path} tidak ditemukan")
    config["drives"] = new_drives
    await config_manager.update_storage_config(config)
    return {"message": f"Drive {path} berhasil dihapus"}


@router.put("/drives/{path_encoded}/assign")
async def assign_cameras(
    path_encoded: str,
    body: CameraAssign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_super_admin),
):
    path = urllib.parse.unquote(path_encoded)
    config = await config_manager.get_storage_config()
    drives = config.get("drives", [])

    if not any(d.get("path") == path for d in drives):
        raise HTTPException(status_code=404, detail=f"Drive {path} tidak ditemukan")

    for d in drives:
        if d.get("path") == path:
            d["cameras"] = body.camera_ids
        else:
            d["cameras"] = [cid for cid in d.get("cameras", []) if cid not in body.camera_ids]

    config["drives"] = drives
    await config_manager.update_storage_config(config)

    repo = CameraRepository(db)
    recording_manager = request.app.state.recording_manager
    storage_manager = request.app.state.storage_manager

    for camera_id in body.camera_ids:
        camera = await repo.get_by_id(camera_id)
        if camera:
            camera.storage_drive = path
            if storage_manager:
                storage_manager.update_camera_drive(camera_id, path)
            if recording_manager:
                await recording_manager.restart_camera(camera_id)

    await db.commit()
    return {"message": f"Kamera berhasil dipetakan ke drive {path}"}
