"""
Router: /api/v1/recordings
List, playback, protect, delete rekaman.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository
from backend.api.schemas.recording import RecordingResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User

router = APIRouter(tags=["recordings"])


@router.get("")
async def list_recordings(
    camera_id: str | None = Query(None),
    date: str | None = Query(None),  # YYYY-MM-DD format
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman dengan filter opsional."""
    repo = RecordingRepository(db)
    
    if camera_id and date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_from = date_obj.replace(hour=0, minute=0, second=0)
            date_to = date_obj.replace(hour=23, minute=59, second=59)
            recordings = await repo.get_by_camera_and_date(camera_id, date_from, date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        recordings = await repo.get_all()
    
    return recordings


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


@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Stream file video untuk playback langsung di browser with Range header support."""
    repo = RecordingRepository(db)
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")
    
    # Handle Range header for video scrubbing
    range_header = request.headers.get("range")
    if range_header:
        # Parse Range header (e.g., "bytes=0-1023")
        try:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            end = int(end) if end else file_path.stat().st_size - 1
        except:
            start = 0
            end = file_path.stat().st_size - 1
        
        file_size = file_path.stat().st_size
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(min(end - start + 1, chunk_size))
        
        from fastapi.responses import Response
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Content-Type": "video/mp4",
        }
        return Response(data, status_code=206, headers=headers)
    
    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)


@router.get("/{camera_id}/timeline")
async def get_timeline(
    camera_id: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get timeline data for a camera on a specific date."""
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_from = date_obj.replace(hour=0, minute=0, second=0)
        date_to = date_obj.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get recordings for the day
    recording_repo = RecordingRepository(db)
    recordings = await recording_repo.get_by_camera_and_date(camera_id, date_from, date_to)
    
    # Get motion events for the day
    event_repo = EventRepository(db)
    events = await event_repo.get_by_camera_and_date(camera_id, date_from, date_to)
    
    # Build timeline (hourly blocks)
    timeline = []
    for hour in range(24):
        hour_start = date_obj.replace(hour=hour, minute=0, second=0)
        hour_end = date_obj.replace(hour=hour, minute=59, second=59)
        
        # Check if any recording exists in this hour
        has_recording = any(
            hour_start <= rec.started_at <= hour_end 
            for rec in recordings
        )
        
        # Check if any motion event exists in this hour
        has_motion = any(
            hour_start <= evt.started_at <= hour_end 
            for evt in events
        )
        
        timeline.append({
            "hour": hour,
            "has_recording": has_recording,
            "has_motion": has_motion
        })
    
    return {
        "camera_id": camera_id,
        "date": date,
        "timeline": timeline,
        "total_recordings": len(recordings),
        "total_events": len(events)
    }


@router.post("/{recording_id}/protect")
async def toggle_protect(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("operator")),
):
    """Lock/unlock rekaman agar tidak ikut auto-delete."""
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = RecordingRepository(db)
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    if rec.is_protected:
        raise HTTPException(status_code=400, detail="Rekaman dilindungi, lepas proteksi dulu")
    Path(rec.file_path).unlink(missing_ok=True)
    await repo.delete_by_id(recording_id)
