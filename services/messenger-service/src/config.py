"""
Configuration for Messenger Service
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service
    service_name: str = "messenger-service"
    port: int = 3001
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@db:5432/video_hosting"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Auth service
    auth_service_url: str = "http://auth-service:8000"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env


settings = Settings()
