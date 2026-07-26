"""In-memory playback transcode/remux queue."""
import asyncio
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.logging import get_logger
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.recording_repo import RecordingRepository
from backend.services.recorder.ffmpeg_wrapper import (
    probe_codec_from_file,
    remux_for_streaming,
    transcode_to_h264,
)

logger = get_logger(__name__, service="transcode")


class TranscodeQueue:
    _instance: "TranscodeQueue | None" = None

    def __init__(self, max_concurrent: int = 3):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.recording_jobs: dict[int, str] = {}
        self.cache_dir = Path(tempfile.gettempdir()) / "nvr_remux"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._workers: list[asyncio.Task] = []
        self._cleanup_task: asyncio.Task | None = None
        self._max_concurrent = max_concurrent

    @classmethod
    def get_instance(cls) -> "TranscodeQueue":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self) -> None:
        if not self._workers:
            self._workers = [
                asyncio.create_task(self._worker_loop(i))
                for i in range(self._max_concurrent)
            ]
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        if self._cleanup_task:
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
        self._workers = []
        self._cleanup_task = None

    def add_job(self, recording_id: int) -> str:
        existing_job_id = self.recording_jobs.get(recording_id)
        if existing_job_id:
            existing = self.jobs.get(existing_job_id)
            if existing and existing["status"] in {"queued", "processing", "done"}:
                return existing_job_id

        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "recording_id": recording_id,
            "status": "queued",
            "progress_pct": 0,
            "cache_path": None,
            "error_msg": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.recording_jobs[recording_id] = job_id
        self.queue.put_nowait(job_id)
        logger.info(
            f"Queued transcode job for recording {recording_id}",
            extra={"job_id": job_id, "action": "queued"},
        )
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)

    def get_status_by_recording(self, recording_id: int) -> dict[str, Any] | None:
        job_id = self.recording_jobs.get(recording_id)
        return self.get_status(job_id) if job_id else None

    def cache_info(self) -> dict[str, Any]:
        files = [p for p in self.cache_dir.glob("*.mp4") if p.is_file()]
        total_bytes = sum(p.stat().st_size for p in files)
        now = datetime.now(timezone.utc).timestamp()
        oldest_age_hours = 0.0
        if files:
            oldest_mtime = min(p.stat().st_mtime for p in files)
            oldest_age_hours = (now - oldest_mtime) / 3600
        return {
            "path": str(self.cache_dir),
            "file_count": len(files),
            "total_size_gb": round(total_bytes / (1024 ** 3), 2),
            "oldest_file_age_hours": round(oldest_age_hours, 1),
        }

    async def _worker_loop(self, worker_id: int) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await self._process_job(job_id, worker_id)
            finally:
                self.queue.task_done()

    async def _process_job(self, job_id: str, worker_id: int) -> None:
        job = self.jobs[job_id]
        job["status"] = "processing"
        job["progress_pct"] = 10
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Processing transcode job {job_id}",
            extra={"job_id": job_id, "action": "processing"},
        )

        try:
            async with AsyncSessionLocal() as db:
                repo = RecordingRepository(db)
                rec = await repo.get_by_id(job["recording_id"])

            if not rec:
                raise FileNotFoundError("Recording tidak ditemukan")
            file_path = Path(rec.file_path)
            if not file_path.exists():
                raise FileNotFoundError("File rekaman tidak ditemukan")
            if file_path.stat().st_size < 1024:
                raise ValueError("File rekaman kosong")

            loop = asyncio.get_running_loop()
            codec = await loop.run_in_executor(None, probe_codec_from_file, str(file_path))
            job["progress_pct"] = 25
            if codec in ("hevc", "h265"):
                cache_path = self.cache_dir / f"rec_{rec.id}_h264.mp4"
                if not cache_path.exists():
                    success = await loop.run_in_executor(
                        None, transcode_to_h264, str(file_path), str(cache_path)
                    )
                    if not success:
                        raise RuntimeError("Gagal transcode HEVC ke H.264")
                job["progress_pct"] = 95
            else:
                cache_path = self.cache_dir / f"rec_{rec.id}.mp4"
                if not cache_path.exists():
                    success = await loop.run_in_executor(
                        None, remux_for_streaming, str(file_path), str(cache_path)
                    )
                    if not success:
                        raise RuntimeError("Gagal remux file untuk streaming")
                job["progress_pct"] = 95

            job["cache_path"] = str(cache_path)
            job["status"] = "done"
            job["progress_pct"] = 100
            logger.info(
                f"Transcode job done: {cache_path}",
                extra={"job_id": job_id, "action": "done"},
            )
        except Exception as exc:
            job["status"] = "error"
            job["error_msg"] = str(exc)
            logger.error(
                f"Transcode job failed: {exc}",
                extra={"job_id": job_id, "action": "error"},
            )
        finally:
            job["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(6 * 60 * 60)
            self.cleanup_cache()

    def cleanup_cache(self, max_age_hours: int = 24, max_total_gb: float = 2.0) -> dict[str, Any]:
        now = datetime.now(timezone.utc).timestamp()
        files = sorted(
            [p for p in self.cache_dir.glob("*.mp4") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
        )
        deleted = 0
        freed_bytes = 0

        for path in list(files):
            if (now - path.stat().st_mtime) / 3600 > max_age_hours:
                size = path.stat().st_size
                path.unlink(missing_ok=True)
                deleted += 1
                freed_bytes += size
                files.remove(path)

        total_bytes = sum(p.stat().st_size for p in files if p.exists())
        max_bytes = max_total_gb * 1024 ** 3
        for path in list(files):
            if total_bytes <= max_bytes:
                break
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            deleted += 1
            freed_bytes += size
            total_bytes -= size

        result = {"deleted": deleted, "freed_gb": round(freed_bytes / (1024 ** 3), 2)}
        logger.info(
            f"Transcode cache cleanup deleted={deleted}, freed_gb={result['freed_gb']}",
            extra={"action": "cleanup"},
        )
        return result
