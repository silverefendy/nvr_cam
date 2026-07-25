# HANDOFF DOCUMENT — nvr_cam
## Panduan Melanjutkan Development di Sesi Baru

**Terakhir diperbarui:** 25 Juli 2026, 09:45 WIB  
**Sesi Terakhir:** #011 (Claude — Fix Live View Grid, Drag-Drop, Error Form, Cleanup Repo)  
**Repo:** https://github.com/silverefendy/nvr_cam

---

## ⚡ MULAI CEPAT — Jika Token Habis / Ganti Claude Baru

Copy-paste ke Claude baru:

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam
Akses via MCP GitHub. Baca file-file ini sebelum mulai:
1. HANDOFF.md   → status proyek + panduan ini
2. ISSUES.md    → semua bug + issue + backlog

Progress per 25 Juli 2026, 09:45 WIB (Sesi #011 selesai):
- Backend:     ✅ SELESAI
- Frontend:    ✅ SELESAI (perlu `docker compose up --build -d frontend` untuk apply fix terbaru)
- Flutter:     🟡 Code ada, flutter analyze belum diverifikasi
- Deploy:      ✅ scripts/install.sh siap untuk native Ubuntu
- Docker mode: ✅ Sudah bisa jalan (Live View berfungsi, HEVC auto-transcode)
- Live View:   ✅ Grid selector, fullscreen, PiP, toggle stream, drag-drop, filter kamera

Stack: FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
Server: Ubuntu Server 24.04, Intel i5, 8x WD Purple 4TB ZFS
Kamera: 30x Dahua H.265 RTSP

Next task: [sebutkan apa yang mau dikerjakan]
```

---

## Status Proyek Saat Ini

| Layer | Status | Catatan |
|-------|--------|---------|
| Backend | ✅ **SELESAI** | 11 router, semua services, Python import passing |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS — fix terbaru perlu rebuild Docker |
| Mobile Flutter | 🟡 **Code Ada** | `flutter analyze` belum diverifikasi |
| Deploy Scripts | ✅ **SIAP** | `scripts/install.sh` untuk native Ubuntu |
| Docker Dev Mode | ✅ **BERJALAN** | Live View sudah tampil, HEVC auto-transcode ke H.264 |

---

## Yang Baru Selesai di Sesi #011

| Fix | File | Keterangan |
|-----|------|------------|
| BUG-038 | `store/cameras.ts` | Tombol grid sekarang auto-expand/trim `selectedCameras` |
| BUG-039 | `LiveView/index.tsx`, `VideoPlayer.tsx`, `CameraGrid.tsx` | Full dark theme, no border-radius, gap 2px |
| BUG-040 | `CameraGrid.tsx`, `store/cameras.ts` | Drag-drop HTML5 native, swap posisi kamera |
| BUG-041 | `CameraForm.tsx` | Error banner merah + validasi client-side |
| Cleanup | root + `docs/` | 4 file `fix_*.py`, 3 file `.md` redundan dihapus |

**Perlu dilakukan setelah pull:**
```bash
git pull && docker compose up --build -d frontend
```

---

## Dokumen Referensi (Setelah Cleanup)

| File | Isi | Kapan Dibaca |
|------|-----|--------------|
| `HANDOFF.md` | File ini — panduan cepat + template | Selalu, pertama kali |
| `ISSUES.md` | Semua bug historis + issue aktif + backlog | Saat cek history, mau fix bug, atau tambah fitur |
| `FEATURES.md` | Daftar lengkap 130 fitur + status | Saat mau cek/tambah fitur spesifik |
| `README.md` | Setup, quick start, struktur proyek | Saat setup awal |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis lengkap | Saat perlu pahami desain sistem |

---

## Deployment

### Native Ubuntu (Production)
```bash
git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
cd /opt/nvr_cam
sudo bash scripts/install.sh
nano /opt/nvr_cam/.env   # isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN, dll
systemctl status nvr-api nvr-recorder nvr-motion nvr-encoder
```

### Docker Dev Mode (Development)
```bash
docker compose up --build -d
# Akses: http://localhost:3000 (frontend), http://localhost:8000 (API)
```

### Service Names
| Konteks | Format |
|---------|--------|
| `docker compose` commands | `api`, `frontend`, `db` |
| `docker exec` / `docker logs` | `cctv_api`, `cctv_web`, `cctv_db` |
| Native systemd (production) | `nvr-api`, `nvr-recorder`, `nvr-motion`, `nvr-encoder` |

---

## Next Steps yang Direkomendasikan

| Prioritas | Task | ID |
|-----------|------|----|
| 🔴 Tinggi | Rebuild frontend untuk apply Fix 13–16 | — |
| 🔴 Tinggi | Verifikasi BUG-032: 403 di `/api/v1/config/system` | BUG-032 |
| 🟠 Sedang | UI redesign 6 halaman sisa ke tema terang | ISSUES.md bagian UI |
| 🟠 Sedang | Batch 3 — Alert disk kritis via Telegram | F-10 |
| 🟡 Rendah | Snapshot lightbox (klik foto → modal besar) | E-07 |

---

## Informasi Proyek

| Item | Detail |
|------|--------|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Install dir (native) | `/opt/nvr_cam` |
| Runtime dir (native) | `/var/lib/nvr_cam/` (HLS + snapshots) |
| Volume Docker (dev) | `hls_data` → `/var/lib/nvr_cam/hls`, `snapshot_data` |
| Notifikasi | Telegram Bot + SMTP email |
| Login default | `admin / nvr1234` (**ganti sebelum production!**) |
