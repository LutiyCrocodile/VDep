from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: str
    last_name: str
    department: Optional[str] = None
    position: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    status: str
    last_seen: datetime
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    avatar_url: Optional[str] = None
