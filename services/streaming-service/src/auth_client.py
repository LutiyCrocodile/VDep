"""
Auth client for streaming-service — uses the same RBAC service as video ("video").
"""
import httpx
from typing import Optional, Dict, List
from .config import settings
import logging

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self):
        self.auth_url = settings.auth_service_url
        self.internal_token = settings.internal_auth_token
        self.service_id = "video"

    async def verify_token(self, token: str) -> Optional[Dict]:
        async with httpx.AsyncClient() as client:
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
                logger.error(f"Auth service request failed: {e}")
                return None

    async def get_user_service_permissions(self, user_id: str) -> Optional[Dict]:
        async with httpx.AsyncClient() as client:
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
                logger.error(f"Failed to get user service permissions: {e}")
                return None


auth_client = AuthClient()
