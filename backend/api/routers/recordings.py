"""
Router: /api/v1/recordings
List, playback, protect, delete rekaman.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.api.schemas.recording import RecordingResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User

router = APIRouter(tags=["recordings"])


@router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    camera_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    has_motion: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman dengan filter opsional."""
    repo = RecordingRepository(db)
    if camera_id and date_from and date_to:
        recordings = await repo.get_by_camera_and_date(camera_id, date_from, date_to)
    else:
        recordings = await repo.get_all()
    return recordings


@router.get("/{recording_id}", response_model=RecordingResponse)
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Stream file video untuk playback langsung di browser."""
    repo = RecordingRepository(db)
    rec = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")
    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)


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
