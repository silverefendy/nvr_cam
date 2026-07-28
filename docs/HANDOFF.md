# HANDOFF — nvr_cam
## Status Proyek + Issue Tracker (Dokumen Tunggal untuk Claude Baru)

**Terakhir diperbarui:** 28 Juli 2026 (Sesi #023)
**Sesi Terakhir:** #023 (Verifikasi kode BUG-058/059/060 — semua sudah resolved di kode)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## ⚡ TEMPLATE MULAI CEPAT — Copy-paste ke Claude Baru

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam
Akses via MCP GitHub. Baca file ini sebelum mulai: docs/HANDOFF.md

Progress per 28 Juli 2026 (Sesi #023 selesai):
- Backend:     🟡 Perlu build ulang + verifikasi (setelah fix sesi #021)
- Frontend:    ✅ SELESAI (npm run build SUCCESS, Tailwind fix sudah include)
- Flutter:     🟡 Code ada, flutter analyze belum diverifikasi
- Deploy:      ✅ scripts/install.sh siap untuk native Ubuntu
- Docker mode: 🟡 Build errors sudah di-fix — perlu build ulang dan verifikasi
- Live View:   ✅ Grid selector, fullscreen, PiP, toggle stream, drag-drop, filter, floating mode, sort filter
- Playback:    ✅ Auth token fix, HEVC transcode, file >100MB bisa diputar, file 0MB tidak muncul
- Cameras:     ✅ Sort per kolom, filter search + dropdown status
- Discovery:   🟡 Kode sudah benar (async executor + fallback port scan) — belum ditest karena container belum rebuild
- Storage:     🟡 Path benar, endpoint /browse ada — belum ditest karena container belum rebuild

Stack: FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
Server: Ubuntu Server 24.04, Intel i5, 8x WD Purple 4TB ZFS
Kamera: 30x Dahua H.265 RTSP

Next task: [sebutkan apa yang mau dikerjakan]

Dokumen penting:
- docs/HANDOFF.md  → file ini — status + issues
- docs/FEATURES.md → 130 fitur + status masing-masing
- docs/TECH_DEBT.md → audit + backlog improvement
- docs/INSTALL_OPS.md → install, runbook, arsitektur, security
```

---

## Status Layer Saat Ini

| Layer | Status | Catatan |
|-------|--------|----------|
| Backend | 🟡 **Perlu Verifikasi** | Build errors sudah di-fix — jalankan `docker compose up --build` |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS |
| Mobile Flutter | 🟡 **Code Ada** | `flutter analyze` belum diverifikasi |
| Deploy Scripts | ✅ **SIAP** | `scripts/install.sh` untuk native Ubuntu |
| Docker Dev Mode | 🟡 **Perlu Build Ulang** | Jalankan `docker compose up --build -d` setelah pull latest |
| Discovery | 🟡 **Kode Sudah Fix** | `onvif_scanner.py` sudah async-safe + fallback port scan — perlu build ulang untuk test |
| Storage | 🟡 **Kode Sudah Fix** | `storage.yaml` path benar, `/browse` endpoint ada — perlu build ulang untuk test |

---

## Yang Selesai per Sesi

### Sesi #023 — 28 Juli 2026 (Verifikasi kode)

Verifikasi langsung ke source code — semua bug yang dicatat di sesi #022 ternyata **sudah diperbaiki di kode**:

| ID | Temuan Awal (Sesi #022) | Status Setelah Verifikasi |
|----|-------------------------|---------------------------|
| BUG-058 | `_ws_discovery()` sync blocking | ✅ **Sudah fix** — `_ws_discovery_blocking()` dijalankan via `asyncio.get_event_loop().run_in_executor(_UDP_EXECUTOR, ...)`. Fallback port scan 80/8000/8080 juga sudah ada di `_port_scan()`. |
| BUG-059 | `onvif-zeep==0.2.12` di requirements.txt | ✅ **Sudah fix** — library tidak ada di `requirements.txt`. Yang ada hanya `aiohttp==3.10.0` (benar). |
| BUG-060 | `storage.yaml` path salah + tidak ada `/browse` | ✅ **Sudah fix** — `storage.yaml` sudah pakai `/mnt/driveA`. Endpoint `GET /api/v1/storage/browse` sudah lengkap di `storage.py` dengan validasi path + info disk. |

**Catatan:** Discovery dan storage belum bisa ditest fungsional karena container belum di-rebuild setelah sesi #021. Langkah wajib sebelum test:
```bash
git pull
docker compose up --build -d
docker compose logs api --tail 30
# Tunggu: "NVR API service started successfully"
```

---

### Sesi #022 — 28 Juli 2026 (Audit)

Sesi audit — tidak ada file code yang di-push. Temuan:

| ID | Temuan | Status |
|----|--------|--------|
| BUG-058 | `onvif_scanner.py` async blocking + tidak ada fallback | ✅ Ternyata sudah fix (lihat sesi #023) |
| BUG-059 | `onvif-zeep` di requirements | ✅ Ternyata sudah fix |
| BUG-060 | `storage.yaml` path salah + tidak ada `/browse` | ✅ Ternyata sudah fix |

### Sesi #021 — 28 Juli 2026

| ID | Item | Status |
|----|------|--------|
| BUG-056 | Alembic revision chain putus | ✅ Fixed — distandardisasi ke `001`, `001b`, `002`, `003` |
| BUG-057 | Migration 003 crash sync di async engine | ✅ Fixed — pakai `sqlalchemy.text()` dalam `run_sync()` |
| BUG-055 | Migration 003 DROP TABLE gagal tanpa CASCADE | ✅ Fixed — semua DROP pakai `IF EXISTS ... CASCADE` |
| CHORE | `docker-compose.yml` hardcoded Windows path | ✅ Fixed — Docker named volume `nvr_recordings` |
| CHORE | `fix-cameras-discovery-jsx.ps1` | ✅ Dihapus |
| CHORE | `docs/NVR_CAM_Blueprint.md` | ✅ Dihapus |

### Sesi #020 — 27 Juli 2026 (Malam)

| ID | Item | Status |
|----|------|--------|
| BUG-055 | API crash loop — Alembic migration 003 crash loop | ✅ Fixed di sesi #021 |
| DEBUG | Discovery endpoint return 404 — container masih image lama | 🟡 Perlu build ulang |

### Sesi #019 — 27 Juli 2026 (Siang)

| ID | Fitur / Fix | File | Status |
|----|-------------|------|--------|
| G-06 | Discovery UI tombol "🔍 Cari Kamera" tidak muncul | `Cameras/index.tsx` | ✅ Fixed |
| BUG-TS-1 | TypeScript error `<DiscoveryModal>` di luar wrapper | `Cameras/index.tsx` | ✅ Fixed |
| BUG-TS-2 | TypeScript error `useMutation` + `buildRtspMain` unused | `DiscoveryModal.tsx` | ✅ Fixed |

### Sesi #018 — 26 Juli 2026 (Malam)

| ID | Fitur / Fix | File | Status |
|----|-------------|------|--------|
| BUG-054 | Login styling tidak muncul — Tailwind tidak di-load | `tailwind.config.js`, `postcss.config.js` | ✅ Fixed |
| A-10 | Role matrix + permission dependencies lengkap | `auth.py`, `dependencies.py` | ✅ Done |
| BUG-052 | Storage drive fix — sync volume mount + endpoints CRUD | `docker-compose.yml`, `storage.yaml`, `storage.py` | ✅ Fixed |
| E-14 | Snapshot manual via FFmpeg | `cameras.py` | ✅ Done |
| E-15 | Scheduled recording per kamera | `camera_recorder.py` | ✅ Done |
| B-13 | Camera group/tag — tabel + CRUD endpoints | `camera_groups.py` | ✅ Done |
| Settings | Settings router komprehensif ke `system.yaml` | `settings.py` | ✅ Done |

### Sesi #017 — 26 Juli 2026

| ID | Bug | Fix |
|----|-----|-----|
| BUG-051 | Live View video ter-crop | ✅ Fixed |
| BUG-052 | Storage mapping tidak sinkron | ✅ Fixed |
| BUG-053 | Live View hitam saat HLS belum ready | ✅ Fixed |
| A-06 | Profile user + ganti password | ✅ Fixed |
| A-08 | Audit log aktivitas admin/user | ✅ Fixed |
| O-01 | Storage diagnostics endpoint | ✅ Done |
| O-02 | Request ID + structured logging | ✅ Done |
| O-03 | Async playback transcode queue | ✅ Done |

### Sesi #016 — 26 Juli 2026

| ID | Fitur | File | Catatan |
|----|-------|------|--------|
| C-15 | Sort tabel Cameras per kolom | `Cameras/index.tsx` | Klik header → sort asc/desc |
| C-16 | Filter tabel Cameras — search + dropdown status | `Cameras/index.tsx` | Client-side |
| C-17 | Sort kamera di panel filter LiveView | `LiveView/index.tsx` | Sort by Name/Location/Status |

### Sesi #015 — 26 Juli 2026

| ID | Bug | Fix |
|----|-----|-----|
| BUG-047 | Playback file >100MB error | HEVC transcode pipeline |
| BUG-048 | File 0MB menumpuk | Cleanup + filter dari API |
| BUG-049 | Duplikasi fungsi `ffmpeg_wrapper.py` | Deduplikasi |
| BUG-050 | Timeout remux 60s terlalu pendek | Naik ke 300s/1200s |

### Sesi #010–014 — 24–26 Juli 2026
- BUG-028–046: Docker runtime, storage 500, HLS 404, playback HEVC, auth 401 — semua fixed
- Floating Window Mode (drag, resize, minimize)

---

## Alembic Revision Chain (setelah sesi #021)

```
001 (initial schema)
 └─→ 001b (add audit_logs)
      └─→ 002 (camera groups + recording schedule)
           └─→ 003 (partition recordings + motion_events)
```

**Catatan penting:** Jika DB sudah ada dari sebelum sesi #021 (revision `20260726_000001` di alembic_version):
```bash
docker compose exec api alembic stamp 001b
docker compose exec api alembic upgrade head
```

---

## Pipeline Playback

```
Browser klik ▶
    ↓
GET /api/v1/recordings/{id}/play?token=...
    ↓
Cek cache _remux_cache → jika ada, skip ke serve
    ↓
Probe codec file (ffprobe)
    ↓
┌────────────────────────────────────────────────────────────┐
│ HEVC/H.265 → transcode ke H.264 (2–20 menit)              │
│             cache: /tmp/nvr_remux/rec_{id}_h264.mp4        │
├────────────────────────────────────────────────────────────┤
│ H.264, bukan faststart → remux (10–300 detik)              │
│             cache: /tmp/nvr_remux/rec_{id}.mp4             │
├────────────────────────────────────────────────────────────┤
│ H.264 + faststart → serve langsung (instan)                │
├────────────────────────────────────────────────────────────┤
│ File 0MB → HTTP 422 (error jelas ke browser)               │
└────────────────────────────────────────────────────────────┘
    ↓
Serve dengan Range header support (206 Partial Content)
```

---

## Deployment

### Docker Dev Mode
```bash
git pull
docker compose up --build -d
# Akses: http://localhost:3000 (frontend), http://localhost:8000 (API)
docker compose logs api -f
```

**Catatan docker-compose.yml:** Volume `nvr_recordings` adalah Docker named volume (untuk dev).
Untuk production, ganti dengan bind mount:
```yaml
volumes:
  - /mnt/nvr_recordings:/mnt/driveA  # ganti sesuai path HDD server
```

### Native Ubuntu Production
```bash
git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
cd /opt/nvr_cam
sudo bash scripts/install.sh
nano /opt/nvr_cam/.env   # isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN
systemctl status nvr-api nvr-recorder nvr-motion nvr-encoder
```

### Nama Service
| Konteks | Format |
|---------|--------|
| `docker compose` | `api`, `frontend`, `db` |
| `docker exec` / `docker logs` | `cctv_api`, `cctv_web`, `cctv_db` |
| Native systemd | `nvr-api`, `nvr-recorder`, `nvr-motion`, `nvr-encoder` |

---

## Informasi Proyek

| Item | Detail |
|------|--------|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Install dir (native) | `/opt/nvr_cam` |
| Runtime dir (native) | `/var/lib/nvr_cam/` (HLS + snapshots) |
| Volume Docker (dev) | `hls_data`, `snapshot_data`, `nvr_recordings` (named volumes) |
| Notifikasi | Telegram Bot + SMTP email |
| Login awal | User `admin`; password dari `ADMIN_PASSWORD` atau output acak `scripts/setup_db.py` |

---

## Issue Tracker & Backlog

### ✅ Tidak Ada Bug Kritis Aktif

Semua bug kritis sudah resolved di kode. Langkah selanjutnya: rebuild container dan verifikasi fungsional.

```bash
git pull
docker compose up --build -d
docker compose logs api -f
```

### ❓ Yang Masih Perlu Diverifikasi (setelah build ulang)

| # | Item | Cara Verifikasi |
|---|------|----------------|
| 1 | API tidak crash loop | `docker compose logs api --tail 30` — harus ada `NVR API service started successfully` |
| 2 | Discovery scan ONVIF | Swagger `http://localhost:8000/api/docs` → POST `/api/v1/discovery/cameras` |
| 3 | Storage browse endpoint | GET `http://localhost:8000/api/v1/storage/browse` — harus return daftar folder di `/mnt` |
| 4 | Storage page tidak kosong | Buka halaman Storage di frontend — harus ada info drive `/mnt/driveA` |
| 5 | cam_03 — 403 Forbidden | Edit cam_03 di halaman Cameras → update credentials RTSP |
| 6 | Playback file >100MB | Buka Playback, klik file >100MB |
| 7 | Live View grid 2x2 dan 4x4 | Buka grid, pastikan video tidak ter-crop |
| 8 | Profile + ganti password | Coba `/profile`, ganti password |
| 9 | Sort & filter tabel Cameras | Klik header kolom Name → sort |

### 🔴 Prioritas Tinggi — Fitur Belum Dikerjakan

| ID | Task | Catatan |
|----|------|--------|
| F-08 | Statistik storage per kamera | Berapa GB per kamera per hari |
| F-09 | Jadwal cleanup terjadwal | Cleanup rutin, bukan hanya saat disk penuh |
| F-10 | Alert disk kritis via Telegram | Penting untuk 30 kamera |
| D-09 | Download rekaman ke lokal | Tombol download di halaman Playback |
| G-07 | Auto-add kamera dari hasil discovery | Tombol "Tambah ke sistem" langsung dari modal discovery |

### 🟠 Prioritas Sedang — Fitur Belum Dikerjakan

**Auth & User**
| A-07 | Two-Factor Authentication | ⏳ |
| A-09 | Session timeout auto logout | ⏳ |

**Kamera**
| B-14 | PTZ control via ONVIF | ⏳ |
| B-16 | Kamera non-RTSP (MJPEG/HTTP) | ⏳ |

**Live View**
| C-09 | Digital zoom | ⏳ |
| C-10 | Audio live | ⏳ |
| C-12 | FPS custom per kamera | 🎯 Desain sudah final |

**Rekaman**
| D-10 | Motion marker di timeline | ⏳ |
| D-11 | Kliping rekaman (export X–Y menit) | ⏳ |

**Motion Detection**
| E-07 | Snapshot lightbox | ⏳ |
| E-09 | Motion masking area | ⏳ |
| E-10 | Sensitivitas adjustable per kamera | ⏳ |
| E-11 | Cooldown notifikasi anti-spam | ⏳ |
| E-12 | Klip video pre/post event | ⏳ |
| E-13 | FPS adaptif saat motion | 🎯 Desain sudah final |

**Monitoring**
| I-08 | Log viewer di UI | ⏳ |
| I-09 | Alert CPU/RAM tinggi | ⏳ |
| I-10 | Grafik historis (CPU/RAM/disk) | ⏳ |
| I-11 | Restart service dari UI | ⏳ |

### 🟡 Prioritas Rendah

| ID | Fitur | Status |
|----|-------|--------|
| L-07 | HTTPS/SSL | ⏭️ nanti |
| L-08–L-09 | Health check publik, UFW firewall | ⏳ |
| K-06–K-10 | Flutter analyze, build APK, FCM, biometric, landscape | ⏭️ nanti |
| J-04–J-05 | AV1 progress encode, GPU acceleration | ⏳ |

### UI Redesign Sisa (Tema Terang)

| Halaman | Status |
|---------|--------|
| Storage | ⏳ |
| Playback | ⏳ |
| Events | ⏳ |
| Cameras | ⏳ |
| Users | ⏳ |
| Settings | ⏳ |

---

## Tips Debug API

| Cara | Keterangan |
|------|----------|
| **Swagger UI** | `http://localhost:8000/api/docs` — test endpoint langsung via browser, ada tombol Authorize untuk paste JWT |
| **ReDoc** | `http://localhost:8000/api/redoc` — dokumentasi semua endpoint |
| **PowerShell curl** | `Invoke-RestMethod -Method POST -Uri "..." -Headers @{Authorization="Bearer $TOKEN"} -Body '...'` |
| **httpie** | `pip install httpie` lalu `http POST localhost:8000/api/v1/... Authorization:"Bearer $TOKEN"` |

---

## Timeline Sesi Development

| No | Tanggal | Sesi | Agent | Yang Dikerjakan |
|----|---------|------|-------|----------------|
| 1–2 | — | #001–002 | Claude | Kerangka awal, backend, frontend, Flutter |
| 3 | 2 Juli 2026 | #003 | Claude | Audit + update dokumentasi |
| 4 | 3 Juli 2026 | #004 | Devin AI | Fix BUG-001–012 |
| 5 | 8 Juli 2026 | #006 | Cascade AI | Fix BUG-014–018 |
| 6 | 9 Juli 2026 | #007 | Claude | Fix install.sh (BUG-020–024) |
| 7 | 22 Juli 2026 | #008–009 | Claude | Audit, fix BUG-025–027, Batch 1+2 |
| 8 | 24 Juli 2026 | #010 | Claude | Fix Docker runtime (BUG-028–037), UI redesign |
| 9 | 25 Juli 2026 | #011 | Claude | Fix BUG-038–041, cleanup file repo |
| 10 | 25 Juli 2026 | #012 | Claude | Fix BUG-042 (adaptive grid), fitur C-14 (Floating Mode) |
| 11 | 25 Juli 2026 | #013 | Claude | Fix BUG-043 (ganti IP kamera tidak apply) |
| 12 | 26 Juli 2026 | #014 | Claude | Fix BUG-044 (playback HEVC) + BUG-045 (codec hardcode) |
| 13 | 26 Juli 2026 | #014b | Claude | Fix BUG-046 (401 saat play video) |
| 14 | 26 Juli 2026 | #015 | Claude | Fix BUG-047–050 (playback besar, file 0MB, duplikasi, timeout) |
| 15 | 26 Juli 2026 | #016 | Claude | Fitur C-15, C-16, C-17 (sort & filter Cameras + LiveView) |
| 16 | 26 Juli 2026 | #017 | Claude | Async queue, diagnostics, structured logs, audit logs, health |
| 17 | 26 Juli 2026 | #018 | Claude | Login UI fix, role matrix, settings redesign, dual-stream, snapshot, schedule, camera groups |
| 18 | 27 Juli 2026 | #019 | Claude | Discovery UI fix (tombol muncul, TypeScript error) |
| 19 | 27 Juli 2026 | #020 | Claude | Debug discovery scan + temukan BUG-055 (migration 003 crash loop) |
| 20 | 28 Juli 2026 | #021 | Claude | Fix BUG-055/056/057, docker-compose path, hapus file sampah |
| 21 | 28 Juli 2026 | #022 | Claude | Audit discovery + storage — temuan BUG-058/059/060 (ternyata sudah fix) |
| 22 | 28 Juli 2026 | #023 | Claude | Verifikasi source code — BUG-058/059/060 confirmed resolved di kode |

---

## Klarifikasi Penting — Setting H.265

> **Tidak ada setting H.265 di aplikasi NVR ini — by design.**
>
> Kamera Dahua dikonfigurasi codec H.265 langsung dari **web UI kamera**: `http://<IP_kamera>` → Setting → Camera → Video → Encode.
>
> Aplikasi NVR hanya menerima stream RTSP dari kamera dan otomatis mendeteksi codec via `ffprobe`. Tidak perlu — dan tidak bisa — mengubah codec kamera dari dalam aplikasi NVR.
