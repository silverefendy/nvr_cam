# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 25 Juli 2026, 17:10 WIB (Sesi #013 — Fix ganti IP kamera tidak apply)  
**Repo:** https://github.com/silverefendy/nvr_cam

> File ini mencatat semua issue/task yang sedang dikerjakan atau sudah selesai.  
> Update setiap sesi: ubah status, isi kolom Sesi + Tanggal.

---

## Legenda

| Simbol | Arti |
|--------|------|
| ✅ | Selesai dan sudah di-push ke repo |
| 🔄 | Sedang dikerjakan |
| ⏳ | Belum mulai |
| ⏭️ | Ditunda / skip untuk sekarang |
| ❌ | Dibatalkan |
| ⚠️ | Perlu verifikasi lanjut |

---

## 🐛 Bug Fixes Sesi #013 — Fix Ganti IP Kamera Tidak Apply

> **Tanggal:** 25 Juli 2026  
> **Scope:** Edit kamera (ganti IP) tidak efektif setelah save — recorder tetap pakai konfigurasi lama

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-043 | Ganti IP kamera tidak apply — recorder tetap streaming dari IP lama setelah edit & save | Dua root cause: (1) `restart_camera()` tidak ada locking → beberapa PUT berturut-turut (save 3 kamera) trigger restart concurrent untuk kamera yang sama; recorder baru start sebelum yang lama mati → konflik HLS segment → error `Invalid data found`. (2) File HLS lama (*.ts + index.m3u8) tidak dibersihkan saat restart → FFmpeg baru baca manifest stale yang referensikan segment dari RTSP sebelumnya. | ✅ Fixed |

**Fix detail (BUG-043):**
- `manager.py`: tambah `_restart_locks: dict[str, asyncio.Lock]` — per-camera lock agar `restart_camera` tidak berjalan concurrent untuk kamera yang sama. Restart kedua menunggu yang pertama selesai, lalu pakai config terbaru dari DB.
- `manager.py`: tambah `await asyncio.sleep(2)` setelah `stop()` — beri waktu FFmpeg lama release file handle sebelum recorder baru start.
- `camera_recorder.py`: tambah `_clear_hls_files()` — hapus semua `*.ts` dan `*.m3u8` di direktori HLS sebelum FFmpeg baru dijalankan. Dipanggil di awal `_run_hls_loop()`.

**Catatan:** Data di DB sudah benar sejak awal (RTSP URL sudah di-update saat PUT). Masalah murni di timing restart recorder, bukan di penyimpanan konfigurasi.

### ⚠️ Perlu Dilakukan Setelah Pull

```bash
git pull && docker compose up --build -d api
```

Verifikasi:
1. Edit kamera, ganti IP, klik Save
2. Tunggu ~10 detik
3. Cek log: `docker compose logs --tail 20 api` — harusnya ada `Restarted recording for camera cam_XX` sekali saja (bukan berkali-kali)
4. Live view harusnya tampil dari IP baru tanpa error `Invalid data found`

---

## 🐛 Fix + Fitur Sesi #012 — Adaptive Grid + Floating Window Mode

> **Tanggal:** 25 Juli 2026  
> **Scope:** Grid tidak mengisi layar penuh, tambah mode floating window

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-042 | Grid kamera tidak mengisi tinggi layar — ada ruang kosong di bawah | `CameraGrid` hanya definisikan `gridTemplateColumns`, tidak `gridTemplateRows`. Browser tidak tahu tinggi per baris → semua kamera menumpuk atas | ✅ Fix: tambah `gridTemplateRows: repeat(N, 1fr)` agar baris mengisi container penuh. Tambah `min-height: 0` agar flex children tidak overflow |

### Fitur Baru

| ID | Fitur | File | Status |
|----|-------|------|--------|
| C-14 | **Floating Window Mode** — setiap kamera tampil sebagai window yang bisa di-drag dan di-resize | `FloatingCameraLayout.tsx` (baru), `LiveView/index.tsx` | ✅ |

**Detail Floating Window Mode:**
- Setiap kamera muncul sebagai window terpisah dengan header berwarna gelap
- **Drag** window dengan menarik header (cursor move)
- **Resize** window dari sudut kanan-bawah (resize handle ⟁)
- **Minimize** window ke bar kecil (tombol `─`, restore dengan `▢`)
- Dot hijau/merah di header menunjukkan status online/offline kamera
- Window baru dimulai dari posisi tile otomatis (4 kolom), tidak tumpuk
- Toggle antara Grid Mode (⊞) dan Floating Mode (⧉) ada di toolbar
- Grid selector (1x1, 2x2, dll) hanya muncul di Grid Mode

---

## 🐛 Bug Fixes Sesi #011 — Live View + Cleanup

> **Tanggal:** 25 Juli 2026

| ID | Bug | Status |
|----|-----|--------|
| BUG-038 | Tombol grid tidak sinkron dengan jumlah kamera | ✅ Fixed |
| BUG-039 | Live View tampilan jelek — sudut rounded, background putih | ✅ Fixed |
| BUG-040 | Drag-drop kamera di grid tidak ada | ✅ Fixed |
| BUG-041 | Error tambah kamera silent fail | ✅ Fixed |

**Cleanup sesi #011:** hapus 4 script `fix_*.py` + 3 file `.md` redundan (PROGRESS, AUDIT_REPORT, SUMMARY, debug_summary)

---

## 🐛 Bug Fixes Sesi #010 — Docker Mode + UI Redesign

> **Tanggal:** 24 Juli 2026

| ID | Bug | Status |
|----|-----|--------|
| BUG-028 | `GET /api/v1/storage` → 500 | ✅ Fixed |
| BUG-029 | `system/health` data kosong di frontend | ✅ Fixed |
| BUG-030 | Tambah kamera → OSError: Read-only file system | ✅ Fixed |
| BUG-031 | Test connection selalu gagal | ✅ Fixed |
| BUG-032 | `GET /api/v1/config/system` → 403 | ⚠️ Belum diverifikasi |
| BUG-033 | `/storage/status` → 401 | ✅ Fixed |
| BUG-034 | Test connection timeout tidak informatif | ✅ Fixed |
| BUG-035 | Sidebar mojibake emoji | ✅ Fixed |
| BUG-036 | HLS 404 di nginx container | ✅ Fixed |
| BUG-037 | Zustand user null setelah refresh | ✅ Fixed |

**UI Redesign sesi #010 (tema terang):** Login, Sidebar, App.tsx, System, LiveView toolbar, CameraForm, RTSPTestButton, index.css  
**Halaman BELUM diredesign:** Storage, Playback, Events, Cameras, Users, Settings

---

## 🐛 Bug Fixes Sesi #001–#009 (Historis)

| Range | Sesi | Status |
|-------|------|--------|
| BUG-001–012 | #004 Devin | ✅ All fixed |
| BUG-013 | Flutter analyze | ⏭️ nanti |
| BUG-014–018 | #006 Cascade | ✅ All fixed |
| BUG-019 | structlog dead code | ⏭️ skip |
| BUG-020–024 | #007 Claude (install.sh) | ✅ All fixed |
| BUG-025–027 | #009 Claude (Docker bootstrap) | ✅ All fixed |

**Bug Recorder/Docker antara sesi #009–#010** (semua ✅ fixed): asyncio.Lock deadlock, config YAML vs PostgreSQL, redirect /setup paksa, BaseRepo tidak commit, Popen blocking, HLS path salah, segment_duration AttributeError, status offline palsu, password hilang saat edit, hls_temp_dir salah, useHLSPlayer race condition, HEVC tidak didukung hls.js.

---

## 🎯 Batch Status

| Batch | Fitur | Status |
|-------|-------|--------|
| Batch 1 — Live View | C-05 Fullscreen, C-06 Grid pilihan, C-07 Filter, C-08 Drag-drop, C-11 Toggle stream, C-13 PiP, C-14 Floating Mode | ✅ Selesai |
| Batch 2 — Download Rekaman | D-09 Download | ✅ Selesai |
| Batch 3 — Alert Disk | F-08, F-09, F-10 | ⏳ Belum mulai |

---

## ❓ Yang Masih Perlu Diverifikasi

| # | Item | Cara Verifikasi |
|---|------|-----------------|
| 1 | BUG-032: 403 di `/api/v1/config/system` | `SELECT username, role FROM users;` di DB |
| 2 | BUG-043: ganti IP kamera apply dengan benar | `docker compose up --build -d api`, edit kamera, cek log |
| 3 | Sesi #012 adaptive grid + floating mode | `docker compose up --build -d frontend` lalu tes kedua mode |

---

## 🔲 Backlog Umum (Belum Dijadwalkan)

### Auth & User
| ID | Issue | Status |
|----|-------|--------|
| A-06 | Ganti password sendiri | ⏳ |
| A-07 | Two-Factor Authentication | ⏭️ nanti |
| A-08 | Audit log aktivitas user | ⏳ |
| A-09 | Session timeout auto logout | ⏳ |

### Kamera
| ID | Issue | Status |
|----|-------|--------|
| B-13 | Kamera group/tag per area | ⏳ |
| B-14 | PTZ control via ONVIF | ⏳ |
| B-16 | Kamera non-RTSP (MJPEG/HTTP) | ⏳ |

### Live View
| ID | Issue | Status |
|----|-------|--------|
| C-09 | Digital zoom | ⏳ |
| C-10 | Audio live | ⏳ |
| C-12 | FPS custom per kamera | ⏳ |

### Rekaman
| ID | Issue | Status |
|----|-------|--------|
| D-10 | Motion marker di timeline | ⏳ |
| D-11 | Kliping rekaman (export X–Y menit) | ⏳ |
| D-12 | Export format lain (MKV, AVI) | ⏳ |
| D-13 | Cari rekaman by rentang tanggal | ⏳ |

### Motion Detection
| ID | Issue | Status |
|----|-------|--------|
| E-07 | Snapshot lightbox | ⏳ |
| E-08 | Export laporan CSV/PDF | ⏳ |
| E-09 | Motion masking | ⏳ |
| E-10 | Sensitivitas adjustable per kamera | ⏳ |
| E-11 | Cooldown notifikasi anti-spam | ⏳ |
| E-12 | Klip video pre/post event | ⏳ |
| E-13 | FPS adaptif saat motion | ⏳ |

### Storage (Batch 3)
| ID | Issue | Status |
|----|-------|--------|
| F-08 | Statistik storage per kamera | ⏳ |
| F-09 | Jadwal cleanup dari UI | ⏳ |
| F-10 | Alert disk kritis via Telegram | ⏳ |

### Konfigurasi & Monitoring
| ID | Issue | Status |
|----|-------|--------|
| H-09–H-12 | FPS adaptif, FPS custom, WhatsApp, Webhook | ⏳ |
| I-08–I-11 | Log viewer, Alert CPU/RAM, Grafik historis, Restart service | ⏳ |

### AV1 & Discovery
| ID | Issue | Status |
|----|-------|--------|
| J-04–J-05 | Progress encode, GPU acceleration | ⏳ |
| G-07 | Auto-add dari discovery | ⏳ |

### Deployment
| ID | Issue | Status |
|----|-------|--------|
| L-07 | HTTPS/SSL | ⏭️ nanti |
| L-08–L-09 | Health check, UFW firewall | ⏳ |

### Mobile Flutter
| ID | Issue | Status |
|----|-------|--------|
| K-06–K-10 | analyze, build APK, FCM, biometric, landscape | ⏭️ nanti |

---

## UI Redesign Sisa (Tema Terang)

| Halaman | Status |
|---------|--------|
| Storage | ⏳ |
| Playback | ⏳ |
| Events | ⏳ |
| Cameras | ⏳ |
| Users | ⏳ |
| Settings | ⏳ |

---

## Timeline Sesi Development

| No | Tanggal | Sesi | Agent | Yang Dikerjakan |
|----|---------|------|-------|-----------------|
| 1–2 | — | #001–002 | Claude | Kerangka awal, backend, frontend, Flutter |
| 3 | 2 Juli 2026 | #003 | Claude | Audit + update dokumentasi |
| 4 | 3 Juli 2026 | #004 | Devin AI | Fix BUG-001–012 |
| 5 | 8 Juli 2026 | #006 | Cascade AI | Fix BUG-014–018 |
| 6 | 9 Juli 2026 | #007 | Claude | Fix install.sh (BUG-020–024) |
| 7 | 22 Juli 2026 | #008–009 | Claude | Audit, fix BUG-025–027, Batch 1+2 |
| 8 | 24 Juli 2026 | #010 | Claude | Fix Docker runtime (BUG-028–037), UI redesign |
| 9 | 25 Juli 2026 | #011 | Claude | Fix BUG-038–041, cleanup file repo |
| 10 | 25 Juli 2026 | #012 | Claude | Fix BUG-042 (adaptive grid), fitur C-14 (Floating Mode) |
| 11 | 25 Juli 2026 | #013 | Claude | Fix BUG-043 (ganti IP kamera tidak apply — per-camera lock + clear HLS) |
