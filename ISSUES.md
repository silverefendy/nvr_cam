# ISSUES — nvr_cam
## Issue Tracker & Status Penyelesaian

**Dibuat:** 22 Juli 2026  
**Diperbarui:** 26 Juli 2026, 21:30 WIB (Sesi #016 — Sort & Filter halaman Cameras + LiveView)  
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

## 🎨 Fitur Sesi #016 — Sort & Filter Halaman Cameras + LiveView

> **Tanggal:** 26 Juli 2026, 21:30 WIB  
> **Scope:** UI improvement — tabel Cameras bisa di-sort per kolom & di-filter, panel filter LiveView juga mendapat sort

### Fitur Baru

| ID | Fitur | File | Status |
|----|-------|------|--------|
| C-15 | Sort tabel Cameras per kolom (ID, Name, Location, Status, Storage, Motion, Retention) — klik header toggle asc/desc, ada ikon ↑↓ | `Cameras/index.tsx` | ✅ Done |
| C-16 | Filter bar di halaman Cameras — search teks (ID/Name/Location) + dropdown filter Status (All/Online/Offline) | `Cameras/index.tsx` | ✅ Done |
| C-17 | Sort kamera di panel filter LiveView — tombol sort by Name, Location, Status (online dulu / offline dulu) | `LiveView/index.tsx` | ✅ Done |

**Detail implementasi:**
- `Cameras/index.tsx`: tambah state `sortKey`, `sortDir`, `filterStatus`, `filterSearch`. Header kolom jadi clickable dengan ikon sort. Filter bar muncul di bawah header page (search input + dropdown status). Data diproses: filter dulu → sort. Tidak ada perubahan ke backend.
- `LiveView/index.tsx`: di panel filter (showFilter), tambah row tombol sort di atas chip kamera. Sort state: `sortBy` ('name' | 'location' | 'status') + `sortDir` ('asc' | 'desc'). Chip kamera diurutkan sesuai pilihan.

**Catatan:** Ini murni client-side sort/filter — tidak ada request tambah ke API.

### Cara Apply

```powershell
# Jalankan perintah ini di PowerShell (C:\github\silverefendy\nvr_cam\)
git pull
```

Lalu copy-paste isi file dari script PS1 yang akan Claude berikan, atau run:

```powershell
cd frontend
npm run build
```

Verifikasi:
1. Buka halaman **Cameras** → klik header kolom "Name" → harus sort A-Z, klik lagi → Z-A
2. Coba filter "Pos" di search box → hanya tampil kamera yang ada kata "Pos"
3. Dropdown status "Offline" → hanya tampil kamera offline
4. Buka **Live View** → klik tombol Filter → coba tombol sort "Name" / "Status"

---

## 🐛 Bug Fixes Sesi #015 — Fix Playback File >100MB, File 0MB, Cleanup Duplikasi

> **Tanggal:** 26 Juli 2026, 20:30 WIB  
> **Scope:** Playback file besar gagal, file 0MB menumpuk di storage, duplikasi fungsi di ffmpeg_wrapper.py

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-047 | Playback file >100MB error "No video with supported format and MIME type found" | Fungsi `probe_codec_from_file()` dan `transcode_to_h264()` sudah dibuat di sesi #014 di `ffmpeg_wrapper.py`, tapi **tidak pernah dipanggil** di endpoint `/play`. Endpoint masih pakai logic lama (hanya cek faststart). File kecil <100MB kebetulan H.264 sehingga bisa jalan. File besar kemungkinan HEVC — tidak di-transcode — langsung error di browser. | ✅ Fixed |
| BUG-048 | File 0MB menumpuk di storage dan muncul di list rekaman | FFmpeg crash/timeout sebelum sempat write data → file .mp4 dibuat tapi ukurannya 0 byte. Tidak ada mekanisme cleanup. File ini tetap muncul di DB dan UI tapi tidak bisa diputar. | ✅ Fixed |
| BUG-049 | `ffmpeg_wrapper.py` ada duplikasi fungsi `probe_codec_from_file()` dan `transcode_to_h264()` (masing-masing definisi 2x) | Sisa dari sesi #014 — fungsi ditambahkan dua kali tanpa disadari. Python pakai definisi terakhir, tidak error, tapi code jadi tidak bersih dan membingungkan. | ✅ Fixed |
| BUG-050 | `remux_for_streaming()` timeout terlalu pendek (60 detik) untuk file H.264 besar | File H.264 >500MB bisa makan waktu >60 detik saat remux. Timeout habis → fungsi return `False` → file tidak di-serve dengan benar. | ✅ Fixed (timeout naik ke 300 detik) |

**Fix detail:**
- `recordings.py` (`/play` endpoint): Sekarang **probe codec dulu** sebelum serve. Pipeline baru:
  1. Cek cache → serve dari cache jika ada
  2. Probe codec file via `probe_codec_from_file()`
  3. HEVC → `transcode_to_h264()` (cache di `/tmp/nvr_remux/rec_{id}_h264.mp4`)
  4. H.264 bukan faststart → `remux_for_streaming()` (cache di `/tmp/nvr_remux/rec_{id}.mp4`)
  5. H.264 + faststart → serve langsung
  6. File 0MB → return HTTP 422 dengan pesan error jelas
- `recordings.py` (list endpoint): Filter rekaman dengan `file_size_mb = 0` dari response — tidak muncul di UI
- `camera_recorder.py`: Tambah `_cleanup_empty_files()` — hapus file MP4 <1KB dari disk **sebelum** `_save_recording_to_db()` dipanggil. Dipanggil setelah setiap segment FFmpeg selesai.
- `camera_recorder.py` (`_save_recording_to_db`): Probe codec aktual via `probe_codec_from_file()` — simpan `"H265"` atau `"H264"` ke DB sesuai isi file
- `ffmpeg_wrapper.py`: Hapus duplikasi fungsi (2x `probe_codec_from_file` dan 2x `transcode_to_h264`). Timeout `remux_for_streaming` naik dari 60s ke 300s. Timeout `transcode_to_h264` naik dari 600s ke 1200s untuk file sangat besar.

**Klarifikasi — Setting H.265 di Aplikasi:**
> Tidak ada setting H.265 di aplikasi NVR ini karena **by design** — konfigurasi codec H.265 ada di **kamera Dahua langsung** (buka web UI kamera: `http://<IP_kamera>` → Setting → Camera → Video → Encode). Aplikasi NVR hanya terima stream RTSP dari kamera dan otomatis deteksi codecnya via `probe_codec_from_file()`.

### ⚠️ Perlu Dilakukan Setelah Pull

```bash
git pull && docker compose up --build -d api
```

---

## 🐛 Bug Fixes Sesi #014b — Fix 401 Unauthorized saat Playback Video

> **Tanggal:** 26 Juli 2026  
> **Scope:** Video tidak bisa diputar di halaman Playback — muncul error atau layar hitam

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-046 | `GET /api/v1/recordings/{id}/play` selalu 401 Unauthorized | HTML5 `<video src="...">` tidak bisa kirim `Authorization: Bearer ...` header secara otomatis. Browser buka URL video langsung tanpa token. Backend auth middleware tolak request → 401 sebelum sampai ke logic codec/streaming | ✅ Fixed |

---

## 🐛 Bug Fixes Sesi #014 — Fix Playback HEVC + Codec Detection

> **Tanggal:** 26 Juli 2026  
> **Scope:** Playback rekaman gagal dengan error "No video with supported format and MIME type found"

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-044 | Playback rekaman error "No video with supported format and MIME type found" | Dua kemungkinan: (1) File rekaman bercodec HEVC/H.265 — browser Chrome/Firefox tidak support HEVC di HTML5 `<video>` natively. (2) File lama tanpa `-movflags +faststart` (moov atom di akhir). Backend tidak mendeteksi codec aktual sebelum serve — langsung stream file mentah ke browser. | ✅ Fixed |
| BUG-045 | Kolom `codec` di DB selalu isi "H264" meskipun kamera rekam HEVC | `_save_recording_to_db()` hardcode `codec="H264"` tanpa probe file aktual | ✅ Fixed |

---

## 🐛 Bug Fixes Sesi #013 — Fix Ganti IP Kamera Tidak Apply

> **Tanggal:** 25 Juli 2026

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-043 | Ganti IP kamera tidak apply | Dua root cause: (1) `restart_camera()` tidak ada locking → restart concurrent; (2) File HLS lama tidak dibersihkan saat restart | ✅ Fixed |

---

## 🐛 Fix + Fitur Sesi #012 — Adaptive Grid + Floating Window Mode

> **Tanggal:** 25 Juli 2026

| ID | Bug/Fitur | Status |
|----|-----------|--------|
| BUG-042 | Grid kamera tidak mengisi tinggi layar | ✅ Fixed |
| C-14 | Floating Window Mode (drag, resize, minimize) | ✅ Done |

---

## 🐛 Bug Fixes Sesi #011 — Live View + Cleanup

> **Tanggal:** 25 Juli 2026

| ID | Bug | Status |
|----|-----|--------|
| BUG-038 | Tombol grid tidak sinkron dengan jumlah kamera | ✅ Fixed |
| BUG-039 | Live View tampilan jelek | ✅ Fixed |
| BUG-040 | Drag-drop kamera di grid tidak ada | ✅ Fixed |
| BUG-041 | Error tambah kamera silent fail | ✅ Fixed |

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
| Batch 2b — Cameras Sort+Filter | C-15 Sort tabel, C-16 Filter tabel, C-17 Sort LiveView filter | ✅ Selesai |
| Batch 3 — Alert Disk | F-08, F-09, F-10 | ⏳ Belum mulai |

---

## ❓ Yang Masih Perlu Diverifikasi

| # | Item | Cara Verifikasi |
|---|------|----------------|
| 1 | BUG-032: 403 di `/api/v1/config/system` | `SELECT username, role FROM users;` di DB |
| 2 | BUG-047: Playback file >100MB bisa diputar setelah fix sesi #015 | `docker compose up --build -d api`, buka Playback, klik file >100MB |
| 3 | BUG-048: File 0MB sudah tidak muncul di UI | Buka halaman Playback, pastikan semua item punya ukuran file valid |
| 4 | C-15/C-16: Sort & filter tabel Cameras | Klik header kolom Name → sort. Ketik "Pos" di search → filter |
| 5 | C-17: Sort kamera di LiveView filter panel | Buka LiveView → Filter → coba tombol sort Name/Status |
| 6 | BUG-051: Live View tidak crop di semua grid/floating mode | Jalankan `scripts/apply_frontend_s017.ps1`, buka Live View 2x2 dan 4x4, pastikan video `contain` dengan area hitam |
| 7 | BUG-052: Kamera baru langsung terpetakan ke storage + recorder | Tambah kamera baru, cek `GET /api/v1/storage/diagnostics` dan pastikan `camera_drive_map` terisi |
| 8 | BUG-053: HLS retry dan status loading tampil saat stream belum ready | Restart stream kamera, buka Live View, pastikan muncul "Menghubungkan... (mencoba ulang)" sebelum video tampil |
| 9 | A-06: Profile + ganti password + reset password admin | Coba `/profile`, ganti password sendiri, lalu reset password user lain dari halaman Users |

---

## Update Sesi #017 — 26 Juli 2026

| ID | Bug/Fitur | Status |
|----|-----------|--------|
| BUG-051 | Live View video ter-crop karena `object-fit: cover` | ✅ Backend/frontend patch script siap |
| BUG-052 | Storage mapping/recording tidak sinkron setelah tambah kamera baru | ✅ Fixed |
| BUG-053 | Kamera online tapi Live View hitam saat HLS belum ready / FFmpeg error | ✅ Backend fixed + frontend patch script siap |
| A-06 | Profile user + ganti password sendiri + reset password oleh admin | ✅ Backend fixed + frontend patch script siap |
| A-08 | Audit log aktivitas admin/user | ✅ Fixed |
| O-01 | Storage diagnostics endpoint | ✅ Done |
| O-02 | Request ID + structured logging + richer health surface | ✅ Done |
| O-03 | Async playback transcode queue + cache lifecycle management | ✅ Done |

## 🔲 Backlog Umum (Belum Dijadwalkan)

### Auth & User
| ID | Issue | Status |
|----|-------|--------|
| A-06 | Ganti password sendiri / profile / reset password admin | ✅ |
| A-07 | Two-Factor Authentication | ⏭️ nanti |
| A-08 | Audit log aktivitas user | ✅ |
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
| 12 | 26 Juli 2026 | #014 | Claude | Fix BUG-044 (playback HEVC error) + BUG-045 (codec hardcode H264) |
| 13 | 26 Juli 2026 | #014b | Claude | Fix BUG-046 (401 saat play video — token via query param, get_current_user_flexible) |
| 14 | 26 Juli 2026 | #015 | Claude | Fix BUG-047 (playback >100MB HEVC tidak di-transcode), BUG-048 (file 0MB), BUG-049 (duplikasi fungsi ffmpeg_wrapper), BUG-050 (timeout remux terlalu pendek) |
| 15 | 26 Juli 2026 | #016 | Claude | Fitur C-15 (sort tabel Cameras), C-16 (filter tabel Cameras), C-17 (sort kamera di LiveView filter panel) |
