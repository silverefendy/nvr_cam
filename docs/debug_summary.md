# nvr_cam — Debug Session Summary
**Repo:** https://github.com/silverefendy/nvr_cam  
**Stack:** FastAPI + PostgreSQL + React (Vite) + Nginx + FFmpeg + Docker Compose  
**Terakhir diupdate:** 2026-07-25 06:40 WIB

---

## Status Saat Ini

| Fitur | Status |
|---|---|
| Login | ✅ Berfungsi |
| Tambah kamera (POST /config/cameras) | ✅ Berfungsi (error sekarang ditampilkan ke user) |
| Hapus kamera (DELETE /config/cameras) | ✅ Berfungsi |
| Edit kamera (PUT /config/cameras) | ✅ Berfungsi |
| Test connection RTSP | ✅ Berfungsi |
| Status Online/Offline di halaman Cameras | ✅ Berfungsi (auto-refresh 10s) |
| Password tersimpan saat Edit | ✅ Berfungsi |
| File HLS terbentuk di volume | ✅ Terbentuk di /var/lib/nvr_cam/hls/ |
| Live View menampilkan video | ✅ Berfungsi (HEVC auto-transcode ke H.264) |
| **Tombol grid 1x1/2x2/3x3/4x4** | ⏳ **Fix di-push — perlu rebuild frontend** |
| **Tampilan Live View (dark, no border-radius)** | ⏳ **Fix di-push — perlu rebuild frontend** |
| **Drag-drop kamera di grid** | ⏳ **Fix di-push — perlu rebuild frontend** |

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
- **Bug:** `build_hls_command()` pakai `-c:v copy`. Kamera yang output HEVC menghasilkan `.ts` yang tidak bisa di-decode hls.js.
- **Fix:** `detect_video_codec()` via ffprobe, auto `force_transcode=True` jika HEVC. HLS stderr sekarang di-log.

### 13. Tombol grid 1x1/2x2/3x3/4x4 tidak sinkron dengan jumlah kamera
- **File:** `frontend/src/store/cameras.ts`
- **Commit:** `a9844bf`
- **Bug:** `setGridSize()` hanya update state `gridSize`, tidak menyesuaikan `selectedCameras`. Grid columns berubah tapi jumlah VideoPlayer tidak berubah → 2x2 tampil 3 kamera, 4x4 tetap tampil 3 kamera.
- **Fix:** `setGridSize()` sekarang auto-expand (tambah kamera yang belum tampil) atau auto-trim (`slice`) sesuai kapasitas grid. Ditambah konstanta `GRID_CAPACITY` untuk mapping `GridSize → max cameras`.

### 14. Tampilan Live View jelek — sudut rounded, background putih
- **File:** `frontend/src/pages/LiveView/index.tsx`, `frontend/src/components/camera/VideoPlayer.tsx`, `frontend/src/components/camera/CameraGrid.tsx`
- **Commit:** `22603c7`, `f12ccf2`, `f72d60e`
- **Bug:** Background `bg-slate-100` (abu terang), `VideoPlayer` pakai `rounded` class, video tidak fill container, gap antar kamera terlalu besar.
- **Fix:** Full dark theme (`#0f1117`, `#1a1d27`). VideoPlayer tidak ada border-radius. Gap antar kamera 2px. Video `object-fit: contain`. CameraGrid pakai inline `style` (CSS grid) agar lebih presisi dari Tailwind.

### 15. Drag-drop kamera di grid tidak ada
- **File:** `frontend/src/components/camera/CameraGrid.tsx`, `frontend/src/store/cameras.ts`
- **Commit:** `f72d60e`, `a9844bf`
- **Implementasi:** HTML5 native drag-drop (`draggable`, `onDragStart`, `onDragOver`, `onDrop`). Drop highlight dengan outline biru. `reorderCameras(fromIndex, toIndex)` di store — swap posisi di `selectedCameras` array. Icon `⠿` muncul saat hover sebagai visual hint.

### 16. Error tambah kamera tidak ditampilkan ke user
- **File:** `frontend/src/components/camera/CameraForm.tsx`
- **Commit:** `bf983b8`
- **Bug:** `saveMutation.onError` tidak di-handle → kalau backend return error (misal duplikasi ID, storage drive kosong), form tutup diam-diam atau tidak ada feedback sama sekali.
- **Fix:** Tambah `errorMsg` state + banner merah di atas form. Parse `err.response.data.detail` dari FastAPI. Tambah validasi client-side (nama wajib, IP wajib, storage wajib) sebelum kirim ke backend.

---

## Masalah yang Belum Selesai

Semua masalah yang dilaporkan sudah di-fix dan di-push. Perlu rebuild frontend:

```bash
git pull && docker compose up --build -d frontend
```

Setelah rebuild, verifikasi:
1. Tombol 1x1/2x2/3x3/4x4 → kamera tampil bertambah/berkurang sesuai grid
2. Live View background hitam, tidak ada sudut rounded
3. Coba drag kamera dari satu slot ke slot lain
4. Coba tambah kamera dengan field kosong → harus muncul pesan error di form

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
| `frontend/src/store/cameras.ts` | Zustand store kamera + grid state + drag-drop reorder |
| `frontend/src/pages/Cameras/index.tsx` | Halaman manajemen kamera |
| `frontend/src/pages/LiveView/index.tsx` | Halaman live view (dark theme) |
| `frontend/src/components/camera/CameraGrid.tsx` | Grid layout + drag-drop handler |
| `frontend/src/components/camera/VideoPlayer.tsx` | Video player (hls.js, no rounded corners) |
| `frontend/src/components/camera/CameraForm.tsx` | Form tambah/edit kamera + error banner |
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
