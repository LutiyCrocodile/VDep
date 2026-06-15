from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


DATABASE_URL = get_env("DATABASE_URL")
SECRET_KEY = get_env("SECRET_KEY", "change-me")
APP_NAME = get_env("APP_NAME", "Helpdesk")
ENV = get_env("ENV", "dev")
PUBLIC_BASE_URL = get_env("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
AUTH_SERVICE_URL = get_env("AUTH_SERVICE_URL", "http://auth-service:8000")
INTERNAL_AUTH_TOKEN = get_env("INTERNAL_AUTH_TOKEN", "internal-secret-token")
PORTAL_URL = get_env("PORTAL_URL", "http://localhost:3002")
DB_SCHEMA = get_env("DB_SCHEMA", "support")
