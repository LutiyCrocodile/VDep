# Быстрый запуск микросервисного видеохостинга

## Требования

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB+ RAM
- 20GB+ свободного места на диске

## Быстрый старт

### 1. Клонирование и настройка

```bash
cd infrastructure/docker
cp .env.example .env
```

### 2. Запуск всех сервисов

```bash
docker compose up -d --build
```

Это запустит:
- PostgreSQL 15 (порт 5432)
- Redis 7 (порт 6379)
- RabbitMQ 4 (порты 5672, 15672)
- MinIO (порты 9000, 9001)
- Elasticsearch 8 (порт 9200)
- Auth Service (порт 8000)
- Video Service (порт 8001)
- Streaming Service (порт 8002, 1935)
- Notification Service (порт 8003)
- Search Service (порт 8004)
- Celery Worker
- Nginx (порты 80, 443)
- Prometheus (порт 9090)
- Grafana (порт 3000)
- Node Exporter (порт 9100)

### 3. Проверка статуса

```bash
docker compose ps
```

Все сервисы должны быть в статусе "healthy".

### 4. Инициализация базы данных

База данных инициализируется автоматически из `schema.sql` при первом запуске PostgreSQL.

### 5. Создание бакета MinIO

MinIO создаст бакет автоматически, но вы можете проверить через консоль:
- http://localhost:9001
- Логин: minioadmin
- Пароль: minioadmin

### 6. Проверка API

```bash
# Health checks
curl http://localhost:8000/health  # Auth Service
curl http://localhost:8001/health  # Video Service
curl http://localhost:8002/health  # Streaming Service
curl http://localhost:8003/health  # Notification Service
curl http://localhost:8004/health  # Search Service
```

### 7. Регистрация первого пользователя

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@dgi.ru",
    "password": "securepassword123",
    "role_id": "admin-role-id"
  }'
```

**Важно:** Сначала получите ID роли администратора из базы данных:
```bash
docker compose exec db psql -U user -d video_hosting -c "SELECT id FROM roles WHERE name='admin';"
```

### 8. Логин и получение токена

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=securepassword123"
```

Сохраните `access_token` для последующих запросов.

### 9. Загрузка тестового видео

```bash
# Инициализация загрузки
curl -X POST http://localhost:8001/api/video/videos/upload/init \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Тестовое видео",
    "description": "Описание тестового видео",
    "filename": "test.mp4",
    "file_size": 10485760
  }'
```

Вы получите `upload_url` и `video_id`. Загрузите файл на этот URL.

### 10. Мониторинг

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Фронтенд

### Установка зависимостей

```bash
cd frontend
npm install
```

### Запуск в режиме разработки

```bash
npm run dev
```

Фронтенд будет доступен на http://localhost:3000

### Сборка для production

```bash
npm run build
npm start
```

## Полезные команды

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f auth-service
docker compose logs -f video-service
```

### Перезапуск сервисов

```bash
# Все сервисы
docker compose restart

# Конкретный сервис
docker compose restart auth-service
```

### Остановка

```bash
docker compose down
```

### Полная очистка (включая volumes)

```bash
docker compose down -v
```

## Структура проекта

```
video.dgi.mos.ru/
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── nginx.conf
│   │   └── .env.example
│   └── database/
│       └── schema.sql
├── services/
│   ├── auth-service/
│   ├── video-service/
│   ├── streaming-service/
│   ├── notification-service/
│   └── search-service/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   └── lib/
│   ├── package.json
│   └── tsconfig.json
└── docs/
    ├── FRONTEND_BACKEND_INTEGRATION.md
    ├── DFD_DIAGRAMS.md
    ├── ARCHITECTURE_DIAGRAMS.md
    └── DEPLOYMENT_GUIDE.md
```

## Следующие шаги

1. Настройте SSL сертификаты для production (см. DEPLOYMENT_GUIDE.md)
2. Настройте LDAP интеграцию для Active Directory
3. Настройте SMTP для email уведомлений
4. Разверните на сервер (см. DEPLOYMENT_GUIDE.md)
5. Настройте домен и DNS

## Troubleshooting

### Сервисы не запускаются

Проверьте логи:
```bash
docker compose logs -f
```

Убедитесь, что порты не заняты:
```bash
netstat -tuln | grep -E ':(80|443|8000|8001|8002|8003|8004|5432|6379|5672|9000|9200)'
```

### Проблемы с PostgreSQL

```bash
docker compose exec db psql -U user -d video_hosting
```

### Проблемы с MinIO

Проверьте, что бакет создан:
```bash
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc ls local/
```

### Проблемы с транскодированием

Проверьте логи Celery worker:
```bash
docker compose logs -f celery-worker
```

Убедитесь, что FFmpeg установлен в контейнере celery-worker.

## Документация

- [Интеграция фронтенда и бекенда](../docs/FRONTEND_BACKEND_INTEGRATION.md)
- [DFD диаграммы](../docs/DFD_DIAGRAMS.md)
- [Архитектурные диаграммы](../docs/ARCHITECTURE_DIAGRAMS.md)
- [Руководство по деплою](../docs/DEPLOYMENT_GUIDE.md)
