# Обмен сообщениями между микросервисами

## Принципы

- **Видеохостинг** — набор независимых микросервисов (не монолит).
- **auth-service** — единая точка соприкосновения: JWT, RBAC, internal API (`/internal/users/*`).
- **portal** — единая точка входа пользователя (логин, выдача токенов в подсистемы).
- **messenger / dashboard / support** — заготовки; позже подключаются к auth и (опционально) к шине событий.

## Текущая реализация (dev)

| Назначение | Технология | Пример |
|------------|------------|--------|
| Проверка пользователя | HTTP → auth `GET /users/me` | Все API с Bearer JWT |
| Сервис → сервис | HTTP + `INTERNAL_AUTH_TOKEN` | video/streaming → notification `/internal/events/channel` |
| Фоновые задачи (транскодинг) | **Celery + Redis** | `celery-worker`, очереди `video_transcoding` |
| Дедуп уведомлений | **Redis** | `notified:stream_live:*` |
| Межсервисные события (целевое) | **RabbitMQ** | Описано в `ARCHITECTURE.md`, код — в плане |

**RabbitMQ** поднимается в `dev-up.ps1`, но приложения пока не публикуют в AMQP. Контейнер healthy, очереди в Management UI пустые — это ожидаемо.

## Целевая схема (масштабирование)

1. **Redis** — Celery, кэш, краткоживущие ключи (presence, dedupe).
2. **RabbitMQ** — domain events: `auth.user.updated`, `video.ready`, `stream.live`; подписчики: notification, заготовки messenger/dashboard.
3. **HTTP internal** — остаётся для запросов «здесь и сейчас» (контакт пользователя, subscriber IDs).

Подключение RabbitMQ — отдельная фаза, без ломания текущих HTTP-уведомлений.
