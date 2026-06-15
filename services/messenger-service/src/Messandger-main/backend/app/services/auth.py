from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_client import auth_client
from app.database import get_db
from app.models.user import User
from app.services.profiles import ensure_messenger_profile

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация через портал",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_user = await auth_client.verify_token(credentials.credentials)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован")

    service_access = await auth_client.get_messenger_access(auth_user["id"])
    if not service_access or not service_access.get("role") or not service_access.get("permissions"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к мессенджеру. Обратитесь в Управление информатизации",
        )

    user = await ensure_messenger_profile(db, auth_user)
    
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован в мессенджере. Обратитесь к администратору",
        )

    return user
