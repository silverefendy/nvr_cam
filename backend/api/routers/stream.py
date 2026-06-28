"""
Router: /api/v1/stream
Live HLS streaming dari kamera.
FFmpeg konversi RTSP → HLS segments di /tmp/hls/{camera_id}/
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User
from backend.core.config import settings
from backend.services.recorder.ffmpeg_wrapper import build_snapshot_command
import subprocess

router = APIRouter(tags=["stream"])


@router.get("/{camera_id}/live")
async def get_live_url(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    """Dapatkan URL HLS untuk live view kamera."""
    return {
        "hls_url": f"/api/v1/stream/{camera_id}/index.m3u8",
        "camera_id": camera_id,
    }


@router.get("/{camera_id}/index.m3u8")
async def serve_hls_playlist(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    """Serve HLS playlist file."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / "index.m3u8"
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS playlist not found")

    return FileResponse(hls_path, media_type="application/vnd.apple.mpegurl")


@router.get("/{camera_id}/segment/{filename}")
async def serve_hls_segment(
    camera_id: str,
    filename: str,
    _: User = Depends(get_current_user),
):
    """Serve HLS segment file (.ts)."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / filename
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS segment not found")

    return FileResponse(hls_path, media_type="video/mp2t")


@router.get("/{camera_id}/snapshot.jpg")
async def get_snapshot(
    camera_id: str,
    request: Request,
    _: User = Depends(get_current_user),
):
    """Capture and serve a snapshot from the camera."""
    # Get camera RTSP URL from database
    from backend.db.base import AsyncSessionLocal
    from backend.db.repositories.camera_repo import CameraRepository
    
    async with AsyncSessionLocal() as db:
        repo = CameraRepository(db)
        camera = await repo.get_by_id(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        rtsp_url = camera.rtsp_main
    
    # Generate snapshot path
    snapshot_dir = Path(settings.hls_temp_dir) / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{camera_id}_snapshot.jpg"
    
    # Capture snapshot using FFmpeg
    cmd = build_snapshot_command(rtsp_url, str(snapshot_path))
    try:
        subprocess.run(cmd, timeout=10, capture_output=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture snapshot: {e}")
    
    if not snapshot_path.exists():
        raise HTTPException(status_code=500, detail="Snapshot file not created")
    
    return FileResponse(snapshot_path, media_type="image/jpeg")
