# HANDOFF DOCUMENT — nvr_cam
## Panduan Melanjutkan Development di Sesi Baru

**Terakhir diperbarui:** 26 Juli 2026, 23:45 WIB
**Sesi Terakhir:** #017 (Codex — bug fixes + observability + playback queue)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## ⚡ MULAI CEPAT — Jika Token Habis / Ganti Claude Baru

Copy-paste ke Claude baru:

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam
Akses via MCP GitHub. Baca file-file ini sebelum mulai:
1. HANDOFF.md   → status proyek + panduan ini
2. ISSUES.md    → semua bug + issue + backlog

Progress per 26 Juli 2026, 21:30 WIB (Sesi #016 selesai):
- Backend:     ✅ SELESAI
- Frontend:    ✅ SELESAI (perlu npm run build setelah git pull)
- Flutter:     🟡 Code ada, flutter analyze belum diverifikasi
- Deploy:      ✅ scripts/install.sh siap untuk native Ubuntu
- Docker mode: ✅ Sudah bisa jalan
- Live View:   ✅ Grid selector, fullscreen, PiP, toggle stream, drag-drop, filter kamera, floating mode, sort filter panel
- Playback:    ✅ Auth token fix, HEVC transcode, file >100MB sudah bisa diputar, file 0MB tidak muncul
- Cameras:     ✅ Sort per kolom (klik header), filter search + dropdown status

Stack: FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
Server: Ubuntu Server 24.04, Intel i5, 8x WD Purple 4TB ZFS
Kamera: 30x Dahua H.265 RTSP

Next task: [sebutkan apa yang mau dikerjakan]
```

---

## Status Proyek Saat Ini

| Layer | Status | Catatan |
|-------|--------|---------|
| Backend | ✅ **SELESAI** | 11 router, semua services, Python import passing |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS |
| Mobile Flutter | 🟡 **Code Ada** | `flutter analyze` belum diverifikasi |
| Deploy Scripts | ✅ **SIAP** | `scripts/install.sh` untuk native Ubuntu |
| Docker Dev Mode | ✅ **BERJALAN** | Live View ✅, Playback ✅ (termasuk HEVC + file >100MB) |

---

## Yang Baru Selesai di Sesi #016

| Fitur | File | Keterangan |
|-------|------|------------|
| C-15 Sort tabel Cameras | `Cameras/index.tsx` | Klik header kolom → sort asc/desc. Kolom yang aktif ada ikon ↑↓. Semua kolom bisa di-sort: ID, Name, Location, Status, Storage, Motion, Retention |
| C-16 Filter tabel Cameras | `Cameras/index.tsx` | Search bar (filter ID/Name/Location) + dropdown status (All/Online/Offline). Muncul di bawah header bar. |
| C-17 Sort di LiveView filter panel | `LiveView/index.tsx` | Tombol sort by Name / Location / Status di panel filter. Klik lagi toggle asc/desc. |

**Catatan:** Ini murni client-side — tidak ada perubahan backend.

**Cara apply:**
```powershell
git pull
cd frontend && npm run build
```

---

## Yang Baru Selesai di Sesi #015

| Fix | File | Keterangan |
|-----|------|------------|
| BUG-047 | `recordings.py` (`/play`) | Probe codec dulu sebelum serve. HEVC → transcode H.264. Pipeline lengkap: cache → probe → transcode/remux → serve |
| BUG-048 | `camera_recorder.py`, `recordings.py` (list) | File 0MB: hapus dari disk setelah setiap segment, filter dari list API |
| BUG-049 | `ffmpeg_wrapper.py` | Hapus duplikasi `probe_codec_from_file()` dan `transcode_to_h264()` |
| BUG-050 | `ffmpeg_wrapper.py` | Timeout `remux_for_streaming` naik 60s→300s, `transcode_to_h264` naik 600s→1200s |

---

## Klarifikasi Penting — Setting H.265

> **Tidak ada setting H.265 di aplikasi NVR ini — by design.**
>
> Kamera Dahua dikonfigurasi codec H.265 langsung dari **web UI kamera**: `http://<IP_kamera>` → Setting → Camera → Video → Encode.
>
> Aplikasi NVR hanya menerima stream RTSP dari kamera dan otomatis mendeteksi codec via `ffprobe`. Tidak perlu — dan tidak bisa — mengubah codec kamera dari dalam aplikasi NVR.

---

## Pipeline Playback (Setelah Sesi #015)

```
Browser klik ▶
    ↓
GET /api/v1/recordings/{id}/play?token=...
    ↓
Cek cache _remux_cache → jika ada, skip ke serve
    ↓
Probe codec file (ffprobe, <1 detik)
    ↓
┌──────────────────────────────────────────────────────┐
│ HEVC/H.265 → transcode ke H.264 (2–20 menit)        │
│             cache: /tmp/nvr_remux/rec_{id}_h264.mp4  │
├──────────────────────────────────────────────────────┤
│ H.264, bukan faststart → remux (10–300 detik)        │
│             cache: /tmp/nvr_remux/rec_{id}.mp4       │
├──────────────────────────────────────────────────────┤
│ H.264 + faststart → serve langsung (instan)          │
├──────────────────────────────────────────────────────┤
│ File 0MB → HTTP 422 (error jelas ke browser)         │
└──────────────────────────────────────────────────────┘
    ↓
Serve dengan Range header support (206 Partial Content)
```

---

## Dokumen Referensi

| File | Isi | Kapan Dibaca |
|------|-----|--------------|
| `HANDOFF.md` | File ini — panduan cepat + template | Selalu, pertama kali |
| `ISSUES.md` | Semua bug historis + issue aktif + backlog | Saat cek history, mau fix bug, atau tambah fitur |
| `FEATURES.md` | Daftar lengkap 130 fitur + status | Saat mau cek/tambah fitur spesifik |
| `README.md` | Setup, quick start, struktur proyek | Saat setup awal |
| `docs/NVR_CAM_Blueprint.md` | Arsitektur teknis lengkap | Saat perlu pahami desain sistem |

---

## Deployment

### Native Ubuntu (Production)
```bash
git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
cd /opt/nvr_cam
sudo bash scripts/install.sh
nano /opt/nvr_cam/.env   # isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN, dll
systemctl status nvr-api nvr-recorder nvr-motion nvr-encoder
```

### Docker Dev Mode (Development)
```bash
docker compose up --build -d
# Akses: http://localhost:3000 (frontend), http://localhost:8000 (API)
```

### Service Names
| Konteks | Format |
|---------|--------|
| `docker compose` commands | `api`, `frontend`, `db` |
| `docker exec` / `docker logs` | `cctv_api`, `cctv_web`, `cctv_db` |
| Native systemd (production) | `nvr-api`, `nvr-recorder`, `nvr-motion`, `nvr-encoder` |

---

## Next Steps yang Direkomendasikan

| Prioritas | Task | ID |
|-----------|------|----|
| 🔴 Tinggi | Verifikasi BUG-051–053 di UI setelah jalankan script frontend sesi #017 | BUG-051, BUG-052, BUG-053 |
| 🔴 Tinggi | Verifikasi A-06 end-to-end: profile, ganti password, reset password admin | A-06 |
| 🟠 Sedang | Lengkapi UI frontend Wave 5 yang belum terotomasi penuh bila ada mismatch build | W5-UX |
| 🟠 Sedang | Tambah alerting lebih luas selain storage (CPU/RAM/container failure) | Wave 4 |
| 🟡 Rendah | UI redesign 6 halaman sisa ke tema terang | ISSUES.md bagian UI |
| 🟡 Rendah | Snapshot lightbox (klik foto → modal besar) | E-07 |

---

## Update Sesi #017 — Minggu, 26 Juli 2026

### Backend

- `PUT /api/v1/users/me/password` untuk ganti password sendiri.
- `PUT /api/v1/users/{user_id}/reset-password` untuk reset password oleh admin.
- `GET /api/v1/storage/diagnostics` untuk `camera_drive_map`, drive status, `recording_status`, dan `transcode_cache`.
- `GET /api/v1/audit-logs` + model/migration `audit_logs`.
- Middleware `X-Request-ID` + structured JSON logging.
- Health endpoint diperluas dengan kamera, storage, process count, dan `last_errors`.
- Playback queue async (`TranscodeQueue`) untuk transcode/remux di luar request path.
- `Dockerfile.backend` sudah copy `scripts/` agar `scripts/setup_db.py` tersedia di container.

### Frontend

- Patch frontend tidak di-push langsung ke source `.tsx`/`.ts`.
- Gunakan script `scripts/apply_frontend_s017.ps1` untuk apply perubahan UI/UX sesi ini.

### Verifikasi cepat

```powershell
git pull
docker compose up --build -d
docker exec cctv_api alembic upgrade head
docker exec cctv_api python -m pytest backend/tests -q
powershell -ExecutionPolicy Bypass -File .\scripts\apply_frontend_s017.ps1
cd frontend
npm run build
```

## Informasi Proyek

| Item | Detail |
|------|--------|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Install dir (native) | `/opt/nvr_cam` |
| Runtime dir (native) | `/var/lib/nvr_cam/` (HLS + snapshots) |
| Volume Docker (dev) | `hls_data` → `/var/lib/nvr_cam/hls`, `snapshot_data` |
| Notifikasi | Telegram Bot + SMTP email |
| Login awal | User `admin`; password dari `ADMIN_PASSWORD` atau output acak `scripts/setup_db.py` |
