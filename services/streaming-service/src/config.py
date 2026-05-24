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

    # Video service (channel check + archive upload)
    video_service_url: str = os.getenv("VIDEO_SERVICE_URL", "http://video-service:8001")

    # RTMP / HLS (MediaMTX)
    public_rtmp_host: str = os.getenv("PUBLIC_RTMP_HOST", "localhost")
    public_rtmp_port: int = int(os.getenv("PUBLIC_RTMP_PORT", "1935"))
    public_hls_base: str = os.getenv("PUBLIC_HLS_BASE", "http://localhost:8888")
    rtmp_app: str = os.getenv("RTMP_APP", "live")
    mediamtx_api_url: str = os.getenv("MEDIAMTX_API_URL", "http://mediamtx:9997")

    # Shared volume with MediaMTX recordings
    recordings_path: str = os.getenv("RECORDINGS_PATH", "/recordings")
    # После остановки эфира: если дольше — считаем зависшей архивацией
    archive_stale_seconds: int = int(os.getenv("ARCHIVE_STALE_SECONDS", "120"))

    # RTMP settings (metadata)
    rtmp_port: int = int(os.getenv("RTMP_PORT", "1935"))
    hls_segment_duration: int = int(os.getenv("HLS_SEGMENT_DURATION", "2"))
    hls_playlist_length: int = int(os.getenv("HLS_PLAYLIST_LENGTH", "10"))
    dvr_max_duration: int = int(os.getenv("DVR_MAX_DURATION", "86400"))

    stream_key_length: int = int(os.getenv("STREAM_KEY_LENGTH", "16"))

    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    class Config:
        env_file = ".env"


settings = Settings()
