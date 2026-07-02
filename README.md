# nvr_cam — Custom NVR Recording Application

> Sistem NVR custom berbasis Python + React untuk 30 kamera Dahua/ONVIF.
> Tanpa lisensi channel, scalable, dan 100% open source.

## Quick Start

```bash
# Di server Ubuntu — 1 perintah install semua
curl -fsSL https://raw.githubusercontent.com/silverefendy/nvr_cam/main/scripts/install.sh | sudo bash
```

## Akses Setelah Install

- **Web Dashboard:** `http://IP-SERVER` (dari jaringan lokal)
- **Login default:** `admin` / `cctv1234`
- **API Docs:** `http://IP-SERVER/api/docs`

## Update Aplikasi

```bash
cd /opt/nvr_cam && sudo bash scripts/update.sh
```

## Struktur Proyek

```
nvr_cam/
├── backend/          ← Python (FastAPI, FFmpeg, OpenCV)
│   ├── api/          ← REST API endpoints + WebSocket
│   ├── core/         ← Config, security, logging, exceptions
│   ├── db/           ← Models (SQLAlchemy) + Repositories + Migrations (Alembic)
│   ├── services/     ← recorder, motion, storage, encoder, notifier, auth, discovery, health
│   └── utils/        ← health.py, setup_db.py
├── frontend/         ← React + TypeScript + Tailwind
│   └── src/
│       ├── api/      ← API client functions
│       ├── components/ ← UI components (VideoPlayer, CameraGrid, Sidebar)
│       ├── pages/    ← Login, LiveView, Playback, Events, Cameras, Storage, Settings, Users, System
│       ├── store/    ← Zustand state management
│       └── hooks/    ← useHLSPlayer, useWebSocket
├── mobile/           ← Flutter (Android APK) — screens implemented, build issues pending
│   └── lib/
│       ├── screens/  ← login, home, camera_view, playback, events, settings, splash
│       ├── models/   ← Dart data models
│       └── services/ ← API service layer
├── config/           ← cameras.yaml, system.yaml, storage.yaml
├── scripts/          ← install.sh, update.sh, nginx, systemd
└── Docs/             ← NVR_CAM_Blueprint.md (arsitektur lengkap)
```

## Tech Stack

| Layer | Teknologi |
|---|---|
| OS | Ubuntu Server 24.04 LTS |
| Filesystem | ZFS (kompresi LZ4 + dedup) |
| Video engine | FFmpeg (record + HLS) |
| Motion detect | OpenCV |
| Backend | Python 3.12 + FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 + Alembic migrations |
| Frontend | React 18 + TypeScript + Tailwind + Vite |
| Mobile | Flutter 3 (screens done, build fixes pending) |
| Notifikasi | Telegram Bot API + Email SMTP |
| Remote access | ZeroTier (kantor ↔ rumah) |
| Process mgr | systemd |

## Services

```bash
systemctl status nvr-api        # FastAPI backend
systemctl status nvr-recorder   # FFmpeg recording engine
systemctl status nvr-motion     # OpenCV motion detection
systemctl status nvr-encoder    # AV1 idle re-encoder
```

## Konfigurasi

Edit file-file berikut sesuai setup:
- `/opt/nvr_cam/.env` — secrets (DB password, JWT, Telegram token)
- `/opt/nvr_cam/config/cameras.yaml` — daftar dan RTSP URL semua kamera
- `/opt/nvr_cam/config/storage.yaml` — mapping kamera ke drive HDD
- `/opt/nvr_cam/config/system.yaml` — threshold, jadwal, parameter sistem

## Environment Setup (Developer)

```bash
# Clone repo
git clone https://github.com/silverefendy/nvr_cam
cd nvr_cam

# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# Edit .env: isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN

# Database
alembic upgrade head

# Jalankan API dev mode
python backend/main.py

# Frontend
cd frontend && npm install && npm run dev
# Buka http://localhost:5173
```

## Progress & Handoff

Lihat **[PROGRESS.md](PROGRESS.md)** untuk status implementasi terkini dan panduan melanjutkan development.
