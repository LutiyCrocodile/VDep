import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/video_hosting")

    # Auth service
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "internal-secret-token")

    # Notification service
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")

    # Video service (for archiving)
    video_service_url: str = os.getenv("VIDEO_SERVICE_URL", "http://video-service:8001")

    # RTMP settings
    rtmp_port: int = int(os.getenv("RTMP_PORT", "1935"))
    rtmp_app: str = os.getenv("RTMP_APP", "live")

    # HLS settings
    hls_segment_duration: int = int(os.getenv("HLS_SEGMENT_DURATION", "2"))  # seconds
    hls_playlist_length: int = int(os.getenv("HLS_PLAYLIST_LENGTH", "10"))  # segments
    dvr_max_duration: int = int(os.getenv("DVR_MAX_DURATION", "86400"))  # 24 hours in seconds

    # Stream keys
    stream_key_length: int = int(os.getenv("STREAM_KEY_LENGTH", "16"))

    # Redis/Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    class Config:
        env_file = ".env"

settings = Settings()
