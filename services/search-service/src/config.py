import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/video_hosting")

    # Elasticsearch
    elasticsearch_hosts: str = os.getenv("ELASTICSEARCH_HOSTS", "http://elasticsearch:9200")
    elasticsearch_index: str = os.getenv("ELASTICSEARCH_INDEX", "videos")

    # Redis/Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    # Auth service (единая точка соприкосновения)
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    video_service_url: str = os.getenv("VIDEO_SERVICE_URL", "http://video-service:8001")
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "internal-secret-token")
    public_video_api_url: str = os.getenv("PUBLIC_VIDEO_API_URL", "http://localhost:8001")
    public_media_via_api: bool = os.getenv("PUBLIC_MEDIA_VIA_API", "true").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()
