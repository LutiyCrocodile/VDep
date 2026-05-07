"""
Auth client for video-service to communicate with auth-service.
Supports both standalone (dev) and shared (prod) modes.
"""
import httpx
from typing import Optional, Dict, List
from .config import settings
import logging

logger = logging.getLogger(__name__)

class AuthClient:
    """Client for authentication service"""
    
    def __init__(self):
        self.auth_url = settings.auth_service_url
        self.internal_token = settings.internal_auth_token
        self.service_id = "video"  # This service's identifier
    
    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token with auth service"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.auth_url}/api/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError as e:
                logger.error(f"Auth service request failed: {e}")
                return None
    
    async def get_user_service_permissions(self, user_id: str) -> Optional[Dict]:
        """Get user's permissions for this service (video)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.auth_url}/internal/users/{user_id}/services/{self.service_id}",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError as e:
                logger.error(f"Failed to get user service permissions: {e}")
                return None
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission in this service"""
        perms = await self.get_user_service_permissions(user_id)
        if not perms:
            return False
        return permission in perms.get("permissions", [])
    
    async def list_service_users(self) -> List[Dict]:
        """List all users with access to this service"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.auth_url}/internal/services/{self.service_id}/users",
                    headers={"Authorization": f"Bearer {self.internal_token}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("users", [])
                return []
            except httpx.RequestError as e:
                logger.error(f"Failed to list service users: {e}")
                return []

# Global instance
auth_client = AuthClient()
