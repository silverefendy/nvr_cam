"""
Logging terpusat — semua service pakai logger dari sini.
Format: JSON agar mudah di-parse oleh monitoring tools.
"""
import logging
import json
from datetime import datetime, timezone
from .config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "app"),
            "message": record.getMessage(),
            "module": record.module,
        })


def get_logger(name: str, service: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger = logging.LoggerAdapter(logger, {"service": service})
    return logger
