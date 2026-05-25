# Чеклист оптимизации (регрессия dev)

Перед и после каждой фазы — ручная проверка на стеке `infrastructure/docker/scripts/dev-up.ps1`.

## Архитектурные ограничения

- [ ] Микросервисы не объединяются в монолит
- [ ] auth-service — единая авторизация для всех подсистем
- [ ] portal — единая точка входа
- [ ] Заготовки messenger / dashboard / support не удаляются
- [ ] Порты и `dev-up.ps1` без неожиданных изменений

## Функционал видеохостинга

- [ ] Вход через portal → frontend с токенами в URL
- [ ] Каталог и просмотр `/watch`
- [ ] Загрузка и публикация видео (транскодинг celery-worker)
- [ ] Go-live / stream `/stream/[id]`
- [ ] Подписки, лайки, уведомления (колокольчик)
- [ ] Email-уведомления (SMTP в `.env`)
- [ ] Поиск `/search?q=...` (search-service :8004)

## API (smoke)

- [ ] `GET http://localhost:8000/health`
- [ ] `GET http://localhost:8001/health`
- [ ] `GET http://localhost:8002/health`
- [ ] `GET http://localhost:8003/health`
- [ ] `GET http://localhost:8004/health`
- [ ] `POST http://localhost:8003/internal/test-email` (при настроенном SMTP)

## Фазы

| Фаза | Статус | Содержание |
|------|--------|------------|
| 1 | ✅ | portal-url, поиск :8004, индексация ES |
| 2 | ✅ | N+1, индексы БД, httpx pool |
| 3 | ✅ video+streaming / ⏳ auth | Разбиение main.py на routers |
| 4 | план | Redis presence, RabbitMQ events |
| 5 | план | lock-файлы, интеграционные тесты |
| 6 | с вами | Prod deploy, секреты, nginx TLS |
