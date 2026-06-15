# CODEMAP — DGI Portal System

## Структура проекта
```
video.dgi.mos.ru/
├── infrastructure/docker/       # Главная директория запуска
│   ├── docker-compose.yml       # Полная оркестрация всех сервисов
│   ├── .env.example             # Шаблон переменных окружения
│   ├── nginx.conf               # Dev-конфиг nginx (profile: proxy)
│   ├── nginx.prod.conf          # Prod-конфиг nginx (HTTPS, поддомены)
│   ├── mediamtx.yml             # Конфиг RTMP/HLS сервера
│   └── monitoring/              # prometheus.yml, grafana dashboards
├── services/
│   ├── auth-service/            # FastAPI, JWT, LDAP
│   ├── video-service/           # FastAPI, Celery, MinIO, HLS
│   ├── streaming-service/       # FastAPI, WebSocket, MediaMTX
│   ├── notification-service/    # FastAPI, SMTP, WebSocket
│   ├── search-service/          # FastAPI, Elasticsearch
│   ├── messenger-service/       # FastAPI + Vite React
│   ├── support-service/DGI_SUPPORT-main/  # FastAPI
│   └── dashboard-service/       # Django + Vite React
│       ├── backend/             # Django 5.2, DRF
│       │   ├── config/          # settings.py, urls.py, wsgi.py, auth.py
│       │   ├── dashboard_app/   # MetricType, MetricsData
│       │   ├── reports_app/     # Report, Template, PPTX/PDF генераторы
│       │   ├── properties_app/  # Property (объекты недвижимости)
│       │   ├── hr_app/          # HrEmployee
│       │   └── users_app/       # User, Role
│       └── frontend/            # Vite React
│           └── src/
│               ├── App.jsx      # Маршруты, навигация
│               ├── authStore.js # apiFetch, JWT хранилище
│               ├── ProtectedRoute.jsx
│               └── pages/
│                   ├── Dashboard.jsx      # Главная аналитика
│                   ├── ReportsList.jsx    # Управление отчётами
│                   ├── ImportPage.jsx     # Импорт Excel
│                   ├── HrStatusPage.jsx   # HR-статусы обучения
│                   ├── TemplateBuilder.jsx
│                   └── LoginPage.jsx
├── frontend/                    # Next.js 14 (видео-хостинг)
└── portal/                      # Next.js 14 (единый портал входа)
```

---

## Сервисы и порты

| Сервис               | Внутренний порт | Внешний порт | Технология        |
|----------------------|-----------------|--------------|-------------------|
| db                   | 5432            | 5432         | PostgreSQL 15     |
| redis                | 6379            | 6379         | Redis 7           |
| rabbitmq             | 5672/15672      | 5672/15672   | RabbitMQ 4.1.8    |
| minio                | 9000/9001       | 9000/9001    | MinIO             |
| elasticsearch        | 9200/9300       | 9200/9300    | Elasticsearch 8   |
| mediamtx             | 1935/8888/9997  | 1935/8888    | MediaMTX          |
| auth-service         | 8000            | 8000         | FastAPI           |
| video-service        | 8001            | 8001         | FastAPI + Celery  |
| streaming-service    | 8002            | 8002         | FastAPI           |
| notification-service | 8003            | 8003         | FastAPI           |
| search-service       | 8004            | 8004         | FastAPI           |
| messenger-service    | 8005            | 8005         | FastAPI           |
| support-service      | 3004            | 3004         | FastAPI           |
| dashboard-service    | 8000            | 3003         | Django + gunicorn |
| dashboard-frontend   | 5173            | 5173         | Vite React        |
| messenger-frontend   | 3005            | 3005         | Vite React        |
| frontend             | 3000            | 3000         | Next.js 14        |
| portal               | 3001            | 3002         | Next.js 14        |
| prometheus           | 9090            | 9090         | Prometheus        |
| grafana              | 3000            | 3001         | Grafana           |
| node-exporter        | 9100            | 9100         | Prometheus exporter|

---

## API роуты

### auth-service (:8000)
```
POST   /token                          — логин (OAuth2)
POST   /refresh                        — обновить токен
POST   /logout                         — выход
GET    /users/me                       — профиль текущего пользователя
GET    /users/me/services              — сервисы пользователя
GET    /users                          — все пользователи
GET    /users/search                   — поиск пользователей
GET    /internal/users/{id}/permissions        — [internal]
GET    /internal/users/{id}/services/{slug}    — [internal]
GET    /internal/services/{slug}/users         — [internal]
GET    /health
GET    /metrics
```

### video-service (:8001)
```
POST   /videos/upload/init             — инициализация загрузки
POST   /videos/{id}/upload-data        — передача данных
POST   /videos/{id}/complete           — завершение загрузки
POST   /videos/{id}/publish            — публикация → Celery transcoding
GET    /videos                         — список
GET    /videos/{id}                    — детали
GET    /videos/{id}/signed-url         — подписанный URL
GET    /videos/{id}/thumbnail          — превью
GET    /videos/{id}/playlist           — HLS плейлист
PUT    /videos/{id}                    — обновление
DELETE /videos/{id}                    — удаление
POST   /videos/{id}/like               — лайк
GET    /videos/{id}/access             — список доступа
POST   /channels                       — создать канал
GET    /channels/my                    — мой канал
GET    /media/{path}                   — медиа через API
GET    /health
```

### streaming-service (:8002)
```
POST   /streams                        — создать стрим
GET    /streams                        — список стримов
GET    /streams/live                   — live стримы
GET    /streams/{id}                   — детали
PUT    /streams/{id}/start             — запустить
PUT    /streams/{id}/stop              — остановить
WS     /streams/{id}/ws                — WebSocket обновления
POST   /internal/mediamtx/auth         — [internal] auth для MediaMTX
GET    /health
```

### notification-service (:8003)
```
POST   /notifications                  — создать уведомление
GET    /notifications                  — список
PUT    /notifications/{id}/read        — прочитать
POST   /notifications/mark-all-read    — прочитать все
GET    /notifications/unread-count     — счётчик
WS     /ws                             — WebSocket
GET    /health
```

### search-service (:8004)
```
GET    /search                         — поиск в Elasticsearch
GET    /videos/{id}/subtitles          — субтитры
POST   /search/index/{id}              — индексировать видео
DELETE /search/index/{id}              — удалить из индекса
GET    /health
```

### messenger-service (:8005)
```
[FastAPI с DB schema: messenger]
GET    /api/health
```

### support-service (:3004)
```
[FastAPI с DB schema: support]
GET    /
```

### dashboard-service (:3003 → Django :8000)
```
GET/POST/PUT/DELETE  /api/report-statuses/
GET/POST/PUT/DELETE  /api/report-templates/
GET/POST/PUT/DELETE  /api/reports/
POST                 /api/reports/{id}/generate_pptx/
POST                 /api/reports/{id}/generate_pdf/
POST                 /api/reports/{id}/load_from_metrics/    — загрузка из MetricsData
POST                 /api/reports/{id}/change_status/
GET/POST/PUT/DELETE  /api/shared-reports/
GET/POST/PUT/DELETE  /api/comments/
GET/POST/PUT/DELETE  /api/users/
GET/POST/PUT/DELETE  /api/roles/
GET/POST/PUT/DELETE  /api/metric-types/
GET/POST/PUT/DELETE  /api/metrics-data/
GET/POST/PUT/DELETE  /api/properties/
POST                 /api/excel-import/upload/              — импорт метрик из Excel
POST                 /api/excel-import/hr_status/           — импорт HR-статусов
```

---

## Зависимости сервисов

```
auth-service ←── db
video-service ←── db, minio, redis, rabbitmq, auth-service
streaming-service ←── db, redis, auth-service, video-service, minio, mediamtx
notification-service ←── db, redis, auth-service
search-service ←── db, elasticsearch, redis, auth-service
celery-worker ←── redis, minio, db, auth-service, video-service
messenger-service ←── db, redis, auth-service
support-service ←── db, auth-service
dashboard-service ←── db, auth-service
```

---

## Переменные окружения (критические для prod)

```
SECRET_KEY                   — JWT секрет auth-service (openssl rand -hex 32)
INTERNAL_AUTH_TOKEN          — inter-service токен (openssl rand -hex 32)
POSTGRES_PASSWORD            — пароль БД
MINIO_ROOT_USER/PASSWORD     — MinIO credentials
CORS_ORIGINS                 — список разрешённых доменов
PUBLIC_VIDEO_API_URL         — внешний URL video-service (для браузера)
PUBLIC_HLS_BASE              — внешний URL HLS стримов
PUBLIC_RTMP_HOST             — внешний хост RTMP
MINIO_EXTERNAL_ENDPOINT      — внешний URL MinIO (для ссылок в JSON)
SMTP_SERVER/PORT/USERNAME/PASSWORD — SMTP для уведомлений
```

---

## Ключевые файлы для изменения при деплое

| Файл | Что менять |
|------|-----------|
| `infrastructure/docker/.env` | Все секреты и prod-URL |
| `infrastructure/docker/nginx.prod.conf` | Домены, SSL пути |
| `services/dashboard-service/backend/config/settings.py` | SECRET_KEY, ALLOWED_HOSTS, DEBUG=False, CORS |
| `infrastructure/docker/docker-compose.yml` | PORT маппинги, volume пути |
| `portal/.env.local` | Внешние URL сервисов |
| `frontend/.env.local` (если есть) | API URLs |

---

## Известные проблемы

1. **dashboard-service settings.py** — `SECRET_KEY` захардкожен, `DEBUG=True`, нужно параметризовать через env
2. **dashboard-service CORS** — жёстко прописаны localhost порты, нужно добавить prod домен
3. **dashboard-service frontend** — Vite dev server (не подходит для prod, нужен nginx)
4. **minio-init CORS** — разрешены только localhost:3000/3002, нужно добавить prod домены
5. **nginx.prod.conf** — upstream messenger ссылается на :3001 (устарело, теперь :8005)
6. **frontend/video** — монтирует src как volume (dev-режим), для prod надо убрать
7. **dashboard-service** — нет healthcheck в docker-compose (закомментирован)
8. **db порт 5432** — открыт наружу, в prod надо закрыть
