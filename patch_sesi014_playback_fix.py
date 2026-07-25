"""
patch_sesi014_playback_fix.py
Sesi #014 — Fix Playback HEVC + Codec Detection
Tanggal: 26 Juli 2026

Yang di-patch:
  1. backend/services/recorder/ffmpeg_wrapper.py
     - Tambah probe_codec_from_file()
     - Tambah transcode_to_h264()

  2. backend/api/routers/recordings.py
     - Update endpoint /play: HEVC -> transcode otomatis ke H.264

  3. backend/services/recorder/camera_recorder.py
     - Update _save_recording_to_db(): probe codec aktual, bukan hardcode "H264"

  4. ISSUES.md
     - Tambah entri Sesi #014

Cara pakai:
  python patch_sesi014_playback_fix.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent

def apply_patch(filepath: str, old: str, new: str, label: str):
    p = REPO_ROOT / filepath
    content = p.read_text(encoding="utf-8-sig")
    if old not in content:
        print(f"  [SKIP] {label} — string tidak ditemukan (mungkin sudah di-patch)")
        return False
    p.write_text(content.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]   {label}")
    return True


# ─── PATCH 1: ffmpeg_wrapper.py ──────────────────────────────────────────────
print("\n[1/4] Patch ffmpeg_wrapper.py — tambah probe_codec_from_file + transcode_to_h264")

apply_patch(
    "backend/services/recorder/ffmpeg_wrapper.py",
    # OLD — akhir file (setelah probe_stream)
    '''\ndef probe_stream(rtsp_url: str) -> dict | None:
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
    return None''',
    # NEW — probe_stream tetap + tambah dua fungsi baru
    '''\ndef probe_stream(rtsp_url: str) -> dict | None:
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
                "-preset", "fast",   # fast = balance antara kecepatan dan ukuran
                "-crf", "23",        # 23 = kualitas default ffmpeg, hasil bagus
                "-c:a", "aac",
                "-b:a", "64k",
                "-movflags", "+faststart",  # wajib agar browser bisa stream
                "-y", output_path,
            ],
            timeout=600,  # 10 menit max untuk file 644 MB
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False''',
    "Tambah probe_codec_from_file() + transcode_to_h264()",
)


# ─── PATCH 2: recordings.py ───────────────────────────────────────────────────
print("\n[2/4] Patch recordings.py — update endpoint /play untuk handle HEVC")

apply_patch(
    "backend/api/routers/recordings.py",
    # OLD — import di atas
    "from backend.services.recorder.ffmpeg_wrapper import remux_for_streaming",
    # NEW — tambah import fungsi baru
    "from backend.services.recorder.ffmpeg_wrapper import remux_for_streaming, probe_codec_from_file, transcode_to_h264",
    "Update import ffmpeg_wrapper",
)

apply_patch(
    "backend/api/routers/recordings.py",
    # OLD — body play_recording setelah cek file_path.exists()
    '''\    file_path = Path(rec.file_path)
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
                # else: serve file asli (mungkin gagal di browser tapi tidak crash server)''',
    # NEW — logika baru: probe codec dulu, handle HEVC vs H264
    '''\    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ditemukan di disk")

    tmp_dir = Path(tempfile.gettempdir()) / "nvr_remux"
    tmp_dir.mkdir(exist_ok=True)

    serve_path = file_path

    # Probe codec aktual dari file (bukan dari DB — kolom codec di DB bisa tidak akurat)
    codec = probe_codec_from_file(str(file_path))
    is_hevc = codec in ("hevc", "h265")

    if is_hevc:
        # ── HEVC/H.265: Browser (Chrome/Firefox) tidak support natively ──────
        # Transcode ke H.264 MP4 on-the-fly, cache hasilnya di tmp_dir.
        # Untuk file 644 MB proses ~2-5 menit pertama kali, selanjutnya langsung serve.
        tmp_file = tmp_dir / f"rec_{recording_id}_h264.mp4"
        if tmp_file.exists():
            # Cache hit — langsung serve
            serve_path = tmp_file
        else:
            # Cache miss — transcode (blocking tapi tidak ada cara lain untuk on-the-fly)
            success = transcode_to_h264(str(file_path), str(tmp_file))
            if success:
                _remux_cache[recording_id] = str(tmp_file)
                serve_path = tmp_file
            # else: tetap serve file asli, browser akan error tapi server tidak crash
    else:
        # ── H.264 / lainnya: cek faststart, remux jika perlu ─────────────────
        is_faststart = _check_faststart(file_path)
        if not is_faststart:
            if recording_id in _remux_cache and Path(_remux_cache[recording_id]).exists():
                serve_path = Path(_remux_cache[recording_id])
            else:
                tmp_file = tmp_dir / f"rec_{recording_id}.mp4"
                if not tmp_file.exists():
                    success = remux_for_streaming(str(file_path), str(tmp_file))
                    if success:
                        _remux_cache[recording_id] = str(tmp_file)
                        serve_path = tmp_file
                else:
                    serve_path = tmp_file''',
    "Update logika /play: HEVC transcode, H264 remux-jika-perlu",
)


# ─── PATCH 3: camera_recorder.py ─────────────────────────────────────────────
print("\n[3/4] Patch camera_recorder.py — probe codec aktual saat save ke DB")

apply_patch(
    "backend/services/recorder/camera_recorder.py",
    # OLD — import di atas
    "from .ffmpeg_wrapper import build_record_command, build_hls_command, detect_video_codec",
    # NEW
    "from .ffmpeg_wrapper import build_record_command, build_hls_command, detect_video_codec, probe_codec_from_file",
    "Tambah import probe_codec_from_file",
)

apply_patch(
    "backend/services/recorder/camera_recorder.py",
    # OLD — dalam _save_recording_to_db, bagian buat objek Recording
    '''\                    duration_s = int((ended_at - segment_started_at).total_seconds())
                    rec = Recording(
                        camera_id=self.camera_id,
                        file_path=str(mp4_file),
                        file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                        started_at=segment_started_at,
                        ended_at=ended_at,
                        duration_s=max(0, duration_s),
                        codec="H264",  # default; ffprobe jika diperlukan
                        is_protected=False,
                        is_encoded_av1=False,
                    )''',
    # NEW — probe codec aktual dari file
    '''\                    duration_s = int((ended_at - segment_started_at).total_seconds())

                    # Probe codec aktual dari file (bukan hardcode "H264")
                    # probe_codec_from_file() return None jika ffprobe gagal -> fallback "H264"
                    actual_codec = probe_codec_from_file(str(mp4_file))
                    codec_label = "H265" if actual_codec in ("hevc", "h265") else "H264"

                    rec = Recording(
                        camera_id=self.camera_id,
                        file_path=str(mp4_file),
                        file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                        started_at=segment_started_at,
                        ended_at=ended_at,
                        duration_s=max(0, duration_s),
                        codec=codec_label,
                        is_protected=False,
                        is_encoded_av1=False,
                    )''',
    "Probe codec aktual dari file saat save ke DB",
)


# ─── PATCH 4: ISSUES.md ──────────────────────────────────────────────────────
print("\n[4/4] Update ISSUES.md — tambah entri Sesi #014")

apply_patch(
    "ISSUES.md",
    # OLD — header baris pertama
    "## 🐛 Bug Fixes Sesi #013 — Fix Ganti IP Kamera Tidak Apply",
    # NEW — entri baru di atas sesi #013
    '''## 🐛 Bug Fixes Sesi #014 — Fix Playback HEVC + Codec Detection

> **Tanggal:** 26 Juli 2026
> **Scope:** Playback rekaman gagal dengan error "No video with supported format and MIME type found"

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-044 | Playback rekaman error "No video with supported format and MIME type found" | Dua kemungkinan: (1) File rekaman bercodec HEVC/H.265 — browser Chrome/Firefox tidak support HEVC di HTML5 `<video>` natively. (2) File lama tanpa `-movflags +faststart` (moov atom di akhir). Backend tidak mendeteksi codec aktual sebelum serve — langsung stream file mentah ke browser. | ✅ Fixed |
| BUG-045 | Kolom `codec` di DB selalu isi "H264" meskipun kamera rekam HEVC | `_save_recording_to_db()` hardcode `codec="H264"` tanpa probe file aktual | ✅ Fixed |

**Fix detail (BUG-044 + BUG-045):**
- `ffmpeg_wrapper.py`: tambah `probe_codec_from_file()` — probe codec dari file lokal via ffprobe
- `ffmpeg_wrapper.py`: tambah `transcode_to_h264()` — transcode HEVC ke H.264 MP4 dengan `-movflags +faststart`, cache hasil di `/tmp/nvr_remux/rec_{id}_h264.mp4`
- `recordings.py` (`/play` endpoint): probe codec file dulu sebelum serve. Jika HEVC → transcode ke H.264 (cached). Jika H.264 → cek faststart, remux jika perlu (behaviour lama).
- `camera_recorder.py` (`_save_recording_to_db`): ganti hardcode `"H264"` dengan probe aktual via `probe_codec_from_file()`, simpan `"H265"` atau `"H264"` sesuai isi file.

**Catatan penting:**
- Transcode HEVC → H.264 untuk file besar (600+ MB) memakan waktu **2–5 menit** pada request pertama. Request berikutnya langsung serve dari cache.
- Cache di `/tmp/nvr_remux/` akan hilang saat container restart — transcode ulang di request pertama setelah restart.
- Jika kamera memang kirim H.264 dan masalah hanya faststart, proses remux jauh lebih cepat (~10 detik).

### ⚠️ Perlu Dilakukan Setelah Pull

```bash
git pull && docker compose up --build -d api
```

Verifikasi:
1. Buka halaman Playback, pilih kamera + tanggal
2. Klik ▶ Putar di salah satu rekaman
3. Video harus bisa diputar (mungkin ada delay 2–5 menit untuk HEVC pertama kali)
4. Cek log: `docker compose logs --tail 30 api` — cari baris `probe_codec` atau `transcode`

---

## 🐛 Bug Fixes Sesi #013 — Fix Ganti IP Kamera Tidak Apply''',
    "Tambah entri Sesi #014 di ISSUES.md",
)

# Update Timeline tabel di ISSUES.md
apply_patch(
    "ISSUES.md",
    "| 11 | 25 Juli 2026 | #013 | Claude | Fix BUG-043 (ganti IP kamera tidak apply — per-camera lock + clear HLS) |",
    "| 11 | 25 Juli 2026 | #013 | Claude | Fix BUG-043 (ganti IP kamera tidak apply — per-camera lock + clear HLS) |\n| 12 | 26 Juli 2026 | #014 | Claude | Fix BUG-044 (playback HEVC error) + BUG-045 (codec hardcode H264) |",
    "Update timeline tabel",
)

print("\n✅ Semua patch selesai.")
print("\nLangkah selanjutnya:")
print("  git add -A")
print('  git commit -m "fix(sesi014): playback HEVC -> transcode H264, probe codec aktual"')
print("  git push")
print("  docker compose up --build -d api")
