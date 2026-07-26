# RUNBOOKS — nvr_cam

Terakhir diperbarui: Minggu, 26 Juli 2026

## 1) Disk penuh

### Identifikasi drive bermasalah

```bash
docker exec cctv_api curl -s http://localhost:8000/api/v1/storage/diagnostics -H "Authorization: Bearer <TOKEN>"
docker exec cctv_api python - <<'PY'
from pathlib import Path
import shutil
for path in [Path('/mnt/driveA')]:
    if path.exists():
        total, used, free = shutil.disk_usage(path)
        print(path, 'free_gb=', round(free / 1024**3, 2))
PY
```

### Hapus rekaman lama manual

```bash
docker exec -it cctv_api sh
find /mnt/driveA -type f -name "*.mp4" | head
find /mnt/driveA -type f -name "*.mp4" -mtime +30 -delete
```

### Restart recorder

```bash
docker restart cctv_api
docker logs -f cctv_api
```

## 2) Kamera offline

### Cek konektivitas dasar

```bash
docker exec -it cctv_api ping -c 4 <IP_KAMERA>
```

### Cek RTSP manual via ffprobe

```bash
docker exec -it cctv_api ffprobe -v error -rtsp_transport tcp -show_streams "<RTSP_URL>"
```

### Restart recorder kamera spesifik

```bash
curl -X POST http://localhost:8000/api/v1/cameras/<CAMERA_ID>/restart \
  -H "Authorization: Bearer <TOKEN>"
```

### Cek health dan error terakhir

```bash
curl -s http://localhost:8000/api/v1/system/health \
  -H "Authorization: Bearer <TOKEN>"
```

## 3) Restore backup

### Upload backup via endpoint

```bash
curl -X POST http://localhost:8000/api/v1/config/restore \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@backup.zip"
```

### Validasi hasil restore

```bash
curl -s http://localhost:8000/api/v1/config/cameras -H "Authorization: Bearer <TOKEN>"
curl -s http://localhost:8000/api/v1/storage/diagnostics -H "Authorization: Bearer <TOKEN>"
docker logs --tail 200 cctv_api
```

## 4) Reset password admin

Karena `scripts/setup_db.py` sekarang ikut di-copy ke image backend, reset manual bisa dilakukan dari container.

### Opsi cepat via Python langsung

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

### Opsi via script setup DB

```bash
docker exec -it cctv_api python scripts/setup_db.py
```

## 5) Service crash

### Baca log

```bash
docker logs --tail 300 cctv_api
docker logs --tail 300 cctv_web
docker logs --tail 300 cctv_db
```

### Restart container

```bash
docker restart cctv_api
docker restart cctv_web
docker restart cctv_db
```

### Cek health setelah restart

```bash
curl -s http://localhost:8000/api/v1/system/health \
  -H "Authorization: Bearer <TOKEN>"
```

### Jika recorder/HLS bermasalah

```bash
curl -s http://localhost:8000/api/v1/storage/diagnostics \
  -H "Authorization: Bearer <TOKEN>"
docker exec -it cctv_api ls -lah /var/lib/nvr_cam/hls
```
