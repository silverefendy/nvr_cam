"""
FastAPI application factory.
Semua router didaftarkan di sini.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.exceptions import CCTVBaseException
from backend.api.routers import auth, cameras, stream, recordings, events, storage, users, settings, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup dan shutdown logic."""
    # TODO: start RecordingManager, StorageManager, dll
    yield
    # TODO: stop semua service dengan bersih


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

    return app


app = create_app()
