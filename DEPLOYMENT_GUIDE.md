# Полное руководство по деплою видеохостинга на сервер с доменом

## Таблица содержания

1. [Предварительные требования](#предварительные-требования)
2. [Покупка и настройка домена](#покупка-и-настройка-домена)
3. [Подготовка сервера](#подготовка-сервера)
4. [Настройка DNS](#настройка-dns)
5. [Установка Docker и Docker Compose](#установка-docker-и-docker-compose)
6. [Настройка SSL сертификатов](#настройка-ssl-сертификатов)
7. [Развертывание приложения](#развертывание-приложения)
8. [Настройка мониторинга](#настройка-мониторинга)
9. [Настройка резервного копирования](#настройка-резервного-копирования)
10. [Безопасность и харденинг](#безопасность-и-харденинг)
11. [Обновление и обслуживание](#обновление-и-обслуживание)
12. [Troubleshooting](#troubleshooting)

---

## Предварительные требования

### Требования к серверу

**Минимальная конфигурация:**
- CPU: 8 ядер (Intel Xeon E-2388G или аналогичный)
- RAM: 64 ГБ
- SSD: 2x960 ГБ NVMe (RAID 1)
- Сеть: 1 Гбит/с
- ОС: Ubuntu Server 22.04 LTS

**Рекомендуемые провайдеры:**
- Selectel (https://selectel.ru) - дата-центры в РФ
- Cloud.ru
- Rostelecom Cloud

### Требования к домену

- Зарегистрированный домен (например, video.dgi.ru)
- Доступ к панели управления DNS

### Требования к локальной машине

- Git
- SSH клиент
- Docker Desktop (для локального тестирования)

---

## Покупка и настройка домена

### Шаг 1: Регистрация домена

1. Перейдите на REG.RU (https://reg.ru) или другой регистратор
2. Проверьте доступность домена
3. Зарегистрируйте домен на 1 год или более
4. Укажите контактные данные администратора

### Шаг 2: Настройка DNS в REG.RU

После регистрации:

1. Войдите в личный кабинет REG.RU
2. Перейдите в раздел "Домены" → "Управление DNS"
3. Добавьте следующие записи:

```
Тип: A
Имя: @
Значение: <IP-адрес вашего сервера>
TTL: 300

Тип: A
Имя: www
Значение: <IP-адрес вашего сервера>
TTL: 300

Тип: CNAME
Имя: api
Значение: @
TTL: 300

Тип: CNAME
Имя: stream
Значение: @
TTL: 300

Тип: MX
Имя: @
Значение: <ваш MX сервер>
Приоритет: 10
TTL: 300
```

### Шаг 3: Делегирование на Cloudflare (опционально, рекомендуется)

Для защиты от DDoS и CDN:

1. Создайте аккаунт на Cloudflare (https://cloudflare.com)
2. Добавьте ваш домен в Cloudflare
3. Cloudflare предоставит NS записи:
   - `anna.ns.cloudflare.com`
   - `bob.ns.cloudflare.com` (пример)
4. В REG.RU измените NS записи на предоставленные Cloudflare
5. Подождите 24-48 часов для распространения DNS

### Шаг 4: Проверка DNS

```bash
# Проверка A записи
dig video.dgi.ru +short

# Проверка распространения DNS
dig video.dgi.ru NS
```

---

## Подготовка сервера

### Шаг 1: Подключение к серверу

```bash
ssh root@<IP-адрес-сервера>
```

### Шаг 2: Обновление системы

```bash
# Обновление пакетов
apt update && apt upgrade -y

# Установка базовых утилит
apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    ncdu \
    iotop \
    net-tools \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

### Шаг 3: Настройка часового пояса

```bash
# Установка часового пояса Москва
timedatectl set-timezone Europe/Moscow

# Проверка
timedatectl
```

### Шаг 4: Создание пользователя deploy

```bash
# Создание пользователя
useradd -m -s /bin/bash deploy

# Добавление в sudo группу
usermod -aG sudo deploy

# Установка пароля
passwd deploy

# Переключение на пользователя deploy
su - deploy
```

### Шаг 5: Настройка SSH ключей

**На локальной машине:**

```bash
# Генерация SSH ключа (если нет)
ssh-keygen -t ed25519 -C "deploy@video.dgi.ru"

# Копирование ключа на сервер
ssh-copy-id deploy@<IP-адрес-сервера>
```

**На сервере:**

```bash
# Отключение парольной аутентификации
sudo vim /etc/ssh/sshd_config

# Измените следующие параметры:
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
Port 22222  # Смена стандартного порта

# Перезапуск SSH
sudo systemctl restart sshd
```

### Шаг 6: Настройка Firewall (UFW)

```bash
# Разрешение SSH на новом порту
sudo ufw allow 22222/tcp

# Разрешение HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Разрешение RTMP для стриминга
sudo ufw allow 1935/tcp

# Включение firewall
sudo ufw --force enable

# Проверка статуса
sudo ufw status
```

### Шаг 7: Настройка RAID 1 (если два диска)

```bash
# Установка mdadm
sudo apt install -y mdadm

# Создание RAID 1 массива (ВНИМАНИЕ: это уничтожит данные на дисках!)
sudo mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/nvme0n1 /dev/nvme1n1

# Создание файловой системы
sudo mkfs.ext4 /dev/md0

# Монтирование
sudo mkdir /data
sudo mount /dev/md0 /data

# Добавление в /etc/fstab
echo '/dev/md0 /data ext4 defaults,noatime 0 0' | sudo tee -a /etc/fstab

# Сохранение конфигурации RAID
sudo mdadm --detail --scan | sudo tee -a /etc/mdadm/mdadm.conf

# Обновление initramfs
sudo update-initramfs -u
```

---

## Настройка DNS

### Шаг 1: Проверка резолвинга

```bash
# Проверка, что домен указывает на сервер
ping video.dgi.ru
nslookup video.dgi.ru
```

### Шаг 2: Настройка /etc/hosts

```bash
sudo vim /etc/hosts

# Добавьте:
127.0.0.1 video.dgi.ru localhost
<IP-адрес> video.dgi.ru
```

---

## Установка Docker и Docker Compose

### Шаг 1: Установка Docker

```bash
# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновление и установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Добавление пользователя в docker группу
sudo usermod -aG docker deploy

# Перезапуск сессии для применения изменений
exit
# Снова подключитесь
ssh -p 22222 deploy@<IP-адрес>
```

### Шаг 2: Проверка установки

```bash
docker --version
docker compose version
```

### Шаг 3: Настройка Docker daemon

```bash
sudo mkdir -p /etc/docker
sudo vim /etc/docker/daemon.json

# Добавьте:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}

# Перезапуск Docker
sudo systemctl restart docker
sudo systemctl enable docker
```

---

## Настройка SSL сертификатов

### Шаг 1: Установка Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Шаг 2: Получение SSL сертификата

```bash
# Получение сертификата (временно запустим nginx для проверки)
sudo certbot certonly --standalone -d video.dgi.ru -d www.video.dgi.ru

# Следуйте инструкциям:
# - Введите email
# - Согласитесь с условиями
# - Выберите "No" для рассылки
```

### Шаг 3: Проверка сертификата

```bash
sudo certbot certificates
```

Сертификаты будут сохранены в:
- `/etc/letsencrypt/live/video.dgi.ru/fullchain.pem`
- `/etc/letsencrypt/live/video.dgi.ru/privkey.pem`

### Шаг 4: Настройка автопродления

```bash
# Проверка автопродления
sudo certbot renew --dry-run

# Добавление в cron
sudo crontab -e

# Добавьте строку:
0 12 * * * /usr/bin/certbot renew --quiet --post-hook "docker-compose -f /home/deploy/video-hosting/infrastructure/docker/docker-compose.yml restart nginx"
```

---

## Развертывание приложения

### Шаг 1: Клонирование репозитория

```bash
# Клонирование репозитория
cd /home/deploy
git clone <URL-вашего-репозитория> video-hosting
cd video-hosting
```

### Шаг 2: Настройка переменных окружения

```bash
cd infrastructure/docker
cp .env.example .env
vim .env
```

**Редактируйте .env:**

```env
# Безопасность
SECRET_KEY=<сгенерируйте-256-битный-ключ>
INTERNAL_AUTH_TOKEN=<сгенерируйте-случайный-токен>

# База данных
POSTGRES_DB=video_hosting
POSTGRES_USER=video_user
POSTGRES_PASSWORD=<сильный-пароль>

# MinIO
MINIO_ACCESS_KEY=<сгенерируйте>
MINIO_SECRET_KEY=<сильный-пароль>

# Redis
REDIS_PASSWORD=<сильный-пароль>

# RabbitMQ
RABBITMQ_DEFAULT_USER=video_rabbit
RABBITMQ_DEFAULT_PASS=<сильный-пароль>

# LDAP (если используется)
LDAP_SERVER=ldap://your-ad-server.dgi.mos.ru
LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
LDAP_BIND_USER=cn=service,dc=dgi,dc=mos,dc=ru
LDAP_BIND_PASSWORD=<пароль>

# Email
SMTP_SERVER=smtp.dgi.mos.ru
SMTP_PORT=587
SMTP_USERNAME=notifications@video.dgi.ru
SMTP_PASSWORD=<пароль-SMTP>
SMTP_FROM_EMAIL=notifications@video.dgi.ru

# Elasticsearch
ELASTICSEARCH_PASSWORD=<сильный-пароль>

# Домен
DOMAIN=video.dgi.ru
```

**Генерация секретных ключей:**

```bash
# Генерация SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Генерация INTERNAL_AUTH_TOKEN
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

### Шаг 3: Настройка Nginx конфигурации

```bash
vim nginx.conf
```

**Обновите nginx.conf для production:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream auth_service {
        server auth-service:8000;
        keepalive 32;
    }

    upstream video_service {
        server video-service:8001;
        keepalive 32;
    }

    upstream streaming_service {
        server streaming-service:8002;
        keepalive 32;
    }

    upstream notification_service {
        server notification-service:8003;
        keepalive 32;
    }

    upstream search_service {
        server search-service:8004;
        keepalive 32;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name video.dgi.ru www.video.dgi.ru;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name video.dgi.ru www.video.dgi.ru;

        # SSL certificates
        ssl_certificate /etc/letsencrypt/live/video.dgi.ru/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/video.dgi.ru/privkey.pem;

        # SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API routes
        location /api/auth/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://auth_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/video/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://video_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Large file upload support
            client_max_body_size 10G;
            proxy_read_timeout 600s;
        }

        location /api/streaming/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://streaming_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/notifications/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://notification_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/search/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://search_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support
        location /ws/ {
            proxy_pass http://websocket-service:8005;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # HLS streaming
        location /hls/ {
            proxy_pass http://minio:9000;
            proxy_set_header Host $host;
            
            # CORS
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Range' always;
            
            # Cache
            expires 7d;
            add_header Cache-Control "public, immutable";
        }

        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # RTMP server
    rtmp {
        server {
            listen 1935;
            chunk_size 4096;

            application live {
                live on;
                record off;
                
                # HLS
                hls on;
                hls_path /tmp/hls;
                hls_fragment 2s;
                hls_playlist_length 24h;
                
                # DVR
                hls_continuous on;
                hls_nested on;
                
                # Authentication
                on_publish http://auth-service:8000/api/streaming/validate;
            }
        }
    }
}
```

### Шаг 4: Обновление docker-compose.yml

```bash
vim docker-compose.yml
```

**Добавьте монтирование SSL сертификатов и порты:**

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
    - "1935:1935"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - nginx_cache:/var/cache/nginx
    - minio_cache:/tmp/minio_cache
    - hls_temp:/tmp/hls
  depends_on:
    - auth-service
    - video-service
    - streaming-service
    - notification-service
    - search-service
    - minio
  networks:
    - video_network
  restart: unless-stopped

# Добавьте volume для HLS
volumes:
  # ... существующие volumes ...
  hls_temp:
```

### Шаг 5: Инициализация базы данных

```bash
# Запуск только PostgreSQL
docker compose up -d db

# Ожидание готовности (10 секунд)
sleep 10

# Инициализация схемы
docker compose exec -T db psql -U video_user -d video_hosting < ../../database/schema.sql

# Проверка
docker compose exec db psql -U video_user -d video_hosting -c "\dt"
```

### Шаг 6: Запуск всех сервисов

```bash
# Сборка и запуск
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### Шаг 7: Проверка работоспособности

```bash
# Проверка health endpoints
curl https://video.dgi.ru/api/auth/health
curl https://video.dgi.ru/api/video/health
curl https://video.dgi.ru/api/streaming/health
curl https://video.dgi.ru/api/notifications/health
curl https://video.dgi.ru/api/search/health
```

### Шаг 8: Настройка фронтенда

Если фронтенд отдельный:

```bash
# Клонирование фронтенда
cd /home/deploy
git clone <frontend-repo> video-hosting-frontend
cd video-hosting-frontend

# Установка зависимостей
npm install

# Сборка для production
npm run build

# Настройка Next.js для production
vim .env.production

NEXT_PUBLIC_API_URL=https://video.dgi.ru
NEXT_PUBLIC_WS_URL=wss://video.dgi.ru

# Запуск с PM2
npm install -g pm2
pm2 start npm --name "video-frontend" -- start
pm2 save
pm2 startup
```

---

## Настройка мониторинга

### Шаг 1: Настройка Prometheus

```bash
vim monitoring/prometheus.yml
```

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:8000']
    metrics_path: '/metrics'

  - job_name: 'video-service'
    static_configs:
      - targets: ['video-service:8001']
    metrics_path: '/metrics'

  - job_name: 'streaming-service'
    static_configs:
      - targets: ['streaming-service:8002']
    metrics_path: '/metrics'

  - job_name: 'notification-service'
    static_configs:
      - targets: ['notification-service:8003']
    metrics_path: '/metrics'

  - job_name: 'search-service'
    static_configs:
      - targets: ['search-service:8004']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']
```

### Шаг 2: Настройка Grafana

```bash
# Доступ к Grafana
https://video.dgi.ru:3000

# Логин: admin / admin
# Смените пароль при первом входе

# Добавьте datasource Prometheus
# URL: http://prometheus:9090

# Импортируйте дашборды из monitoring/grafana/dashboards/
```

### Шаг 3: Настройка алертов

```bash
# Создайте конфигурацию Alertmanager
vim monitoring/alertmanager.yml
```

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage'
        send_resolved: true
```

### Шаг 4: Настройка Telegram бота для алертов

1. Создайте бота через @BotFather в Telegram
2. Получите токен
3. Получите ваш chat ID (через @userinfobot)
4. Настройте webhook в Alertmanager

---

## Настройка резервного копирования

### Шаг 1: Создание скрипта бэкапа

```bash
sudo vim /home/deploy/backup.sh
```

```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/deploy/backups"
RETENTION_DAYS=7

# Создание директории
mkdir -p $BACKUP_DIR

echo "Starting backup at $DATE"

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T db pg_dump -U video_user video_hosting | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup MinIO
echo "Backing up MinIO..."
docker run --rm \
  -v video-hosting_minio_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/minio_$DATE.tar.gz -C /data .

# Backup Elasticsearch
echo "Backing up Elasticsearch..."
docker run --rm \
  -v video-hosting_elasticsearch_data:/usr/share/elasticsearch/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/elasticsearch_$DATE.tar.gz -C /usr/share/elasticsearch/data .

# Удаление старых бэкапов
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed at $(date)"
```

### Шаг 2: Сделайте скрипт исполняемым

```bash
chmod +x /home/deploy/backup.sh
```

### Шаг 3: Настройка cron

```bash
crontab -e

# Добавьте:
0 2 * * * /home/deploy/backup.sh >> /home/deploy/backup.log 2>&1
```

### Шаг 4: Настройка удалённого бэкапа (опционально)

```bash
# Установка rclone для бэкапа в облако
curl https://rclone.org/install.sh | sudo bash

# Настройка rclone
rclone config

# Добавьте в backup.sh:
rclone copy $BACKUP_DIR remote:video-hosting-backups
```

---

## Безопасность и харденинг

### Шаг 1: Настройка fail2ban

```bash
sudo apt install -y fail2ban

sudo vim /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22222
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
```

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Шаг 2: Настройка автоматических обновлений безопасности

```bash
sudo apt install -y unattended-upgrades

sudo vim /etc/apt/apt.conf.d/50unattended-upgrades
```

```conf
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
```

```bash
sudo systemctl enable unattended-upgrades
```

### Шаг 3: Ограничение доступа к мониторингу

```bash
# Добавьте basic auth для Grafana
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Обновите nginx.conf для Grafana
location /grafana/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://grafana:3000;
}
```

### Шаг 4: Настройка логирования

```bash
# Централизованное логирование
sudo apt install -y rsyslog

# Настройка ротации логов
sudo vim /etc/logrotate.d/docker-containers
```

```
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker compose restart > /dev/null
    endscript
}
```

---

## Обновление и обслуживание

### Шаг 1: Процедура обновления

```bash
cd /home/deploy/video-hosting/infrastructure/docker

# 1. Pull изменений из git
git pull

# 2. Backup текущей версии
docker compose exec db pg_dump -U video_user video_hosting > backup_before_update_$(date +%Y%m%d).sql

# 3. Pull новых Docker образов
docker compose pull

# 4. Пересборка при необходимости
docker compose build

# 5. Перезапуск с минимальным downtime
docker compose up -d --no-deps --build auth-service
docker compose up -d --no-deps --build video-service
docker compose up -d --no-deps --build streaming-service
docker compose up -d --no-deps --build notification-service
docker compose up -d --no-deps --build search-service

# 6. Перезапуск nginx
docker compose restart nginx

# 7. Проверка health
docker compose ps
curl https://video.dgi.ru/health
```

### Шаг 2: Процедура отката

```bash
# Если что-то пошло не так
cd /home/deploy/video-hosting/infrastructure/docker

# Откат к предыдущему коммиту
git log
git checkout <previous-commit-hash>

# Перезапуск
docker compose down
docker compose up -d --build

# Восстановление БД если нужно
docker compose exec -T db psql -U video_user video_hosting < backup_before_update_YYYYMMDD.sql
```

### Шаг 3: Мониторинг дискового пространства

```bash
# Регулярная проверка
df -h

# Очистка Docker
docker system prune -a --volumes -f

# Очистка старых логов
sudo journalctl --vacuum-time=7d
```

---

## Troubleshooting

### Проблема: Контейнеры не запускаются

```bash
# Проверка логов
docker compose logs

# Проверка статуса
docker compose ps

# Перезапуск
docker compose restart <service-name>

# Полный перезапуск
docker compose down
docker compose up -d --build
```

### Проблема: База данных недоступна

```bash
# Проверка подключения
docker compose exec db pg_isready -U video_user -d video_hosting

# Проверка логов
docker compose logs db

# Перезапуск БД
docker compose restart db
```

### Проблема: Ошибки SSL

```bash
# Проверка сертификата
sudo certbot certificates

# Перевыпуск сертификата
sudo certbot renew --force-renewal

# Перезапуск nginx
docker compose restart nginx
```

### Проблема: Высокая нагрузка на CPU

```bash
# Проверка процессов
htop

# Проверка Docker контейнеров
docker stats

# Масштабирование воркеров
docker compose up -d --scale celery-worker=3
```

### Проблема: Заполнение диска

```bash
# Проверка места
df -h
du -sh /var/lib/docker

# Очистка Docker
docker system prune -a --volumes -f

# Очистка старых бэкапов
find /home/deploy/backups -mtime +30 -delete
```

### Проблема: Медленная загрузка видео

```bash
# Проверка скорости сети
iperf3 -c <server-ip>

# Проверка кэша Nginx
docker compose exec nginx cat /var/cache/nginx

# Очистка кэша
docker compose exec nginx rm -rf /var/cache/nginx/*
docker compose restart nginx
```

---

## Проверочный чек-лист после деплоя

- [ ] Домен резолвится в IP сервера
- [ ] SSL сертификат установлен и валиден
- [ ] Все контейнеры в статусе "healthy"
- [ ] Health endpoints возвращают 200
- [ ] База данных инициализирована
- [ ] MinIO доступен и бакет создан
- [ ] Elasticsearch работает
- [ ] RabbitMQ принимает сообщения
- [ ] Redis кэширует данные
- [ ] Nginx проксирует запросы
- [ ] Firewall настроен правильно
- [ ] SSH работает на порту 22222
- [ ] Резервное копирование настроено
- [ ] Мониторинг (Grafana) доступен
- [ ] Алерты настроены
- [ ] Логи записываются
- [ ] Автообновление SSL настроено

---

## Контакты и поддержка

- Техническая поддержка: support@video.dgi.ru
- Документация: https://docs.video.dgi.ru
- Репозиторий: https://github.com/dgi/video-hosting
- Мониторинг: https://video.dgi.ru:3000
