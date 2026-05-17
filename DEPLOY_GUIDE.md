# Руководство по деплою микросервисной системы видеохостинга ДГИ

## Содержание
1. [Подготовка сервера](#1-подготовка-сервера)
2. [Настройка DNS и SSL](#2-настройка-dns-и-ssl)
3. [Установка Docker и Docker Compose](#3-установка-docker-и-docker-compose)
4. [Подготовка проекта к деплою](#4-подготовка-проекта-к-деплою)
5. [Настройка переменных окружения](#5-настройка-переменных-окружения)
6. [Настройка Nginx для production](#6-настройка-nginx-для-production)
7. [Запуск системы](#7-запуск-системы)
8. [Настройка бэкапов](#8-настройка-бэкапов)
9. [Мониторинг и логирование](#9-мониторинг-и-логирование)
10. [Безопасность](#10-безопасность)

---

## 1. Подготовка сервера

### 1.1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget vim htop net-tools ufw fail2ban
```

### 1.2. Настройка firewall (UFW)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 1.3. Настройка swap (если RAM < 32GB)
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 1.4. Оптимизация параметров ядра для Elasticsearch
```bash
sudo vim /etc/sysctl.conf
```
Добавить:
```
vm.max_map_count=262144
fs.file-max=65536
```
Применить:
```bash
sudo sysctl -p
```

---

## 2. Настройка DNS и SSL

### 2.1. Настройка DNS записей
В панели управления доменом добавьте записи:

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | portal.dgi.mos.ru | IP_ВАШЕГО_СЕРВЕРА | 3600 |
| A | video.dgi.mos.ru | IP_ВАШЕГО_СЕРВЕРА | 3600 |
| A | api.dgi.mos.ru | IP_ВАШЕГО_СЕРВЕРА | 3600 |

### 2.2. Установка Certbot для Let's Encrypt
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2.3. Получение SSL сертификатов
```bash
sudo certbot certonly --nginx -d portal.dgi.mos.ru -d video.dgi.mos.ru -d api.dgi.mos.ru
```

Сертификаты будут сохранены в `/etc/letsencrypt/live/portal.dgi.mos.ru/`

### 2.4. Настройка автообновления
```bash
sudo certbot renew --dry-run
```
Certbot автоматически добавит cron-задачу для обновления.

---

## 3. Установка Docker и Docker Compose

### 3.1. Установка Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 3.2. Установка Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 3.3. Настройка Docker daemon для production
```bash
sudo vim /etc/docker/daemon.json
```
Добавить:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
```
Перезапустить:
```bash
sudo systemctl restart docker
```

---

## 4. Подготовка проекта к деплою

### 4.1. Клонирование репозитория
```bash
cd /opt
sudo git clone <ВАШ_РЕПОЗИТОРИЙ> video-dgi
sudo chown -R $USER:$USER video-dgi
cd video-dgi
```

### 4.2. Создание production docker-compose.yml
Создайте файл `docker-compose.prod.yml` на основе существующего, но с изменениями:

```yaml
version: '3.8'

services:
  # PostgreSQL
  db:
    image: postgres:15
    container_name: video_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: video_hosting
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - video_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d video_hosting"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: video_redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - video_network

  # RabbitMQ
  rabbitmq:
    image: rabbitmq:4.1.8-management
    container_name: video_rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - video_network

  # MinIO
  minio:
    image: minio/minio:latest
    container_name: video_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    networks:
      - video_network

  # Elasticsearch
  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: video_elasticsearch
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - video_network

  # Auth Service
  auth-service:
    build: ./services/auth-service
    container_name: auth_service
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      REDIS_URL: redis://redis:6379/0
      LDAP_SERVER: ${LDAP_SERVER}
      LDAP_BASE_DN: ${LDAP_BASE_DN}
      LDAP_BIND_USER: ${LDAP_BIND_USER}
      LDAP_BIND_PASSWORD: ${LDAP_BIND_PASSWORD}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - video_network

  # Video Service
  video-service:
    build: ./services/video-service
    container_name: video_service
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET: videos
      AUTH_SERVICE_URL: http://auth-service:8000
      RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672/
    depends_on:
      db:
        condition: service_healthy
      minio:
        condition: service_started
      rabbitmq:
        condition: service_started
    networks:
      - video_network

  # Celery Worker (Video Transcoding)
  celery-worker:
    build: ./services/video-service
    container_name: celery_worker
    restart: unless-stopped
    command: celery -A src.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET: videos
      RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672/
    depends_on:
      db:
        condition: service_healthy
      minio:
        condition: service_started
      rabbitmq:
        condition: service_started
    networks:
      - video_network

  # Streaming Service
  streaming-service:
    build: ./services/streaming-service
    container_name: streaming_service
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      AUTH_SERVICE_URL: http://auth-service:8000
    depends_on:
      db:
        condition: service_healthy
    networks:
      - video_network

  # Notification Service
  notification-service:
    build: ./services/notification-service
    container_name: notification_service
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      AUTH_SERVICE_URL: http://auth-service:8000
      SMTP_SERVER: ${SMTP_SERVER}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USERNAME: ${SMTP_USERNAME}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      SMTP_FROM_EMAIL: ${SMTP_FROM_EMAIL}
    depends_on:
      db:
        condition: service_healthy
    networks:
      - video_network

  # Search Service
  search-service:
    build: ./services/search-service
    container_name: search_service
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/video_hosting
      SECRET_KEY: ${SECRET_KEY}
      INTERNAL_AUTH_TOKEN: ${INTERNAL_AUTH_TOKEN}
      AUTH_SERVICE_URL: http://auth-service:8000
      VIDEO_SERVICE_URL: http://video-service:8001
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    depends_on:
      db:
        condition: service_healthy
      elasticsearch:
        condition: service_started
    networks:
      - video_network

  # Messenger Service
  messenger-service:
    build: ./services/messenger-service
    container_name: messenger_service
    restart: unless-stopped
    environment:
      AUTH_SERVICE_URL: http://auth-service:8000
    depends_on:
      - auth-service
    networks:
      - video_network

  # Dashboard Service
  dashboard-service:
    build: ./services/dashboard-service
    container_name: dashboard_service
    restart: unless-stopped
    environment:
      AUTH_SERVICE_URL: http://auth-service:8000
    depends_on:
      - auth-service
    networks:
      - video_network

  # Support Service
  support-service:
    build: ./services/support-service
    container_name: support_service
    restart: unless-stopped
    environment:
      AUTH_SERVICE_URL: http://auth-service:8000
    depends_on:
      - auth-service
    networks:
      - video_network

  # Portal Frontend
  portal:
    build: ./portal
    container_name: portal_frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_AUTH_URL: https://api.dgi.mos.ru
      NEXT_PUBLIC_VIDEO_URL: https://video.dgi.mos.ru
    networks:
      - video_network

  # Video Frontend
  frontend:
    build: ./frontend
    container_name: video_frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_AUTH_URL: https://api.dgi.mos.ru
      NEXT_PUBLIC_API_URL: https://api.dgi.mos.ru
    networks:
      - video_network

  # Nginx
  nginx:
    image: nginx:latest
    container_name: video_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "1935:1935"
    volumes:
      - ./infrastructure/docker/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - portal
      - frontend
      - auth-service
      - video-service
    networks:
      - video_network

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    volumes:
      - ./infrastructure/docker/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - video_network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    networks:
      - video_network

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
  elasticsearch_data:
  prometheus_data:
  grafana_data:

networks:
  video_network:
    driver: bridge
```

---

## 5. Настройка переменных окружения

### 5.1. Создание .env для Docker Compose
```bash
cd infrastructure/docker
cp .env.example .env
vim .env
```

### 5.2. Заполнение критичных переменных
```bash
# База данных
POSTGRES_USER=video_user
POSTGRES_PASSWORD=СГЕНЕРИРУЙ_СИЛЬНЫЙ_ПАРОЛЬ_МИНИМУМ_32_СИМВОЛА

# JWT
SECRET_KEY=СГЕНЕРИРУЙ_СИЛЬНЫЙ_ПАРОЛЬ_МИНИМУМ_64_СИМВОЛА
INTERNAL_AUTH_TOKEN=СГЕНЕРИРУЙ_СИЛЬНЫЙ_ПАРОЛЬ_МИНИМУМ_64_СИМВОЛА

# RabbitMQ
RABBITMQ_USER=rabbit_user
RABBITMQ_PASSWORD=СГЕНЕРИРУЙ_СИЛЬНЫЙ_ПАРОЛЬ_МИНИМУМ_32_СИМВОЛА

# MinIO
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=СГЕНЕРИРУЙ_СИЛЬНЫЙ_ПАРОЛЬ_МИНИМУМ_32_СИМВОЛА

# LDAP (если используется)
LDAP_SERVER=ldap://ldap.dgi.mos.ru
LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
LDAP_BIND_USER=CN=service_account,OU=Services,DC=dgi,DC=mos,DC=ru
LDAP_BIND_PASSWORD=ПАРОЛЬ_ОТ_LDAP

# SMTP
SMTP_SERVER=smtp.dgi.mos.ru
SMTP_PORT=587
SMTP_USERNAME=video@dgi.mos.ru
SMTP_PASSWORD=ПАРОЛЬ_ОТ_SMTP
SMTP_FROM_EMAIL=noreply@dgi.mos.ru

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=СГЕНЕРИРУЙ_ПАРОЛЬ
```

### 5.3. Генерация сильных паролей
```bash
# Для генерации случайных паролей
openssl rand -base64 32
```

---

## 6. Настройка Nginx для production

### 6.1. Создание nginx.prod.conf
Создайте файл `infrastructure/docker/nginx.prod.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=1r/s;

    # Upstream servers (только внутренние, не доступны извне)
    upstream portal_upstream {
        server portal:3000;
    }

    upstream video_frontend_upstream {
        server frontend:3000;
    }

    upstream auth_service_upstream {
        server auth-service:8000;
    }

    upstream video_service_upstream {
        server video-service:8001;
    }

    upstream streaming_service_upstream {
        server streaming-service:8002;
    }

    upstream notification_service_upstream {
        server notification-service:8003;
    }

    upstream search_service_upstream {
        server search-service:8004;
    }

    upstream messenger_service_upstream {
        server messenger-service:3001;
    }

    upstream dashboard_service_upstream {
        server dashboard-service:3003;
    }

    upstream support_service_upstream {
        server support-service:3004;
    }

    # HTTP server (redirect to HTTPS)
    server {
        listen 80;
        server_name portal.dgi.mos.ru video.dgi.mos.ru api.dgi.mos.ru;

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS server - Portal (единая точка входа)
    server {
        listen 443 ssl http2;
        server_name portal.dgi.mos.ru;

        ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.dgi.mos.ru https://video.dgi.mos.ru;" always;

        location / {
            proxy_pass http://portal_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }
    }

    # HTTPS server - Video Frontend
    server {
        listen 443 ssl http2;
        server_name video.dgi.mos.ru;

        ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.dgi.mos.ru; media-src 'self' https: blob: data:;" always;

        location / {
            proxy_pass http://video_frontend_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }
    }

    # HTTPS server - API (закрыт для прямого доступа, только через frontend)
    server {
        listen 443 ssl http2;
        server_name api.dgi.mos.ru;

        ssl_certificate /etc/letsencrypt/live/portal.dgi.mos.ru/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/portal.dgi.mos.ru/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Auth Service
        location /api/auth/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://auth_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Video Service
        location /api/video/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://video_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Upload endpoint - stricter rate limit
        location /api/video/videos/upload {
            limit_req zone=upload_limit burst=5 nodelay;
            client_max_body_size 2G;
            proxy_pass http://video_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_request_buffering off;
        }

        # Streaming Service
        location /api/streaming/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://streaming_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Notification Service
        location /api/notifications/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://notification_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Search Service
        location /api/search/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://search_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Messenger Service
        location /api/messenger/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://messenger_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Dashboard Service
        location /api/dashboard/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://dashboard_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Support Service
        location /api/support/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://support_service_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket для уведомлений
        location /ws/notifications {
            proxy_pass http://notification_service_upstream/ws/notifications;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # RTMP server (для live streaming)
    server {
        listen 1935;
        server_name api.dgi.mos.ru;

        application live {
            live on;
            record off;
            
            on_publish http://auth-service:8000/api/streaming/validate;
            
            push rtmp://localhost/hls;
        }
    }
}
```

### 6.2. Важные моменты конфигурации
- **API закрыт для прямого доступа:** Хотя API доступен по домену `api.dgi.mos.ru`, пользователи не должны знать о нём. Frontend должен обращаться к API только через этот домен.
- **CORS:** В production CORS должен быть настроен только на разрешённые домены (`portal.dgi.mos.ru`, `video.dgi.mos.ru`).
- **Rate limiting:** API ограничен 10 запросами в секунду, загрузка — 1 запросом в секунду.
- **Security headers:** CSP настроен строго, разрешены только необходимые источники.

---

## 7. Запуск системы

### 7.1. Сборка и запуск
```bash
cd /opt/video-dgi
docker-compose -f docker-compose.prod.yml --env-file .env build
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

### 7.2. Проверка статуса контейнеров
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 7.3. Просмотр логов
```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f auth-service
docker-compose -f docker-compose.prod.yml logs -f video-service
```

### 7.4. Инициализация базы данных
```bash
# Запуск миграций (если используется Alembic)
docker-compose -f docker-compose.prod.yml exec auth-service alembic upgrade head
docker-compose -f docker-compose.prod.yml exec video-service alembic upgrade head

# Загрузка seed данных
docker-compose -f docker-compose.prod.yml exec db psql -U video_user -d video_hosting -f /docker-entrypoint-initdb.d/seed_data.sql
```

### 7.5. Создание бакета MinIO
```bash
# Войти в MinIO console: https://ВАШ_IP:9001
# Логин: minio_admin, пароль из .env
# Создать бакет "videos" с политикой public read
```

Или через mc CLI:
```bash
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

mc alias set local http://localhost:9000 minio_admin ПАРОЛЬ
mc mb local/videos
mc anonymous set download local/videos
```

### 7.6. Проверка работоспособности
```bash
# Проверка portal
curl -I https://portal.dgi.mos.ru

# Проверка video frontend
curl -I https://video.dgi.mos.ru

# Проверка auth API
curl https://api.dgi.mos.ru/api/auth/health

# Проверка video API
curl https://api.dgi.mos.ru/api/video/health
```

---

## 8. Настройка бэкапов

### 8.1. Бэкап PostgreSQL
Создайте скрипт `/opt/backup-postgres.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker-compose -f /opt/video-dgi/docker-compose.prod.yml exec -T db pg_dump -U video_user video_hosting > $BACKUP_DIR/backup_$DATE.sql

# Удаление бэкапов старше 7 дней
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

Добавьте в cron:
```bash
chmod +x /opt/backup-postgres.sh
crontab -e
# Добавить строку:
0 2 * * * /opt/backup-postgres.sh
```

### 8.2. Бэкап MinIO
Создайте скрипт `/opt/backup-minio.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/minio"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

mc mirror local/videos $BACKUP_DIR/videos_$DATE

# Удаление бэкапов старше 7 дней
find $BACKUP_DIR -type d -name "videos_*" -mtime +7 -exec rm -rf {} \;
```

Добавьте в cron:
```bash
chmod +x /opt/backup-minio.sh
crontab -e
# Добавить строку:
0 3 * * * /opt/backup-minio.sh
```

---

## 9. Мониторинг и логирование

### 9.1. Настройка Prometheus
Создайте `infrastructure/docker/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:8000']
    metrics_path: '/metrics'

  - job_name: 'video-service'
    static_configs:
      - targets: ['video-service:8001']
    metrics_path: '/metrics'

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
```

### 9.2. Доступ к Grafana
- URL: `https://ВАШ_IP:3001` (или настройте через nginx)
- Логин: admin
- Пароль: из `.env`

### 9.3. Логирование
Все логи Docker хранятся в `/var/lib/docker/containers/`. Для централизованного логирования можно использовать ELK Stack или Loki.

---

## 10. Безопасность

### 10.1. Fail2Ban
Установите и настройте Fail2Ban для защиты от brute-force:

```bash
sudo apt install -y fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo vim /etc/fail2ban/jail.local
```

Добавьте:
```ini
[nginx-req-limit]
enabled = true
filter = nginx-req-limit
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 600
bantime = 7200
```

### 10.2. Настройка SSH
```bash
sudo vim /etc/ssh/sshd_config
```
Измените:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

### 10.3. Обновление системы
Настройте автоматические обновления безопасности:
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 11. Обновление системы

### 11.1. Процесс обновления
```bash
cd /opt/video-dgi
git pull origin main
docker-compose -f docker-compose.prod.yml --env-file .env build
docker-compose -f docker-compose.prod.yml --env-file .env up -d
docker-compose -f docker-compose.prod.yml --env-file .env exec db alembic upgrade head
```

### 11.2. Откат при проблемах
```bash
git checkout <previous_commit>
docker-compose -f docker-compose.prod.yml --env-file .env up -d
```

---

## 12. Troubleshooting

### 12.1. Контейнер не запускается
```bash
docker-compose -f docker-compose.prod.yml logs <service_name>
docker inspect <container_name>
```

### 12.2. Проблемы с PostgreSQL
```bash
docker-compose -f docker-compose.prod.yml exec db psql -U video_user -d video_hosting
```

### 12.3. Проблемы с Elasticsearch
```bash
curl -X GET "localhost:9200/_cluster/health?pretty"
```

### 12.4. Проблемы с Nginx
```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 13. Проверка единой точки входа

После деплоя убедитесь:

1. **Пользователь заходит только через портал:** `https://portal.dgi.mos.ru`
2. **API недоступен напрямую для пользователей:** Хотя `https://api.dgi.mos.ru` существует, пользователи не должны знать о нём. Frontend обращается к API через этот домен.
3. **Все сервисы доступны только через портал:** Переходы на video, messenger, dashboard, support происходят через портал с передачей токена.
4. **CORS настроен правильно:** Запросы с `portal.dgi.mos.ru` и `video.dgi.mos.ru` разрешены, остальные — нет.

---

## 14. Дополнительные рекомендации

### 14.1. CDN для видео
Для улучшения стриминга рассмотрите использование CDN (Cloudflare, Akamai) для доставки HLS-плейлистов.

### 14.2. Масштабирование
При росте нагрузки:
- Реплицируйте `celery-worker` для параллельного транскодирования
- Реплицируйте `video-service` для обработки большего количества запросов
- Используйте Kubernetes вместо Docker Compose

### 14.3. Мониторинг производительности
Добавьте APM (Application Performance Monitoring) — Sentry, Datadog или New Relic.

---

## Контакты для поддержки
При возникновении проблем проверьте логи и обратитесь к документации каждого сервиса.
