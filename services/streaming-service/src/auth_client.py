"""
Auth client for streaming-service — uses the same RBAC service as video ("video").
"""
import logging
from typing import Dict, Optional

import httpx

from .config import settings
from .http_client import get_http_client

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self):
        self.auth_url = settings.auth_service_url
        self.internal_token = settings.internal_auth_token
        self.service_id = "video"

    async def verify_token(self, token: str) -> Optional[Dict]:
        client = get_http_client()
        try:
            response = await client.get(
                f"{self.auth_url}/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError as e:
            logger.error("Auth service request failed: %s", e)
            return None

    async def get_user_service_permissions(self, user_id: str) -> Optional[Dict]:
        client = get_http_client()
        try:
            response = await client.get(
                f"{self.auth_url}/internal/users/{user_id}/services/{self.service_id}",
                headers={"Authorization": f"Bearer {self.internal_token}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError as e:
            logger.error("Failed to get user service permissions: %s", e)
            return None


auth_client = AuthClient()
