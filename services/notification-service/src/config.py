import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/video_hosting")

    # Redis/Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    # SMTP settings
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.dgi.mos.ru")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "true").lower() in ("1", "true", "yes")
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "notifications@video.dgi.mos.ru")

    # Auth / video services
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    video_service_url: str = os.getenv("VIDEO_SERVICE_URL", "http://video-service:8001")
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "internal-secret-token")
    frontend_public_url: str = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:3000").rstrip("/")

    # WebSocket settings
    websocket_heartbeat: int = int(os.getenv("WEBSOCKET_HEARTBEAT", "30"))

    class Config:
        env_file = ".env"

settings = Settings()
