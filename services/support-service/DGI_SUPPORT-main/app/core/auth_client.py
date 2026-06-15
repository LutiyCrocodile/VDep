from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import AUTH_SERVICE_URL, INTERNAL_AUTH_TOKEN

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self):
        self.auth_url = AUTH_SERVICE_URL.rstrip("/")
        self.internal_token = INTERNAL_AUTH_TOKEN
        self.service_slug = "support"

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
            logger.error("Failed to get support service access: %s", exc)
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

    async def create_user_internal(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str | None,
        role: str = "user",
        is_employee: bool = True,
    ) -> tuple[int, dict | None]:
        try:
            url = f"{self.auth_url}/internal/users/create"
            logger.info(f"POST to auth-service: {url}")
            logger.info(f"Payload: username={username}, email={email}, role={role}, is_employee={is_employee}")
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                    json={
                        "username": username,
                        "email": email,
                        "password": password,
                        "full_name": full_name,
                        "role": role,
                        "is_employee": is_employee,
                        "service_slug": self.service_slug,
                        "service_role": role,
                    },
                )
                logger.info(f"Auth-service response status: {response.status_code}")
                logger.info(f"Auth-service response body: {response.text}")
                try:
                    return response.status_code, response.json()
                except Exception:
                    return response.status_code, {"detail": response.text}
        except Exception as exc:
            logger.error("Failed to create user in auth-service: %s", exc)
            return 0, None

    async def update_user_internal(
        self,
        user_id: str,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
        full_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[int, dict | None]:
        payload: dict[str, object] = {}
        if username is not None:
            payload["username"] = username
        if email is not None:
            payload["email"] = email
        if password is not None:
            payload["password"] = password
        if full_name is not None:
            payload["full_name"] = full_name
        if role is not None:
            payload["role"] = role
        if is_active is not None:
            payload["is_active"] = is_active

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    f"{self.auth_url}/internal/users/{user_id}/update",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                    json=payload,
                )
                logger.info(f"Auth-service update response: status={response.status_code}, body={response.text}")
                return response.status_code, response.json() if response.status_code == 200 else None
        except Exception as exc:
            logger.error("Failed to update user in auth-service: %s", exc)
            return 0, None

    async def delete_user_internal(
        self,
        user_id: str,
    ) -> tuple[int, dict | None]:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    f"{self.auth_url}/internal/users/{user_id}/delete",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                )
                return response.status_code, response.json() if response.status_code == 200 else None
        except Exception as exc:
            logger.error("Failed to delete user in auth-service: %s", exc)
            return 0, None

    async def get_services(self) -> list[dict]:
        """Get list of all services with their roles"""
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.auth_url}/internal/services",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                )
                if response.status_code == 200:
                    return response.json().get("services", [])
                return []
        except Exception as exc:
            logger.error("Failed to get services: %s", exc)
            return []

    async def assign_service_role(
        self,
        user_id: str,
        service_slug: str,
        role_name: str,
    ) -> tuple[int, dict | None]:
        """Assign a role to a user for a specific service"""
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(
                    f"{self.auth_url}/internal/users/{user_id}/services/{service_slug}/role",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                    json={"role": role_name},
                )
                logger.info(f"Assign service role response: status={response.status_code}, body={response.text}")
                return response.status_code, response.json() if response.status_code == 200 else None
        except Exception as exc:
            logger.error("Failed to assign service role: %s", exc)
            return 0, None

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


auth_client = AuthClient()

