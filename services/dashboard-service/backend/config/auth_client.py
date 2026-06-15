from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self, auth_url: str = None, internal_token: str = None):
        self.auth_url = (auth_url or "http://auth-service:8000").rstrip("/")
        self.internal_token = internal_token or "internal-secret-token"
        self.service_slug = "dashboard"

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        token = (token or "").strip()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as client:
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

    async def get_service_access(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.auth_url}/internal/users/{user_id}/services/{self.service_slug}",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as exc:
            logger.error("Failed to get dashboard service access: %s", exc)
            return None

    async def get_all_service_access(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's access to all services"""
        if not user_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.auth_url}/internal/users/{user_id}/services",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as exc:
            logger.error("Failed to get all service access: %s", exc)
            return None

    async def search_users(self, token: str, query: str) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
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

    async def get_user_profile_internal(
        self,
        user_id: str,
    ) -> dict | None:
        """Get user profile from auth-service (internal)"""
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.auth_url}/internal/users/{user_id}/profile-mini",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as exc:
            logger.error("Failed to get user profile from auth-service: %s", exc)
            return None


# Singleton instance
auth_client = AuthClient()
