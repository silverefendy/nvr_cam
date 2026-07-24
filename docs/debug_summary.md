# nvr_cam — Debug Session Summary
**Repo:** https://github.com/silverefendy/nvr_cam  
**Stack:** FastAPI + PostgreSQL + React (Vite) + Nginx + FFmpeg + Docker Compose  
**Terakhir diupdate:** 2026-07-25 06:25 WIB

---

## Status Saat Ini

| Fitur | Status |
|---|---|
| Login | ✅ Berfungsi |
| Tambah kamera (POST /config/cameras) | ✅ Berfungsi |
| Hapus kamera (DELETE /config/cameras) | ✅ Berfungsi |
| Edit kamera (PUT /config/cameras) | ✅ Berfungsi |
| Test connection RTSP | ✅ Berfungsi |
| Status Online/Offline di halaman Cameras | ✅ Berfungsi (auto-refresh 10s) |
| Password tersimpan saat Edit | ✅ Berfungsi |
| File HLS terbentuk di volume | ✅ Terbentuk di /var/lib/nvr_cam/hls/ |
| **Live View menampilkan video** | ⏳ **Fix sudah di-push — perlu rebuild & test** |

---

## Semua Bug yang Sudah Difix

### 1. Deadlock asyncio.Lock di ConfigManager
- **File:** `backend/utils/config_manager.py`
- **Commit:** `988525a`
- **Bug:** `add_camera()`, `delete_camera()`, dll memanggil `_create_backup()` + `_read_yaml()` berurutan, masing-masing acquire `self._lock`. `asyncio.Lock` tidak re-entrant → deadlock.
- **Fix:** Buat versi `_unlocked()` untuk internal calls, acquire lock hanya di level atas.

### 2. Config router pakai YAML bukan PostgreSQL
- **File:** `backend/api/routers/config.py`
- **Commit:** `e8a3365`, `32d8055`
- **Bug:** `/api/v1/config/cameras` (CRUD kamera) baca/tulis ke `cameras.yaml`, sementara `/api/v1/cameras` (list kamera) baca dari PostgreSQL. Dua sumber data tidak sinkron → delete/edit kamera selalu "not found".
- **Fix:** Rewrite seluruh CRUD kamera di `config.py` untuk pakai `CameraRepository` (PostgreSQL).

### 3. Redirect paksa ke /setup saat kamera kosong
- **File:** `frontend/src/App.tsx`
- **Commit:** `6ba5621`
- **Bug:** Setelah semua kamera dihapus, App.tsx redirect ke `/setup` dan user tidak bisa kembali ke halaman Cameras untuk tambah kamera baru.
- **Fix:** Hapus redirect paksa. Default landing ke `/cameras`.

### 4. BaseRepository tidak commit setelah create/delete
- **File:** `backend/db/repositories/base_repo.py`
- **Commit:** `95f5a51`
- **Bug:** `create()` hanya `flush()` tanpa `commit()` → data hilang saat session close. `delete_by_id()` juga tidak commit.
- **Fix:** Tambah `await self.db.commit()` di kedua method.

### 5. subprocess.Popen blocking asyncio event loop
- **File:** `backend/services/recorder/camera_recorder.py`
- **Commit:** `f8386b3`
- **Bug:** `subprocess.Popen` + `proc.wait()` via `run_in_executor` masih bisa block. Diganti ke `asyncio.create_subprocess_exec` agar benar-benar non-blocking.

### 6. HLS ditulis ke /tmp/hls bukan volume Docker
- **File:** `backend/services/recorder/camera_recorder.py`
- **Commit:** `f8386b3`
- **Bug:** FFmpeg menulis HLS ke `/tmp/hls/<id>/` tapi Nginx serve dari `/var/lib/nvr_cam/hls/` (Docker volume `hls_data`). File tidak pernah ditemukan → Live View 404.
- **Fix:** Ganti `HLS_BASE_DIR = Path("/var/lib/nvr_cam/hls")`. Nama direktori: `<camera_id>_sub/` agar cocok dengan yang diminta stream router dan Nginx.

### 7. segment_duration tidak ada di model Camera
- **File:** `backend/services/recorder/manager.py`
- **Commit:** `19edcfa`
- **Bug:** `restart_camera()` dan `load_cameras_from_db()` akses `cam.segment_duration` tapi field itu tidak ada di SQLAlchemy model → `AttributeError` → recorder tidak pernah start setelah add/edit kamera.
- **Fix:** Buat helper `_camera_to_dict()` yang baca `segment_duration` dari `config_json` dengan default 3600.

### 8. Status Offline padahal recorder jalan
- **File:** `frontend/src/pages/Cameras/index.tsx`
- **Commit:** `29420e1`
- **Bug:** Halaman Cameras query `/config/cameras` yang tidak punya field `is_online`. Selalu tampil Offline.
- **Fix:** Ganti ke `/cameras` (lewat RecordingManager, ada `is_online` real-time). Tambah `refetchInterval: 10000`.

### 9. Password hilang saat Edit kamera
- **File:** `frontend/src/pages/Cameras/index.tsx`
- **Commit:** `29420e1`
- **Bug:** Form di-populate dengan `password: ''` hardcoded. User harus input ulang setiap kali edit.
- **Fix:** Baca dari `camera.config_json.password` yang disimpan backend saat create/update.

### 10. hls_temp_dir salah di settings
- **File:** `backend/core/config.py`
- **Commit:** `cd053c7`
- **Bug:** Default `hls_temp_dir = "/tmp/hls"` tidak konsisten dengan volume Docker `/var/lib/nvr_cam/hls`.
- **Fix:** Ganti default ke `/var/lib/nvr_cam/hls`.

### 11. useHLSPlayer tidak re-attach jika videoRef masih null saat mount
- **File:** `frontend/src/hooks/useHLSPlayer.ts`
- **Commit:** `da2cd7c`
- **Bug:** `useEffect` hanya bergantung pada `[hlsUrl]`. Jika `videoRef.current` masih `null` saat effect pertama jalan (race condition antara data query selesai dan DOM render), `hls.attachMedia()` tidak pernah dipanggil → video player kosong meski HLS URL sudah ada.
- **Fix:** Tambahkan `videoRef.current` ke dependency array. Tambah HLS error recovery handler (`startLoad`, `recoverMediaError`) dan retry config (`fragLoadingMaxRetry: 6`).

### 12. HEVC (H.265) tidak didukung hls.js di browser
- **File:** `backend/services/recorder/ffmpeg_wrapper.py`, `backend/services/recorder/camera_recorder.py`
- **Commit:** `d37b6c3`, `7928196`
- **Bug:** `build_hls_command()` pakai `-c:v copy` — stream copy langsung dari kamera tanpa transcode. Kamera yang output HEVC/H.265 (termasuk cam_07 di 10.1.0.151) menghasilkan file `.ts` dengan codec yang tidak bisa di-decode hls.js di browser (hls.js hanya support H.264 via MSE).
- **Fix:**
  - Tambah parameter `force_transcode: bool` di `build_hls_command()`. Jika True: pakai `-c:v libx264 -preset ultrafast -crf 23`.
  - Tambah fungsi `detect_video_codec(rtsp_url)` untuk probe codec via `ffprobe`.
  - Di `_run_hls_loop()`: probe codec sekali saat pertama start via `run_in_executor` (non-blocking). Auto-set `force_transcode=True` jika codec `hevc` atau `h265`.
  - HLS FFmpeg stderr sekarang di-log (sebelumnya `DEVNULL`) untuk memudahkan debug.

---

## Masalah yang Belum Selesai

### ✅ Live View — semua fix sudah di-push, perlu verifikasi

**Langkah verifikasi setelah rebuild:**

```bash
# 1. Rebuild backend (perubahan Python)
git pull && docker compose up --build -d api

# 2. Rebuild frontend (perubahan TypeScript hook)
docker compose up --build -d frontend

# 3. Cek log — pastikan deteksi codec muncul
docker compose logs -f api | grep -E "Codec|HEVC|transcode|HLS"
# Contoh output yang diharapkan:
# [cam_07] Codec HEVC terdeteksi ('hevc') → aktifkan transcode H.264 untuk kompatibilitas browser
# [cam_08] Codec: h264 → stream copy (tanpa transcode)

# 4. Cek file HLS terbentuk
docker exec cctv_api find /var/lib/nvr_cam/hls/ -name "*.m3u8" -type f

# 5. Test akses via browser
# Buka: http://<IP>:3000 → Live View → buka DevTools (F12) → Console
# Tidak boleh ada error "[HLS] Fatal error"
```

**Jika masih kosong setelah rebuild:**
1. Buka DevTools → Network tab → filter `/hls/` → cek apakah `.m3u8` return 200 atau 404.
2. Cek Console → ada error dari hls.js? Copy error lengkapnya.
3. Jalankan: `docker compose logs -f api | grep -i "hls\|error\|codec"` → lihat apakah FFmpeg HLS process crash.
4. Kemungkinan lain: `libx264` tidak ter-install di image Docker. Cek dengan: `docker exec cctv_api ffmpeg -encoders 2>&1 | grep libx264`

**Jika libx264 tidak ada di container:**
- Edit `Dockerfile.backend` → pastikan base image punya `ffmpeg` dengan libx264 support.
- Contoh: `apt-get install -y ffmpeg` di Ubuntu sudah include libx264 secara default.

---

## Arsitektur Sistem

```
Browser (React + hls.js)
    │
    ├── GET /api/v1/cameras           → FastAPI → PostgreSQL (list + status)
    ├── GET /api/v1/stream/XX/live    → FastAPI → return { hls_url: "/hls/XX_sub/index.m3u8" }
    └── GET /hls/XX_sub/index.m3u8   → Nginx → /var/lib/nvr_cam/hls/ (Docker volume)
                                                      ↑
                                              FFmpeg (via CameraRecorder)
                                              nulis HLS segments ke sini
                                              (auto-transcode HEVC → H.264 jika perlu)
                                                      ↑
                                              RTSP stream dari kamera fisik
```

## Struktur Docker

```yaml
services:
  api:      Dockerfile.backend — port 8000
  frontend: Dockerfile.frontend.prod — Nginx port 3000
  db:       postgres:16-alpine — port 5432

volumes:
  hls_data:      /var/lib/nvr_cam/hls  (shared antara api dan frontend)
  snapshot_data: /var/lib/nvr_cam/snapshots
  postgres_data: /var/lib/postgresql/data
```

## File-File Kunci

| File | Fungsi |
|---|---|
| `backend/api/routers/config.py` | CRUD kamera via PostgreSQL |
| `backend/api/routers/cameras.py` | List kamera + status real-time |
| `backend/api/routers/stream.py` | Return HLS URL |
| `backend/services/recorder/camera_recorder.py` | FFmpeg recording + HLS + deteksi codec |
| `backend/services/recorder/ffmpeg_wrapper.py` | Builder command FFmpeg (record, HLS, transcode, probe) |
| `backend/services/recorder/manager.py` | Singleton RecordingManager |
| `backend/db/repositories/base_repo.py` | Base CRUD DB |
| `frontend/src/pages/Cameras/index.tsx` | Halaman manajemen kamera |
| `frontend/src/pages/LiveView/index.tsx` | Halaman live view |
| `frontend/src/components/camera/VideoPlayer.tsx` | Video player (hls.js) |
| `frontend/src/hooks/useHLSPlayer.ts` | Hook HLS player (attach + error recovery) |
| `scripts/nginx/cctv.conf` | Nginx config |
| `backend/core/config.py` | Settings (hls_temp_dir, dll) |

## Cara Rebuild

```bash
# Rebuild semua (perlu setelah ada perubahan Dockerfile atau dependency)
git pull && docker compose up --build -d

# Rebuild hanya backend (perubahan Python)
git pull && docker compose up --build -d api

# Rebuild hanya frontend (perubahan React/TypeScript)
git pull && docker compose up --build -d frontend

# Restart tanpa rebuild (TIDAK cukup untuk perubahan kode)
docker compose restart api

# Lihat log real-time
docker compose logs -f api | Select-String "cam_0|recording|Gagal|hls|error|codec"
```

## Nama Service Docker (Penting!)

- Service name di docker-compose.yml: `api`, `frontend`, `db`
- Container name: `cctv_api`, `cctv_web`, `cctv_db`
- Perintah: `docker compose logs -f api` (bukan `cctv_api`)
- Exec: `docker exec cctv_api <command>` (pakai container name)
