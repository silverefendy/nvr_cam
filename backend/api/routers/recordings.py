"""
Router: /api/v1/recordings
List, playback, download, protect, delete rekaman.
POST /sync: scan file di disk dan daftarkan ke DB.
"""
from datetime import datetime
from pathlib import Path
import tempfile
import os
from fastapi import APIRouter, Depends, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.recording import Recording
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User
from backend.services.recorder.ffmpeg_wrapper import remux_for_streaming

router = APIRouter(tags=["recordings"])

# Cache file yang sudah di-remux agar tidak proses ulang setiap request
_remux_cache: dict[int, str] = {}


@router.get("")
async def list_recordings(
    camera_id: str | None = Query(None),
    date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman. Tanpa filter: 500 terbaru."""
    repo = RecordingRepository(db)
    if camera_id and date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            recordings = await repo.get_by_camera_and_date(
                camera_id,
                date_obj.replace(hour=0, minute=0, second=0),
                date_obj.replace(hour=23, minute=59, second=59),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")
    elif camera_id:
        recordings = await repo.get_by_camera(camera_id)
    elif date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            recordings = await repo.get_by_date_range(
                date_obj.replace(hour=0, minute=0, second=0),
                date_obj.replace(hour=23, minute=59, second=59),
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")
    else:
        recordings = await repo.get_recent(limit=500)
    return recordings


@router.post("/sync")
async def sync_recordings_from_disk(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Scan semua file .mp4 di storage dan daftarkan yang belum ada di DB.
    Berguna untuk rekaman lama sebelum patch atau setelah DB reset.
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

        for mp4_file in sorted(cam_dir.rglob("*.mp4")):
            try:
                existing = await db.execute(
                    select(Recording).where(Recording.file_path == str(mp4_file))
                )
                if existing.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                stat = mp4_file.stat()
                if stat.st_size < 1024:
                    continue

                try:
                    date_str = mp4_file.parent.name
                    time_str = mp4_file.stem
                    started_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H-%M-%S")
                except ValueError:
                    started_at = datetime.fromtimestamp(stat.st_mtime)

                # Estimasi durasi dari ukuran file (kasar)
                size_mb = stat.st_size / (1024 * 1024)
                # ~1MB per menit untuk H.264 720p, ~2MB untuk 1080p
                estimated_duration_s = int(size_mb * 30)

                rec = Recording(
                    camera_id=cam.id,
                    file_path=str(mp4_file),
                    file_size_mb=round(size_mb, 2),
                    started_at=started_at,
                    ended_at=None,
                    duration_s=estimated_duration_s,
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
        "error_details": errors[:10],
    }


@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Stream file MP4 ke browser dengan Range header support.

    FIX: File lama yang direkam tanpa -movflags +faststart tidak bisa
    langsung di-stream browser karena moov atom ada di akhir file.
    Solusi: remux on-the-fly ke file temp, lalu serve file temp tersebut.
    File baru (setelah patch) sudah punya faststart jadi langsung jalan.
    """
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ditemukan di disk")

    # Cek apakah file sudah punya moov di awal (faststart)
    # Cara cepat: baca 8 byte pertama dan cek apakah ada 'ftyp' atau 'moov'
    serve_path = file_path
    is_faststart = _check_faststart(file_path)

    if not is_faststart:
        # File lama: cek cache dulu
        if recording_id in _remux_cache and Path(_remux_cache[recording_id]).exists():
            serve_path = Path(_remux_cache[recording_id])
        else:
            # Remux ke file temp
            tmp_dir = Path(tempfile.gettempdir()) / "nvr_remux"
            tmp_dir.mkdir(exist_ok=True)
            tmp_file = tmp_dir / f"rec_{recording_id}.mp4"

            if not tmp_file.exists():
                success = remux_for_streaming(str(file_path), str(tmp_file))
                if success:
                    _remux_cache[recording_id] = str(tmp_file)
                    serve_path = tmp_file
                # else: serve file asli (mungkin gagal di browser tapi tidak crash server)

    # Serve dengan Range support
    file_size = serve_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        try:
            range_val = range_header.replace("bytes=", "")
            start_str, end_str = range_val.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else min(start + 1024 * 1024 - 1, file_size - 1)
        except Exception:
            start, end = 0, min(1024 * 1024 - 1, file_size - 1)

        chunk_size = end - start + 1
        with open(serve_path, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)

        headers = {
            "Content-Range":  f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(len(data)),
            "Content-Type":   "video/mp4",
        }
        return Response(data, status_code=206, headers=headers)

    return FileResponse(
        serve_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )


def _check_faststart(file_path: Path) -> bool:
    """
    Cek apakah file MP4 punya moov atom di awal (faststart).
    Baca 12 byte pertama: jika ada 'ftyp' atau 'moov' di offset 4, berarti faststart.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(12)
        if len(header) < 8:
            return False
        # Box type ada di byte 4-8
        box_type = header[4:8]
        return box_type in (b'ftyp', b'moov')
    except Exception:
        return False


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan di disk")

    try:
        ts = datetime.fromisoformat(str(rec.started_at)).strftime("%Y-%m-%d_%H-%M-%S")
    except Exception:
        ts = "unknown"
    cam_slug = (rec.camera_id or "cam").replace("-", "_")
    filename = f"{cam_slug}_{ts}.mp4"

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
        raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")

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
            "has_recording": any(hour_start <= r.started_at.replace(tzinfo=None) <= hour_end for r in recordings),
            "has_motion":    any(hour_start <= e.started_at.replace(tzinfo=None) <= hour_end for e in events),
        })
    return {
        "camera_id": camera_id, "date": date,
        "timeline": timeline,
        "total_recordings": len(recordings),
        "total_events": len(events),
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
        raise HTTPException(status_code=400, detail="Rekaman dilindungi. Lepas proteksi dulu.")
    try:
        Path(rec.file_path).unlink(missing_ok=True)
        # Hapus juga cache remux jika ada
        if recording_id in _remux_cache:
            Path(_remux_cache.pop(recording_id)).unlink(missing_ok=True)
    except Exception:
        pass
    await repo.delete_by_id(recording_id)
