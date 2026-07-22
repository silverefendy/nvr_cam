# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 22 Juli 2026 (Sesi #009 — lanjutan)  
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

---

## 🐛 Bug Fixes Sesi #009

| ID | Bug | Status | Sesi | Tanggal | Root Cause |
|----|-----|--------|------|---------|------------|
| BUG-025 | `cctv_db` crash: `database "nvr_user" does not exist` | ✅ | #009 | 22 Jul 2026 | `docker-compose.yml` masih pakai default lama `cctv_user`/`cctv_db` — tidak sinkron dengan `.env.example` |
| BUG-026 | `cctv_api` crash: `Path doesn't exist: '/app/db/migrations'` | ✅ | #009 | 22 Jul 2026 | `alembic.ini` pakai `script_location = db/migrations` tapi WORKDIR di Docker adalah `/app` dan kode ada di `/app/backend/` — path tidak match. Fix: `sed` di Dockerfile patch jadi `backend/db/migrations` |
| BUG-027 | `cctv_web` crash: `unknown directive "﻿server"` | ✅ | #009 | 22 Jul 2026 | BOM character (UTF-8 BOM `\xEF\xBB\xBF`) di `cctv.conf` dan `Dockerfile.frontend.prod` — file disimpan dengan encoding Windows BOM. Fix: tulis ulang file tanpa BOM |

---

## 🎯 Batch 1 — Live View Improvements

> **Target:** Perbaiki UI live view agar lebih fungsional untuk monitoring 30 kamera  
> **Sesi:** #009 — 22 Juli 2026  
> **Status Batch:** ✅ Selesai

| ID | Issue | Status | Sesi | Tanggal | File yang Diubah |
|----|-------|--------|------|---------|------------------|
| C-05 | Fullscreen per kamera (double-click atau tombol ⛶) | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx`, `FullscreenPlayer.tsx` (baru), `CameraGrid.tsx`, `cameras.ts` (store) |
| C-06 | Pilihan layout grid (1×1, 2×2, 3×3, 4×4, 5×6) | ✅ | #009 | 22 Jul 2026 | `LiveView/index.tsx` |
| C-07 | Filter/multi-select subset kamera yang ditampilkan | ✅ | #009 | 22 Jul 2026 | `LiveView/index.tsx`, `cameras.ts` (store: tambah selectAll/selectNone) |
| C-11 | Toggle Main/Sub stream per kamera | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx`, `cameras.ts` (store: streamTypeOverride), `api/cameras.ts`, `stream.py` |
| C-13 | Picture-in-Picture via Browser PiP API | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx` |

### Catatan Teknis Batch 1

- **Fullscreen (C-05):** Overlay modal full-window. Double-click video atau klik tombol ⛶. Tutup dengan ESC atau tombol Tutup. Component baru: `FullscreenPlayer.tsx`
- **Layout grid (C-06):** Tombol 1×1/2×2/3×3/4×4/5×6 di toolbar. State di Zustand store.
- **Filter kamera (C-07):** Panel filter toggle, search by nama/lokasi, toggle per kamera, tombol Pilih Semua / Hapus Semua. Badge status online/offline per kamera di filter.
- **Toggle stream (C-11):** Tombol MAIN/SUB muncul saat hover di atas video. Default: SUB stream. State per-kamera di Zustand. Backend `stream.py` sudah support query param `?stream=main|sub`, HLS dir dipisah: `{camera_id}_main/` dan `{camera_id}_sub/`.
- **PiP (C-13):** Browser PiP API. Tombol ⧉ muncul saat hover, hanya jika browser support.

---

## 🎯 Batch 2 — Download Rekaman

> **Target:** User bisa download file rekaman dari halaman Playback  
> **Sesi:** #009 — 22 Juli 2026  
> **Status Batch:** ✅ Selesai

| ID | Issue | Status | Sesi | Tanggal | File yang Diubah |
|----|-------|--------|------|---------|------------------|
| D-09 | Download rekaman ke lokal (endpoint + tombol di UI) | ✅ | #009 | 22 Jul 2026 | `backend/api/routers/recordings.py` (endpoint baru `/download`), `frontend/src/pages/Playback/index.tsx` (tombol ⬇ sudah ada), `frontend/src/api/recordings.ts` (downloadUrl sudah ada) |

### Catatan Teknis Batch 2

- **Backend endpoint baru:** `GET /api/v1/recordings/{id}/download`
- Berbeda dari `/play` — endpoint ini mengirim header `Content-Disposition: attachment` sehingga browser langsung save dialog
- Nama file otomatis: `{camera_id}_{YYYY-MM-DD_HH-MM-SS}.mp4` (deskriptif untuk arsip)
- Frontend `Playback/index.tsx` sudah punya tombol ⬇ Download di setiap item list dan di info bar bawah player — tidak ada perubahan frontend
- Frontend `api/recordings.ts` sudah punya `downloadUrl` yang point ke `/download` — tidak ada perubahan

---

## 🎯 Batch 3 — Alert Disk + Auto-delete Setting

> **Target:** Notifikasi saat disk kritis + setting jadwal cleanup dari UI  
> **Status Batch:** ⏳ Belum mulai

| ID | Issue | Status | Sesi | Tanggal | File yang Diubah |
|----|-------|--------|------|---------|------------------|
| F-10 | Alert Telegram saat disk < threshold kritis | ⏳ | — | — | `backend/services/storage/manager.py`, `backend/services/notifier/dispatcher.py` |
| F-09 | Jadwal cleanup terjadwal (bukan hanya saat disk penuh) | ⏳ | — | — | `backend/services/storage/manager.py`, `frontend/src/pages/Settings/` |
| F-08 | Statistik penggunaan storage per kamera | ⏳ | — | — | `backend/api/routers/storage.py`, `frontend/src/pages/Storage/` |

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

### Live View (sisa setelah Batch 1)
| ID | Issue | Status |
|----|-------|--------|
| C-08 | Drag-drop reorder posisi kamera di grid | ⏳ |
| C-09 | Digital zoom live view (scroll/pinch) | ⏳ |
| C-10 | Audio live (jika kamera support) | ⏳ |
| C-12 | FPS custom live view per kamera | ⏳ |

### Rekaman (sisa setelah Batch 2)
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
| K-06 | flutter analyze verify | ⏭️ nanti |
| K-07 | flutter build APK release | ⏭️ nanti |
| K-08 | Push notification FCM | ⏭️ nanti |
| K-09 | Fingerprint/biometric login | ⏭️ nanti |
| K-10 | Landscape mode/tablet layout | ⏭️ nanti |

---

## Bug Tracker Keseluruhan

| ID | Bug | Status |
|----|-----|--------|
| BUG-001 s/d BUG-024 | Berbagai bug sesi #001–#007 | ✅ Semua fixed |
| BUG-025 | docker-compose DB name tidak sinkron | ✅ Fixed sesi #009 |
| BUG-026 | alembic path salah di Docker | ✅ Fixed sesi #009 |
| BUG-027 | nginx BOM character crash | ✅ Fixed sesi #009 |
| BUG-013 | Flutter analyze belum diverifikasi | ⏭️ nanti |
| BUG-019 | structlog dead code | ⏭️ skip |

---

## Ringkasan Progress

| Batch | Fitur | Status |
|-------|-------|--------|
| Batch 1 — Live View | 5 fitur (C-05, C-06, C-07, C-11, C-13) | ✅ Selesai |
| Batch 2 — Download Rekaman | 1 fitur (D-09) | ✅ Selesai |
| Batch 3 — Alert Disk | 3 fitur (F-08, F-09, F-10) | ⏳ Belum |
| Bug fixes sesi #009 | 3 bug (BUG-025, BUG-026, BUG-027) | ✅ Selesai |
| Sisa backlog | ~38 fitur | ⏳ Belum dijadwalkan |
