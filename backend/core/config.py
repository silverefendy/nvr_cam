"""
Konfigurasi terpusat — semua setting dibaca dari .env
Tidak ada hardcode nilai di tempat lain selain file ini.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "cctv_db"
    db_user: str = "cctv_user"
    db_password: str = "changeme"

    # JWT
    jwt_secret: str = "changeme-secret-key-for-development-only"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Storage
    storage_threshold_pct: float = 10.0
    hls_temp_dir: str = "/tmp/hls"
    config_dir: str = "config"

    # App
    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
