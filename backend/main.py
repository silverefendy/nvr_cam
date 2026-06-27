"""
Entry point — jalankan API server dengan Uvicorn.
Usage: python backend/main.py
"""
import uvicorn
from backend.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
