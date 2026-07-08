# HANDOFF DOCUMENT — nvr_cam
## Panduan Melanjutkan Development di Sesi Baru

**Terakhir diperbarui:** 9 Juli 2026, 09:00 WIB
**Sesi Terakhir:** #007 (Claude — Fix Native Install & Cleanup + FEATURES.md)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## ⚡ MULAI CEPAT — Jika Token Habis / Ganti Claude Baru

Jika sesi Claude sebelumnya terputus atau token habis, copy-paste teks ini ke Claude baru:

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam
Akses repo via MCP GitHub (tool: github:get_file_contents, dll).

Tolong baca file-file ini secara berurutan sebelum mulai:
1. HANDOFF.md       → status proyek + panduan ini
2. PROGRESS.md      → timeline sesi, daftar bug lengkap
3. FEATURES.md      → daftar lengkap semua fitur (sudah ada + backlog)

Progress per 9 Juli 2026, 09:00 WIB (Sesi #007 selesai):
- Backend:     ✅ SELESAI — 11 router, semua services, Python import passing
- Frontend:    ✅ SELESAI — npm run build SUCCESS (0 errors)
- Flutter:     🟡 Code fixed, flutter analyze BELUM diverifikasi (BUG-013)
- Deploy:      ✅ scripts/install.sh SIAP untuk native Ubuntu (no Docker)
- Fitur:       79/123 fitur selesai (64%) — lihat FEATURES.md untuk detail

Stack: FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
Server: Ubuntu Server 24.04, Intel i5, 8x WD Purple 4TB ZFS
Kamera: 30x Dahua H.265 RTSP

Next task: [sebutkan apa yang mau dikerjakan]
```

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

| File | Isi | Kapan Dibaca |
|------|-----|--------------|
| `HANDOFF.md` | File ini — panduan singkat & template sesi baru | Selalu, pertama kali |
| `PROGRESS.md` | Timeline sesi, daftar bug lengkap, next steps | Saat mau cek history atau bug |
| `FEATURES.md` | Laporan lengkap semua fitur + backlog prioritas | Saat mau tambah / cek fitur |
| `README.md` | Setup, quick start, struktur proyek | Saat setup awal |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis lengkap | Saat perlu pahami desain sistem |

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
systemctl status nvr-api nvr-recorder nvr-motion nvr-encoder

# Log real-time:
journalctl -u nvr-api -f
journalctl -u nvr-recorder -f
```

---

## Yang Masih Perlu Dilakukan

### 🟡 BUG-013 — Flutter verify (Pending)
```bash
cd mobile
flutter analyze    # harus 0 issues
flutter build apk --release
```

### 🔲 Deploy ke Production
```bash
sudo bash scripts/install.sh
nano /opt/nvr_cam/.env
systemctl restart nvr-api nvr-recorder nvr-motion nvr-encoder
```
Buka `http://IP-SERVER` → login `admin / nvr1234`

### 🔲 Feature Priorities
Lihat `FEATURES.md` bagian "Backlog Prioritas Tinggi" untuk daftar lengkap.
Ringkasan 3 teratas:
- **D-09** — Download rekaman ke lokal
- **E-07** — Snapshot lightbox (klik foto jadi besar)
- **E-10 / E-11** — Sensitivitas motion + cooldown notifikasi

---

## Panduan Update Dokumen Saat Ada Fitur Baru

Setiap sesi yang menambah / menyelesaikan fitur, update **kedua file ini**:

| File | Yang Diupdate |
|------|--------------|
| `FEATURES.md` | Status fitur ✅, nomor sesi, statistik total |
| `PROGRESS.md` | Timeline sesi baru, next steps |
| `HANDOFF.md` | Tanggal + sesi terakhir, template copy-paste |

---

## Informasi Proyek

| Item | Detail |
|------|--------|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Install dir | `/opt/nvr_cam` |
| Runtime dir | `/var/lib/nvr_cam/` (HLS + snapshots) |
| Notifikasi | Telegram Bot + SMTP email |
| Login default | `admin / nvr1234` |
| Progress fitur | 79/123 (64%) — detail di `FEATURES.md` |
