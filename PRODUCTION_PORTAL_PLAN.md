# План развёртывания Единого Портала ДГИ

## 1. Рекомендуемая конфигурация сервера

### Облачный провайдер
**Рекомендация:** Yandex Cloud / VK Cloud / Selectel (Российские провайдеры для гос. структур)

### Минимальная конфигурация (до 1000 пользователей)
```
CPU:     8 vCPU (Intel Xeon / AMD EPYC)
RAM:     16 GB DDR4
Storage: 200 GB NVMe SSD (система + данные)
         + 500 GB HDD/S3 (хранение видео - можно подключить Object Storage)
Network: 100 Mbps (гарантированный)
OS:      Ubuntu 22.04 LTS Server
```

### Оптимальная конфигурация (1000-10000 пользователей)
```
CPU:     16 vCPU
RAM:     32 GB DDR4
Storage: 500 GB NVMe SSD (PostgreSQL + MySQL)
         + 2 TB Object Storage (MinIO / S3 для видео)
Network: 500 Mbps
```

### Стоимость (примерно)
- Yandex Cloud: ~15,000-25,000 ₽/мес (оптимальная)
- VK Cloud: ~12,000-20,000 ₽/мес
- Selectel: ~18,000-30,000 ₽/мес

---

## 2. Доменное имя и DNS

### Варианты доменов:
1. **portal.dgi.mos.ru** - поддомен ДГИ (если есть доступ к DNS)
2. **dgi-portal.ru** - отдельный домен
3. **сотрудникам-дги.рф** - кириллический

### DNS записи:
```
portal.dgi.mos.ru     A     <IP сервера>
auth.dgi.mos.ru       A     <IP сервера>
video.dgi.mos.ru      A     <IP сервера>
messenger.dgi.mos.ru  A     <IP сервера>
dashboard.dgi.mos.ru  A     <IP сервера>
support.dgi.mos.ru    A     <IP сервера>

; Или одна запись с путями:
dgi-portal.ru         A     <IP сервера>
```

### SSL сертификаты:
- **Let's Encrypt** (бесплатно, автоматическое обновление)
- **Яндекс SSL** (если используете Yandex Cloud)

---

## 3. Архитектура Единого Портала

### Общая схема
```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      NGINX (443)                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │  SSL    │  │  SSO    │  │  Rate   │  │ Static  │         │
│  │ Terminat│  │ Check   │  │ Limiting│  │ Files   │         │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  DOCKER COMPOSE STACK                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Frontend  │  │   Frontend  │  │   Frontend  │         │
│  │   (Portal)  │  │   (Video)   │  │   (Support) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│  ┌──────┴────────────────┴────────────────┴──────┐         │
│  │              Auth Service                      │         │
│  │         (Единая точка входа)                  │         │
│  └──────────────────┬─────────────────────────────┘         │
│                     │                                        │
│  ┌──────────────────┼──────────────────────────────────────┐  │
│  │                  ▼    Docker Internal Network         │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │  │
│  │  │ Video   │  │Messenger│  │Dashboard│  │Support  │   │  │
│  │  │Service  │  │Service  │  │Service  │  │Service  │   │  │
│  │  │ (8001)  │  │ (8005)  │  │ (8006)  │  │ (8007)  │   │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │  │
│  │       │            │            │            │           │  │
│  │       └────────────┴────────────┴────────────┘           │  │
│  │                    │                                      │  │
│  │  ┌─────────────────┼────────────────────────────────┐   │  │
│  │  │       PostgreSQL (Shared Auth DB)                 │   │  │
│  │  │  - users                                         │   │  │
│  │  │  - roles                                         │   │  │
│  │  │  - service_permissions                           │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │       PostgreSQL (Video Service DB)             │   │  │
│  │  │  - videos, channels, views                       │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │       MySQL (Tech Support DB)                   │   │  │
│  │  │  - tickets, categories                           │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │       MinIO (Object Storage)                    │   │  │
│  │  │  - videos, avatars, attachments                  │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │       Redis (Shared Cache & Sessions)          │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Единая точка входа (SSO)

### Вариант A: Subdomain-based (рекомендуется)
```
portal.dgi.mos.ru      → Единый landing page
├── auth.dgi.mos.ru    → Auth Service (8000)
├── video.dgi.mos.ru   → Video Hosting (8001)
├── messenger.dgi.mos.ru → Messenger (8005)
├── dashboard.dgi.mos.ru → Dashboard (8006)
└── support.dgi.mos.ru → Tech Support (8007)
```

### Вариант B: Path-based
```
dgi-portal.ru/         → Landing page
dgi-portal.ru/auth/    → Auth Service
dgi-portal.ru/video/   → Video Hosting
dgi-portal.ru/messenger/ → Messenger
dgi-portal.ru/dashboard/ → Dashboard
dgi-portal.ru/support/ → Tech Support
```

### Рекомендация: Вариант A (Subdomains)
**Преимущества:**
- Чище архитектура
- Легче масштабировать отдельные сервисы
- Проще CORS
- Изолированные cookie

### SSO Flow
```
1. Пользователь открывает portal.dgi.mos.ru
   → Видит единую страницу с карточками сервисов

2. Нажимает "Видеохостинг"
   → Редирект на auth.dgi.mos.ru/login?redirect=video

3. Вводит логин/пароль
   → Auth Service проверяет в PostgreSQL
   → Создаёт JWT с сервисами: {"video": {...}, "messenger": {...}}
   → Редирект на video.dgi.mos.ru?token=JWT

4. Video Service проверяет JWT
   → Валидирует подпись
   → Проверяет права на video
   → Показывает интерфейс

5. Пользователь переходит в Messenger
   → Уже есть JWT, просто проверка прав
```

---

## 5. База данных работников ДГИ

### Схема (PostgreSQL - Shared)

```sql
-- Основная таблица работников
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ldap_dn VARCHAR(255) UNIQUE,           -- LDAP Distinguished Name
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL, -- login
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),              -- Отдел
    position VARCHAR(100),                  -- Должность
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Сервисы
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,     -- 'video', 'messenger', 'dashboard', 'support'
    name VARCHAR(100) NOT NULL,           -- 'Видеохостинг ДГИ'
    description TEXT,
    icon_url VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    requires_auth BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Роли внутри сервисов
CREATE TABLE service_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,            -- 'admin', 'user', 'viewer', 'agent'
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(service_id, name)
);

-- Права (разрешения)
CREATE TABLE service_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,           -- 'video:upload', 'messenger:create_channel'
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Связь ролей и прав
CREATE TABLE service_role_permissions (
    role_id UUID REFERENCES service_roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES service_permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Назначение ролей работникам
CREATE TABLE employee_service_roles (
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    service_role_id UUID REFERENCES service_roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES employees(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                   -- Для временных доступов
    PRIMARY KEY (employee_id, service_role_id)
);

-- История входов (аудит)
CREATE TABLE login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(id),
    service_slug VARCHAR(50),               -- В какой сервис вошли
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN,
    failure_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Сессии (для logout со всех устройств)
CREATE TABLE active_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    token_jti VARCHAR(255),                 -- JWT ID
    device_info TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP
);

-- Заполнение сервисов
INSERT INTO services (slug, name, description, icon_url) VALUES
('video', 'Видеохостинг ДГИ', 'Система видеохостинга для сотрудников', '/icons/video.svg'),
('messenger', 'Мессенджер ДГИ', 'Защищённый корпоративный мессенджер', '/icons/messenger.svg'),
('dashboard', 'Дашборд ДГИ', 'Аналитика и показатели', '/icons/dashboard.svg'),
('support', 'Техподдержка ДГИ', 'Система заявок в техническую поддержку', '/icons/support.svg');
```

### Данные для каждого сервиса

**Video Hosting** (PostgreSQL - отдельная БД или схема):
```sql
-- Схема video_service
CREATE TABLE video_service.channels (...)
CREATE TABLE video_service.videos (...)
CREATE TABLE video_service.views (...)
-- Связь с employees через employee_id UUID
```

**Tech Support** (MySQL - как требуется):
```sql
-- База support_db
CREATE TABLE tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id VARCHAR(36),  -- UUID из PostgreSQL
    title VARCHAR(255),
    description TEXT,
    status ENUM('open', 'in_progress', 'resolved', 'closed'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Messenger** (может использовать PostgreSQL или MongoDB):
```sql
-- Схема messenger_service
CREATE TABLE conversations (...)
CREATE TABLE messages (...)
```

---

## 6. Nginx конфигурация (единая точка входа)

```nginx
# /etc/nginx/nginx.conf

upstream auth_service {
    server localhost:8000;
}

upstream video_service {
    server localhost:8001;
}

upstream messenger_service {
    server localhost:8005;
}

upstream dashboard_service {
    server localhost:8006;
}

upstream support_service {
    server localhost:8007;
}

upstream portal_frontend {
    server localhost:3000;
}

# Portal landing page
server {
    listen 443 ssl http2;
    server_name portal.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://portal_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Auth Service
server {
    listen 443 ssl http2;
    server_name auth.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://auth_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Video Hosting
server {
    listen 443 ssl http2;
    server_name video.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    # Video streaming (HLS)
    location /hls/ {
        alias /var/www/hls/;
        add_header Cache-Control "public, max-age=31536000";
        add_header Access-Control-Allow-Origin "*";
    }

    # API
    location /api/ {
        proxy_pass http://video_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://video_service;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Messenger
server {
    listen 443 ssl http2;
    server_name messenger.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://messenger_service;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;  # WebSocket support
    }
}

# Dashboard
server {
    listen 443 ssl http2;
    server_name dashboard.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://dashboard_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Tech Support
server {
    listen 443 ssl http2;
    server_name support.dgi.mos.ru;

    ssl_certificate /etc/letsencrypt/live/dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://support_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name *.dgi.mos.ru dgi.mos.ru;
    return 301 https://$host$request_uri;
}
```

---

## 7. Docker Compose для Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # ═══════════════════════════════════════════════════
  # REVERSE PROXY
  # ═══════════════════════════════════════════════════
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      - auth-service
      - video-service
      - messenger-service
      - dashboard-service
      - support-service
    networks:
      - dgi_network
    restart: always

  # ═══════════════════════════════════════════════════
  # SHARED AUTHENTICATION
  # ═══════════════════════════════════════════════════
  auth-service:
    build: ./services/auth-service
    environment:
      # Database
      DATABASE_URL: postgresql+asyncpg://auth_user:${AUTH_DB_PASSWORD}@postgres-shared:5432/dgi_auth
      
      # JWT
      SECRET_KEY: ${JWT_SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      
      # Service config
      AUTH_MODE: standalone  # Все сервисы на одном сервере
      SERVICE_ID: auth
      SERVICE_NAME: "Авторизация ДГИ"
      
      # LDAP (для интеграции с AD)
      LDAP_SERVER: ${LDAP_SERVER}
      LDAP_BASE_DN: ${LDAP_BASE_DN}
    depends_on:
      postgres-shared:
        condition: service_healthy
    networks:
      - dgi_network
    restart: always

  # ═══════════════════════════════════════════════════
  # MICROSERVICES
  # ═══════════════════════════════════════════════════
  video-service:
    build: ./services/video-service
    environment:
      DATABASE_URL: postgresql+asyncpg://video_user:${VIDEO_DB_PASSWORD}@postgres-video:5432/video_service
      AUTH_SERVICE_URL: http://auth-service:8000
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - auth-service
      - postgres-video
      - minio
      - redis
    networks:
      - dgi_network
    restart: always

  messenger-service:
    build: ./services/messenger  # Ваш другой проект
    environment:
      DATABASE_URL: postgresql+asyncpg://messenger_user:${MESSENGER_DB_PASSWORD}@postgres-messenger:5432/messenger_service
      AUTH_SERVICE_URL: http://auth-service:8000
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      REDIS_URL: redis://redis:6379/1
    depends_on:
      - auth-service
      - postgres-messenger
      - redis
    networks:
      - dgi_network
    restart: always

  dashboard-service:
    build: ./services/dashboard  # Ваш другой проект
    environment:
      DATABASE_URL: postgresql+asyncpg://dashboard_user:${DASHBOARD_DB_PASSWORD}@postgres-dashboard:5432/dashboard_service
      AUTH_SERVICE_URL: http://auth-service:8000
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
    depends_on:
      - auth-service
      - postgres-dashboard
    networks:
      - dgi_network
    restart: always

  support-service:
    build: ./services/support  # Ваш другой проект
    environment:
      DATABASE_URL: mysql+pymysql://support_user:${SUPPORT_DB_PASSWORD}@mysql-support:3306/support_service
      AUTH_SERVICE_URL: http://auth-service:8000
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
    depends_on:
      - auth-service
      - mysql-support
    networks:
      - dgi_network
    restart: always

  # ═══════════════════════════════════════════════════
  # FRONTENDS
  # ═══════════════════════════════════════════════════
  portal-frontend:
    build: ./frontend/portal  # Единый landing page
    environment:
      NEXT_PUBLIC_AUTH_URL: https://auth.dgi.mos.ru
      NEXT_PUBLIC_VIDEO_URL: https://video.dgi.mos.ru
      NEXT_PUBLIC_MESSENGER_URL: https://messenger.dgi.mos.ru
      NEXT_PUBLIC_DASHBOARD_URL: https://dashboard.dgi.mos.ru
      NEXT_PUBLIC_SUPPORT_URL: https://support.dgi.mos.ru
    networks:
      - dgi_network
    restart: always

  # ═══════════════════════════════════════════════════
  # DATABASES
  # ═══════════════════════════════════════════════════
  postgres-shared:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dgi_auth
      POSTGRES_USER: auth_user
      POSTGRES_PASSWORD: ${AUTH_DB_PASSWORD}
    volumes:
      - postgres_shared_data:/var/lib/postgresql/data
      - ./init-scripts/postgres-shared:/docker-entrypoint-initdb.d
    networks:
      - dgi_network
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U auth_user -d dgi_auth"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres-video:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: video_service
      POSTGRES_USER: video_user
      POSTGRES_PASSWORD: ${VIDEO_DB_PASSWORD}
    volumes:
      - postgres_video_data:/var/lib/postgresql/data
    networks:
      - dgi_network
    restart: always

  postgres-messenger:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: messenger_service
      POSTGRES_USER: messenger_user
      POSTGRES_PASSWORD: ${MESSENGER_DB_PASSWORD}
    volumes:
      - postgres_messenger_data:/var/lib/postgresql/data
    networks:
      - dgi_network
    restart: always

  postgres-dashboard:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dashboard_service
      POSTGRES_USER: dashboard_user
      POSTGRES_PASSWORD: ${DASHBOARD_DB_PASSWORD}
    volumes:
      - postgres_dashboard_data:/var/lib/postgresql/data
    networks:
      - dgi_network
    restart: always

  mysql-support:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: support_service
      MYSQL_USER: support_user
      MYSQL_PASSWORD: ${SUPPORT_DB_PASSWORD}
    volumes:
      - mysql_support_data:/var/lib/mysql
    networks:
      - dgi_network
    restart: always

  # ═══════════════════════════════════════════════════
  # INFRASTRUCTURE
  # ═══════════════════════════════════════════════════
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - dgi_network
    restart: always

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    networks:
      - dgi_network
    restart: always

  # Celery Worker (для видео)
  celery-worker:
    build: ./services/video-service
    command: celery -A src.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://video_user:${VIDEO_DB_PASSWORD}@postgres-video:5432/video_service
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    depends_on:
      - redis
      - postgres-video
      - minio
    networks:
      - dgi_network
    restart: always

volumes:
  postgres_shared_data:
  postgres_video_data:
  postgres_messenger_data:
  postgres_dashboard_data:
  mysql_support_data:
  redis_data:
  minio_data:
  nginx_cache:

networks:
  dgi_network:
    driver: bridge
```

---

## 8. План миграции (пошагово)

### Phase 1: Подготовка (1-2 недели)
```
□ Арендовать сервер
□ Купить домен
□ Настроить DNS
□ Создать .env.production с секретами
□ Подготовить SSL сертификаты
```

### Phase 2: Базовая инфраструктура (1 неделя)
```
□ Установить Ubuntu 22.04
□ Настроить UFW firewall
□ Установить Docker & Docker Compose
□ Развернуть PostgreSQL (shared)
□ Развернуть Auth Service
□ Настроить Nginx + SSL
□ Настроить мониторинг (Prometheus/Grafana)
```

### Phase 3: Video Hosting (1 неделя)
```
□ Перенести текущий video-service
□ Миграция базы данных
□ Настроить MinIO
□ Тестирование загрузки/воспроизведения
□ Настройка LDAP интеграции
```

### Phase 4: Остальные сервисы (2-3 недели)
```
□ Интеграция Messenger
□ Интеграция Dashboard
□ Интеграция Tech Support
□ Настройка единого портала
□ Тестирование SSO
```

### Phase 5: Запуск (1 неделя)
```
□ Загрузка базы работников
□ Назначение ролей
□ Обучение пользователей
□ Мониторинг и оптимизация
```

---

## 9. Скрипты для автоматизации

### init-server.sh
```bash
#!/bin/bash
# Инициализация сервера Ubuntu 22.04

# Обновление
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Установка дополнительных пакетов
apt install -y nginx certbot python3-certbot-nginx fail2ban ufw

# Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Fail2ban
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF
systemctl restart fail2ban

echo "Server initialized. Reboot and run deploy.sh"
```

### deploy.sh
```bash
#!/bin/bash
# Деплой проекта

cd /opt/dgi-portal

# Pull latest code
git pull origin main

# Generate secrets если нет
if [ ! -f .env ]; then
    echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" > .env
    echo "INTERNAL_AUTH_TOKEN=$(uuidgen)" >> .env
    echo "AUTH_DB_PASSWORD=$(openssl rand -base64 32)" >> .env
    # ... остальные переменные
fi

# Build and deploy
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build

# Cleanup
docker system prune -f

echo "Deployed successfully!"
```

---

## 10. Мониторинг и логирование

### Prometheus + Grafana (уже в проекте)
```yaml
# Добавить в docker-compose.prod.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus

grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"  # Только для admin VPN
  volumes:
    - grafana_data:/var/lib/grafana
```

### Логи
```yaml
# ELK Stack или Loki
loki:
  image: grafana/loki:latest
  volumes:
    - ./monitoring/loki-config.yml:/etc/loki/config.yml
    - loki_data:/loki
```

### Алерты (Alertmanager)
- CPU > 80%
- RAM > 85%
- Disk > 90%
- Service down
- Failed login attempts > 10/min

---

## 11. Резервное копирование

### backup.sh
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups
S3_BUCKET=s3://dgi-portal-backups

# PostgreSQL
pg_dump -h localhost -U auth_user dgi_auth | gzip > $BACKUP_DIR/auth_$DATE.sql.gz
pg_dump -h localhost -U video_user video_service | gzip > $BACKUP_DIR/video_$DATE.sql.gz

# MySQL
mysqldump -h localhost -u support_user -p$SUPPORT_DB_PASSWORD support_service | gzip > $BACKUP_DIR/support_$DATE.sql.gz

# MinIO
mc mirror minio/videos $BACKUP_DIR/minio_videos_$DATE

# Upload to S3
aws s3 sync $BACKUP_DIR $S3_BUCKET/daily/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
```

### Cron
```
0 2 * * * /opt/dgi-portal/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## Итоговая структура проекта

```
dgi-portal/
├── infrastructure/
│   └── docker/
│       ├── docker-compose.yml
│       ├── .env.example
│       └── .env                # <-- не коммитировать (из .env.example)
├── nginx/
│   ├── nginx.conf
│   └── ssl/
├── services/
│   ├── auth-service/       # Единый auth (текущий)
│   ├── video-service/      # Видеохостинг (текущий)
│   ├── messenger/          # Другой проект
│   ├── dashboard/          # Другой проект
│   └── support/            # Другой проект
├── frontend/
│   ├── portal/             # Единый landing
│   ├── video/              # Видеохостинг UI
│   ├── messenger/          # Мессенджер UI
│   ├── dashboard/          # Дашборд UI
│   └── support/            # Техподдержка UI
├── init-scripts/
│   └── postgres-shared/
│       └── 01-init-auth.sql
├── monitoring/
│   ├── prometheus.yml
│   ├── grafana-dashboards/
│   └── alertmanager/
├── scripts/
│   ├── init-server.sh
│   ├── deploy.sh
│   └── backup.sh
└── docs/
    ├── DEPLOYMENT.md
    ├── MULTI_SERVICE_AUTH.md
    └── ADMIN_GUIDE.md
```

---

## Что нужно сделать прямо сейчас:

1. **Выбрать облачный провайдер** - Yandex Cloud рекомендую
2. **Купить домен** - dgi-portal.ru или поддомен от ДГИ
3. **Подготовить .env** - заполнить все секреты
4. **Настроить Git** - если ещё не в репозитории
5. **Создать Portal Frontend** - единую страницу входа

Готов помочь с любым из шагов!
