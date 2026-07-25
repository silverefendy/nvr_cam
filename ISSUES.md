# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 25 Juli 2026, 09:45 WIB (Sesi #011 — Fix Live View + Cleanup Repo)  
**Repo:** https://github.com/silverefendy/nvr_cam

> File ini mencatat semua issue/task yang sedang dikerjakan atau sudah selesai.  
> Update setiap sesi: ubah status, isi kolom Sesi + Tanggal.

---

## Legenda

| Simbol | Arti |
|--------|------|
| ✅ | Selesai dan sudah di-push ke repo |
| 🔄 | Sedang dikerjakan |
| ⏳ | Belum mulai |
| ⏭️ | Ditunda / skip untuk sekarang |
| ❌ | Dibatalkan |
| ⚠️ | Perlu verifikasi lanjut |

---

## 🐛 Bug Fixes Sesi #011 — Live View + Cleanup

> **Tanggal:** 25 Juli 2026  
> **Scope:** Fix tombol grid, UI dark theme, drag-drop, error handling form; cleanup file sampah

### Frontend

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-038 | Tombol 1x1/2x2/3x3/4x4 tidak sinkron | `setGridSize()` hanya update kolom, tidak sesuaikan `selectedCameras`. Grid columns berubah tapi jumlah VideoPlayer tetap | ✅ Fix: `setGridSize()` sekarang auto-expand/trim `selectedCameras` sesuai `GRID_CAPACITY` |
| BUG-039 | Live View tampilan jelek — sudut rounded, background putih/abu | `CameraGrid` pakai Tailwind class yang override styling, `VideoPlayer` pakai `rounded`, gap terlalu besar | ✅ Fix: full dark theme (`#0f1117`), inline style, gap 2px, no border-radius |
| BUG-040 | Drag-drop kamera di grid tidak ada | Belum diimplementasikan sama sekali | ✅ Fix: HTML5 native drag-drop di `CameraGrid.tsx`, `reorderCameras()` di store |
| BUG-041 | Error tambah kamera silent fail | `saveMutation.onError` tidak di-handle → form tutup tanpa feedback | ✅ Fix: error banner merah, parse FastAPI error format, validasi client-side |

### Cleanup

| Item | Tindakan | Status |
|------|----------|--------|
| `fix_cameras_page.py` | Hapus — script patch satu kali yang sudah di-apply | ✅ Dihapus |
| `fix_dep_repo.py` | Hapus — script patch satu kali yang sudah di-apply | ✅ Dihapus |
| `fix_fps.py` | Hapus — script patch satu kali yang sudah di-apply | ✅ Dihapus |
| `patch_dep.py` | Hapus — duplikat dari fix_dep_repo.py, sudah di-apply | ✅ Dihapus |
| `PROGRESS.md` | Hapus — konten sudah tercakup di ISSUES.md + HANDOFF.md | ✅ Dihapus |
| `AUDIT_REPORT.md` | Hapus — outdated (22 Juli), temuan kritis sudah masuk ISSUES.md | ✅ Dihapus |
| `SUMMARY.md` | Hapus — duplikasi dari README.md + ISSUES.md | ✅ Dihapus |
| `docs/debug_summary.md` | Hapus — konten diintegrasikan ke ISSUES.md | ✅ Dihapus |

### ⚠️ Perlu Dilakukan Setelah Push

```bash
git pull && docker compose up --build -d frontend
```

Verifikasi setelah rebuild:
1. Tombol 1x1/2x2/3x3/4x4 → jumlah VideoPlayer bertambah/berkurang sesuai grid
2. Live View background hitam, tidak ada sudut rounded di video
3. Drag kamera dari satu slot ke slot lain → posisi tertukar
4. Tambah kamera dengan field kosong → muncul pesan error merah di form

---

## 🐛 Bug Fixes Sesi #010 — Docker Mode + UI Redesign

> **Tanggal:** 24 Juli 2026  
> **Scope:** Debugging runtime Docker, perbaikan UI ke tema terang, fix auth + navigation

### Backend

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-028 | `GET /api/v1/storage` → 500 | `DriveStatus` schema field mismatch (`mount=` vs `path=`) | ✅ Fixed |
| BUG-029 | `GET /api/v1/system/health` → data kosong di frontend | Field nama mismatch backend vs frontend | ✅ Fixed |
| BUG-030 | Tambah kamera → `OSError: Read-only file system` | `config/` di-mount `:ro` di docker-compose | ✅ Fixed |
| BUG-031 | `POST /cameras/test-connection` selalu gagal | Route statis tertutup oleh `{camera_id}` + BOM character di file | ✅ Fixed |
| BUG-032 | `GET /api/v1/config/system` → 403 | Role user kurang | ⚠️ Belum diverifikasi — cek `SELECT username, role FROM users;` |
| BUG-033 | `/api/v1/storage/status` → 401 | Frontend tidak kirim token | ✅ Fixed |
| BUG-034 | Test connection timeout tidak informatif | `ffprobe` UDP + pesan error panjang | ✅ Fixed |
| BUG-035 | Sidebar mojibake emoji | Encoding bukan UTF-8 | ✅ Fixed |
| BUG-036 | HLS 404 di nginx container | Volume `hls_data` tidak di-mount ke service `frontend` | ✅ Fixed |
| BUG-037 | Zustand `user` null setelah refresh → menu tidak muncul | Tidak ada persistensi ke `localStorage` | ✅ Fixed |

### UI Redesign (Sesi #010 — tema terang)

| File | Perubahan |
|------|-----------|
| `pages/Login/index.tsx` | Tema putih/sky, label rapi, spinner loading, error box berwarna |
| `components/layout/Sidebar.tsx` | Putih bersih, nav aktif sky-600, avatar inisial user, footer role |
| `App.tsx` | Background `bg-slate-100` |
| `pages/System/index.tsx` | Kartu putih, badge berwarna, progress bar 3 warna |
| `pages/LiveView/index.tsx` | Toolbar putih (sesi #010) → **dioverride ke dark di sesi #011** |
| `components/camera/CameraForm.tsx` | Section divider, toggle switch custom, grid 3 kolom |
| `components/camera/RTSPTestButton.tsx` | Tombol sky, hasil berwarna |
| `index.css` | Background `#f1f5f9` sebagai fallback |

> **Halaman yang BELUM di-redesign ke tema terang:** Storage, Playback, Events, Cameras, Users, Settings

---

## 🐛 Bug Fixes Sesi #009 — Docker Bootstrap

| ID | Bug | Status |
|----|-----|--------|
| BUG-025 | `database "nvr_user" does not exist` | ✅ Fixed |
| BUG-026 | `Path doesn't exist: '/app/db/migrations'` | ✅ Fixed |
| BUG-027 | nginx crash `unknown directive "﻿server"` (BOM) | ✅ Fixed |

---

## 🐛 Bug Fixes Sesi #001–#008 (Historis)

| ID | Bug | Status |
|----|-----|--------|
| BUG-001 | `api/users.ts` missing | ✅ Fixed (#004 Devin) |
| BUG-002 | `api/storage.ts` missing | ✅ Fixed (#004 Devin) |
| BUG-003 | `SystemHealth` field names mismatch | ✅ Fixed (#004 Devin) |
| BUG-004 | `DriveStatus/StorageStatus` field mismatch | ✅ Fixed (#004 Devin) |
| BUG-005 | `User.id` string vs number | ✅ Fixed (#004 Devin) |
| BUG-006 | `systemApi.getHealth` alias missing | ✅ Fixed (#004 Devin) |
| BUG-007 | Flutter `sharedPreferencesProvider` cross-file | ✅ Fixed (#004 Devin) |
| BUG-008 | VLC Player constructor salah | ✅ Fixed (#004 Devin) |
| BUG-009 | `withOpacity()` deprecated + assets folder | ✅ Fixed (#004 Devin) |
| BUG-010 | TanStack Query `onSuccess` deprecated | ✅ Fixed (#004 Devin) |
| BUG-011 | `index.html` entry point missing | ✅ Fixed (#004 Devin) |
| BUG-012 | `getSnapshot` → `snapshot` API method name | ✅ Fixed (#004 Devin) |
| BUG-013 | Flutter `flutter analyze` belum diverifikasi | ⏭️ nanti |
| BUG-014 | `backend/Dockerfile` duplikat + CMD salah | ✅ Fixed (#006 Cascade) |
| BUG-015 | `docker-compose.yml` pakai Dockerfile salah | ✅ Fixed (#006 Cascade) |
| BUG-016 | `AsyncSessionLocal.close_all()` tidak ada | ✅ Fixed (#006 Cascade) |
| BUG-017 | `alembic.ini` URL masih placeholder | ✅ Fixed (#006 Cascade) |
| BUG-018 | Default DB name/user tidak sinkron | ✅ Fixed (#006 Cascade) |
| BUG-019 | `logger.py` dead code (structlog) | ⏭️ skip |
| BUG-020 | `install.sh` DB name/user salah | ✅ Fixed (#007 Claude) |
| BUG-021 | `install.sh` nama service salah | ✅ Fixed (#007 Claude) |
| BUG-022 | `install.sh` path nginx conf salah | ✅ Fixed (#007 Claude) |
| BUG-023 | nginx `cctv.conf` snapshots path ke `/tmp/hls` | ✅ Fixed (#007 Claude) |
| BUG-024 | `install.sh` HLS dir di `/tmp/hls` | ✅ Fixed (#007 Claude) |

---

## 🐛 Bug Fixes Docker/Recorder (Debug Session antara #009–#010)

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| — | Deadlock asyncio.Lock di ConfigManager | `_create_backup()` + `_read_yaml()` nested acquire lock yang sama (non-reentrant) | ✅ Fixed: versi `_unlocked()` untuk internal calls |
| — | Config router pakai YAML bukan PostgreSQL | `config.py` CRUD kamera tulis ke `cameras.yaml`, list kamera baca dari PostgreSQL | ✅ Fixed: rewrite CRUD pakai `CameraRepository` |
| — | Redirect paksa ke /setup saat kamera kosong | `App.tsx` redirect ke `/setup` jika kamera kosong | ✅ Fixed: hapus redirect paksa |
| — | BaseRepository tidak commit setelah create/delete | `create()` hanya `flush()` tanpa `commit()` | ✅ Fixed: tambah `await self.db.commit()` |
| — | `subprocess.Popen` blocking asyncio | `proc.wait()` via `run_in_executor` masih blocking | ✅ Fixed: ganti ke `asyncio.create_subprocess_exec` |
| — | HLS ditulis ke `/tmp/hls` bukan volume Docker | `HLS_BASE_DIR` pointing ke `/tmp/hls` | ✅ Fixed: ganti ke `/var/lib/nvr_cam/hls` |
| — | `segment_duration` tidak ada di model Camera | `cam.segment_duration` akses field yang tidak ada di SQLAlchemy model | ✅ Fixed: helper `_camera_to_dict()` baca dari `config_json` |
| — | Status Offline padahal recorder jalan | Halaman Cameras query `/config/cameras` (tanpa `is_online`) | ✅ Fixed: ganti ke `/cameras` dengan `refetchInterval: 10000` |
| — | Password hilang saat Edit kamera | Form populate dengan `password: ''` hardcoded | ✅ Fixed: baca dari `camera.config_json.password` |
| — | `hls_temp_dir` default salah di settings | `config.py` default `/tmp/hls` | ✅ Fixed: ganti ke `/var/lib/nvr_cam/hls` |
| — | `useHLSPlayer` tidak re-attach jika videoRef null saat mount | Dependency array tidak include `videoRef.current` | ✅ Fixed: tambah ke deps, plus error recovery handler |
| — | HEVC (H.265) tidak didukung hls.js di browser | HLS pakai `-c:v copy`, output HEVC tidak bisa di-decode hls.js | ✅ Fixed: `detect_video_codec()`, auto-transcode jika HEVC |

---

## 🎯 Batch 1 — Live View Improvements

> **Status Batch:** ✅ Selesai (Sesi #009)

| ID | Issue | Status |
|----|-------|--------|
| C-05 | Fullscreen per kamera (double-click atau tombol ⛶) | ✅ |
| C-06 | Layout grid pilihan (1×1, 2×2, 3×3, 4×4, 5×6) | ✅ |
| C-07 | Filter/multi-select subset kamera | ✅ |
| C-08 | Drag-drop reorder kamera di grid | ✅ (Sesi #011) |
| C-11 | Toggle Main/Sub stream per kamera | ✅ |
| C-13 | Picture-in-Picture via Browser PiP API | ✅ |

---

## 🎯 Batch 2 — Download Rekaman

> **Status Batch:** ✅ Selesai (Sesi #009)

| ID | Issue | Status |
|----|-------|--------|
| D-09 | Download rekaman ke lokal | ✅ |

---

## 🎯 Batch 3 — Alert Disk + Storage

> **Status Batch:** ⏳ Belum mulai

| ID | Issue | Status |
|----|-------|--------|
| F-10 | Alert Telegram saat disk < threshold kritis | ⏳ |
| F-09 | Jadwal cleanup terjadwal dari UI | ⏳ |
| F-08 | Statistik penggunaan storage per kamera | ⏳ |

---

## ❓ Yang Masih Perlu Diverifikasi

| # | Item | Cara Verifikasi |
|---|------|-----------------|
| 1 | Test connection kamera bisa dijangkau dari dalam Docker | `docker exec cctv_api ping 10.1.0.150` |
| 2 | BUG-032: 403 di `/api/v1/config/system` | `SELECT username, role FROM users;` di DB |
| 3 | Fix 13–16 sudah berjalan setelah rebuild | `docker compose up --build -d frontend` |

---

## 🔲 Backlog Umum (Belum Dijadwalkan)

### Auth & User
| ID | Issue | Status |
|----|-------|--------|
| A-06 | Ganti password sendiri | ⏳ |
| A-07 | Two-Factor Authentication (2FA) | ⏭️ nanti |
| A-08 | Audit log aktivitas user | ⏳ |
| A-09 | Session timeout auto logout | ⏳ |

### Kamera
| ID | Issue | Status |
|----|-------|--------|
| B-13 | Kamera group/tag per area | ⏳ |
| B-14 | PTZ control via ONVIF | ⏳ |
| B-16 | Dukungan kamera non-RTSP (MJPEG/HTTP) | ⏳ |

### Live View
| ID | Issue | Status |
|----|-------|--------|
| C-09 | Digital zoom live view | ⏳ |
| C-10 | Audio live | ⏳ |
| C-12 | FPS custom live view per kamera | ⏳ |

### Rekaman
| ID | Issue | Status |
|----|-------|--------|
| D-10 | Motion event marker di timeline playback | ⏳ |
| D-11 | Kliping rekaman (export menit X–Y) | ⏳ |
| D-12 | Export ke format lain (MKV, AVI) | ⏳ |
| D-13 | Pencarian rekaman by rentang tanggal fleksibel | ⏳ |

### Motion Detection
| ID | Issue | Status |
|----|-------|--------|
| E-07 | Snapshot lightbox (klik thumbnail → modal besar) | ⏳ |
| E-08 | Export laporan events CSV/PDF | ⏳ |
| E-09 | Motion masking (zona area diabaikan) | ⏳ |
| E-10 | Sensitivitas motion adjustable per kamera | ⏳ |
| E-11 | Cooldown notifikasi anti-spam | ⏳ |
| E-12 | Klip video pre/post event (buffer 10 detik) | ⏳ |
| E-13 | FPS adaptif saat motion | ⏳ |

### Konfigurasi & Monitoring
| ID | Issue | Status |
|----|-------|--------|
| H-09 | Setting FPS adaptif motion | ⏳ |
| H-10 | Setting FPS custom live view | ⏳ |
| H-11 | WhatsApp/Signal notification | ⏳ |
| H-12 | Webhook notification | ⏳ |
| I-08 | Log viewer di halaman System | ⏳ |
| I-09 | Alert CPU/RAM tinggi via Telegram | ⏳ |
| I-10 | Grafik historis CPU/RAM/disk | ⏳ |
| I-11 | Restart service dari UI | ⏳ |

### AV1 & Discovery
| ID | Issue | Status |
|----|-------|--------|
| J-04 | Progress encode di UI | ⏳ |
| J-05 | Hardware acceleration GPU/VA-API | ⏳ |
| G-07 | Auto-add kamera dari hasil discovery | ⏳ |

### Deployment
| ID | Issue | Status |
|----|-------|--------|
| L-07 | HTTPS/SSL (Let's Encrypt) | ⏭️ nanti |
| L-08 | Health check endpoint publik `/health` | ⏳ |
| L-09 | Firewall setup UFW | ⏳ |

### Mobile Flutter
| ID | Issue | Status |
|----|-------|--------|
| K-06 | `flutter analyze` verify | ⏭️ nanti |
| K-07 | `flutter build APK` release | ⏭️ nanti |
| K-08 | Push notification FCM | ⏭️ nanti |
| K-09 | Fingerprint/biometric login | ⏭️ nanti |
| K-10 | Landscape mode/tablet layout | ⏭️ nanti |

---

## UI Redesign Sisa (Tema Terang)

> Halaman berikut belum di-redesign ke tema terang (seperti Login + Sidebar)

| Halaman | Status |
|---------|--------|
| Storage | ⏳ |
| Playback | ⏳ |
| Events | ⏳ |
| Cameras | ⏳ |
| Users | ⏳ |
| Settings | ⏳ |

---

## Timeline Sesi Development

| No | Tanggal | Sesi | Agent | Yang Dikerjakan |
|----|---------|------|-------|-----------------|
| 1–2 | — | #001–002 | Claude | Kerangka awal, backend, frontend, Flutter |
| 3 | 2 Juli 2026 | #003 | Claude | Audit + update dokumentasi |
| 4 | 3 Juli 2026 | #004 | Devin AI | Fix BUG-001–012 (frontend build success) |
| 5 | 8 Juli 2026 | #006 | Cascade AI | Fix BUG-014–018 (Docker, SQLAlchemy, Alembic) |
| 6 | 9 Juli 2026 | #007 | Claude | Fix install.sh (BUG-020–024), cleanup repo |
| 7 | 22 Juli 2026 | #008–009 | Claude | Audit kode, fix BUG-025–027, Batch 1+2 features |
| 8 | 24 Juli 2026 | #010 | Claude | Fix Docker runtime (BUG-028–037), UI redesign sebagian |
| 9 | 25 Juli 2026 | #011 | Claude | Fix BUG-038–041 (Live View grid + drag-drop), cleanup file |
