# SUMMARY — nvr_cam
## Ringkasan Proyek NVR CCTV Custom

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 22 Juli 2026 (Sesi #009 — lanjutan)  
**Sumber:** Audit kode + dokumen repo

---

## Apa Ini?

**nvr_cam** adalah sistem NVR (Network Video Recorder) CCTV custom yang dibangun dari nol untuk kebutuhan factory/pabrik. Dirancang untuk mengelola hingga 30 kamera IP Dahua berbasis RTSP, tanpa biaya lisensi channel seperti NVR komersial.

---

## Deployment — Cara Aplikasi Dijalankan

| Mode | Keterangan |
|------|------------|
| **Production** | Native Ubuntu Server 24.04 via `scripts/install.sh` + 4 systemd services + Nginx |
| **Development** | Docker Compose (`docker-compose.yml`) untuk testing lokal |

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
| Mobile | Flutter 3 (Android APK — screens done, build nanti) |
| Notifikasi | Telegram Bot API + Email SMTP |
| Remote access | ZeroTier (kantor ↔ rumah) |
| Process manager | systemd |
| Web server | Nginx (reverse proxy) |

---

## Fitur yang Sudah Ada (✅ Selesai)

### Kamera & Live View
- Live view grid hingga 30 kamera via HLS
- **Fullscreen per kamera** — double-click atau tombol ⛶, tutup ESC *(Sesi #009)*
- **Layout grid pilihan** — 1×1, 2×2, 3×3, 4×4, 5×6 *(Sesi #009)*
- **Filter/select kamera** — pilih subset, search by nama/lokasi *(Sesi #009)*
- **Toggle Main/Sub stream** per kamera saat hover *(Sesi #009)*
- **Picture-in-Picture** via Browser PiP API *(Sesi #009)*
- Manajemen kamera: tambah, edit, hapus, test koneksi RTSP
- Discovery kamera otomatis via ONVIF WS-Discovery
- Status online/offline real-time via WebSocket
- Snapshot on-demand per kamera

### Rekaman
- Rekaman otomatis 24/7 (H.265 stream copy, tanpa re-encode)
- Segmentasi per jam (1 file = 1 jam)
- Playback di browser dengan scrub/seek
- **Download rekaman ke lokal** *(Sesi #009 — D-09)*
- Filter rekaman by kamera + tanggal + timeline jam
- Auto-delete circular saat disk > threshold
- Proteksi rekaman dari auto-delete

### Deteksi Gerakan
- OpenCV MOG2 background subtractor
- Notifikasi Telegram (teks + foto) dan Email SMTP
- Riwayat events di database + snapshot otomatis

### Storage
- Multi-drive support (hingga 8 HDD) + ZFS
- Dashboard status drive + estimasi hari
- Mapping kamera per drive
- Auto-cleanup + manual cleanup dari UI

### Monitoring & Konfigurasi
- CPU/RAM/disk real-time via WebSocket
- Status 4 services
- Edit config dari UI + backup/restore ZIP
- Re-encode AV1 background (hemat ~50% storage)

### Auth & User
- Login JWT, 5 role RBAC, CRUD user

---

## Fitur Prioritas Berikutnya

| Batch | Fitur | Status |
|-------|-------|--------|
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
| Live Streaming | 9 | 13 |
| Rekaman | **9** | 13 |
| Motion Detection | 6 | 13 |
| Storage | 7 | 10 |
| Discovery ONVIF | 7 | 8 |
| Konfigurasi Sistem | 8 | 12 |
| Monitoring Server | 7 | 11 |
| AV1 Encoder | 3 | 5 |
| Mobile Flutter | 5 | 10 |
| Deployment | 7 | 9 |
| **TOTAL** | **86** | **130** |

**Progress: 86/130 fitur selesai (66%) — naik dari 85 setelah D-09 Download Rekaman**

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
| `FEATURES.md` | Daftar lengkap semua fitur |
| `PROGRESS.md` | Timeline sesi + bug tracker historis |
| `HANDOFF.md` | Panduan handoff ke AI baru |
| `ISSUES.md` | Issue tracker aktif — status per fitur |
| `AUDIT_REPORT.md` | Laporan audit teknis lengkap |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis sistem |
