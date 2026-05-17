# Сравнительная таблица сервисов проекта

Порты — **на хосте** при запуске `docker compose` из `infrastructure/docker` (локальная разработка).  
Внутренние имена в Docker-сети: `http://<service>:<port>`.

**Легенда статуса:** ✅ в `docker-compose.yml` · ⚠️ есть в коде/nginx, но **не** подключён в compose

---

## 1. Прикладные сервисы (бизнес-логика)

| Сервис | Порт (хост) | Порт (контейнер) | Назначение | Ключевые технологии | Статус |
|--------|-------------|------------------|------------|---------------------|--------|
| **portal** | **3002** | 3001 | Единая точка входа: портал ДГИ, ссылки на подсистемы, вход через auth | Next.js 14, React 18, TypeScript, Tailwind CSS | ✅ |
| **frontend** | **3000** | 3000 | UI видеохостинга: каталог, загрузка, просмотр, эфир (HLS/RTMP) | Next.js 14, React 18, TypeScript, Tailwind, Radix UI, TanStack Query, hls.js, Zustand, Axios | ✅ |
| **auth-service** | **8000** | 8000 | Единая авторизация: JWT, RBAC по сервисам, LDAP (опц.), internal API | Python 3.11, FastAPI, SQLAlchemy (async), asyncpg, JWT (python-jose), bcrypt, LDAP | ✅ |
| **video-service** | **8001** | 8001 | Видео: метаданные, загрузка, MinIO, права, интеграция с auth | Python 3.11, FastAPI, SQLAlchemy, MinIO SDK, Celery (очереди), OpenCV, MoviePy | ✅ |
| **streaming-service** | **8002** | 8002 | Прямые эфиры: каналы, webhooks MediaMTX, архив записей | Python 3.11, FastAPI, SQLAlchemy, httpx, MediaMTX (внешний контейнер) | ✅ |
| **notification-service** | **8003** | 8003 | Уведомления: email (SMTP), фоновые задачи | Python 3.11, FastAPI, Celery, Redis, aiosmtplib, WebSockets | ✅ |
| **search-service** | **8004** | 8004 | Поиск по видео, индексация в Elasticsearch | Python 3.11, FastAPI, Elasticsearch 8 (async), Celery, Redis | ✅ |
| **messenger-service** | **3001** | 3001 | Корпоративный мессенджер (заготовка UI + API) | Python 3.11, FastAPI, SQLAlchemy, httpx, Prometheus client | ⚠️ |
| **dashboard-service** | **3003** | 3003 | Аналитический дашборд (заготовка) | Python 3.11, FastAPI, SQLAlchemy, httpx, Prometheus client | ⚠️ |
| **support-service** | **3004** | 3004 | Техподдержка, заявки (заготовка) | Python 3.11, FastAPI, SQLAlchemy, httpx, Prometheus client | ⚠️ |
| **celery-worker** | — | — | Фоновая обработка видео (транскодинг, очереди `video_transcoding`) | Celery 5, Redis, тот же образ/код, что video-service | ✅ |
| **nginx** | **80**, **443** | 80, 443 | Reverse proxy, маршрутизация к API/UI, SSL (при настройке) | Nginx Alpine | ✅ |

> **Конфликт портов:** Grafana на хосте тоже использует **3001** (`3001:3000`). При одновременном запуске Grafana и messenger-service на 3001 — смените маппинг одного из сервисов в compose.

---

## 2. Стриминг и медиа

| Сервис | Порт (хост) | Назначение | Ключевые технологии | Статус |
|--------|-------------|------------|---------------------|--------|
| **mediamtx** | **1935** (RTMP), **8888** (HLS) | Приём RTMP, раздача HLS, каталог записей | MediaMTX (bluenviron/mediamtx) | ✅ |
| **minio** | **9000** (API), **9001** (консоль) | S3-совместимое хранилище файлов/видео | MinIO | ✅ |
| **minio-init** | — | Одноразовая инициализация бакета `videos`, публичное чтение | MinIO Client (`mc`) | ✅ |

---

## 3. Инфраструктура данных и очереди

| Сервис | Порт (хост) | Назначение | Ключевые технологии | Статус |
|--------|-------------|------------|---------------------|--------|
| **db** (PostgreSQL) | **5432** | Общая БД: пользователи, RBAC, видео, стримы | PostgreSQL 15 | ✅ |
| **redis** | **6379** | Кэш, брокер/бэкенд Celery | Redis 7 Alpine | ✅ |
| **rabbitmq** | **5672** (AMQP), **15672** (UI) | Очередь сообщений для video-service | RabbitMQ 4.1 Alpine | ✅ |
| **elasticsearch** | **9200**, **9300** | Полнотекстовый поиск (search-service) | Elasticsearch 8.11 | ✅ |

---

## 4. Мониторинг

| Сервис | Порт (хост) | Назначение | Ключевые технологии | Статус |
|--------|-------------|------------|---------------------|--------|
| **prometheus** | **9090** | Сбор метрик | Prometheus | ✅ |
| **grafana** | **3001** | Дашборды и визуализация метрик | Grafana | ✅ |
| **node-exporter** | **9100** | Метрики хоста (CPU, диск, сеть) | Prometheus Node Exporter | ✅ |

---

## 5. Сводка по доменам ДГИ (логические подсистемы)

| Подсистема | UI | API / backend | Порт UI | Порт API | Auth slug |
|------------|-----|---------------|---------|----------|-----------|
| Портал | portal | auth (логин) | 3002 | 8000 | — |
| Видеохостинг | frontend | video + streaming + search + notification | 3000 | 8001, 8002, 8004, 8003 | `video` |
| Мессенджер | в messenger-service | messenger-service | 3001 | 3001 | `messenger` |
| Дашборд | в dashboard-service | dashboard-service | 3003 | 3003 | `dashboard` |
| Техподдержка | в support-service | support-service | 3004 | 3004 | `support` |

---

## 6. Быстрая карта портов (localhost)

```
3000  frontend (видеохостинг)
3001  grafana ИЛИ messenger* (см. конфликт)
3002  portal
3003  dashboard*
3004  support*

8000  auth-service
8001  video-service
8002  streaming-service
8003  notification-service
8004  search-service

5432  PostgreSQL
6379  Redis
5672  RabbitMQ
15672 RabbitMQ Management
9000  MinIO API
9001  MinIO Console
9200  Elasticsearch
1935  RTMP (MediaMTX)
8888  HLS (MediaMTX)
80/443 nginx
9090  Prometheus
9100  node-exporter

* — сервис есть в репозитории; в текущем docker-compose.yml не поднят
```

---

*Источник: `infrastructure/docker/docker-compose.yml`, Dockerfile/pyproject.toml сервисов, `portal/package.json`, `frontend/package.json`.*
