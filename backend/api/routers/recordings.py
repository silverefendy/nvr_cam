"""
Router: /api/v1/recordings
List, playback, download, protect, delete rekaman.
POST /sync: scan file di disk dan daftarkan ke DB.
"""
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os
from fastapi import APIRouter, Depends, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.recording import Recording
from backend.api.middleware.auth import get_current_user, get_current_user_flexible, require_role
from backend.db.models.user import User
from backend.services.recorder.ffmpeg_wrapper import probe_codec_from_file
from backend.services.audit import write_audit_log
from backend.services.transcode_queue import TranscodeQueue

router = APIRouter(tags=["recordings"])

# Cache file yang sudah di-remux/transcode agar tidak proses ulang setiap request
# key: recording_id, value: path ke file hasil remux/transcode
_remux_cache: dict[int, str] = {}


@router.get("")
async def list_recordings(
    camera_id: str | None = Query(None),
    date: str | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman. Tanpa filter: 500 terbaru."""
    repo = RecordingRepository(db)
    if start or end:
        start_dt = start or datetime.min
        end_dt = end or datetime.max
        recordings = await repo.get_by_date_range(start_dt, end_dt)
        if camera_id:
            recordings = [r for r in recordings if r.camera_id == camera_id]
    elif camera_id and date:
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

    # FIX: Filter rekaman dengan file_size_mb = 0 agar tidak muncul di UI
    # File 0MB adalah file yang gagal direkam (FFmpeg crash sebelum write data)
    return [r for r in recordings if (r.file_size_mb or 0) > 0]


@router.post("/sync")
async def sync_recordings_from_disk(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Scan semua file .mp4 di storage dan daftarkan yang belum ada di DB.
    Berguna untuk rekaman lama sebelum patch atau setelah DB reset.
    File 0MB otomatis diabaikan.
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

                # Probe codec aktual dari file
                codec_name = probe_codec_from_file(str(mp4_file))
                if codec_name in ("hevc", "h265"):
                    codec_str = "H265"
                else:
                    codec_str = "H264"

                # Estimasi durasi dari ukuran file (kasar)
                size_mb = stat.st_size / (1024 * 1024)
                estimated_duration_s = int(size_mb * 30)

                rec = Recording(
                    camera_id=cam.id,
                    file_path=str(mp4_file),
                    file_size_mb=round(size_mb, 2),
                    started_at=started_at,
                    ended_at=None,
                    duration_s=estimated_duration_s,
                    codec=codec_str,
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
    _: User = Depends(get_current_user_flexible),
):
    """
    Stream file MP4 ke browser dengan Range header support.

    Pipeline:
    1. Probe codec file (ffprobe) — cepat, hanya baca metadata
    2. Jika HEVC/H.265 → transcode ke H.264 (cache di /tmp/nvr_remux/)
    3. Jika H.264 tapi tidak faststart → remux copy (cepat, <1 menit)
    4. Jika H.264 + faststart → serve langsung

    Note:
    - Transcode HEVC file besar (100MB+) bisa makan 2-10 menit pertama kali.
      Request berikutnya serve dari cache.
    - Cache hilang saat container restart → transcode ulang pertama kali.
    - Token auth via query param ?token=... agar browser bisa akses URL video langsung.
    """
    repo = RecordingRepository(db)
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ditemukan di disk")

    # Tolak file 0MB — tidak ada data video yang bisa diputar
    file_size_actual = file_path.stat().st_size
    if file_size_actual < 1024:
        raise HTTPException(
            status_code=422,
            detail="File rekaman kosong (0MB) — kemungkinan rekaman gagal dimulai"
        )

    serve_path = file_path

    # --- Step 1: Cek cache dulu ---
    if recording_id in _remux_cache:
        cached = Path(_remux_cache[recording_id])
        if cached.exists():
            serve_path = cached
        else:
            # Cache sudah dihapus (container restart)
            del _remux_cache[recording_id]

    # --- Step 2: Probe codec + queue processing jika belum ada di cache ---
    if serve_path == file_path:
        loop = __import__('asyncio').get_event_loop()

        # Probe codec file (non-blocking)
        codec = await loop.run_in_executor(
            None, probe_codec_from_file, str(file_path)
        )

        tmp_dir = Path(tempfile.gettempdir()) / "nvr_remux"
        tmp_dir.mkdir(exist_ok=True)

        if codec in ("hevc", "h265"):
            tmp_file = tmp_dir / f"rec_{recording_id}_h264.mp4"
            if tmp_file.exists():
                _remux_cache[recording_id] = str(tmp_file)
                serve_path = tmp_file
            else:
                queue = TranscodeQueue.get_instance()
                queue.start()
                job_id = queue.add_job(recording_id)
                return JSONResponse(
                    status_code=202,
                    content={
                        "job_id": job_id,
                        "status": "queued",
                        "status_url": f"/api/v1/recordings/{recording_id}/play/status?job_id={job_id}",
                    },
                )

        else:
            # H.264 atau codec lain — cek faststart
            is_faststart = _check_faststart(file_path)
            if not is_faststart:
                # Remux untuk pindahkan moov atom ke awal
                tmp_file = tmp_dir / f"rec_{recording_id}.mp4"
                if tmp_file.exists():
                    _remux_cache[recording_id] = str(tmp_file)
                    serve_path = tmp_file
                else:
                    queue = TranscodeQueue.get_instance()
                    queue.start()
                    job_id = queue.add_job(recording_id)
                    return JSONResponse(
                        status_code=202,
                        content={
                            "job_id": job_id,
                            "status": "queued",
                            "status_url": f"/api/v1/recordings/{recording_id}/play/status?job_id={job_id}",
                        },
                    )
            # else: H.264 + faststart → serve_path masih file_path, langsung serve

    # --- Step 3: Serve dengan Range support ---
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
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Content-Type": "video/mp4",
        }
        return Response(data, status_code=206, headers=headers)

    return FileResponse(
        serve_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/{recording_id}/play/status")
async def play_recording_status(
    recording_id: int,
    job_id: str | None = Query(None),
    _: User = Depends(get_current_user_flexible),
):
    queue = TranscodeQueue.get_instance()
    status_data = queue.get_status(job_id) if job_id else queue.get_status_by_recording(recording_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job playback tidak ditemukan")
    return status_data


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
    rec = await repo.get_by_id(recording_id)
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
    rec = await repo.get_by_id(recording_id)
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
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_from = date_obj.replace(hour=0, minute=0, second=0)
        date_to = date_obj.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")

    recording_repo = RecordingRepository(db)
    recordings = await recording_repo.get_by_camera_and_date(camera_id, date_from, date_to)
    event_repo = EventRepository(db)
    events = await event_repo.get_by_camera_and_date(camera_id, date_from, date_to)

    timeline = []
    for hour in range(24):
        hour_start = date_obj.replace(hour=hour, minute=0, second=0)
        hour_end = date_obj.replace(hour=hour, minute=59, second=59)
        timeline.append({
            "hour": hour,
            "has_recording": any(hour_start <= r.started_at.replace(tzinfo=None) <= hour_end for r in recordings),
            "has_motion": any(hour_start <= e.started_at.replace(tzinfo=None) <= hour_end for e in events),
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
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    rec.is_protected = not rec.is_protected
    await db.commit()
    return {"is_protected": rec.is_protected}


@router.delete("/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    repo = RecordingRepository(db)
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    if rec.is_protected:
        raise HTTPException(status_code=400, detail="Rekaman dilindungi. Lepas proteksi dulu.")
    try:
        Path(rec.file_path).unlink(missing_ok=True)
        # Hapus juga cache remux/transcode jika ada
        if recording_id in _remux_cache:
            Path(_remux_cache.pop(recording_id)).unlink(missing_ok=True)
    except Exception:
        pass
    await repo.delete_by_id(recording_id)
    await write_audit_log(
        db,
        action="recording.delete",
        user_id=current_user.id,
        target_type="recording",
        target_id=str(recording_id),
        detail={"camera_id": rec.camera_id, "file_path": rec.file_path},
        ip_address=request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# Footage Export Endpoints
# ---------------------------------------------------------------------------
from pydantic import BaseModel
import uuid

class ExportRequest(BaseModel):
    camera_id: str
    start_time: datetime
    end_time: datetime


# Global in-memory export job tracker
# key: job_id, value: {"status": str, "file_path": str, "error": str}
_export_jobs: dict[str, dict] = {}


async def _run_export_background(job_id: str, camera_id: str, start_time: datetime, end_time: datetime):
    from backend.services.recorder.exporter import export_footage
    from backend.db.base import AsyncSessionLocal

    _export_jobs[job_id]["status"] = "processing"
    try:
        async with AsyncSessionLocal() as db:
            file_path = await export_footage(db, camera_id, start_time, end_time)
            _export_jobs[job_id]["status"] = "done"
            _export_jobs[job_id]["file_path"] = file_path
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[EXPORT] Job {job_id} failed: {e}")
        _export_jobs[job_id]["status"] = "failed"
        _export_jobs[job_id]["error"] = str(e)


@router.post("/export")
async def trigger_footage_export(
    body: ExportRequest,
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_user),
):
    """
    Queue a background task to merge and export footage from a custom time range.
    """
    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail="Waktu selesai harus setelah waktu mulai")

    duration = body.end_time - body.start_time
    if duration > timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Rentang waktu export maksimal 24 jam")

    job_id = str(uuid.uuid4())
    _export_jobs[job_id] = {
        "status": "queued",
        "file_path": None,
        "error": None
    }

    background_tasks.add_task(
        _run_export_background,
        job_id,
        body.camera_id,
        body.start_time,
        body.end_time
    )

    return {
        "job_id": job_id,
        "status": "queued"
    }


@router.get("/export/{job_id}")
async def get_export_status(
    job_id: str,
    _: User = Depends(get_current_user),
):
    """
    Get the status of an export job.
    """
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Pekerjaan export tidak ditemukan")

    response = {
        "status": job["status"],
        "download_url": f"/api/v1/recordings/export/{job_id}/download" if job["status"] == "done" else None
    }
    if job["error"]:
        response["error"] = job["error"]
    return response


@router.get("/export/{job_id}/download")
async def download_exported_file(
    job_id: str,
    _: User = Depends(get_current_user),
):
    """
    Stream/download the exported video file.
    """
    job = _export_jobs.get(job_id)
    if not job or job["status"] != "done" or not job["file_path"]:
        raise HTTPException(status_code=404, detail="File hasil export tidak ditemukan atau belum selesai")

    file_path = Path(job["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File hasil export sudah dibersihkan atau tidak ada")

    filename = file_path.name
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
