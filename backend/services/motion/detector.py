"""
MotionDetector — deteksi gerak per zona menggunakan OpenCV.
Berjalan dari sub-stream (360p) agar ringan di CPU.
"""
import cv2
import asyncio
import numpy as np
from datetime import datetime, timezone
from backend.core.logging import get_logger

logger = get_logger(__name__, service="motion")


class MotionDetector:
    def __init__(self, camera: dict, on_motion_callback):
        self.camera = camera
        self.camera_id = camera["id"]
        self.on_motion = on_motion_callback
        self.zones = self._parse_zones()
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        self._last_event_time: dict[str, float] = {}
        self._cooldown_s = 60  # min detik antar notifikasi per zona
        self._frame_skip = 8   # proses tiap 8 frame (~3fps dari 25fps)

    def _parse_zones(self) -> list[dict]:
        config = self.camera.get("config_json") or {}
        return config.get("motion_zones", [{"name": "full_frame", "coords": None}])

    async def run(self):
        """Loop utama — baca frame dari sub-stream dan analisis."""
        rtsp_url = self.camera.get("rtsp_sub") or self.camera["rtsp_main"]
        cap = cv2.VideoCapture(rtsp_url)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                logger.warning(f"[{self.camera_id}] Sub-stream putus, retry 10s")
                await asyncio.sleep(10)
                cap = cv2.VideoCapture(rtsp_url)
                continue

            frame_count += 1
            if frame_count % self._frame_skip != 0:
                continue  # skip frame — hemat CPU

            small = cv2.resize(frame, (640, 360))

            for zone in self.zones:
                if self._detect_in_zone(small, zone):
                    await self._trigger_event(zone, frame)

            await asyncio.sleep(0)  # yield ke event loop

    def _detect_in_zone(self, frame: np.ndarray, zone: dict) -> bool:
        """Deteksi gerakan di area zona tertentu."""
        if zone.get("coords"):
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            pts = np.array(zone["coords"], dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
            roi = cv2.bitwise_and(frame, frame, mask=mask)
        else:
            roi = frame

        fg_mask = self.subtractor.apply(roi)
        # Hilangkan noise kecil
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        motion_pct = np.count_nonzero(fg_mask) / fg_mask.size * 100

        return motion_pct > 1.5  # threshold: 1.5% area bergerak

    async def _trigger_event(self, zone: dict, frame: np.ndarray):
        """Kirim event jika cooldown sudah lewat."""
        import time
        zone_name = zone["name"]
        now = time.time()
        last = self._last_event_time.get(zone_name, 0)

        if now - last < self._cooldown_s:
            return  # masih dalam cooldown

        self._last_event_time[zone_name] = now
        snapshot_path = self._save_snapshot(frame, zone_name)
        await self.on_motion(self.camera_id, zone_name, snapshot_path)

    def _save_snapshot(self, frame: np.ndarray, zone_name: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"/tmp/snapshots/{self.camera_id}_{zone_name}_{ts}.jpg"
        import os; os.makedirs("/tmp/snapshots", exist_ok=True)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return path
