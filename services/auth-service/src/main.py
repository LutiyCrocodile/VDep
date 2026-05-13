from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
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
                "uploader": ["video:upload", "video:manage_own"]
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Video frontend
        "http://localhost:3001",   # Messenger (будет)
        "http://localhost:3002",   # Portal
        "http://localhost:3003",   # Dashboard (будет)
        "http://localhost:3004",   # Support (будет)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))

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
            services = await user.get_service_permissions(db)
            to_encode["services"] = services
            to_encode["is_employee"] = getattr(user, 'is_employee', True)
    
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

    # If not found locally, try LDAP
    if user is None and LDAP_SERVER:
        ldap_user = await authenticate_ldap(username, password)
        if ldap_user:
            # Create user in local DB if authenticated via LDAP
            role = await Role.get_by_name(db, "employee")  # Default role
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

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
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
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "user",
        is_active=current_user.is_active,
        is_employee=getattr(current_user, 'is_employee', True) or True,
        full_name=getattr(current_user, 'full_name', None)
    )

@app.get("/users/me/services")
async def read_user_services(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get service-specific permissions for current user"""
    services = await current_user.get_service_permissions(db)
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
    
    user = await User.get_by_username(db, user_id)
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
    
    user = await User.get_by_username(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's service permissions
    services = await user.get_service_permissions(db)
    service_access = services.get(service_slug)
    
    if not service_access:
        raise HTTPException(status_code=403, detail=f"User has no access to service: {service_slug}")
    
    return {
        "user_id": str(user.id),
        "service": service_slug,
        "role": service_access.get("role"),
        "permissions": service_access.get("perms", [])
    }

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
