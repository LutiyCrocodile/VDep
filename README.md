# 🎬 DGI Video Platform

> Корпоративная видеоплатформа Департамента городского имущества Москвы.  
> Загрузка, транскодирование, поиск и live-стриминг видео для сотрудников ДГИ.

---

## 📐 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (80/443)                        │
│              reverse proxy · SSL · rate limiting             │
└──────┬──────────┬───────────┬──────────┬────────────────────┘
       │          │           │          │
  portal:3002  frontend:3000  /api/*   :8888 HLS / :1935 RTMP
       │          │           │
       │    ┌─────┴──────┐    │
       │    │  Next.js   │    │
       │    │  Frontend  │    │
       │    └────────────┘    │
       │                      │
  ┌────┴──────────────────────┴──────────────────┐
  │               Backend Microservices           │
  │                                              │
  │  auth-service :8000   video-service :8001    │
  │  streaming-service :8002                     │
  │  notification-service :8003                  │
  │  search-service :8004                        │
  │                                              │
  │  dashboard-service  messenger-service        │
  │  support-service                             │
  └──────────────────────┬───────────────────────┘
                         │
  ┌──────────────────────┴───────────────────────┐
  │              Infrastructure                  │
  │                                              │
  │  PostgreSQL 15   Redis 7   RabbitMQ 4        │
  │  MinIO (S3)      Elasticsearch 8             │
  │  MediaMTX        Celery Worker               │
  │  Prometheus + Grafana                        │
  └──────────────────────────────────────────────┘
```

---

## 🧩 Сервисы

### Backend (Python 3.11 · FastAPI · SQLAlchemy asyncpg)

| Сервис | Порт | Назначение |
|---|---|---|
| **auth-service** | 8000 | JWT-аутентификация, LDAP/AD, RBAC, ESIA-заглушка |
| **video-service** | 8001 | Загрузка видео, каналы, лайки, история просмотров, HLS |
| **streaming-service** | 8002 | RTMP-ингест, HLS live-стрим, WebSocket уведомления |
| **notification-service** | 8003 | Email (SMTP), WebSocket уведомления |
| **search-service** | 8004 | Elasticsearch: поиск видео и субтитров |
| **dashboard-service** | 3003 | Аналитика (mock-данные, Django + React) |
| **messenger-service** | 3001 | Корпоративный чат (in-memory demo) |
| **support-service** | 3004 | Техподдержка (in-memory demo) |

### Frontend (Next.js 14 · React 18 · TypeScript · TailwindCSS · shadcn/ui)

| Приложение | Порт | Назначение |
|---|---|---|
| **frontend** | 3000 | Видеохостинг: просмотр, загрузка, стриминг |
| **portal** | 3002 | Единый портал входа для всех сервисов ДГИ |

---

## ⚙️ Основные возможности

### Видео
- Трёхэтапная загрузка: `init → upload-data → complete`
- Транскодирование через **Celery + FFmpeg**: HLS 180p–1080p с водяным знаком «DGI»
- Авто-генерация превью (thumbnail)
- Поиск по названию, описанию и субтитрам (Elasticsearch)
- Классификация доступа: `public / internal / confidential / restricted`

### Live-стриминг
- RTMP-ингест через **MediaMTX** (OBS → `rtmp://host:1935/live/<key>`)
- HLS-плейбек через Nginx → MediaMTX `:8888`
- Автоматическая финализация стрима при отключении OBS (reconcile loop)
- Запись стримов в `/recordings`

### Аутентификация и доступ
- JWT: access 15 мин, refresh 7 дней
- LDAP/Active Directory + локальный bcrypt fallback
- RBAC с сервисными ролями (service-specific permissions в JWT)
- Только сотрудники (`is_employee=true`) допускаются на портал

---

## 🗄️ База данных

Единая PostgreSQL `video_hosting` для всех сервисов.

```
users · roles · permissions · role_permissions
channels · videos · subscriptions · video_views · video_likes
streams · subtitles · notifications · audit_logs
services · service_roles · user_service_roles
```

---

## 🚀 Быстрый старт

### Требования
- Docker 24+ и Docker Compose v2
- 4 GB RAM свободно

### Запуск

```bash
cd infrastructure/docker

# 1. Настроить окружение
cp .env.example .env
# отредактировать .env (пароли, SECRET_KEY и т.д.)

# 2. Поднять все сервисы
docker compose up -d

# 3. Открыть
# Портал:   http://localhost:3002
# Frontend: http://localhost:3000
# Grafana:  http://localhost:3001  (admin/admin)
# MinIO:    http://localhost:9001  (minioadmin/minioadmin)
```

### Тестовые пользователи (пароль: `admin123`)

| Логин | Роль |
|---|---|
| `admin` | Полный доступ ко всем сервисам |
| `video_admin` | Администратор видеохостинга |
| `employee` | Стандартный сотрудник |
| `external` | Не-сотрудник (без доступа к порталу) |

---

## 🏗️ Структура проекта

```
video.dgi.mos.ru/
├── frontend/                  # Next.js видеохостинг
├── portal/                    # Next.js единый портал
├── services/
│   ├── auth-service/          # FastAPI: аутентификация
│   ├── video-service/         # FastAPI: видео
│   ├── streaming-service/     # FastAPI: стриминг
│   ├── notification-service/  # FastAPI: уведомления
│   ├── search-service/        # FastAPI: поиск
│   ├── dashboard-service/     # Django + React: аналитика
│   ├── messenger-service/     # FastAPI: мессенджер
│   └── support-service/       # FastAPI: техподдержка
├── infrastructure/
│   ├── docker/                # docker-compose.yml, nginx.conf, mediamtx.yml
│   └── database/              # schema.sql, seed_data.sql
└── tests/                     # Интеграционные тесты
```

---

## 🛠️ Технологический стек

| Слой | Технологии |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic, Celery |
| **Frontend** | Next.js 14, React 18, TypeScript, TailwindCSS, shadcn/ui, HLS.js |
| **БД / Кэш** | PostgreSQL 15, Redis 7, Elasticsearch 8 |
| **Очереди** | RabbitMQ 4, Celery |
| **Медиа** | FFmpeg 6, MediaMTX, Vosk (STT), MinIO |
| **Инфра** | Docker Compose, Nginx, Prometheus, Grafana |

---

## 📡 Production-деплой

```bash
cd infrastructure/docker

# SSL-сертификаты в ./ssl/
# Настроить nginx.prod.conf + публичные URLs в .env

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Ключевые переменные для прода:**

```env
SECRET_KEY=<openssl rand -hex 32>
POSTGRES_PASSWORD=<strong_password>
PUBLIC_HLS_BASE=https://your-domain.ru:8888
PUBLIC_RTMP_HOST=your-domain.ru
CORS_ORIGINS=https://your-domain.ru
```

---

## 📊 Мониторинг

- **Prometheus** → `http://localhost:9090`
- **Grafana** → `http://localhost:3001` (admin / `$GRAFANA_ADMIN_PASSWORD`)

Метрики собираются со всех FastAPI-сервисов через `/metrics`.

---

<div align="center">
  <sub>Дипломный проект · Департамент городского имущества Москвы</sub>
</div>
