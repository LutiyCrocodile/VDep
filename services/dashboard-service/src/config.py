"""
Configuration for Dashboard Service
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    service_name: str = "dashboard-service"
    port: int = 3003
    
    database_url: str = "postgresql+asyncpg://user:password@db:5432/video_hosting"
    redis_url: str = "redis://redis:6379/0"
    auth_service_url: str = "http://auth-service:8000"
    
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env


settings = Settings()
