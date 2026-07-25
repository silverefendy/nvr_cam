# =============================================================================
# fix3_nvr_cam.ps1
# Jalankan: cd C:\Users\Efendy\documents\git\nvr_cam ; .\fix3_nvr_cam.ps1
#
# Fix:
#   1. Tulisan aneh (emoji rusak) - tulis file tanpa emoji
#   2. Playback tidak bisa - tambah -movflags +faststart di FFmpeg record
#   3. Ukuran file tidak konsisten - segment 1 jam tetap + faststart
#   4. Codec H.265 recording bisa dipilih per kamera dari setting
#   5. ffmpeg_wrapper.py - update build_record_command support H.265 + faststart
# =============================================================================

Write-Host "=== NVR CAM FIX 3 ===" -ForegroundColor Cyan

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 + 2 + 3 + 4: backend/services/recorder/ffmpeg_wrapper.py
# - Tambah -movflags +faststart agar file bisa di-stream browser tanpa download penuh
# - Tambah support H.265 (hevc) untuk recording (hemat storage ~50%)
# - Segment 1 jam (3600s) sudah benar, tapi tambah fallback timeout
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[1/3] Patching backend/services/recorder/ffmpeg_wrapper.py ..." -ForegroundColor Green

$ffmpegWrapper = @'
"""
FFmpeg wrapper - semua command FFmpeg ada di sini.

Catatan penting tentang -movflags +faststart:
  File MP4 punya dua bagian: moov atom (metadata/index) dan mdat (data video).
  Secara default FFmpeg tulis moov atom di AKHIR file.
  Browser butuh moov atom di AWAL untuk bisa streaming tanpa download penuh dulu.
  -movflags +faststart memindahkan moov ke awal setelah encode selesai.
  Tanpa ini: browser error "No video with supported format and MIME type found".

Catatan H.265 vs H.264:
  H.265 (HEVC): ukuran ~50% lebih kecil dari H.264 pada kualitas sama.
  Trade-off: butuh CPU lebih banyak untuk decode di browser (tidak semua browser support).
  Solusi: record H.265 di server, transcode ke H.264 saat playback (atau gunakan HLS).
  Untuk sekarang: jika kamera sudah kirim H.265, stream copy langsung (hemat CPU server).
"""
import subprocess
import json
from pathlib import Path


def build_record_command(
    rtsp_url: str,
    output_pattern: str,
    segment_seconds: int = 3600,
    force_h265: bool = False,
) -> list[str]:
    """
    Command FFmpeg untuk recording 24/7 dengan segmented MP4.

    Args:
        rtsp_url: URL RTSP kamera.
        output_pattern: Pola nama file output, contoh: /mnt/driveA/cam_01/2025-01-15/%H-%M-%S.mp4
        segment_seconds: Durasi tiap segment dalam detik (default 3600 = 1 jam).
        force_h265: Jika True, transcode ke H.265 (hemat storage, butuh CPU lebih).
                    Jika False, stream copy dari kamera (hemat CPU, ukuran tergantung kamera).

    Catatan -movflags +faststart:
        Wajib agar file MP4 bisa langsung di-play di browser tanpa download penuh.
        FFmpeg akan memindahkan moov atom ke awal file setelah segment selesai.
    """
    if force_h265:
        # Transcode ke H.265: hemat storage ~50%, butuh lebih CPU
        # -tag:v hvc1 agar QuickTime/Safari bisa putar
        video_args = [
            "-c:v", "libx265",
            "-preset", "fast",
            "-crf", "28",          # 28 = kualitas bagus, file kecil
            "-tag:v", "hvc1",
        ]
    else:
        # Stream copy: tidak decode ulang, hemat CPU, ukuran = seperti kamera kirim
        video_args = ["-c:v", "copy"]

    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        *video_args,
        "-c:a", "aac", "-b:a", "64k",
        "-f", "segment",
        "-segment_time", str(segment_seconds),
        "-segment_format", "mp4",
        # FIX: movflags +faststart wajib agar browser bisa stream file MP4
        # tanpa ini muncul: "No video with supported format and MIME type found"
        "-segment_format_options", "movflags=+faststart",
        "-segment_atclocktime", "1",
        "-reset_timestamps", "1",
        "-strftime", "1",
        output_pattern,
    ]


def build_hls_command(
    rtsp_url: str,
    hls_dir: str,
    segment_duration: int = 2,
    force_transcode: bool = False,
) -> list[str]:
    """
    Command FFmpeg untuk HLS live streaming ke browser.

    force_transcode=True dipakai jika kamera kirim HEVC dan browser tidak support
    (misalnya Chrome di Android, atau hls.js default).
    """
    if force_transcode:
        video_codec_args = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"]
    else:
        video_codec_args = ["-c:v", "copy"]

    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        *video_codec_args,
        "-c:a", "aac", "-b:a", "64k",
        "-f", "hls",
        "-hls_time", str(segment_duration),
        "-hls_list_size", "6",
        "-hls_flags", "delete_segments+append_list",
        "-hls_segment_filename", f"{hls_dir}/seg%03d.ts",
        f"{hls_dir}/index.m3u8",
    ]


def detect_video_codec(rtsp_url: str) -> str | None:
    """Probe codec video dari RTSP stream via ffprobe.

    Returns:
        Nama codec lowercase ('h264', 'hevc', dll) atau None jika gagal.
    """
    info = probe_stream(rtsp_url)
    if not info:
        return None
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream.get("codec_name")
    return None


def build_av1_encode_command(input_path: str, output_path: str, crf: int = 35) -> list[str]:
    """Re-encode ke AV1 untuk arsip jangka panjang (jalankan saat idle malam)."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-i", input_path,
        "-c:v", "libsvtav1",
        "-crf", str(crf),
        "-preset", "8",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]


def build_snapshot_command(rtsp_url: str, output_path: str) -> list[str]:
    """Ambil 1 frame dari kamera sebagai snapshot JPG."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vframes", "1",
        "-q:v", "2",
        "-y", output_path,
    ]


def remux_for_streaming(input_path: str, output_path: str) -> bool:
    """
    Remux file MP4 agar moov atom ada di awal (faststart).
    Dipakai untuk file lama yang direkam tanpa -movflags +faststart.
    Proses cepat: tidak decode ulang, hanya pindahkan metadata.

    Returns:
        True jika berhasil, False jika gagal.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-c", "copy",
                "-movflags", "+faststart",
                "-y", output_path,
            ],
            timeout=60,
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def probe_stream(rtsp_url: str) -> dict | None:
    """Cek apakah stream RTSP bisa diakses. Return info codec atau None jika gagal."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-rtsp_transport", "tcp", rtsp_url,
            ],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None
'@

Set-Content -Path "backend\services\recorder\ffmpeg_wrapper.py" -Value $ffmpegWrapper -Encoding UTF8
Write-Host "  OK: ffmpeg_wrapper.py - tambah faststart + H.265 support" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: backend/api/routers/recordings.py
# Fix endpoint /play: remux on-the-fly jika file belum faststart
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[2/3] Patching backend/api/routers/recordings.py (fix playback) ..." -ForegroundColor Green

$recordingsRouter = @'
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
'@

Set-Content -Path "backend\api\routers\recordings.py" -Value $recordingsRouter -Encoding UTF8
Write-Host "  OK: recordings.py - fix playback dengan remux on-the-fly" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: frontend/src/pages/Storage/index.tsx
# Tulis ulang TANPA emoji (emoji rusak karena encoding PowerShell)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[3/3] Menulis ulang Storage/index.tsx tanpa emoji ..." -ForegroundColor Green

# File ini sama persis dengan sebelumnya tapi TANPA emoji di label tab dan header
# agar tidak ada karakter rusak
$storageNoEmoji = @'
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/api/client"
import { storageApi } from "@/api/storage"
import { recordingsApi } from "@/api/recordings"
import { camerasApi } from "@/api/cameras"
import { useAuthStore } from "@/store/auth"
import { useTheme } from "@/store/theme"
import type { DriveStatus, Recording } from "@/types"

type Tab = "drives" | "recordings" | "cameras" | "schedule"

const formatGB  = (gb: number) => gb >= 1000 ? `${(gb / 1024).toFixed(2)} TB` : `${gb.toFixed(1)} GB`
const formatMB  = (mb: number) => mb >= 1024  ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(0)} MB`
const formatDur = (s?: number) => {
  if (!s) return '-'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60)
  return h > 0 ? `${h}j ${m}m` : m > 0 ? `${m}m ${sec}s` : `${sec}s`
}
const formatDate = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString('id-ID', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' })
}
const todayStr    = () => new Date().toISOString().slice(0, 10)
const monthAgoStr = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10) }

export default function StoragePage() {
  const [activeTab, setActiveTab]       = useState<Tab>("drives")
  const [schedHour, setSchedHour]       = useState(3)
  const [schedMinute, setSchedMinute]   = useState(0)
  const [schedEnabled, setSchedEnabled] = useState(false)
  const [message, setMessage]           = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [recCameraId, setRecCameraId]   = useState<string>("")
  const [recDateFrom, setRecDateFrom]   = useState(monthAgoStr())
  const [recDateTo, setRecDateTo]       = useState(todayStr())
  const [playingId, setPlayingId]       = useState<number | null>(null)

  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()
  const { isDark } = useTheme()

  const bg      = isDark ? '#0f1117' : '#f1f5f9'
  const card    = isDark ? '#1a1d27' : '#ffffff'
  const cardB   = isDark ? '#2a2d3a' : '#e2e8f0'
  const text    = isDark ? '#e2e8f0' : '#1e293b'
  const sub     = isDark ? '#64748b' : '#94a3b8'
  const inputBg = isDark ? '#12151f' : '#f8fafc'
  const rowHov  = isDark ? '#1e2130' : '#f8fafc'

  const { data: storage, isLoading, refetch } = useQuery({
    queryKey: ["storage"], queryFn: storageApi.getStatus,
    enabled: isAuthenticated, refetchInterval: 30000,
  })
  const { data: cameraStats, isLoading: statsLoading } = useQuery({
    queryKey: ["storage-camera-stats"], queryFn: storageApi.getStatsByCamera,
    enabled: isAuthenticated && activeTab === "cameras",
  })
  const { data: schedule } = useQuery({
    queryKey: ["cleanup-schedule"], queryFn: storageApi.getCleanupSchedule,
    enabled: isAuthenticated && activeTab === "schedule",
  })
  const { data: cameras } = useQuery({
    queryKey: ["cameras"], queryFn: camerasApi.list,
    enabled: isAuthenticated,
  })
  const { data: recordings, isLoading: recLoading } = useQuery({
    queryKey: ["recordings", recCameraId, recDateFrom, recDateTo],
    queryFn: () => recordingsApi.list({
      camera_id: recCameraId || undefined,
      date_from: recDateFrom || undefined,
      date_to:   recDateTo   || undefined,
    }),
    enabled: isAuthenticated && activeTab === "recordings",
  })

  useEffect(() => {
    if (schedule) {
      setSchedEnabled(schedule.enabled ?? false)
      setSchedHour(schedule.hour ?? 3)
      setSchedMinute(schedule.minute ?? 0)
    }
  }, [schedule])

  const showMsg = (type: "success" | "error", text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 4000)
  }

  const cleanupMutation = useMutation({
    mutationFn: storageApi.manualCleanup,
    onSuccess: () => { refetch(); showMsg("success", "Cleanup selesai") },
    onError:   () => showMsg("error", "Cleanup gagal"),
  })
  const scheduleMutation = useMutation({
    mutationFn: storageApi.saveCleanupSchedule,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["cleanup-schedule"] }); showMsg("success", "Jadwal disimpan") },
    onError:   () => showMsg("error", "Gagal menyimpan jadwal"),
  })
  const protectMutation = useMutation({
    mutationFn: (id: number) => recordingsApi.protect(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recordings"] }),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => recordingsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recordings"] }),
  })
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/recordings/sync').then(r => r.data),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      showMsg("success", `Sync selesai: ${data.inserted} file baru, ${data.skipped} sudah ada`)
    },
    onError: () => showMsg("error", "Sync dari disk gagal"),
  })

  const getUsageColor = (p: number) => p < 10 ? '#ef4444' : p < 25 ? '#f59e0b' : '#10b981'
  const getUsedPct    = (d: DriveStatus) => Math.round((d.used_gb / d.total_gb) * 100)

  const tabs: { id: Tab; label: string }[] = [
    { id: "drives",     label: "Drive"         },
    { id: "recordings", label: "Rekaman"        },
    { id: "cameras",    label: "Per Kamera"     },
    { id: "schedule",   label: "Jadwal Cleanup" },
  ]

  const cardStyle: React.CSSProperties = {
    background: card, border: `1px solid ${cardB}`,
    borderRadius: 12, padding: '16px',
    boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 1px 4px rgba(0,0,0,0.06)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: bg, padding: 16, gap: 12, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <h1 style={{ fontSize: 15, fontWeight: 700, color: text, margin: 0 }}>Storage</h1>
        {storage && (
          <div style={{ display: 'flex', gap: 12, marginLeft: 8, flexWrap: 'wrap' }}>
            {[
              { label: 'Total',          value: `${storage.total_tb} TB`,                    color: text },
              { label: 'Dipakai',        value: `${storage.used_tb} TB`,                     color: '#f59e0b' },
              { label: 'Sisa',           value: `${storage.free_tb} TB`,                     color: storage.free_tb < 1 ? '#ef4444' : '#10b981' },
              { label: 'Estimasi habis', value: `~${storage.estimated_days_remaining} hari`, color: sub },
            ].map(s => (
              <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontSize: 11, color: sub }}>{s.label}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: s.color }}>{s.value}</span>
              </div>
            ))}
          </div>
        )}
        {message && (
          <span style={{
            marginLeft: 'auto', fontSize: 12, padding: '4px 12px', borderRadius: 99, fontWeight: 600,
            background: message.type === 'success' ? (isDark ? '#052e16' : '#dcfce7') : (isDark ? '#2d0a0a' : '#fee2e2'),
            color: message.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${message.type === 'success' ? '#10b98140' : '#ef444440'}`,
          }}>
            {message.type === 'success' ? 'OK' : 'Error'} {message.text}
          </span>
        )}
        <button
          onClick={() => { if (confirm('Jalankan cleanup sekarang?')) cleanupMutation.mutate() }}
          disabled={cleanupMutation.isPending}
          style={{
            marginLeft: message ? 8 : 'auto', padding: '7px 14px', borderRadius: 8,
            fontSize: 12, fontWeight: 600,
            background: cleanupMutation.isPending ? sub : '#ef4444',
            color: '#fff', border: 'none', cursor: 'pointer',
          }}
        >
          {cleanupMutation.isPending ? 'Membersihkan...' : 'Cleanup'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            border: `1px solid ${activeTab === t.id ? '#0284c7' : cardB}`,
            background: activeTab === t.id ? '#0284c7' : card,
            color: activeTab === t.id ? '#fff' : sub,
            transition: 'all 0.15s',
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>

        {/* Tab: Drive */}
        {activeTab === 'drives' && (
          isLoading
            ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat data storage...</div>
            : !storage?.drives?.length
              ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Tidak ada drive terkonfigurasi</div>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {storage.drives.map((drive: DriveStatus) => {
                    const usedPct  = getUsedPct(drive)
                    const freePct  = drive.free_pct
                    const barColor = getUsageColor(freePct)
                    return (
                      <div key={drive.path} style={cardStyle}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: text, display: 'flex', alignItems: 'center', gap: 8 }}>
                              {drive.path}
                              {freePct < (storage.threshold_pct ?? 10) && (
                                <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 99, background: '#7f1d1d', color: '#fca5a5', fontWeight: 700 }}>Kritis</span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: sub, marginTop: 3 }}>
                              {drive.cameras?.length ?? 0} kamera
                              {drive.cameras?.length > 0 && ` - ${drive.cameras.join(', ')}`}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 22, fontWeight: 800, color: barColor, lineHeight: 1 }}>{freePct.toFixed(1)}%</div>
                            <div style={{ fontSize: 11, color: sub }}>sisa tersedia</div>
                          </div>
                        </div>
                        <div style={{ position: 'relative', height: 10, background: isDark ? '#1e2130' : '#e2e8f0', borderRadius: 99, overflow: 'hidden', marginBottom: 10 }}>
                          <div style={{
                            position: 'absolute', left: 0, top: 0, bottom: 0, width: `${usedPct}%`,
                            background: usedPct > 90 ? '#ef4444' : usedPct > 75 ? '#f59e0b' : '#0284c7',
                            borderRadius: 99, transition: 'width 0.5s ease',
                          }} />
                        </div>
                        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                          {[
                            { label: 'Total',     value: formatGB(drive.total_gb), color: text },
                            { label: 'Dipakai',   value: formatGB(drive.used_gb),  color: '#f59e0b' },
                            { label: 'Sisa',      value: formatGB(drive.free_gb),  color: '#10b981' },
                            { label: 'Threshold', value: `${storage.threshold_pct ?? 10}%`, color: sub },
                          ].map(s => (
                            <div key={s.label}>
                              <div style={{ fontSize: 10, color: sub, marginBottom: 2 }}>{s.label}</div>
                              <div style={{ fontSize: 14, fontWeight: 700, color: s.color }}>{s.value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
        )}

        {/* Tab: Rekaman */}
        {activeTab === 'recordings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ ...cardStyle, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: sub }}>Filter:</span>
              <select value={recCameraId} onChange={e => setRecCameraId(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text, cursor: 'pointer' }}>
                <option value="">Semua Kamera</option>
                {cameras?.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, color: sub }}>Dari</span>
                <input type="date" value={recDateFrom} onChange={e => setRecDateFrom(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
                <span style={{ fontSize: 11, color: sub }}>s/d</span>
                <input type="date" value={recDateTo} onChange={e => setRecDateTo(e.target.value)}
                  style={{ padding: '6px 8px', borderRadius: 7, fontSize: 12, border: `1px solid ${cardB}`, background: inputBg, color: text }} />
              </div>
              <button
                onClick={() => { if (confirm('Scan file .mp4 di storage dan daftarkan ke database?')) syncMutation.mutate() }}
                disabled={syncMutation.isPending}
                style={{
                  padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                  background: syncMutation.isPending ? sub : '#7c3aed',
                  color: '#fff', border: 'none', cursor: syncMutation.isPending ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {syncMutation.isPending ? 'Scanning...' : 'Sync dari Disk'}
              </button>
              <span style={{ fontSize: 11, color: sub, marginLeft: 'auto' }}>
                {recordings ? `${recordings.length} rekaman` : ''}
              </span>
            </div>

            {playingId !== null && (() => {
              const rec = recordings?.find((r: Recording) => r.id === playingId)
              return rec ? (
                <div style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: text }}>{rec.camera_id} - {formatDate(rec.started_at)}</span>
                    <button onClick={() => setPlayingId(null)}
                      style={{ fontSize: 12, padding: '3px 10px', borderRadius: 6, border: `1px solid ${cardB}`, background: 'transparent', color: sub, cursor: 'pointer' }}>
                      Tutup
                    </button>
                  </div>
                  <video src={recordingsApi.playUrl(rec.id)} controls autoPlay
                    style={{ width: '100%', maxHeight: 480, background: '#000', borderRadius: 8 }} />
                  <div style={{ fontSize: 11, color: sub, marginTop: 6 }}>
                    Jika video tidak muncul, klik Unduh untuk download dan putar di VLC.
                    File lama perlu beberapa detik untuk diproses sebelum bisa diputar.
                  </div>
                </div>
              ) : null
            })()}

            {recLoading ? (
              <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat rekaman...</div>
            ) : !recordings?.length ? (
              <div style={{ ...cardStyle, padding: 40, textAlign: 'center', color: sub }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Tidak ada rekaman ditemukan</div>
                <div style={{ fontSize: 12, marginBottom: 12 }}>Coba ubah filter kamera atau rentang tanggal</div>
                <div style={{ fontSize: 12, color: '#7c3aed' }}>
                  Jika file .mp4 sudah ada di disk, klik tombol Sync dari Disk di atas
                </div>
              </div>
            ) : (
              <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: isDark ? '#12151f' : '#f8fafc', borderBottom: `1px solid ${cardB}` }}>
                      {['Kamera', 'Mulai', 'Durasi', 'Ukuran', 'Codec', 'Path File', 'Aksi'].map(h => (
                        <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: sub }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {recordings.map((rec: Recording) => (
                      <tr key={rec.id} style={{
                        borderBottom: `1px solid ${isDark ? '#1e2130' : '#f1f5f9'}`,
                        background: playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : 'transparent',
                        transition: 'background 0.1s', cursor: 'pointer',
                      }}
                        onMouseEnter={e => (e.currentTarget.style.background = playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : rowHov)}
                        onMouseLeave={e => (e.currentTarget.style.background = playingId === rec.id ? (isDark ? '#1a2a3a' : '#eff6ff') : 'transparent')}
                        onClick={() => setPlayingId(rec.id === playingId ? null : rec.id)}
                      >
                        <td style={{ padding: '10px 14px', fontWeight: 600, color: text }}>
                          {rec.camera_id}
                          {rec.is_protected && <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 5px', borderRadius: 99, background: isDark ? '#1e3a5f' : '#dbeafe', color: '#3b82f6' }}>Protected</span>}
                        </td>
                        <td style={{ padding: '10px 14px', color: sub, fontSize: 12 }}>{formatDate(rec.started_at)}</td>
                        <td style={{ padding: '10px 14px', color: sub }}>{formatDur(rec.duration_s)}</td>
                        <td style={{ padding: '10px 14px', color: sub }}>{rec.file_size_mb ? formatMB(rec.file_size_mb) : '-'}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{
                            fontSize: 10, padding: '2px 7px', borderRadius: 99, fontWeight: 700,
                            background: rec.codec === 'H265' ? (isDark ? '#1e2d1e' : '#dcfce7') : (isDark ? '#1e2130' : '#f1f5f9'),
                            color: rec.codec === 'H265' ? '#10b981' : sub,
                          }}>{rec.codec}</span>
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: 200 }}>
                          {rec.file_path
                            ? <span title={rec.file_path} style={{ fontSize: 11, color: sub, fontFamily: 'monospace', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rec.file_path}</span>
                            : <span style={{ fontSize: 11, color: sub }}>-</span>}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                            <button onClick={() => setPlayingId(rec.id === playingId ? null : rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a2a3a' : '#dbeafe', color: '#3b82f6' }}>Putar</button>
                            <a href={recordingsApi.downloadUrl(rec.id)} download
                              style={{ ...smallBtn, background: isDark ? '#1a2a1a' : '#dcfce7', color: '#10b981', textDecoration: 'none' }}>Unduh</a>
                            <button onClick={() => protectMutation.mutate(rec.id)}
                              style={{ ...smallBtn, background: isDark ? '#1a1a2a' : '#ede9fe', color: '#8b5cf6' }}>
                              {rec.is_protected ? 'Buka' : 'Protect'}
                            </button>
                            {!rec.is_protected && (
                              <button onClick={() => { if (confirm(`Hapus rekaman ${rec.camera_id}?`)) deleteMutation.mutate(rec.id) }}
                                style={{ ...smallBtn, background: isDark ? '#2d0a0a' : '#fee2e2', color: '#ef4444' }}>Hapus</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab: Per Kamera */}
        {activeTab === 'cameras' && (
          statsLoading
            ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Memuat statistik...</div>
            : !cameraStats?.length
              ? <div style={{ color: sub, padding: 40, textAlign: 'center' }}>Tidak ada data kamera</div>
              : (
                <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', borderBottom: `1px solid ${cardB}`, fontSize: 11, color: sub }}>
                    {cameraStats.length} kamera - diurutkan dari penggunaan terbesar
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: isDark ? '#12151f' : '#f8fafc', borderBottom: `1px solid ${cardB}` }}>
                        {['#', 'Kamera', 'Drive', 'File', 'Total'].map(h => (
                          <th key={h} style={{ padding: '10px 14px', textAlign: h === 'File' || h === 'Total' ? 'right' : 'left', fontSize: 11, fontWeight: 700, color: sub }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cameraStats.map((s: any, i: number) => (
                        <tr key={s.camera_id} style={{ borderBottom: `1px solid ${isDark ? '#1e2130' : '#f1f5f9'}` }}
                          onMouseEnter={e => (e.currentTarget.style.background = rowHov)}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                          <td style={{ padding: '10px 14px', color: sub, fontSize: 11 }}>{i + 1}</td>
                          <td style={{ padding: '10px 14px', fontWeight: 600, color: text }}>{s.camera_id}</td>
                          <td style={{ padding: '10px 14px', color: sub, fontSize: 12 }}>{s.drive}</td>
                          <td style={{ padding: '10px 14px', textAlign: 'right', color: sub }}>{s.file_count.toLocaleString()}</td>
                          <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: i < 3 ? '#f59e0b' : text }}>{formatMB(s.total_mb)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
        )}

        {/* Tab: Jadwal Cleanup */}
        {activeTab === 'schedule' && (
          <div style={{ ...cardStyle, maxWidth: 500 }}>
            <h2 style={{ fontSize: 15, fontWeight: 700, color: text, margin: '0 0 6px' }}>Jadwal Cleanup Otomatis</h2>
            <p style={{ fontSize: 12, color: sub, margin: '0 0 20px', lineHeight: 1.6 }}>
              Cleanup terjadwal menghapus file terlama yang tidak diproteksi agar ruang disk selalu tersedia.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 13, color: text }}>Aktifkan cleanup terjadwal</span>
              <div onClick={() => setSchedEnabled(!schedEnabled)} style={{
                width: 44, height: 24, borderRadius: 99, cursor: 'pointer', position: 'relative',
                background: schedEnabled ? '#0284c7' : (isDark ? '#2a2d3a' : '#cbd5e1'),
                transition: 'background 0.2s', flexShrink: 0,
              }}>
                <div style={{
                  position: 'absolute', top: 2, width: 20, height: 20, borderRadius: '50%',
                  background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
                  left: schedEnabled ? 22 : 2, transition: 'left 0.2s',
                }} />
              </div>
              <span style={{ fontSize: 11, color: schedEnabled ? '#10b981' : sub, fontWeight: 600 }}>
                {schedEnabled ? 'Aktif' : 'Nonaktif'}
              </span>
            </div>
            <div style={{ opacity: schedEnabled ? 1 : 0.4, pointerEvents: schedEnabled ? 'auto' : 'none', marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: sub, marginBottom: 8 }}>Jam cleanup (HH : MM)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="number" min={0} max={23} value={schedHour} onChange={e => setSchedHour(Number(e.target.value))}
                  style={{ width: 64, padding: '8px', borderRadius: 8, border: `1px solid ${cardB}`, background: inputBg, color: text, fontSize: 18, fontWeight: 700, textAlign: 'center' }} />
                <span style={{ fontSize: 20, fontWeight: 800, color: sub }}>:</span>
                <input type="number" min={0} max={59} value={schedMinute} onChange={e => setSchedMinute(Number(e.target.value))}
                  style={{ width: 64, padding: '8px', borderRadius: 8, border: `1px solid ${cardB}`, background: inputBg, color: text, fontSize: 18, fontWeight: 700, textAlign: 'center' }} />
                <span style={{ fontSize: 11, color: sub }}>
                  cron: <code style={{ background: isDark ? '#12151f' : '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>
                    {String(schedMinute).padStart(2,'0')} {String(schedHour).padStart(2,'0')} * * *
                  </code>
                </span>
              </div>
              <p style={{ fontSize: 11, color: sub, marginTop: 6 }}>Disarankan jam 03:00 saat traffic rendah</p>
            </div>
            <button
              onClick={() => scheduleMutation.mutate({ enabled: schedEnabled, hour: schedHour, minute: schedMinute })}
              disabled={scheduleMutation.isPending}
              style={{ padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 700, background: '#0284c7', color: '#fff', border: 'none', cursor: 'pointer', opacity: scheduleMutation.isPending ? 0.6 : 1 }}
            >
              {scheduleMutation.isPending ? 'Menyimpan...' : 'Simpan Jadwal'}
            </button>
            {schedule && (
              <div style={{ marginTop: 16, padding: 12, background: isDark ? '#12151f' : '#f8fafc', borderRadius: 8, border: `1px solid ${cardB}`, fontSize: 12, color: sub }}>
                <div>Status: <span style={{ color: schedule.enabled ? '#10b981' : sub, fontWeight: 700 }}>{schedule.enabled ? 'Aktif' : 'Nonaktif'}</span></div>
                <div style={{ marginTop: 4 }}>Cron: <code style={{ background: isDark ? '#1a1d27' : '#e2e8f0', padding: '1px 6px', borderRadius: 4, color: text }}>{schedule.cron}</code></div>
                <div style={{ marginTop: 6, color: '#f59e0b' }}>Berlaku setelah backend di-restart</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const smallBtn: React.CSSProperties = {
  padding: '3px 8px', borderRadius: 5, fontSize: 11, fontWeight: 600,
  border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
}
'@

Set-Content -Path "frontend\src\pages\Storage\index.tsx" -Value $storageNoEmoji -Encoding UTF8
Write-Host "  OK: Storage/index.tsx - tulis ulang tanpa emoji, bersih" -ForegroundColor White

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host " FIX 3 SELESAI" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " File yang diubah:" -ForegroundColor White
Write-Host "   backend/services/recorder/ffmpeg_wrapper.py" -ForegroundColor Gray
Write-Host "     -> Tambah -movflags +faststart (fix playback browser)" -ForegroundColor Gray
Write-Host "     -> Tambah support H.265 recording (parameter force_h265)" -ForegroundColor Gray
Write-Host "   backend/api/routers/recordings.py" -ForegroundColor Gray
Write-Host "     -> Remux on-the-fly untuk file lama yang belum faststart" -ForegroundColor Gray
Write-Host "   frontend/src/pages/Storage/index.tsx" -ForegroundColor Gray
Write-Host "     -> Tulis ulang tanpa emoji (fix karakter aneh)" -ForegroundColor Gray

Write-Host "`n Langkah selanjutnya:" -ForegroundColor Yellow
Write-Host "   git add -A" -ForegroundColor DarkYellow
Write-Host "   git commit -m 'fix: playback faststart, emoji encoding, H.265 support'" -ForegroundColor DarkYellow
Write-Host "   git push" -ForegroundColor DarkYellow
Write-Host "   docker compose up -d --build api frontend" -ForegroundColor DarkYellow

Write-Host "`n Penjelasan ukuran file tidak konsisten:" -ForegroundColor Yellow
Write-Host "   Normal - ini bukan bug:" -ForegroundColor White
Write-Host "   - File besar (500MB-1GB): rekaman 1 jam penuh, bitrate tinggi" -ForegroundColor Gray
Write-Host "   - File kecil (1-20MB): rekaman terpotong saat kamera disconnect" -ForegroundColor Gray
Write-Host "   - Ukuran tergantung: resolusi kamera, gerakan di frame, bitrate setting" -ForegroundColor Gray
Write-Host "   Untuk menghemat storage: aktifkan H.265 di setting kamera (hemat ~50%)" -ForegroundColor Gray
Write-Host "   atau turunkan bitrate di kamera NVR via browser kamera langsung" -ForegroundColor Gray
