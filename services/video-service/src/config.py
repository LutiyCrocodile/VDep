import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/video_hosting")

    # MinIO
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "videos")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    minio_external_endpoint: str = os.getenv("MINIO_EXTERNAL_ENDPOINT", "localhost:9000")  # For frontend access
    # Публичный URL video-service для браузера (HLS/превью через /media — без CORS MinIO)
    public_video_api_url: str = os.getenv("PUBLIC_VIDEO_API_URL", "http://localhost:8001")
    public_media_via_api: bool = os.getenv("PUBLIC_MEDIA_VIA_API", "true").lower() == "true"

    # Auth service
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "internal-secret-token")
    notification_service_url: str = os.getenv(
        "NOTIFICATION_SERVICE_URL", "http://notification-service:8003"
    )
    search_service_url: str = os.getenv(
        "SEARCH_SERVICE_URL", "http://search-service:8004"
    )
    frontend_public_url: str = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:3000").rstrip("/")

    # Upload settings
    upload_expiry_seconds: int = int(os.getenv("UPLOAD_EXPIRY_SECONDS", "3600"))
    signed_url_expiry_seconds: int = int(os.getenv("SIGNED_URL_EXPIRY_SECONDS", "3600"))
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10737418240"))  # 10GB

    # Transcoding settings
    transcoding_qualities: List[str] = ["180p", "360p", "480p", "720p", "1080p"]
    hls_segment_duration: int = 10  # seconds

    # Redis/Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    # RabbitMQ
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    class Config:
        env_file = ".env"

settings = Settings()
