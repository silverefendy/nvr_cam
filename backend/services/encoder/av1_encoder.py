"""
AV1 Encoder — re-encode rekaman H.264/H.265 ke AV1 saat server idle.
Dijadwalkan otomatis tiap malam (01:00-05:00) via scheduler.
"""
import subprocess
import os
from pathlib import Path
from backend.core.logging import get_logger
from backend.services.recorder.ffmpeg_wrapper import build_av1_encode_command

logger = get_logger(__name__, service="encoder")


def encode_to_av1(input_path: str, crf: int = 35) -> bool:
    """
    Re-encode 1 file ke AV1. Return True jika berhasil.
    File asli dihapus setelah encode berhasil diverifikasi.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        return False

    output_path = str(input_p.with_suffix(".av1.mp4"))
    cmd = build_av1_encode_command(input_path, output_path, crf=crf)

    logger.info(f"Encode AV1: {input_p.name}")
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        logger.error(f"Encode gagal: {result.stderr.decode()[:200]}")
        Path(output_path).unlink(missing_ok=True)
        return False

    # Verifikasi output valid
    original_size = input_p.stat().st_size
    new_size = Path(output_path).stat().st_size
    if new_size < original_size * 0.1:  # output terlalu kecil = korup
        logger.error(f"Output AV1 mencurigakan ({new_size} bytes), batalkan")
        Path(output_path).unlink(missing_ok=True)
        return False

    # Ganti file asli dengan AV1
    input_p.unlink()
    Path(output_path).rename(input_p)
    reduction = (1 - new_size / original_size) * 100
    logger.info(f"Encode selesai: hemat {reduction:.1f}% ({original_size//1024//1024}MB → {new_size//1024//1024}MB)")
    return True
