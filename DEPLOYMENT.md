# Руководство по развертыванию системы видеохостинга

## Предварительные требования

### 1. Сервер и домен
- **Сервер**: Ubuntu Server 22.04 LTS, минимум 8 ядер CPU, 64GB RAM, 2x960GB NVMe SSD
- **Домен**: video.dgi.ru (зарегистрирован через REG.RU)
- **Хостинг**: Рекомендуется Selectel (дата-центр в РФ)

### 2. Системные зависимости
```bash
# На сервере
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin nginx ffmpeg postgresql-client redis-tools
```

### 3. Настройка сервера
```bash
# Создание пользователя deploy
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh

# Настройка SSH
sudo sed -i 's/#Port 22/Port 22222/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Настройка firewall
sudo ufw allow 22222/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 1935/tcp  # RTMP
sudo ufw --force enable
```

## Развертывание

### 1. Клонирование репозитория
```bash
cd /home/deploy
git clone https://github.com/your-repo/video-hosting.git
cd video-hosting
```

### 2. Настройка переменных окружения
```bash
cp infrastructure/docker/.env.example infrastructure/docker/.env
nano infrastructure/docker/.env
```

Содержимое `.env`:
```env
# Database
POSTGRES_PASSWORD=your-secure-db-password
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/video_hosting

# JWT
SECRET_KEY=your-256-bit-secret-key-here
INTERNAL_AUTH_TOKEN=internal-communication-token

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-minio-secret-key

# LDAP (для интеграции с AD)
LDAP_SERVER=ldap://your-ad-server
LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
LDAP_BIND_USER=your-bind-user
LDAP_BIND_PASSWORD=your-bind-password

# Email (для уведомлений)
SMTP_SERVER=smtp.dgi.mos.ru
SMTP_PORT=587
SMTP_USERNAME=notifications@video.dgi.ru
SMTP_PASSWORD=your-smtp-password

# Elasticsearch
ELASTICSEARCH_PASSWORD=your-elasticsearch-password
```

### 3. Инициализация базы данных
```bash
cd infrastructure/docker
docker-compose up -d db
sleep 10
docker-compose exec db psql -U user -d video_hosting -f /docker-entrypoint-initdb.d/01-schema.sql
```

### 4. Запуск системы
```bash
docker-compose up -d --build
```

### 5. Проверка развертывания
```bash
# Проверка контейнеров
docker-compose ps

# Проверка API
curl http://localhost/api/auth/health
curl http://localhost/api/video/health
curl http://localhost/api/streaming/health

# Проверка MinIO
curl http://localhost:9001
```

## Настройка домена и SSL

### 1. DNS настройки
В панели REG.RU настройте:
```
Тип: A, Имя: @, Значение: ваш_IP_адрес
Тип: A, Имя: www, Значение: ваш_IP_адрес
Тип: MX, Имя: @, Значение: mail.dgi.mos.ru
```

### 2. Делегирование на Cloudflare
1. В REG.RU измените NS-записи на серверы Cloudflare
2. В панели Cloudflare добавьте домен video.dgi.ru
3. Настройте DNS-записи аналогично шагу 1
4. Включите защиту от DDoS

### 3. SSL сертификаты
```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d video.dgi.ru -d www.video.dgi.ru

# Настройка автопродления
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Мониторинг и обслуживание

### 1. Доступ к сервисам
- **Grafana**: http://your-domain:3000 (admin/admin)
- **Prometheus**: http://your-domain:9090
- **MinIO Console**: http://your-domain:9001 (minioadmin/minioadmin)
- **RabbitMQ**: http://your-domain:15672 (guest/guest)

### 2. Логи
```bash
# Просмотр логов сервисов
docker-compose logs -f auth-service
docker-compose logs -f video-service

# Системные логи
sudo journalctl -u docker -f
```

### 3. Резервное копирование
```bash
# Создание скрипта backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U user video_hosting > backup_$DATE.sql
docker run --rm -v video-hosting_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_$DATE.tar.gz -C /data .
```

### 4. Масштабирование
```bash
# Добавление реплик сервисов
docker-compose up -d --scale video-service=3
docker-compose up -d --scale auth-service=2

# Настройка балансировки в Nginx
```

## Безопасность

### 1. Обновления
```bash
# Регулярные обновления
sudo apt update && sudo apt upgrade -y
docker-compose pull && docker-compose up -d
```

### 2. Мониторинг безопасности
- Настройте алерты в Grafana для подозрительной активности
- Регулярно проверяйте логи аудита
- Мониторьте использование дискового пространства

### 3. Резервное копирование
- Автоматическое резервное копирование базы данных
- Резервное копирование MinIO данных
- Тестирование восстановления из резервных копий

## Производительность

### 1. Оптимизация
- Настройте кэширование в Nginx
- Оптимизируйте параметры PostgreSQL
- Настройте лимиты соединений

### 2. Мониторинг производительности
- Отслеживайте CPU, память, диск I/O
- Мониторьте время ответа API
- Настройте алерты при превышении порогов

## Troubleshooting

### Распространенные проблемы

1. **Контейнеры не запускаются**
   ```bash
   docker-compose logs
   docker system df  # Проверить место на диске
   ```

2. **База данных недоступна**
   ```bash
   docker-compose exec db pg_isready -U user -d video_hosting
   ```

3. **MinIO недоступен**
   ```bash
   docker-compose logs minio
   curl http://localhost:9000/minio/health/live
   ```

4. **Транскодирование зависает**
   ```bash
   docker-compose logs celery-worker
   docker-compose exec celery-worker ps aux
   ```

### Контакты поддержки
- Техническая поддержка: support@video.dgi.ru
- Документация: https://docs.video.dgi.ru
- Репозиторий: https://github.com/dgi/video-hosting
