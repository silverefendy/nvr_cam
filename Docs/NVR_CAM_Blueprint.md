# Blueprint Aplikasi NVR CCTV Custom
## Berbasis: `silverefendy/nvr_cam` — Dikembangkan & Diskalakan

> **Dokumen ini mencakup:** Persiapan, arsitektur, komponen, teknologi (dengan perbandingan), dan langkah-langkah pembuatan secara sistematis dan scalable.

---

## Daftar Isi

1. [Gambaran Umum Proyek](#1-gambaran-umum-proyek)
2. [Analisis Referensi (nvr_cam)](#2-analisis-referensi-nvr_cam)
3. [Arsitektur Sistem](#3-arsitektur-sistem)
4. [Persiapan Lingkungan](#4-persiapan-lingkungan)
5. [Komponen Aplikasi — Detail Lengkap](#5-komponen-aplikasi--detail-lengkap)
6. [Perbandingan Teknologi](#6-perbandingan-teknologi)
7. [Struktur Folder & Kode](#7-struktur-folder--kode)
8. [Langkah-Langkah Pembuatan](#8-langkah-langkah-pembuatan)
9. [Panduan Scalability & Fitur Masa Depan](#9-panduan-scalability--fitur-masa-depan)
10. [Keamanan & Best Practice](#10-keamanan--best-practice)
11. [Checklist Pre-Production](#11-checklist-pre-production)

---

## 1. Gambaran Umum Proyek

### Tujuan
Membangun sistem NVR (Network Video Recorder) **custom**, **open source**, **tanpa lisensi channel**, yang dapat:
- Merekam 30+ kamera IP (Dahua/ONVIF) secara 24/7
- Menyimpan rekaman ke multi-HDD dengan manajemen storage otomatis
- Menyajikan live view dan playback via web browser dan APK Android
- Mengirim notifikasi motion detection ke Telegram
- Dikelola penuh oleh tim internal tanpa ketergantungan vendor

### Topologi Jaringan
```
[Pabrik]                    [Kantor]                   [Rumah]
30x Kamera Dahua            Web Dashboard              Monitor / HP
     |                           |                          |
Switch PoE 24-port          Mikrotik + ZeroTier        ZeroTier Client
     |                           |                          |
Ubuntu Server ←─── P2P Ubiquiti ─┘◄──── ZeroTier ──────────┘
(Recording Engine)
(FastAPI Backend)
(HLS Streaming)
(PostgreSQL DB)
(8x HDD 4TB = 32TB ZFS)
```

### Prinsip Desain
- **Modular** — setiap komponen berdiri sendiri, bisa diganti tanpa merusak komponen lain
- **Scalable** — dari 4 kamera bisa berkembang ke 100+ kamera dengan perubahan minimal
- **Self-hosted** — tidak ada ketergantungan layanan cloud berbayar
- **API-first** — semua fitur tersedia via REST API sehingga web, mobile, dan integrasi ERP bisa konsumsi endpoint yang sama

---

## 2. Analisis Referensi (nvr_cam)

### Apa yang dilakukan nvr_cam
Repository `silverefendy/nvr_cam` adalah implementasi dasar NVR berbasis Python yang mencakup:
- Koneksi ke stream RTSP kamera IP
- Perekaman video ke file lokal
- Deteksi motion sederhana menggunakan OpenCV
- Penyimpanan rekaman berdasarkan event motion

### Keterbatasan yang Akan Diatasi
| Keterbatasan nvr_cam | Solusi di Blueprint ini |
|---|---|
| Single camera / sedikit kamera | Multi-threaded, support 30+ kamera |
| Tidak ada web UI | React dashboard lengkap |
| Tidak ada API | FastAPI REST API + WebSocket |
| Storage tidak terkelola | ZFS + circular delete otomatis |
| Tidak ada notifikasi | Telegram Bot + Email |
| Tidak ada auth/user | JWT auth + role-based access |
| Tidak ada mobile app | Flutter APK Android |
| Tidak scalable | Arsitektur modular + Docker-ready |
| Tidak ada playback UI | Timeline-based playback |
| H.264 saja | H.265 + AV1 re-encode otomatis |

### Yang Dipertahankan dan Dikembangkan
- Konsep dasar: RTSP → capture → simpan file
- Motion detection berbasis OpenCV (dikembangkan dengan zona)
- Python sebagai bahasa utama backend

---

## 3. Arsitektur Sistem

### Diagram Layer

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│  [Web Browser]  [APK Android]  [ERPNext Integration]    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/HTTPS + WebSocket
┌────────────────────────▼────────────────────────────────┐
│                    API LAYER                             │
│  FastAPI (REST API + WebSocket)                          │
│  - Auth (JWT)          - Camera management              │
│  - Stream proxy (HLS)  - Playback endpoints             │
│  - Motion events       - Storage management             │
│  - Notification mgmt   - User management                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  SERVICE LAYER                           │
│  [Recording Engine]  [Motion Detector]  [Notifier]      │
│  [AV1 Encoder]       [Storage Manager] [Health Monitor] │
└──────┬──────────────────┬──────────────────┬────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼────────┐  ┌─────▼──────────┐
│  FFmpeg     │  │   OpenCV        │  │  Telegram Bot  │
│  Processes  │  │   Analysis      │  │  Gmail SMTP    │
└──────┬──────┘  └────────┬────────┘  └─────┬──────────┘
       │                  │                  │
┌──────▼──────────────────▼──────────────────▼──────────┐
│                  DATA LAYER                             │
│  [PostgreSQL DB]        [ZFS Storage Pool]              │
│  - Users & roles        - /mnt/driveE  (cam 1-3)       │
│  - Camera config        - /mnt/driveF  (cam 4-6)       │
│  - Motion events        - /mnt/driveG  (cam 7-9)       │
│  - Storage metadata     - ... dst                       │
│  - System logs          - /mnt/driveO  (cam 28-30)     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  HARDWARE LAYER                          │
│  Ubuntu Server 24.04 LTS (bare metal)                   │
│  Intel i5-13400 + 16GB RAM + NVMe 512GB                 │
│  8x HDD WD Purple 4TB (ZFS pool = 32TB usable)          │
│  Switch Gigabit 24-port                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Persiapan Lingkungan

### 4.1 Hardware yang Dibutuhkan

| Komponen | Spesifikasi | Qty | Estimasi Harga |
|---|---|---|---|
| CPU | Intel Core i5-13400 (iGPU QuickSync) | 1 | Rp 2.800.000 |
| Motherboard | B660/H610 ATX (8 SATA, 2 NVMe) | 1 | Rp 1.500.000 |
| RAM | DDR4 16GB dual channel | 1 set | Rp 600.000 |
| NVMe SSD | 512GB (OS + Aplikasi) | 1 | Rp 450.000 |
| HDD Surveillance | WD Purple 4TB | 8 | Rp 8.800.000 |
| PCIe SATA Card | Tambah 4 port SATA | 1 | Rp 200.000 |
| Casing + PSU | Tower 8-bay + 550W 80+ Bronze | 1 | Rp 700.000 |
| Switch Gigabit | 24-port (jaringan server) | 1 | Rp 900.000 |
| Switch PoE | 24-port 250W (power kamera) | 2 | Rp 3.000.000 |
| UPS | 1000VA | 1 | Rp 800.000 |
| Kamera IP | Dahua 4MP H.265 PoE ONVIF | 30 | Rp 15.000.000 |
| Kabel Cat6 + instalasi | Per kamera ~30m | 1 lot | Rp 4.000.000 |
| **Total** | | | **~Rp 38.750.000** |

> **Catatan:** Software seluruhnya gratis (Ubuntu, Python, FFmpeg, PostgreSQL, React, Flutter, dll).

### 4.2 Software & Tools Pengembangan

**Di laptop developer:**
- VS Code + extension Python, ESLint, Prettier, GitLens
- Git
- Docker Desktop (untuk test lokal)
- Flutter SDK (untuk develop APK)
- Node.js 20 LTS + npm
- Python 3.12+ + pip
- DBeaver (GUI PostgreSQL)
- Postman atau Bruno (test API)

**Di server Ubuntu:**
- Ubuntu Server 24.04 LTS (minimal, tanpa GUI desktop)
- ZFS on Linux
- FFmpeg (versi terbaru dari PPA)
- Python 3.12+
- PostgreSQL 16
- Node.js 20 LTS (untuk build frontend)
- Nginx (reverse proxy + serve frontend)
- Certbot (SSL, jika pakai domain)
- Supervisor atau systemd (process manager)

### 4.3 Akun & Layanan yang Dibutuhkan

| Layanan | Fungsi | Biaya |
|---|---|---|
| GitHub (private repo) | Version control | Gratis |
| Telegram (BotFather) | Notifikasi | Gratis |
| DuckDNS | DDNS dynamic IP | Gratis |
| ZeroTier | Remote access VPN | Gratis |
| Oracle Cloud Free Tier | VPS untuk ZeroTier Moon (opsional) | Gratis |
| Gmail | SMTP notifikasi email | Gratis |

---

## 5. Komponen Aplikasi — Detail Lengkap

### 5.1 Recording Engine (`backend/recorder/`)

**Fungsi:** Komponen inti. Mengelola koneksi RTSP ke semua kamera dan menyimpan stream ke file.

**Cara kerja:**
```
Kamera RTSP → FFmpeg process (stream copy, tanpa decode) → File .mp4 per segmen per jam
```

**Fitur yang diimplementasikan:**
- **Multi-camera manager:** Spawn 1 FFmpeg process per kamera, dikelola oleh Python
- **Stream copy mode:** Tidak decode/encode ulang — sangat ringan di CPU
- **Segmented recording:** Rekam dalam potongan per jam, format: `cam01/2025-01-15/14-00-00.mp4`
- **Auto-reconnect:** Jika kamera disconnect, coba reconnect tiap 30 detik
- **Health check:** Pantau status setiap FFmpeg process, restart jika mati
- **Dual stream support:** Main stream (HD) untuk lokal, sub-stream (low-res) untuk forward ke remote

**Konfigurasi kamera (config/cameras.yaml):**
```yaml
cameras:
  - id: "cam_01"
    name: "Pintu Masuk"
    rtsp_main: "rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0"
    rtsp_sub:  "rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=1"
    storage_drive: "/mnt/driveE"
    motion_detect: true
    motion_zones:
      - name: "area_gerbang"
        coords: [[100, 200], [400, 200], [400, 500], [100, 500]]
    retention_days: 30

  - id: "cam_02"
    name: "Parkiran"
    rtsp_main: "rtsp://admin:password@192.168.1.102:554/cam/realmonitor?channel=1&subtype=0"
    rtsp_sub:  "rtsp://admin:password@192.168.1.102:554/cam/realmonitor?channel=1&subtype=1"
    storage_drive: "/mnt/driveE"
    motion_detect: false
    retention_days: 14
```

### 5.2 Motion Detection Engine (`backend/motion/`)

**Fungsi:** Analisis video dari sub-stream untuk mendeteksi gerakan per zona, lalu simpan tag ke database.

**Cara kerja:**
```
Sub-stream RTSP (360p) → OpenCV decode → Background subtraction per zona → Event ke DB → Notifikasi Telegram
```

**Fitur:**
- **Per-zone detection:** Setiap kamera bisa punya beberapa zona independen
- **Background subtraction:** MOG2 algorithm — adaptif terhadap perubahan cahaya
- **Frame sampling:** Analisis hanya 3 fps dari sub-stream, bukan 25 fps penuh (hemat CPU)
- **Pre/post buffer:** Simpan tag 10 detik sebelum motion terdeteksi hingga 30 detik setelah selesai
- **Cooldown:** Hindari spam notifikasi — min 60 detik antar notifikasi per kamera
- **Snapshot:** Capture frame saat motion terdeteksi, simpan sebagai JPG untuk notifikasi

**Skema event di database:**
```sql
CREATE TABLE motion_events (
    id          BIGSERIAL PRIMARY KEY,
    camera_id   VARCHAR(20) NOT NULL,
    zone_name   VARCHAR(50),
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,
    duration_s  INTEGER,
    snapshot_path TEXT,
    video_file  TEXT,         -- path ke file rekaman yang mengandung event ini
    video_offset INTEGER,     -- detik ke berapa dalam file
    severity    SMALLINT DEFAULT 1,  -- 1=low, 2=medium, 3=high
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_motion_camera_time ON motion_events (camera_id, started_at DESC);
```

### 5.3 Storage Manager (`backend/storage/`)

**Fungsi:** Mengelola penggunaan disk — circular delete, laporan kapasitas, assign kamera ke drive.

**Fitur:**
- **Circular delete:** Jika sisa disk < threshold (default 10%), hapus file tertua secara otomatis
- **Lock/protect:** File bisa di-flag "protected" — tidak ikut auto-delete (untuk rekaman penting)
- **Drive assignment:** Setiap kamera punya drive sendiri sesuai config
- **Storage report:** API endpoint untuk query kapasitas, retensi aktual, estimasi penuh
- **Cleanup schedule:** Cron job tiap malam untuk re-scan dan bersihkan file orphan

**Logika circular delete:**
```python
def check_and_clean_drive(drive_path: str, threshold_pct: float = 10.0):
    usage = shutil.disk_usage(drive_path)
    free_pct = (usage.free / usage.total) * 100
    
    if free_pct < threshold_pct:
        # Ambil file rekaman tertua yang tidak diprotect
        oldest_files = get_oldest_recordings(drive_path, exclude_protected=True)
        for f in oldest_files:
            os.remove(f.path)
            db.delete_recording_metadata(f.id)
            if free_pct >= threshold_pct + 5:  # beri ruang 5% extra
                break
            free_pct = get_free_pct(drive_path)
```

### 5.4 AV1 Re-encoder (`backend/encoder/`)

**Fungsi:** Re-encode rekaman kemarin ke format AV1 saat server idle (dini hari), menghemat storage 40-60%.

**Cara kerja:**
```
Cron 01:00 WIB → Ambil file kemarin yang belum di-encode AV1 → 
FFmpeg encode (libsvtav1) → Verifikasi output → Hapus file lama → Update DB
```

**Konfigurasi:**
```python
AV1_ENCODE_SCHEDULE = "01:00"   # Mulai encode jam 01:00
AV1_ENCODE_STOP     = "05:00"   # Stop encode jam 05:00 (sebelum aktivitas pagi)
AV1_CRF             = 35        # Quality factor (28=high quality, 40=small file)
AV1_PRESET          = 8         # Speed preset (0=slowest/best, 12=fastest)
AV1_MAX_CAMERAS     = 5         # Encode max 5 kamera sekaligus (jaga CPU)
```

### 5.5 REST API (`backend/api/`)

**Fungsi:** Menyajikan semua data dan fungsi sistem melalui endpoint HTTP yang terstandar.

**Teknologi:** FastAPI + Uvicorn + Python

**Endpoint utama:**

```
AUTH
POST   /api/v1/auth/login          → JWT token
POST   /api/v1/auth/refresh        → Refresh token
POST   /api/v1/auth/logout

CAMERAS
GET    /api/v1/cameras             → List semua kamera + status
GET    /api/v1/cameras/{id}        → Detail kamera
POST   /api/v1/cameras             → Tambah kamera baru
PUT    /api/v1/cameras/{id}        → Update konfigurasi kamera
DELETE /api/v1/cameras/{id}        → Hapus kamera
GET    /api/v1/cameras/{id}/snapshot → Ambil snapshot terbaru

STREAMING
GET    /api/v1/stream/{id}/live    → URL HLS live stream
GET    /api/v1/stream/{id}/hls/*   → Serve HLS segments (.m3u8, .ts)

RECORDINGS
GET    /api/v1/recordings          → List rekaman (filter: camera, date, motion)
GET    /api/v1/recordings/{id}     → Detail rekaman
GET    /api/v1/recordings/{id}/play → Stream file untuk playback
DELETE /api/v1/recordings/{id}     → Hapus rekaman
POST   /api/v1/recordings/{id}/protect → Lock/unlock proteksi

MOTION EVENTS
GET    /api/v1/events              → List event motion (filter: camera, date, severity)
GET    /api/v1/events/{id}         → Detail event + snapshot
GET    /api/v1/events/summary      → Ringkasan harian

STORAGE
GET    /api/v1/storage             → Status semua drive
GET    /api/v1/storage/{drive}     → Detail drive tertentu

USERS
GET    /api/v1/users               → List user (admin only)
POST   /api/v1/users               → Tambah user
PUT    /api/v1/users/{id}          → Update user / reset password
DELETE /api/v1/users/{id}          → Hapus user

SETTINGS
GET    /api/v1/settings            → Semua pengaturan sistem
PUT    /api/v1/settings            → Update pengaturan
GET    /api/v1/settings/cameras/{id}/bitrate → Info bitrate kamera
PUT    /api/v1/settings/cameras/{id}         → Update bitrate, resolusi, jadwal

SYSTEM
GET    /api/v1/system/health       → Status server (CPU, RAM, disk, suhu)
GET    /api/v1/system/logs         → Log sistem terbaru
WebSocket /ws/events               → Real-time event stream ke dashboard
```

### 5.6 Web Dashboard (`frontend/`)

**Fungsi:** Antarmuka web untuk monitoring, playback, dan administrasi sistem.

**Teknologi:** React 18 + TypeScript + Tailwind CSS + Vite

**Halaman dan fitur:**

| Halaman | Fitur |
|---|---|
| **Live View** | Grid kamera 1x1/2x2/3x3/4x4/5x6, drag-drop layout, motion indicator, status badge, fullscreen per kamera, pilih drive/zona |
| **Playback** | Calendar picker tanggal, timeline per jam, motion markers di timeline, putar video langsung di browser, download klip |
| **Events** | List event motion, filter kamera/tanggal/severity, preview snapshot, link ke playback titik event |
| **Kamera** | Tambah/edit/hapus kamera, test koneksi RTSP, setting resolusi dan bitrate |
| **Storage** | Grafik kapasitas per drive, retensi aktual, file terlama, tombol manual cleanup |
| **User & Akses** | Manajemen user, assign role (admin/operator/viewer), log login |
| **Pengaturan** | Konfigurasi global: jadwal rekam, threshold storage, pengaturan notifikasi, tema tampilan, grid default |
| **Laporan** | Grafik motion per hari/minggu, uptime kamera, penggunaan storage trend |
| **System Monitor** | CPU/RAM/disk real-time, status service, log sistem |

**Role dan akses:**

| Role | Live View | Playback | Events | Kamera | Storage | User | Setting |
|---|---|---|---|---|---|---|---|
| Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Operator | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Viewer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Security | ✓ (kamera tertentu) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |

### 5.7 Notification Service (`backend/notifier/`)

**Fungsi:** Kirim notifikasi ke Telegram dan Email berdasarkan event.

**Jenis notifikasi:**

| Event | Channel | Isi |
|---|---|---|
| Motion terdeteksi | Telegram | Foto snapshot + nama kamera + waktu + zona |
| Kamera offline | Telegram + Email | Nama kamera + durasi offline |
| Disk hampir penuh | Telegram + Email | Drive mana + persentase sisa |
| File terlindungi terancam hapus | Telegram | Peringatan |
| Laporan harian | Telegram (opsional) | Ringkasan: total motion, kamera offline, storage |
| Server restart | Telegram | Notif otomatis saat service naik lagi |

**Format notifikasi Telegram:**
```
🔴 MOTION DETECTED
📷 CAM-01 — Pintu Masuk
📍 Zona: Area Gerbang
🕐 15 Jan 2025, 14:32:07
⏱️ Durasi: 8 detik
[foto snapshot dilampirkan]
```

### 5.8 Mobile App — APK Android (`mobile/`)

**Fungsi:** Akses live view, playback, dan notifikasi dari HP Android.

**Teknologi:** Flutter 3 + Dart

**Fitur:**
- Login dengan akun yang sama dengan web
- Live view kamera (1 atau 4 kamera sekaligus)
- Playback rekaman dengan date picker
- Push notification dari Telegram (terpisah dari APK)
- Status kamera (online/offline)
- Snapshot terbaru per kamera
- Dark mode otomatis

### 5.9 Database Schema (`backend/db/`)

**Teknologi:** PostgreSQL 16

**Tabel utama:**

```sql
-- Users & Auth
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE,
    password_hash TEXT NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active   BOOLEAN DEFAULT TRUE,
    last_login  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Camera Registry
CREATE TABLE cameras (
    id              VARCHAR(20) PRIMARY KEY,   -- "cam_01"
    name            VARCHAR(100) NOT NULL,
    location        VARCHAR(100),
    rtsp_main       TEXT NOT NULL,
    rtsp_sub        TEXT,
    storage_drive   VARCHAR(50) NOT NULL,
    motion_enabled  BOOLEAN DEFAULT FALSE,
    retention_days  INTEGER DEFAULT 30,
    is_active       BOOLEAN DEFAULT TRUE,
    config_json     JSONB,                     -- setting tambahan
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Recording Index
CREATE TABLE recordings (
    id              BIGSERIAL PRIMARY KEY,
    camera_id       VARCHAR(20) REFERENCES cameras(id),
    file_path       TEXT NOT NULL UNIQUE,
    file_size_mb    FLOAT,
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_s      INTEGER,
    codec           VARCHAR(10) DEFAULT 'H265',  -- H264, H265, AV1
    is_protected    BOOLEAN DEFAULT FALSE,
    is_encoded_av1  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recordings_camera_time ON recordings (camera_id, started_at DESC);
CREATE INDEX idx_recordings_time ON recordings (started_at DESC);

-- Motion Events
CREATE TABLE motion_events (
    id              BIGSERIAL PRIMARY KEY,
    camera_id       VARCHAR(20) REFERENCES cameras(id),
    recording_id    BIGINT REFERENCES recordings(id),
    zone_name       VARCHAR(50),
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_s      INTEGER,
    snapshot_path   TEXT,
    video_offset_s  INTEGER,
    severity        SMALLINT DEFAULT 1,
    notified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- System Logs
CREATE TABLE system_logs (
    id          BIGSERIAL PRIMARY KEY,
    level       VARCHAR(10),   -- INFO, WARN, ERROR
    service     VARCHAR(30),   -- recorder, motion, storage, api
    message     TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Notification Log
CREATE TABLE notification_log (
    id          BIGSERIAL PRIMARY KEY,
    type        VARCHAR(30),   -- motion, camera_offline, disk_full
    channel     VARCHAR(20),   -- telegram, email
    status      VARCHAR(10),   -- sent, failed
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Settings
CREATE TABLE settings (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Perbandingan Teknologi

### 6.1 Backend Framework

| Kriteria | **FastAPI** ⭐ | Flask | Django | Node.js/Express |
|---|---|---|---|---|
| Performance | Sangat tinggi (async) | Sedang | Sedang | Tinggi |
| Async native | ✓ Ya | Partial | Partial | ✓ Ya |
| Auto docs (Swagger) | ✓ Otomatis | Manual | Manual | Manual |
| WebSocket | ✓ Built-in | Library | Library | ✓ Built-in |
| Type safety | ✓ Pydantic | ✗ | Partial | TypeScript |
| Learning curve | Rendah | Rendah | Tinggi | Rendah |
| Cocok untuk video API | ✓ Sangat cocok | Cukup | Kurang | Cukup |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

### 6.2 Video Engine

| Kriteria | **FFmpeg** ⭐ | OpenCV | GStreamer | MediaMTX |
|---|---|---|---|---|
| Stream copy (tanpa decode) | ✓ Ya | ✗ Tidak | ✓ Ya | ✓ Ya |
| HLS output | ✓ Native | ✗ | Plugin | ✓ Native |
| H.265/AV1 encode | ✓ Ya | Partial | ✓ Ya | ✓ Ya |
| Hardware decode (QuickSync) | ✓ Ya | Partial | ✓ Ya | ✓ Ya |
| RTSP input | ✓ Ya | ✓ Ya | ✓ Ya | ✓ Ya |
| Motion detection | ✗ | ✓ Ya | Plugin | ✗ |
| Resource usage | Rendah | Tinggi | Sedang | Rendah |
| **Pilihan** | ✅ Record + HLS | ✅ Motion only | — | — |

> **Kombinasi terbaik:** FFmpeg untuk recording dan HLS streaming, OpenCV **hanya** untuk motion detection dari sub-stream.

### 6.3 Database

| Kriteria | **PostgreSQL** ⭐ | MySQL | SQLite | MongoDB |
|---|---|---|---|---|
| JSONB support | ✓ Native | Partial | ✗ | ✓ Native |
| Time-series queries | ✓ Sangat baik | Cukup | Buruk | Cukup |
| Indexing | ✓ Canggih | Baik | Terbatas | Baik |
| Concurrent writes | ✓ Baik | Baik | ✗ Buruk | ✓ Baik |
| Backup tools | pg_dump, streaming | mysqldump | File copy | mongodump |
| Cocok untuk event log | ✓ Sangat cocok | Cukup | Buruk | Cukup |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

### 6.4 Web Frontend

| Kriteria | **React + TypeScript** ⭐ | Vue 3 | Angular | Svelte |
|---|---|---|---|---|
| Ekosistem | Terbesar | Besar | Besar | Kecil |
| Video player library | HLS.js, Video.js | Sama | Sama | Sama |
| State management | Zustand/Redux | Pinia | NgRx | Built-in |
| Learning curve | Sedang | Rendah | Tinggi | Rendah |
| TypeScript support | ✓ Excellent | ✓ Baik | ✓ Excellent | ✓ Baik |
| Community & support | Terbesar | Besar | Besar | Kecil |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

### 6.5 Mobile App

| Kriteria | **Flutter** ⭐ | React Native | Native Android | Kotlin Multiplatform |
|---|---|---|---|---|
| 1 kode → Android + iOS | ✓ Ya | ✓ Ya | ✗ Android only | ✓ Ya |
| Video player RTSP/HLS | flutter_vlc_player | react-native-vlc | ExoPlayer | — |
| Performance | Sangat baik | Baik | Excellent | Baik |
| Learning curve | Sedang (Dart) | Rendah (JS) | Tinggi | Tinggi |
| Hot reload | ✓ Ya | ✓ Ya | Partial | Partial |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

### 6.6 Filesystem / Storage

| Kriteria | **ZFS** ⭐ | ext4 | Btrfs | XFS |
|---|---|---|---|---|
| Kompresi transparan | ✓ LZ4/ZSTD | ✗ | ✓ | ✗ |
| Deduplication | ✓ Built-in | ✗ | Partial | ✗ |
| Self-healing | ✓ Checksums | ✗ | Partial | ✗ |
| Snapshot | ✓ Instan | ✗ | ✓ | ✗ |
| Multi-disk pool | ✓ Native | LVM | ✓ | LVM |
| Cocok untuk 24/7 write | ✓ Excellent | Baik | Baik | Baik |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

### 6.7 Video Codec

| Kriteria | H.264 | **H.265** ⭐ | **AV1** ⭐ | H.266/VVC |
|---|---|---|---|---|
| Ukuran file (1080p 1 jam) | ~2.6 GB | ~1.3 GB | ~800 MB | ~650 MB |
| Hardware decode tersedia | Semua | i5 Gen 6+ | Masih terbatas | Belum |
| Kamera Dahua support | ✓ Ya | ✓ Ya | ✗ Tidak | ✗ Tidak |
| FFmpeg encode support | ✓ Ya | ✓ Ya | ✓ libsvtav1 | Partial |
| Royalti | ✓ Bebas | Ada (diabaikan) | ✓ Bebas | Ada |
| **Pilihan** | — | ✅ Live recording | ✅ Re-encode malam | — |

### 6.8 Process Manager

| Kriteria | **Systemd** ⭐ | Supervisor | PM2 | Docker |
|---|---|---|---|---|
| Built-in Ubuntu | ✓ Ya | ✗ Install | ✗ Install | ✗ Install |
| Auto-restart | ✓ Ya | ✓ Ya | ✓ Ya | ✓ Ya |
| Log management | journald | File | File | Container log |
| Resource limits | ✓ cgroups | Partial | Partial | ✓ Ya |
| Dependency ordering | ✓ Ya | Partial | ✗ | ✓ Ya |
| **Pilihan** | ✅ **Dipakai** | — | — | — |

---

## 7. Struktur Folder & Kode

```
cctv-system/
│
├── README.md
├── .gitignore
├── install.sh                    ← Installer otomatis 1 perintah
├── docker-compose.yml            ← Opsional untuk dev lokal
│
├── config/
│   ├── cameras.yaml              ← Konfigurasi semua kamera
│   ├── system.yaml               ← Konfigurasi sistem global
│   ├── storage.yaml              ← Mapping kamera ke drive
│   └── notifications.yaml        ← Konfigurasi Telegram, email
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                   ← Entry point — start semua service
│   │
│   ├── api/                      ← FastAPI REST API
│   │   ├── __init__.py
│   │   ├── app.py                ← FastAPI app instance
│   │   ├── dependencies.py       ← Auth, DB session
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── cameras.py
│   │   │   ├── stream.py
│   │   │   ├── recordings.py
│   │   │   ├── events.py
│   │   │   ├── storage.py
│   │   │   ├── users.py
│   │   │   ├── settings.py
│   │   │   └── system.py
│   │   └── websocket.py          ← Real-time event stream
│   │
│   ├── recorder/                 ← Recording engine
│   │   ├── manager.py            ← Kelola semua FFmpeg process
│   │   ├── camera_recorder.py    ← 1 instance per kamera
│   │   ├── ffmpeg_wrapper.py     ← Abstraksi perintah FFmpeg
│   │   └── reconnect.py          ← Auto-reconnect logic
│   │
│   ├── motion/                   ← Motion detection
│   │   ├── detector.py           ← OpenCV background subtraction
│   │   ├── zone_manager.py       ← Kelola zona per kamera
│   │   └── event_writer.py       ← Tulis event ke DB
│   │
│   ├── storage/                  ← Storage management
│   │   ├── manager.py            ← Circular delete, monitor
│   │   ├── indexer.py            ← Index file rekaman ke DB
│   │   └── cleaner.py            ← Cleanup orphan files
│   │
│   ├── encoder/                  ← AV1 re-encoder
│   │   ├── scheduler.py          ← Cron job encode
│   │   └── av1_encoder.py        ← FFmpeg AV1 wrapper
│   │
│   ├── notifier/                 ← Notification service
│   │   ├── telegram.py           ← Telegram Bot API
│   │   ├── email.py              ← Gmail SMTP
│   │   └── dispatcher.py         ← Route event ke channel
│   │
│   ├── db/                       ← Database layer
│   │   ├── connection.py         ← PostgreSQL connection pool
│   │   ├── models.py             ← SQLAlchemy models
│   │   ├── migrations/           ← Alembic migrations
│   │   └── repositories/         ← Data access objects
│   │       ├── camera_repo.py
│   │       ├── recording_repo.py
│   │       ├── event_repo.py
│   │       └── user_repo.py
│   │
│   └── utils/
│       ├── logger.py             ← Centralized logging
│       ├── config_loader.py      ← Load YAML config
│       └── health.py             ← System health checks
│
├── frontend/                     ← React web dashboard
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                  ← API client functions
│       ├── components/           ← Reusable UI components
│       │   ├── CameraGrid/
│       │   ├── VideoPlayer/
│       │   ├── Timeline/
│       │   ├── MotionBadge/
│       │   └── StorageChart/
│       ├── pages/                ← Halaman utama
│       │   ├── LiveView/
│       │   ├── Playback/
│       │   ├── Events/
│       │   ├── Cameras/
│       │   ├── Storage/
│       │   ├── Users/
│       │   ├── Settings/
│       │   └── System/
│       ├── store/                ← Zustand state management
│       └── hooks/                ← Custom React hooks
│
├── mobile/                       ← Flutter APK Android
│   ├── pubspec.yaml
│   ├── android/
│   ├── ios/
│   └── lib/
│       ├── main.dart
│       ├── api/
│       ├── screens/
│       │   ├── live_view.dart
│       │   ├── playback.dart
│       │   └── events.dart
│       └── widgets/
│
└── scripts/
    ├── install.sh                ← Installer utama
    ├── setup_zfs.sh              ← Setup ZFS pool
    ├── setup_db.py               ← Inisialisasi database
    ├── setup_nginx.sh            ← Konfigurasi Nginx
    ├── backup_config.sh          ← Backup konfigurasi
    ├── update.sh                 ← Update aplikasi dari GitHub
    └── health_check.sh           ← Cek kesehatan semua service
```

---

## 8. Langkah-Langkah Pembuatan

### Fase 0 — Persiapan (1–2 hari)

**0.1 Setup repository:**
```bash
# Di laptop developer
git init cctv-system
cd cctv-system
git remote add origin https://github.com/username/cctv-system.git
# Buat .gitignore (Python, Node, env files)
# Buat struktur folder
mkdir -p backend/{api/routers,recorder,motion,storage,encoder,notifier,db/{migrations,repositories},utils}
mkdir -p frontend/src/{api,components,pages,store,hooks}
mkdir -p mobile/lib/{api,screens,widgets}
mkdir -p config scripts
```

**0.2 Setup lingkungan Python:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy asyncpg alembic opencv-python-headless \
            python-telegram-bot pydantic-settings pyyaml psutil
pip freeze > backend/requirements.txt
```

**0.3 Setup Ubuntu Server:**
```bash
# Install dependencies sistem
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg python3 python3-pip python3-venv \
                    postgresql-16 nginx git curl wget \
                    zfsutils-linux nvme-cli smartmontools

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# Verifikasi
ffmpeg -version
python3 --version
psql --version
node --version
```

---

### Fase 1 — Infrastructure (1–2 hari)

**1.1 Setup ZFS pool:**
```bash
# Lihat nama disk
lsblk

# Buat ZFS pool dari 8 HDD (misal /dev/sdb sampai /dev/sdi)
sudo zpool create -f cctv_pool \
  /dev/sdb /dev/sdc /dev/sdd /dev/sde \
  /dev/sdf /dev/sdg /dev/sdh /dev/sdi

# Aktifkan kompresi LZ4
sudo zfs set compression=lz4 cctv_pool

# Buat dataset per grup kamera
sudo zfs create cctv_pool/driveE  # cam 1-3
sudo zfs create cctv_pool/driveF  # cam 4-6
sudo zfs create cctv_pool/driveG  # cam 7-9
# ... dst

# Lihat status
sudo zpool status
sudo zfs list
```

**1.2 Setup PostgreSQL:**
```bash
sudo -u postgres psql
CREATE USER cctv_user WITH PASSWORD 'password_kuat_di_sini';
CREATE DATABASE cctv_db OWNER cctv_user;
GRANT ALL PRIVILEGES ON DATABASE cctv_db TO cctv_user;
\q
```

**1.3 Test koneksi RTSP kamera:**
```bash
# Test stream kamera
ffplay rtsp://admin:password@192.168.1.101:554/cam/realmonitor

# Atau tanpa tampilan (cek koneksi saja)
ffprobe -v quiet -print_format json -show_streams \
  rtsp://admin:password@192.168.1.101:554/cam/realmonitor
```

---

### Fase 2 — Recording Engine (3–4 hari)

**2.1 Config loader:**
```python
# backend/utils/config_loader.py
import yaml
from pathlib import Path

def load_cameras() -> list[dict]:
    config_path = Path("config/cameras.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)["cameras"]
```

**2.2 FFmpeg wrapper:**
```python
# backend/recorder/ffmpeg_wrapper.py
import subprocess
from pathlib import Path
from datetime import datetime

def start_recording(camera: dict) -> subprocess.Popen:
    now = datetime.now()
    output_dir = Path(camera["storage_drive"]) / camera["id"] / now.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{now.strftime('%H-%M-%S')}.mp4"
    
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", camera["rtsp_main"],
        "-c", "copy",              # stream copy — tidak decode ulang
        "-f", "segment",           # potong per segmen
        "-segment_time", "3600",   # 1 jam per segmen
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        str(output_dir / "%H-%M-%S.mp4")
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
```

**2.3 Camera manager (multi-kamera):**
```python
# backend/recorder/manager.py
import asyncio
from .camera_recorder import CameraRecorder
from utils.config_loader import load_cameras

class RecordingManager:
    def __init__(self):
        self.recorders: dict[str, CameraRecorder] = {}
    
    async def start_all(self):
        cameras = load_cameras()
        tasks = [self._start_camera(cam) for cam in cameras if cam.get("is_active", True)]
        await asyncio.gather(*tasks)
    
    async def _start_camera(self, camera: dict):
        recorder = CameraRecorder(camera)
        self.recorders[camera["id"]] = recorder
        await recorder.start()
```

**2.4 Register sebagai systemd service:**
```ini
# /etc/systemd/system/cctv-recorder.service
[Unit]
Description=CCTV Recording Engine
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=cctv
WorkingDirectory=/opt/cctv
ExecStart=/opt/cctv/venv/bin/python backend/main.py --service recorder
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cctv-recorder
sudo systemctl start cctv-recorder
sudo systemctl status cctv-recorder
```

---

### Fase 3 — Database & API (4–6 hari)

**3.1 Database migrations:**
```bash
cd backend
alembic init db/migrations
# Edit alembic.ini dan env.py
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**3.2 FastAPI app:**
```python
# backend/api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, cameras, stream, recordings, events, storage, users, settings, system

app = FastAPI(title="CCTV NVR API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], 
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router,       prefix="/api/v1/auth")
app.include_router(cameras.router,    prefix="/api/v1/cameras")
app.include_router(stream.router,     prefix="/api/v1/stream")
app.include_router(recordings.router, prefix="/api/v1/recordings")
app.include_router(events.router,     prefix="/api/v1/events")
app.include_router(storage.router,    prefix="/api/v1/storage")
app.include_router(users.router,      prefix="/api/v1/users")
app.include_router(settings.router,   prefix="/api/v1/settings")
app.include_router(system.router,     prefix="/api/v1/system")
```

**3.3 HLS streaming untuk live view:**
```python
# backend/api/routers/stream.py
import asyncio, subprocess
from fastapi import APIRouter, BackgroundTasks
from pathlib import Path

router = APIRouter()
active_streams: dict[str, subprocess.Popen] = {}

@router.get("/{camera_id}/live")
async def get_live_stream(camera_id: str, background_tasks: BackgroundTasks):
    if camera_id not in active_streams:
        background_tasks.add_task(start_hls_stream, camera_id)
    return {"hls_url": f"/api/v1/stream/{camera_id}/hls/index.m3u8"}

async def start_hls_stream(camera_id: str):
    hls_dir = Path(f"/tmp/hls/{camera_id}")
    hls_dir.mkdir(parents=True, exist_ok=True)
    # FFmpeg: RTSP sub-stream → HLS segments
    cmd = [
        "ffmpeg", "-rtsp_transport", "tcp",
        "-i", get_rtsp_sub(camera_id),
        "-c:v", "copy", "-c:a", "aac",
        "-f", "hls",
        "-hls_time", "2",
        "-hls_list_size", "5",
        "-hls_flags", "delete_segments",
        str(hls_dir / "index.m3u8")
    ]
    proc = subprocess.Popen(cmd)
    active_streams[camera_id] = proc
```

---

### Fase 4 — Web Dashboard (1–2 minggu)

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install @tanstack/react-query zustand hls.js axios \
            tailwindcss @headlessui/react recharts \
            @heroicons/react react-router-dom date-fns
npx tailwindcss init -p
```

**Komponen kunci yang dibangun:**
1. `CameraGrid` — grid video player dengan resize dinamis
2. `HLSPlayer` — video player berbasis hls.js
3. `Timeline` — bar jam dengan motion markers untuk playback
4. `MotionBadge` — indikator real-time motion via WebSocket
5. `StorageGauge` — gauge kapasitas per drive

---

### Fase 5 — Motion Detection & Notifikasi (3–5 hari)

```python
# backend/motion/detector.py
import cv2
import asyncio

class MotionDetector:
    def __init__(self, camera: dict):
        self.camera = camera
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
    
    async def run(self):
        cap = cv2.VideoCapture(self.camera["rtsp_sub"])
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(5)
                cap = cv2.VideoCapture(self.camera["rtsp_sub"])
                continue
            
            frame_count += 1
            if frame_count % 8 != 0:  # Proses tiap 8 frame (~3fps dari 25fps)
                continue
            
            # Resize ke resolusi rendah untuk analisis
            small = cv2.resize(frame, (640, 360))
            
            # Deteksi per zona
            for zone in self.camera.get("motion_zones", []):
                if self._check_zone(small, zone):
                    await self._on_motion_detected(zone, frame)
```

---

### Fase 6 — APK Android (1–2 minggu)

```bash
# Install Flutter
flutter create mobile --org com.namaperusahaan --project-name cctv_mobile
cd mobile
flutter pub add http flutter_vlc_player shared_preferences \
               go_router flutter_secure_storage
```

---

### Fase 7 — AV1 Re-encoder (2–3 hari)

```bash
# Pastikan FFmpeg support AV1
ffmpeg -encoders | grep av1
# Harus ada: libsvtav1

# Test encode manual
ffmpeg -i input.mp4 -c:v libsvtav1 -crf 35 -preset 8 -c:a copy output_av1.mp4
```

```python
# backend/encoder/scheduler.py
import schedule, time
from .av1_encoder import encode_yesterday_recordings

schedule.every().day.at("01:00").do(encode_yesterday_recordings)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### Fase 8 — Installer Script (1–2 hari)

```bash
#!/bin/bash
# install.sh — Installer otomatis CCTV System

set -e
echo "======================================"
echo " CCTV System Installer"
echo "======================================"

# 1. Update & install dependencies
apt-get update -qq
apt-get install -y -qq ffmpeg python3 python3-pip python3-venv \
    postgresql-16 nginx git nodejs npm zfsutils-linux

# 2. Clone aplikasi
git clone https://github.com/username/cctv-system /opt/cctv
cd /opt/cctv

# 3. Setup Python env
python3 -m venv venv
./venv/bin/pip install -q -r backend/requirements.txt

# 4. Setup database
sudo -u postgres createuser cctv_user
sudo -u postgres createdb cctv_db -O cctv_user
./venv/bin/alembic upgrade head

# 5. Build web frontend
cd frontend && npm install -q && npm run build && cd ..

# 6. Konfigurasi Nginx
cp scripts/nginx.conf /etc/nginx/sites-available/cctv
ln -sf /etc/nginx/sites-available/cctv /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 7. Register systemd services
cp scripts/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cctv-recorder cctv-api cctv-motion cctv-encoder
systemctl start  cctv-recorder cctv-api cctv-motion cctv-encoder

# 8. Selesai
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "======================================"
echo " Instalasi selesai!"
echo " Buka browser: http://$SERVER_IP"
echo " Default login: admin / cctv1234"
echo "======================================"
```

---

## 9. Panduan Scalability & Fitur Masa Depan

### Skala Horizontal
Jika kamera bertambah dari 30 menjadi 100+:
- Pisahkan recording engine ke server kedua
- API server tetap 1 (atau load balance dengan Nginx)
- Database tetap 1 PostgreSQL (atau upgrade ke Citus untuk sharding)
- Storage: tambah HDD atau NAS via NFS mount

### Fitur yang Bisa Ditambah (tanpa ubah arsitektur)

| Fitur | Modul Baru | Estimasi Waktu |
|---|---|---|
| Face recognition | `backend/ai/face_recognizer.py` | 2–3 minggu |
| License plate detection | `backend/ai/lpr.py` | 2–3 minggu |
| Object detection (YOLO) | `backend/ai/object_detector.py` | 1–2 minggu |
| PTZ control | `backend/ptz/dahua_ptz.py` | 3–5 hari |
| Integrasi ERPNext | `backend/integrations/erpnext.py` | 1 minggu |
| ONVIF discovery otomatis | `backend/discovery/onvif_scan.py` | 3–5 hari |
| Timelapse generator | `backend/encoder/timelapse.py` | 2–3 hari |
| Export rekaman ke cloud | `backend/storage/cloud_backup.py` | 3–5 hari |
| Analytics dashboard | Frontend page baru | 1 minggu |
| Multi-site (pabrik + gudang) | Config multi-site + API routing | 2 minggu |

---

## 10. Keamanan & Best Practice

### API Security
```python
# JWT dengan expiry pendek
ACCESS_TOKEN_EXPIRE = 60  # menit
REFRESH_TOKEN_EXPIRE = 7  # hari

# Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempt per menit
async def login(...): ...
```

### Jaringan
- Nginx sebagai reverse proxy — backend tidak langsung expose ke internet
- HTTPS wajib jika akses dari internet (gunakan Certbot / Let's Encrypt gratis)
- Firewall: UFW — hanya buka port 80, 443, dan 22 (SSH)
- SSH: disable password login, pakai SSH key

### Database
- Password PostgreSQL disimpan di environment variable, bukan di kode
- Backup otomatis tiap malam: `pg_dump cctv_db | gzip > backup_$(date +%Y%m%d).sql.gz`

### RTSP Kamera
- Ganti password default kamera sebelum install
- Gunakan RTSP over TCP (bukan UDP) untuk koneksi yang lebih stabil dan secure
- Isolasi kamera di VLAN tersendiri jika memungkinkan

---

## 11. Checklist Pre-Production

### Hardware
- [ ] Semua HDD terpasang dan terdeteksi (`lsblk`)
- [ ] ZFS pool terbuat dan mount point tersedia
- [ ] Switch PoE menyuplai daya kamera
- [ ] Semua kamera dapat IP dan RTSP stream bisa diakses
- [ ] UPS terhubung dan ditest

### Software
- [ ] Ubuntu update penuh
- [ ] PostgreSQL berjalan dan database terbuat
- [ ] Semua systemd service enabled dan berjalan
- [ ] Nginx serve frontend di port 80
- [ ] Semua kamera berhasil direkam (cek file di drive)
- [ ] Motion detection berjalan minimal untuk kamera prioritas
- [ ] Telegram Bot mengirim notifikasi test berhasil
- [ ] Web dashboard bisa diakses dari browser internal
- [ ] Login dan semua halaman web berfungsi
- [ ] Playback rekaman berhasil dari web

### Remote Access
- [ ] ZeroTier berjalan di Mikrotik kantor dan rumah
- [ ] Web dashboard bisa diakses dari luar via ZeroTier
- [ ] APK Android terpasang dan bisa live view

### Monitoring
- [ ] Alert kamera offline berfungsi (test dengan cabut kamera)
- [ ] Alert disk hampir penuh berfungsi
- [ ] Circular delete berjalan otomatis
- [ ] Backup config dijadwalkan

---

*Dokumen ini bersifat living document — perbarui setiap kali ada perubahan arsitektur atau teknologi yang digunakan.*

**Versi:** 1.0.0  
**Dibuat:** 2025  
**Referensi:** `silverefendy/nvr_cam`, `PhazerTech/rtsp-security-cam`, `pynvr`
