import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.http_client import get_http_client

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self):
        self.auth_url = settings.AUTH_SERVICE_URL.rstrip("/")
        self.internal_token = settings.INTERNAL_AUTH_TOKEN
        self.service_slug = "messenger"

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        client = get_http_client()
        try:
            response = await client.get(
                f"{self.auth_url}/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as exc:
            logger.error("Auth service request failed: %s", exc)
            return None

    async def get_messenger_access(self, user_id: str) -> Optional[Dict[str, Any]]:
        client = get_http_client()
        try:
            response = await client.get(
                f"{self.auth_url}/internal/users/{user_id}/services/{self.service_slug}",
                headers={"Authorization": f"Bearer {self.internal_token}"},
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as exc:
            logger.error("Failed to get messenger service access: %s", exc)
            return None

    async def search_users(self, token: str, query: str) -> List[Dict[str, Any]]:
        client = get_http_client()
        try:
            response = await client.get(
                f"{self.auth_url}/users/search",
                params={"q": query},
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return response.json().get("users", [])
            return []
        except Exception as exc:
            logger.error("User search failed: %s", exc)
            return []

    async def get_contacts(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        if not user_ids:
            return []
        client = get_http_client()
        try:
            response = await client.post(
                f"{self.auth_url}/internal/users/contacts",
                json={"user_ids": user_ids},
                headers={"Authorization": f"Bearer {self.internal_token}"},
            )
            if response.status_code == 200:
                return response.json().get("contacts", [])
            return []
        except Exception as exc:
            logger.error("Failed to fetch contacts: %s", exc)
            return []

    async def update_user(self, user_id: str, full_name: Optional[str] = None) -> bool:
        """Update user in auth-service (syncs full_name across all services)"""
        if not full_name:
            return True
        client = get_http_client()
        try:
            response = await client.post(
                f"{self.auth_url}/internal/users/{user_id}/update",
                json={"full_name": full_name},
                headers={"Authorization": f"Bearer {self.internal_token}"},
            )
            return response.status_code == 200
        except Exception as exc:
            logger.error("Failed to update user in auth-service: %s", exc)
            return False


auth_client = AuthClient()
