from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uvicorn
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import ldap
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import logging
import hashlib

from .database import get_db, create_tables, async_session, User, Role, Permission, Service, ServiceRole, ServicePermission, ServiceRolePermission, UserServiceRole
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security = HTTPBearer()

# JWT settings
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# LDAP settings (for integration with Active Directory)
LDAP_SERVER = settings.ldap_server
LDAP_BASE_DN = settings.ldap_base_dn
LDAP_BIND_USER = settings.ldap_bind_user
LDAP_BIND_PASSWORD = settings.ldap_bind_password

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role_id: Optional[str] = None
    full_name: Optional[str] = None
    is_employee: bool = True

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    is_employee: bool = True
    full_name: Optional[str] = None
    services: Optional[dict] = None


class InternalUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "user"
    is_employee: bool = True
    service_slug: Optional[str] = None
    service_role: Optional[str] = None


class InternalUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

async def initialize_services(db: AsyncSession):
    """Initialize default services, roles, and permissions for multi-service architecture"""
    from sqlalchemy import text

    services = [
        {"slug": "video", "name": "Видеохостинг ДГИ", "description": "Система видеохостинга"},
        {"slug": "messenger", "name": "Мессенджер ДГИ", "description": "Корпоративный мессенджер"},
        {"slug": "dashboard", "name": "Дашборд ДГИ", "description": "Аналитический дашборд"},
        {"slug": "support", "name": "Техподдержка ДГИ", "description": "Система техподдержки"},
    ]

    # Service-specific roles and permissions definitions
    service_definitions = {
        "video": {
            "roles": [
                {"name": "admin", "description": "Video service administrator"},
                {"name": "manager", "description": "Video service manager"},
                {"name": "uploader", "description": "Can upload and manage own videos"},
                {"name": "viewer", "description": "Can view public videos"}
            ],
            "permissions": [
                {"name": "video:upload", "description": "Can upload videos"},
                {"name": "video:view_private", "description": "Can view private videos"},
                {"name": "video:manage_own", "description": "Can manage own videos"},
                {"name": "video:manage_all", "description": "Can manage all videos"},
                {"name": "video:stream", "description": "Can create live streams"},
                {"name": "video:moderate", "description": "Can moderate content"},
                {"name": "video:audit", "description": "Can view audit logs"}
            ],
            "role_permissions": {
                "admin": ["video:upload", "video:view_private", "video:manage_all", "video:stream", "video:moderate", "video:audit"],
                "manager": ["video:upload", "video:view_private", "video:stream"],
                "uploader": ["video:upload", "video:manage_own"],
                "viewer": ["video:stream"],
            }
        },
        "messenger": {
            "roles": [
                {"name": "admin", "description": "Messenger administrator"},
                {"name": "moderator", "description": "Can moderate chats"},
                {"name": "user", "description": "Regular messenger user"}
            ],
            "permissions": [
                {"name": "messenger:send", "description": "Can send messages"},
                {"name": "messenger:create_chat", "description": "Can create group chats"},
                {"name": "messenger:moderate", "description": "Can moderate messages"},
                {"name": "messenger:admin", "description": "Full messenger administration"}
            ],
            "role_permissions": {
                "admin": ["messenger:send", "messenger:create_chat", "messenger:moderate", "messenger:admin"],
                "moderator": ["messenger:send", "messenger:create_chat", "messenger:moderate"],
                "user": ["messenger:send"]
            }
        },
        "dashboard": {
            "roles": [
                {"name": "admin", "description": "Dashboard administrator"},
                {"name": "viewer", "description": "Can view dashboard data"},
                {"name": "editor", "description": "Can edit dashboard configurations"}
            ],
            "permissions": [
                {"name": "dashboard:view", "description": "Can view dashboard"},
                {"name": "dashboard:edit", "description": "Can edit dashboard"},
                {"name": "dashboard:admin", "description": "Full dashboard administration"}
            ],
            "role_permissions": {
                "admin": ["dashboard:view", "dashboard:edit", "dashboard:admin"],
                "editor": ["dashboard:view", "dashboard:edit"],
                "viewer": ["dashboard:view"]
            }
        },
        "support": {
            "roles": [
                {"name": "admin", "description": "Support administrator"},
                {"name": "agent", "description": "Support agent"},
                {"name": "user", "description": "Can submit support tickets"}
            ],
            "permissions": [
                {"name": "support:create_ticket", "description": "Can create support tickets"},
                {"name": "support:respond", "description": "Can respond to tickets"},
                {"name": "support:close", "description": "Can close tickets"},
                {"name": "support:admin", "description": "Full support administration"}
            ],
            "role_permissions": {
                "admin": ["support:create_ticket", "support:respond", "support:close", "support:admin"],
                "agent": ["support:create_ticket", "support:respond", "support:close"],
                "user": ["support:create_ticket"]
            }
        }
    }

    for svc in services:
        # Check if service exists
        result = await db.execute(
            text("SELECT id FROM services WHERE slug = :slug"),
            {"slug": svc["slug"]}
        )
        service_row = result.first()
        if not service_row:
            # Create service
            result = await db.execute(
                text("INSERT INTO services (id, slug, name, description, is_active) VALUES (gen_random_uuid(), :slug, :name, :description, true) RETURNING id"),
                svc
            )
            service_id = result.first().id
            logger.info(f"Created service: {svc['name']}")
        else:
            service_id = service_row.id

        # Initialize service-specific roles and permissions
        svc_def = service_definitions.get(svc["slug"])
        if svc_def:
            # Create permissions
            for perm in svc_def["permissions"]:
                result = await db.execute(
                    text("SELECT id FROM service_permissions WHERE service_id = :service_id AND name = :name"),
                    {"service_id": service_id, "name": perm["name"]}
                )
                if not result.first():
                    await db.execute(
                        text("INSERT INTO service_permissions (id, service_id, name, description) VALUES (gen_random_uuid(), :service_id, :name, :description)"),
                        {"service_id": service_id, **perm}
                    )

            # Create roles
            for role in svc_def["roles"]:
                result = await db.execute(
                    text("SELECT id FROM service_roles WHERE service_id = :service_id AND name = :name"),
                    {"service_id": service_id, "name": role["name"]}
                )
                role_row = result.first()
                if not role_row:
                    result = await db.execute(
                        text("INSERT INTO service_roles (id, service_id, name, description, is_active) VALUES (gen_random_uuid(), :service_id, :name, :description, true) RETURNING id"),
                        {"service_id": service_id, **role}
                    )
                    role_id = result.first().id
                else:
                    role_id = role_row.id

                # Assign permissions to role
                perm_names = svc_def["role_permissions"].get(role["name"], [])
                for perm_name in perm_names:
                    # Get permission id
                    perm_result = await db.execute(
                        text("SELECT id FROM service_permissions WHERE service_id = :service_id AND name = :name"),
                        {"service_id": service_id, "name": perm_name}
                    )
                    perm_row = perm_result.first()
                    if perm_row:
                        # Check if role-permission exists
                        rp_result = await db.execute(
                            text("SELECT 1 FROM service_role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
                            {"role_id": role_id, "perm_id": perm_row.id}
                        )
                        if not rp_result.first():
                            await db.execute(
                                text("INSERT INTO service_role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"),
                                {"role_id": role_id, "perm_id": perm_row.id}
                            )

    await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    
    # Initialize services
    async with async_session() as db:
        await initialize_services(db)
    
    logger.info(f"Auth service started in {settings.auth_mode} mode")
    logger.info(f"Service ID: {settings.service_id}")
    yield
    # Shutdown
    logger.info("Auth service shutting down")

app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)

# CORS middleware
def _cors_allow_origins() -> list:
    raw = (settings.cors_origins or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:5173",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    password_bytes = plain_password.encode("utf-8")[:72]
    try:
        if isinstance(hashed_password, bytes):
            hashed_bytes = hashed_password
        else:
            hashed_bytes = str(hashed_password).encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

async def create_access_token(data: dict, db: AsyncSession, expires_delta: Optional[timedelta] = None):
    """Create JWT with service-specific permissions"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    
    # Add service permissions and employee status if user_id present
    if "sub" in to_encode:
        user = await User.get_by_username(db, to_encode["sub"])
        if user:
            try:
                services = await user.get_service_permissions(db)
                to_encode["services"] = services
            except Exception:
                logger.exception("get_service_permissions failed for user %s; token without services", user.username)
                to_encode["services"] = {}
            to_encode["is_employee"] = getattr(user, "is_employee", True)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(db: AsyncSession, username: str, password: str):
    # First try local authentication
    user = await User.get_by_username(db, username)
    if user and user.password_hash and verify_password(password, user.password_hash):
        return user

    # If not found locally, try LDAP (only when LDAP_SERVER задан в окружении)
    if user is None and LDAP_SERVER and LDAP_SERVER.strip():
        ldap_user = await authenticate_ldap(username, password)
        if ldap_user:
            # Create user in local DB if authenticated via LDAP
            role = await Role.get_by_name(db, "user")  # глобальная роль из seed / 005_bootstrap
            user_data = {
                "username": username,
                "email": f"{username}@dgi.mos.ru",  # Assume domain
                "ldap_dn": ldap_user['dn'],
                "role_id": role.id if role else None
            }
            user = await User.create(db, **user_data)
            return user

    return False

async def authenticate_ldap(username: str, password: str) -> Optional[dict]:
    try:
        ldap_client = ldap.initialize(LDAP_SERVER)
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        ldap_client.simple_bind_s(f"{username}@{LDAP_BASE_DN.split(',')[0].split('=')[1]}", password)

        # Search for user details
        search_filter = f"(sAMAccountName={username})"
        search_attrs = ['dn', 'displayName', 'mail', 'memberOf']

        result = ldap_client.search_s(LDAP_BASE_DN, ldap.SCOPE_SUBTREE, search_filter, search_attrs)
        ldap_client.unbind_s()

        if result:
            dn, attrs = result[0]
            return {
                'dn': dn,
                'displayName': attrs.get('displayName', [b''])[0].decode('utf-8'),
                'mail': attrs.get('mail', [b''])[0].decode('utf-8'),
                'groups': [g.decode('utf-8') for g in attrs.get('memberOf', [])]
            }
    except ldap.INVALID_CREDENTIALS:
        return None
    except Exception as e:
        logger.error(f"LDAP authentication error: {e}")
        return None

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _is_token_revoked(db: AsyncSession, token: str) -> bool:
    # Best-effort cleanup of expired revoked tokens
    await db.execute(text("DELETE FROM revoked_tokens WHERE expires_at < now()"))
    res = await db.execute(
        text("SELECT 1 FROM revoked_tokens WHERE token_hash = :h LIMIT 1"),
        {"h": _token_hash(token)},
    )
    return res.first() is not None


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if await _is_token_revoked(db, token):
            raise credentials_exception
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = await User.get_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke current access token so other services (messenger/video/etc)
    see 401 and logout too.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Token required")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if not exp:
            # If token has no exp, revoke for short time
            expires_at = datetime.utcnow() + timedelta(minutes=30)
        else:
            expires_at = datetime.utcfromtimestamp(int(exp))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    await db.execute(
        text("""
            INSERT INTO revoked_tokens (token_hash, expires_at)
            VALUES (:h, :expires_at)
            ON CONFLICT (token_hash) DO UPDATE SET expires_at = EXCLUDED.expires_at
        """),
        {"h": _token_hash(token), "expires_at": expires_at},
    )
    await db.commit()
    return {"status": "ok"}

@app.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if registration is allowed
    if not settings.allow_registration:
        raise HTTPException(
            status_code=403,
            detail="Registration is currently disabled. Please contact administrator."
        )
    
    # Check if user exists
    existing_user = await User.get_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    existing_email = await User.get_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Get or create default role
    role_id = user_data.role_id
    if not role_id:
        default_role = await Role.get_by_name(db, "user")
        if not default_role:
            # Create default role if not exists
            role_id = await Role.create(db, name="user", description="Default user role")
        else:
            role_id = str(default_role.id)

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_employee=user_data.is_employee
    )
    user = await db.merge(new_user)
    await db.commit()

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.name if user.role else "none",
        is_active=user.is_active
    )

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await create_access_token(data={"sub": user.username}, db=db)
    refresh_token = create_refresh_token(data={"sub": user.username})

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token
    )

@app.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = await User.get_by_username(db, username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        access_token = await create_access_token(data={"sub": user.username}, db=db)
        new_refresh_token = create_refresh_token(data={"sub": user.username})

        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/users/search")
async def search_users(
    q: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search users by username or email"""
    search_pattern = f"%{q}%"
    result = await db.execute(
        text("""
            SELECT id, username, email, is_active
            FROM users
            WHERE (username ILIKE :pattern OR email ILIKE :pattern)
            AND is_active = true
            LIMIT 10
        """),
        {"pattern": search_pattern}
    )
    rows = result.fetchall()
    return {
        "users": [
            {
                "id": str(row.id),
                "username": row.username,
                "full_name": None,
                "email": row.email,
                "is_active": row.is_active
            }
            for row in rows
        ]
    }

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    services = await current_user.get_service_permissions(db)
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "user",
        is_active=current_user.is_active,
        is_employee=getattr(current_user, 'is_employee', True) or True,
        full_name=getattr(current_user, 'full_name', None),
        services=services
    )

@app.get("/users/me/services")
async def read_user_services(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get service-specific permissions for current user"""
    services = await current_user.get_service_permissions(db)

    # Default access model (dev/prod-safe baseline):
    # - Any authenticated user can access any active service.
    # - Service role is derived automatically when explicit grant doesn't exist.
    #   Global admin => admin in any service.
    #   Otherwise: video=>viewer, messenger=>user, dashboard=>viewer, support=>user.
    global_role = current_user.role.name if current_user.role else "user"
    defaults = {
        "video": "viewer",
        "messenger": "user",
        "dashboard": "viewer",
        "support": "user",
    }

    for slug, default_role in defaults.items():
        if slug in services:
            continue
        role_name = "admin" if global_role == "admin" else default_role
        # Fetch permissions for that service role
        result = await db.execute(
            text("""
                SELECT array_agg(sp.name) AS permissions
                FROM service_roles sr
                JOIN services s ON s.id = sr.service_id
                LEFT JOIN service_role_permissions srp ON sr.id = srp.role_id
                LEFT JOIN service_permissions sp ON sp.id = srp.permission_id
                WHERE s.slug = :service_slug AND sr.name = :role_name AND s.is_active = true AND sr.is_active = true
            """),
            {"service_slug": slug, "role_name": role_name},
        )
        row = result.first()
        perms = [p for p in (row.permissions if row and row.permissions else []) if p is not None]
        services[slug] = {"role": role_name, "perms": perms}
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "services": services
    }

@app.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Only admin can list all users
    # For simplicity, allow all authenticated users for now
    result = await db.execute(
        text("SELECT id, username, email, is_active, created_at FROM users LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "username": row.username,
            "email": row.email,
            "full_name": None,
            "is_active": row.is_active,
            "created_at": str(row.created_at)
        }
        for row in rows
    ]

@app.get("/users/search-all")
async def search_all_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search all users for granting video access (simplified version)"""
    result = await db.execute(
        text("SELECT id, username, email FROM users WHERE is_active = true LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    rows = result.fetchall()
    return {
        "users": [
            {
                "id": str(row.id),
                "username": row.username,
                "email": row.email,
                "full_name": None
            }
            for row in rows
        ]
    }

@app.post("/logout")
async def logout(response: dict):
    # In a real implementation, you might want to invalidate the token
    # For JWT without a blacklist, client-side token removal is sufficient
    return {"message": "Successfully logged out"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    # Basic metrics endpoint for Prometheus
    return {"status": "ok", "service": "auth-service"}

# Internal endpoints for inter-service communication
@app.get("/internal/users/{user_id}/profile-mini")
async def internal_user_profile_mini(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Минимальный профиль (username, email) для списков эфиров и других межсервисных сценариев."""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(user.id), "username": user.username, "email": user.email}


@app.get("/internal/users/{user_id}/contact")
async def internal_user_contact(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Email и username для рассылки уведомлений подписчикам."""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
    }


class InternalContactsRequest(BaseModel):
    user_ids: List[str]


@app.post("/internal/users/contacts")
async def internal_users_contacts(
    payload: InternalContactsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Контакты нескольких пользователей (batch для notification-service)."""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    users = await User.get_by_ids(db, payload.user_ids)
    return {
        "contacts": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
            }
            for u in users
        ]
    }


@app.get("/internal/users/{user_id}/permissions")
async def get_user_permissions_internal(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint for other services to get user permissions"""
    # Validate internal token
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's role permissions
    result = await db.execute(
        text("""
            SELECT p.name 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN roles r ON rp.role_id = r.id
            WHERE r.id = :role_id
        """),
        {"role_id": user.role_id}
    )
    
    permissions = [row[0] for row in result.fetchall()]
    return permissions

@app.get("/internal/users/{user_id}/services")
async def get_user_all_services_internal(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint to get user's access to all services"""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's service permissions
    services = await user.get_service_permissions(db)

    return {
        "user_id": str(user.id),
        "services": services
    }


@app.get("/internal/users/{user_id}/services/{service_slug}")
async def check_user_service_access_internal(
    user_id: str,
    service_slug: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint to check if user has access to specific service"""
    # Validate internal token
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's service permissions
    services = await user.get_service_permissions(db)
    service_access = services.get(service_slug)

    # If user has no service-specific role, deny access (no fallback to global role)
    if not service_access:
        return {
            "user_id": str(user.id),
            "service": service_slug,
            "role": None,
            "permissions": []
        }

    return {
        "user_id": str(user.id),
        "service": service_slug,
        "role": service_access.get("role"),
        "permissions": service_access.get("perms", [])
    }


@app.get("/internal/services")
async def list_services_internal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint to list all services with their roles"""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        text("""
            SELECT s.id, s.slug, s.name, s.description, s.is_active
            FROM services s
            WHERE s.is_active = true
            ORDER BY s.slug
        """)
    )

    services = []
    for row in result.fetchall():
        service_id = row.id
        # Get roles for this service
        roles_result = await db.execute(
            text("""
                SELECT id, name, description, is_active
                FROM service_roles
                WHERE service_id = :service_id AND is_active = true
                ORDER BY name
            """),
            {"service_id": service_id}
        )

        roles = []
        for role_row in roles_result.fetchall():
            roles.append({
                "id": str(role_row.id),
                "name": role_row.name,
                "description": role_row.description,
            })

        services.append({
            "id": str(service_id),
            "slug": row.slug,
            "name": row.name,
            "description": row.description,
            "roles": roles
        })

    return {"services": services}


@app.post("/internal/users/{user_id}/services/{service_slug}/role")
async def assign_user_service_role_internal(
    user_id: str,
    service_slug: str,
    payload: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint to assign a role to a user for a specific service"""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_name = payload.get("role")

    # Get service
    result = await db.execute(
        text("SELECT id FROM services WHERE slug = :slug AND is_active = true"),
        {"slug": service_slug}
    )
    service_row = result.first()
    if not service_row:
        raise HTTPException(status_code=404, detail="Service not found")

    service_id = service_row.id

    # If role_name is empty, remove the service role (no access)
    if not role_name or role_name.strip() == "":
        await db.execute(
            text("""
                DELETE FROM user_service_roles
                WHERE user_id = :user_id
                AND service_role_id IN (
                    SELECT id FROM service_roles WHERE service_id = :service_id
                )
            """),
            {"user_id": str(user.id), "service_id": service_id}
        )
        await db.commit()
        return {"success": True, "service_slug": service_slug, "role": None}

    # Get service role
    result = await db.execute(
        text("SELECT id FROM service_roles WHERE service_id = :service_id AND name = :role_name AND is_active = true"),
        {"service_id": service_id, "role_name": role_name}
    )
    role_row = result.first()
    if not role_row:
        raise HTTPException(status_code=404, detail="Role not found in this service")

    service_role_id = role_row.id

    # Remove existing role for this service (if any)
    await db.execute(
        text("""
            DELETE FROM user_service_roles
            WHERE user_id = :user_id
            AND service_role_id IN (
                SELECT id FROM service_roles WHERE service_id = :service_id
            )
        """),
        {"user_id": str(user.id), "service_id": service_id}
    )

    # Assign new role
    await db.execute(
        text("""
            INSERT INTO user_service_roles (user_id, service_role_id, granted_at, granted_by)
            VALUES (:user_id, :service_role_id, NOW(), :granted_by)
        """),
        {"user_id": str(user.id), "service_role_id": service_role_id, "granted_by": str(user.id)}
    )

    await db.commit()

    return {"success": True, "service_slug": service_slug, "role": role_name}


@app.get("/internal/services/{service_slug}/users")
async def list_service_users_internal(
    service_slug: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint to list all users with access to a service"""
    # Validate internal token
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Get all users with roles in this service
    result = await db.execute(
        text("""
            SELECT u.id, u.username, u.email, u.full_name, sr.name as role_name
            FROM users u
            JOIN user_service_roles usr ON u.id = usr.user_id
            JOIN service_roles sr ON usr.service_role_id = sr.id
            JOIN services s ON sr.service_id = s.id
            WHERE s.slug = :service_slug AND s.is_active = true AND sr.is_active = true AND u.is_active = true
        """),
        {"service_slug": service_slug}
    )
    
    users = []
    for row in result.fetchall():
        users.append({
            "id": str(row.id),
            "username": row.username,
            "email": row.email,
            "full_name": row.full_name,
            "role": row.role_name
        })
    
    return {"service": service_slug, "users": users}


@app.post("/internal/users/create")
async def internal_create_user(
    payload: InternalUserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Create a user from trusted internal services (portal/support)."""
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    username = payload.username.strip()
    email = payload.email.strip().lower()
    password = payload.password.strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing_username = await User.get_by_username(db, username)
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing_email = await User.get_by_email(db, email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    role_name = "admin" if payload.role.strip().lower() == "admin" else "user"
    role = await Role.get_by_name(db, role_name)
    if not role:
        role_id = await Role.create(db, name=role_name, description=f"Auto-created {role_name} role")
    else:
        role_id = str(role.id)

    created_user = await User.create(
        db,
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role_id=role_id,
        is_active=True,
        is_employee=payload.is_employee,
    )

    if payload.full_name and created_user:
        await db.execute(
            text("UPDATE users SET full_name = :full_name WHERE id = CAST(:uid AS uuid)"),
            {"uid": str(created_user.id), "full_name": payload.full_name.strip()},
        )
        await db.commit()
        created_user = await User.get_by_id(db, str(created_user.id))

    # Assign service role if provided
    if payload.service_slug and payload.service_role and created_user:
        # Get service
        result = await db.execute(
            text("SELECT id FROM services WHERE slug = :slug AND is_active = true"),
            {"slug": payload.service_slug}
        )
        service_row = result.first()
        if service_row:
            service_id = service_row.id
            # Get service role
            result = await db.execute(
                text("SELECT id FROM service_roles WHERE service_id = :service_id AND name = :role_name AND is_active = true"),
                {"service_id": service_id, "role_name": payload.service_role}
            )
            role_row = result.first()
            if role_row:
                service_role_id = role_row.id
                # Assign role to user
                await db.execute(
                    text("""
                        INSERT INTO user_service_roles (user_id, service_role_id, granted_at, granted_by)
                        VALUES (:user_id, :service_role_id, NOW(), :granted_by)
                        ON CONFLICT (user_id, service_role_id) DO NOTHING
                    """),
                    {"user_id": str(created_user.id), "service_role_id": service_role_id, "granted_by": str(created_user.id)}
                )
                await db.commit()

    return {
        "id": str(created_user.id),
        "username": created_user.username,
        "email": created_user.email,
        "full_name": getattr(created_user, "full_name", None),
        "role": created_user.role.name if created_user.role else role_name,
        "is_active": created_user.is_active,
        "is_employee": created_user.is_employee,
    }


@app.post("/internal/users/{user_id}/update")
async def internal_update_user(
    user_id: str,
    payload: InternalUserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates: list[str] = []
    params: dict = {"uid": str(user.id)}

    if payload.username is not None:
        username = payload.username.strip()
        result = await db.execute(
            text("SELECT id FROM users WHERE username = :username AND id <> CAST(:uid AS uuid)"),
            {"username": username, "uid": str(user.id)},
        )
        if result.first():
            raise HTTPException(status_code=400, detail="Username already exists")
        updates.append("username = :username")
        params["username"] = username

    if payload.email is not None:
        email = payload.email.strip().lower()
        result = await db.execute(
            text("SELECT id FROM users WHERE email = :email AND id <> CAST(:uid AS uuid)"),
            {"email": email, "uid": str(user.id)},
        )
        if result.first():
            raise HTTPException(status_code=400, detail="Email already exists")
        updates.append("email = :email")
        params["email"] = email

    if payload.password is not None and payload.password.strip():
        if len(payload.password.strip()) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        updates.append("password_hash = :password_hash")
        params["password_hash"] = get_password_hash(payload.password.strip())

    if payload.full_name is not None:
        updates.append("full_name = :full_name")
        params["full_name"] = payload.full_name.strip() or None

    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = bool(payload.is_active)

    if payload.role is not None:
        role_name = "admin" if payload.role.strip().lower() == "admin" else "user"
        role = await Role.get_by_name(db, role_name)
        if not role:
            role_id = await Role.create(db, name=role_name, description=f"Auto-created {role_name} role")
        else:
            role_id = str(role.id)
        updates.append("role_id = CAST(:role_id AS uuid)")
        params["role_id"] = role_id

    if updates:
        await db.execute(
            text(f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = CAST(:uid AS uuid)"),
            params,
        )
        await db.commit()

    refreshed = await User.get_by_id(db, str(user.id))
    return {
        "id": str(refreshed.id),
        "username": refreshed.username,
        "email": refreshed.email,
        "full_name": getattr(refreshed, "full_name", None),
        "role": refreshed.role.name if refreshed.role else "user",
        "is_active": refreshed.is_active,
        "is_employee": refreshed.is_employee,
    }


@app.post("/internal/users/{user_id}/delete")
async def internal_delete_user(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    if credentials.credentials != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await User.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete - set is_active to False
    await db.execute(
        text("UPDATE users SET is_active = false, updated_at = NOW() WHERE id = CAST(:uid AS uuid)"),
        {"uid": user_id},
    )
    await db.commit()

    return {"id": user_id, "deleted": True}


@app.get("/api/auth/esia/login")
async def esia_login():
    """Initiate ESIA (Gosuslugi) OAuth2 login flow - returns authorization URL"""
    # Production: construct URL with client_id, scope, redirect_uri, state
    esia_auth_url = (
        "https://esia.gosuslugi.ru/aas/oauth2/v3/sberid/authorize"
        "?client_id=YOUR_ESIA_CLIENT_ID"
        "&redirect_uri=http://localhost:3002/auth/esia/callback"
        "&scope=openid fullname snils"
        "&response_type=code"
    )
    return {
        "auth_url": esia_auth_url,
        "message": "ESIA integration prepared. Configure ESIA_CLIENT_ID and ESIA_PRIVATE_KEY in production.",
        "status": "ready"
    }

@app.post("/api/auth/esia/callback")
async def esia_callback(code: str, state: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Handle ESIA OAuth2 callback - exchange authorization code for access token"""
    # Production implementation:
    # 1. Exchange 'code' for ESIA access token using private key JWT
    # 2. Fetch user info (SNILS, fullName, email) from ESIA /rs/prns/
    # 3. Find or create user by esia_id / SNILS
    # 4. Issue internal JWT tokens for portal/video services
    return {
        "message": "ESIA callback endpoint prepared. Implement token exchange and user linking in production.",
        "code": code,
        "state": state,
        "integration_status": "prepared",
        "next_step": "Exchange code for ESIA token, then call /rs/prns/ for user info"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
