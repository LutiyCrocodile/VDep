import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/video_hosting")

    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Service identification for multi-service architecture
    service_id: str = os.getenv("SERVICE_ID", "video")  # 'video', 'messenger', 'dashboard', 'support'
    service_name: str = os.getenv("SERVICE_NAME", "Видеохостинг ДГИ")
    
    # Auth mode: 'standalone' (default, dev) or 'shared' (production with external auth)
    auth_mode: str = os.getenv("AUTH_MODE", "standalone")  # 'standalone' or 'shared'
    
    # Shared auth service URL (used when auth_mode='shared')
    shared_auth_url: str = os.getenv("SHARED_AUTH_URL", "http://auth-service:8000")

    # Internal auth token for service-to-service communication
    internal_auth_token: str = os.getenv("INTERNAL_AUTH_TOKEN", "internal-secret-token-change-in-production")

    # LDAP (for Active Directory integration)
    ldap_server: str = os.getenv("LDAP_SERVER", "")
    ldap_base_dn: str = os.getenv("LDAP_BASE_DN", "DC=dgi,DC=mos,DC=ru")
    ldap_bind_user: str = os.getenv("LDAP_BIND_USER", "")
    ldap_bind_password: str = os.getenv("LDAP_BIND_PASSWORD", "")

    # ESIA (for external authentication)
    esia_client_id: str = os.getenv("ESIA_CLIENT_ID", "")
    esia_client_secret: str = os.getenv("ESIA_CLIENT_SECRET", "")
    esia_redirect_uri: str = os.getenv("ESIA_REDIRECT_URI", "")

    # Registration control
    allow_registration: bool = os.getenv("ALLOW_REGISTRATION", "false").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()
