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
        video_args = [
            "-c:v", "libx265",
            "-preset", "fast",
            "-crf", "28",
            "-tag:v", "hvc1",
        ]
    else:
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
    Dipakai untuk file H.264 lama yang direkam tanpa -movflags +faststart.
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
            timeout=300,  # 5 menit — lebih aman untuk file besar
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


def probe_codec_from_file(file_path: str) -> str | None:
    """
    Probe codec video dari file lokal (bukan RTSP stream).
    Dipakai saat playback untuk cek apakah file perlu di-transcode.

    Returns:
        Nama codec lowercase: 'h264', 'hevc', 'av1', dll — atau None jika gagal.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", file_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    return stream.get("codec_name")  # 'h264', 'hevc', dll
    except Exception:
        pass
    return None


def transcode_to_h264(input_path: str, output_path: str) -> bool:
    """
    Transcode file HEVC/H.265 ke H.264 MP4 agar bisa diputar di browser
    via HTML5 <video> tag (Chrome/Firefox tidak support HEVC natively).

    Proses ini memakan waktu untuk file besar — hasilnya di-cache di tmp_dir
    agar tidak perlu transcode ulang setiap request playback.

    Returns:
        True jika berhasil, False jika gagal.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "64k",
                "-movflags", "+faststart",
                "-y", output_path,
            ],
            timeout=1200,  # 20 menit max untuk file sangat besar (600MB+)
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False
