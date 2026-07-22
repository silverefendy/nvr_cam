"""
Router: /api/v1/stream
Live HLS streaming dari kamera.
FFmpeg konversi RTSP → HLS segments di /tmp/hls/{camera_id}/
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Literal

from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User
from backend.core.config import settings
from backend.services.recorder.ffmpeg_wrapper import build_snapshot_command
import subprocess

router = APIRouter(tags=["stream"])


@router.get("/{camera_id}/live")
async def get_live_url(
    camera_id: str,
    stream: Literal["main", "sub"] = Query("sub", description="Stream type: main (HD) atau sub (SD, hemat bandwidth)"),
    _: User = Depends(get_current_user),
):
    """
    Dapatkan URL HLS untuk live view kamera.

    Query param:
    - stream=sub  → sub stream (default, SD, hemat bandwidth untuk monitoring)
    - stream=main → main stream (HD, resolusi penuh)

    Frontend (C-11 toggle MAIN/SUB) mengirim param ini.
    HLS segments disimpan di folder terpisah agar keduanya bisa berjalan bersamaan.
    """
    return {
        "hls_url": f"/api/v1/stream/{camera_id}/{stream}/index.m3u8",
        "camera_id": camera_id,
        "stream": stream,
    }


@router.get("/{camera_id}/{stream_type}/index.m3u8")
async def serve_hls_playlist(
    camera_id: str,
    stream_type: Literal["main", "sub"],
    _: User = Depends(get_current_user),
):
    """
    Serve HLS playlist file.
    Folder: /tmp/hls/{camera_id}/{stream_type}/index.m3u8
    Dipisah per stream type agar main dan sub tidak conflict.
    """
    hls_path = Path(settings.hls_temp_dir) / camera_id / stream_type / "index.m3u8"
    if not hls_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"HLS playlist tidak ditemukan untuk kamera {camera_id} stream {stream_type}"
        )

    return FileResponse(hls_path, media_type="application/vnd.apple.mpegurl")


@router.get("/{camera_id}/{stream_type}/segment/{filename}")
async def serve_hls_segment(
    camera_id: str,
    stream_type: Literal["main", "sub"],
    filename: str,
    _: User = Depends(get_current_user),
):
    """Serve HLS segment file (.ts) per stream type."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / stream_type / filename
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS segment not found")

    return FileResponse(hls_path, media_type="video/mp2t")


# ─── Legacy endpoints (backward compat, tanpa stream_type) ──────────────────
# Tetap dipertahankan sementara agar tidak breaking change
# TODO: hapus setelah semua FFmpeg worker sudah pakai path baru

@router.get("/{camera_id}/index.m3u8")
async def serve_hls_playlist_legacy(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    """[Legacy] Serve HLS playlist tanpa stream_type — fallback ke sub."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / "index.m3u8"
    if not hls_path.exists():
        # Coba fallback ke sub folder
        hls_path = Path(settings.hls_temp_dir) / camera_id / "sub" / "index.m3u8"
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS playlist not found")
    return FileResponse(hls_path, media_type="application/vnd.apple.mpegurl")


@router.get("/{camera_id}/segment/{filename}")
async def serve_hls_segment_legacy(
    camera_id: str,
    filename: str,
    _: User = Depends(get_current_user),
):
    """[Legacy] Serve HLS segment tanpa stream_type."""
    hls_path = Path(settings.hls_temp_dir) / camera_id / filename
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS segment not found")
    return FileResponse(hls_path, media_type="video/mp2t")


@router.get("/{camera_id}/snapshot.jpg")
async def get_snapshot(
    camera_id: str,
    request: Request,
    stream: Literal["main", "sub"] = Query("sub", description="Stream untuk snapshot"),
    _: User = Depends(get_current_user),
):
    """Capture dan serve snapshot dari kamera."""
    from backend.db.base import AsyncSessionLocal
    from backend.db.repositories.camera_repo import CameraRepository

    async with AsyncSessionLocal() as db:
        repo = CameraRepository(db)
        camera = await repo.get_by_id(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        # Pilih RTSP URL sesuai stream type
        if stream == "main":
            rtsp_url = camera.rtsp_main
        else:
            rtsp_url = camera.rtsp_sub or camera.rtsp_main

    snapshot_dir = Path(settings.hls_temp_dir) / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{camera_id}_{stream}_snapshot.jpg"

    cmd = build_snapshot_command(rtsp_url, str(snapshot_path))
    try:
        subprocess.run(cmd, timeout=10, capture_output=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture snapshot: {e}")

    if not snapshot_path.exists():
        raise HTTPException(status_code=500, detail="Snapshot file not created")

    return FileResponse(snapshot_path, media_type="image/jpeg")
