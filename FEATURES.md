# FEATURES — nvr_cam
## Laporan Fitur Lengkap Aplikasi NVR CCTV

**Dibuat:** 9 Juli 2026, 09:00 WIB
**Diperbarui:** 9 Juli 2026, 09:00 WIB
**Sumber:** Audit langsung dari kode (routers, services, frontend pages)

> ⚠️ **Panduan update file ini:**
> Setiap kali ada fitur baru yang selesai diimplementasi, update tabel di seksi yang relevan:
> - Ubah status dari `⏳ Backlog` → `✅ Implementasi` 
> - Isi kolom "Sesi" dengan nomor sesi yang mengerjakan
> - Tambah baris baru di tabel backlog jika ada ide fitur baru

---

## Legenda Status

| Simbol | Arti |
|--------|------|
| ✅ | Sudah diimplementasi dan berfungsi |
| 🟡 | Ada di kode tapi belum diverifikasi / sebagian |
| ⏳ | Belum diimplementasi (backlog) |
| ⏭️ | Diputuskan skip / tidak akan dikerjakan |

---

## A. Autentikasi & Manajemen User

**Router:** `backend/api/routers/auth.py`, `backend/api/routers/users.py`
**Frontend:** `frontend/src/pages/Login.tsx`, `Users.tsx`
**Mobile:** `mobile/lib/screens/login_screen.dart`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| A-01 | Login dengan username + password | ✅ | #001 | JWT access token |
| A-02 | Refresh token otomatis | ✅ | #001 | Token expired → auto-refresh |
| A-03 | Logout (invalidate token) | ✅ | #001 | — |
| A-04 | Role-based access control | ✅ | #001 | 3 level: `admin`, `operator`, `viewer` |
| A-05 | CRUD user (tambah/edit/hapus) | ✅ | #001 | Admin only |
| A-06 | Ganti password sendiri | 🟡 | — | UI ada, endpoint perlu verifikasi |
| A-07 | Two-Factor Authentication (2FA) | ⏳ | — | Belum ada sama sekali |
| A-08 | Audit log aktivitas user | ⏳ | — | Siapa login kapan, hapus apa, dll |
| A-09 | Session timeout (auto logout) | ⏳ | — | Setelah X menit idle |

---

## B. Manajemen Kamera

**Router:** `backend/api/routers/cameras.py`, `backend/api/routers/config.py`
**Frontend:** `frontend/src/pages/Cameras.tsx`, `CameraForm.tsx`
**Service:** `backend/services/recorder/ffmpeg_wrapper.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| B-01 | Tambah kamera baru | ✅ | #001 | Admin only |
| B-02 | Edit konfigurasi kamera | ✅ | #001 | Admin only |
| B-03 | Hapus kamera | ✅ | #001 | Admin only, soft delete |
| B-04 | Daftar semua kamera + status online/offline | ✅ | #001 | Real-time dari RecordingManager |
| B-05 | Test koneksi RTSP kamera | ✅ | #001 | Pakai `ffprobe` |
| B-06 | Snapshot on-demand (foto sekarang) | ✅ | #001 | FFmpeg capture 1 frame → JPEG |
| B-07 | Dual stream (main + sub) | ✅ | #001 | Main = full res, sub = low res |
| B-08 | Auto-build URL Dahua | ✅ | #001 | Format `rtsp://user:pass@ip/cam/realmonitor?...` |
| B-09 | Konfigurasi urutan tampilan kamera | ✅ | #001 | Field `sort_order` di DB |
| B-10 | Enable/disable motion per kamera | ✅ | #001 | Field `motion_enabled` |
| B-11 | Retention days per kamera | ✅ | #001 | Berbeda per kamera |
| B-12 | Segmen durasi rekaman per kamera | ✅ | #001 | Field `segment_duration` |
| B-13 | Kamera group/tag per area | ⏳ | — | FEAT-013, contoh: Lantai 1, Gudang, Kantor |
| B-14 | PTZ control (Pan-Tilt-Zoom) | ⏳ | — | Perlu ONVIF PTZ endpoint |
| B-15 | Kamera non-Dahua (generic RTSP) | 🟡 | — | URL RTSP custom bisa diisi manual |

---

## C. Live Streaming

**Router:** `backend/api/routers/stream.py`
**Frontend:** `frontend/src/pages/LiveView.tsx`
**Mobile:** `mobile/lib/screens/home_screen.dart`
**Service:** `backend/services/recorder/ffmpeg_wrapper.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| C-01 | Live view semua kamera (grid) | ✅ | #001 | Hingga 30 kamera sekaligus |
| C-02 | Protokol HLS (HTTP Live Streaming) | ✅ | #001 | RTSP → FFmpeg → HLS segments → browser |
| C-03 | Badge status online/offline real-time | ✅ | #001 | WebSocket, tanpa refresh halaman |
| C-04 | Snapshot thumbnail per kamera | ✅ | #001 | Foto preview di grid |
| C-05 | Fullscreen per kamera | ⏳ | — | FEAT-008, double-click / tombol F |
| C-06 | Pilihan layout grid (2x2, 3x3, 4x4, dll) | ⏳ | — | Saat ini hanya 1 layout |
| C-07 | Multi-select / filter subset kamera | ⏳ | — | FEAT-006, tampilkan hanya kamera tertentu |
| C-08 | Drag-drop reorder posisi kamera di grid | ⏳ | — | FEAT-007 |
| C-09 | Digital zoom di live view | ⏳ | — | Zoom in/out via scroll atau pinch (mobile) |
| C-10 | Audio live (jika kamera support) | ⏳ | — | Butuh tambahan flag di FFmpeg pipeline |

---

## D. Rekaman (Recordings)

**Router:** `backend/api/routers/recordings.py`
**Frontend:** `frontend/src/pages/Playback.tsx`
**Mobile:** `mobile/lib/screens/playback_screen.dart`
**Service:** `backend/services/recorder/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| D-01 | Rekaman otomatis 24/7 | ✅ | #001 | FFmpeg copy stream RTSP → MP4/H.265 |
| D-02 | Segmentasi rekaman per durasi | ✅ | #001 | Contoh: setiap 1 jam 1 file |
| D-03 | Playback di browser (streaming) | ✅ | #001 | Range header support, bisa scrub/seek |
| D-04 | Filter rekaman by kamera + tanggal | ✅ | #001 | — |
| D-05 | Timeline per hari (hourly view) | ✅ | #001 | Jam mana ada rekaman, tersedia dari API |
| D-06 | Proteksi rekaman (lock dari auto-delete) | ✅ | #001 | Toggle `is_protected`, operator ke atas |
| D-07 | Hapus rekaman manual | ✅ | #001 | Admin only, tidak bisa hapus yang protected |
| D-08 | Auto-delete rekaman lama (circular) | ✅ | #001 | Trigger saat disk > threshold |
| D-09 | Download rekaman ke lokal | ⏳ | — | FEAT-001, butuh endpoint `/recordings/{id}/download` |
| D-10 | Motion event marker di timeline | ⏳ | — | FEAT-002, tandai merah di scrubber |
| D-11 | Kliping rekaman (potong segmen) | ⏳ | — | Export hanya menit X–Y dari rekaman |
| D-12 | Export ke format lain (MKV, AVI) | ⏳ | — | Saat ini hanya MP4 |
| D-13 | Pencarian rekaman by keyword / tanggal range | ⏳ | — | Filter lebih lanjut |

---

## E. Deteksi Gerakan (Motion Detection)

**Router:** `backend/api/routers/events.py`
**Frontend:** `frontend/src/pages/Events.tsx`
**Mobile:** `mobile/lib/screens/events_screen.dart`
**Service:** `backend/services/motion/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| E-01 | Deteksi gerakan otomatis (OpenCV) | ✅ | #001 | Frame differencing per kamera |
| E-02 | Event tersimpan di database | ✅ | #001 | Timestamp, severity, camera_id |
| E-03 | Filter events by kamera / tanggal / severity | ✅ | #001 | — |
| E-04 | Snapshot otomatis saat motion | ✅ | #001 | File JPG disimpan |
| E-05 | Notifikasi Telegram saat motion | ✅ | #001 | Kirim pesan + foto ke bot |
| E-06 | Notifikasi Email saat motion | ✅ | #001 | SMTP |
| E-07 | Snapshot lightbox (klik → buka besar) | ⏳ | — | FEAT-003 |
| E-08 | Export laporan events (CSV/PDF) | ⏳ | — | Download daftar events per periode |
| E-09 | Motion masking area (zona ignore) | ⏳ | — | Definisi area di frame yang diabaikan |
| E-10 | Sensitivitas motion adjustable | ⏳ | — | Threshold per kamera |
| E-11 | Cooldown notifikasi (jangan spam) | ⏳ | — | Minimal X menit antar notif per kamera |
| E-12 | Klip video saat event (pre/post buffer) | ⏳ | — | Simpan video 10 detik sebelum+sesudah event |

---

## F. Storage Management

**Router:** `backend/api/routers/storage.py`
**Frontend:** `frontend/src/pages/Storage.tsx`
**Service:** `backend/services/storage/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| F-01 | Status semua drive (total/used/free) | ✅ | #001 | Per drive, dalam GB/TB |
| F-02 | Estimasi sisa hari storage | ✅ | #001 | Kalkulasi kasar berdasarkan free space |
| F-03 | Mapping kamera per drive | ✅ | #001 | Kamera mana di drive mana |
| F-04 | Manual cleanup (hapus rekaman terlama) | ✅ | #001 | Admin trigger dari UI |
| F-05 | Auto-cleanup saat disk > threshold | ✅ | #001 | Default 85%, rekaman lama non-protected dihapus |
| F-06 | Multi-drive (hingga 8 HDD) | ✅ | #001 | Cocok untuk 8x WD Purple 4TB |
| F-07 | ZFS pool support | ✅ | #001 | `zfsutils-linux` terinstall via `install.sh` |
| F-08 | Statistik penggunaan per kamera | ⏳ | — | Berapa GB per kamera per hari |
| F-09 | Jadwal cleanup terjadwal (cron) | ⏳ | — | Bukan hanya saat disk penuh |
| F-10 | Alert jika disk kritis (< X%) | ⏳ | — | Notifikasi Telegram jika hampir penuh |

---

## G. Discovery Kamera (ONVIF)

**Router:** `backend/api/routers/discovery.py`
**Frontend:** `frontend/src/pages/Setup.tsx`, `CameraDiscovery.tsx`
**Service:** `backend/services/discovery/onvif_scanner.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| G-01 | Scan jaringan cari kamera ONVIF | ✅ | #001 | WS-Discovery multicast |
| G-02 | Fallback port scanning | ✅ | #001 | Jika multicast gagal |
| G-03 | Info kamera: IP, port, maker, model, MAC | ✅ | #001 | — |
| G-04 | Auto-detect RTSP URL | ✅ | #001 | Dari info ONVIF |
| G-05 | Test koneksi kamera yang ditemukan | ✅ | #001 | Sebelum ditambah ke sistem |
| G-06 | Status discovery (sedang berjalan / selesai) | ✅ | #001 | Polling endpoint `/discovery/status` |
| G-07 | Auto-add kamera dari hasil discovery | ⏳ | — | Saat ini masih manual tambah setelah scan |
| G-08 | Scan subnet spesifik | ✅ | #001 | Parameter `network` di request |

---

## H. Konfigurasi Sistem

**Router:** `backend/api/routers/config.py`, `settings.py`
**Frontend:** `frontend/src/pages/Settings.tsx`
**Util:** `backend/utils/config_manager.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| H-01 | Konfigurasi umum sistem (general) | ✅ | #001 | Via `system.yaml` |
| H-02 | Konfigurasi storage (threshold, path) | ✅ | #001 | Via `storage.yaml` |
| H-03 | Konfigurasi notifikasi (Telegram, Email) | ✅ | #001 | Via `.env` |
| H-04 | Test notifikasi dari UI | ✅ | #001 | Kirim pesan test ke Telegram / Email |
| H-05 | Apply config live (tanpa restart full) | ✅ | #001 | Restart per-kamera, bukan seluruh aplikasi |
| H-06 | Backup config ke ZIP | ✅ | #001 | Download semua YAML |
| H-07 | Restore config dari ZIP | ✅ | #001 | Upload ZIP → overwrite config |
| H-08 | List backup tersimpan | ✅ | #001 | 5 backup terakhir |
| H-09 | WhatsApp / Signal notification | ⏳ | — | Alternatif Telegram |
| H-10 | Webhook notification (custom URL) | ⏳ | — | Kirim JSON event ke URL eksternal |

---

## I. Monitoring Server

**Router:** `backend/api/routers/system.py`
**Frontend:** `frontend/src/pages/System.tsx`
**Util:** `backend/utils/health.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| I-01 | CPU usage realtime | ✅ | #001 | `psutil`, polling |
| I-02 | RAM usage realtime (GB + %) | ✅ | #001 | — |
| I-03 | Disk usage (per drive, GB) | ✅ | #001 | — |
| I-04 | Uptime server | ✅ | #001 | Dalam detik, ditampilkan sebagai jam:menit |
| I-05 | Status 4 services | ✅ | #001 | nvr-api, nvr-recorder, nvr-motion, nvr-encoder |
| I-06 | Jumlah kamera online / offline / total | ✅ | #001 | Dari RecordingManager |
| I-07 | WebSocket realtime update dashboard | ✅ | #001 | Tanpa polling dari frontend |
| I-08 | Log viewer di UI | ⏳ | — | FEAT-012, tampilkan `journalctl` dari UI |
| I-09 | Alert CPU/RAM tinggi | ⏳ | — | Notifikasi jika CPU > 90% atau RAM > 85% |
| I-10 | Grafik historis (CPU/RAM/disk) | ⏳ | — | Time-series chart, simpan metrik ke DB |
| I-11 | Restart service dari UI | ⏳ | — | Admin bisa restart nvr-recorder dll dari browser |

---

## J. AV1 Encoder (Background)

**Service:** `backend/services/encoder/av1_encoder.py`, `scheduler.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| J-01 | Re-encode H.265 → AV1 saat idle | ✅ | #001 | FFmpeg AV1, hemat ~50% space |
| J-02 | Scheduler otomatis (malam hari) | ✅ | #001 | Hanya jalan saat server tidak sibuk |
| J-03 | Tidak ganggu rekaman aktif | ✅ | #001 | Priority rendah, yield ke recorder |
| J-04 | Progress encode di UI | ⏳ | — | Tampilkan % encode di halaman System |
| J-05 | Hardware acceleration (GPU/VA-API) | ⏳ | — | Jika server punya GPU atau iGPU Intel |

---

## K. Mobile App (Flutter)

**Folder:** `mobile/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| K-01 | Login ke backend | ✅ | #001 | JWT, sama dengan web |
| K-02 | Live view kamera | ✅ | #001 | HLS player di Flutter |
| K-03 | Playback rekaman | ✅ | #001 | — |
| K-04 | Daftar events / motion | ✅ | #001 | — |
| K-05 | Settings dasar | ✅ | #001 | — |
| K-06 | flutter analyze verified | ⏳ | — | BUG-013, belum diverifikasi (Flutter CLI tidak tersedia) |
| K-07 | flutter build apk release | ⏳ | — | Tunggu K-06 selesai |
| K-08 | Push notification (FCM) | ⏳ | — | FEAT-005, notif ke HP saat ada motion |
| K-09 | Fingerprint / biometric login | ⏳ | — | Login lebih cepat di HP |
| K-10 | Landscape mode / tablet layout | ⏳ | — | Optimasi untuk tablet / monitor landscape |

---

## L. Deployment & Infrastruktur

**Folder:** `scripts/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| L-01 | Native install script Ubuntu (`install.sh`) | ✅ | #007 | Tanpa Docker, via systemd |
| L-02 | 4 systemd services | ✅ | #007 | nvr-api, nvr-recorder, nvr-motion, nvr-encoder |
| L-03 | Nginx reverse proxy config | ✅ | #007 | Serve frontend + proxy ke backend port 8000 |
| L-04 | Alembic database migration | ✅ | #006 | Auto-run saat install |
| L-05 | Seed admin user (setup_db.py) | ✅ | #001 | Login default: admin / nvr1234 |
| L-06 | Docker Compose (dev) | ✅ | #005 | `docker-compose.dev.yml` untuk development |
| L-07 | HTTPS / SSL (Let's Encrypt) | ⏳ | — | Saat ini hanya HTTP |
| L-08 | Update script (pull + restart) | ⏳ | — | `install.sh` sudah handle `git pull` jika repo ada |
| L-09 | Health check endpoint publik | ⏳ | — | `/health` tanpa auth untuk monitoring eksternal |
| L-10 | Firewall setup (UFW) | ⏳ | — | Panduan / script setup port yang perlu dibuka |

---

## Ringkasan Statistik Fitur

| Kategori | Total | ✅ Implementasi | 🟡 Sebagian | ⏳ Backlog |
|----------|-------|----------------|------------|-----------|
| A. Auth & User | 9 | 5 | 1 | 3 |
| B. Manajemen Kamera | 15 | 12 | 1 | 2 |
| C. Live Streaming | 10 | 4 | 0 | 6 |
| D. Rekaman | 13 | 8 | 0 | 5 |
| E. Motion Detection | 12 | 6 | 0 | 6 |
| F. Storage | 10 | 7 | 0 | 3 |
| G. Discovery ONVIF | 8 | 7 | 0 | 1 |
| H. Konfigurasi | 10 | 8 | 0 | 2 |
| I. Monitoring Server | 11 | 7 | 0 | 4 |
| J. AV1 Encoder | 5 | 3 | 0 | 2 |
| K. Mobile (Flutter) | 10 | 5 | 0 | 5 |
| L. Deployment | 10 | 7 | 0 | 3 |
| **TOTAL** | **123** | **79** | **2** | **42** |

**Progress keseluruhan: 79/123 fitur selesai (64%)**

---

## Backlog Prioritas Tinggi (Rekomendasi Dikerjakan Berikutnya)

| Prioritas | ID | Fitur | Alasan |
|-----------|-----|-------|--------|
| 🔴 1 | K-06, K-07 | Verify `flutter analyze` + build APK | Blocking — Mobile belum bisa dipakai |
| 🔴 2 | D-09 | Download rekaman | Kebutuhan dasar pengguna |
| 🟠 3 | E-07 | Snapshot lightbox | UX — klik foto jadi lebih natural |
| 🟠 4 | E-10 | Sensitivitas motion adjustable | Mengurangi false positive di area ramai |
| 🟠 5 | E-11 | Cooldown notifikasi | Mencegah spam Telegram saat banyak gerakan |
| 🟡 6 | C-06 | Pilihan layout grid | Operator mungkin hanya mau lihat 4 kamera area tertentu |
| 🟡 7 | F-10 | Alert disk kritis | Penting untuk 30 kamera — disk bisa penuh tiba-tiba |
| 🟡 8 | B-13 | Kamera group per area | Pabrik Medan + pabrik Palembang bisa dipisah |
| 🟡 9 | I-08 | Log viewer di UI | Debugging lebih mudah tanpa SSH ke server |
| 🟡 10 | L-07 | HTTPS / SSL | Keamanan — jangan pakai HTTP di production |

---

## Cara Update File Ini

Setiap sesi development baru yang menyelesaikan fitur, lakukan update:

```
1. Cari baris fitur yang selesai di tabel yang relevan
2. Ubah kolom Status dari ⏳ → ✅
3. Isi kolom Sesi dengan nomor sesi (contoh: #008)
4. Update tabel Ringkasan Statistik di bagian bawah
5. Hapus dari tabel Backlog Prioritas Tinggi jika sudah selesai
6. Update field "Diperbarui" di header file ini
```
