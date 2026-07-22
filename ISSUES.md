# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 22 Juli 2026  
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

## 🎯 Batch 1 — Live View Improvements

> **Target:** Perbaiki UI live view agar lebih fungsional untuk monitoring 30 kamera  
> **Sesi:** #009 — 22 Juli 2026  
> **Status Batch:** ✅ Selesai

| ID | Issue | Status | Sesi | Tanggal | File yang Diubah |
|----|-------|--------|------|---------|------------------|
| C-05 | Fullscreen per kamera (double-click atau tombol ⛶) | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx`, `FullscreenPlayer.tsx` (baru), `CameraGrid.tsx`, `cameras.ts` (store) |
| C-06 | Pilihan layout grid (1×1, 2×2, 3×3, 4×4, 5×6) | ✅ | #009 | 22 Jul 2026 | `LiveView/index.tsx` (sudah ada tombolnya, diperbaiki UI) |
| C-07 | Filter/multi-select subset kamera yang ditampilkan | ✅ | #009 | 22 Jul 2026 | `LiveView/index.tsx`, `cameras.ts` (store: tambah selectAll/selectNone) |
| C-11 | Toggle Main/Sub stream per kamera | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx`, `cameras.ts` (store: streamTypeOverride), `api/cameras.ts` |
| C-13 | Picture-in-Picture via Browser PiP API | ✅ | #009 | 22 Jul 2026 | `VideoPlayer.tsx` |

### Catatan Teknis Batch 1

- **Fullscreen (C-05):** Overlay modal full-window. Double-click video atau klik tombol ⛶. Tutup dengan ESC atau tombol Tutup. Component baru: `FullscreenPlayer.tsx`
- **Layout grid (C-06):** Tombol 1×1/2×2/3×3/4×4/5×6 di toolbar. State di Zustand store.
- **Filter kamera (C-07):** Panel filter toggle, search by nama/lokasi, toggle per kamera, tombol Pilih Semua / Hapus Semua. Badge status online/offline per kamera di filter.
- **Toggle stream (C-11):** Tombol MAIN/SUB muncul saat hover di atas video. Default: SUB stream (hemat bandwidth). State per-kamera di Zustand, dikirim ke backend via query param `?stream=main` atau `?stream=sub`.
- **PiP (C-13):** Browser PiP API (`requestPictureInPicture()`). Tombol ⧉ muncul saat hover, hanya jika browser support. ESC dari PiP otomatis oleh browser.
- **useHLSPlayer:** Signature diubah — sekarang menerima `RefObject<HTMLVideoElement>` dari luar (bukan buat ref sendiri), agar VideoPlayer bisa akses `videoRef.current` untuk PiP API.

### ⚠️ Perlu Diverifikasi di Backend

Toggle stream (C-11) mengirim param `?stream=main` atau `?stream=sub` ke endpoint `GET /stream/{id}/live`.  
Perlu pastikan backend router `backend/api/routers/stream.py` membaca query param ini dan mengembalikan HLS URL yang sesuai (main stream vs sub stream).

---

## 🎯 Batch 2 — Download Rekaman

> **Target:** User bisa download file rekaman dari halaman Playback  
> **Status Batch:** ⏳ Belum mulai

| ID | Issue | Status | Sesi | Tanggal | File yang Diubah |
|----|-------|--------|------|---------|------------------|
| D-09 | Download rekaman ke lokal (endpoint + tombol di UI) | ⏳ | — | — | `backend/api/routers/recordings.py`, `frontend/src/pages/Playback/` |

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

### Storage (sisa setelah Batch 3)
| ID | Issue | Status |
|----|-------|--------|
| (sudah dicover di Batch 3) | — | — |

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

## Bug Tracker

Semua bug dari Sesi #001–#007 sudah difix. Lihat `PROGRESS.md` untuk detail lengkap.

| ID | Bug | Status |
|----|-----|--------|
| BUG-013 | Flutter analyze belum diverifikasi | ⏭️ nanti |
| BUG-019 | structlog dead code | ⏭️ skip |

---

## Ringkasan Progress

| Batch | Fitur | Status |
|-------|-------|--------|
| Batch 1 — Live View | 5 fitur (C-05, C-06, C-07, C-11, C-13) | ✅ Selesai |
| Batch 2 — Download Rekaman | 1 fitur (D-09) | ⏳ Belum |
| Batch 3 — Alert Disk | 3 fitur (F-08, F-09, F-10) | ⏳ Belum |
| Sisa backlog | ~41 fitur | ⏳ Belum dijadwalkan |
