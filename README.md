# Микросервисный видеохостинг - Руководство по запуску

## Архитектура системы

Система состоит из следующих микросервисов:

| Сервис | Порт | Описание |
|--------|------|----------|
| auth-service | 8000 | Аутентификация и авторизация (JWT, LDAP) |
| video-service | 8001 | Загрузка и обработка видео (транскодирование в HLS) |
| streaming-service | 8002 | Live-стриминг (RTMP/HLS) |
| notification-service | 8003 | Уведомления (email, WebSocket) |
| search-service | 8004 | Поиск по видео и субтитрам (Elasticsearch) |

### Инфраструктурные компоненты

| Компонент | Порт | Описание |
|-----------|------|----------|
| PostgreSQL | 5432 | Основная база данных |
| Redis | 6379 | Кэш и брокер для Celery |
| RabbitMQ | 5672, 15672 | Очереди сообщений |
| MinIO | 9000, 9001 | Объектное хранилище |
| Elasticsearch | 9200, 9300 | Поисковый движок |
| Nginx | 80, 443 | Reverse proxy |
| Prometheus | 9090 | Мониторинг |
| Grafana | 3000 | Визуализация метрик |

---

## Быстрый старт (локальная разработка)

### Требования

- Docker Desktop (Windows/Mac) или Docker + Docker Compose (Linux)
- Минимум 8 ГБ оперативной памяти
- 20 ГБ свободного места на диске

### Шаг 1: Клонирование и подготовка

```bash
cd C:\Users\Maks\Desktop\ДИПЛОМ\video.dgi.mos.ru
```

### Шаг 2: Создание файла окружения

Скопируйте `.env.example` в `.env` в папке `infrastructure/docker/`:

```bash
cp infrastructure/docker/.env.example infrastructure/docker/.env
```

Отредактируйте `.env` при необходимости (для локальной разработки можно оставить значения по умолчанию).

### Шаг 3: Запуск системы

```bash
cd infrastructure/docker
docker-compose up -d --build
```

Первый запуск может занять 5-10 минут (скачивание образов, сборка контейнеров).

### Шаг 4: Проверка работоспособности

```bash
# Проверка статуса контейнеров
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

Все сервисы должны иметь статус `healthy`.

### Шаг 5: Тестирование API

#### 1. Проверка health endpoints

```bash
curl http://localhost/api/auth/health
curl http://localhost/api/video/health
curl http://localhost/api/streaming/health
curl http://localhost/api/notifications/health
curl http://localhost/api/search/health
```

#### 2. Регистрация пользователя

```bash
curl -X POST http://localhost/api/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"testuser\",\"email\":\"test@dgi.mos.ru\",\"password\":\"password123\",\"role_id\":\"<role-uuid>\"}"
```

UUID роли можно получить из базы данных или использовать один из default:
- admin: выполните запрос к БД для получения UUID
- employee: аналогично

#### 3. Получение токена

```bash
curl -X POST http://localhost/api/auth/token ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "username=testuser&password=password123"
```

Сохраните `access_token` для последующих запросов.

---

## Доступ к сервисам

| Сервис | URL | Credentials |
|--------|-----|-------------|
| API Gateway | http://localhost | - |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| RabbitMQ Management | http://localhost:15672 | guest / guest |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Elasticsearch | http://localhost:9200 | - |

---

## Остановка системы

```bash
cd infrastructure/docker
docker-compose down
```

Для полного удаления данных (включая volumes):

```bash
docker-compose down -v
```

---

## Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Лог конкретного сервиса
docker-compose logs -f video-service
docker-compose logs -f auth-service
docker-compose logs -f celery-worker
```

---

## Масштабирование

```bash
# Увеличение количества воркеров Celery
docker-compose up -d --scale celery-worker=3

# Увеличение количества реплик video-service
docker-compose up -d --scale video-service=2
```

---

## Разработка и внесение изменений

### Структура проекта

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
└── .env.example
```

### Внесение изменений в код

1. Измените код в соответствующем сервисе
2. Пересоберите контейнер:
   ```bash
   docker-compose up -d --build <service-name>
   ```
3. Проверьте логи:
   ```bash
   docker-compose logs -f <service-name>
   ```

---

## Решение проблем

### Контейнеры не запускаются

```bash
# Проверка места на диске
docker system df

# Очистка неиспользуемых ресурсов
docker system prune -a

# Пересоздание контейнеров
docker-compose down
docker-compose up -d --build
```

### База данных недоступна

```bash
# Проверка состояния БД
docker-compose exec db pg_isready -U user -d video_hosting

# Перезапуск БД
docker-compose restart db
```

### MinIO недоступен

```bash
# Проверка логов MinIO
docker-compose logs minio

# Проверка health
curl http://localhost:9000/minio/health/live
```

### Celery worker не обрабатывает задачи

```bash
# Проверка логов воркера
docker-compose logs celery-worker

# Проверка очереди RabbitMQ
# Откройте http://localhost:15672 (guest/guest)
```

### Ошибки транскодирования

1. Проверьте логи video-service:
   ```bash
   docker-compose logs video-service
   ```

2. Проверьте наличие FFmpeg в контейнере:
   ```bash
   docker-compose exec video-service ffmpeg -version
   ```

---

## API Endpoints

### Auth Service (`/api/auth/`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/register` | Регистрация пользователя |
| POST | `/token` | Получение токена (login) |
| POST | `/refresh` | Обновление токена |
| GET | `/users/me` | Получение текущего пользователя |
| GET | `/health` | Health check |

### Video Service (`/api/video/`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/videos/upload/init` | Инициализация загрузки |
| POST | `/videos/{id}/complete` | Завершение загрузки |
| GET | `/videos` | Список видео |
| GET | `/videos/{id}` | Получение видео |
| GET | `/videos/{id}/signed-url` | Получение подписанной ссылки |
| GET | `/health` | Health check |

### Streaming Service (`/api/streaming/`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/streams` | Создание стрима |
| GET | `/streams` | Список стримов |
| GET | `/streams/{id}` | Получение стрима |
| PUT | `/streams/{id}/start` | Запуск стрима |
| PUT | `/streams/{id}/stop` | Остановка стрима |
| GET | `/health` | Health check |

### Notification Service (`/api/notifications/`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/notifications` | Создание уведомления |
| GET | `/notifications` | Список уведомлений |
| PUT | `/notifications/{id}/read` | Отметка как прочитанное |
| POST | `/notifications/mark-all-read` | Отметить все как прочитанные |
| GET | `/health` | Health check |

### Search Service (`/api/search/`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/search?q=<query>` | Поиск видео |
| GET | `/videos/{id}/subtitles` | Получение субтитров |
| POST | `/search/index/{id}` | Индексация видео |
| DELETE | `/search/index/{id}` | Удаление из индекса |
| GET | `/health` | Health check |

---

## Интеграция с LDAP/Active Directory

Для включения LDAP-аутентификации настройте в `.env`:

```env
LDAP_SERVER=ldap://your-ad-server.dgi.mos.ru
LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
LDAP_BIND_USER=cn=admin,dc=dgi,dc=mos,dc=ru
LDAP_BIND_PASSWORD=your-password
```

---

## Production развёртывание

Для развёртывания на боевом сервере следуйте инструкциям в [DEPLOYMENT.md](./DEPLOYMENT.md).

### Ключевые отличия production от development:

1. **SSL/TLS**: Обязательно настройте HTTPS через Certbot
2. **Секреты**: Замените все пароли и ключи на безопасные
3. **Масштабирование**: Настройте реплики сервисов
4. **Мониторинг**: Включите алерты в Grafana
5. **Backup**: Настройте автоматическое резервное копирование
6. **LDAP**: Настройте интеграцию с Active Directory

---

## Контакты

По вопросам обращайтесь: support@video.dgi.ru
