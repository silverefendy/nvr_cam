"""
Router: /api/v1/stream
Live HLS streaming dari kamera.
FFmpeg konversi RTSP → HLS segments di /tmp/hls/{camera_id}/
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User
from backend.core.config import settings

router = APIRouter(tags=["stream"])


@router.get("/{camera_id}/live")
async def get_live_url(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    """Dapatkan URL HLS untuk live view kamera."""
    # TODO: pastikan FFmpeg HLS process sudah berjalan untuk kamera ini
    return {
        "hls_url": f"/api/v1/stream/{camera_id}/hls/index.m3u8",
        "camera_id": camera_id,
    }


@router.get("/{camera_id}/hls/{filename:path}")
async def serve_hls(
    camera_id: str,
    filename: str,
    _: User = Depends(get_current_user),
):
    """Serve file HLS (.m3u8 playlist dan .ts segments)."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / filename
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS segment tidak ditemukan")

    media_type = "application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/mp2t"
    return FileResponse(hls_path, media_type=media_type)
