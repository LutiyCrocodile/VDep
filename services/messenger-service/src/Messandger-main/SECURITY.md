# Безопасность приложения

Документ описывает меры по обеспечению информационной безопасности корпоративного мессенджера ДГИ.

---

## 1. Аутентификация и управление сессиями

- **JWT-токены** (HMAC-SHA256, `app/services/auth.py`). `Authorization: Bearer <token>` для REST, query-параметр `?token=` при подключении к WebSocket `/ws`. Проверка подписи на каждом запросе.
- **Хеширование паролей** — bcrypt через `passlib`, уникальная соль для каждого пользователя.
- **Срок действия пароля** — 90 дней (`User.password_expires_at`). По истечении клиент получает `password_expired=true` и принудительно перенаправляется на смену пароля.
- **Блокировка / заморозка** учётной записи (`is_blocked`, `is_frozen`) проверяется при каждом входе.

## 2. Защита от перебора (brute-force)

`backend/app/routers/auth.py` + общий middleware:

- Счётчик `email + IP`. После **5 неудач** → блокировка комбинации на **15 минут** (HTTP 429). Сбрасывается при успешном логине.
- **Глобальный sliding-window rate limiter** (`app/middleware.py`): 300 req/min/IP по умолчанию, ужесточённые лимиты для `/api/auth/login` (10/мин), `/api/auth/access-request` (5/5мин), `/api/auth/me/avatar/upload` (10/мин). Превышение — 429 + запись в аудит `rate_limit_exceeded`.

## 3. Авторизация и разграничение ролей

- **RBAC**: `super_admin`, `admin`, `head`, `deputy_head`, `member`, `readonly`.
- Все админские эндпоинты защищены `require_admin`.
- Внутри чата — `ChatMember.role`: `owner / admin / member / readonly`.
- Автоповышение прав начальников / заместителей при добавлении в групповой чат.

## 4. Подтверждение деструктивных операций

Глобальный `ConfirmDialog` + `useConfirmStore` на фронтенде. Любое удаление / блокировка / сброс пароля проходит через явное подтверждение.

## 5. Шифрование канала и БД

### Канал
- **HTTPS / WSS** обязателен в production. Заголовок `Strict-Transport-Security: max-age=31536000; includeSubDomains` форсирует HTTPS.
- Заголовки безопасности (middleware `_security_headers` в `app/middleware.py`):
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` — камера/микрофон/screen-capture только для своего домена
  - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'` для `/api/*`
- **CORS** — белый список через `CORS_ORIGINS`.

### База данных
- **TLS для PostgreSQL** включается автоматически: при `DB_REQUIRE_TLS=true` (по умолчанию) драйвер получает `ssl=require`. Параметр в `app/database.py::_build_engine()`.
- **SQLCipher для SQLite** — прозрачное AES-шифрование файла БД. Включается через переменную окружения `DB_ENCRYPTION_KEY`. При наличии `sqlcipher`-совместимого DBAPI на каждом подключении выполняется `PRAGMA key='<KEY>'; PRAGMA cipher_compatibility=4;`. Без ключа БД работает в открытом виде; в production это вызовет предупреждение при старте (`validate_security_config`).
- **Валидация конфигурации** при старте: в `production` запрещён дефолтный `SECRET_KEY` и слишком короткий ключ (< 32 символа).

## 6. Резервное копирование и восстановление при инцидентах

`app/services/backup.py` + фоновая задача `backup_worker` (запускается из `lifespan`):

- Используется встроенный **SQLite Online Backup API** (`sqlite3.Connection.backup`) — это hot-backup без блокировки приложения и без риска повреждения файла.
- Бэкапы складываются в `BACKUP_DIR` (по умолчанию `backups/`), сжимаются gzip, имеют имя `backup_<UTC>_<reason>.db.gz`.
- Для каждого бэкапа считается **SHA-256** (для проверки целостности).
- **Ротация**: хранятся последние `BACKUP_KEEP` (по умолчанию 30) файлов.
- **Расписание**: `BACKUP_INTERVAL_HOURS` (по умолчанию 6). Перед каждым бэкапом выполняется `PRAGMA integrity_check` + `PRAGMA quick_check`.
- **Аварийный бэкап** при обнаружении повреждения БД создаётся немедленно (`reason="integrity_fail"`) и пишется событие аудита `db_integrity_fail`.
- **Ручные бэкапы**: эндпоинт `POST /api/admin/backups` (только админ) — `reason="manual"`.
- **Скачивание**: `GET /api/admin/backups/{filename}/download` — защищён от path traversal.
- **Аудит**: каждое создание/скачивание бэкапа фиксируется в `audit_logs`.

### Восстановление при компрометации
1. Изолировать сервер, отключить трафик.
2. Через админский эндпоинт скачать актуальный бэкап (`GET /api/admin/backups`).
3. Развернуть бэкап на чистом окружении: `gunzip < backup_*.db.gz > messenger.db`.
4. Сменить `SECRET_KEY` (это инвалидирует все JWT) и `DB_ENCRYPTION_KEY` при необходимости.
5. Сбросить пароли всем пользователям (`is_frozen=true` + принудительная смена при следующем входе).
6. Проанализировать `audit_logs` за период инцидента (фильтр `?action=login_failed&status=failed`).

## 7. Журнал аудита

Модель `AuditLog` (`app/models/audit.py`), сервис `app/services/audit.py`, эндпоинт `GET /api/admin/audit-log`.

Фиксируемые события:

| Action                  | Когда пишется                             |
|-------------------------|-------------------------------------------|
| `login_success`         | Успешный вход                             |
| `login_failed`          | Неверные креденшелы                       |
| `login_blocked`         | Аккаунт заблокирован/заморожен/неактивен  |
| `password_change`       | Смена пароля                              |
| `rate_limit_exceeded`   | Превышен rate limit                       |
| `unhandled_exception`   | Необработанная ошибка в эндпоинте         |
| `db_error`              | Ошибка SQLAlchemy                         |
| `db_integrity_fail`     | Нарушена целостность БД                   |
| `backup_create`         | Создан бэкап (плановый/ручной/аварийный)  |
| `backup_download`       | Скачан бэкап                              |

Поля: `actor_id`, `actor_email`, `action`, `object_type`, `object_id`, `ip_address`, `user_agent`, `status`, `details` (JSON), `created_at`.

Аудит пишется в **независимой** сессии БД, поэтому событие сохраняется даже если основная транзакция откатилась.

## 8. Мониторинг и метрики

In-memory счётчики в `app/services/metrics.py`. Эндпоинт `GET /api/admin/metrics` (только админ) возвращает:

- `request_total`, `http_2xx_3xx`, `http_4xx`, `http_5xx`
- `rate_limited`, `payload_too_large`
- `ws_active` — число активных WebSocket-подключений
- `uptime_seconds`, `started_at`
- `env`, `db_url_kind` (sqlite/postgresql), `db_encrypted`

Каждый HTTP-ответ содержит:
- `X-Request-Id` — корреляционный ID, включается в `audit_logs.details` и в сообщения об ошибках для пользователя
- `X-Response-Time-Ms` — время обработки

## 9. Глобальная обработка ошибок

### Backend (`app/middleware.py`)
- HTTP-middleware ловит любое необработанное исключение → возвращает `500 {detail, request_id}` без утечки stack trace, пишет полный трейс в логи + аудит.
- Отдельные обработчики для `StarletteHTTPException`, `RequestValidationError`, `SQLAlchemyError`.
- Лимит размера тела запроса: 50 МБ (200 МБ для `/api/chats/*/upload`) → 413.

### Frontend
- `ErrorBoundary` (`src/components/ErrorBoundary.jsx`) ловит ошибки рендера и показывает экран восстановления.
- Глобальный axios-interceptor (`src/api/axios.js`) показывает понятные toast-уведомления для 4xx/5xx, тайм-аутов и обрывов сети, в т.ч. с request_id из заголовка ответа.

## 10. Безопасность WebRTC и звонков

См. подробное описание в разделе **«Как работают звонки»** в `README.md`. Краткое:

- Сигнализация (SDP, ICE) идёт через WebSocket `/ws` (события `call_invite / call_accept / call_reject / call_signal / call_end`); тело сигнала обрабатывается в `backend/app/routers/websocket.py`.
- Медиа-потоки (audio/video/screen) идут **peer-to-peer** между браузерами; на сервере не хранятся и не обрабатываются.
- Шифрование на уровне **DTLS-SRTP** — обязательное требование стандарта WebRTC, реализуется браузером.
- ICE-серверы — **публичные STUN от Google** (`stun.l.google.com:19302` и др.). В production развернуть **собственный TURN** (например, `coturn`) внутри корпоративного контура.
- Доступ к камере/микрофону/экрану ограничен `Permissions-Policy` и стандартным permission-диалогом браузера.
- Звонок логируется в БД (`calls`, `call_participants`): инициатор, тип, время начала/конца, длительность.

## 11. Защита от XSS, CSRF и инъекций

- React автоматически экранирует текст; `dangerouslySetInnerHTML` не используется.
- Ссылки рендерятся с `rel="noopener noreferrer"`.
- SQL-инъекции невозможны: только параметризованные запросы SQLAlchemy.
- ID — UUID v4 (непредсказуемые).
- CSRF: API использует `Authorization: Bearer` (не cookies) — уязвимости CSRF к этой схеме неприменимы. Cookie-сессии не используются.

## 12. Безопасность загружаемых файлов

`backend/app/routers/chats.py::upload_file`:

- **Whitelist расширений** (`ALLOWED_UPLOAD_EXT` в config). Запрещены `.exe`, `.bat`, `.js`, `.html` и т.п.
- **Лимит размера** `MAX_UPLOAD_MB` (по умолчанию 100 МБ) — проверяется потоково, при превышении файл удаляется и возвращается 413.
- Файлы хранятся под UUID-именами в `uploads/`, исходное имя — только в БД (защита от path traversal и перезаписи).
- Скачивание требует валидного токена и членства в чате.

## 13. Рекомендации по эксплуатации

- В production: HTTPS-прокси (nginx/Traefik) перед FastAPI, сертификат от внутреннего CA или Let's Encrypt.
- Сменить `SECRET_KEY` на random ≥ 64 байт.
- Установить `ENV=production` — это включит строгие проверки конфигурации.
- Для SQLite — установить `DB_ENCRYPTION_KEY` и пакет `sqlcipher3-binary`. Для PostgreSQL — оставить `DB_REQUIRE_TLS=true`.
- Ограничить доступ к серверу БД через `pg_hba.conf` или firewall.
- Настроить **внешнее** копирование папки `backups/` (rsync на NAS, S3 с serverside-encryption и т.п.) — локальные бэкапы защищают от повреждения, но не от компрометации хоста.
- Развернуть собственный TURN-сервер.
- Для критичных учёток (super_admin) — рассмотреть TOTP-2FA.
- Регулярно мониторить `GET /api/admin/audit-log?action=login_failed&status=failed` — рост количества неудачных входов = признак атаки.
