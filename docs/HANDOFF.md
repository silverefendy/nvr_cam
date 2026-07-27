# HANDOFF — nvr_cam
## Status Proyek + Issue Tracker (Dokumen Tunggal untuk Claude Baru)

**Terakhir diperbarui:** 27 Juli 2026 (Sesi #020)
**Sesi Terakhir:** #020 (Discovery ONVIF scan, Alembic migration crash loop)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## ⚡ TEMPLATE MULAI CEPAT — Copy-paste ke Claude Baru

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam
Akses via MCP GitHub. Baca file ini sebelum mulai: docs/HANDOFF.md

Progress per 27 Juli 2026 (Sesi #020 selesai):
- Backend:     ✅ SELESAI (11 router, semua services, Python import passing)
- Frontend:    ✅ SELESAI (npm run build SUCCESS, Tailwind fix sudah include)
- Flutter:     🟡 Code ada, flutter analyze belum diverifikasi
- Deploy:      ✅ scripts/install.sh siap untuk native Ubuntu
- Docker mode: 🔴 API container CRASH LOOP — migration 003 setengah jalan (lihat BUG-055)
- Live View:   ✅ Grid selector, fullscreen, PiP, toggle stream, drag-drop, filter, floating mode, sort filter
- Playback:    ✅ Auth token fix, HEVC transcode, file >100MB bisa diputar, file 0MB tidak muncul
- Cameras:     ✅ Sort per kolom, filter search + dropdown status
- Discovery:   🔴 Belum bisa ditest — API crash loop dulu harus diselesaikan

Stack: FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
Server: Ubuntu Server 24.04, Intel i5, 8x WD Purple 4TB ZFS
Kamera: 30x Dahua H.265 RTSP

MASALAH AKTIF YANG HARUS DISELESAIKAN DULU:
  → BUG-055: API container crash loop karena migration 003 setengah jalan
    Fix: lihat bagian "Issue Tracker" di bawah

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
| Backend | 🔴 **CRASH LOOP** | Migration 003 setengah jalan — lihat BUG-055 |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS |
| Mobile Flutter | 🟡 **Code Ada** | `flutter analyze` belum diverifikasi |
| Deploy Scripts | ✅ **SIAP** | `scripts/install.sh` untuk native Ubuntu |
| Docker Dev Mode | 🔴 **API DOWN** | Harus fix BUG-055 dulu sebelum bisa lanjut apapun |

---

## Yang Selesai per Sesi

### Sesi #020 — 27 Juli 2026 (Malam)

| ID | Item | Status |
|----|------|--------|
| BUG-055 | API crash loop — Alembic migration 003 setengah jalan (DROP TABLE gagal tanpa CASCADE) | 🔴 **Ditemukan, belum di-fix** |
| DEBUG | Discovery endpoint `POST /api/v1/discovery/cameras` return 404 — container masih image lama | 🔴 **Ditemukan — tertutup oleh BUG-055** |
| DEBUG | `onvif-zeep` tidak terinstall di container — tapi tidak relevan karena `onvif_scanner.py` tidak pakai library ini (pakai `aiohttp` + WS-Discovery UDP manual) | ✅ Temuan — bukan bug |

### Sesi #019 — 27 Juli 2026 (Siang)

| ID | Fitur / Fix | File | Status |
|----|-------------|------|--------|
| G-06 | Discovery kamera ONVIF — tombol "🔍 Cari Kamera" tidak muncul di UI | `Cameras/index.tsx` | ✅ Fixed (rebuild frontend) |
| BUG-TS-1 | TypeScript error `Cameras/index.tsx` baris 252 — `<DiscoveryModal>` di luar wrapper `<div>` | `Cameras/index.tsx` | ✅ Fixed |
| BUG-TS-2 | TypeScript error `DiscoveryModal.tsx` — `useMutation` unused + `buildRtspMain` unused | `DiscoveryModal.tsx` | ✅ Fixed |

### Sesi #018 — 26 Juli 2026 (Malam)

| ID | Fitur / Fix | File | Status |
|----|-------------|------|--------|
| BUG-054 | Login styling tidak muncul — Tailwind tidak di-load | `tailwind.config.js`, `postcss.config.js` | ✅ Fixed |
| A-10 | Role matrix + permission dependencies lengkap | `auth.py`, `dependencies.py` | ✅ Done |
| BUG-052 | Storage drive fix — sync volume mount + endpoints CRUD storage | `docker-compose.yml`, `storage.yaml`, `storage.py` | ✅ Fixed |
| E-14 | Snapshot manual via FFmpeg | `cameras.py` | ✅ Done |
| E-15 | Scheduled recording per kamera | `camera_recorder.py` | ✅ Done |
| B-13 | Camera group/tag — tabel + CRUD endpoints | `camera_groups.py` | ✅ Done |
| Settings | Settings router komprehensif menyimpan ke `system.yaml` | `settings.py` | ✅ Done |

### Sesi #017 — 26 Juli 2026

| ID | Bug | Fix |
|----|-----|-----|
| BUG-051 | Live View video ter-crop (`object-fit: cover`) | ✅ Backend/frontend patch siap |
| BUG-052 | Storage mapping tidak sinkron setelah tambah kamera | ✅ Fixed |
| BUG-053 | Live View hitam saat HLS belum ready | ✅ Fixed |
| A-06 | Profile user + ganti password sendiri + reset oleh admin | ✅ Fixed |
| A-08 | Audit log aktivitas admin/user | ✅ Fixed |
| O-01 | Storage diagnostics endpoint | ✅ Done |
| O-02 | Request ID + structured logging + richer health surface | ✅ Done |
| O-03 | Async playback transcode queue + cache lifecycle management | ✅ Done |

### Sesi #016 — 26 Juli 2026

| ID | Fitur | File | Catatan |
|----|-------|------|---------|
| C-15 | Sort tabel Cameras per kolom | `Cameras/index.tsx` | Klik header → sort asc/desc |
| C-16 | Filter tabel Cameras — search + dropdown status | `Cameras/index.tsx` | Client-side |
| C-17 | Sort kamera di panel filter LiveView | `LiveView/index.tsx` | Sort by Name/Location/Status |

### Sesi #015 — 26 Juli 2026

| ID | Bug | Fix |
|----|-----|-----|
| BUG-047 | Playback file >100MB error — HEVC tidak di-transcode | Pipeline: probe codec → HEVC transcode → H264 remux → serve |
| BUG-048 | File 0MB menumpuk di storage dan muncul di list | Cleanup setelah segment + filter dari API list |
| BUG-049 | Duplikasi fungsi di `ffmpeg_wrapper.py` | Deduplikasi |
| BUG-050 | Timeout remux 60s terlalu pendek | Naik ke 300s (remux) dan 1200s (transcode) |

### Sesi #014 + #014b — 26 Juli 2026

| ID | Bug | Fix |
|----|-----|-----|
| BUG-044 | Playback error HEVC — browser tidak support natively | Probe + transcode H264 sebelum serve |
| BUG-045 | Kolom `codec` di DB selalu H264 | Probe file aktual via `ffprobe` |
| BUG-046 | 401 saat play video — HTML5 `<video>` tidak kirim `Authorization` header | Token via query param + `get_current_user_flexible` |

### Sesi #013 — 25 Juli 2026
| BUG-043 | Ganti IP kamera tidak apply — concurrent restart + HLS cache lama | Per-camera asyncio.Lock + clear HLS folder saat restart |

### Sesi #012 — 25 Juli 2026
| BUG-042 | Grid kamera tidak isi tinggi layar | Fixed |
| C-14 | Floating Window Mode (drag, resize, minimize) | Done |

### Sesi #011 — 25 Juli 2026
| BUG-038–041 | Live View sync, tampilan, drag-drop, silent fail | All fixed |

### Sesi #010 — 24 Juli 2026
| BUG-028–037 | Docker runtime, storage 500, health kosong, HLS 404, Zustand null dll | All fixed (BUG-032 belum diverifikasi) |

---

## Pipeline Playback (Setelah Sesi #015)

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
docker compose up --build -d
# Akses: http://localhost:3000 (frontend), http://localhost:8000 (API)
docker compose exec api alembic -c backend/alembic.ini upgrade head
docker exec cctv_api python scripts/setup_db.py
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
| Volume Docker (dev) | `hls_data` → `/var/lib/nvr_cam/hls`, `./recordings:/mnt/driveA` |
| Notifikasi | Telegram Bot + SMTP email |
| Login awal | User `admin`; password dari `ADMIN_PASSWORD` atau output acak `scripts/setup_db.py` |

---

## Issue Tracker & Backlog

### 🔴 KRITIS — Harus Diselesaikan Sekarang

#### BUG-055: API Container Crash Loop — Alembic Migration 003 Setengah Jalan

**Gejala:** Container `cctv_api` restart terus, error di log:
```
DROP TABLE motion_events_old;
ERROR: default value for column id ... depends on sequence motion_events_id_seq
HINT: Use DROP ... CASCADE
```

**Root cause:** Migration `20260727_000003_partition_recordings_and_events.py` gagal di step terakhir.
Timeline eksekusi migration:
- ✅ `RENAME motion_events → motion_events_old`
- ✅ `RENAME recordings → recordings_old`
- ✅ `CREATE TABLE recordings (PARTITIONED)`
- ✅ `CREATE TABLE motion_events (PARTITIONED)` + semua child partitions
- ✅ `INSERT INTO recordings ... SELECT FROM recordings_old` (copy data)
- ✅ `INSERT INTO motion_events ... SELECT FROM motion_events_old` (copy data)
- ❌ `DROP TABLE motion_events_old` ← **GAGAL** karena sequence dependency
- ❌ `DROP TABLE recordings_old` ← tidak sempat dieksekusi

**State DB sekarang:** Partitioned tables sudah ada + terisi data. Tapi `motion_events_old` dan `recordings_old` masih ada di DB.

**Fix — jalankan step ini berurutan:**

```powershell
# Step 1: Drop tabel lama yang nyangkut
docker compose exec postgres psql -U nvr_user -d nvr_db -c "DROP TABLE IF EXISTS motion_events_old CASCADE;"
docker compose exec postgres psql -U nvr_user -d nvr_db -c "DROP TABLE IF EXISTS recordings_old CASCADE;"

# Step 2: Stamp Alembic supaya tidak re-run migration 003
docker compose run --rm api alembic -c backend/alembic.ini stamp 003

# Step 3: Restart API
docker compose up -d api

# Step 4: Verifikasi — tunggu 15 detik lalu cek log
Start-Sleep 15
docker compose logs api --tail 20
```

**Fix permanen di code** (agar tidak terjadi lagi):
```powershell
# Buat fix.py lalu jalankan
Set-Content -Path fix.py -Value @'
path = "backend/db/migrations/versions/20260727_000003_partition_recordings_and_events.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace(
    'op.execute("DROP TABLE motion_events_old;")',
    'op.execute("DROP TABLE IF EXISTS motion_events_old CASCADE;")'
)
content = content.replace(
    'op.execute("DROP TABLE recordings_old;")',
    'op.execute("DROP TABLE IF EXISTS recordings_old CASCADE;")'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")
'@
python fix.py
```

**Status:** Belum di-fix — menunggu eksekusi.

---

### ❓ Yang Masih Perlu Diverifikasi (setelah BUG-055 selesai)

| # | Item | Cara Verifikasi |
|---|------|-----------------|
| 1 | Discovery scan ONVIF — hasil "Not Found" di UI | Setelah API up: test via Swagger `http://localhost:8000/api/docs` → POST `/api/v1/discovery/cameras` |
| 2 | cam_03 — 403 Forbidden terus | Edit cam_03 di halaman Cameras → update credentials RTSP yang benar |
| 3 | cam_02 — Connection refused | Cek apakah kamera online / IP berubah |
| 4 | BUG-032: 403 di `/api/v1/config/system` | `SELECT username, role FROM users;` di DB |
| 5 | BUG-047: Playback file >100MB bisa diputar | Buka halaman Playback, klik file >100MB |
| 6 | BUG-048: File 0MB tidak muncul di UI | Buka Playback, semua item harus punya ukuran valid |
| 7 | BUG-051: Live View video tidak ter-crop | Jalankan `scripts/apply_frontend_s017.ps1`, buka grid 2x2 dan 4x4 |
| 8 | BUG-052: Kamera baru langsung terpetakan ke storage | Tambah kamera, cek `GET /api/v1/storage/diagnostics` |
| 9 | BUG-053: HLS retry loading indicator muncul | Restart stream kamera, buka Live View |
| 10 | A-06: Profile + ganti password + reset admin | Coba `/profile`, ganti password, reset user lain dari Users |
| 11 | C-15/C-16: Sort & filter tabel Cameras | Klik header kolom Name → sort. Ketik di search → filter |
| 12 | C-17: Sort kamera di LiveView filter panel | Buka LiveView → Filter → tombol sort Name/Status |

### 🔴 Prioritas Tinggi

| ID | Task | Catatan |
|----|------|---------|
| — | **Fix BUG-055 dulu** sebelum apapun | API tidak bisa jalan |
| — | Verifikasi semua item di tabel atas | Terutama BUG-051, 052, 053 dan A-06 |
| F-08 | Statistik storage per kamera | Berapa GB per kamera per hari |
| F-09 | Jadwal cleanup terjadwal | Cleanup rutin, bukan hanya saat disk penuh |
| F-10 | Alert disk kritis via Telegram | Penting untuk 30 kamera |

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
| D-09 | Download rekaman ke lokal | ⏳ |
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
|----|-------|---------|
| L-07 | HTTPS/SSL | ⏭️ nanti |
| L-08–L-09 | Health check publik, UFW firewall | ⏳ |
| K-06–K-10 | Flutter analyze, build APK, FCM, biometric, landscape | ⏭️ nanti |
| J-04–J-05 | AV1 progress encode, GPU acceleration | ⏳ |
| G-07 | Auto-add dari discovery | ⏳ |

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
|------|-----------|
| **Swagger UI** | `http://localhost:8000/api/docs` — test endpoint langsung via browser, ada tombol Authorize untuk paste JWT |
| **ReDoc** | `http://localhost:8000/api/redoc` — dokumentasi semua endpoint |
| **PowerShell curl** | `Invoke-RestMethod -Method POST -Uri "..." -Headers @{Authorization="Bearer $TOKEN"} -Body '...'` |
| **httpie** | `pip install httpie` lalu `http POST localhost:8000/api/v1/... Authorization:"Bearer $TOKEN"` |
| **Postman/Insomnia** | Import dari Swagger URL untuk test GUI yang lebih lengkap |

---

## Timeline Sesi Development

| No | Tanggal | Sesi | Agent | Yang Dikerjakan |
|----|---------|------|-------|-----------------|
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

---

## Klarifikasi Penting — Setting H.265

> **Tidak ada setting H.265 di aplikasi NVR ini — by design.**
>
> Kamera Dahua dikonfigurasi codec H.265 langsung dari **web UI kamera**: `http://<IP_kamera>` → Setting → Camera → Video → Encode.
>
> Aplikasi NVR hanya menerima stream RTSP dari kamera dan otomatis mendeteksi codec via `ffprobe`. Tidak perlu — dan tidak bisa — mengubah codec kamera dari dalam aplikasi NVR.
