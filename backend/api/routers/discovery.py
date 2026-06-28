"""
Discovery API Router

Provides endpoints for discovering ONVIF cameras on the network.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from backend.services.discovery.onvif_scanner import discover_cameras
from backend.api.dependencies import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoveryRequest(BaseModel):
    """Request model for camera discovery."""
    network: Optional[str] = Field(
        None,
        description="Network CIDR to scan (e.g., '192.168.1.0/24'). If not provided, uses local subnet."
    )
    timeout: float = Field(
        5.0,
        ge=1.0,
        le=30.0,
        description="Discovery timeout in seconds"
    )
    ports: Optional[List[int]] = Field(
        None,
        description="List of ports to scan. If not provided, uses common ONVIF ports."
    )


class DiscoveredCamera(BaseModel):
    """Model for a discovered camera."""
    ip: str
    port: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None
    mac_address: Optional[str] = None


class DiscoveryResponse(BaseModel):
    """Response model for camera discovery."""
    cameras: List[DiscoveredCamera]
    count: int
    network_scanned: Optional[str] = None


class DiscoveryStatus(BaseModel):
    """Status of an ongoing discovery operation."""
    is_running: bool
    cameras_found: int = 0


# In-memory storage for discovery status
_discovery_status = {
    "is_running": False,
    "cameras_found": 0
}


@router.post("/cameras", response_model=DiscoveryResponse)
async def discover_onvif_cameras(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    _user = Depends(get_current_admin_user)
):
    """
    Discover ONVIF cameras on the network.
    
    This endpoint performs network scanning to find ONVIF-compatible IP cameras.
    It uses WS-Discovery multicast probes and port scanning as fallback.
    
    Args:
        request: Discovery parameters (network, timeout, ports)
    
    Returns:
        List of discovered cameras
    """
    global _discovery_status
    
    if _discovery_status["is_running"]:
        raise HTTPException(status_code=409, detail="Discovery already in progress")
    
    _discovery_status["is_running"] = True
    _discovery_status["cameras_found"] = 0
    
    try:
        cameras = await discover_cameras(
            network=request.network,
            timeout=request.timeout
        )
        
        _discovery_status["cameras_found"] = len(cameras)
        
        return DiscoveryResponse(
            cameras=[DiscoveredCamera(**cam) for cam in cameras],
            count=len(cameras),
            network_scanned=request.network
        )
    except Exception as e:
        logger.error(f"Camera discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
    finally:
        _discovery_status["is_running"] = False


@router.get("/status", response_model=DiscoveryStatus)
async def get_discovery_status(_user = Depends(get_current_admin_user)):
    """
    Get the status of an ongoing discovery operation.
    
    Returns:
        Current discovery status
    """
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
    _user = Depends(get_current_admin_user)
):
    """
    Test connection to a specific camera.
    
    Args:
        ip: Camera IP address
        port: RTSP port (default 554)
        username: RTSP username (optional)
        password: RTSP password (optional)
    
    Returns:
        Connection test result
    """
    # Import here to avoid circular dependency
    from backend.api.routers.config import test_rtsp_connection
    
    # Build RTSP URL if credentials provided
    rtsp_url = None
    if username and password:
        rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/"
    else:
        rtsp_url = f"rtsp://{ip}:{port}/"
    
    try:
        result = await test_rtsp_connection(rtsp_url)
        return result
    except Exception as e:
        logger.error(f"Camera connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
