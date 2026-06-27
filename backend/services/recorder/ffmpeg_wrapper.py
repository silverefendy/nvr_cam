"""
FFmpeg wrapper — semua perintah FFmpeg ada di sini.
Tidak ada string FFmpeg tersebar di tempat lain.
"""
import subprocess
from pathlib import Path
from datetime import datetime


def build_record_command(rtsp_url: str, output_pattern: str) -> list[str]:
    """Bangun command FFmpeg untuk recording 24/7 dengan segmented output."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c", "copy",              # stream copy — TIDAK decode ulang
        "-f", "segment",
        "-segment_time", "3600",   # 1 jam per file
        "-segment_format", "mp4",
        "-segment_atclocktime", "1",
        "-reset_timestamps", "1",
        "-strftime", "1",
        output_pattern,            # cth: /mnt/driveE/cam_01/2025-01-15/%H-%M-%S.mp4
    ]


def build_hls_command(rtsp_url: str, hls_dir: str, segment_duration: int = 2) -> list[str]:
    """Bangun command FFmpeg untuk HLS live streaming ke browser."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "64k",
        "-f", "hls",
        "-hls_time", str(segment_duration),
        "-hls_list_size", "6",
        "-hls_flags", "delete_segments+append_list",
        "-hls_segment_filename", f"{hls_dir}/seg%03d.ts",
        f"{hls_dir}/index.m3u8",
    ]


def build_av1_encode_command(input_path: str, output_path: str, crf: int = 35) -> list[str]:
    """Bangun command FFmpeg untuk re-encode ke AV1 (saat idle malam hari)."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-i", input_path,
        "-c:v", "libsvtav1",
        "-crf", str(crf),
        "-preset", "8",            # 0=lambat/kecil, 12=cepat/besar
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]


def build_snapshot_command(rtsp_url: str, output_path: str) -> list[str]:
    """Ambil 1 frame dari kamera sebagai JPG snapshot."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vframes", "1",
        "-q:v", "2",
        "-y", output_path,
    ]


def probe_stream(rtsp_url: str) -> dict | None:
    """Cek apakah stream RTSP bisa diakses. Return info codec atau None jika gagal."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-rtsp_transport", "tcp", rtsp_url],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
    except Exception:
        pass
    return None
