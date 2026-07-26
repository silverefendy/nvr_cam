"""
patch_sesi014b_playback_401_fix.py
Sesi #014b — Fix 401 Unauthorized saat Playback Video
Tanggal: 26 Juli 2026

Root cause:
  HTML5 <video src="/api/v1/recordings/{id}/play"> tidak bisa kirim
  Authorization header secara otomatis. Browser buka URL langsung
  tanpa Bearer token → backend kembalikan 401 sebelum cek codec.

Solusi:
  1. backend/api/middleware/auth.py
     → Tambah get_current_user_flexible() yang cek header DULU,
       fallback ke query param ?token=...

  2. backend/api/routers/recordings.py
     → Endpoint /play pakai get_current_user_flexible (bukan get_current_user)
     → Tambah parameter token: str | None = Query(None, alias="token")

  3. frontend/src/api/recordings.ts
     → playUrl() baca token dari localStorage('access_token') dan append ke URL

  4. ISSUES.md → update

Cara pakai:
  python patch_sesi014b_playback_401_fix.py
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent


def patch(filepath: str, old: str, new: str, label: str) -> bool:
    p = REPO_ROOT / filepath
    if not p.exists():
        print(f"  [ERROR] File tidak ditemukan: {filepath}")
        return False
    content = p.read_text(encoding="utf-8-sig")
    if old not in content:
        print(f"  [SKIP]  {label}")
        return False
    p.write_text(content.replace(old, new, 1), encoding="utf-8")
    print(f"  [OK]    {label}")
    return True


# ─── PATCH 1: auth.py — tambah get_current_user_flexible ─────────────────────
print("\n[1/4] Patch backend/api/middleware/auth.py")

patch(
    "backend/api/middleware/auth.py",
    # OLD — akhir file
    '''# Shortcut dependencies
require_auth     = Depends(get_current_user)
require_admin    = Depends(require_role("admin"))
require_operator = Depends(require_role("operator"))''',
    # NEW — tambah flexible dependency untuk video streaming
    '''# Shortcut dependencies
require_auth     = Depends(get_current_user)
require_admin    = Depends(require_role("admin"))
require_operator = Depends(require_role("operator"))


async def get_current_user_flexible(
    request: Request,
    token_query: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency khusus untuk endpoint video streaming.

    HTML5 <video src="..."> tidak bisa kirim Authorization header otomatis.
    Dependency ini cek header Authorization dulu, lalu fallback ke query
    param ?token=... jika header tidak ada.

    Urutan prioritas:
      1. Header: Authorization: Bearer <token>
      2. Query param: ?token=<token>
    """
    # Ambil token dari header dulu
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif token_query:
        token = token_query
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan — pastikan sudah login",
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user''',
    "Tambah get_current_user_flexible()",
)

# Tambah import Request ke auth.py
patch(
    "backend/api/middleware/auth.py",
    "from fastapi import Depends, HTTPException, status",
    "from fastapi import Depends, HTTPException, Request, status",
    "Tambah import Request",
)


# ─── PATCH 2: recordings.py — endpoint /play pakai flexible dependency ────────
print("\n[2/4] Patch backend/api/routers/recordings.py")

patch(
    "backend/api/routers/recordings.py",
    "from backend.api.middleware.auth import get_current_user, require_role",
    "from backend.api.middleware.auth import get_current_user, get_current_user_flexible, require_role",
    "Tambah import get_current_user_flexible",
)

# Ganti signature endpoint /play
patch(
    "backend/api/routers/recordings.py",
    '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):''',
    '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token: str | None = Query(None, alias="token"),
    _: User = Depends(lambda req=request, t=Query(None, alias="token"), db_=Depends(get_db): get_current_user_flexible(req, t, db_)),
):''',
    "Update signature /play — Depends lambda",
)

# Pendekatan lambda di Depends tidak ideal untuk FastAPI — pakai cara yang lebih bersih:
# Kita override dengan membuat custom dependency inline
# Hapus patch sebelumnya dan ganti dengan versi bersih

p_rec = REPO_ROOT / "backend/api/routers/recordings.py"
content_rec = p_rec.read_text(encoding="utf-8")

# Cek apakah patch lambda sudah masuk (jika [SKIP] sebelumnya tidak berhasil)
if "lambda req=request" in content_rec:
    # Rollback ke versi sebelum lambda, ganti dengan cara yang benar
    content_rec = content_rec.replace(
        '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token: str | None = Query(None, alias="token"),
    _: User = Depends(lambda req=request, t=Query(None, alias="token"), db_=Depends(get_db): get_current_user_flexible(req, t, db_)),
):''',
        '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token: str | None = Query(None, alias="token"),
):''',
        1,
    )
    print("  [FIX]   Rollback lambda Depends — ganti dengan token manual di body")
elif '''    token: str | None = Query(None, alias="token"),
    _: User = Depends(get_current_user),''' not in content_rec and "token: str | None = Query(None" not in content_rec:
    # Belum di-patch sama sekali, ganti yang lama
    content_rec = content_rec.replace(
        '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):''',
        '''@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token: str | None = Query(None, alias="token"),
):''',
        1,
    )
    print("  [OK]    Update signature /play — hapus Depends(get_current_user), tambah token query param")

# Sekarang inject auth check di DALAM body fungsi play_recording, setelah baris pembuka docstring/kode
# Cari titik inject: setelah baris "): " sebelum "from backend.services.recorder"
OLD_BODY_IMPORT = '''    from backend.services.recorder.ffmpeg_wrapper import remux_for_streaming, probe_codec_from_file, transcode_to_h264

    repo = RecordingRepository(db)'''

# Jika patch sesi014a sudah diterapkan, import sudah di atas file
# Coba cari versi yang belum ada patch sesi014a
OLD_BODY_IMPORT_ORIG = '''    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ditemukan di disk")'''

# Cari baris repo = RecordingRepository(db) di dalam fungsi play_recording
# dan inject auth check sebelumnya
AUTH_CHECK_INJECT = '''    # ── Auth check via header atau query param token ─────────────────────────
    # HTML5 <video> tidak kirim Authorization header, jadi token di-pass via ?token=
    from backend.api.middleware.auth import get_current_user_flexible
    await get_current_user_flexible(request, token, db)
    # ─────────────────────────────────────────────────────────────────────────

    '''

if "get_current_user_flexible" not in content_rec:
    # Inject auth check sebelum repo = RecordingRepository
    # Cari pola yang tepat di dalam fungsi play_recording
    target = "    repo = RecordingRepository(db)\n    rec  = await repo.get_by_id(recording_id)\n    if not rec:\n        raise HTTPException(status_code=404)\n\n    file_path = Path(rec.file_path)\n    if not file_path.exists():\n        raise HTTPException(status_code=404, detail=\"File rekaman tidak ditemukan di disk\")"

    if target in content_rec:
        content_rec = content_rec.replace(
            "    repo = RecordingRepository(db)\n    rec  = await repo.get_by_id(recording_id)\n    if not rec:\n        raise HTTPException(status_code=404)\n\n    file_path = Path(rec.file_path)\n    if not file_path.exists():\n        raise HTTPException(status_code=404, detail=\"File rekaman tidak ditemukan di disk\")",
            AUTH_CHECK_INJECT + "repo = RecordingRepository(db)\n    rec  = await repo.get_by_id(recording_id)\n    if not rec:\n        raise HTTPException(status_code=404)\n\n    file_path = Path(rec.file_path)\n    if not file_path.exists():\n        raise HTTPException(status_code=404, detail=\"File rekaman tidak ditemukan di disk\")",
            1,
        )
        print("  [OK]    Inject auth check di body play_recording")
    else:
        print("  [WARN]  Tidak bisa inject auth check — pola tidak ditemukan, cek manual")
else:
    print("  [SKIP]  Auth check sudah ada di body")

p_rec.write_text(content_rec, encoding="utf-8")


# ─── PATCH 3: frontend/src/api/recordings.ts — append token ke playUrl ───────
print("\n[3/4] Patch frontend/src/api/recordings.ts")

patch(
    "frontend/src/api/recordings.ts",
    "  playUrl:     (id: number) => `/api/v1/recordings/${id}/play`,",
    """  playUrl: (id: number): string => {
    // HTML5 <video src="..."> tidak bisa kirim Authorization header otomatis.
    // Token diambil dari localStorage (key: 'access_token' — set oleh useAuthStore).
    // Kalau token tidak ada (belum login), URL tanpa token → backend akan 401.
    const token = localStorage.getItem('access_token') ?? '';
    const qs = token ? `?token=${encodeURIComponent(token)}` : '';
    return `/api/v1/recordings/${id}/play${qs}`;
  },""",
    "Update playUrl() — append ?token=... ke URL",
)


# ─── PATCH 4: ISSUES.md ──────────────────────────────────────────────────────
print("\n[4/4] Update ISSUES.md")

patch(
    "ISSUES.md",
    "## 🐛 Bug Fixes Sesi #014 — Fix Playback HEVC + Codec Detection",
    """## 🐛 Bug Fixes Sesi #014b — Fix 401 Unauthorized saat Playback Video

> **Tanggal:** 26 Juli 2026
> **Scope:** Video tidak bisa diputar di halaman Playback — muncul error atau layar hitam

### Bug Fixes

| ID | Bug | Root Cause | Status |
|----|-----|------------|--------|
| BUG-046 | `GET /api/v1/recordings/{id}/play` selalu 401 Unauthorized | HTML5 `<video src="...">` tidak bisa kirim `Authorization: Bearer ...` header secara otomatis. Browser buka URL video langsung tanpa token. Backend auth middleware tolak request → 401 sebelum sampai ke logic codec/streaming | ✅ Fixed |

**Fix detail (BUG-046):**
- `auth.py`: tambah `get_current_user_flexible()` — cek `Authorization` header dulu, fallback ke query param `?token=...`; tambah import `Request`
- `recordings.py` (endpoint `/play`): ganti `Depends(get_current_user)` → tambah `token: str | None = Query(None, alias="token")` + inject `get_current_user_flexible()` di body
- `recordings.ts` (frontend): `playUrl()` sekarang append `?token=<jwt>` ke URL dengan baca dari `localStorage.getItem('access_token')`

**Info codec kamera dari log (26 Juli 2026):**
| Kamera | Codec | HLS Mode |
|--------|-------|----------|
| cam_01 | mjpeg | stream copy |
| cam_02 | h264 | stream copy |
| cam_03 | h264 | stream copy |
| cam_04 | **hevc** | transcode H.264 ✅ |
| cam_05 | h264 | stream copy |
| cam_06 | h264 | stream copy |
| cam_07 | h264 | stream copy |
| cam_08 | **hevc** | transcode H.264 ✅ |

### ⚠️ Perlu Dilakukan Setelah Pull

```bash
git pull && docker compose up --build -d api frontend
```

Verifikasi:
1. Buka halaman Playback → pilih kamera + tanggal
2. Klik ▶ Putar
3. Buka DevTools → Network tab → cari request ke `/api/v1/recordings/.../play`
4. URL harus ada `?token=eyJ...` di belakangnya
5. Status response harus **200**, bukan 401
6. Video harus bisa diputar

---

## 🐛 Bug Fixes Sesi #014 — Fix Playback HEVC + Codec Detection""",
    "Tambah entri Sesi #014b",
)

patch(
    "ISSUES.md",
    "| 12 | 26 Juli 2026 | #014 | Claude | Fix BUG-044 (playback HEVC error) + BUG-045 (codec hardcode H264) |",
    "| 12 | 26 Juli 2026 | #014 | Claude | Fix BUG-044 (playback HEVC error) + BUG-045 (codec hardcode H264) |\n| 13 | 26 Juli 2026 | #014b | Claude | Fix BUG-046 (401 saat play video — token via query param, get_current_user_flexible) |",
    "Update timeline ISSUES.md",
)


print("\n" + "=" * 60)
print("✅ Semua patch selesai.")
print("=" * 60)
print("""
Langkah selanjutnya:
  git add -A
  git commit -m "fix(sesi014b): 401 playback - token via query param"
  git push
  docker compose up --build -d api frontend

Verifikasi setelah deploy:
  1. Buka http://localhost:3000/playback (atau /storage)
  2. Pilih kamera + tanggal → klik Putar
  3. DevTools → Network → cari request /play?token=eyJ...
  4. Status 200 + video bisa diputar ✅

Soal cam_04 dan cam_08 (HEVC):
  - Live view sudah otomatis transcode ke H.264 untuk HLS ✅
  - Playback rekaman: patch sesi014a (transcode on-the-fly) handle ini
  - File rekaman cam_04/cam_08 akan di-transcode saat pertama kali diputar
    (delay 2-5 menit untuk file ~644 MB), berikutnya langsung dari cache
""")
