# HANDOFF DOCUMENT — nvr_cam
## Panduan Melanjutkan Development di Sesi Baru

**Terakhir diperbarui:** 9 Juli 2026, 08:00 WIB
**Sesi Terakhir:** #007 (Claude — Fix Native Install & Cleanup)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## Status Proyek Saat Ini

| Layer | Status | Catatan |
|-------|--------|---------|
| Backend | ✅ **SELESAI** | Python import passing, semua services & routers |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS — 0 errors |
| Mobile Flutter | 🟡 **Code Fixed** | `flutter analyze` belum diverifikasi (BUG-013) |
| Deploy Scripts | ✅ **SIAP** | `scripts/install.sh` sudah difix untuk native Ubuntu |

---

## Dokumen Referensi

| File | Isi |
|------|-----|
| `README.md` | Setup, quick start, struktur proyek |
| `PROGRESS.md` | Status lengkap — timeline sesi, daftar bug, feature backlog |
| `HANDOFF.md` | File ini — panduan singkat untuk sesi baru |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis lengkap |

---

## Deployment Native Ubuntu (Tanpa Docker)

Repo ini menggunakan **native install** via `scripts/install.sh` — **tidak perlu Docker**.

```bash
# Di server Ubuntu 24.04 (jalankan sebagai root):
git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
cd /opt/nvr_cam
sudo bash scripts/install.sh
```

Script ini otomatis:
- Install `ffmpeg`, `python3`, `postgresql`, `nginx`, `nodejs` via `apt`
- Setup virtualenv Python + install `requirements.txt`
- Buat database `nvr_cam` + user `nvr_user` di PostgreSQL
- Jalankan `alembic upgrade head`
- Build frontend React
- Register 4 systemd services (`nvr-api`, `nvr-recorder`, `nvr-motion`, `nvr-encoder`)
- Setup Nginx

### Setelah Install — Edit `.env`

```bash
nano /opt/nvr_cam/.env
```

Wajib diisi:
```env
DB_PASSWORD=password_kuat_kamu
JWT_SECRET=string_random_minimal_32_karakter
TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_CHAT_ID=chat_id_kamu
RECORDINGS_BASE_PATH=/mnt/recordings   # sesuaikan ke ZFS pool
```

### Cek Status Services

```bash
systemctl status nvr-api
systemctl status nvr-recorder
systemctl status nvr-motion
systemctl status nvr-encoder

# Lihat log real-time:
journalctl -u nvr-api -f
```

---

## Yang Masih Perlu Dilakukan

### 🟡 BUG-013 — Flutter verify (Pending)
Jalankan di mesin yang ada Flutter CLI-nya:
```bash
cd mobile
flutter analyze    # harus 0 issues
flutter build apk --release
```

### 🔲 Deploy ke Production
```bash
# Di server Ubuntu 24.04:
sudo bash scripts/install.sh

# Edit .env:
nano /opt/nvr_cam/.env

# Restart services setelah edit .env:
systemctl restart nvr-api nvr-recorder nvr-motion nvr-encoder
```

### 🔲 End-to-End Test
Setelah deploy:
- Buka `http://IP-SERVER` → login `admin / nvr1234`
- Tambah kamera RTSP dari Dahua
- Verifikasi live stream, rekaman, motion alert Telegram

### 🔲 Feature Enhancements
- FEAT-001: Export/download rekaman
- FEAT-002: Motion markers di timeline
- FEAT-003: Snapshot lightbox
- Detail: lihat `PROGRESS.md`

---

## Template untuk Sesi Baru (Copy-Paste)

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam (akses via MCP GitHub)

Progress per 9 Juli 2026, 08:00 WIB (Sesi #007 selesai):
- Backend:     ✅ SELESAI — 11 router, semua services, Python import passing
- Frontend:    ✅ SELESAI — npm run build SUCCESS (0 errors)
- Flutter:     🟡 Code fixed, flutter analyze BELUM diverifikasi (BUG-013)
- Deploy:      ✅ scripts/install.sh SIAP untuk native Ubuntu (no Docker)

Next task: [sebutkan]
```

---

## Informasi Proyek

| Item | Detail |
|---|---|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Install dir | `/opt/nvr_cam` |
| Runtime dir | `/var/lib/nvr_cam/` (HLS + snapshots) |
| Notifikasi | Telegram Bot + SMTP email |
| Login default | admin / nvr1234 |
