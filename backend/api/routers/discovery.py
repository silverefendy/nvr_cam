"""
Discovery API Router

Provides endpoints for discovering ONVIF cameras on the network.
Filter: hanya tampilkan IP camera (ONVIF device type NetworkVideoTransmitter
AU port RTSP 554 terbuka), exclude komputer/PC.
"""

import asyncio
import logging
import socket
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from backend.services.discovery.onvif_scanner import discover_cameras
from backend.api.dependencies import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])


# ---------------------------------------------------------------------------
# Known camera vendor OUI prefixes (3 hex bytes of MAC)
# Source: IEEE OUI registry — major IP camera manufacturers
# ---------------------------------------------------------------------------
CAMERA_VENDOR_OUIS = {
    # Dahua
    "9c:51:2a", "2c:c8:1b", "a0:24:1e", "00:26:03", "70:85:c8",
    "9c:15:03", "c4:4f:ec", "10:13:ee", "34:e6:d7", "44:7c:bf",
    # Hikvision
    "44:19:b6", "bc:ad:28", "e8:b4:c8", "14:23:63", "54:56:cb",
    "d8:0d:17", "00:1e:10", "88:5d:90", "c8:e0:de", "a4:14:37",
    # Axis
    "00:40:8c", "ac:cc:8e", "00:30:7c",
    # Hanwha/Samsung
    "b4:a2:eb", "00:09:18", "40:b8:9a",
    # Bosch
    "00:07:5f",
    # Vivotek
    "00:02:d1",
    # Uniview
    "c4:65:16", "54:b1:21",
    # Reolink
    "ec:71:db",
}


def _is_camera_by_oui(mac: Optional[str]) -> bool:
    """Return True jika 3 byte pertama MAC address cocok dengan vendor kamera."""
    if not mac:
        return False
    normalized = mac.lower().replace("-", ":")
    prefix = ":".join(normalized.split(":")[:3])
    return prefix in CAMERA_VENDOR_OUIS


async def _check_rtsp_port(ip: str, port: int = 554, timeout: float = 2.0) -> bool:
    """Cek apakah port RTSP (554) terbuka di IP tersebut."""
    loop = asyncio.get_event_loop()
    try:
        conn = asyncio.open_connection(ip, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _is_likely_camera(cam: dict) -> bool:
    """
    Filter berlapis untuk memastikan device adalah IP camera, bukan PC/server.

    Lulus jika:
    1. onvif_support = True (respond WS-Discovery sebagai NetworkVideoTransmitter), ATAU
    2. MAC address cocok dengan OUI vendor kamera terkenal

    Tidak lulus jika:
    - Tidak punya RTSP URL dan tidak punya onvif_support
    """
    onvif = cam.get("onvif_support") or cam.get("onvif") or False
    mac = cam.get("mac_address") or cam.get("mac")

    if onvif:
        return True
    if _is_camera_by_oui(mac):
        return True
    # Fallback: punya rtsp_url → kemungkinan besar kamera
    if cam.get("rtsp_url"):
        return True
    return False


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DiscoveryRequest(BaseModel):
    network: Optional[str] = Field(
        None,
        description="Network CIDR (e.g., '192.168.1.0/24'). Default: subnet lokal."
    )
    timeout: float = Field(5.0, ge=1.0, le=30.0)
    ports: Optional[List[int]] = None
    camera_only: bool = Field(
        True,
        description="Jika True, hanya tampilkan IP camera (filter PC/server)."
    )


class DiscoveredCamera(BaseModel):
    ip: str
    port: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None
    mac_address: Optional[str] = None
    is_camera: bool = True


class DiscoveryResponse(BaseModel):
    cameras: List[DiscoveredCamera]
    count: int
    total_found: int
    filtered_out: int
    network_scanned: Optional[str] = None


class DiscoveryStatus(BaseModel):
    is_running: bool
    cameras_found: int = 0


_discovery_status = {"is_running": False, "cameras_found": 0}


@router.post("/cameras", response_model=DiscoveryResponse)
async def discover_onvif_cameras(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    _user=Depends(get_current_admin_user)
):
    """
    Temukan kamera IP di jaringan.
    Gunakan camera_only=true (default) untuk exclude PC/server dari hasil.

    Filter berlapis:
    1. WS-Discovery device type NetworkVideoTransmitter (ONVIF)
    2. MAC address OUI vendor kamera terkenal (Dahua, Hikvision, Axis, dll)
    3. Memiliki RTSP URL dari ONVIF profile
    """
    global _discovery_status

    if _discovery_status["is_running"]:
        raise HTTPException(status_code=409, detail="Discovery sedang berjalan")

    _discovery_status["is_running"] = True
    _discovery_status["cameras_found"] = 0

    try:
        raw_cameras = await discover_cameras(
            network=request.network,
            timeout=request.timeout
        )

        total_found = len(raw_cameras)

        # Terapkan filter kamera-only jika diminta
        if request.camera_only:
            filtered = [cam for cam in raw_cameras if _is_likely_camera(cam)]
        else:
            filtered = raw_cameras

        filtered_out = total_found - len(filtered)
        _discovery_status["cameras_found"] = len(filtered)

        cameras = []
        for cam in filtered:
            try:
                cameras.append(DiscoveredCamera(**cam, is_camera=True))
            except Exception:
                # Jika field tidak cocok, coba manual
                cameras.append(DiscoveredCamera(
                    ip=cam.get("ip", cam.get("ip_address", "")),
                    port=cam.get("port", 554),
                    manufacturer=cam.get("manufacturer"),
                    model=cam.get("model"),
                    name=cam.get("name"),
                    rtsp_url=cam.get("rtsp_url"),
                    onvif_url=cam.get("onvif_url"),
                    mac_address=cam.get("mac_address"),
                    is_camera=True,
                ))

        return DiscoveryResponse(
            cameras=cameras,
            count=len(cameras),
            total_found=total_found,
            filtered_out=filtered_out,
            network_scanned=request.network,
        )
    except Exception as e:
        logger.error(f"Camera discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery gagal: {str(e)}")
    finally:
        _discovery_status["is_running"] = False


@router.get("/status", response_model=DiscoveryStatus)
async def get_discovery_status(_user=Depends(get_current_admin_user)):
    return DiscoveryStatus(
        is_running=_discovery_status["is_running"],
        cameras_found=_discovery_status["cameras_found"]
    )


@router.post("/cameras/{ip}/test")
async def test_camera_connection(
    ip: str,
    port: int = 554,
    username: Optional[str] = None,
    password: Optional[str] = None,
    _user=Depends(get_current_admin_user)
):
    from backend.api.routers.config import test_rtsp_connection
    rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/" if username and password else f"rtsp://{ip}:{port}/"
    try:
        result = await test_rtsp_connection(rtsp_url)
        return result
    except Exception as e:
        logger.error(f"Camera connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
