# Install, Operasional, Arsitektur & Security — nvr_cam

Dokumen ini menggabungkan: Panduan Instalasi, Runbook Operasional, Arsitektur, Security Review, dan Performance Review.

---

## 1. Instalasi

### 1A. Windows (Development / Demo)

**Persyaratan:** Windows 10/11, Docker Desktop berjalan.

```cmd
git clone https://github.com/silverefendy/nvr_cam
cd nvr_cam
copy .env.example .env
```

Edit `.env` — ubah `DB_PASSWORD`, `JWT_SECRET`, `ADMIN_PASSWORD`, set `APP_ENV=development`.

```cmd
docker compose up --build -d
docker exec -it cctv_api python3 scripts/setup_db.py
```

Akses: `http://localhost:3000` | Login: `admin` / password dari `.env`.

---

### 1B. Ubuntu Server (Production)

**Persyaratan:** Ubuntu 22.04 atau 24.04 LTS, min 4GB RAM, HDD rekaman sudah terpasang.

```bash
# 1. Clone repo
git clone https://github.com/silverefendy/nvr_cam /opt/nvr_cam
cd /opt/nvr_cam

# 2. Jalankan installer
sudo bash scripts/install.sh

# 3. Setup environment
sudo cp .env.example .env
sudo nano .env
# Isi: DB_PASSWORD, JWT_SECRET, ADMIN_PASSWORD, APP_ENV=production

# 4. Mount HDD rekaman
lsblk
sudo mkdir -p /mnt/hdd1
sudo mount /dev/sdb1 /mnt/hdd1
echo "/dev/sdb1 /mnt/hdd1 ext4 defaults 0 2" | sudo tee -a /etc/fstab

# 5. Edit storage.yaml
sudo nano /opt/nvr_cam/config/storage.yaml
# drives: - path: /mnt/hdd1

# 6. Start services
sudo systemctl start nvr-api
sudo systemctl enable nvr-api
cd /opt/nvr_cam && python3 scripts/setup_db.py
```

Akses: `http://<IP_SERVER>:3000`

---

### 1C. Migrasi ke Komputer Baru

**Step 1 — Backup dari komputer lama:**
- Dashboard → Settings → Backup & Restore → Download Backup
- Atau backup rekaman: `docker cp cctv_api:/mnt/driveA ./backup_recordings`

**Step 2 — Restore di komputer baru:**
1. Lakukan fresh install (1A atau 1B)
2. Dashboard → Settings → Backup & Restore → Upload file ZIP backup
3. Restart: `docker compose down && docker compose up --build -d`
4. Copy kembali folder rekaman ke path drive yang sesuai

---

## 2. Runbook Operasional

### 2A. Disk Penuh

```bash
# Identifikasi drive bermasalah
docker exec cctv_api curl -s http://localhost:8000/api/v1/storage/diagnostics \
  -H "Authorization: Bearer <TOKEN>"

# Hapus rekaman lama manual
docker exec -it cctv_api sh
find /mnt/driveA -type f -name "*.mp4" -mtime +30 -delete

# Restart recorder
docker restart cctv_api
```

### 2B. Kamera Offline

```bash
# Cek konektivitas
docker exec -it cctv_api ping -c 4 <IP_KAMERA>

# Cek RTSP manual
docker exec -it cctv_api ffprobe -v error -rtsp_transport tcp \
  -show_streams "<RTSP_URL>"

# Restart recorder kamera spesifik
curl -X POST http://localhost:8000/api/v1/cameras/<CAMERA_ID>/restart \
  -H "Authorization: Bearer <TOKEN>"

# Cek health
curl -s http://localhost:8000/api/v1/system/health \
  -H "Authorization: Bearer <TOKEN>"
```

### 2C. Restore Backup Config

```bash
# Upload backup via endpoint
curl -X POST http://localhost:8000/api/v1/config/restore \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@backup.zip"

# Validasi hasil restore
curl -s http://localhost:8000/api/v1/config/cameras \
  -H "Authorization: Bearer <TOKEN>"
docker logs --tail 200 cctv_api
```

### 2D. Reset Password Admin

```bash
docker exec -it cctv_api python - <<'PY'
import asyncio
from sqlalchemy import select
from backend.db.base import AsyncSessionLocal
from backend.db.models.user import User
from backend.core.security import hash_password

NEW_PASSWORD = "ganti-password-baru"

async def main():
    async with AsyncSessionLocal() as db:
        row = await db.execute(select(User).where(User.username == "admin"))
        user = row.scalar_one()
        user.password_hash = hash_password(NEW_PASSWORD)
        await db.commit()
        print("Password admin berhasil direset")

asyncio.run(main())
PY
```

### 2E. Service Crash

```bash
# Baca log
docker logs --tail 300 cctv_api
docker logs --tail 300 cctv_web
docker logs --tail 300 cctv_db

# Restart
docker restart cctv_api
docker restart cctv_web

# Health check setelah restart
curl -s http://localhost:8000/api/v1/system/health \
  -H "Authorization: Bearer <TOKEN>"

# Jika HLS bermasalah
docker exec -it cctv_api ls -lah /var/lib/nvr_cam/hls
```

---

## 3. Arsitektur Sistem

### Layer Architecture

```
Client Layer:    [Web Browser (React)]  [Flutter APK Android]
        |
        | HTTP/HTTPS + WebSocket
        |
API Layer:       FastAPI routers (backend/api/routers/)
                 Auth, Cameras, Stream, Recordings, Events,
                 Storage, Users, Settings, System, Discovery
        |
Service Layer:   recorder | motion | storage | encoder | notifier | health
        |
Runtime Layer:   FFmpeg processes | OpenCV analysis | HLS folders
Data Layer:      PostgreSQL 16 | ZFS storage pool | File system
Hardware Layer:  Ubuntu Server 24.04 | Intel i5 | 8x WD Purple 4TB
```

### Kekuatan Arsitektur Saat Ini
- Folder structure mapped ke business domain
- Repository pattern untuk DB access
- Recorder, motion, storage, encoder, notifier adalah service modul independen
- Frontend memisahkan API clients, pages, stores, hooks, components
- Deploy support native Ubuntu/systemd dan Docker

### Risiko Arsitektur yang Perlu Diatasi

| Prioritas | Risiko | Rekomendasi |
|-----------|--------|-------------|
| High | Transcode HEVC berjalan in-request path | Background job dengan status polling |
| High | Startup API me-launch semua service sekaligus | Pisahkan service menjadi command terpisah (systemd sudah ada) |
| Medium | Settings tersebar di `.env`, YAML, DB, `config_json` | Define single source of truth per field |
| Medium | Service singleton via import dari `backend.api.app` | Gunakan app state atau service registry |

### Service yang Direkomendasikan Ditambah
- `CameraConfigService` — RTSP URL building, credential masking, recorder restart
- `PlaybackService` — codec probe, cache lookup, remux/transcode job
- `RetentionService` — disk cleanup + DB reconciliation

---

## 4. Security Review

### Status Security (Per Sesi #017–018)

**Critical — SUDAH SELESAI:**
- ✅ Playback auth: endpoint `/recordings/{id}/play` sekarang validasi token via `get_current_user_flexible`
- ✅ Config restore auth: endpoint `/config/restore` sekarang require admin + validasi ZIP
- ✅ Production secret guard: startup gagal jika `JWT_SECRET` atau `DB_PASSWORD` masih default
- ✅ CORS: diganti dari wildcard ke env-driven allowlist

**High — Yang Masih Perlu Ditangani:**

| Issue | Risiko | Fix |
|-------|--------|-----|
| Camera credentials di RTSP URL dan `config_json` | Credential leak via DB dump atau logs | Pisahkan credential, mask di response |
| Docker backend masih root | Blast radius besar jika container breach | Tambah non-root user di Dockerfile |
| Tidak ada rate limiting di login | Brute force lebih mudah | Rate limit di app atau Nginx |
| Token di `localStorage` | XSS bisa steal token | Pertimbangkan httpOnly cookie |
| PostgreSQL port published di Compose | Port DB expose ke host network | Bind ke `127.0.0.1` atau gunakan dev profile |

### Secure Configuration Checklist

- [ ] Ganti password admin segera setelah install
- [ ] Set `JWT_SECRET` random, minimal 32 bytes entropy
- [ ] Set password PostgreSQL unik per environment
- [ ] Restrict CORS ke origin dashboard yang sebenarnya
- [ ] Letakkan NVR di belakang VPN atau HTTPS reverse proxy
- [ ] Jangan expose PostgreSQL ke luar host
- [ ] Rotate credential kamera, jangan commit ke Git

### Test Security yang Harus Ada

- Playback tanpa token → 401
- Playback dengan token invalid → 401
- Playback dengan token valid → 200/206
- Config restore tanpa token → 401
- Config restore sebagai non-admin → 403
- Config restore dengan ZIP berisi `../` → reject
- Login rate-limited setelah beberapa kali gagal
- Production startup gagal dengan JWT secret default

---

## 5. Performance Review

### Model Performance Saat Ini

- Recording: FFmpeg stream copy (CPU sangat efisien)
- Live view: HLS, HEVC stream di-transcode ke H.264 untuk browser
- Motion detection: sub-stream frame, skip frame (hemat CPU)
- Storage cleanup: periodik, hapus file lama saat free space < threshold
- Playback: remux H.264 atau transcode HEVC on demand, cache hasil

### Bottleneck Utama

| Prioritas | Bottleneck | Rekomendasi |
|-----------|------------|-------------|
| High | HEVC playback transcode di request path | Background job dengan progress polling |
| High | HLS transcode per HEVC kamera | Prefer sub-stream H.264 untuk live view; max concurrent transcode |
| High | Storage scan via recursive file walk | Gunakan DB metadata untuk stats; filesystem reconcile saat maintenance |
| Medium | Motion detection loop blocking OpenCV | Run detector di proses/thread terpisah |

### Safeguard yang Direkomendasikan

1. Tolak playback transcode baru saat CPU > threshold yang dikonfigurasi
2. Limit concurrent HEVC-to-H264 playback job
3. Prefer H.264 sub-stream untuk live view
4. Nightly pre-processing untuk recording yang sering diakses
5. Cache cleanup by size dan age
6. Pertahankan stream copy sebagai default recording

### Metrik yang Perlu Dipantau

- Active recording FFmpeg processes
- Active HLS FFmpeg processes
- Active transcode/remux jobs
- CPU load per process
- Free disk % per drive
- Recording write failures dan 0-byte cleanup count
- Playback preparation time by codec dan file size
