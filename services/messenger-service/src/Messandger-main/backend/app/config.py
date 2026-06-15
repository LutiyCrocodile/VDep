from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/video_hosting"
    DB_SCHEMA: str = "messenger"
    DB_ENCRYPTION_KEY: str = ""
    DB_REQUIRE_TLS: bool = False

    REDIS_URL: str = "redis://localhost:6379"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    AUTH_SERVICE_URL: str = "http://localhost:8000"
    INTERNAL_AUTH_TOKEN: str = "internal-secret-token"
    PORTAL_URL: str = "http://localhost:3002"

    CORS_ORIGINS: str = "http://localhost:3005,http://localhost:3002,http://localhost:3000"

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 100
    ALLOWED_UPLOAD_EXT: str = (
        "jpg,jpeg,png,gif,webp,bmp,svg,"
        "mp4,webm,mov,mkv,avi,"
        "mp3,wav,ogg,m4a,opus,flac,aac,"
        "pdf,doc,docx,xls,xlsx,ppt,pptx,txt,csv,zip,rar,7z"
    )

    BACKUP_DIR: str = "backups"
    BACKUP_INTERVAL_HOURS: int = 6
    BACKUP_KEEP: int = 30

    ENV: str = "development"

    @property
    def cors_origins_list(self):
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions(self):
        return {e.strip().lower().lstrip(".") for e in self.ALLOWED_UPLOAD_EXT.split(",") if e.strip()}

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() in ("prod", "production")

    class Config:
        env_file = ".env"


settings = Settings()


def validate_security_config():
    """Проверка критичных параметров безопасности при старте."""
    import warnings

    if settings.is_production and "sqlite" in settings.DATABASE_URL and not settings.DB_ENCRYPTION_KEY:
        warnings.warn("В production рекомендуется DB_ENCRYPTION_KEY (SQLCipher) или PostgreSQL c TLS")
