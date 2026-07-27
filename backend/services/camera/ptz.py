"""
ONVIF PTZ Camera Controls Service.
"""
from onvif import ONVIFCamera
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
import logging
import re
import asyncio

logger = logging.getLogger(__name__)

class PTZController:
    @classmethod
    async def _get_onvif_camera(cls, camera_id: str) -> ONVIFCamera:
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            camera = await repo.get_by_id(camera_id)
            if not camera:
                raise ValueError(f"Kamera dengan ID {camera_id} tidak ditemukan")

            config = camera.config_json or {}

            # Read credentials from config_json or fallback to RTSP parsing
            ip = config.get("ip_address") or cls._extract_ip(camera.rtsp_main)
            port = int(config.get("port") or 80)
            username = config.get("username") or "admin"
            password = config.get("password") or ""

            if not ip:
                raise ValueError(f"Kamera {camera_id} tidak memiliki konfigurasi IP/RTSP valid")

            cam = ONVIFCamera(ip, port, username, password)
            await asyncio.to_thread(cam.update_xaddrs)
            return cam

    @staticmethod
    def _extract_ip(rtsp_url: str) -> str:
        """Extract IP from RTSP URL: rtsp://user:pass@192.168.1.x:554/..."""
        m = re.search(r"@([\d.]+)", rtsp_url or "")
        return m.group(1) if m else ""

    @classmethod
    async def move(cls, camera_id: str, direction: str, speed: float = 0.5):
        """Continuous move (up/down/left/right/zoom_in/zoom_out)."""
        cam = await cls._get_onvif_camera(camera_id)
        ptz = await asyncio.to_thread(cam.create_ptz_service)
        media = await asyncio.to_thread(cam.create_media_service)
        profiles = await asyncio.to_thread(media.GetProfiles)
        if not profiles:
            raise ValueError("Tidak ada ONVIF media profile ditemukan")
        profile_token = profiles[0].token

        # Get PTZ status or configuration to get valid ranges
        status = await asyncio.to_thread(ptz.GetStatus, {"ProfileToken": profile_token})
        request = await asyncio.to_thread(ptz.create_type, "ContinuousMove")
        request.ProfileToken = profile_token
        request.Velocity = status.Position

        # Reset velocities
        request.Velocity.PanTilt.x = 0.0
        request.Velocity.PanTilt.y = 0.0
        request.Velocity.Zoom.x = 0.0

        dir_lower = direction.lower()
        if dir_lower == "up":
            request.Velocity.PanTilt.y = speed
        elif dir_lower == "down":
            request.Velocity.PanTilt.y = -speed
        elif dir_lower == "left":
            request.Velocity.PanTilt.x = -speed
        elif dir_lower == "right":
            request.Velocity.PanTilt.x = speed
        elif dir_lower == "zoom_in":
            request.Velocity.Zoom.x = speed
        elif dir_lower == "zoom_out":
            request.Velocity.Zoom.x = -speed
        else:
            raise ValueError(f"Direction {direction} tidak didukung")

        await asyncio.to_thread(ptz.ContinuousMove, request)

    @classmethod
    async def stop(cls, camera_id: str):
        """Stop PTZ movement."""
        cam = await cls._get_onvif_camera(camera_id)
        ptz = await asyncio.to_thread(cam.create_ptz_service)
        media = await asyncio.to_thread(cam.create_media_service)
        profiles = await asyncio.to_thread(media.GetProfiles)
        if not profiles:
            raise ValueError("Tidak ada ONVIF media profile ditemukan")
        profile_token = profiles[0].token

        request = await asyncio.to_thread(ptz.create_type, "Stop")
        request.ProfileToken = profile_token
        request.PanTilt = True
        request.Zoom = True
        await asyncio.to_thread(ptz.Stop, request)

    @classmethod
    async def get_presets(cls, camera_id: str) -> list:
        """Return list of ONVIF presets."""
        cam = await cls._get_onvif_camera(camera_id)
        ptz = await asyncio.to_thread(cam.create_ptz_service)
        media = await asyncio.to_thread(cam.create_media_service)
        profiles = await asyncio.to_thread(media.GetProfiles)
        if not profiles:
            raise ValueError("Tidak ada ONVIF media profile ditemukan")
        profile_token = profiles[0].token

        presets = await asyncio.to_thread(ptz.GetPresets, {"ProfileToken": profile_token})
        return [
            {
                "token": p.token,
                "name": p.Name,
            }
            for p in presets
        ] if presets else []

    @classmethod
    async def goto_preset(cls, camera_id: str, preset_token: str):
        """Go to preset."""
        cam = await cls._get_onvif_camera(camera_id)
        ptz = await asyncio.to_thread(cam.create_ptz_service)
        media = await asyncio.to_thread(cam.create_media_service)
        profiles = await asyncio.to_thread(media.GetProfiles)
        if not profiles:
            raise ValueError("Tidak ada ONVIF media profile ditemukan")
        profile_token = profiles[0].token

        request = await asyncio.to_thread(ptz.create_type, "GotoPreset")
        request.ProfileToken = profile_token
        request.PresetToken = preset_token
        await asyncio.to_thread(ptz.GotoPreset, request)

    @classmethod
    async def set_preset(cls, camera_id: str, preset_name: str) -> str:
        """Save current position as preset, return token."""
        cam = await cls._get_onvif_camera(camera_id)
        ptz = await asyncio.to_thread(cam.create_ptz_service)
        media = await asyncio.to_thread(cam.create_media_service)
        profiles = await asyncio.to_thread(media.GetProfiles)
        if not profiles:
            raise ValueError("Tidak ada ONVIF media profile ditemukan")
        profile_token = profiles[0].token

        request = await asyncio.to_thread(ptz.create_type, "SetPreset")
        request.ProfileToken = profile_token
        request.PresetName = preset_name

        response = await asyncio.to_thread(ptz.SetPreset, request)
        return response.PresetToken if response else ""
