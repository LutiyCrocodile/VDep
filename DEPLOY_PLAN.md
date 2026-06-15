# Детальный план деплоя DGI Portal на сервер

## Требования к серверу
- **OS:** Ubuntu 22.04 LTS
- **CPU:** 8+ vCPU
- **RAM:** 16+ GB
- **SSD:** 200+ GB
- **Сеть:** публичный IP, домен, открыты порты 80, 443, 1935 (RTMP)

---

## ЭТАП 1 — Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Установка Nginx (для Certbot)
sudo apt install nginx certbot python3-certbot-nginx -y

# Установка UFW (файрвол)
sudo apt install ufw -y
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 1935    # RTMP
sudo ufw enable

# Установка Fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

---

## ЭТАП 2 — SSL сертификаты (Let's Encrypt)

```bash
# Получение сертификатов для всех поддоменов
# Замените YOUR_DOMAIN на ваш домен (например portal.dgi.mos.ru)
sudo certbot certonly --nginx \
  -d portal.dgi.mos.ru \
  -d video.dgi.mos.ru \
  -d api.dgi.mos.ru

# Проверка автообновления
sudo certbot renew --dry-run
```

---

## ЭТАП 3 — Копирование кода на сервер

```bash
# На сервере — клонирование репозитория
git clone <YOUR_REPO_URL> /opt/dgi-portal
cd /opt/dgi-portal
```

---

## ЭТАП 4 — Настройка переменных окружения

```bash
cd /opt/dgi-portal/infrastructure/docker
cp .env.example .env
nano .env
```

**Обязательные значения в .env:**
```env
COMPOSE_PROJECT_NAME=video_dgim_mos

# PostgreSQL
POSTGRES_DB=video_hosting
POSTGRES_USER=dgi_user
POSTGRES_PASSWORD=<СИЛЬНЫЙ_ПАРОЛЬ>

# Секреты (генерация: openssl rand -hex 32)
SECRET_KEY=<СГЕНЕРИРОВАТЬ>
INTERNAL_AUTH_TOKEN=<СГЕНЕРИРОВАТЬ>

# MinIO
MINIO_ROOT_USER=<ПОЛЬЗОВАТЕЛЬ>
MINIO_ROOT_PASSWORD=<СИЛЬНЫЙ_ПАРОЛЬ>

# Медиа URLs (внешние, для браузера)
PUBLIC_VIDEO_API_URL=https://api.dgi.mos.ru
PUBLIC_MEDIA_VIA_API=true
MINIO_EXTERNAL_ENDPOINT=api.dgi.mos.ru/minio

# Стриминг
PUBLIC_HLS_BASE=https://api.dgi.mos.ru/hls
PUBLIC_RTMP_HOST=portal.dgi.mos.ru

# SMTP (уведомления)
SMTP_SERVER=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USERNAME=<EMAIL>
SMTP_PASSWORD=<ПАРОЛЬ_ПРИЛОЖЕНИЯ>
SMTP_FROM_EMAIL=<EMAIL>
FRONTEND_PUBLIC_URL=https://video.dgi.mos.ru

# CORS — список prod доменов
CORS_ORIGINS=https://portal.dgi.mos.ru,https://video.dgi.mos.ru,https://api.dgi.mos.ru

# Grafana
GRAFANA_ADMIN_PASSWORD=<СИЛЬНЫЙ_ПАРОЛЬ>

# Portal
AUTH_INTERNAL_URL=http://auth-service:8000
PORTAL_URL=https://portal.dgi.mos.ru

# Nginx
NGINX_HTTP_PORT=80
```

---

## ЭТАП 5 — Исправление конфигураций для prod

### 5.1. dashboard-service/backend/config/settings.py

Параметризировать через env:
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://localhost:3002'
).split(',')
```

### 5.2. Добавить ALLOWED_HOSTS в docker-compose.yml для dashboard-service

```yaml
dashboard-service:
  environment:
    SECRET_KEY: ${SECRET_KEY}
    DEBUG: "False"
    ALLOWED_HOSTS: "portal.dgi.mos.ru,api.dgi.mos.ru,dashboard-service"
    CORS_ALLOWED_ORIGINS: "https://portal.dgi.mos.ru,https://video.dgi.mos.ru"
```

### 5.3. Собрать dashboard-frontend для prod (не Vite dev)

Изменить `Dockerfile.frontend`:
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 5.4. Закрыть внутренние порты БД

В `docker-compose.yml` удалить маппинги портов для:
- `db` (5432 → убрать, только внутри docker сети)
- `redis` (6379 → убрать)
- `rabbitmq` (5672, 15672 → убрать)
- `elasticsearch` (9200, 9300 → убрать)

### 5.5. MinIO CORS для prod

В `minio-init` добавить prod домены:
```bash
printf '%s\n' '{"CORSRules":[{"AllowedOrigins":["https://portal.dgi.mos.ru","https://video.dgi.mos.ru"],"AllowedMethods":["GET","HEAD"],"AllowedHeaders":["*"],"MaxAgeSeconds":3000}]}' > /tmp/cors.json
```

### 5.6. nginx.prod.conf — исправить upstream messenger

```nginx
upstream messenger_service_upstream {
    server messenger-service:8005;  # было 3001
}
```

---

## ЭТАП 6 — Настройка Nginx на хосте (для SSL и проксирования)

Создать `/etc/nginx/sites-available/dgi-portal`:
```nginx
# Редирект HTTP → HTTPS
server {
    listen 80;
    server_name portal.dgi.mos.ru video.dgi.mos.ru api.dgi.mos.ru;
    return 301 https://$host$request_uri;
}

# Portal
server {
    listen 443 ssl http2;
    server_name portal.dgi.mos.ru;
    ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Video Frontend
server {
    listen 443 ssl http2;
    server_name video.dgi.mos.ru;
    ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# API (все backend-сервисы)
server {
    listen 443 ssl http2;
    server_name api.dgi.mos.ru;
    ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;

    client_max_body_size 2G;

    location /api/auth/    { proxy_pass http://127.0.0.1:8000/; }
    location /api/video/   { proxy_pass http://127.0.0.1:8001/; }
    location /api/streaming/ { proxy_pass http://127.0.0.1:8002/; }
    location /api/notifications/ { proxy_pass http://127.0.0.1:8003/; }
    location /api/search/  { proxy_pass http://127.0.0.1:8004/; }
    location /api/messenger/ { proxy_pass http://127.0.0.1:8005/; }
    location /api/dashboard/ { proxy_pass http://127.0.0.1:3003/api/; }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # HLS стриминг
    location /hls/ {
        proxy_pass http://127.0.0.1:8888/;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dgi-portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## ЭТАП 7 — Деплой контейнеров

```bash
cd /opt/dgi-portal/infrastructure/docker

# Первый запуск — собрать и поднять все
docker compose up -d --build

# Проверить статус
docker compose ps

# Ждать пока все healthy (30-60 сек)
watch docker compose ps

# Применить миграции dashboard-service
docker compose exec dashboard-service python manage.py migrate

# Создать начальные данные
docker compose exec dashboard-service python add_statuses.py
docker compose exec dashboard-service python reset_and_seed_data.py
```

---

## ЭТАП 8 — Инициализация базы данных

```bash
# Проверить что БД поднялась
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"

# Если нужно — накатить schema для auth-service (автоматически при старте)
docker compose logs auth-service | grep -i "migration\|error"
```

---

## ЭТАП 9 — Проверка работоспособности

```bash
# Health checks
curl https://api.dgi.mos.ru/api/auth/health
curl https://api.dgi.mos.ru/api/video/health
curl https://api.dgi.mos.ru/api/streaming/health
curl https://api.dgi.mos.ru/api/notifications/health
curl https://api.dgi.mos.ru/api/search/health
curl https://api.dgi.mos.ru/api/dashboard/api/report-statuses/

# Проверка порталa
curl https://portal.dgi.mos.ru
curl https://video.dgi.mos.ru
```

---

## ЭТАП 10 — Мониторинг

```bash
# Grafana доступна внутри на порту 3001
# Для доступа снаружи — добавить в nginx:
server {
    listen 443 ssl http2;
    server_name grafana.dgi.mos.ru;
    ...
    location / { proxy_pass http://127.0.0.1:3001; }
}

# Логи сервисов
docker compose logs -f auth-service
docker compose logs -f dashboard-service
docker compose logs -f video-service
```

---

## ЭТАП 11 — Бэкапы

```bash
# Создать скрипт автобэкапа /opt/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > /backups/db_$DATE.sql
gzip /backups/db_$DATE.sql
# Удалять бэкапы старше 30 дней
find /backups -name "*.gz" -mtime +30 -delete

# Cron — каждый день в 3:00
crontab -e
# 0 3 * * * /opt/backup.sh
```

---

## Порядок исправлений ПЕРЕД деплоем (критично)

### Исправление 1: dashboard settings.py → параметризация SECRET_KEY и DEBUG
**Файл:** `services/dashboard-service/backend/config/settings.py`
- `SECRET_KEY` из env
- `DEBUG = False`
- `ALLOWED_HOSTS` из env

### Исправление 2: dashboard Dockerfile.frontend → prod сборка через nginx
**Файл:** `services/dashboard-service/Dockerfile.frontend`
- Multi-stage build: npm run build + nginx

### Исправление 3: Закрыть порты БД
**Файл:** `infrastructure/docker/docker-compose.yml`
- Убрать `ports:` у db, redis, rabbitmq, elasticsearch

### Исправление 4: nginx.prod.conf messenger upstream
**Файл:** `infrastructure/docker/nginx.prod.conf`
- `messenger-service:8005` вместо `3001`

### Исправление 5: video-service — убрать dev volume mount
**Файл:** `infrastructure/docker/docker-compose.yml`
- Убрать `- ../../services/video-service/src:/app/src:ro`

### Исправление 6: CORS для prod в minio-init и во всех сервисах
**Файл:** `infrastructure/docker/docker-compose.yml`
- Добавить prod домены в CORS_ORIGINS и minio-init

---

## Итоговая архитектура на сервере

```
Интернет
    ↓ 80/443
Nginx (хостовой)
    ├── portal.dgi.mos.ru → 127.0.0.1:3002 (portal Next.js)
    ├── video.dgi.mos.ru  → 127.0.0.1:3000 (frontend Next.js)
    └── api.dgi.mos.ru    → 127.0.0.1:800X (микросервисы)
                            ├── /api/auth/       → auth-service:8000
                            ├── /api/video/      → video-service:8001
                            ├── /api/streaming/  → streaming-service:8002
                            ├── /api/notifications/ → notification-service:8003
                            ├── /api/search/     → search-service:8004
                            ├── /api/messenger/  → messenger-service:8005
                            └── /api/dashboard/  → dashboard-service:3003
    ↓ 1935 (RTMP)
MediaMTX → HLS → /hls/ через nginx
```
