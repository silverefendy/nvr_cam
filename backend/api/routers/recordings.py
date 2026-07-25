"""
Router: /api/v1/recordings
List, playback, download, protect, delete rekaman.
Tambah: POST /sync â€” scan file di disk dan daftarkan ke DB.
"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.recording import Recording
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User

router = APIRouter(tags=["recordings"])


@router.get("")
async def list_recordings(
    camera_id: str | None = Query(None),
    date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman dengan filter opsional.
    Tanpa filter â†’ kembalikan 500 rekaman terbaru.
    """
    repo = RecordingRepository(db)
    if camera_id and date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_from = date_obj.replace(hour=0, minute=0, second=0)
            date_to   = date_obj.replace(hour=23, minute=59, second=59)
            recordings = await repo.get_by_camera_and_date(camera_id, date_from, date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    elif camera_id:
        recordings = await repo.get_by_camera(camera_id)
    elif date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_from = date_obj.replace(hour=0, minute=0, second=0)
            date_to   = date_obj.replace(hour=23, minute=59, second=59)
            recordings = await repo.get_by_date_range(date_from, date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        # Kembalikan 500 rekaman terbaru tanpa filter
        recordings = await repo.get_recent(limit=500)
    return recordings


@router.post("/sync")
async def sync_recordings_from_disk(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Scan semua file .mp4 di storage dan daftarkan yang belum ada di DB.

    Berguna untuk:
    - Rekaman lama sebelum patch yang belum tercatat di DB
    - Recovery setelah DB reset
    - File yang ada di disk tapi hilang dari tabel recordings
    """
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()

    inserted = 0
    skipped = 0
    errors = []

    for cam in cameras:
        drive = cam.storage_drive
        cam_dir = Path(drive) / cam.id
        if not cam_dir.exists():
            continue

        # Scan semua file .mp4 rekursif (struktur: <drive>/<cam_id>/<date>/<time>.mp4)
        for mp4_file in sorted(cam_dir.rglob("*.mp4")):
            try:
                # Cek apakah sudah ada di DB
                existing = await db.execute(
                    select(Recording).where(Recording.file_path == str(mp4_file))
                )
                if existing.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                stat = mp4_file.stat()
                if stat.st_size < 1024:  # Skip file kosong
                    continue

                # Coba parse waktu dari nama file (format: %H-%M-%S.mp4)
                try:
                    date_str = mp4_file.parent.name  # YYYY-MM-DD
                    time_str = mp4_file.stem           # HH-MM-SS
                    started_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H-%M-%S")
                except ValueError:
                    # Fallback: gunakan mtime file
                    started_at = datetime.fromtimestamp(stat.st_mtime)

                rec = Recording(
                    camera_id=cam.id,
                    file_path=str(mp4_file),
                    file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                    started_at=started_at,
                    ended_at=None,
                    duration_s=None,
                    codec="H264",
                    is_protected=False,
                    is_encoded_av1=False,
                )
                db.add(rec)
                inserted += 1

            except Exception as e:
                errors.append({"file": str(mp4_file), "error": str(e)})

    await db.commit()

    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
        "errors": len(errors),
        "error_details": errors[:10],  # Max 10 error ditampilkan
    }


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    return rec


@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Stream file video untuk playback di browser dengan Range header support."""
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")

    range_header = request.headers.get("range")
    if range_header:
        try:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            file_size = file_path.stat().st_size
            end = int(end) if end else file_size - 1
        except Exception:
            start, end = 0, file_path.stat().st_size - 1
            file_size  = file_path.stat().st_size

        chunk_size = 1024 * 1024
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(min(end - start + 1, chunk_size))

        from fastapi.responses import Response
        headers = {
            "Content-Range":  f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(len(data)),
            "Content-Type":   "video/mp4",
        }
        return Response(data, status_code=206, headers=headers)

    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Rekaman tidak ditemukan")

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")

    try:
        ts = datetime.fromisoformat(str(rec.started_at)).strftime("%Y-%m-%d_%H-%M-%S")
    except Exception:
        ts = "unknown"
    cam_slug = (rec.camera_id or "cam").replace("-", "_")
    download_name = f"{cam_slug}_{ts}.mp4"

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@router.get("/{camera_id}/timeline")
async def get_timeline(
    camera_id: str,
    date: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        date_obj  = datetime.strptime(date, "%Y-%m-%d")
        date_from = date_obj.replace(hour=0,  minute=0,  second=0)
        date_to   = date_obj.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    recording_repo = RecordingRepository(db)
    recordings     = await recording_repo.get_by_camera_and_date(camera_id, date_from, date_to)
    event_repo     = EventRepository(db)
    events         = await event_repo.get_by_camera_and_date(camera_id, date_from, date_to)

    timeline = []
    for hour in range(24):
        hour_start = date_obj.replace(hour=hour, minute=0,  second=0)
        hour_end   = date_obj.replace(hour=hour, minute=59, second=59)
        timeline.append({
            "hour":          hour,
            "has_recording": any(hour_start <= rec.started_at.replace(tzinfo=None) <= hour_end for rec in recordings),
            "has_motion":    any(hour_start <= evt.started_at.replace(tzinfo=None) <= hour_end for evt in events),
        })

    return {
        "camera_id":        camera_id,
        "date":             date,
        "timeline":         timeline,
        "total_recordings": len(recordings),
        "total_events":     len(events),
    }


@router.post("/{recording_id}/protect")
async def toggle_protect(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("operator")),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    rec.is_protected = not rec.is_protected
    await db.commit()
    return {"is_protected": rec.is_protected}


@router.delete("/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    if rec.is_protected:
        raise HTTPException(status_code=400, detail="Rekaman dilindungi, lepas proteksi dulu")
    Path(rec.file_path).unlink(missing_ok=True)
    await repo.delete_by_id(recording_id)
