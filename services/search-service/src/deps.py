"""Зависимости FastAPI (аутентификация)."""
from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .http_client import get_http_client

security = HTTPBearer(auto_error=False)
internal_bearer = HTTPBearer(auto_error=True)


async def require_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    client = get_http_client()
    try:
        response = await client.get(
            f"{settings.auth_service_url}/users/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if response.status_code == 200:
            return response.json()["id"]
        raise HTTPException(status_code=401, detail="Недействительный токен")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Сервис авторизации недоступен") from e
