from __future__ import annotations

from datetime import timedelta

from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import SECRET_KEY

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="helpdesk-session")


def hash_password(password: str) -> str:
    password = password.strip()
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    password = password.strip()
    return pwd_context.verify(password, password_hash)


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_token(token: str, max_age: timedelta) -> int | None:
    try:
        data = _serializer.loads(token, max_age=int(max_age.total_seconds()))
    except BadSignature:
        return None
    user_id = data.get("user_id")
    if not isinstance(user_id, int):
        return None
    return user_id
