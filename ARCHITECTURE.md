# Архитектура Единого Портала ДГИ

> Детальная схема потоков данных, аутентификации и авторизации для группового проекта.
> GitHub рендерит диаграммы Mermaid автоматически.

---

## 1. Общая архитектура системы

```mermaid
flowchart TB
    subgraph Internet["🌐 Пользователь (Браузер)"]
        U["Browser"]
    end

    subgraph NginxBlock["NGINX (Reverse Proxy)"]
        N["NGINX<br/>SSL / Rate Limit / Routing"]
    end

    subgraph DockerStack["Docker Compose Stack"]
        direction TB

        subgraph Portal["Единый Портал (Next.js :3002)"]
            P1["Landing Page"]
            P2["Service Cards"]
            P3["Login Handler"]
        end

        subgraph Auth["Auth Service (FastAPI :8000)"]
            A1["/login (LDAP/ЕСИА)"]
            A2["/token (JWT issue)"]
            A3["/users/me (validate)"]
            A4["/internal/* (svc-to-svc)"]
        end

        subgraph Microservices["Микросервисы"]
            V["Video Service (:8001)"]
            M["Messenger (:8005)"]
            D["Dashboard (:8006)"]
            S["Support (:8007)"]
        end

        subgraph Storage["Хранилища"]
            PG[(PostgreSQL<br/>Shared Auth DB)]
            PG2[(PostgreSQL<br/>Video DB)]
            R[(Redis<br/>Sessions)]
            MQ[(RabbitMQ<br/>Events)]
            MIN[(MinIO<br/>Video Storage)]
        end

        subgraph Monitoring["Мониторинг"]
            GR[(Grafana :3001)]
            PR[(Prometheus)]
        end
    end

    U -->|"HTTPS 443"| N
    N -->|"/"| Portal
    N -->|"/auth/*"| Auth
    N -->|"/video/*"| V
    N -->|"/messenger/*"| M
    N -->|"/dashboard/*"| D
    N -->|"/support/*"| S
    N -->|"/grafana/*"| GR

    Auth --> PG
    V --> PG2
    V --> MIN
    Auth --> R
    Auth --> MQ
    V --> MQ
    M --> MQ
```

### Порты (Dev среда)

| Компонент | Порт | URL |
|-----------|------|-----|
| Nginx | 80/443 | `http://localhost` |
| Portal | 3002 | `http://localhost:3002` |
| Auth Service | 8000 | `http://localhost:8000` |
| Video Service | 8001 | `http://localhost:3000` |
| Grafana | 3001 | `http://localhost:3001` |
| PostgreSQL | 5432 | — |
| Redis | 6379 | — |

---

## 2. Поток аутентификации (SSO)

```mermaid
sequenceDiagram
    autonumber
    actor U as Пользователь
    participant B as Browser
    participant N as Nginx
    participant P as Portal (Next.js)
    participant A as Auth Service
    participant L as LDAP / ЕСИА
    participant R as Redis (Session)

    U->>B: Открыть http://localhost/
    B->>N: GET /
    N->>P: proxy_pass portal:3002
    P-->>N: HTML + JS (Landing Page)
    N-->>B: 200 OK (страница портала)
    U->>B: Клик "Войти"
    B->>N: GET /auth/login
    N->>A: proxy_pass auth:8000/api/v1/login
    A->>L: redirect на форму LDAP
    L-->>B: HTML форма логина
    U->>B: Ввод логин/пароль
    B->>L: POST credentials
    L->>L: Валидация в AD/LDAP
    L-->>A: success/fail
    alt Успешная авторизация
        A->>A: Создать JWT access_token (15 мин)
        A->>A: Создать JWT refresh_token (7 дней)
        A->>R: Сохранить session
        A-->>B: 302 Redirect to / (Set-Cookie)
        Note over A,B: Cookies: session_id=xxx; access_token=eyJ...
        B->>N: GET / (with cookies)
        N->>P: proxy (with headers)
        P->>A: GET /users/me (validate JWT)
        A-->>P: User profile + service_roles
        P-->>N: HTML (авторизованная страница)
        N-->>B: 200 OK (имя пользователя в шапке)
    else Ошибка авторизации
        A-->>B: 401 Unauthorized
        B->>U: Показать ошибку входа
    end
```

### Данные на каждом шаге

#### Шаг 1–4: Загрузка портала (анонимный пользователь)

```http
GET / HTTP/1.1
Host: localhost
Accept: text/html, application/xhtml+xml
Cookie: (none)
```

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Set-Cookie: __Host-next-auth.csrf-token=abc; Path=/; Secure

<!DOCTYPE html>
<html>
  <body>
    <!-- Next.js рендерит Landing Page -->
    <!-- Service Cards: Video, Messenger, Dashboard, Support -->
    <!-- Button: "Войти" -->
  </body>
</html>
```

#### Шаг 15–19: Авторизованная загрузка

```http
GET / HTTP/1.1
Host: localhost
Cookie: access_token=eyJhbGciOiJSUzI1NiIs...
Accept: text/html
```

**JWT Payload (декодированный):**

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "username": "ivanov.ii",
  "email": "ivanov.ii@dgi.mos.ru",
  "full_name": "Иванов И.И.",
  "department": "IT",
  "iat": 1715083200,
  "exp": 1715084100,
  "type": "access",
  "service_roles": {
    "video": { "role": "admin", "permissions": ["upload", "delete", "edit", "view"] },
    "messenger": { "role": "user", "permissions": ["read", "write"] }
  }
}
```

---

## 3. Поток авторизации (RBAC) — доступ к сервису

```mermaid
sequenceDiagram
    autonumber
    actor U as Пользователь
    participant B as Browser
    participant N as Nginx
    participant V as Video Service
    participant A as Auth Service
    participant PG as PostgreSQL

    U->>B: Клик "Видеохостинг"
    B->>N: GET /video/ (Cookie: access_token=eyJ...)
    N->>V: proxy_pass video:8001 (X-User-ID, Authorization)
    V->>V: Извлечь JWT из заголовка
    V->>V: Верифицировать подпись (public key)
    V->>V: Извлечь service_roles.video

    alt Нет доступа к video
        V-->>N: 403 Forbidden
        N-->>B: 403 Forbidden
        B->>U: "Нет доступа к Видеохостингу"
    else Доступ есть
        V->>PG: SELECT * FROM videos WHERE ...
        PG-->>V: список видео
        V-->>N: 200 OK + JSON
        N-->>B: 200 OK (HTML/JSON)
        B->>U: Отобразить видео-контент
    end

    Note over V,A: Опционально:<br/>Video Service может<br/>запросить Auth Service<br/>через /internal/...<br/>для double-check
```

### Данные авторизации

**Заголовки при проксировании (Nginx → Video Service):**

```http
GET /api/videos HTTP/1.1
Host: video-service:8001
Authorization: Bearer eyJhbGciOiJSUzI1Ni...
X-User-ID: 550e8400-e29b-41d4-a716-446655440000
X-User-Role: video_admin
X-Real-IP: 192.168.1.100
X-Request-ID: req-550e8400-1234
```

**Проверка в Video Service (Python pseudocode):**

```python
from fastapi import Depends, HTTPException
from jose import jwt

PUBLIC_KEY = open("/secrets/auth_pubkey.pem").read()

async def require_video_access(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    
    service_roles = payload.get("service_roles", {})
    video_perms = service_roles.get("video")
    
    if not video_perms:
        raise HTTPException(403, "No access to video service")
    
    return UserContext(
        id=payload["sub"],
        role=video_perms["role"],           # "admin" | "editor" | "viewer"
        permissions=video_perms["permissions"] # ["upload", "delete", "view"]
    )
```

---

## 4. Поток запроса к сервису (полный цикл)

```mermaid
flowchart LR
    subgraph Browser["Browser"]
        B1["Cookie:<br/>access_token=eyJ..."]
    end

    subgraph Nginx["NGINX"]
        N1["Route: /video/*"]
        N2["Add Headers:<br/>X-User-ID<br/>X-User-Role<br/>X-Request-ID"]
    end

    subgraph Video["Video Service (8001)"]
        V1["JWT Verify"]
        V2["RBAC Check"]
        V3["Process Request"]
    end

    subgraph DB["PostgreSQL"]
        D1["video_db"]
    end

    subgraph MinIO["MinIO"]
        S1["Video Files"]
    end

    B1 -->|"GET /video/upload"| N1
    N1 --> N2
    N2 -->|"+ JWT + Headers"| V1
    V1 --> V2
    V2 -->|"Разрешено"| V3
    V2 -->|"Запрещено"| E1["403 Forbidden"]
    V3 -->|"INSERT/SELECT"| D1
    V3 -->|"GET object"| S1
    V3 -->|"200 OK + JSON"| N2
    N2 -->|"Response"| B1
```

### Пример данных на каждом этапе

#### Этап 1: Browser → Nginx

```http
GET /video/api/videos?page=1 HTTP/1.1
Host: localhost
Cookie: access_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
```

#### Этап 2: Nginx → Video Service (internal)

```http
GET /api/videos?page=1 HTTP/1.1
Host: video-service:8001
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
X-Real-IP: 192.168.1.100
X-Forwarded-For: 192.168.1.100
X-Forwarded-Proto: http
X-User-ID: 550e8400-e29b-41d4-a716-446655440000
X-User-Role: video_admin
X-Request-ID: req-7a3f-2024-05-07-001
```

#### Этап 3: Video Service → PostgreSQL

```sql
SELECT v.id, v.title, v.description, v.created_at, c.name as channel_name
FROM videos v
JOIN channels c ON v.channel_id = c.id
WHERE v.is_public = TRUE OR v.owner_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY v.created_at DESC
LIMIT 20 OFFSET 0;
```

#### Этап 4: Video Service → Browser

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60
X-Request-ID: req-7a3f-2024-05-07-001

{
  "data": [
    {
      "id": "vid-001",
      "title": "Обзор системы",
      "description": "...",
      "thumbnail_url": "http://localhost/video/thumbs/vid-001.jpg",
      "channel": "IT Департамент",
      "created_at": "2024-05-01T10:00:00Z",
      "view_count": 150,
      "duration": 360
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  },
  "user_context": {
    "role": "video_admin",
    "permissions": ["upload", "delete", "edit", "view", "moderate"]
  }
}
```

---

## 5. Поток выхода из системы (Logout)

```mermaid
sequenceDiagram
    autonumber
    actor U as Пользователь
    participant B as Browser
    participant P as Portal
    participant A as Auth Service
    participant R as Redis

    U->>B: Клик "Выйти"
    B->>P: POST /api/logout
    P->>P: Очистить localStorage
    P->>A: POST /auth/logout
    A->>R: DEL session:{user_id}:{device_id}
    R-->>A: OK
    A-->>P: 200 OK (Set-Cookie: max-age=0)
    P-->>B: redirect to /
    B->>P: GET / (без cookies)
    P-->>B: Landing Page (анонимный)
    B->>U: Показать страницу входа
```

---

## 6. Структуры данных

### 6.1 JWT Access Token

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "username": "ivanov.ii",
  "email": "ivanov.ii@dgi.mos.ru",
  "full_name": "Иванов Иван Иванович",
  "department": "IT",
  "position": "Ведущий специалист",
  "iat": 1715083200,
  "exp": 1715084100,
  "type": "access",
  "jti": "at-uuid-123",
  "service_roles": {
    "video": {
      "role": "admin",
      "role_id": "role-video-admin-uuid",
      "permissions": ["upload", "delete", "edit", "view", "moderate", "analytics"]
    },
    "messenger": {
      "role": "user",
      "role_id": "role-messenger-user-uuid",
      "permissions": ["read", "write", "call", "file_share"]
    },
    "dashboard": {
      "role": "viewer",
      "role_id": "role-dash-viewer-uuid",
      "permissions": ["read", "export_pdf"]
    }
  }
}
```

### 6.2 Refresh Token

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "jti": "rt-uuid-789",
  "type": "refresh",
  "device_id": "browser-chrome-win10-abc123",
  "iat": 1715083200,
  "exp": 1715688000
}
```

### 6.3 Session (Redis)

```
Key:    session:550e8400-e29b-41d4-a716-446655440000:browser-chrome-win10-abc123
TTL:    604800 (7 дней)
Value:
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "refresh_token_jti": "rt-uuid-789",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
  "created_at": "2024-05-07T12:00:00Z",
  "last_active": "2024-05-07T12:15:00Z",
  "services_accessed": ["video", "messenger"]
}
```

### 6.4 Database Schema (Shared Auth)

```sql
-- Пользователи (синхронизируются с LDAP)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    ldap_dn VARCHAR(255),
    department VARCHAR(100),
    position VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Сервисы
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,    -- 'video', 'messenger'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Роли в рамках сервиса
CREATE TABLE service_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(id),
    name VARCHAR(50) NOT NULL,           -- 'admin', 'editor', 'viewer'
    display_name VARCHAR(100),
    permissions JSONB DEFAULT '[]',      -- ["upload", "delete"]
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(service_id, name)
);

-- Связь пользователь ↔ роль в сервисе
CREATE TABLE user_service_roles (
    user_id UUID REFERENCES users(id),
    service_role_id UUID REFERENCES service_roles(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, service_role_id)
);
```

---

## 7. Service-to-Service Communication

### 7.1 Internal Auth

```mermaid
sequenceDiagram
    participant V as Video Service
    participant A as Auth Service
    participant PG as PostgreSQL

    V->>A: GET /internal/users/{user_id}/services/video
    Note over V,A: Authorization: Bearer INTERNAL_TOKEN<br/>X-From-Service: video-service
    A->>A: Validate INTERNAL_TOKEN against env
    A->>PG: SELECT roles, permissions FROM ...
    PG-->>A: user roles for 'video'
    A-->>V: 200 OK { role, permissions }
```

### 7.2 Internal Token

```http
GET /internal/users/550e8400-e29b-41d4-a716-446655440000/services/video HTTP/1.1
Host: auth-service:8000
Authorization: Bearer dgi-internal-service-token-2024-secure
X-From-Service: video-service
X-Request-ID: internal-req-001
```

---

## 8. Состояния пользователя (State Machine)

```mermaid
stateDiagram-v2
    [*] --> Anonymous: Открыть сайт
    Anonymous --> Authenticating: Клик "Войти"
    
    Authenticating --> Authenticated: LDAP + JWT success
    Authenticating --> Anonymous: Неверный пароль
    
    Authenticated --> ServiceAccess: Клик сервиса
    Authenticated --> Authenticated: Token refresh (auto)
    
    ServiceAccess --> Authenticated: Вернуться на портал
    ServiceAccess --> Forbidden: Нет роли в сервисе
    Forbidden --> ServiceAccess: Запросить доступ
    
    Authenticated --> Anonymous: Клик "Выйти"
    Authenticated --> Anonymous: Refresh token expired (7 дней)
    
    Anonymous --> [*]
```

---

## 9. Таблица маршрутизации Nginx

| Path | Upstream | Auth Required | Описание |
|------|----------|---------------|----------|
| `/` | `portal:3002` | Нет | Landing page |
| `/auth/*` | `auth-service:8000` | Нет | Login, register, token |
| `/video/*` | `video-service:8001` | Да (JWT) | Видеохостинг |
| `/messenger/*` | `messenger:8005` | Да (JWT) | Мессенджер (в планах) |
| `/dashboard/*` | `dashboard:8006` | Да (JWT) | Аналитика (в планах) |
| `/support/*` | `support:8007` | Да (JWT) | Техподдержка (в планах) |
| `/grafana/*` | `grafana:3000` | Admin | Мониторинг |
| `/prometheus/*` | `prometheus:9090` | Internal | Метрики |

---

## 10. Event Flow (RabbitMQ)

```mermaid
flowchart LR
    subgraph Events["Auth Events"]
        direction TB
        E1["user.created"]
        E2["user.updated"]
        E3["role.changed"]
        E4["user.logout"]
    end

    subgraph Queues["Очереди"]
        direction TB
        Q1["video.queue"]
        Q2["messenger.queue"]
        Q3["dashboard.queue"]
    end

    A["Auth Service"] -->|"publish"| E1
    A -->|"publish"| E2
    A -->|"publish"| E3
    A -->|"publish"| E4

    E1 --> Q1
    E2 --> Q2
    E3 --> Q3
    E4 --> Q1
    E4 --> Q2

    Q1 --> V["Video Service<br/>(invalidate cache)"]
    Q2 --> M["Messenger Service<br/>(update presence)"]
    Q3 --> D["Dashboard Service<br/>(recalc metrics)"]
```

---

*Документ для группового проекта ДГИ. Последнее обновление: 2024-05-07*
