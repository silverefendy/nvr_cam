# FEATURES — nvr_cam
## Laporan Fitur Lengkap Aplikasi NVR CCTV

**Dibuat:** 9 Juli 2026  
**Diperbarui:** 27 Juli 2026 (dipindah ke docs/ saat konsolidasi)

> Update file ini setiap fitur baru selesai: ubah status, isi kolom Sesi, tambah baris baru bila perlu.

---

## Legenda

| Simbol | Arti |
|--------|------|
| ✅ | Sudah diimplementasi dan berfungsi |
| 🟡 | Ada di kode tapi belum diverifikasi / sebagian |
| ⏳ | Belum diimplementasi (backlog) |
| 🎯 | Dirancang — desain sudah final |
| ⏭️ | Diputuskan skip / tidak akan dikerjakan |

---

## A. Autentikasi & User

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| A-01 | Login username + password, JWT access token | ✅ | #001 |
| A-02 | Refresh token otomatis | ✅ | #001 |
| A-03 | Logout (invalidate token) | ✅ | #001 |
| A-04 | Role-based access control (5 level) | ✅ | #001 |
| A-05 | CRUD user (admin only) | ✅ | #001 |
| A-06 | Ganti password sendiri + reset oleh admin | ✅ | #017 |
| A-07 | Two-Factor Authentication (2FA) | ⏳ | — |
| A-08 | Audit log aktivitas user | ✅ | #017 |
| A-09 | Session timeout (auto logout) | ⏳ | — |
| A-10 | Role matrix + permission dependencies | ✅ | #018 |

---

## B. Manajemen Kamera

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| B-01 | Tambah kamera baru (admin only) | ✅ | #001 |
| B-02 | Edit konfigurasi kamera | ✅ | #001 |
| B-03 | Hapus kamera (soft delete) | ✅ | #001 |
| B-04 | Daftar kamera + status online/offline | ✅ | #001 |
| B-05 | Test koneksi RTSP via ffprobe | ✅ | #001 |
| B-06 | Snapshot on-demand | ✅ | #001 |
| B-07 | Dual stream (main + sub) | ✅ | #018 |
| B-08 | Auto-build URL Dahua | ✅ | #001 |
| B-09 | Sort order kamera | ✅ | #001 |
| B-10 | Enable/disable motion per kamera | ✅ | #001 |
| B-11 | Retention days per kamera | ✅ | #001 |
| B-12 | Segmen durasi rekaman per kamera | ✅ | #001 |
| B-13 | Camera group / tag per area | ✅ | #018 |
| B-14 | PTZ control (ONVIF) | ⏳ | — |
| B-15 | Kamera non-Dahua RTSP (generic URL) | ✅ | #001 |
| B-16 | Kamera non-RTSP (MJPEG / HTTP) | 🎯 | — |

---

## C. Live Streaming

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| C-01 | Live view semua kamera (grid) — hingga 30 kamera | ✅ | #001 |
| C-02 | HLS (RTSP → FFmpeg → HLS → browser) | ✅ | #001 |
| C-03 | Badge status online/offline real-time via WebSocket | ✅ | #001 |
| C-04 | Snapshot thumbnail per kamera | ✅ | #001 |
| C-05 | Fullscreen per kamera | ✅ | #009 |
| C-06 | Pilihan layout grid (2x2, 3x3, 4x4, dll) | ✅ | #009 |
| C-07 | Multi-select / filter subset kamera | ✅ | #009 |
| C-08 | Drag-drop reorder posisi kamera | ✅ | #011 |
| C-09 | Digital zoom di live view | ⏳ | — |
| C-10 | Audio live | ⏳ | — |
| C-11 | Toggle Main / Sub Stream per kamera | ✅ | #009 |
| C-12 | FPS custom live view | 🎯 | — |
| C-13 | Picture-in-Picture (browser PiP API) | ✅ | #009 |
| C-14 | Floating Window Mode (drag, resize, minimize) | ✅ | #012 |
| C-15 | Sort tabel Cameras per kolom | ✅ | #016 |
| C-16 | Filter tabel Cameras (search + dropdown status) | ✅ | #016 |
| C-17 | Sort kamera di LiveView filter panel | ✅ | #016 |

---

## D. Rekaman

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| D-01 | Rekaman otomatis 24/7 (FFmpeg stream copy) | ✅ | #001 |
| D-02 | Segmentasi rekaman per durasi (default 1 jam) | ✅ | #001 |
| D-03 | Playback di browser (Range header, seek) | ✅ | #014 |
| D-04 | Filter rekaman by kamera + tanggal | ✅ | #001 |
| D-05 | Timeline per hari (hourly view) | ✅ | #001 |
| D-06 | Proteksi rekaman (lock dari auto-delete) | ✅ | #001 |
| D-07 | Hapus rekaman manual (admin only) | ✅ | #001 |
| D-08 | Auto-delete rekaman lama (circular) | ✅ | #001 |
| D-09 | Download rekaman ke lokal | ⏳ | — |
| D-10 | Motion event marker di timeline | ⏳ | — |
| D-11 | Kliping rekaman (potong segmen) | ⏳ | — |
| D-12 | Export ke format lain (MKV, AVI) | ⏳ | — |
| D-13 | Pencarian rekaman by tanggal range | ⏳ | — |

---

## E. Deteksi Gerakan

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| E-01 | Deteksi gerakan otomatis (OpenCV MOG2) | ✅ | #001 |
| E-02 | Event tersimpan di database | ✅ | #001 |
| E-03 | Filter events by kamera / tanggal / severity | ✅ | #001 |
| E-04 | Snapshot otomatis saat motion | ✅ | #001 |
| E-05 | Notifikasi Telegram saat motion | ✅ | #001 |
| E-06 | Notifikasi Email saat motion | ✅ | #001 |
| E-07 | Snapshot lightbox (klik → modal besar) | ⏳ | — |
| E-08 | Export laporan events (CSV/PDF) | ⏳ | — |
| E-09 | Motion masking area (zona ignore) | ⏳ | — |
| E-10 | Sensitivitas motion adjustable per kamera | ⏳ | — |
| E-11 | Cooldown notifikasi (anti-spam) | ⏳ | — |
| E-12 | Klip video pre/post event | ⏳ | — |
| E-13 | FPS adaptif saat motion | 🎯 | — |
| E-14 | Snapshot manual | ✅ | #018 |
| E-15 | Scheduled recording per kamera | ✅ | #018 |

---

## F. Storage Management

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| F-01 | Status semua drive (total/used/free) | ✅ | #001 |
| F-02 | Estimasi sisa hari storage | ✅ | #001 |
| F-03 | Mapping kamera per drive | ✅ | #001 |
| F-04 | Manual cleanup (hapus rekaman terlama) | ✅ | #001 |
| F-05 | Auto-cleanup saat disk > threshold | ✅ | #001 |
| F-06 | Multi-drive (hingga 8 HDD) | ✅ | #001 |
| F-07 | ZFS pool support | ✅ | #001 |
| F-08 | Statistik penggunaan per kamera | ⏳ | — |
| F-09 | Jadwal cleanup terjadwal | ⏳ | — |
| F-10 | Alert disk kritis via Telegram | ⏳ | — |

---

## G. Discovery Kamera (ONVIF)

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| G-01 | Scan jaringan cari kamera ONVIF (WS-Discovery) | ✅ | #001 |
| G-02 | Fallback port scanning | ✅ | #001 |
| G-03 | Info kamera: IP, port, maker, model, MAC | ✅ | #001 |
| G-04 | Auto-detect RTSP URL dari ONVIF | ✅ | #001 |
| G-05 | Test koneksi kamera yang ditemukan | ✅ | #001 |
| G-06 | Status discovery (berjalan / selesai) | ✅ | #001 |
| G-07 | Auto-add kamera dari hasil discovery | ⏳ | — |
| G-08 | Scan subnet spesifik | ✅ | #001 |

---

## H. Konfigurasi Sistem

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| H-01 | Konfigurasi umum sistem (general) via `system.yaml` | ✅ | #001 |
| H-02 | Konfigurasi storage (threshold, path) via `storage.yaml` | ✅ | #001 |
| H-03 | Konfigurasi notifikasi (Telegram, Email) via `.env` | ✅ | #001 |
| H-04 | Test notifikasi dari UI | ✅ | #001 |
| H-05 | Apply config live (tanpa restart full) | ✅ | #001 |
| H-06 | Backup config ke ZIP | ✅ | #001 |
| H-07 | Restore config dari ZIP | ✅ | #001 |
| H-08 | List backup tersimpan (5 terakhir) | ✅ | #001 |
| H-09 | Setting FPS adaptif motion | 🎯 | — |
| H-10 | Setting FPS custom live view | 🎯 | — |
| H-11 | WhatsApp / Signal notification | ⏳ | — |
| H-12 | Webhook notification (custom URL) | ⏳ | — |

---

## I. Monitoring Server

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| I-01 | CPU usage realtime (psutil) | ✅ | #001 |
| I-02 | RAM usage realtime | ✅ | #001 |
| I-03 | Disk usage per drive | ✅ | #001 |
| I-04 | Uptime server | ✅ | #001 |
| I-05 | Status 4 services | ✅ | #001 |
| I-06 | Jumlah kamera online/offline/total | ✅ | #001 |
| I-07 | WebSocket realtime update dashboard | ✅ | #001 |
| I-08 | Log viewer di UI | ⏳ | — |
| I-09 | Alert CPU/RAM tinggi via notifikasi | ⏳ | — |
| I-10 | Grafik historis (CPU/RAM/disk) | ⏳ | — |
| I-11 | Restart service dari UI | ⏳ | — |

---

## J. AV1 Encoder (Background)

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| J-01 | Re-encode H.265 → AV1 saat idle (libsvtav1) | ✅ | #001 |
| J-02 | Scheduler otomatis (malam hari) | ✅ | #001 |
| J-03 | Tidak ganggu rekaman aktif | ✅ | #001 |
| J-04 | Progress encode di UI | ⏳ | — |
| J-05 | Hardware acceleration (GPU/VA-API) | ⏳ | — |

---

## K. Mobile App (Flutter)

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| K-01 | Login ke backend (JWT) | ✅ | #001 |
| K-02 | Live view kamera (HLS player) | ✅ | #001 |
| K-03 | Playback rekaman | ✅ | #001 |
| K-04 | Daftar events / motion | ✅ | #001 |
| K-05 | Settings dasar | ✅ | #001 |
| K-06 | flutter analyze verified | ⏳ | — |
| K-07 | flutter build apk release | ⏳ | — |
| K-08 | Push notification (FCM) | ⏳ | — |
| K-09 | Fingerprint / biometric login | ⏳ | — |
| K-10 | Landscape mode / tablet layout | ⏳ | — |

---

## L. Deployment & Infrastruktur

| # | Fitur | Status | Sesi |
|---|-------|--------|------|
| L-01 | Native install script Ubuntu (`install.sh`) | ✅ | #007 |
| L-02 | 4 systemd services | ✅ | #007 |
| L-03 | Nginx reverse proxy config | ✅ | #007 |
| L-04 | Alembic database migration | ✅ | #006 |
| L-05 | Seed admin user (setup_db.py) | ✅ | #001 |
| L-06 | Docker Compose (dev) | ✅ | #005 |
| L-07 | HTTPS / SSL (Let's Encrypt) | ⏳ | — |
| L-08 | Health check endpoint publik | ⏳ | — |
| L-09 | Firewall setup (UFW) | ⏳ | — |

---

## Ringkasan Statistik

| Kategori | Total | ✅ Selesai | 🎯 Dirancang | ⏳ Backlog | ⏭️ Skip |
|----------|-------|-----------|-------------|-----------|--------|
| A. Auth & User | 10 | 7 | 0 | 3 | 0 |
| B. Kamera | 16 | 13 | 1 | 2 | 0 |
| C. Live Streaming | 17 | 13 | 2 | 2 | 0 |
| D. Rekaman | 13 | 8 | 0 | 5 | 0 |
| E. Motion Detection | 15 | 8 | 1 | 6 | 0 |
| F. Storage | 10 | 7 | 0 | 3 | 0 |
| G. Discovery ONVIF | 8 | 7 | 0 | 1 | 0 |
| H. Konfigurasi | 12 | 8 | 2 | 2 | 0 |
| I. Monitoring Server | 11 | 7 | 0 | 4 | 0 |
| J. AV1 Encoder | 5 | 3 | 0 | 2 | 0 |
| K. Mobile (Flutter) | 10 | 5 | 0 | 5 | 0 |
| L. Deployment | 9 | 7 | 0 | 2 | 0 |
| **TOTAL** | **136** | **93** | **6** | **37** | **0** |

**Progress: 93 selesai + 6 dirancang = 99/136 dalam pipeline (73%)**
