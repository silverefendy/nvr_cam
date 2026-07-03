# HANDOFF DOCUMENT — nvr_cam
## Panduan Melanjutkan Development di Sesi Baru

**Terakhir diperbarui:** 3 Juli 2026, 14:30 WIB
**Sesi Terakhir:** #005 (Claude — Setup CI/CD Lokal)
**Repo:** https://github.com/silverefendy/nvr_cam

---

## Status Proyek: FASE 4 — Testing Lokal & Deployment

| Layer | Status | Catatan |
|-------|--------|---------|
| Backend | ✅ **SELESAI** | Python import passing, semua services & routers |
| Frontend | ✅ **SELESAI** | `npm run build` SUCCESS — 0 errors |
| Mobile Flutter | 🟡 **Code Fixed** | `flutter analyze` belum diverifikasi (BUG-013) |
| CI/CD Lokal | ✅ **BARU** | Docker Compose dev, git hook deploy, Makefile, test script |

---

## Dokumen Penting

| File | Isi |
|------|-----|
| `README.md` | Setup, quick start, struktur proyek |
| `PROGRESS.md` | Status lengkap — timeline sesi, bug list, feature backlog |
| `HANDOFF.md` | File ini — panduan singkat untuk sesi baru |
| `DEVIN_PROMPT.md` | Prompt untuk Devin AI (update jika ada task baru) |
| `Docs/NVR_CAM_Blueprint.md` | Arsitektur teknis lengkap |

---

## CI/CD Lokal — File yang Sudah Ada (Sesi #005)

```
nvr_cam/
├── docker-compose.dev.yml       ← Stack lokal: DB + Backend + Frontend
├── Dockerfile.backend           ← Docker image backend Python
├── frontend/
│   ├── Dockerfile.frontend.dev  ← Dev server hot-reload
│   └── Dockerfile.frontend.prod ← Build production
├── Makefile                     ← Shortcut semua perintah
├── .env.example                 ← Template env vars (lengkap)
└── scripts/
    ├── local-test.sh            ← Test suite lokal (backend + frontend + flutter)
    ├── setup-local.sh           ← Setup awal dari nol (1x saja)
    └── hooks/post-receive       ← Git hook auto-deploy ke server
```

### Cara Pakai (Quick Reference)

```bash
# PERTAMA KALI — setup dari nol
bash scripts/setup-local.sh

# Sehari-hari
make dev          # jalankan stack lokal
make test         # test sebelum deploy
make deploy       # push ke server (otomatis test dulu)
make logs         # lihat log
make stop         # stop stack
```

---

## Setup Git Hook di Server (1x saja)

```bash
# Di SERVER Ubuntu:
sudo mkdir -p /opt/nvr_cam.git
sudo git init --bare /opt/nvr_cam.git
sudo cp /opt/nvr_cam/scripts/hooks/post-receive /opt/nvr_cam.git/hooks/
sudo chmod +x /opt/nvr_cam.git/hooks/post-receive

# Di PC LOKAL kamu:
git remote add server ssh://USER@IP-SERVER/opt/nvr_cam.git

# Deploy ke server (setelah ini):
make deploy
# atau manual:
git push server main
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

### 🔲 Fase 4 — End-to-End Testing
```bash
make dev           # jalankan stack lokal
make test          # verifikasi semua komponen
# Lalu test manual:
# - Buka http://localhost:5173 → login admin/cctv1234
# - Test tambah kamera RTSP
# - Test motion detection → Telegram alert
```

### 🔲 Fase 5 — Deployment Production
```bash
# Di server Ubuntu (1x install):
bash scripts/install.sh

# Setup git remote di PC lokal:
git remote add server ssh://USER@IP-SERVER/opt/nvr_cam.git

# Deploy:
make deploy
```

### 🔲 Fase 6 — Enhancement
- FEAT-001: Export/download rekaman
- FEAT-002: Motion markers di timeline
- FEAT-003: Snapshot lightbox
- Detail: lihat `PROGRESS.md`

---

## Template untuk Sesi Baru (Copy-Paste)

```
Repo nvr_cam: https://github.com/silverefendy/nvr_cam (akses via MCP GitHub)

Progress per 3 Juli 2026, 14:30 WIB (Sesi #005 selesai):
- Backend:  ✅ SELESAI
- Frontend: ✅ SELESAI (npm run build — 0 errors)
- Flutter:  🟡 Code fixed, flutter analyze BELUM diverifikasi (BUG-013)
- CI/CD:    ✅ SELESAI — docker-compose dev + Makefile + git hook deploy + local-test.sh

Cara jalankan lokal: bash scripts/setup-local.sh → make dev
Next task: [sebutkan]
```

---

## Informasi Proyek

| Item | Detail |
|---|---|
| Repo | https://github.com/silverefendy/nvr_cam |
| Server | Ubuntu Server 24.04 + Intel i5 + 8x WD Purple 4TB ZFS |
| Kamera | 30x Dahua H.265 RTSP |
| Jaringan | P2P Ubiquiti pabrik↔kantor, ZeroTier kantor↔rumah |
| Notifikasi | Telegram Bot + SMTP email |
| Login default | admin / cctv1234 |
