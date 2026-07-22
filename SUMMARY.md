# SUMMARY — nvr_cam
## Ringkasan Proyek NVR CCTV Custom

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 22 Juli 2026 (Sesi #009)  
**Sumber:** Audit kode + dokumen repo (README, FEATURES, PROGRESS, HANDOFF, docker-compose, Dockerfile)

---

## Apa Ini?

**nvr_cam** adalah sistem NVR (Network Video Recorder) CCTV custom yang dibangun dari nol untuk kebutuhan factory/pabrik. Dirancang untuk mengelola hingga 30 kamera IP Dahua berbasis RTSP, tanpa biaya lisensi channel seperti NVR komersial.

---

## Deployment — Cara Aplikasi Dijalankan

Aplikasi ini menggunakan **native install langsung ke Ubuntu Server** — **bukan Docker** untuk production.

| Mode | Keterangan |
|------|------------|
| **Production** | Native Ubuntu Server 24.04 via `scripts/install.sh` + 4 systemd services + Nginx |
| **Development** | Docker Compose (`docker-compose.dev.yml`) untuk testing lokal |

Script `install.sh` otomatis menginstall semua dependensi (`ffmpeg`, `postgresql`, `nginx`, `nodejs`, Python virtualenv), menjalankan migrasi database, build frontend, dan mendaftarkan semua services ke systemd.

### 4 Services Systemd (Production)

| Service | Fungsi |
|---------|--------|
| `nvr-api` | FastAPI backend (port 8000, di-proxy Nginx) |
| `nvr-recorder` | Engine rekaman FFmpeg per kamera |
| `nvr-motion` | Deteksi gerakan OpenCV |
| `nvr-encoder` | Re-encoder AV1 background saat idle malam |

---

## Tech Stack

| Layer | Teknologi |
|-------|-----------|
| OS | Ubuntu Server 24.04 LTS |
| Filesystem | ZFS (LZ4 compression + dedup) |
| Video engine | FFmpeg (recording + HLS streaming) |
| Motion detect | OpenCV (background subtractor MOG2) |
| Backend | Python 3.12 + FastAPI + SQLAlchemy (async) |
| Database | PostgreSQL 16 + Alembic migrations |
| Frontend | React 18 + TypeScript + Tailwind CSS + Vite |
| Mobile | Flutter 3 (Android APK — screens done, build pending) |
| Notifikasi | Telegram Bot API + Email SMTP |
| Remote access | ZeroTier (kantor ↔ rumah) |
| Process manager | systemd |
| Web server | Nginx (reverse proxy) |

---

## Fitur Utama yang Sudah Ada (✅ Selesai)

### Kamera & Streaming
- Live view semua kamera dalam grid (hingga 30 kamera) via HLS
- **Fullscreen per kamera** — double-click video atau tombol ⛶, tutup dengan ESC *(baru: Sesi #009)*
- **Layout grid pilihan** — 1×1, 2×2, 3×3, 4×4, 5×6 *(baru: Sesi #009)*
- **Filter/select kamera** — pilih kamera mana yang ditampilkan, search by nama/lokasi *(baru: Sesi #009)*
- **Toggle Main/Sub stream** per kamera saat hover — default sub stream hemat bandwidth *(baru: Sesi #009)*
- **Picture-in-Picture** via Browser PiP API — tombol ⧉ saat hover *(baru: Sesi #009)*
- Manajemen kamera: tambah, edit, hapus, test koneksi RTSP
- Discovery kamera otomatis via ONVIF WS-Discovery
- Status online/offline real-time via WebSocket
- Dual stream support (main + sub stream Dahua)
- Snapshot on-demand per kamera

### Rekaman
- Rekaman otomatis 24/7 (H.265 stream copy, tanpa re-encode)
- Segmentasi per durasi (default 1 jam per file)
- Playback di browser dengan scrub/seek (HTTP Range support)
- Filter rekaman berdasarkan kamera + tanggal + timeline jam
- Auto-delete rekaman lama saat disk > threshold (circular buffer)
- Proteksi rekaman penting dari auto-delete

### Deteksi Gerakan
- Deteksi motion otomatis per kamera via OpenCV
- Notifikasi Telegram (teks + foto) dan Email SMTP saat ada gerakan
- Riwayat events tersimpan di database
- Snapshot otomatis saat motion terdeteksi

### Storage
- Multi-drive support (hingga 8 HDD, cocok untuk WD Purple 4TB)
- ZFS pool support
- Dashboard status drive (total/used/free + estimasi hari)
- Mapping kamera per drive
- Auto-cleanup dan manual cleanup dari UI

### Monitoring Server
- Dashboard CPU, RAM, disk usage real-time via WebSocket
- Uptime server
- Status 4 services (api, recorder, motion, encoder)
- Jumlah kamera online/offline/total

### Autentikasi & User
- Login JWT (access + refresh token)
- 5 role: `super_admin`, `admin`, `operator`, `viewer`, `security`
- CRUD user

### Konfigurasi
- Edit konfigurasi sistem dari UI (storage threshold, notifikasi, dll)
- Backup + restore config ke file ZIP
- Apply config live tanpa restart penuh

### Background Encoding
- Re-encode rekaman lama H.265 → AV1 secara otomatis saat server idle malam hari (hemat ~50% storage)

---

## Fitur yang Sedang Dirancang / Backlog Prioritas

| Batch | Fitur | Status |
|-------|-------|--------|
| Batch 2 | Download rekaman ke lokal (D-09) | ⏳ |
| Batch 3 | Alert disk kritis via Telegram (F-10) | ⏳ |
| Batch 3 | Jadwal cleanup terjadwal dari UI (F-09) | ⏳ |
| Batch 3 | Statistik storage per kamera (F-08) | ⏳ |

Lihat **ISSUES.md** untuk daftar lengkap semua issue dan statusnya.

---

## Progress Keseluruhan

| Kategori | Selesai | Total |
|----------|---------|-------|
| Auth & User | 5 | 10 |
| Manajemen Kamera | 13 | 16 |
| Live Streaming | **9** | 13 |
| Rekaman | 8 | 13 |
| Motion Detection | 6 | 13 |
| Storage | 7 | 10 |
| Discovery ONVIF | 7 | 8 |
| Konfigurasi Sistem | 8 | 12 |
| Monitoring Server | 7 | 11 |
| AV1 Encoder | 3 | 5 |
| Mobile Flutter | 5 | 10 |
| Deployment | 7 | 9 |
| **TOTAL** | **85** | **130** |

**Progress: 85/130 fitur selesai (65%) — naik dari 80 setelah Batch 1 Live View**

---

## Infrastruktur Target

| Item | Spesifikasi |
|------|-------------|
| Server | Ubuntu Server 24.04, Intel i5 |
| Storage | 8x HDD WD Purple 4TB, ZFS pool |
| Kamera | 30x Dahua H.265 (RTSP) |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Login default | `admin / nvr1234` |
| Install dir | `/opt/nvr_cam` |

---

## Dokumen Terkait

| File | Isi |
|------|-----|
| `README.md` | Quick start, struktur proyek, setup dev |
| `FEATURES.md` | Daftar lengkap semua fitur + backlog + keputusan desain |
| `PROGRESS.md` | Timeline sesi development + daftar bug |
| `HANDOFF.md` | Panduan melanjutkan development di sesi AI baru |
| `ISSUES.md` | Issue tracker aktif — status selesai/belum per fitur |
| `AUDIT_REPORT.md` | Laporan audit teknis lengkap |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis sistem |
