# Архитектура Единого Портала ДГИ — Детальная схема потоков данных

## Содержание
1. [Общая архитектура системы](#1-общая-архитектура)
2. [Поток аутентификации (SSO)](#2-поток-аутентификации-sso)
3. [Поток авторизации (RBAC)](#3-поток-авторизации-rbac)
4. [Поток запроса к сервису](#4-поток-запроса-к-сервису)
5. [Поток выхода из системы](#5-поток-выхода)
6. [Структуры данных](#6-структуры-данных)
7. [Внутреннее взаимодействие микросервисов](#7-внутреннее-взаимодействие)

---

## 1. Общая архитектура

### 1.1 Компоненты системы

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ПОЛЬЗОВАТЕЛЬ (Браузер)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Cookie     │  │   JWT Token  │  │  HTML/JSON   │  │   Redirect   │     │
│  │  session_id  │  │   ( Bearer ) │  │   ответы     │  │   URL        │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼─────────────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           NGINX (Reverse Proxy)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  SSL/TLS     │  │  Rate Limit  │  │  Path-based  │  │  Static      │    │
│  │ Termination  │  │  (req/sec)   │  │  Routing     │  │  Caching     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Docker Compose Stack                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         ЕДИНЫЙ ПОРТАЛ (Next.js)                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │    │
│  │  │  Landing   │  │   Header   │  │  Service   │  │   Login    │   │    │
│  │  │   Page     │  │ Component  │  │   Cards    │  │  Handler   │   │    │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │    │
│  │        └────────────────┴───────────────┴───────────────┘          │    │
│  │                          Port: 3002                                │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│  ┌──────────────────────────────┼──────────────────────────────────────┐    │
│  │                    AUTH-SERVICE (FastAPI)                            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │    │
│  │  │  /login    │  │  /register │  │  /token    │  │  /users/me │   │    │
│  │  │ (Form+LDAP)│  │ (LDAP sync)│  │(JWT issue) │  │(validate)  │   │    │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │    │
│  │        └────────────────┴───────────────┴───────────────┘          │    │
│  │                          Port: 8000                                │    │
│  │  ┌─────────────────────────────────────────────────────────────┐ │    │
│  │  │              PostgreSQL (Shared Auth DB)                     │ │    │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │ │    │
│  │  │  │  users  │  │  roles  │  │ user_svc │  │services │        │ │    │
│  │  │  │  table  │  │  table  │  │  roles   │  │  table  │        │ │    │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │ │    │
│  │  └─────────────────────────────────────────────────────────────┘ │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│  ┌──────────────────────────────┼──────────────────────────────────────┐    │
│  │  ┌────────────┐  ┌─────────┴────────┐  ┌────────────┐            │    │
│  │  │ VIDEO-SVC  │  │ MESSENGER-SVC    │  │ DASHBOARD  │            │    │
│  │  │  Port:8001 │  │   Port:8005      │  │  Port:8006 │  ...       │    │
│  │  └─────┬──────┘  └───────┬──────────┘  └─────┬──────┘            │    │
│  │        │                 │                   │                   │    │
│  │        └─────────────────┴───────────────────┘                   │    │
│  │                          │                                      │    │
│  │  ┌───────────────────────┴───────────────────────┐                │    │
│  │  │         Service Databases (PostgreSQL)      │                │    │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │                │    │
│  │  │  │  video  │  │  chat   │  │ metrics │     │                │    │
│  │  │  │  DB     │  │  DB     │  │  DB     │     │                │    │
│  │  │  └─────────┘  └─────────┘  └─────────┘     │                │    │
│  │  └─────────────────────────────────────────────┘                │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Support: Redis, MinIO, Elasticsearch, RabbitMQ, Prometheus, Grafana│  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Порты и URL (Dev среда)

| Компонент | Порт | URL | Назначение |
|-----------|------|-----|------------|
| Nginx | 80/443 | `http://localhost` | Единый вход, SSL, роутинг |
| Portal (Next.js) | 3002 | `http://localhost:3002` | Landing page, UI |
| Auth Service | 8000 | `http://localhost:8000` | Аутентификация, JWT |
| Video Service | 8001 | `http://localhost:3000` | Видеохостинг |
| Messenger | 8005 | — | Мессенджер (в планах) |
| Dashboard | 8006 | — | Аналитика (в планах) |
| Grafana | 3001 | `http://localhost:3001` | Мониторинг |
| PostgreSQL | 5432 | — | Shared auth DB |

---

## 2. Поток аутентификации (SSO)

### 2.1 Sequence Diagram — Вход пользователя

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Browser │     │  Nginx  │     │  Portal │     │  Auth   │     │   LDAP  │
│ (User)  │     │         │     │ (3002)  │     │ (8000)  │     │         │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │               │
     │  1. GET /     │               │               │               │
     │────────────────>               │               │               │
     │               │               │               │               │
     │               │  2. proxy /   │               │               │
     │               │───────────────>│               │               │
     │               │               │               │               │
     │               │  3. HTML + JS │               │               │
     │               │<───────────────│               │               │
     │               │               │               │               │
     │  4. Render UI │               │               │               │
     │<───────────────│               │               │               │
     │               │               │               │               │
     │  5. Click     │               │               │               │
     │   "Войти"     │               │               │               │
     │────────────────>               │               │               │
     │               │               │               │               │
     │               │  6. redirect  │               │               │
     │               │  to /auth/login│               │               │
     │               │               │               │               │
     │<───────────────│               │               │               │
     │               │               │               │               │
     │  7. GET /auth/login             │               │               │
     │──────────────────────────────────────────────>│               │
     │               │               │               │               │
     │               │               │               │  8. redirect  │
     │               │               │               │  to LDAP login│
     │               │               │               │               │
     │<───────────────────────────────────────────────────────────────│
     │               │               │               │               │
     │  9. Форма LDAP │               │               │               │
     │   логин/пароль │               │               │               │
     │───────────────────────────────────────────────────────────────>│
     │               │               │               │               │
     │               │               │               │  10. Validate │
     │               │               │               │    creds      │
     │               │               │               │<───────────────│
     │               │               │               │               │
     │               │               │               │  11. Success/ │
     │               │               │               │    Fail       │
     │               │               │               │               │
     │               │               │               │  12. Create │
     │               │               │               │    session    │
     │               │               │               │    + JWT      │
     │               │               │               │               │
     │  13. Set      │               │               │               │
     │   cookies:    │               │               │               │
     │   session_id  │               │               │               │
     │   access_token│               │               │               │
     │<───────────────────────────────────────────────────────────────│
     │               │               │               │               │
     │  14. Redirect │               │               │               │
     │    to /       │               │               │               │
     │<───────────────│               │               │               │
     │               │               │               │               │
     │  15. GET /    │               │               │               │
     │   (with JWT)  │               │               │               │
     │────────────────>               │               │               │
     │               │               │               │               │
     │               │  16. Check    │               │               │
     │               │    JWT        │               │               │
     │               │  (middleware) │               │               │
     │               │               │               │               │
     │               │  17. GET      │               │               │
     │               │  /users/me    │               │               │
     │               │───────────────────────────────>│               │
     │               │               │               │               │
     │               │  18. User     │               │               │
     │               │   profile     │               │               │
     │               │<───────────────────────────────│               │
     │               │               │               │               │
     │  19. Render   │               │               │               │
     │   dashboard   │               │               │               │
     │<───────────────│               │               │               │
     │               │               │               │               │
```

### 2.2 Детализация шагов аутентификации

#### Шаг 1–4: Загрузка портала
- **Browser → Nginx**: `GET http://localhost/`
  - Headers: `Host: localhost`, `Accept: text/html`
  
- **Nginx → Portal**: `GET /` (proxy_pass to portal:3002)
  - Nginx добавляет: `X-Real-IP`, `X-Forwarded-For`
  
- **Portal → Browser**: HTML страница с React-приложением
  - Response: `200 OK`, `Content-Type: text/html; charset=utf-8`
  - Body: Next.js рендереная страница с service cards

#### Шаг 5–8: Инициация входа
- **Browser**: Пользователь кликает "Войти через ЕСИА/ЛДАП"
  - Event: `onClick={() => window.location.href = '/auth/login'}`
  
- **Nginx**: Роутит `/auth/login` → `auth-service:8000/api/v1/login`
  
- **Auth Service**: Проверяет наличие active session
  - Если нет: редирект на LDAP/ЕСИА login URL
  - Если есть: редирект обратно на portal с новым токеном

#### Шаг 9–12: LDAP валидация
- **Auth Service → LDAP**: `ldap3` connection
  ```python
  # Псевдокод
  conn = ldap3.Connection(server, user=dn, password=password, auto_bind=True)
  if conn.bind():
      user = await sync_user_from_ldap(db, conn.result)
      access_token = create_jwt(user.id, roles, expiry=15min)
      refresh_token = create_jwt(user.id, type="refresh", expiry=7days)
  ```

#### Шаг 13–14: Установка токенов
- **Auth Service → Browser**: `302 Found` redirect
  - Set-Cookie: `session_id=abc123; HttpOnly; Secure; SameSite=Lax`
  - Set-Cookie: `access_token=eyJhbG...; Secure; SameSite=Lax`
  - Location: `http://localhost/`

#### Шаг 15–19: Авторизованная загрузка
- **Browser → Nginx**: `GET /` с cookie `access_token=eyJhbG...`
- **Nginx → Portal**: Проксирует запрос с заголовками
- **Portal (middleware)**: Проверяет JWT
  ```javascript
  // Middleware pseudocode
  const token = req.cookies.access_token;
  const payload = jwt.verify(token, AUTH_SECRET);
  req.user = await fetchUserFromAuthService(payload.sub);
  ```
- **Portal → Browser**: Страница с персонализированным header (имя пользователя)

---

## 3. Поток авторизации (RBAC)

### 3.1 Проверка доступа к сервису

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │     │    Nginx    │     │Video Service│     │Auth Service │
│  (User)     │     │             │     │  (8001)     │     │  (8000)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │  1. GET /video    │                   │                   │
       │  (with JWT)       │                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │  2. proxy /video  │                   │
       │                   │  + X-User-ID      │                   │
       │                   │  + Authorization  │                   │
       │                   │──────────────────>│                   │
       │                   │                   │                   │
       │                   │                   │  3. Extract JWT   │
       │                   │                   │  from header      │
       │                   │                   │                   │
       │                   │                   │  4. Validate JWT  │
       │                   │                   │  locally (pub key)│
       │                   │                   │                   │
       │                   │                   │  5. Extract:      │
       │                   │                   │     user_id       │
       │                   │                   │     service_roles │
       │                   │                   │                   │
       │                   │                   │  6. [Optional]    │
       │                   │                   │  Check internal   │
       │                   │                   │  with auth svc    │
       │                   │                   │──────────────────>│
       │                   │                   │                   │
       │                   │                   │  7. Return perms│
       │                   │                   │<──────────────────│
       │                   │                   │                   │
       │                   │                   │  8. Check:        │
       │                   │                   │  user has role    │
       │                   │                   │  "video_user"?    │
       │                   │                   │                   │
       │                   │  9. If NO:        │                   │
       │                   │  403 Forbidden    │                   │
       │<───────────────────│                   │                   │
       │                   │                   │                   │
       │                   │  10. If YES:      │                   │
       │                   │  proxy request    │                   │
       │                   │  + X-User-Role    │                   │
       │                   │──────────────────>│                   │
       │                   │                   │                   │
       │                   │                   │  11. Process      │
       │                   │                   │  video request    │
       │                   │                   │  (upload/list)    │
       │                   │                   │                   │
       │                   │  12. JSON/HTML    │                   │
       │                   │<──────────────────│                   │
       │                   │                   │                   │
       │  13. Response     │                   │                   │
       │<───────────────────│                   │                   │
       │                   │                   │                   │
```

### 3.2 Детализация авторизации

#### Шаг 1–2: Запрос к сервису
- **Browser**: `GET http://localhost/video`
  - Headers:
    ```
    Cookie: access_token=eyJhbGciOiJSUzI1NiIs...
    Accept: application/json, text/html
    ```

- **Nginx**: 
  ```nginx
  location /video/ {
      proxy_pass http://video_service;
      proxy_set_header Authorization $http_authorization;
      proxy_set_header X-User-ID $cookie_user_id;  # из JWT декодирования
  }
  ```

#### Шаг 3–8: JWT валидация в Video Service
```python
# video-service/src/dependencies.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    # 1. Декодируем JWT локально (auth-service предоставляет public key)
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    
    # 2. Проверяем service-specific claims
    service_roles = payload.get("service_roles", {})
    video_perms = service_roles.get("video", {})
    
    if not video_perms:
        raise HTTPException(403, "No access to video service")
    
    # 3. Возвращаем enriched user object
    return UserContext(
        id=payload["sub"],
        username=payload["username"],
        role=video_perms["role"],  # "admin" | "editor" | "viewer"
        permissions=video_perms["permissions"]  # ["upload", "delete", "view"]
    )
```

#### Шаг 9–13: Результат проверки
- **403 Forbidden**: У пользователя нет роли `video_*`
  - Response: `{"detail": "User lacks video service access"}`
  
- **200 OK**: Разрешено
  - Response: `{"videos": [...], "user_role": "video_admin"}`

---

## 4. Поток запроса к сервису (полный цикл)

### 4.1 Данные на каждом этапе

```
ЭТАП 1: Пользователь → Nginx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHOD:  GET | POST | PUT | DELETE
URL:     http://localhost/{service}/{resource}
HEADERS:
  Host:           localhost
  Cookie:         session_id=xxx; access_token=eyJ...
  Authorization:  Bearer eyJhbGciOiJSUzI1Ni...
  Accept:         application/json
  User-Agent:     Mozilla/5.0...

ЭТАП 2: Nginx → Service (internal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHOD:  (same)
URL:     http://{service}:800X/{resource}
HEADERS:
  X-Real-IP:        192.168.1.100
  X-Forwarded-For:  192.168.1.100
  X-Forwarded-Proto: http
  Authorization:    Bearer eyJ... (forwarded)
  X-User-ID:        user-uuid-123 (из JWT декодирования)
  X-User-Role:      video_admin (из JWT)
  X-Request-ID:     req-uuid-456 (для tracing)

ЭТАП 3: Service → Auth Service (internal, optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHOD:  GET
URL:     http://auth-service:8000/internal/users/{user_id}/services/{slug}
HEADERS:
  Authorization: Bearer internal_service_token (shared secret)
  X-From-Service: video-service

RESPONSE:
  {
    "user_id": "uuid-123",
    "service": "video",
    "role": "admin",
    "permissions": ["upload", "delete", "edit", "view"]
  }

ЭТАП 4: Service → Database
━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHOD:  SQL Query (asyncpg/SQLAlchemy)
CONN:    postgresql://video_user:pass@video-db:5432/video_db
QUERY:   SELECT * FROM videos WHERE ... LIMIT ... OFFSET ...
RESULT:  List[Video] → Pydantic models

ЭТАП 5: Service → Nginx → Browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATUS:  200 OK | 201 Created | 400 Bad Request | 403 Forbidden
HEADERS:
  Content-Type: application/json
  Cache-Control: no-cache (для dynamic), max-age=3600 (для static)
BODY:
  {
    "data": [...],
    "meta": {
      "page": 1,
      "per_page": 20,
      "total": 150
    },
    "user_context": {
      "role": "video_admin",
      "permissions": [...]
    }
  }
```

---

## 5. Поток выхода из системы

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Browser │     │  Nginx  │     │  Portal │     │  Auth   │
│ (User)  │     │         │     │         │     │ Service │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │
     │  1. Click     │               │               │
     │   "Выход"     │               │               │
     │────────────────>               │               │
     │               │               │               │
     │               │  2. POST      │               │
     │               │  /api/logout  │               │
     │               │               │               │
     │               │  3. Clear     │               │
     │               │  localStorage │               │
     │               │  + cookies    │               │
     │               │               │               │
     │               │  4. POST      │               │
     │               │  /auth/logout │               │
     │               │───────────────────────────────>│
     │               │               │               │
     │               │               │               │  5. Invalidate
     │               │               │               │     session
     │               │               │               │     in Redis
     │               │               │               │
     │               │               │  6. Clear     │
     │               │  Set-Cookie:  │               │
     │               │  access_token=│               │
     │               │  ; Max-Age=0  │               │
     │<───────────────│               │               │
     │               │               │               │
     │  7. Reload    │               │               │
     │   page        │               │               │
     │────────────────>               │               │
     │               │               │               │
     │  8. Show      │               │               │
     │   login page  │               │               │
     │<───────────────│               │               │
     │               │               │               │
```

---

## 6. Структуры данных

### 6.1 JWT Access Token (Payload)

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "username": "ivanov.ii",
  "email": "ivanov.ii@dgi.mos.ru",
  "full_name": "Иванов Иван Иванович",
  "department": "IT",
  "iat": 1715083200,
  "exp": 1715084100,
  "type": "access",
  "service_roles": {
    "video": {
      "role": "admin",
      "permissions": ["upload", "delete", "edit", "view", "moderate"]
    },
    "messenger": {
      "role": "user",
      "permissions": ["read", "write", "call"]
    },
    "dashboard": {
      "role": "viewer",
      "permissions": ["read"]
    }
  }
}
```

### 6.2 Refresh Token (Payload)

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "jti": "refresh-token-uuid-789",
  "iat": 1715083200,
  "exp": 1715688000,
  "type": "refresh",
  "device_id": "browser-chrome-win10-abc"
}
```

### 6.3 Session (Redis)

```
Key:    session:550e8400-e29b-41d4-a716-446655440000:browser-chrome-win10-abc
Value:  {
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "refresh_token_jti": "refresh-token-uuid-789",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-05-07T12:00:00Z",
  "last_active": "2024-05-07T12:15:00Z"
}
TTL:    604800 seconds (7 days)
```

### 6.4 User (PostgreSQL)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    ldap_dn VARCHAR(255),
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 6.5 Service Role (PostgreSQL)

```sql
CREATE TABLE service_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(id),
    name VARCHAR(50) NOT NULL,           -- "video_admin"
    display_name VARCHAR(100),            -- "Администратор видео"
    permissions JSONB DEFAULT '[]',         -- ["upload", "delete"]
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(service_id, name)
);

CREATE TABLE user_service_roles (
    user_id UUID REFERENCES users(id),
    service_role_id UUID REFERENCES service_roles(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, service_role_id)
);
```

---

## 7. Внутреннее взаимодействие микросервисов

### 7.1 Service-to-Service Auth

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│ Video Svc   │          │  Auth Svc   │          │ Internal    │
│  (8001)     │          │  (8000)     │          │ Network     │
└──────┬──────┘          └──────┬──────┘          └──────┬──────┘
       │                        │                        │
       │  1. Internal request  │                        │
       │  GET /internal/...    │                        │
       │───────────────────────>│                        │
       │  Headers:              │                        │
       │  Authorization:        │                        │
       │  Bearer INTERNAL_TOKEN │                        │
       │  X-From-Service: video │                        │
       │                        │                        │
       │                        │  2. Validate token     │
       │                        │  against env var       │
       │                        │  INTERNAL_AUTH_TOKEN   │
       │                        │                        │
       │                        │  3. Check:             │
       │                        │  token == expected?    │
       │                        │                        │
       │  4. 403 Forbidden     │                        │
       │  (if invalid)         │                        │
       │<───────────────────────│                        │
       │                        │                        │
       │                        │  5. Query DB           │
       │                        │  for user perms        │
       │                        │                        │
       │  6. Return perms      │                        │
       │<───────────────────────│                        │
       │                        │                        │
```

### 7.2 Internal Token

```
Header:  Authorization: Bearer dgi-internal-service-token-2024
Origin:  X-From-Service: video-service

Validation:
  expected_token = os.getenv("INTERNAL_AUTH_TOKEN")
  if provided_token != expected_token:
      raise HTTPException(403, "Invalid internal token")
```

### 7.3 Event Flow (RabbitMQ)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Auth Svc   │     │  RabbitMQ   │     │  Other Svcs │
│             │     │  (Events)   │     │             │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  1. User updated  │                   │
       │  (role changed)   │                   │
       │──────────────────>│                   │
       │                   │                   │
       │  2. Publish       │                   │
       │  exchange:        │                   │
       │  "auth.events"    │                   │
       │  routing_key:     │                   │
       │  "user.updated"   │                   │
       │                   │                   │
       │                   │  3. Route to      │
       │                   │     queues        │
       │                   │                   │
       │                   │──────────────────>│
       │                   │  (Video Svc       │
       │                   │   queue)          │
       │                   │                   │
       │                   │──────────────────>│
       │                   │  (Dashboard       │
       │                   │   queue)          │
       │                   │                   │
       │                   │                   │  4. Invalidate
       │                   │                   │     local cache
       │                   │                   │
```

---

## 8. Таблица маршрутизации Nginx

| Path | Upstream | Service | Auth Required |
|------|----------|---------|---------------|
| `/` | `portal:3002` | Portal | No |
| `/auth/*` | `auth-service:8000` | Auth | No |
| `/video/*` | `video-service:8001` | Video | Yes (JWT) |
| `/messenger/*` | `messenger:8005` | Messenger | Yes (JWT) |
| `/dashboard/*` | `dashboard:8006` | Dashboard | Yes (JWT) |
| `/api/*` | varies | API Gateway | Yes (JWT) |
| `/grafana/*` | `grafana:3000` | Monitoring | Admin only |
| `/prometheus/*` | `prometheus:9090` | Metrics | Internal |

---

## 9. Состояния пользователя

```
                    ┌─────────────┐
                    │  Анонимный  │
                    │  (No JWT)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │  Portal  │ │  Portal  │ │  Portal  │
       │ (read)   │ │ (login)  │ │ (error)  │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            │   Click "Войти"         │
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  LDAP/ЕСИА   │
                  │  (External)  │
                  └──────┬───────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       ┌──────────┐          ┌──────────┐
       │  Успех   │          │  Отказ   │
       │ (JWT set)│          │ (retry)  │
       └────┬─────┘          └────┬─────┘
            │                     │
            ▼                     │
       ┌──────────┐              │
       │Авторизован│             │
       │  (JWT)   │<─────────────┘
       └────┬─────┘
            │
    ┌───────┼───────┐
    │       │       │
    ▼       ▼       ▼
┌──────┐┌──────┐┌──────┐
│Video ││Mess. ││Dash. │
│(role)││(role)││(role)│
└──────┘└──────┘└──────┘
    │
    │ Token expires (15 min)
    │
    ▼
┌──────────┐
│ Refresh  │──> GET /auth/refresh
│  Token   │    (with refresh_token cookie)
│  (7 days)│
└────┬─────┘
     │
     │ Refresh expires
     │
     ▼
┌──────────┐
│  Logout  │──> POST /auth/logout
│  (Clear) │    (invalidate session)
└──────────┘
     │
     ▼
┌──────────┐
│ Анонимный│
│ (No JWT) │
└──────────┘
```

---

*Документ создан для группового проекта ДГИ. Последнее обновление: 2024-05-07*
