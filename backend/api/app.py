"""
FastAPI application factory.
Semua router didaftarkan di sini.
"""
import asyncio
import yaml
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.exceptions import CCTVBaseException
from backend.core.logging import get_logger
from backend.core.config import settings
from backend.api.routers import auth, cameras, stream, recordings, events, storage, users, settings, system
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.camera import Camera
from backend.services.recorder.manager import RecordingManager
from backend.services.storage.manager import StorageManager
from backend.services.motion.manager import MotionManager
from backend.api.websocket import ConnectionManager

logger = get_logger(__name__, service="api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup dan shutdown logic."""
    # Startup
    logger.info("Starting NVR API service...")
    
    # Initialize managers
    recording_manager = RecordingManager.get_instance()
    storage_manager = None
    motion_manager = None
    
    try:
        # Load cameras from database
        async with AsyncSessionLocal() as db:
            camera_repo = CameraRepository(db)
            cameras = await camera_repo.get_active_cameras()
            
            # If DB is empty, seed from config/cameras.yaml
            if not cameras:
                logger.info("No cameras in DB, seeding from config/cameras.yaml")
                config_path = Path(__file__).parent.parent.parent / "config" / "cameras.yaml"
                if config_path.exists():
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    for cam_config in config.get("cameras", []):
                        camera = Camera(
                            id=cam_config["id"],
                            name=cam_config["name"],
                            location=cam_config.get("location"),
                            rtsp_main=cam_config["rtsp_main"],
                            rtsp_sub=cam_config.get("rtsp_sub"),
                            storage_drive=cam_config["storage_drive"],
                            motion_enabled=cam_config.get("motion_enabled", False),
                            retention_days=cam_config.get("retention_days", 30),
                            sort_order=cam_config.get("sort_order", 0),
                            config_json=cam_config.get("config_json"),
                        )
                        await camera_repo.create(camera)
                    await db.commit()
                    cameras = await camera_repo.get_active_cameras()
                    logger.info(f"Seeded {len(cameras)} cameras from config")
        
        # Convert cameras to dict format for RecordingManager
        camera_dicts = []
        for cam in cameras:
            camera_dicts.append({
                "id": cam.id,
                "name": cam.name,
                "location": cam.location,
                "rtsp_main": cam.rtsp_main,
                "rtsp_sub": cam.rtsp_sub,
                "storage_drive": cam.storage_drive,
                "motion_enabled": cam.motion_enabled,
                "retention_days": cam.retention_days,
                "segment_duration": cam.segment_duration,
                "is_active": cam.is_active,
                "config_json": cam.config_json,
            })
        
        # Start RecordingManager
        logger.info(f"Starting recording for {len(camera_dicts)} cameras")
        asyncio.create_task(recording_manager.start_all(camera_dicts))
        
        # Initialize StorageManager
        camera_drive_map = {cam["id"]: cam["storage_drive"] for cam in camera_dicts}
        storage_manager = StorageManager(camera_drive_map)
        asyncio.create_task(storage_manager.monitor_loop())
        logger.info("Storage manager started")
        
        # Start MotionManager for motion-enabled cameras
        motion_cameras = [cam for cam in camera_dicts if cam.get("motion_enabled")]
        if motion_cameras:
            motion_manager = MotionManager()
            asyncio.create_task(motion_manager.start_all(motion_cameras))
            logger.info(f"Motion detection started for {len(motion_cameras)} cameras")
        
        # Store managers in app state for access by routers
        app.state.recording_manager = recording_manager
        app.state.storage_manager = storage_manager
        app.state.motion_manager = motion_manager
        app.state.websocket_manager = ConnectionManager()
        
        logger.info("NVR API service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down NVR API service...")
    
    try:
        # Stop RecordingManager
        await recording_manager.stop_all()
        logger.info("Recording manager stopped")
        
        # Stop MotionManager
        if motion_manager:
            await motion_manager.stop_all()
            logger.info("Motion manager stopped")
        
        # Close DB connections
        await AsyncSessionLocal.close_all()
        logger.info("Database connections closed")
        
        logger.info("NVR API service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="CCTV NVR API",
        version="1.0.0",
        description="API untuk sistem NVR CCTV custom — 30 kamera Dahua",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS — izinkan frontend dan mobile akses API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],      # ganti dengan domain spesifik di production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handler
    @app.exception_handler(CCTVBaseException)
    async def cctv_exception_handler(request: Request, exc: CCTVBaseException):
        return JSONResponse(
            status_code=400,
            content={"error": exc.code, "message": exc.message}
        )

    # Daftarkan semua router
    app.include_router(auth.router,       prefix="/api/v1/auth")
    app.include_router(cameras.router,    prefix="/api/v1/cameras")
    app.include_router(stream.router,     prefix="/api/v1/stream")
    app.include_router(recordings.router, prefix="/api/v1/recordings")
    app.include_router(events.router,     prefix="/api/v1/events")
    app.include_router(storage.router,    prefix="/api/v1/storage")
    app.include_router(users.router,      prefix="/api/v1/users")
    app.include_router(settings.router,   prefix="/api/v1/settings")
    app.include_router(system.router,     prefix="/api/v1/system")
    app.include_router(config_router.router,    prefix="/api/v1/config")
    app.include_router(discovery_router.router, prefix="/api/v1/discovery")

    return app


app = create_app()
