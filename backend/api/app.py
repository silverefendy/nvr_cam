"""
FastAPI application factory.
Semua router didaftarkan di sini.
"""
import asyncio
import uuid
import yaml
import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.exceptions import CCTVBaseException
from backend.core.logging import get_logger
from backend.core.logging import request_id_ctx
from backend.core.config import settings as app_settings
from backend.api.routers import (
    auth, cameras, stream, recordings, events, storage, users,
    settings as settings_router, system,
    config as config_router, discovery as discovery_router,
    audit_logs as audit_logs_router,
    camera_groups as camera_groups_router,
)
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.camera import Camera
from backend.db.models.app_setting import AppSetting
from backend.services.recorder.manager import RecordingManager
from backend.services.storage.manager import StorageManager
from backend.services.motion.manager import MotionManager
from backend.services.transcode_queue import TranscodeQueue
from backend.api.websocket import ConnectionManager
from sqlalchemy import select

logger = get_logger(__name__, service="api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup dan shutdown logic."""
    logger.info("Starting NVR API service...")

    recording_manager = RecordingManager.get_instance()
    storage_manager = None
    motion_manager = None

    try:
        # 1. Seed any missing app settings or cameras from YAML files
        async with AsyncSessionLocal() as db:
            # Seed app settings
            res = await db.execute(select(AppSetting).where(AppSetting.key == "system"))
            if not res.scalar_one_or_none():
                system_yaml_path = Path(__file__).parent.parent.parent / "config" / "system.yaml"
                if system_yaml_path.exists():
                    with open(system_yaml_path) as f:
                        sys_data = yaml.safe_load(f) or {}
                    db.add(AppSetting(key="system", value=json.dumps(sys_data)))
                    logger.info("Seeded system settings from YAML")

            res = await db.execute(select(AppSetting).where(AppSetting.key == "storage"))
            if not res.scalar_one_or_none():
                storage_yaml_path = Path(__file__).parent.parent.parent / "config" / "storage.yaml"
                if storage_yaml_path.exists():
                    with open(storage_yaml_path) as f:
                        stor_data = yaml.safe_load(f) or {}
                    db.add(AppSetting(key="storage", value=json.dumps(stor_data)))
                    logger.info("Seeded storage settings from YAML")

            res = await db.execute(select(AppSetting).where(AppSetting.key == "notification"))
            if not res.scalar_one_or_none():
                notif_data = {
                    "telegram_bot_token": app_settings.telegram_bot_token,
                    "telegram_chat_id": app_settings.telegram_chat_id,
                    "smtp_host": app_settings.smtp_host,
                    "smtp_port": app_settings.smtp_port,
                    "smtp_user": app_settings.smtp_user,
                    "smtp_password": app_settings.smtp_password,
                }
                db.add(AppSetting(key="notification", value=json.dumps(notif_data)))
                logger.info("Seeded notification settings from .env")

            # Seed cameras
            camera_repo = CameraRepository(db)
            cameras = await camera_repo.get_active_cameras()

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
                    cameras = await camera_repo.get_active_cameras()
                    logger.info(f"Seeded {len(cameras)} cameras from config")

            await db.commit()

        # 2. Load database settings into backend/core/config.py settings in-memory cache
        from backend.utils.config_manager import load_db_settings_into_config
        await load_db_settings_into_config()

        # Convert cameras to dict for RecordingManager
        camera_dicts = []
        for cam in cameras:
            camera_dicts.append({
                "id": cam.id,
                "name": cam.name,
                "location": cam.location,
                "rtsp_main": cam.rtsp_main,
                "rtsp_sub": cam.rtsp_sub,
                "rtsp_url_main": cam.rtsp_url_main,
                "rtsp_url_sub": cam.rtsp_url_sub,
                "storage_drive": cam.storage_drive,
                "motion_enabled": cam.motion_enabled,
                "retention_days": cam.retention_days,
                "segment_duration": getattr(cam, "segment_duration", 3600),
                "status": getattr(cam, "status", "offline"),
                "is_active": cam.is_active,
                "config_json": cam.config_json,
                "recording_schedule": cam.recording_schedule,
                "schedule_start_time": cam.schedule_start_time,
                "schedule_end_time": cam.schedule_end_time,
                "schedule_days": cam.schedule_days,
            })

        logger.info(f"Starting recording for {len(camera_dicts)} cameras")
        asyncio.create_task(recording_manager.start_all(camera_dicts))

        camera_drive_map = {cam["id"]: cam["storage_drive"] for cam in camera_dicts}
        storage_manager = StorageManager(camera_drive_map)
        recording_manager.storage_manager = storage_manager
        asyncio.create_task(storage_manager.monitor_loop())
        logger.info("Storage manager started")

        motion_cameras = [cam for cam in camera_dicts if cam.get("motion_enabled")]
        if motion_cameras:
            motion_manager = MotionManager()
            asyncio.create_task(motion_manager.start_all(motion_cameras))
            logger.info(f"Motion detection started for {len(motion_cameras)} cameras")

        app.state.recording_manager = recording_manager
        app.state.storage_manager = storage_manager
        app.state.motion_manager = motion_manager
        transcode_queue = TranscodeQueue.get_instance()
        transcode_queue.start()
        app.state.transcode_queue = transcode_queue
        app.state.websocket_manager = ConnectionManager()

        # Startup a background cleanup routine
        try:
            from backend.services.storage.cleanup import start_cleanup_worker
            start_cleanup_worker()
            logger.info("Orphan metadata cleanup worker started")
        except Exception as e:
            logger.error(f"Failed to start cleanup worker: {e}")

        # Startup a background health checker routine
        try:
            from backend.services.health.checker import start_health_checker
            start_health_checker()
            logger.info("Camera health checker started")
        except Exception as e:
            logger.error(f"Failed to start health checker: {e}")

        # Startup a background export cleanup routine
        try:
            from backend.services.recorder.exporter import start_export_cleanup_worker
            start_export_cleanup_worker()
            logger.info("Export cleanup worker started")
        except Exception as e:
            logger.error(f"Failed to start export cleanup worker: {e}")

        logger.info("NVR API service started successfully")

    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down NVR API service...")

    try:
        await recording_manager.stop_all()
        logger.info("Recording manager stopped")

        if motion_manager:
            await motion_manager.stop_all()
            logger.info("Motion manager stopped")

        transcode_queue = getattr(app.state, "transcode_queue", None)
        if transcode_queue:
            await transcode_queue.stop()
            logger.info("Transcode queue stopped")

        from backend.db.base import engine
        await engine.dispose()
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(CCTVBaseException)
    async def cctv_exception_handler(request: Request, exc: CCTVBaseException):
        return JSONResponse(
            status_code=400,
            content={"error": exc.code, "message": exc.message}
        )

    app.include_router(auth.router,              prefix="/api/v1/auth")
    app.include_router(cameras.router,           prefix="/api/v1/cameras")
    app.include_router(stream.router,            prefix="/api/v1/stream")
    app.include_router(recordings.router,        prefix="/api/v1/recordings")
    app.include_router(events.router,            prefix="/api/v1/events")
    app.include_router(storage.router,           prefix="/api/v1/storage")
    app.include_router(users.router,             prefix="/api/v1/users")
    app.include_router(settings_router.router,   prefix="/api/v1/settings")
    app.include_router(system.router,            prefix="/api/v1/system")
    app.include_router(config_router.router,     prefix="/api/v1/config")
    app.include_router(discovery_router.router,  prefix="/api/v1/discovery")
    app.include_router(audit_logs_router.router, prefix="/api/v1/audit-logs")
    app.include_router(camera_groups_router.router, prefix="/api/v1/camera-groups")

    return app


app = create_app()
