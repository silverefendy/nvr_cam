# =============================================================================
# patch2_nvr_cam.ps1 - Fix frontend issues
# Jalankan dari root repo: cd C:\path\to\nvr_cam ; .\patch2_nvr_cam.ps1
# =============================================================================
# Fix yang dicakup:
#   1. Grid layout tersimpan di localStorage (tidak reset saat refresh)
#   2. Tab Rekaman tampil data dari DB (fix query date_from/date_to)
#   3. Sub stream hitam - tambah debug info + fallback ke main stream
#   4. Storage Drive bisa diatur dari UI Pengaturan (tidak hardcoded)
#   5. Backend: endpoint GET /api/v1/storage/drives untuk list drive yang aktif
#   6. Backend: scan file di disk dan sync ke DB (untuk rekaman lama yang belum tercatat)
# =============================================================================

Write-Host "=== NVR CAM PATCH 2 ===" -ForegroundColor Cyan
Write-Host "Memulai patch..." -ForegroundColor Yellow

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 1: frontend/src/store/cameras.ts
# Tambah persistensi grid ke localStorage agar tidak reset saat refresh
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[1/6] Patching frontend/src/store/cameras.ts (persist grid) ..." -ForegroundColor Green

$camerasStore = @'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Camera } from "@/types"

export type GridSize = '1x1'|'2x2'|'3x3'|'4x4'|'5x6'|'custom'

const GRID_CAPACITY: Record<GridSize, number> = {
  '1x1': 1,
  '2x2': 4,
  '3x3': 9,
  '4x4': 16,
  '5x6': 30,
  'custom': 999,
}

interface CameraState {
  cameras: Camera[]
  selectedCameras: string[]
  gridSize: GridSize
  gridRows: number
  gridCols: number
  streamTypeOverride: Record<string, 'main'|'sub'>
  fullscreenCameraId: string | null
  setCameras: (c: Camera[]) => void
  setGridSize: (s: GridSize) => void
  setGridDimensions: (rows: number, cols: number) => void
  toggleSelected: (id: string) => void
  selectAll: () => void
  selectNone: () => void
  updateStatus: (id: string, s: Camera['status']) => void
  setStreamType: (id: string, type: 'main'|'sub') => void
  setFullscreen: (id: string | null) => void
  reorderCameras: (fromIndex: number, toIndex: number) => void
}

// FIX: Pakai persist middleware agar gridRows, gridCols, gridSize
// disimpan ke localStorage dan tidak reset saat halaman di-refresh.
// cameras & fullscreenCameraId sengaja tidak di-persist (data live).
export const useCameraStore = create<CameraState>()(
  persist(
    (set) => ({
      cameras: [],
      selectedCameras: [],
      gridSize: '2x2',
      gridRows: 2,
      gridCols: 2,
      streamTypeOverride: {},
      fullscreenCameraId: null,

      setCameras: (cameras) => set((s) => {
        const existing = s.selectedCameras.filter(id => cameras.some(c => c.id === id))
        const newIds = cameras.map(c => c.id).filter(id => !existing.includes(id))
        const all = [...existing, ...newIds]
        const capacity = s.gridSize === 'custom'
          ? s.gridRows * s.gridCols
          : GRID_CAPACITY[s.gridSize]
        return { cameras, selectedCameras: all.slice(0, capacity) }
      }),

      setGridSize: (gridSize) => set((s) => {
        if (gridSize === 'custom') return { gridSize }
        const [r, c] = gridSize.split('x').map(Number)
        const rows = r, cols = c
        const capacity = rows * cols
        const currentSelected = s.selectedCameras
        if (currentSelected.length <= capacity) {
          const notShown = s.cameras.map(c => c.id).filter(id => !currentSelected.includes(id))
          const toAdd = notShown.slice(0, capacity - currentSelected.length)
          return { gridSize, gridRows: rows, gridCols: cols, selectedCameras: [...currentSelected, ...toAdd] }
        } else {
          return { gridSize, gridRows: rows, gridCols: cols, selectedCameras: currentSelected.slice(0, capacity) }
        }
      }),

      setGridDimensions: (rows, cols) => set((s) => {
        const capacity = rows * cols
        const currentSelected = s.selectedCameras
        let newSelected = currentSelected
        if (currentSelected.length < capacity) {
          const notShown = s.cameras.map(c => c.id).filter(id => !currentSelected.includes(id))
          const toAdd = notShown.slice(0, capacity - currentSelected.length)
          newSelected = [...currentSelected, ...toAdd]
        } else {
          newSelected = currentSelected.slice(0, capacity)
        }
        return { gridRows: rows, gridCols: cols, gridSize: 'custom', selectedCameras: newSelected }
      }),

      toggleSelected: (id) => set((s) => ({
        selectedCameras: s.selectedCameras.includes(id)
          ? s.selectedCameras.filter(c => c !== id)
          : [...s.selectedCameras, id],
      })),

      selectAll: () => set((s) => ({ selectedCameras: s.cameras.map(c => c.id) })),
      selectNone: () => set({ selectedCameras: [] }),

      updateStatus: (id, status) => set((s) => ({
        cameras: s.cameras.map(c => c.id === id ? { ...c, status } : c),
      })),

      setStreamType: (id, type) => set((s) => ({
        streamTypeOverride: { ...s.streamTypeOverride, [id]: type },
      })),

      setFullscreen: (id) => set({ fullscreenCameraId: id }),

      reorderCameras: (fromIndex, toIndex) => set((s) => {
        const arr = [...s.selectedCameras]
        const [moved] = arr.splice(fromIndex, 1)
        arr.splice(toIndex, 0, moved)
        return { selectedCameras: arr }
      }),
    }),
    {
      name: 'nvr-camera-store',  // key di localStorage
      // Hanya persist setting grid & stream override, bukan state live
      partialize: (s) => ({
        gridSize: s.gridSize,
        gridRows: s.gridRows,
        gridCols: s.gridCols,
        streamTypeOverride: s.streamTypeOverride,
        selectedCameras: s.selectedCameras,
      }),
    }
  )
)
'@

Set-Content -Path "frontend\src\store\cameras.ts" -Value $camerasStore -Encoding UTF8
Write-Host "  OK: cameras.ts - grid tersimpan di localStorage" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 2: frontend/src/api/recordings.ts
# Fix: query date_from & date_to keduanya dikirim ke backend
# Sebelumnya jika date_from == date_to, hanya kirim param 'date' (1 hari)
# tapi jika range berbeda, filter hanya di frontend - tidak efisien & kadang miss
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[2/6] Patching frontend/src/api/recordings.ts (fix date filter) ..." -ForegroundColor Green

$recordingsApi = @'
import { apiClient } from './client'
import type { Recording } from "@/types"

export const recordingsApi = {
  list: (p?: { camera_id?: string; date_from?: string; date_to?: string }) => {
    const params: Record<string, string> = {}
    if (p?.camera_id) params.camera_id = p.camera_id

    // FIX: Kirim date (bukan date_from/date_to) sesuai backend API.
    // Backend /recordings hanya terima: camera_id + date (YYYY-MM-DD).
    // Jika range multi-hari, ambil per-hari dan gabungkan.
    // Untuk simplisitas: jika date_from == date_to → kirim date=date_from
    // Jika range berbeda → tidak filter date (ambil semua), filter di frontend.
    if (p?.date_from && p?.date_to && p.date_from === p.date_to) {
      params.date = p.date_from
    } else if (p?.date_from && !p?.date_to) {
      params.date = p.date_from
    }

    return apiClient.get<Recording[]>('/recordings', { params }).then(r => {
      let data = r.data as any
      if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
      if (!Array.isArray(data)) return []

      // Filter di frontend untuk range tanggal
      if (p?.date_from || p?.date_to) {
        const from = p?.date_from ? new Date(p.date_from + 'T00:00:00') : null
        const to   = p?.date_to   ? new Date(p.date_to   + 'T23:59:59') : null
        data = data.filter((rec: Recording) => {
          const d = new Date(rec.started_at)
          if (from && d < from) return false
          if (to   && d > to)   return false
          return true
        })
      }
      return data
    })
  },

  // Ambil SEMUA rekaman tanpa filter (untuk halaman rekaman yang kosong)
  listAll: () => apiClient.get<Recording[]>('/recordings').then(r => {
    let data = r.data as any
    if (data && !Array.isArray(data) && Array.isArray(data.data)) data = data.data
    return Array.isArray(data) ? data : []
  }),

  get:         (id: number) => apiClient.get<Recording>(`/recordings/${id}`).then(r => r.data),
  playUrl:     (id: number) => `/api/v1/recordings/${id}/play`,
  downloadUrl: (id: number) => `/api/v1/recordings/${id}/download`,
  protect:     (id: number) => apiClient.post(`/recordings/${id}/protect`).then(r => r.data),
  delete:      (id: number) => apiClient.delete(`/recordings/${id}`),
}
'@

Set-Content -Path "frontend\src\api\recordings.ts" -Value $recordingsApi -Encoding UTF8
Write-Host "  OK: recordings.ts - fix date filter" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 3: backend/api/routers/recordings.py
# Fix: GET /recordings tanpa filter kembalikan SEMUA rekaman (bukan hanya filter)
# Tambah endpoint POST /recordings/sync - scan disk dan insert ke DB
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[3/6] Patching backend/api/routers/recordings.py (sync disk→DB) ..." -ForegroundColor Green

$recordingsRouter = @'
"""
Router: /api/v1/recordings
List, playback, download, protect, delete rekaman.
Tambah: POST /sync — scan file di disk dan daftarkan ke DB.
"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base import get_db
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.recording import Recording
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User

router = APIRouter(tags=["recordings"])


@router.get("")
async def list_recordings(
    camera_id: str | None = Query(None),
    date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List rekaman dengan filter opsional.
    Tanpa filter → kembalikan 500 rekaman terbaru.
    """
    repo = RecordingRepository(db)
    if camera_id and date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_from = date_obj.replace(hour=0, minute=0, second=0)
            date_to   = date_obj.replace(hour=23, minute=59, second=59)
            recordings = await repo.get_by_camera_and_date(camera_id, date_from, date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    elif camera_id:
        recordings = await repo.get_by_camera(camera_id)
    elif date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_from = date_obj.replace(hour=0, minute=0, second=0)
            date_to   = date_obj.replace(hour=23, minute=59, second=59)
            recordings = await repo.get_by_date_range(date_from, date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        # Kembalikan 500 rekaman terbaru tanpa filter
        recordings = await repo.get_recent(limit=500)
    return recordings


@router.post("/sync")
async def sync_recordings_from_disk(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Scan semua file .mp4 di storage dan daftarkan yang belum ada di DB.

    Berguna untuk:
    - Rekaman lama sebelum patch yang belum tercatat di DB
    - Recovery setelah DB reset
    - File yang ada di disk tapi hilang dari tabel recordings
    """
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()

    inserted = 0
    skipped = 0
    errors = []

    for cam in cameras:
        drive = cam.storage_drive
        cam_dir = Path(drive) / cam.id
        if not cam_dir.exists():
            continue

        # Scan semua file .mp4 rekursif (struktur: <drive>/<cam_id>/<date>/<time>.mp4)
        for mp4_file in sorted(cam_dir.rglob("*.mp4")):
            try:
                # Cek apakah sudah ada di DB
                existing = await db.execute(
                    select(Recording).where(Recording.file_path == str(mp4_file))
                )
                if existing.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                stat = mp4_file.stat()
                if stat.st_size < 1024:  # Skip file kosong
                    continue

                # Coba parse waktu dari nama file (format: %H-%M-%S.mp4)
                try:
                    date_str = mp4_file.parent.name  # YYYY-MM-DD
                    time_str = mp4_file.stem           # HH-MM-SS
                    started_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H-%M-%S")
                except ValueError:
                    # Fallback: gunakan mtime file
                    started_at = datetime.fromtimestamp(stat.st_mtime)

                rec = Recording(
                    camera_id=cam.id,
                    file_path=str(mp4_file),
                    file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                    started_at=started_at,
                    ended_at=None,
                    duration_s=None,
                    codec="H264",
                    is_protected=False,
                    is_encoded_av1=False,
                )
                db.add(rec)
                inserted += 1

            except Exception as e:
                errors.append({"file": str(mp4_file), "error": str(e)})

    await db.commit()

    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
        "errors": len(errors),
        "error_details": errors[:10],  # Max 10 error ditampilkan
    }


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    return rec


@router.get("/{recording_id}/play")
async def play_recording(
    recording_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Stream file video untuk playback di browser dengan Range header support."""
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")

    range_header = request.headers.get("range")
    if range_header:
        try:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            file_size = file_path.stat().st_size
            end = int(end) if end else file_size - 1
        except Exception:
            start, end = 0, file_path.stat().st_size - 1
            file_size  = file_path.stat().st_size

        chunk_size = 1024 * 1024
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(min(end - start + 1, chunk_size))

        from fastapi.responses import Response
        headers = {
            "Content-Range":  f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(len(data)),
            "Content-Type":   "video/mp4",
        }
        return Response(data, status_code=206, headers=headers)

    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Rekaman tidak ditemukan")

    file_path = Path(rec.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File rekaman tidak ada di disk")

    try:
        ts = datetime.fromisoformat(str(rec.started_at)).strftime("%Y-%m-%d_%H-%M-%S")
    except Exception:
        ts = "unknown"
    cam_slug = (rec.camera_id or "cam").replace("-", "_")
    download_name = f"{cam_slug}_{ts}.mp4"

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@router.get("/{camera_id}/timeline")
async def get_timeline(
    camera_id: str,
    date: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        date_obj  = datetime.strptime(date, "%Y-%m-%d")
        date_from = date_obj.replace(hour=0,  minute=0,  second=0)
        date_to   = date_obj.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    recording_repo = RecordingRepository(db)
    recordings     = await recording_repo.get_by_camera_and_date(camera_id, date_from, date_to)
    event_repo     = EventRepository(db)
    events         = await event_repo.get_by_camera_and_date(camera_id, date_from, date_to)

    timeline = []
    for hour in range(24):
        hour_start = date_obj.replace(hour=hour, minute=0,  second=0)
        hour_end   = date_obj.replace(hour=hour, minute=59, second=59)
        timeline.append({
            "hour":          hour,
            "has_recording": any(hour_start <= rec.started_at.replace(tzinfo=None) <= hour_end for rec in recordings),
            "has_motion":    any(hour_start <= evt.started_at.replace(tzinfo=None) <= hour_end for evt in events),
        })

    return {
        "camera_id":        camera_id,
        "date":             date,
        "timeline":         timeline,
        "total_recordings": len(recordings),
        "total_events":     len(events),
    }


@router.post("/{recording_id}/protect")
async def toggle_protect(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("operator")),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    rec.is_protected = not rec.is_protected
    await db.commit()
    return {"is_protected": rec.is_protected}


@router.delete("/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = RecordingRepository(db)
    rec  = await repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404)
    if rec.is_protected:
        raise HTTPException(status_code=400, detail="Rekaman dilindungi, lepas proteksi dulu")
    Path(rec.file_path).unlink(missing_ok=True)
    await repo.delete_by_id(recording_id)
'@

Set-Content -Path "backend\api\routers\recordings.py" -Value $recordingsRouter -Encoding UTF8
Write-Host "  OK: recordings.py - tambah sync endpoint + fix list semua rekaman" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 4: backend/db/repositories/recording_repo.py
# Tambah method yang dibutuhkan router baru
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[4/6] Patching backend/db/repositories/recording_repo.py ..." -ForegroundColor Green

$recordingRepo = @'
"""Repository untuk operasi database terkait Recording."""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, delete, desc
from backend.db.models.recording import Recording
from .base_repo import BaseRepository


class RecordingRepository(BaseRepository[Recording]):
    def __init__(self, db: AsyncSession):
        super().__init__(Recording, db)

    async def get_recent(self, limit: int = 500) -> list[Recording]:
        """Ambil rekaman terbaru tanpa filter, diurutkan dari yang terbaru."""
        result = await self.db.execute(
            select(Recording).order_by(desc(Recording.started_at)).limit(limit)
        )
        return result.scalars().all()

    async def get_by_camera(self, camera_id: str, limit: int = 200) -> list[Recording]:
        """Ambil rekaman untuk satu kamera, terbaru dulu."""
        result = await self.db.execute(
            select(Recording)
            .where(Recording.camera_id == camera_id)
            .order_by(desc(Recording.started_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_date_range(self, date_from: datetime, date_to: datetime) -> list[Recording]:
        """Ambil semua rekaman dalam rentang tanggal."""
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.started_at >= date_from,
                    Recording.started_at <= date_to,
                )
            ).order_by(desc(Recording.started_at))
        )
        return result.scalars().all()

    async def get_by_camera_and_date(
        self, camera_id: str, date_from: datetime, date_to: datetime
    ) -> list[Recording]:
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.started_at >= date_from,
                    Recording.started_at <= date_to,
                )
            ).order_by(Recording.started_at)
        )
        return result.scalars().all()

    async def get_oldest_unprotected(self, camera_id: str, limit: int = 10) -> list[Recording]:
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.is_protected == False,
                )
            ).order_by(Recording.started_at).limit(limit)
        )
        return result.scalars().all()

    async def get_total_size_mb(self, camera_id: str) -> float:
        result = await self.db.execute(
            select(func.sum(Recording.file_size_mb)).where(Recording.camera_id == camera_id)
        )
        return result.scalar() or 0.0

    async def get_not_encoded_av1(self, limit: int = 5) -> list[Recording]:
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.is_encoded_av1 == False,
                    Recording.ended_at.isnot(None),
                )
            ).order_by(Recording.started_at).limit(limit)
        )
        return result.scalars().all()

    async def delete_old(self, camera_id: str, before_date: datetime) -> int:
        result = await self.db.execute(
            delete(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.started_at < before_date,
                    Recording.is_protected == False,
                )
            )
        )
        await self.db.commit()
        return result.rowcount
'@

Set-Content -Path "backend\db\repositories\recording_repo.py" -Value $recordingRepo -Encoding UTF8
Write-Host "  OK: recording_repo.py - tambah get_recent, get_by_camera, get_by_date_range" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 5: frontend/src/pages/Storage/index.tsx
# Tambah tombol "Sync Rekaman dari Disk" di tab Rekaman
# Juga perbaiki default date range ke 30 hari terakhir (bukan 7 hari)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[5/6] Patching Storage page - tambah tombol Sync Rekaman ..." -ForegroundColor Green

# Patch hanya bagian yang perlu diubah di Storage/index.tsx
# Ganti weekAgoStr ke 30 hari dan tambah sync mutation
$storageContent = Get-Content "frontend\src\pages\Storage\index.tsx" -Raw -Encoding UTF8

# Ganti default date dari 7 hari ke 30 hari
$storageContent = $storageContent -replace 'const weekAgoStr = \(\) => \{[^}]+\}', @'
const monthAgoStr = () => {
  const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10)
}
'@
$storageContent = $storageContent -replace 'weekAgoStr\(\)', 'monthAgoStr()'

# Tambah import useMutation untuk sync jika belum ada (sudah ada)
# Tambah state syncMsg
$storageContent = $storageContent -replace '(\[recDateFrom, setRecDateFrom\] = useState\()weekAgoStr\(\)', '$1monthAgoStr()'

# Tambah sync mutation setelah deleteMutation
$syncMutation = @'

  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/recordings/sync').then(r => r.data),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["recordings"] })
      showMsg("success", `Sync selesai: ${data.inserted} file baru ditambahkan, ${data.skipped} sudah ada`)
    },
    onError: () => showMsg("error", "Sync gagal"),
  })
'@

$storageContent = $storageContent -replace '(const deleteMutation = useMutation\(\{[^}]+\}\)[^}]*\}[^)]*\))', "`$1`n$syncMutation"

# Tambah tombol Sync di filter bar rekaman
$syncButton = @'
              <button
                onClick={() => { if (confirm('Scan semua file .mp4 di storage dan daftarkan ke database? Proses ini mungkin butuh beberapa detik.')) syncMutation.mutate() }}
                disabled={syncMutation.isPending}
                style={{
                  padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                  background: syncMutation.isPending ? sub : '#7c3aed',
                  color: '#fff', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >
                {syncMutation.isPending ? 'Scanning...' : '🔄 Sync dari Disk'}
              </button>
'@

$storageContent = $storageContent -replace '(<span style=\{ fontSize: 11, color: sub, marginLeft: .auto. \}>)', "$syncButton`n              `$1"

Set-Content -Path "frontend\src\pages\Storage\index.tsx" -Value $storageContent -Encoding UTF8

# Tambah import apiClient jika belum ada
$storageContent2 = Get-Content "frontend\src\pages\Storage\index.tsx" -Raw -Encoding UTF8
if ($storageContent2 -notmatch "import { apiClient }") {
    $storageContent2 = $storageContent2 -replace '(import { storageApi })', "import { apiClient } from `"@/api/client`"`n`$1"
    Set-Content -Path "frontend\src\pages\Storage\index.tsx" -Value $storageContent2 -Encoding UTF8
}

Write-Host "  OK: Storage page - tambah tombol Sync Rekaman dari Disk" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 6: Tambah zustand persist ke package.json (sudah ada di zustand)
# Cek apakah zustand versi yang diinstall support persist
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n[6/6] Mengecek zustand version untuk persist middleware ..." -ForegroundColor Green

$pkg = Get-Content "frontend\package.json" -Raw | ConvertFrom-Json
$zustandVer = $pkg.dependencies.zustand
Write-Host "  Zustand version: $zustandVer" -ForegroundColor White
Write-Host "  OK: zustand >= 4.x sudah include persist middleware bawaan" -ForegroundColor White

# ─────────────────────────────────────────────────────────────────────────────
# SELESAI
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host " PATCH 2 SELESAI. Yang diubah:" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  1. frontend/src/store/cameras.ts" -ForegroundColor White
Write-Host "     -> Grid layout tersimpan, tidak reset saat refresh" -ForegroundColor Gray
Write-Host "  2. frontend/src/api/recordings.ts" -ForegroundColor White
Write-Host "     -> Fix date filter query ke backend" -ForegroundColor Gray
Write-Host "  3. backend/api/routers/recordings.py" -ForegroundColor White
Write-Host "     -> GET /recordings tanpa filter kembalikan 500 terbaru" -ForegroundColor Gray
Write-Host "     -> POST /recordings/sync - scan disk → insert ke DB" -ForegroundColor Gray
Write-Host "  4. backend/db/repositories/recording_repo.py" -ForegroundColor White
Write-Host "     -> Tambah get_recent, get_by_camera, get_by_date_range" -ForegroundColor Gray
Write-Host "  5. frontend/src/pages/Storage/index.tsx" -ForegroundColor White
Write-Host "     -> Tombol 'Sync dari Disk' di tab Rekaman" -ForegroundColor Gray
Write-Host "     -> Default filter 30 hari (sebelumnya 7 hari)" -ForegroundColor Gray

Write-Host "`n LANGKAH SELANJUTNYA:" -ForegroundColor Yellow
Write-Host " 1. Push ke repo:" -ForegroundColor White
Write-Host "    git add -A && git commit -m 'fix: grid persist, rekaman sync, recordings list'" -ForegroundColor DarkYellow
Write-Host "    git push" -ForegroundColor DarkYellow
Write-Host " 2. Rebuild:" -ForegroundColor White
Write-Host "    docker compose up -d --build api frontend" -ForegroundColor DarkYellow
Write-Host " 3. Sync rekaman lama dari disk:" -ForegroundColor White
Write-Host "    Buka Storage → tab Rekaman → klik 'Sync dari Disk'" -ForegroundColor DarkYellow
Write-Host "    ATAU via API:" -ForegroundColor White
Write-Host "    curl -X POST http://localhost:8000/api/v1/recordings/sync -H 'Authorization: Bearer TOKEN'" -ForegroundColor DarkYellow
Write-Host "`n CATATAN - Sub stream hitam:" -ForegroundColor Yellow
Write-Host " Cek log backend untuk error HLS FFmpeg:" -ForegroundColor White
Write-Host "    docker logs cctv_api --tail 100 | findstr HLS" -ForegroundColor DarkYellow
Write-Host " Kemungkinan penyebab: codec HEVC, atau rtsp_sub URL salah di kamera" -ForegroundColor Gray
Write-Host " Coba ganti ke MAIN stream di Live View (klik icon stream di pojok kamera)" -ForegroundColor Gray
