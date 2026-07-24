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


def build_hls_command(
    rtsp_url: str,
    hls_dir: str,
    segment_duration: int = 2,
    force_transcode: bool = False,
) -> list[str]:
    """Bangun command FFmpeg untuk HLS live streaming ke browser.

    Args:
        rtsp_url: URL RTSP sumber kamera.
        hls_dir: Direktori output HLS (index.m3u8 + seg*.ts).
        segment_duration: Durasi tiap segment HLS dalam detik (default 2).
        force_transcode: Paksa transcode ke H.264 agar kompatibel hls.js di browser.
                         Set True otomatis jika codec kamera terdeteksi HEVC/H.265.
                         False = stream copy (lebih efisien, tapi tidak jalan di browser
                         jika kamera kirim HEVC).
    """
    if force_transcode:
        # Transcode HEVC → H.264 agar bisa diputar hls.js di semua browser
        # -preset ultrafast: prioritas kecepatan (perlu untuk real-time)
        # -crf 23: kualitas seimbang (0=lossless, 51=worst)
        video_codec_args = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"]
    else:
        # Stream copy: tidak decode ulang, hemat CPU, hanya jalan jika codec H.264
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
    """Probe codec video dari RTSP stream.

    Returns:
        Nama codec lowercase ('h264', 'hevc', 'h265', dll) atau None jika gagal.

    Contoh penggunaan:
        codec = detect_video_codec("rtsp://admin:pass@10.1.0.100/stream1")
        force_transcode = codec in ("hevc", "h265")
    """
    info = probe_stream(rtsp_url)
    if not info:
        return None
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream.get("codec_name")  # 'hevc', 'h264', 'h265', dll
    return None


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
