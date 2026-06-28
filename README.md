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
│   ├── api/          ← REST API endpoints
│   ├── core/         ← Config, security, logging, exceptions
│   ├── db/           ← Models (SQLAlchemy) + Repositories
│   └── services/     ← recorder, motion, storage, encoder, notifier
├── frontend/         ← React + TypeScript + Tailwind
│   └── src/
│       ├── api/      ← API client functions
│       ├── components/ ← UI components
│       ├── pages/    ← Halaman aplikasi
│       ├── store/    ← Zustand state management
│       └── hooks/    ← Custom React hooks
├── mobile/           ← Flutter APK Android (TODO)
├── config/           ← cameras.yaml, system.yaml, storage.yaml
└── scripts/          ← install.sh, update.sh, nginx, systemd
```

## Tech Stack

| Layer | Teknologi |
|---|---|
| OS | Ubuntu Server 24.04 LTS |
| Filesystem | ZFS (kompresi LZ4 + dedup) |
| Video engine | FFmpeg (record + HLS) |
| Motion detect | OpenCV |
| Backend | Python 3.12 + FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 |
| Frontend | React 18 + TypeScript + Tailwind + Vite |
| Mobile | Flutter 3 (TODO) |
| Notifikasi | Telegram Bot API |
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
