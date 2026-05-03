from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import ldap
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import logging

from .database import get_db, create_tables, User, Role, Permission
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

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    logger.info("Auth service started")
    yield
    # Shutdown
    logger.info("Auth service shutting down")

app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
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
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
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
    user = await User.create(db, **{
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hashed_password,
        "role_id": role_id
    })

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

    access_token = create_access_token(data={"sub": user.username})
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

        access_token = create_access_token(data={"sub": user.username})
        new_refresh_token = create_refresh_token(data={"sub": user.username})

        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name if current_user.role else "none",
        is_active=current_user.is_active
    )

@app.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    # Internal endpoint for other services
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
        text("SELECT * FROM users LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "username": row.username,
            "email": row.email,
            "is_active": row.is_active,
            "created_at": str(row.created_at)
        }
        for row in rows
    ]

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
