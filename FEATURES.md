# FEATURES — nvr_cam
## Laporan Fitur Lengkap Aplikasi NVR CCTV

**Dibuat:** 9 Juli 2026, 09:00 WIB
**Diperbarui:** 9 Juli 2026, 10:30 WIB
**Sumber:** Audit langsung dari kode (routers, services, frontend pages) + keputusan desain Sesi #008

> ⚠️ **Panduan update file ini:**
> Setiap kali ada fitur baru yang selesai diimplementasi, update tabel di seksi yang relevan:
> - Ubah status dari `⏳ Backlog` → `✅ Implementasi`
> - Isi kolom "Sesi" dengan nomor sesi yang mengerjakan
> - Tambah baris baru di tabel backlog jika ada ide fitur baru
> - Update tabel Ringkasan Statistik dan field "Diperbarui" di atas

---

## Legenda Status

| Simbol | Arti |
|--------|------|
| ✅ | Sudah diimplementasi dan berfungsi |
| 🟡 | Ada di kode tapi belum diverifikasi / sebagian |
| ⏳ | Belum diimplementasi (backlog) |
| 🎯 | Diputuskan untuk dikerjakan — desain sudah final |
| ⏭️ | Diputuskan skip / tidak akan dikerjakan |

---

## Keputusan Desain (Sesi #008)

Rangkuman keputusan dari diskusi yang sudah disepakati, sebagai referensi implementasi:

### Role & Akses
- Role kustom **ditunda** — 5 role yang ada (`super_admin`, `admin`, `operator`, `viewer`, `security`) sudah cukup untuk sekarang
- Kamera non-Dahua dengan RTSP: **sudah aman**, isi URL manual di form
- Kamera non-RTSP (MJPEG, HTTP): perlu diperbaiki nanti — tambah `stream_type` field

### FPS Adaptif Motion
- **Diputuskan: bisa di-setting ON/OFF dari menu Settings**
- Saat ON: saat ada motion, `ffmpeg_wrapper.py` spawn proses rekaman baru dengan FPS lebih tinggi
- **Peringatan wajib ditampilkan di UI** saat toggle ON: "Fitur ini meningkatkan beban CPU dan potensi overheat. Pastikan pendinginan server memadai."
- Rekaman normal (idle) tetap di FPS rendah (default 15fps), saat motion spawn file baru di FPS tinggi (default 25fps)
- **Konsekuensi storage dipahami**: ada 2 file terpisah (normal + motion clip), menggunakan storage lebih banyak
- Setting FPS idle dan FPS motion bisa dikonfigurasi per sistem (bukan per kamera) dari Settings

### Live View Stream & FPS
- **Toggle Main/Sub Stream**: tambahkan di UI LiveView, pilih per-kamera atau global
- **FPS Custom Live View**: bisa di-setting, tapi:
  - Wajib tampilkan warning CPU overhead karena butuh re-encode
  - Bisa pilih kamera mana saja yang naik FPS-nya (tidak harus semua 30 kamera)
  - Default: stream copy (ikut FPS kamera), user bisa override per kamera
- Sub stream default untuk live view direkomendasikan (hemat bandwidth & CPU)

### Picture-in-Picture
- **Implementasi: Browser PiP API** (seperti YouTube) — bukan floating window buatan sendiri
- PiP bisa dipanggil dari 1 kamera yang sedang difullscreen/fokus
- Multi-kamera PiP tidak diimplementasikan (browser API hanya support 1 video PiP sekaligus)
- Jika user ingin pantau lebih dari 1 kamera sambil kerja lain: gunakan tab browser terpisah atau buka halaman LiveView di window kecil

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
| A-04 | Role-based access control | ✅ | #001 | 5 level: `super_admin`, `admin`, `operator`, `viewer`, `security` |
| A-05 | CRUD user (tambah/edit/hapus) | ✅ | #001 | Admin only |
| A-06 | Ganti password sendiri | 🟡 | — | UI ada, endpoint perlu verifikasi |
| A-07 | Two-Factor Authentication (2FA) | ⏳ | — | Belum ada sama sekali |
| A-08 | Audit log aktivitas user | ⏳ | — | Siapa login kapan, hapus apa, dll |
| A-09 | Session timeout (auto logout) | ⏳ | — | Setelah X menit idle |
| A-10 | Role kustom per fitur (granular) | ⏭️ | — | Ditunda — 5 role hierarkis sudah cukup untuk sekarang |

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
| B-13 | Kamera group / tag per area | ⏳ | — | Contoh: Lantai 1, Gudang, Kantor, Pabrik Medan |
| B-14 | PTZ control (Pan-Tilt-Zoom) | ⏳ | — | Perlu ONVIF PTZ endpoint |
| B-15 | Kamera non-Dahua RTSP (generic) | ✅ | #001 | URL RTSP custom diisi manual — sudah bisa |
| B-16 | Kamera non-RTSP (MJPEG / HTTP stream) | 🎯 | — | Perlu tambah field `stream_type` di model + logic di `ffmpeg_wrapper.py`. Format: `http://ip/video.mjpg` |

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
| C-05 | Fullscreen per kamera | ⏳ | — | Double-click / tombol F |
| C-06 | Pilihan layout grid (2x2, 3x3, 4x4, dll) | ⏳ | — | Saat ini hanya 1 layout |
| C-07 | Multi-select / filter subset kamera | ⏳ | — | Tampilkan hanya kamera tertentu |
| C-08 | Drag-drop reorder posisi kamera di grid | ⏳ | — | — |
| C-09 | Digital zoom di live view | ⏳ | — | Zoom in/out via scroll atau pinch (mobile) |
| C-10 | Audio live (jika kamera support) | ⏳ | — | Butuh tambahan flag di FFmpeg pipeline |
| C-11 | Toggle Main / Sub Stream per kamera | 🎯 | — | **Desain:** Tombol di kartu kamera di LiveView. Main = kualitas tinggi, Sub = hemat bandwidth. Default: Sub stream. Pilihan disimpan per-user di localStorage |
| C-12 | FPS custom live view (override) | 🎯 | — | **Desain:** Setting di halaman Settings → Live View. Pilih kamera mana yang di-override FPS-nya (tidak harus semua). Warning wajib tampil: "Re-encode aktif, CPU akan meningkat." Default: stream copy (0 = ikut kamera) |
| C-13 | Picture-in-Picture (PiP) | 🎯 | — | **Desain:** Browser PiP API (`requestPictureInPicture()`). Tombol PiP muncul saat hover di video kamera. Hanya 1 kamera aktif PiP sekaligus (limitasi browser). Multi-kamera: buka tab baru atau window terpisah |

---

## D. Rekaman (Recordings)

**Router:** `backend/api/routers/recordings.py`
**Frontend:** `frontend/src/pages/Playback.tsx`
**Mobile:** `mobile/lib/screens/playback_screen.dart`
**Service:** `backend/services/recorder/`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| D-01 | Rekaman otomatis 24/7 | ✅ | #001 | FFmpeg `-c copy` RTSP → MP4/H.265 |
| D-02 | Segmentasi rekaman per durasi | ✅ | #001 | Default: 1 jam per file |
| D-03 | Playback di browser (streaming) | ✅ | #001 | Range header support, bisa scrub/seek |
| D-04 | Filter rekaman by kamera + tanggal | ✅ | #001 | — |
| D-05 | Timeline per hari (hourly view) | ✅ | #001 | Jam mana ada rekaman, tersedia dari API |
| D-06 | Proteksi rekaman (lock dari auto-delete) | ✅ | #001 | Toggle `is_protected`, operator ke atas |
| D-07 | Hapus rekaman manual | ✅ | #001 | Admin only, tidak bisa hapus yang protected |
| D-08 | Auto-delete rekaman lama (circular) | ✅ | #001 | Trigger saat disk > threshold |
| D-09 | Download rekaman ke lokal | ⏳ | — | Butuh endpoint `/recordings/{id}/download` |
| D-10 | Motion event marker di timeline | ⏳ | — | Tandai merah di scrubber posisi ada gerakan |
| D-11 | Kliping rekaman (potong segmen) | ⏳ | — | Export hanya menit X–Y dari rekaman |
| D-12 | Export ke format lain (MKV, AVI) | ⏳ | — | Saat ini hanya MP4 |
| D-13 | Pencarian rekaman by tanggal range | ⏳ | — | Filter rentang tanggal lebih fleksibel |

---

## E. Deteksi Gerakan (Motion Detection)

**Router:** `backend/api/routers/events.py`
**Frontend:** `frontend/src/pages/Events.tsx`
**Mobile:** `mobile/lib/screens/events_screen.dart`
**Service:** `backend/services/motion/detector.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| E-01 | Deteksi gerakan otomatis (OpenCV) | ✅ | #001 | Frame differencing, background subtractor MOG2 |
| E-02 | Event tersimpan di database | ✅ | #001 | Timestamp, severity, camera_id |
| E-03 | Filter events by kamera / tanggal / severity | ✅ | #001 | — |
| E-04 | Snapshot otomatis saat motion | ✅ | #001 | File JPG disimpan |
| E-05 | Notifikasi Telegram saat motion | ✅ | #001 | Kirim pesan + foto ke bot |
| E-06 | Notifikasi Email saat motion | ✅ | #001 | SMTP |
| E-07 | Snapshot lightbox (klik → buka besar) | ⏳ | — | UX — klik thumbnail foto jadi modal besar |
| E-08 | Export laporan events (CSV/PDF) | ⏳ | — | Download daftar events per periode |
| E-09 | Motion masking area (zona ignore) | ⏳ | — | Definisi poligon area di frame yang diabaikan |
| E-10 | Sensitivitas motion adjustable | ⏳ | — | Threshold `motion_pct` per kamera (saat ini hardcode 1.5%) |
| E-11 | Cooldown notifikasi (anti-spam) | ⏳ | — | Min X menit antar notif per kamera (saat ini hardcode 60 detik) |
| E-12 | Klip video saat event (pre/post buffer) | ⏳ | — | Simpan video 10 detik sebelum+sesudah event |
| E-13 | FPS adaptif saat motion | 🎯 | — | **Desain (lihat detail di bawah)** |

### E-13 — Desain FPS Adaptif Motion (Detail)

**Konsep:** Saat tidak ada motion, rekaman jalan normal dengan FPS rendah (`-c copy`, ikut kamera, misal 15fps). Saat motion terdeteksi, spawn proses FFmpeg baru yang merekam dengan FPS lebih tinggi (re-encode).

**Implementasi yang disepakati:**
- Setting ON/OFF di **Settings → Motion → FPS Adaptif**
- **Warning wajib muncul saat toggle ON:**
  > ⚠️ "Fitur FPS Adaptif akan meningkatkan beban CPU secara signifikan saat ada gerakan. Pastikan server memiliki pendinginan yang memadai dan CPU tidak sudah dalam kondisi tinggi. Rekaman motion akan disimpan sebagai file terpisah dan menggunakan storage tambahan."
- Pengaturan yang bisa dikonfigurasi:
  - FPS idle (default: ikut stream kamera / stream copy)
  - FPS saat motion (default: 25fps)
  - Durasi rekam setelah motion berhenti (default: 30 detik cooldown)
- **Konsekuensi storage:** Ada 2 jenis file rekaman — normal (continuous) + motion clip (file terpisah). Storage usage meningkat.
- **Teknis:** `motion/detector.py` trigger callback → `recorder/manager.py` spawn proses FFmpeg kedua dengan `-vf fps=25 -c:v libx265 -preset ultrafast` untuk durasi motion

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
| F-09 | Jadwal cleanup terjadwal | ⏳ | — | Cleanup rutin, bukan hanya saat disk penuh |
| F-10 | Alert jika disk kritis (< X%) | ⏳ | — | Notifikasi Telegram jika storage hampir penuh |

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
| G-04 | Auto-detect RTSP URL dari ONVIF | ✅ | #001 | — |
| G-05 | Test koneksi kamera yang ditemukan | ✅ | #001 | Sebelum ditambah ke sistem |
| G-06 | Status discovery (berjalan / selesai) | ✅ | #001 | Polling endpoint `/discovery/status` |
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
| H-09 | Setting FPS adaptif motion | 🎯 | — | Lihat E-13. Masuk tab Settings → Motion |
| H-10 | Setting FPS custom live view | 🎯 | — | Lihat C-12. Masuk tab Settings → Live View |
| H-11 | WhatsApp / Signal notification | ⏳ | — | Alternatif Telegram |
| H-12 | Webhook notification (custom URL) | ⏳ | — | Kirim JSON event ke URL eksternal |

---

## I. Monitoring Server

**Router:** `backend/api/routers/system.py`
**Frontend:** `frontend/src/pages/System.tsx`
**Util:** `backend/utils/health.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| I-01 | CPU usage realtime | ✅ | #001 | `psutil` |
| I-02 | RAM usage realtime (GB + %) | ✅ | #001 | — |
| I-03 | Disk usage (per drive, GB) | ✅ | #001 | — |
| I-04 | Uptime server | ✅ | #001 | Ditampilkan sebagai jam:menit:detik |
| I-05 | Status 4 services | ✅ | #001 | nvr-api, nvr-recorder, nvr-motion, nvr-encoder |
| I-06 | Jumlah kamera online / offline / total | ✅ | #001 | Dari RecordingManager |
| I-07 | WebSocket realtime update dashboard | ✅ | #001 | Tanpa polling dari frontend |
| I-08 | Log viewer di UI | ⏳ | — | Tampilkan output `journalctl` dari halaman System |
| I-09 | Alert CPU/RAM tinggi via notifikasi | ⏳ | — | Telegram alert jika CPU > 90% atau RAM > 85% |
| I-10 | Grafik historis (CPU/RAM/disk) | ⏳ | — | Time-series chart, simpan metrik ke DB |
| I-11 | Restart service dari UI | ⏳ | — | Admin bisa restart nvr-recorder dll dari browser |

---

## J. AV1 Encoder (Background)

**Service:** `backend/services/encoder/av1_encoder.py`, `scheduler.py`

| # | Fitur | Status | Sesi | Catatan |
|---|-------|--------|------|---------|
| J-01 | Re-encode H.265 → AV1 saat idle | ✅ | #001 | FFmpeg libsvtav1, hemat ~50% space |
| J-02 | Scheduler otomatis (malam hari) | ✅ | #001 | Hanya jalan saat server tidak sibuk |
| J-03 | Tidak ganggu rekaman aktif | ✅ | #001 | Priority rendah, yield ke recorder |
| J-04 | Progress encode di UI | ⏳ | — | Tampilkan % progress encode di halaman System |
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
| K-06 | flutter analyze verified | ⏳ | — | BUG-013, belum diverifikasi (butuh mesin dengan Flutter CLI) |
| K-07 | flutter build apk release | ⏳ | — | Tunggu K-06 selesai |
| K-08 | Push notification (FCM) | ⏳ | — | Notif ke HP saat ada motion event |
| K-09 | Fingerprint / biometric login | ⏳ | — | Login lebih cepat di HP |
| K-10 | Landscape mode / tablet layout | ⏳ | — | Optimasi untuk tablet / layar landscape |

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
| L-08 | Health check endpoint publik | ⏳ | — | `/health` tanpa auth untuk monitoring eksternal |
| L-09 | Firewall setup (UFW) | ⏳ | — | Panduan / script setup port yang perlu dibuka |

---

## Ringkasan Statistik Fitur

| Kategori | Total | ✅ Selesai | 🎯 Dirancang | 🟡 Sebagian | ⏳ Backlog | ⏭️ Skip |
|----------|-------|-----------|-------------|------------|-----------|--------|
| A. Auth & User | 10 | 5 | 0 | 1 | 3 | 1 |
| B. Manajemen Kamera | 16 | 13 | 1 | 0 | 2 | 0 |
| C. Live Streaming | 13 | 4 | 3 | 0 | 6 | 0 |
| D. Rekaman | 13 | 8 | 0 | 0 | 5 | 0 |
| E. Motion Detection | 13 | 6 | 1 | 0 | 6 | 0 |
| F. Storage | 10 | 7 | 0 | 0 | 3 | 0 |
| G. Discovery ONVIF | 8 | 7 | 0 | 0 | 1 | 0 |
| H. Konfigurasi | 12 | 8 | 2 | 0 | 2 | 0 |
| I. Monitoring Server | 11 | 7 | 0 | 0 | 4 | 0 |
| J. AV1 Encoder | 5 | 3 | 0 | 0 | 2 | 0 |
| K. Mobile (Flutter) | 10 | 5 | 0 | 0 | 5 | 0 |
| L. Deployment | 9 | 7 | 0 | 0 | 2 | 0 |
| **TOTAL** | **130** | **80** | **7** | **1** | **41** | **1** |

**Progress:** 80 selesai + 7 dirancang = **87/130 dalam pipeline (67%)**

---

## Backlog Prioritas — Urutan Pengerjaan yang Disarankan

### 🔴 Prioritas Tinggi (Blocking atau Kebutuhan Utama)

| Urutan | ID | Fitur | Alasan |
|--------|-----|-------|--------|
| 1 | K-06, K-07 | Verify flutter analyze + build APK | Mobile belum bisa dipakai sama sekali |
| 2 | C-11 | Toggle Main/Sub stream live view | Quick win — effort kecil, langsung berguna |
| 3 | C-13 | Picture-in-Picture (PiP) | Quick win — ~20 baris kode, UX langsung meningkat |
| 4 | D-09 | Download rekaman ke lokal | Kebutuhan dasar pengguna |

### 🟠 Prioritas Sedang (Feature Enhancement)

| Urutan | ID | Fitur | Alasan |
|--------|-----|-------|--------|
| 5 | E-13 | FPS adaptif saat motion | Desain sudah final, tinggal implementasi |
| 6 | C-12 | FPS custom live view | Desain sudah final, bisa dikerjakan bersamaan E-13 |
| 7 | E-10 | Sensitivitas motion adjustable | Mengurangi false positive |
| 8 | E-11 | Cooldown notifikasi (anti-spam) | Mencegah banjir notif Telegram |
| 9 | E-07 | Snapshot lightbox | UX improvement kecil |
| 10 | F-10 | Alert disk kritis | Penting untuk 30 kamera, disk bisa penuh cepat |

### 🟡 Prioritas Rendah (Nice-to-Have)

| Urutan | ID | Fitur | Alasan |
|--------|-----|-------|--------|
| 11 | B-13 | Kamera group/tag per area | Berguna untuk 2 lokasi (Medan + Palembang) |
| 12 | B-16 | Dukungan kamera non-RTSP (MJPEG) | Untuk kamera murah tanpa RTSP |
| 13 | C-06 | Pilihan layout grid | Operator mungkin hanya perlu lihat sebagian kamera |
| 14 | I-08 | Log viewer di UI | Debugging lebih mudah tanpa SSH |
| 15 | L-07 | HTTPS / SSL | Keamanan — penting sebelum production penuh |

---

## Catatan Teknis Penting

### Tentang FPS Adaptif (E-13) — Peringatan Implementasi
- Re-encode real-time butuh CPU signifikan. Untuk Intel i5 dengan 30 kamera, **maksimal 5–8 kamera aktif FPS adaptif secara bersamaan** tanpa overload
- Rekomendasikan user untuk set batas kamera yang bisa aktif FPS adaptif sekaligus
- Monitor CPU via `I-07` WebSocket saat fitur aktif
- Pertimbangkan tambah safeguard otomatis: jika CPU > 85%, pause FPS adaptif dan log warning

### Tentang PiP Multi-Kamera (C-13)
- Browser hanya mendukung **1 video PiP aktif sekaligus** (standar W3C)
- Untuk monitor lebih dari 1 kamera sambil kerja lain: solusi terbaik adalah **buka LiveView di browser window terpisah** yang di-resize kecil (seperti monitor kedua virtual)
- Fitur "multi-PiP" tidak ada rencana untuk diimplementasikan karena butuh custom window manager yang kompleks

### Tentang Stream Copy vs Re-Encode (C-12)
- Stream copy (`-c copy`): CPU ~0%, FPS ikut kamera — **default untuk semua kamera**
- Re-encode (`-c:v libx264 -preset ultrafast`): CPU meningkat per kamera ~5–15% di Intel i5
- Untuk 30 kamera, **jangan aktifkan FPS custom untuk semua kamera sekaligus**
- UI harus membatasi / memberikan estimasi CPU impact saat user memilih kamera yang akan di-override
