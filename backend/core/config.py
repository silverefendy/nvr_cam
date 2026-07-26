"""
Konfigurasi terpusat — semua setting dibaca dari .env
Tidak ada hardcode nilai di tempat lain selain file ini.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

DEFAULT_DB_PASSWORD = "devpassword123"
DEFAULT_JWT_SECRET = "changeme-secret-key-for-development-only"
LOCAL_CORS_ORIGINS = (
    "http://localhost:3000,"
    "http://localhost:5173,"
    "http://127.0.0.1:3000,"
    "http://127.0.0.1:5173"
)


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nvr_cam"
    db_user: str = "nvr_user"
    db_password: str = DEFAULT_DB_PASSWORD

    # JWT
    jwt_secret: str = DEFAULT_JWT_SECRET
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
    # Path ini harus cocok dengan volume hls_data di docker-compose.yml
    # dan dengan yang di-serve Nginx: location /hls/ { alias /var/lib/nvr_cam/hls/; }
    hls_temp_dir: str = "/var/lib/nvr_cam/hls"
    config_dir: str = "config"

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_allow_origins: str = LOCAL_CORS_ORIGINS
    admin_password: str = ""

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    def model_post_init(self, __context) -> None:
        if self.app_env.lower() == "production":
            unsafe = []
            if self.db_password == DEFAULT_DB_PASSWORD:
                unsafe.append("DB_PASSWORD")
            if self.jwt_secret == DEFAULT_JWT_SECRET:
                unsafe.append("JWT_SECRET")
            if "*" in self.cors_origins:
                unsafe.append("CORS_ALLOW_ORIGINS")
            if unsafe:
                names = ", ".join(unsafe)
                raise RuntimeError(
                    f"Unsafe default production configuration: {names}. "
                    "Set strong values before starting with APP_ENV=production."
                )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
