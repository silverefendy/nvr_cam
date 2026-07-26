"""
Logging terpusat — semua service pakai logger dari sini.
Format: JSON agar mudah di-parse oleh monitoring tools.
"""
import logging
import json
from contextvars import ContextVar
from datetime import datetime, timezone
from .config import settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "app"),
            "request_id": getattr(record, "request_id", None) or request_id_ctx.get() or "-",
            "camera_id": getattr(record, "camera_id", None),
            "job_id": getattr(record, "job_id", None),
            "message": record.getMessage(),
            "module": record.module,
        }
        for key in ("action", "pid"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


def get_logger(name: str, service: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger = logging.LoggerAdapter(logger, {"service": service})
    return logger
