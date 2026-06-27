# HANDOFF DOCUMENT — CCTV NVR System
## Untuk melanjutkan development di sesi Claude baru

---

## Status Kerangka: SELESAI (Framework Ready)

Kerangka aplikasi sudah dibuat lengkap di `/home/claude/cctv-system/` atau di GitHub repo.
Semua file sudah ada strukturnya. Yang perlu dilakukan selanjutnya adalah **mengisi implementasi** (TODO).

---

## Yang Sudah Ada (Completed)

### Backend (Python/FastAPI)
- `backend/core/config.py` — Settings dari .env via Pydantic
- `backend/core/security.py` — JWT, bcrypt, token generation
- `backend/core/logging.py` — JSON logger terpusat
- `backend/core/exceptions.py` — Custom exception classes
- `backend/db/base.py` — SQLAlchemy async engine
- `backend/db/models/` — User, Camera, Recording, MotionEvent, SystemLog, NotificationLog
- `backend/db/repositories/` — CameraRepo, RecordingRepo, EventRepo, UserRepo (dengan BaseRepository)
- `backend/api/app.py` — FastAPI app factory
- `backend/api/middleware/auth.py` — JWT dependency + role-based access
- `backend/api/schemas/` — Pydantic schemas untuk semua endpoint
- `backend/api/routers/` — auth, cameras, stream, recordings, events, storage, users, settings, system
- `backend/services/recorder/ffmpeg_wrapper.py` — Semua command FFmpeg
- `backend/services/recorder/camera_recorder.py` — 1 instance per kamera + auto-reconnect
- `backend/services/recorder/manager.py` — RecordingManager singleton
- `backend/services/motion/detector.py` — OpenCV background subtraction per zona
- `backend/services/storage/manager.py` — Circular delete + monitoring
- `backend/services/notifier/telegram.py` — Kirim pesan dan foto ke Telegram
- `backend/services/encoder/av1_encoder.py` — Re-encode ke AV1

### Frontend (React/TypeScript)
- `frontend/src/types/index.ts` — Semua TypeScript interfaces
- `frontend/src/api/` — client.ts, auth.ts, cameras.ts, recordings.ts, events.ts, system.ts
- `frontend/src/store/auth.ts` — Zustand auth store + role checking
- `frontend/src/store/cameras.ts` — Zustand camera + grid store
- `frontend/src/hooks/useHLSPlayer.ts` — HLS.js integration
- `frontend/src/hooks/useWebSocket.ts` — Real-time WebSocket
- `frontend/src/components/camera/VideoPlayer.tsx` — HLS video player component
- `frontend/src/components/camera/CameraGrid.tsx` — Responsive grid layout
- `frontend/src/components/layout/Sidebar.tsx` — Navigasi + role filter
- `frontend/src/pages/Login/` — Form login
- `frontend/src/pages/LiveView/` — Grid semua kamera live
- `frontend/src/pages/Playback/` — Player rekaman dengan date picker
- `frontend/src/App.tsx` — Router + protected routes

### Config & Scripts
- `.env.example` — Template environment variables
- `config/cameras.yaml` — Template konfigurasi kamera
- `config/system.yaml` — Parameter sistem
- `config/storage.yaml` — Mapping drive ke kamera
- `scripts/install.sh` — Installer otomatis 1 perintah
- `scripts/update.sh` — Update dari GitHub
- `scripts/nginx/cctv.conf` — Nginx reverse proxy
- `scripts/systemd/*.service` — 4 service files

---

## Yang Belum Ada (TODO — Perlu Diimplementasi)

### Backend Priority 1 (Core)
1. `backend/db/migrations/` — Alembic migration files (jalankan `alembic revision --autogenerate`)
2. `backend/services/recorder/manager.py` — Koneksi ke DB untuk load cameras saat startup
3. `backend/api/app.py` — Lifespan: start RecordingManager, StorageManager saat boot
4. `backend/api/routers/system.py` — WebSocket broadcast actual events
5. `backend/api/routers/storage.py` — Implementasi get_storage_status() baca dari disk nyata
6. `backend/services/motion/detector.py` — Integrasi dengan EventRepository (simpan ke DB)
7. `backend/services/notifier/telegram.py` — Dipanggil dari motion detector
8. `scripts/setup_db.py` — Script inisialisasi user admin pertama

### Backend Priority 2
9. `backend/services/encoder/scheduler.py` — Cron job AV1 encode malam hari
10. `backend/api/routers/cameras.py` — inject status online/offline dari RecordingManager
11. `backend/utils/health.py` — System health check (CPU, RAM, disk, service status)
12. `backend/tests/` — Unit dan integration tests

### Frontend Priority 1
13. `src/pages/Events/index.tsx` — List motion events + filter + snapshot preview
14. `src/pages/Cameras/index.tsx` — CRUD kamera + test koneksi RTSP
15. `src/pages/Storage/index.tsx` — Grafik kapasitas per drive
16. `src/pages/Settings/index.tsx` — Form pengaturan sistem
17. `src/pages/Users/index.tsx` — Manajemen user + role
18. `src/pages/System/index.tsx` — Dashboard monitoring CPU/RAM/disk

### Frontend Priority 2
19. Motion markers di Playback timeline
20. Real-time motion badge overlay di VideoPlayer (via WebSocket)
21. Fullscreen mode untuk VideoPlayer
22. Drag-drop reorder kamera di CameraGrid

### Mobile (Flutter) — Fase Terakhir
23. `mobile/lib/` — Semua screen Flutter (live view, playback, events)

---

## Cara Melanjutkan di Claude Baru

Paste teks berikut di awal sesi Claude baru:

```
Saya sedang membangun aplikasi NVR CCTV custom.
Kerangka sudah selesai di GitHub: https://github.com/USERNAME/cctv-system

Stack: Python FastAPI + PostgreSQL + FFmpeg + OpenCV (backend), React TypeScript Tailwind (frontend).

Yang perlu dilanjutkan: [sebutkan item TODO yang mau dikerjakan]

Struktur yang sudah ada:
- backend/api/routers/ — semua router sudah ada dengan TODO di implementasi
- backend/services/ — recorder, motion, storage, notifier, encoder sudah ada kerangkanya
- frontend/src/ — types, api, store, hooks, components, pages sudah ada kerangkanya

Tolong implementasikan: [nama file / fitur yang mau dikerjakan]
```

---

## Urutan Pengerjaan yang Disarankan

| Prioritas | Task | Estimasi |
|---|---|---|
| 1 | Alembic migration + setup DB | 1 hari |
| 2 | RecordingManager startup di lifespan | 1 hari |
| 3 | Storage status endpoint (baca disk nyata) | 0.5 hari |
| 4 | Motion → simpan DB → kirim Telegram | 2 hari |
| 5 | WebSocket broadcast ke frontend | 1 hari |
| 6 | Frontend: Events, Cameras, Storage pages | 3 hari |
| 7 | Frontend: Settings, Users, System pages | 2 hari |
| 8 | Frontend: motion markers di playback | 1 hari |
| 9 | AV1 encoder scheduler | 1 hari |
| 10 | Flutter APK Android | 2 minggu |

---

## Environment Setup untuk Developer Baru

```bash
# Clone repo
git clone https://github.com/USERNAME/cctv-system
cd cctv-system

# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# Edit .env: isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN

# Database (butuh PostgreSQL running)
alembic upgrade head

# Jalankan API dev mode
python backend/main.py

# Frontend
cd frontend && npm install && npm run dev
# Buka http://localhost:5173
```

---

## Kontak Informasi Proyek

- **Topologi:** Pabrik (30 kamera Dahua) → P2P Ubiquiti → Kantor → P2P Ubiquiti → Rumah
- **Remote:** ZeroTier di Mikrotik kantor + ZeroTier di rumah
- **Server:** Ubuntu Server 24.04 + Intel i5 + 8x HDD WD Purple 4TB (ZFS)
- **Codec:** H.265 dari kamera, re-encode AV1 saat idle malam
- **Notifikasi:** Telegram Bot (gratis)
- **Referensi awal:** github.com/silverefendy/nvr_cam (dikembangkan jauh lebih lengkap)