# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 24 Juli 2026, 18:30 WIB (Sesi #010 — Debugging Docker + UI Redesign)  
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

## 🐛 Bug Fixes Sesi #010 — Docker Mode + UI

> **Tanggal:** 24 Juli 2026  
> **Scope:** Debugging runtime Docker, perbaikan UI ke tema terang, fix auth + navigation

### Backend

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| B-01 | `GET /api/v1/storage` → 500 | `DriveStatus` schema punya field `path` tapi router kirim `mount=` + `label=` yang tidak ada di schema | ✅ Fix: tambah `label: Optional[str]`, ganti `mount=` → `path=` |
| B-02 | `GET /api/v1/system/health` → data kosong di frontend | Field nama mismatch: backend return `cpu_pct`, frontend expect `cpu_usage`, dst. | ✅ Fix: rename semua field di `system.py` agar cocok (`cpu_usage`, `ram_usage`, `disk_usage`, `uptime_seconds`, `cameras_online/offline/total`) |
| B-03 | Tambah kamera → `OSError: Read-only file system` | `config/` di-mount `:ro` di `docker-compose.yml` → folder `backups/` tidak bisa ditulis | ✅ Fix: hapus `:ro`, buat folder `config/backups/` |
| B-04 | Test connection → selalu gagal (route tidak ketemu) | Route `POST /cameras/test-connection` ditambah tapi posisinya setelah `{camera_id}` routes; plus ada BOM character di file | ✅ Fix: rewrite `config.py` bersih tanpa BOM, route statis di atas `{camera_id}` |
| B-05 | `GET /api/v1/config/system` → 403 | User yang login tidak punya role admin yang cukup | ⚠️ Belum diverifikasi — perlu cek role user di DB |
| B-06 | `GET /api/v1/storage/status` → 401 | Frontend tidak kirim token saat hit endpoint ini | ✅ Fix: `RTSPTestButton` dan form kamera kini attach `Authorization` header manual |
| B-07 | Test connection timeout tidak informatif | `ffprobe` pakai UDP default + pesan error mentah panjang | ✅ Fix: tambah `-rtsp_transport tcp`, pesan error dipersempit ke baris terakhir |

### Frontend

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| F-01 | CSS / UI masih gelap setelah update | Docker layer cache — build tidak recompile Tailwind | ✅ Fix: `docker compose build --no-cache frontend` |
| F-02 | Sidebar menu tidak muncul setelah refresh | `user` di Zustand store = null setelah refresh → `hasRole()` return false semua | ✅ Fix: persist user ke `localStorage` (`auth_user`), restore saat init |
| F-03 | Navigasi antar menu lambat | `retry: 1` + `staleTime` pendek → setiap pindah halaman refetch ulang | ✅ Fix: `retry: 0`, `staleTime: 60s`, `refetchOnWindowFocus: false` |
| F-04 | Login lambat (2 round trip) | `authApi.me()` dipanggil setelah `login()` secara sequential, tanpa token di header axios dulu | ✅ Fix: set token ke `apiClient.defaults.headers` sebelum call `/me` |
| F-05 | Konten area mentok ke tepi (no margin) | Semua halaman tidak punya padding container | ✅ Fix: tiap halaman besar diberi `p-4` / `p-6` |
| F-06 | HLS 404 di nginx frontend | Volume `hls_data` hanya di-mount ke container `api`, tidak ke `frontend` | ✅ Fix: tambah `volumes` di service `frontend` di `docker-compose.yml` |
| F-07 | Emoji icon di sidebar render sebagai `â›¯` (mojibake) | File disimpan dengan encoding yang salah (bukan UTF-8) | ✅ Fix: semua `Set-Content` pakai `-Encoding UTF8` |

### UI Redesign (Sesi #010)

| File | Perubahan |
|------|-----------|
| `pages/Login/index.tsx` | Tema putih/sky, label rapi, spinner loading, error box berwarna |
| `components/layout/Sidebar.tsx` | Putih bersih, nav aktif sky-600, avatar inisial user, footer dengan role |
| `App.tsx` | Background `bg-slate-100` ganti hitam pekat |
| `pages/System/index.tsx` | Kartu putih, badge status berwarna, progress bar 3 warna |
| `pages/LiveView/index.tsx` | Toolbar putih, tombol grid lebih rapi, filter panel bersih |
| `components/camera/CameraForm.tsx` | Redesign penuh: section divider, toggle switch custom, layout grid 3 kolom |
| `components/camera/RTSPTestButton.tsx` | Tombol sky, hasil test berwarna (hijau/merah), pesan error lebih jelas |
| `index.css` | Background paksa `#f1f5f9` di level CSS sebagai fallback |

> **Halaman yang BELUM di-redesign ke tema terang:** Storage, Playback, Events, Cameras, Users, Settings

---

## 🐛 Bug Fixes Sesi #009

| ID | Bug | Status |
|----|-----|--------|
| BUG-025 | `cctv_db` crash: `database "nvr_user" does not exist` | ✅ Fixed |
| BUG-026 | `cctv_api` crash: `Path doesn't exist: '/app/db/migrations'` | ✅ Fixed |
| BUG-027 | `cctv_web` crash: `unknown directive "﻿server"` (BOM di nginx config) | ✅ Fixed |

---

## 🎯 Batch 1 — Live View Improvements

> **Status Batch:** ✅ Selesai (Sesi #009, 22 Juli 2026)

| ID | Issue | Status | File yang Diubah |
|----|-------|--------|------------------|
| C-05 | Fullscreen per kamera (double-click atau tombol ⛶) | ✅ | `VideoPlayer.tsx`, `FullscreenPlayer.tsx` (baru), `CameraGrid.tsx`, `cameras.ts` |
| C-06 | Pilihan layout grid (1×1, 2×2, 3×3, 4×4, 5×6) | ✅ | `LiveView/index.tsx` |
| C-07 | Filter/multi-select subset kamera yang ditampilkan | ✅ | `LiveView/index.tsx`, `cameras.ts` |
| C-11 | Toggle Main/Sub stream per kamera | ✅ | `VideoPlayer.tsx`, `cameras.ts`, `api/cameras.ts`, `stream.py` |
| C-13 | Picture-in-Picture via Browser PiP API | ✅ | `VideoPlayer.tsx` |

---

## 🎯 Batch 2 — Download Rekaman

> **Status Batch:** ✅ Selesai (Sesi #009, 22 Juli 2026)

| ID | Issue | Status | File yang Diubah |
|----|-------|--------|------------------|
| D-09 | Download rekaman ke lokal (endpoint + tombol di UI) | ✅ | `recordings.py` (endpoint `/download`), `Playback/index.tsx`, `api/recordings.ts` |

---

## 🎯 Batch 3 — Alert Disk + Auto-delete Setting

> **Status Batch:** ⏳ Belum mulai

| ID | Issue | Status |
|----|-------|--------|
| F-10 | Alert Telegram saat disk < threshold kritis | ⏳ |
| F-09 | Jadwal cleanup terjadwal dari UI | ⏳ |
| F-08 | Statistik penggunaan storage per kamera | ⏳ |

---

## ❓ Yang Masih Perlu Diverifikasi (Carry-over dari Sesi #010)

| # | Item | Cara Verifikasi |
|---|------|-----------------|
| 1 | Test connection kamera bisa dijangkau dari dalam Docker | `docker exec cctv_api ping 10.1.0.150` |
| 2 | 403 di `/api/v1/config/system` | Cek role user di DB: `SELECT username, role FROM users;` |
| 3 | HLS stream 404 sudah resolved setelah volume mount fix | Tes saat kamera fisik online |
| 4 | Redesign halaman Storage, Playback, Events, Cameras, Users, Settings | Belum dikerjakan |

---

## 🔲 Backlog Umum (Belum Dijadwalkan)

### Auth & User
| ID | Issue | Status |
|----|-------|--------|
| A-06 | Ganti password sendiri — endpoint perlu diverifikasi | ⏳ |
| A-07 | Two-Factor Authentication (2FA) | ⏭️ nanti |
| A-08 | Audit log aktivitas user | ⏳ |
| A-09 | Session timeout auto logout | ⏳ |

### Kamera
| ID | Issue | Status |
|----|-------|--------|
| B-13 | Kamera group/tag per area (Lantai 1, Gudang, dll) | ⏳ |
| B-14 | PTZ control via ONVIF | ⏳ |
| B-16 | Dukungan kamera non-RTSP (MJPEG/HTTP) | ⏳ |

### Live View
| ID | Issue | Status |
|----|-------|--------|
| C-08 | Drag-drop reorder posisi kamera di grid | ⏳ |
| C-09 | Digital zoom live view (scroll/pinch) | ⏳ |
| C-10 | Audio live (jika kamera support) | ⏳ |
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

### Storage (Batch 3)
| ID | Issue | Status |
|----|-------|--------|
| F-08 | Statistik storage per kamera | ⏳ |
| F-09 | Jadwal cleanup terjadwal dari UI | ⏳ |
| F-10 | Alert disk kritis via Telegram | ⏳ |

### Konfigurasi
| ID | Issue | Status |
|----|-------|--------|
| H-09 | Setting FPS adaptif motion di Settings UI | ⏳ |
| H-10 | Setting FPS custom live view di Settings UI | ⏳ |
| H-11 | WhatsApp/Signal notification | ⏳ |
| H-12 | Webhook notification (custom URL) | ⏳ |

### Monitoring Server
| ID | Issue | Status |
|----|-------|--------|
| I-08 | Log viewer di halaman System | ⏳ |
| I-09 | Alert CPU/RAM tinggi via Telegram | ⏳ |
| I-10 | Grafik historis CPU/RAM/disk | ⏳ |
| I-11 | Restart service dari UI | ⏳ |

### AV1 Encoder
| ID | Issue | Status |
|----|-------|--------|
| J-04 | Progress encode di UI | ⏳ |
| J-05 | Hardware acceleration GPU/VA-API | ⏳ |

### Discovery
| ID | Issue | Status |
|----|-------|--------|
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

## Bug Tracker Keseluruhan

| ID | Bug | Status |
|----|-----|--------|
| BUG-001 s/d BUG-024 | Berbagai bug sesi #001–#007 | ✅ Fixed |
| BUG-025 | docker-compose DB name tidak sinkron | ✅ Fixed sesi #009 |
| BUG-026 | alembic path salah di Docker | ✅ Fixed sesi #009 |
| BUG-027 | nginx BOM character crash | ✅ Fixed sesi #009 |
| BUG-028 | `DriveStatus` schema field mismatch (`mount=` vs `path=`) | ✅ Fixed sesi #010 |
| BUG-029 | `system.py` field name mismatch frontend–backend | ✅ Fixed sesi #010 |
| BUG-030 | `config/` volume mount `:ro` — tidak bisa tulis backup | ✅ Fixed sesi #010 |
| BUG-031 | `POST /cameras/test-connection` route shadowed oleh `{camera_id}` + BOM | ✅ Fixed sesi #010 |
| BUG-032 | `GET /api/v1/config/system` → 403 | ⚠️ Belum diverifikasi |
| BUG-033 | `/api/v1/storage/status` → 401 (token tidak dikirim) | ✅ Fixed sesi #010 |
| BUG-034 | `ffprobe` timeout tidak informatif (UDP + pesan panjang) | ✅ Fixed sesi #010 |
| BUG-035 | Sidebar mojibake emoji (encoding bukan UTF-8) | ✅ Fixed sesi #010 |
| BUG-036 | HLS volume tidak di-mount ke container frontend | ✅ Fixed sesi #010 |
| BUG-037 | Zustand `user` null setelah refresh → menu tidak muncul | ✅ Fixed sesi #010 |
| BUG-013 | Flutter analyze belum diverifikasi | ⏭️ nanti |
| BUG-019 | structlog dead code | ⏭️ skip |

---

## Ringkasan Progress

| Batch | Fitur | Status |
|-------|-------|--------|
| Batch 1 — Live View | 5 fitur (C-05, C-06, C-07, C-11, C-13) | ✅ Selesai |
| Batch 2 — Download Rekaman | 1 fitur (D-09) | ✅ Selesai |
| Batch 3 — Alert Disk | 3 fitur (F-08, F-09, F-10) | ⏳ Belum |
| Bug fixes sesi #009 | 3 bug (BUG-025–027) | ✅ Selesai |
| Bug fixes sesi #010 | 10 bug (BUG-028–037) | ✅ 9 fixed, 1 pending |
| UI Redesign sesi #010 | 8 file diubah ke tema terang | ✅ Sebagian (6 halaman sisa) |
| Sisa backlog | ~38 fitur | ⏳ Belum dijadwalkan |
