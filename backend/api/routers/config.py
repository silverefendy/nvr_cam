from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_admin_user
from backend.api.schemas.config import (
    CameraConfigCreate,
    CameraConfigUpdate,
    SystemConfigUpdate,
    NotificationConfigUpdate,
    StorageConfigUpdate,
    RTSPTestRequest,
    RTSPTestResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    ConfigApplyResponse,
    BackupInfo,
    BackupListResponse,
    ConfigResponse,
)
from backend.db.base import get_db
from backend.db.models.camera import Camera
from backend.db.repositories.camera_repo import CameraRepository
from backend.services.notifier.telegram import TelegramNotifier
from backend.services.notifier.email import EmailNotifier
from backend.utils.config_manager import config_manager

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

router = APIRouter(tags=["config"])


def _get_recording_manager():
    """Lazy import untuk hindari circular import."""
    from backend.services.recorder.manager import RecordingManager
    return RecordingManager.get_instance()


# ─── CAMERA ROUTES ────────────────────────────────────────────────────────────

@router.get("/cameras", response_model=ConfigResponse)
async def get_cameras_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Ambil semua kamera dari database."""
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()
    cameras_list = [
        {
            "id": cam.id,
            "name": cam.name,
            "location": cam.location,
            "rtsp_main": cam.rtsp_main,
            "rtsp_sub": cam.rtsp_sub,
            "storage_drive": cam.storage_drive,
            "motion_enabled": cam.motion_enabled,
            "retention_days": cam.retention_days,
            "is_active": cam.is_active,
            "sort_order": cam.sort_order,
            "config_json": cam.config_json,
        }
        for cam in cameras
    ]
    return ConfigResponse(data={"cameras": cameras_list})


# PENTING: route statis harus di atas route {camera_id}
@router.post("/cameras/test-connection", response_model=RTSPTestResponse)
async def test_rtsp_connection_adhoc(
    request: RTSPTestRequest,
    _user=Depends(get_current_admin_user),
):
    """Test RTSP URL ad-hoc sebelum kamera disimpan."""
    try:
        result = await _test_rtsp_connection(request.rtsp_url, request.timeout_s or 10)
        return RTSPTestResponse(
            success=result["success"],
            message=result["message"],
            codec=result.get("codec"),
            resolution=result.get("resolution"),
            fps=result.get("fps"),
        )
    except Exception as e:
        return RTSPTestResponse(success=False, message=str(e))


@router.post("/cameras", response_model=ConfigResponse)
async def create_camera_config(
    camera: CameraConfigCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Tambah kamera baru ke database, lalu langsung start recorder."""
    repo = CameraRepository(db)

    # Auto-generate ID jika tidak diisi
    if not camera.id:
        existing = await repo.get_active_cameras()
        max_num = 0
        for cam in existing:
            if cam.id.startswith("cam_"):
                try:
                    num = int(cam.id.replace("cam_", ""))
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        camera.id = f"cam_{max_num + 1:02d}"

    # Cek duplikasi ID
    existing_cam = await repo.get_by_id(camera.id)
    if existing_cam:
        raise HTTPException(status_code=409, detail=f"Camera ID '{camera.id}' sudah ada")

    camera_data = camera.model_dump()

    # Build RTSP URL
    if not camera_data.get("rtsp_main_custom"):
        rtsp_main = _build_dahua_rtsp(
            camera_data["ip_address"], camera_data["port"],
            camera_data["username"], camera_data["password"],
            camera_data["channel"], 0,
        )
    else:
        rtsp_main = camera_data["rtsp_main_custom"]

    if not camera_data.get("rtsp_sub_custom"):
        rtsp_sub = _build_dahua_rtsp(
            camera_data["ip_address"], camera_data["port"],
            camera_data["username"], camera_data["password"],
            camera_data["channel"], 1,
        )
    else:
        rtsp_sub = camera_data["rtsp_sub_custom"]

    # Simpan credential ke config_json
    config_json = {
        "ip_address": camera_data.get("ip_address"),
        "port": camera_data.get("port"),
        "username": camera_data.get("username"),
        "password": camera_data.get("password"),
        "channel": camera_data.get("channel"),
        "motion_zones": camera_data.get("motion_zones"),
    }

    new_camera = Camera(
        id=camera_data["id"],
        name=camera_data["name"],
        location=camera_data.get("location"),
        rtsp_main=rtsp_main,
        rtsp_sub=rtsp_sub,
        storage_drive=camera_data["storage_drive"],
        motion_enabled=camera_data.get("motion_enabled", False),
        retention_days=camera_data.get("retention_days", 30),
        is_active=True,
        sort_order=camera_data.get("sort_order", 0),
        config_json=config_json,
    )

    created = await repo.create(new_camera)

    # Langsung start recorder untuk kamera baru (non-blocking)
    try:
        rm = _get_recording_manager()
        asyncio.create_task(rm.restart_camera(created.id))
    except Exception:
        pass  # Jangan gagalkan request; recorder akan diambil saat restart berikutnya

    return ConfigResponse(data={"camera": {"id": created.id, "name": created.name}})


@router.put("/cameras/{camera_id}", response_model=ConfigResponse)
async def update_camera_config(
    camera_id: str,
    camera: CameraConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Update kamera di database, lalu restart recorder-nya."""
    repo = CameraRepository(db)
    existing = await repo.get_by_id(camera_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Kamera '{camera_id}' tidak ditemukan")

    update_data = camera.model_dump(exclude_unset=True)

    # Ambil credential lama dari config_json
    old_config = existing.config_json or {}
    ip = update_data.get("ip_address", old_config.get("ip_address"))
    port = update_data.get("port", old_config.get("port", 554))
    username = update_data.get("username", old_config.get("username", "admin"))
    password = update_data.get("password", old_config.get("password", ""))
    channel = update_data.get("channel", old_config.get("channel", 1))

    # Rebuild RTSP jika ada perubahan credential/koneksi
    need_rtsp_rebuild = any(k in update_data for k in ["ip_address", "port", "username", "password", "channel"])
    if need_rtsp_rebuild and ip:
        if not update_data.get("rtsp_main_custom"):
            update_data["rtsp_main"] = _build_dahua_rtsp(ip, port, username, password, channel, 0)
        if not update_data.get("rtsp_sub_custom"):
            update_data["rtsp_sub"] = _build_dahua_rtsp(ip, port, username, password, channel, 1)

    if update_data.get("rtsp_main_custom"):
        update_data["rtsp_main"] = update_data.pop("rtsp_main_custom")
    if update_data.get("rtsp_sub_custom"):
        update_data["rtsp_sub"] = update_data.pop("rtsp_sub_custom")

    # Update config_json dengan credential terbaru
    new_config_json = {**old_config}
    for field in ["ip_address", "port", "username", "password", "channel", "motion_zones"]:
        if field in update_data:
            new_config_json[field] = update_data.pop(field)
    update_data["config_json"] = new_config_json

    for field, value in update_data.items():
        if hasattr(existing, field):
            setattr(existing, field, value)

    await db.commit()
    await db.refresh(existing)

    # Restart recorder dengan konfigurasi terbaru (non-blocking)
    try:
        rm = _get_recording_manager()
        asyncio.create_task(rm.restart_camera(camera_id))
    except Exception:
        pass

    return ConfigResponse(data={"camera_id": camera_id})


@router.delete("/cameras/{camera_id}", response_model=ConfigResponse)
async def delete_camera_config(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Hapus kamera dari database, lalu stop recorder-nya."""
    repo = CameraRepository(db)
    existing = await repo.get_by_id(camera_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Kamera '{camera_id}' tidak ditemukan")

    deleted = await repo.delete_by_id(camera_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Gagal menghapus kamera")

    # Stop recorder kamera yang dihapus (non-blocking)
    try:
        rm = _get_recording_manager()
        if camera_id in rm.recorders:
            asyncio.create_task(rm.recorders[camera_id].stop())
            del rm.recorders[camera_id]
    except Exception:
        pass

    return ConfigResponse(data={"camera_id": camera_id})


@router.post("/cameras/{camera_id}/test-rtsp", response_model=RTSPTestResponse)
async def test_camera_rtsp(
    camera_id: str,
    request: RTSPTestRequest,
    _user=Depends(get_current_admin_user),
):
    try:
        result = await _test_rtsp_connection(request.rtsp_url, request.timeout_s)
        return RTSPTestResponse(
            success=result["success"], message=result["message"],
            codec=result.get("codec"), resolution=result.get("resolution"), fps=result.get("fps"),
        )
    except Exception as e:
        return RTSPTestResponse(success=False, message=str(e))


# ─── SYSTEM ROUTES ────────────────────────────────────────────────────────────

@router.get("/system", response_model=ConfigResponse)
async def get_system_config(_user=Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    return ConfigResponse(data=config)


@router.put("/system", response_model=ConfigResponse)
async def update_system_config(config: SystemConfigUpdate, _user=Depends(get_current_admin_user)):
    update_data = config.model_dump(exclude_unset=True)
    await config_manager.update_system_config(update_data)
    return ConfigResponse(data=update_data)


# ─── STORAGE ROUTES ───────────────────────────────────────────────────────────

@router.get("/storage", response_model=ConfigResponse)
async def get_storage_config(_user=Depends(get_current_admin_user)):
    config = await config_manager.get_storage_config()
    return ConfigResponse(data=config)


@router.put("/storage", response_model=ConfigResponse)
async def update_storage_config(config: StorageConfigUpdate, _user=Depends(get_current_admin_user)):
    update_data = config.model_dump()
    await config_manager.update_storage_config(update_data)
    return ConfigResponse(data=update_data)


# ─── NOTIFICATION ROUTES ──────────────────────────────────────────────────────

@router.get("/notifications", response_model=ConfigResponse)
async def get_notification_config(_user=Depends(get_current_admin_user)):
    config = await config_manager.get_notification_config()
    return ConfigResponse(data=config)


@router.put("/notifications", response_model=ConfigResponse)
async def update_notification_config(config: NotificationConfigUpdate, _user=Depends(get_current_admin_user)):
    update_data = config.model_dump(exclude_unset=True)
    await config_manager.update_notification_config(update_data)
    return ConfigResponse(data=update_data)


@router.post("/notifications/test", response_model=NotificationTestResponse)
async def test_notification(request: NotificationTestRequest, _user=Depends(get_current_admin_user)):
    results = {"telegram_sent": False, "email_sent": False}
    errors = []
    if request.telegram:
        try:
            await TelegramNotifier().send_message(request.test_message)
            results["telegram_sent"] = True
        except Exception as e:
            errors.append(f"Telegram failed: {str(e)}")
    if request.email:
        try:
            await EmailNotifier().send_message(subject="NVR Cam Test Notification", body=request.test_message)
            results["email_sent"] = True
        except Exception as e:
            errors.append(f"Email failed: {str(e)}")
    return NotificationTestResponse(
        success=len(errors) == 0,
        message="Test notifications sent" if not errors else "; ".join(errors),
        **results,
    )


# ─── APPLY / BACKUP ───────────────────────────────────────────────────────────

@router.post("/apply", response_model=ConfigApplyResponse)
async def apply_config(request: Request, _user=Depends(get_current_admin_user)):
    try:
        recording_manager = request.app.state.recording_manager
        motion_manager = request.app.state.motion_manager
        cameras = await recording_manager.load_cameras_from_db()
        current_ids = set(recording_manager.recorders.keys())
        new_ids = {cam["id"] for cam in cameras if cam.get("is_active", True)}
        restarted, started, stopped = [], [], []
        for camera_id in current_ids - new_ids:
            if camera_id in recording_manager.recorders:
                await recording_manager.recorders[camera_id].stop()
                del recording_manager.recorders[camera_id]
                stopped.append(camera_id)
        for camera_id in current_ids & new_ids:
            await recording_manager.restart_camera(camera_id)
            restarted.append(camera_id)
        for camera_id in new_ids - current_ids:
            cam_dict = next((c for c in cameras if c["id"] == camera_id), None)
            if cam_dict:
                from backend.services.recorder.camera_recorder import CameraRecorder
                recorder = CameraRecorder(cam_dict)
                recording_manager.recorders[camera_id] = recorder
                asyncio.create_task(recorder.start())
                started.append(camera_id)
        if motion_manager:
            motion_cameras = [cam for cam in cameras if cam.get("motion_enabled")]
            await motion_manager.stop_all()
            if motion_cameras:
                asyncio.create_task(motion_manager.start_all(motion_cameras))
        return ConfigApplyResponse(
            success=True,
            message=f"Applied: {len(restarted)} restarted, {len(started)} started, {len(stopped)} stopped",
            restarted=restarted, started=started, stopped=stopped,
        )
    except Exception as e:
        return ConfigApplyResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/backup", response_class=Response)
async def download_backup(_user=Depends(get_current_admin_user)):
    zip_bytes = await config_manager.backup_all()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(content=zip_bytes, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=nvr_config_backup_{timestamp}.zip"})


@router.post("/restore", response_model=ConfigResponse)
async def restore_backup(file: UploadFile = File(...)):
    zip_bytes = await file.read()
    await config_manager.restore_all(zip_bytes)
    return ConfigResponse(data={"message": "Configuration restored successfully"})


@router.get("/backups", response_model=BackupListResponse)
async def list_backups(_user=Depends(get_current_admin_user)):
    backup_dir = Path(__file__).parent.parent.parent.parent / "config" / "backups"
    backups = []
    if backup_dir.exists():
        for f in sorted(backup_dir.glob("*.yaml.*"), reverse=True)[:5]:
            stat = f.stat()
            backups.append(BackupInfo(
                filename=f.name,
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                size_bytes=stat.st_size,
            ))
    return BackupListResponse(backups=backups)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _build_dahua_rtsp(ip: str, port: int, user: str, password: str, channel: int, subtype: int) -> str:
    return f"rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype={subtype}"


async def _test_rtsp_connection(rtsp_url: str, timeout: int) -> dict[str, Any]:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_streams", "-show_format", "-of", "json",
            "-timeout", str(timeout * 1_000_000),
            "-rtsp_transport", "tcp",
            rtsp_url,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout + 2)
        if process.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            lines = [l for l in err.splitlines() if l.strip()]
            short_err = lines[-1] if lines else "FFprobe error"
            return {"success": False, "message": short_err}
        data = json.loads(stdout.decode())
        stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        codec = stream.get("codec_name", "unknown")
        width, height = stream.get("width"), stream.get("height")
        fps = stream.get("r_frame_rate", "")
        fps_float = None
        if fps:
            try:
                if "/" in str(fps):
                    num, den = fps.split("/")
                    fps_float = round(float(num) / float(den), 2) if float(den) != 0 else None
                else:
                    fps_float = float(fps)
            except Exception:
                fps_float = None

        return {
            "success": True,
            "message": "Koneksi RTSP berhasil",
            "codec": codec,
            "resolution": f"{width}x{height}" if width and height else None,
            "fps": fps_float,
        }
    except asyncio.TimeoutError:
        return {"success": False, "message": f"Timeout setelah {timeout}s — periksa IP/port kamera"}
    except FileNotFoundError:
        return {"success": False, "message": "FFprobe tidak ditemukan di container"}
    except Exception as e:
        return {"success": False, "message": str(e)}
