# DEVIN PROMPT — Bug Fix Session #006
## nvr_cam — Fix 6 Bug Kritis Sebelum Deployment

**Dibuat:** 8 Juli 2026, 21:00 WIB
**Untuk:** Devin AI (sesi #006)
**Prioritas:** Semua bug di dokumen ini HARUS difix sebelum apapun lainnya.

---

## KONTEKS PROYEK

- **Repo:** https://github.com/silverefendy/nvr_cam
- **Stack:** FastAPI (Python 3.12) + PostgreSQL 16 + React/Vite (TypeScript) + Flutter
- **Deployment:** Docker Compose (dev: `docker-compose.dev.yml`, prod: `docker-compose.yml`)
- **Entry point backend:** `backend/api/app.py` → `app` object
- **Cara jalan dev:** `make dev` atau `docker compose -f docker-compose.dev.yml up`

---

## ATURAN WAJIB UNTUK DEVIN

> ⚠️ Baca dan ikuti aturan ini sebelum mengubah satu baris pun.

1. **Hanya ubah file yang disebutkan secara eksplisit** di setiap task di bawah. Jangan refactor file lain.
2. **Jangan ubah logic bisnis** — hanya perbaiki bug struktural/konfigurasi yang disebutkan.
3. **Setelah semua fix selesai**, jalankan verifikasi yang tertulis di bagian "VERIFIKASI AKHIR".
4. **Commit terpisah per bug** dengan format: `fix: BUG-0XX — <deskripsi singkat>`
5. **Jangan install dependency baru** kecuali disebutkan eksplisit.
6. **Jangan ubah** `requirements.txt`, `package.json`, `pubspec.yaml` kecuali BUG yang menyebutkannya.

---

## DAFTAR BUG YANG HARUS DIFIX

### BUG-014 🔴 KRITIS — `backend/Dockerfile` CMD Salah (Duplikat File)

**File:** `backend/Dockerfile`

**Masalah:**
File ini adalah sisa lama yang CMD-nya salah:
```
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
`main:app` tidak valid — ASGI app ada di `backend.api.app:app`, bukan `main:app`.
File ini juga duplikat dari `Dockerfile.backend` di root yang sudah benar.

**Yang harus dilakukan:**
Hapus file `backend/Dockerfile` seluruhnya.

```bash
# Verifikasi file yang BENAR ada di root:
cat Dockerfile.backend
# Pastikan CMD-nya: alembic upgrade head && uvicorn backend.api.app:app ...
```

**Commit:** `fix: BUG-014 — hapus backend/Dockerfile yang CMD-nya salah (duplikat)`

---

### BUG-015 🔴 KRITIS — `docker-compose.yml` Prod Pakai Dockerfile yang Salah

**File:** `docker-compose.yml`

**Masalah:**
Service `api` di `docker-compose.yml` (production) saat ini:
```yaml
services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile      # ← INI SALAH (pakai backend/Dockerfile yang sudah dihapus di BUG-014)
```

**Yang harus dilakukan:**
Ubah bagian `build` service `api` menjadi:
```yaml
services:
  api:
    build:
      context: .                   # ← ubah: context ke root repo
      dockerfile: Dockerfile.backend   # ← ubah: pakai Dockerfile.backend di root
```

**Jangan ubah bagian lain** dari `docker-compose.yml` (volumes, ports, healthcheck, dll tetap sama).

**Commit:** `fix: BUG-015 — docker-compose.yml prod pakai Dockerfile.backend yang benar`

---

### BUG-016 🔴 KRITIS — `AsyncSessionLocal.close_all()` Tidak Ada di SQLAlchemy

**File:** `backend/api/app.py`

**Masalah:**
Di fungsi `lifespan()`, bagian shutdown memanggil:
```python
await AsyncSessionLocal.close_all()   # ← METHOD INI TIDAK ADA di SQLAlchemy async_sessionmaker
```
Ini akan menghasilkan `AttributeError` setiap kali aplikasi shutdown (Ctrl+C, container stop, dll).

**Yang harus dilakukan:**
Cari baris ini di `backend/api/app.py`:
```python
        # Close DB connections
        await AsyncSessionLocal.close_all()
        logger.info("Database connections closed")
```

Ganti dengan:
```python
        # Close DB connections
        from backend.db.base import engine
        await engine.dispose()
        logger.info("Database connections closed")
```

**Jangan ubah bagian lain** dari `lifespan()` atau `create_app()`.

**Commit:** `fix: BUG-016 — ganti AsyncSessionLocal.close_all() dengan engine.dispose()`

---

### BUG-017 🔴 KRITIS — `alembic.ini` URL Masih Placeholder

**File:** `backend/alembic.ini`

**Masalah:**
Baris ini masih berisi nilai placeholder:
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```
Meskipun `backend/db/migrations/env.py` sudah meng-override URL ini dari `settings.db_url`,
placeholder ini menyebabkan kebingungan dan bisa menyebabkan error jika Alembic dijalankan
di luar context Docker (misalnya saat CI/CD atau manual migration check).

**Yang harus dilakukan:**
Di file `backend/alembic.ini`, cari baris:
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Ganti dengan:
```ini
# URL dioverride secara dinamis di backend/db/migrations/env.py dari environment variable.
# Nilai di bawah adalah fallback default (development lokal tanpa Docker).
sqlalchemy.url = postgresql+asyncpg://nvr_user:devpassword123@localhost:5432/nvr_cam
```

**Jangan ubah baris lain** di `alembic.ini`.

**Commit:** `fix: BUG-017 — alembic.ini URL diganti dari placeholder ke default yang valid`

---

### BUG-018 🟠 TINGGI — Default DB Name/User Tidak Sinkron

**File:** `backend/core/config.py`

**Masalah:**
Default value di `Settings` class tidak sinkron dengan `.env.example`:

| Setting | `config.py` (SALAH) | `.env.example` (BENAR) |
|---------|---------------------|------------------------|
| `db_name` | `"cctv_db"` | `"nvr_cam"` |
| `db_user` | `"cctv_user"` | `"nvr_user"` |
| `db_password` | `"changeme"` | (tidak ada default) |

Jika `.env` tidak ada atau tidak lengkap, backend akan mencoba konek ke database `cctv_db` dengan user `cctv_user` yang tidak pernah dibuat di Docker Compose.

**Yang harus dilakukan:**
Di file `backend/core/config.py`, ubah default value di class `Settings`:

Cari:
```python
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "cctv_db"
    db_user: str = "cctv_user"
    db_password: str = "changeme"
```

Ganti dengan:
```python
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nvr_cam"
    db_user: str = "nvr_user"
    db_password: str = "devpassword123"
```

**Jangan ubah** field lain di class `Settings`.

**Commit:** `fix: BUG-018 — sinkronkan default db_name dan db_user di config.py`

---

### BUG-019 🟠 TINGGI — `backend/core/logger.py` Dead Code (Tidak Pernah Dipakai)

**File:** `backend/core/logger.py`

**Masalah:**
Ada dua file logging di `backend/core/`:
- `backend/core/logging.py` — dipakai oleh `app.py` dan semua service (`from backend.core.logging import get_logger`)
- `backend/core/logger.py` — **tidak pernah diimport di manapun**, pakai `structlog` yang berbeda

File `logger.py` adalah dead code yang menyebabkan kebingungan dan `structlog` masuk ke `requirements.txt` tanpa alasan jelas.

**Yang harus dilakukan:**

**Langkah 1:** Hapus file `backend/core/logger.py` seluruhnya.

**Langkah 2:** Di `backend/requirements.txt`, hapus baris:
```
structlog==24.4.0
```
(Pastikan dulu `structlog` tidak diimport di file lain selain `logger.py` yang dihapus. Grep seluruh folder `backend/` untuk `import structlog` atau `from structlog`.)

**Commit:** `fix: BUG-019 — hapus logger.py dead code dan dependency structlog yang tidak dipakai`

---

## VERIFIKASI AKHIR

Setelah semua 6 bug difix, jalankan verifikasi berikut dan **pastikan semua PASS** sebelum push:

### 1. Cek file yang harusnya sudah tidak ada
```bash
# Kedua file ini harus sudah TIDAK ADA:
[ ! -f backend/Dockerfile ] && echo "✅ backend/Dockerfile sudah dihapus" || echo "❌ MASIH ADA!"
[ ! -f backend/core/logger.py ] && echo "✅ backend/core/logger.py sudah dihapus" || echo "❌ MASIH ADA!"
```

### 2. Cek docker-compose.yml
```bash
grep -A3 "build:" docker-compose.yml
# Output harus mengandung:
#   context: .
#   dockerfile: Dockerfile.backend
```

### 3. Cek app.py tidak ada close_all()
```bash
grep "close_all" backend/api/app.py
# Output harus KOSONG (tidak ada baris yang mengandung close_all)
```

### 4. Cek app.py ada engine.dispose()
```bash
grep "engine.dispose" backend/api/app.py
# Output harus ada 1 baris
```

### 5. Cek alembic.ini tidak ada placeholder
```bash
grep "driver://user:pass" backend/alembic.ini
# Output harus KOSONG
```

### 6. Cek config.py default yang benar
```bash
grep "nvr_cam\|nvr_user" backend/core/config.py
# Output harus ada 2 baris (db_name dan db_user)
```

### 7. Cek structlog tidak ada di requirements
```bash
grep "structlog" backend/requirements.txt
# Output harus KOSONG
```

### 8. Cek tidak ada import structlog di kode lain
```bash
grep -r "structlog" backend/ --include="*.py"
# Output harus KOSONG
```

### 9. Python import test
```bash
cd /path/to/nvr_cam
python -c "from backend.api.app import app; print('✅ Import OK')"
# Output harus: ✅ Import OK
```

---

## YANG TIDAK BOLEH DILAKUKAN

- ❌ Jangan ubah logic di `lifespan()` selain baris `close_all()` → `engine.dispose()`
- ❌ Jangan ubah struktur router, model, schema, atau service
- ❌ Jangan ubah `docker-compose.dev.yml` (sudah benar, tidak perlu disentuh)
- ❌ Jangan ubah `Dockerfile.backend` (sudah benar)
- ❌ Jangan tambah atau hapus dependency selain `structlog` di `requirements.txt`
- ❌ Jangan ubah `frontend/` atau `mobile/` — bug ini semua di backend/infra
- ❌ Jangan buat file baru kecuali dibutuhkan untuk fix

---

## SETELAH SEMUA FIX SELESAI

Update `PROGRESS.md` di repo:
- Tandai BUG-013 s/d BUG-019 sebagai ✅ Fixed
- Tambah baris sesi #006 di tabel Timeline
- Update template "Sesi Baru" dengan status terkini
