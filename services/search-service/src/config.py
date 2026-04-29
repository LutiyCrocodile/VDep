import os
from pydantic import BaseSettings

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

    # Auth service
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

    class Config:
        env_file = ".env"

settings = Settings()
