# AUDIT REPORT — nvr_cam
## Laporan Audit Teknis Lengkap

**Tanggal Audit:** 22 Juli 2026  
**Auditor:** Claude (via MCP GitHub)  
**Scope:** Semua file di branch `main` — struktur, kode, konfigurasi, dokumentasi  
**Repo:** https://github.com/silverefendy/nvr_cam

---

## 1. Ringkasan Eksekutif

nvr_cam adalah sistem NVR CCTV custom yang dibangun dalam 7 sesi iteratif (melibatkan Claude, Devin AI, dan Cascade AI) sejak akhir Juni 2026. Secara keseluruhan, proyek ini dalam kondisi **baik untuk tahap development** — backend dan frontend sudah build clean, deployment script native Ubuntu sudah siap. Namun ada beberapa risiko yang perlu diperhatikan sebelum production deployment penuh, terutama di area keamanan, testing, dan Flutter.

**Verdict:** ✅ Siap untuk pilot deployment internal — dengan catatan di bagian risiko.

---

## 2. Cara Aplikasi Dijalankan

### 2.1 Mode Production — Native Ubuntu (Direkomendasikan)

Aplikasi **tidak menggunakan Docker untuk production**. Semua komponen diinstall langsung ke Ubuntu Server 24.04 via `scripts/install.sh`.

```
[Kamera Dahua RTSP]
        ↓
[FFmpeg (nvr-recorder)] ────→ [ZFS HDD Pool /mnt/recordings/]
        ↓
[OpenCV (nvr-motion)] ──────→ [Telegram / Email Notifikasi]
        ↓
[FastAPI (nvr-api)] ────────→ [PostgreSQL 16]
        ↓
[Nginx reverse proxy] ──────→ [React Frontend (port 80)]
                        ↓
               [HLS stream ke browser]
```

**4 systemd services yang berjalan:**

| Service | Binary | Fungsi |
|---------|--------|--------|
| `nvr-api` | `uvicorn backend.api.app:app` | REST API + WebSocket, port 8000 |
| `nvr-recorder` | `python backend/services/recorder/manager.py` | Spawn FFmpeg per kamera |
| `nvr-motion` | `python backend/services/motion/manager.py` | OpenCV frame analysis |
| `nvr-encoder` | `python backend/services/encoder/scheduler.py` | AV1 re-encode background |

### 2.2 Mode Development — Docker Compose

File `docker-compose.dev.yml` tersedia untuk development lokal. Men-container-kan: PostgreSQL, FastAPI backend, dan React frontend. **Tidak men-container-kan FFmpeg recording pipeline** (yang butuh akses device /dev dan network kamera).

```yaml
# docker-compose.yml (production reference — jarang dipakai)
services:
  db:      postgres:16-alpine
  api:     python:3.12-slim + ffmpeg + opencv libs
  frontend: nginx serving built React
```

### 2.3 Nginx sebagai Entry Point

Nginx dikonfigurasi sebagai reverse proxy:
- Port 80 → serve static React build (`/opt/nvr_cam/frontend/dist`)
- `/api/*` → proxy ke `http://localhost:8000` (FastAPI)
- `/ws/*` → proxy WebSocket ke FastAPI
- `/hls/*` → serve HLS segments dari `/var/lib/nvr_cam/hls/`
- `/snapshots/*` → serve snapshot JPEG dari `/var/lib/nvr_cam/snapshots/`

---

## 3. Struktur Proyek

```
nvr_cam/
├── .env.example          ← Template konfigurasi secrets
├── .gitignore
├── Dockerfile.backend    ← Untuk Docker dev mode
├── Makefile              ← Shortcut perintah dev
├── docker-compose.yml    ← Docker prod reference
├── docker-compose.dev.yml← Docker dev mode
├── README.md
├── FEATURES.md           ← Daftar lengkap 130 fitur
├── PROGRESS.md           ← Timeline sesi + bug tracker
├── HANDOFF.md            ← Panduan handoff ke AI baru
├── SUMMARY.md            ← File ini (ringkasan proyek)
├── AUDIT_REPORT.md       ← File ini
├── LICENSE               ← MIT License
├── Docs/
│   └── NVR_CAM_Blueprint.md  ← Arsitektur teknis
├── backend/
│   ├── main.py           ← Entry point development
│   ├── alembic.ini       ← Konfigurasi migrasi DB
│   ├── requirements.txt  ← Dependensi Python
│   ├── pytest.ini
│   ├── api/
│   │   ├── app.py        ← FastAPI app factory + lifespan
│   │   ├── websocket.py  ← WebSocket handler
│   │   └── routers/      ← 11 router (auth, cameras, stream,
│   │                          recordings, events, storage, users,
│   │                          settings, system, config, discovery)
│   ├── core/             ← Config, security, logging, exceptions
│   ├── db/
│   │   ├── models/       ← 6 SQLAlchemy models
│   │   ├── repositories/ ← Data access layer
│   │   └── migrations/   ← Alembic migration files
│   ├── services/
│   │   ├── recorder/     ← ffmpeg_wrapper, camera_recorder, manager
│   │   ├── motion/       ← detector (OpenCV), manager
│   │   ├── storage/      ← circular delete manager
│   │   ├── encoder/      ← av1_encoder, scheduler
│   │   ├── notifier/     ← telegram, email, dispatcher
│   │   ├── discovery/    ← onvif_scanner
│   │   └── auth/         ← JWT auth service
│   ├── utils/
│   │   ├── health.py
│   │   ├── config_manager.py
│   │   └── setup_db.py
│   └── tests/            ← Test files (coverage belum diverifikasi)
├── frontend/
│   └── src/
│       ├── api/          ← API client functions
│       ├── components/   ← VideoPlayer, CameraGrid, Sidebar, dll
│       ├── pages/        ← 10 halaman UI
│       ├── store/        ← Zustand state management
│       └── hooks/        ← useHLSPlayer, useWebSocket
├── mobile/
│   └── lib/
│       ├── screens/      ← 7 screen Flutter
│       ├── models/       ← Dart data models
│       └── services/     ← API service layer
├── config/
│   ├── cameras.yaml      ← Daftar kamera + RTSP URL
│   ├── storage.yaml      ← Mapping kamera ke drive
│   └── system.yaml       ← Parameter sistem
└── scripts/
    ├── install.sh        ← One-line install Ubuntu
    ├── update.sh         ← Update script
    ├── nginx/cctv.conf   ← Nginx config
    ├── systemd/          ← 4 service unit files
    └── setup_db.py       ← Seed admin user
```

**Total estimasi file:** ~80+ file kode (backend + frontend + mobile)

---

## 4. Fitur Aplikasi

### 4.1 Fitur yang Sudah Selesai (80 dari 130)

#### A. Autentikasi & User Management
- Login JWT (access token + auto-refresh)
- Logout + invalidate token
- 5 role RBAC: `super_admin`, `admin`, `operator`, `viewer`, `security`
- CRUD user (admin only)
- Ganti password (UI ada, endpoint perlu verifikasi)

#### B. Manajemen Kamera (13/16)
- CRUD kamera (tambah, edit, hapus soft-delete)
- Test koneksi RTSP via `ffprobe`
- Snapshot on-demand (1 frame JPG via FFmpeg)
- Auto-build URL format Dahua RTSP
- Dual stream (main + sub)
- Enable/disable motion per kamera
- Retention days + segment duration per kamera
- Urutan tampilan kamera (sort_order)
- Discovery ONVIF (WS-Discovery multicast + fallback port scan)
- Kamera non-Dahua RTSP custom URL ✅

#### C. Live Streaming (4/13)
- Live view grid hingga 30 kamera via HLS
- Status online/offline real-time (WebSocket)
- Snapshot thumbnail preview di grid
- RTSP → FFmpeg → HLS pipeline

#### D. Rekaman (8/13)
- Rekaman 24/7 H.265 stream copy
- Segmentasi per jam (1 file = 1 jam)
- Playback di browser (HTTP Range, scrub/seek)
- Filter kamera + tanggal + timeline hourly
- Proteksi rekaman dari auto-delete
- Hapus rekaman manual (admin)
- Auto-delete circular saat disk > threshold

#### E. Deteksi Gerakan (6/13)
- OpenCV MOG2 background subtractor
- Events tersimpan di DB (timestamp, severity, camera)
- Filter events
- Snapshot otomatis saat motion
- Notifikasi Telegram (teks + foto)
- Notifikasi Email SMTP

#### F. Storage (7/10)
- Dashboard status semua drive
- Estimasi sisa hari storage
- Mapping kamera per drive
- Manual cleanup dari UI
- Auto-cleanup saat disk > 85%
- Multi-drive hingga 8 HDD
- ZFS pool support

#### G. Discovery ONVIF (7/8)
- Scan multicast WS-Discovery
- Fallback port scanning
- Info kamera: IP, port, maker, model, MAC
- Auto-detect RTSP URL
- Test koneksi sebelum tambah ke sistem
- Status discovery polling
- Scan subnet spesifik

#### H. Konfigurasi (8/12)
- Edit umum sistem, storage, notifikasi dari UI
- Test notifikasi (Telegram/Email) dari UI
- Apply config live tanpa restart penuh
- Backup + restore config ZIP (5 backup terakhir)

#### I. Monitoring Server (7/11)
- CPU, RAM, disk real-time via WebSocket
- Uptime server
- Status 4 services
- Jumlah kamera online/offline/total

#### J. AV1 Encoder (3/5)
- Re-encode H.265 → AV1 (libsvtav1) saat idle
- Scheduler otomatis malam hari
- Tidak ganggu recorder aktif

#### K. Mobile Flutter (5/10)
- 7 screens sudah dikode (login, home, camera_view, playback, events, settings, splash)
- JWT auth + HLS player

#### L. Deployment (7/9)
- `install.sh` native Ubuntu (sudah difix BUG-020–024)
- 4 systemd services
- Nginx config
- Alembic auto-migration saat install
- Docker Compose dev mode

---

## 5. Kelebihan Aplikasi

### ✅ Arsitektur
- **Tanpa lisensi channel** — hemat biaya signifikan vs NVR komersial (Hikvision/Dahua NVR komersial bayar per channel)
- **Full open source** — bebas dikustomisasi sesuai kebutuhan pabrik
- **Scalable** — desain mendukung hingga 30+ kamera dengan resource server moderat (Intel i5)
- **Native deploy** — tidak bergantung Docker di production, lebih ringan dan stabil untuk server dedicated
- **ZFS storage** — compression LZ4 + dedup menghemat space, integritas data lebih terjamin

### ✅ Fitur Teknis
- **Stream copy rekaman** — rekaman H.265 tanpa re-encode (CPU ~0% untuk recording)
- **AV1 re-encoder background** — hemat ~50% storage jangka panjang
- **HLS streaming** — universal, bisa dibuka di browser apapun tanpa plugin
- **WebSocket real-time** — dashboard update live tanpa polling/refresh
- **ONVIF discovery** — tidak perlu input IP kamera satu per satu secara manual
- **Dual stream Dahua** — sub stream untuk live view hemat bandwidth, main stream untuk rekaman
- **Multi-drive mapping** — kamera bisa tersebar ke drive berbeda untuk load balancing I/O
- **Circular storage** — tidak perlu khawatir disk penuh, otomatis hapus lama

### ✅ Operasional
- **One-command install** — `curl ... | sudo bash` langsung jalan
- **Notifikasi Telegram** — monitoring tanpa perlu buka dashboard
- **Backup config** — mudah pindah server, config tersimpan di ZIP
- **Mobile app** — akses dari HP (pending APK build)
- **ZeroTier remote access** — akses aman dari kantor ke pabrik tanpa VPN hardware

### ✅ Developer Experience
- Dokumentasi lengkap: FEATURES.md, PROGRESS.md, HANDOFF.md, Blueprint
- Bug tracker terintegrasi di PROGRESS.md
- YAML config (tidak hardcode di kode)
- Docker Compose untuk dev mode
- Makefile untuk shortcut perintah

---

## 6. Kekurangan & Risiko

### 🔴 Risiko Tinggi

**1. Tidak ada HTTPS/SSL (L-07 — Backlog)**
- Semua traffic (termasuk login + JWT token) lewat HTTP plain text
- Jika ada akses dari luar jaringan lokal (via ZeroTier), token bisa disadap
- **Rekomendasi:** Pasang Let's Encrypt sebelum expose ke jaringan publik apapun

**2. Password default tidak di-enforce ganti (A-login)**
- Login default `admin / nvr1234` didokumentasikan di README publik
- Tidak ada paksa ganti password saat first login
- **Rekomendasi:** Tambahkan `force_password_change` flag di tabel user, redirect ke halaman ganti password

**3. Tidak ada unit test yang terverifikasi**
- Folder `backend/tests/` ada tapi coverage belum diverifikasi
- Tidak ada CI/CD pipeline (GitHub Actions)
- Bug-bug sebelumnya (BUG-001 s/d BUG-024) ditemukan manual, bukan dari test
- **Rekomendasi:** Minimal tambah test untuk recorder manager, motion detector, storage cleanup

**4. Mobile Flutter belum bisa dipakai (BUG-013)**
- `flutter analyze` belum diverifikasi clean
- APK belum pernah di-build
- Tidak ada FCM push notification
- Mobile adalah satu-satunya cara notifikasi langsung ke HP (selain Telegram bot)

### 🟠 Risiko Sedang

**5. Live View fitur terbatas (4/13 selesai)**
- Tidak ada fullscreen, layout grid pilihan, digital zoom
- Toggle main/sub stream belum ada (hanya 1 stream hardcoded per kamera)
- Untuk pabrik dengan 30 kamera, operator butuh filter subset kamera yang dipantau

**6. Motion detection masih kasar (hardcode threshold)**
- Sensitivitas motion di-hardcode 1.5% — tidak bisa diatur per kamera dari UI
- Cooldown notifikasi di-hardcode 60 detik — tidak bisa diatur
- Tidak ada motion masking (area tertentu diabaikan)
- Potensi false positive tinggi untuk environment pabrik yang dinamis

**7. Download rekaman belum ada (D-09)**
- Operator tidak bisa download clip video untuk dibawa ke kepolisian/asuransi
- Ini fitur dasar NVR yang masih backlog

**8. Tidak ada 2FA (A-07)**
- Akses admin hanya single factor (username + password)
- Jika credential bocor, seluruh sistem exposed

**9. Tidak ada audit log (A-08)**
- Tidak tercatat siapa yang login, hapus rekaman, ubah konfigurasi
- Penting untuk lingkungan pabrik/industri

**10. Alert storage kritis belum ada (F-10)**
- Jika disk penuh dan auto-cleanup gagal, rekaman berhenti tanpa notifikasi
- Untuk 30 kamera H.265, disk bisa penuh lebih cepat dari perkiraan

### 🟡 Risiko Rendah / Minor

**11. HLS latency ~5–30 detik**
- HLS secara nature punya latency karena buffering segments
- Untuk monitoring real-time ketat, ini bisa jadi masalah
- Alternatif (WebRTC) tidak ada di roadmap

**12. OpenCV untuk motion detection di 30 kamera**
- OpenCV CPU-based bisa jadi bottleneck di Intel i5 dengan 30 kamera aktif simultan
- Tidak ada GPU acceleration untuk motion detection
- Belum ada benchmark CPU usage pada beban penuh 30 kamera

**13. Satu server, tidak ada redundansi**
- Jika server mati, semua rekaman berhenti
- Tidak ada failover atau HA setup
- Cocok untuk pilot, perlu dipertimbangkan untuk critical production

**14. Docker Compose tidak fully production-ready**
- `docker-compose.yml` tidak men-container-kan recording pipeline yang butuh akses kamera network
- Volume `/mnt` di-mount langsung — tidak portable
- Tidak ada health check yang lengkap untuk semua services

**15. `structlog` dead code (BUG-019 — Skipped)**
- Ada referensi ke `structlog` yang tidak dipakai, sisa dari desain awal
- Cleanup kecil yang diputuskan skip tapi bisa membingungkan developer baru

---

## 7. Temuan Konfigurasi

### 7.1 Konsistensi Naming (sudah difix di Sesi #007)

Sebelumnya ada inkonsistensi antara nama database (`cctv_db` vs `nvr_cam`), nama user (`cctv_user` vs `nvr_user`), dan nama services (`cctv-*` vs `nvr-*`). Semua sudah difix di Sesi #007.

**Status saat ini (sudah sinkron):**

| Item | Nilai |
|------|-------|
| DB Name | `nvr_cam` |
| DB User | `nvr_user` |
| Service names | `nvr-api`, `nvr-recorder`, `nvr-motion`, `nvr-encoder` |
| Install dir | `/opt/nvr_cam` |
| Runtime dir | `/var/lib/nvr_cam/` |

### 7.2 HLS Directory

Sebelumnya HLS disimpan di `/tmp/hls` yang hilang saat server reboot. Sudah difix ke `/var/lib/nvr_cam/hls/` (persistent).

### 7.3 .env.example

File `.env.example` ada dan lengkap dengan komentar bahasa Indonesia. Secrets yang wajib diisi:
- `DB_PASSWORD`
- `JWT_SECRET` (minimal 32 karakter)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- `RECORDINGS_BASE_PATH` (sesuaikan ke ZFS pool)

⚠️ `.env.example` ter-COPY ke `.env` saat Docker build (`COPY .env.example .env`). Ini berarti pada Docker mode, jika user lupa buat `.env`, value default dari example akan terpakai. Perlu divalidasi di `backend/core/config.py`.

### 7.4 Alembic

alembic.ini sudah difix ke URL environment variable (BUG-017). Auto-run saat install.

---

## 8. Analisis Arsitektur

### 8.1 Kekuatan Arsitektur

- **Separation of concerns jelas** — 4 service terpisah (api, recorder, motion, encoder) tidak tightly coupled
- **Repository pattern** — data access layer terpisah dari business logic
- **Async FastAPI** — non-blocking, cocok untuk banyak koneksi WebSocket simultan
- **YAML config** — admin bisa edit tanpa perlu rebuild aplikasi
- **Lifespan management** — FastAPI app factory dengan proper startup/shutdown handler

### 8.2 Potensi Bottleneck

- **Motion detection 30 kamera simultan** — 30 proses OpenCV pada Intel i5 bisa heavy. Perlu diuji.
- **FFmpeg processes** — setiap kamera spawn 1 proses FFmpeg untuk record + 1 untuk HLS. Total ~60 proses FFmpeg untuk 30 kamera.
- **PostgreSQL single instance** — tidak ada replica/read replica, tapi untuk skala ini masih cukup.
- **Disk I/O contention** — 30 kamera menulis simultan ke ZFS. ZFS ARC cache membantu, tapi perlu dimonitor.

### 8.3 Inter-Service Communication

Kedua service (recorder dan motion) berjalan sebagai proses terpisah. Komunikasi antar service kemungkinan via:
- Database shared (PostgreSQL)
- File system shared (rekaman di `/mnt`, snapshots di `/var/lib/nvr_cam/`)
- Callback/event internal dalam Python (jika di-import bersama)

Perlu verifikasi apakah ada race condition antara `nvr-recorder` dan `nvr-motion` yang membaca frame yang sama dari kamera.

---

## 9. Status Bug Tracker

| Status | Jumlah |
|--------|--------|
| ✅ Fixed | 22 bug |
| ⏳ Pending | 1 bug (BUG-013 — Flutter analyze) |
| ⏭️ Skipped | 1 bug (BUG-019 — structlog dead code) |
| **Total** | **24 bug** |

Semua bug blocking sudah difix. Satu-satunya bug pending adalah BUG-013 yang hanya bisa diverifikasi di mesin dengan Flutter CLI.

---

## 10. Rekomendasi Prioritas

### Sebelum Production Deployment

1. **Ganti password default** — jangan pakai `admin / nvr1234` di server production
2. **Setup HTTPS** — pasang SSL certificate (Let's Encrypt) sebelum akses dari luar LAN
3. **Verifikasi BUG-013** — `flutter analyze` + build APK di mesin dengan Flutter CLI
4. **Test end-to-end** — tambah kamera RTSP nyata, verifikasi rekaman berjalan, alert Telegram diterima
5. **Edit `.env`** — set semua secrets (`DB_PASSWORD`, `JWT_SECRET`, `TELEGRAM_BOT_TOKEN`)

### Fitur Prioritas Tinggi (setelah deploy)

1. **D-09** — Download rekaman (kebutuhan dasar operasional)
2. **F-10** — Alert disk kritis via Telegram
3. **E-10 / E-11** — Sensitivitas motion + cooldown notifikasi (adjustable dari UI)
4. **C-11** — Toggle main/sub stream di live view
5. **A-07 atau A-08** — 2FA atau audit log (security)

---

## 11. Kesimpulan

| Aspek | Status | Catatan |
|-------|--------|----------|
| Backend code | ✅ Baik | Python import passing, 11 router, semua service ada |
| Frontend build | ✅ Baik | npm run build SUCCESS, 0 errors |
| Mobile Flutter | 🟡 Pending | Code ada, belum bisa di-build/verify |
| Deploy script | ✅ Siap | install.sh sudah difix, ready untuk Ubuntu Server |
| Security | 🟠 Perhatian | HTTP only, no 2FA, no audit log, default password public |
| Testing | 🔴 Kurang | Tidak ada CI/CD, test coverage tidak diverifikasi |
| Dokumentasi | ✅ Lengkap | FEATURES, PROGRESS, HANDOFF, Blueprint semua ada |
| Fitur production | 🟡 Cukup | Core NVR functions sudah ada, beberapa UX feature masih backlog |

**Overall: Layak untuk pilot deployment internal di jaringan LAN pabrik, dengan password diganti dan monitoring aktif. Belum direkomendasikan expose ke internet publik sebelum HTTPS dipasang.**

---

*Laporan ini dibuat berdasarkan analisis file di repo pada 22 Juli 2026. Untuk update status terkini, lihat PROGRESS.md dan FEATURES.md.*
