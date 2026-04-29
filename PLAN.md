# ПЛАН ДЕЙСТВИЙ ПО ЗАПУСКУ МИКРОСЕРВИСНОГО ВИДЕОХОСТИНГА

## Этап 0: Предварительная подготовка

### 0.1 Проверка системных требований

**Ваша система:**
- ОС: Windows 10/11
- Требуется: Docker Desktop для Windows
- Минимум: 8 ГБ ОЗУ (рекомендуется 16 ГБ)
- Свободное место: 20+ ГБ

**Проверка:**
```powershell
# Проверка версии Windows
winver

# Проверка виртуализации (должна быть включена)
systeminfo | findstr /C:"Virtualization"
```

### 0.2 Установка Docker Desktop

1. Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Установите с настройками по умолчанию
3. После установки перезагрузите компьютер
4. Запустите Docker Desktop и дождитесь запуска (зелёный индикатор)

**Проверка установки:**
```powershell
docker --version
docker-compose --version
```

---

## Этап 1: Локальный запуск (Development)

### 1.1 Подготовка проекта

Откройте PowerShell и выполните:

```powershell
# Перейдите в директорию проекта
cd C:\Users\Maks\Desktop\ДИПЛОМ\video.dgi.mos.ru

# Создайте файл окружения
Copy-Item infrastructure\docker\.env.example infrastructure\docker\.env
```

### 1.2 Запуск инфраструктуры

```powershell
# Перейдите в директорию docker
cd infrastructure\docker

# Запустите все сервисы (первый запуск ~5-10 минут)
docker-compose up -d --build
```

**Что происходит:**
- Скачиваются Docker образы (PostgreSQL, Redis, RabbitMQ, MinIO, Elasticsearch)
- Собираются образы микросервисов
- Создаются и запускаются контейнеры
- Инициализируется база данных

### 1.3 Проверка работоспособности

```powershell
# Проверка статуса контейнеров
docker-compose ps

# Все сервисы должны иметь статус "healthy"
```

**Ожидаемый результат:**
```
NAME                    STATUS         PORTS
auth-service            Up (healthy)   0.0.0.0:8000->8000/tcp
video-service           Up (healthy)   0.0.0.0:8001->8001/tcp
streaming-service       Up (healthy)   0.0.0.0:8002->8002/tcp
notification-service    Up (healthy)   0.0.0.0:8003->8003/tcp
search-service          Up (healthy)   0.0.0.0:8004->8004/tcp
db                      Up (healthy)   0.0.0.0:5432->5432/tcp
redis                   Up (healthy)   0.0.0.0:6379->6379/tcp
rabbitmq                Up (healthy)   0.0.0.0:5672->5672/tcp
minio                   Up (healthy)   0.0.0.0:9000->9000/tcp
elasticsearch           Up (healthy)   0.0.0.0:9200->9200/tcp
```

### 1.4 Тестирование API

```powershell
# Проверка health endpoints
Invoke-RestMethod http://localhost/api/auth/health
Invoke-RestMethod http://localhost/api/video/health
Invoke-RestMethod http://localhost/api/streaming/health
Invoke-RestMethod http://localhost/api/notifications/health
Invoke-RestMethod http://localhost/api/search/health
```

**Ожидаемый ответ для каждого:**
```json
{"status": "healthy"}
```

### 1.5 Проверка веб-интерфейсов

Откройте в браузере:

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| RabbitMQ Management | http://localhost:15672 | guest / guest |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |

---

## Этап 2: Тестирование функциональности

### 2.1 Регистрация пользователя

Сначала нужно получить UUID роли из базы данных:

```powershell
# Получение UUID роли "employee"
docker-compose exec db psql -U user -d video_hosting -c "SELECT id FROM roles WHERE name = 'employee';"
```

Скопируйте UUID и выполните:

```powershell
# Регистрация пользователя (замените <ROLE_UUID> на полученный UUID)
$roleUuid = "<ROLE_UUID>"
$body = @{
    username = "testuser"
    email = "test@dgi.mos.ru"
    password = "password123"
    role_id = $roleUuid
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost/api/auth/register" -Method Post -ContentType "application/json" -Body $body
```

### 2.2 Получение токена доступа

```powershell
$body = "username=testuser&password=password123"
$response = Invoke-RestMethod -Uri "http://localhost/api/auth/token" -Method Post -ContentType "application/x-www-form-urlencoded" -Body $body
$token = $response.access_token
Write-Host "Access token: $token"
```

### 2.3 Проверка авторизованного запроса

```powershell
$headers = @{
    Authorization = "Bearer $token"
}

Invoke-RestMethod -Uri "http://localhost/api/auth/users/me" -Headers $headers
```

---

## Этап 3: Развёртывание на сервере (Production)

### 3.1 Требования к серверу

**Минимальная конфигурация:**
- CPU: 8 ядер
- RAM: 64 ГБ
- SSD: 2x960 ГБ NVMe (RAID 1)
- ОС: Ubuntu Server 22.04 LTS
- Домен: video.dgi.ru (или другой)

**Рекомендуемые хостинг-провайдеры:**
- Selectel (https://selectel.ru)
- Cloud.ru
- Rostelecom Cloud

### 3.2 Покупка и настройка домена

1. Зарегистрируйте домен у REG.RU или другого регистратора
2. Настройте DNS записи:
   ```
   Тип: A, Имя: @, Значение: <IP сервера>
   Тип: A, Имя: www, Значение: <IP сервера>
   ```

### 3.3 Подготовка сервера

Подключитесь к серверу по SSH:

```bash
ssh root@<IP сервера>
```

Выполните команды:

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
apt install -y docker.io docker-compose-plugin

# Установка дополнительных зависимостей
apt install -y nginx ffmpeg postgresql-client redis-tools certbot python3-certbot-nginx

# Создание пользователя deploy
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# Настройка SSH (опционально, смена порта)
sed -i 's/#Port 22/Port 22222/' /etc/ssh/sshd_config
systemctl restart sshd

# Настройка firewall
ufw allow 22222/tcp  # или 22, если не меняли порт
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 1935/tcp  # RTMP для стриминга
ufw --force enable
```

### 3.4 Развёртывание приложения

```bash
# Переключитесь на пользователя deploy
su - deploy

# Клонирование репозитория
cd /home/deploy
git clone <URL репозитория> video-hosting
cd video-hosting

# Переход в директорию docker
cd infrastructure/docker

# Копирование и настройка .env
cp .env.example .env
nano .env
```

**Отредактируйте .env:**
```env
# Замените на безопасные значения
SECRET_KEY=<сгенерируйте 256-битный ключ>
INTERNAL_AUTH_TOKEN=<сгенерируйте случайный токен>

# MinIO
MINIO_ACCESS_KEY=<сгенерируйте>
MINIO_SECRET_KEY=<сгенерируйте>

# LDAP (если используется)
LDAP_SERVER=ldap://your-ad-server.dgi.mos.ru
LDAP_BIND_USER=cn=admin,dc=dgi,dc=mos,dc=ru
LDAP_BIND_PASSWORD=<ваш пароль>

# Email для уведомлений
SMTP_USERNAME=notifications@video.dgi.ru
SMTP_PASSWORD=<пароль SMTP>
```

### 3.5 Инициализация базы данных

```bash
# Запуск только контейнера БД
docker-compose up -d db

# Ожидание готовности (10 секунд)
sleep 10

# Инициализация схемы БД
docker-compose exec db psql -U user -d video_hosting -f /docker-entrypoint-initdb.d/01-schema.sql
```

### 3.6 Запуск всех сервисов

```bash
docker-compose up -d --build
```

### 3.7 Настройка SSL (HTTPS)

```bash
# Выйдите из контейнеров
exit

# На хосте (не в Docker)
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d video.dgi.ru -d www.video.dgi.ru

# Настройка автопродления
sudo crontab -e
# Добавьте: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3.8 Настройка Nginx для production

Отредактируйте `infrastructure/docker/nginx.conf`:

1. Раскомментируйте SSL настройки
2. Укажите пути к SSL сертификатам
3. Настройте upstream для production

### 3.9 Проверка production развёртывания

```bash
# Проверка контейнеров
docker-compose ps

# Проверка API
curl https://video.dgi.ru/api/auth/health
curl https://video.dgi.ru/api/video/health

# Проверка логов
docker-compose logs -f
```

---

## Этап 4: Мониторинг и обслуживание

### 4.1 Настройка алертов в Grafana

1. Откройте http://your-domain:3000 (admin/admin)
2. Перейдите в Alerting → Notification channels
3. Добавьте канал (email, Telegram, etc.)
4. Создайте правила алертов:
   - CPU > 80%
   - Memory > 85%
   - Disk > 90%
   - Service down

### 4.2 Резервное копирование

Создайте скрипт `/home/deploy/backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/deploy/backups"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T db pg_dump -U user video_hosting > $BACKUP_DIR/db_$DATE.sql

# Backup MinIO
docker run --rm -v video-hosting_minio_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/minio_$DATE.tar.gz -C /data .

# Хранить последние 7 дней
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Настройте cron:
```bash
crontab -e
# Добавьте: 0 2 * * * /home/deploy/backup.sh
```

### 4.3 Обновление системы

```bash
# Регулярное обновление
cd /home/deploy/video-hosting
git pull
docker-compose pull
docker-compose up -d
```

---

## Этап 5: Интеграция с внешними сервисами

### 5.1 Настройка LDAP/Active Directory

1. Убедитесь, что LDAP сервер доступен с хоста
2. Настройте в `.env`:
   ```env
   LDAP_SERVER=ldap://ad-server.dgi.mos.ru
   LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
   LDAP_BIND_USER=cn=service,dc=dgi,dc=mos,dc=ru
   LDAP_BIND_PASSWORD=<password>
   ```

### 5.2 Настройка email уведомлений

1. Получите SMTP credentials у почтового провайдера
2. Настройте в `.env`:
   ```env
   SMTP_SERVER=smtp.dgi.mos.ru
   SMTP_PORT=587
   SMTP_USERNAME=notifications@video.dgi.ru
   SMTP_PASSWORD=<password>
   SMTP_FROM_EMAIL=notifications@video.dgi.ru
   ```

### 5.3 Интеграция с ЕСИА (Госуслуги)

Для интеграции с ЕСИА требуется:
1. Зарегистрировать приложение в РКЦ ЕСИА
2. Получить client_id и client_secret
3. Настроить в `.env`:
   ```env
   ESIA_CLIENT_ID=<ваш client_id>
   ESIA_CLIENT_SECRET=<ваш client_secret>
   ESIA_REDIRECT_URI=https://video.dgi.ru/api/auth/esia/callback
   ```

---

## Troubleshooting

### Проблема: Контейнеры не запускаются

```powershell
# Проверка логов
docker-compose logs

# Проверка места на диске
docker system df

# Очистка
docker system prune -a

# Пересоздание
docker-compose down
docker-compose up -d --build
```

### Проблема: База данных недоступна

```powershell
# Проверка статуса
docker-compose exec db pg_isready -U user -d video_hosting

# Перезапуск
docker-compose restart db
```

### Проблема: Ошибки транскодирования

```powershell
# Проверка логов
docker-compose logs video-service
docker-compose logs celery-worker

# Проверка FFmpeg
docker-compose exec video-service ffmpeg -version
```

### Проблема: MinIO недоступен

```powershell
# Проверка health
Invoke-RestMethod http://localhost:9000/minio/health/live

# Проверка логов
docker-compose logs minio
```

---

## Контакты поддержки

- Техническая поддержка: support@video.dgi.ru
- Документация: https://docs.video.dgi.ru
- Репозиторий: https://github.com/dgi/video-hosting
