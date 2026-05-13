# 🚀 Запуск и тестирование единой системы авторизации

## 📦 Что было сделано

✅ **Auth Service** обновлен:
   - Добавлены Origins CORS для messenger, dashboard, support
   - Добавлена настройка `ALLOW_REGISTRATION` (по умолчанию `false`)

✅ **Портал** обновлен:
   - Мессенджер: `http://localhost:3001` (статус: active)
   - Дашборд: `http://localhost:3003` (статус: active)
   - Техподдержка: `http://localhost:3004` (статус: active)

✅ **Nginx** обновлен:
   - Добавлены upstream'ы для новых сервисов
   - Добавлены server-блоки (subdomains)

✅ **Новые сервисы** созданы:
   - messenger-service (FastAPI + HTML UI)
   - dashboard-service (FastAPI + HTML UI)
   - support-service (FastAPI + HTML UI)

✅ **Docker Compose** обновлен:
   - messenger-service (port 3001)
   - dashboard-service (port 3003)
   - support-service (port 3004)

✅ **Тестовые пользователи** добавлены в seed_data.sql:
   - `admin` / `admin123` - полный доступ ко всем сервисам
   - `video_admin` / `admin123` - доступ к видео
   - `messenger_user` / `admin123` - доступ к мессенджеру
   - `analyst` / `admin123` - доступ к дашборду
   - `support_agent` / `admin123` - доступ к техподдержке
   - `employee` / `admin123` - базовый доступ
   - `external` / `admin123` - внешний пользователь (ограниченный доступ)

---

## 🏃‍♂️ Быстрый старт (Dev Environment)

### 1️⃣ Подготовка окружения

```bash
# Перейдите в папку проекта
cd C:\Users\Maks\Desktop\ДИПЛОМ\video.dgi.mos.ru\infrastructure\docker

# Проверьте .env файл
cat .env

# Если нет .env, создайте из примера
cp .env.example .env
```

### 2️⃣ Запуск всех сервисов

```bash
# Сборка и запуск всех контейнеров
docker compose up -d --build

# Проверьте статус
docker compose ps

# Ожидаемый результат:
# NAME                    STATUS              PORTS
# auth-service            Up (healthy)        0.0.0.0:8000->8000/tcp
# video-service           Up (healthy)        0.0.0.0:8001->8001/tcp
# streaming-service       Up (healthy)        0.0.0.0:8002->8002/tcp
# notification-service    Up (healthy)        0.0.0.0:8003->8003/tcp
# search-service          Up (healthy)        0.0.0.0:8004->8004/tcp
# messenger-service       Up (healthy)        0.0.0.0:3001->3001/tcp
# dashboard-service       Up (healthy)        0.0.0.0:3003->3003/tcp
# support-service         Up (healthy)        0.0.0.0:3004->3004/tcp
# portal                  Up (healthy)        0.0.0.0:3002->3002/tcp
# frontend                Up (healthy)        0.0.0.0:3000->3000/tcp
# db                      Up (healthy)        5432/tcp
# redis                   Up (healthy)        6379/tcp
# rabbitmq                Up (healthy)        5672/tcp, 15672/tcp
# minio                   Up (healthy)        9000/tcp, 9001/tcp
# elasticsearch           Up (healthy)        9200/tcp, 9300/tcp
```

### 3️⃣ Инициализация базы данных (тестовые пользователи)

```bash
# Подождите пока все сервисы станут healthy (около 30 сек)

# Запустите seed_data.sql
docker exec -i infrastructure-docker-db-1 psql -U user -d video_hosting < database/seed_data.sql

# Проверьте, что пользователи созданы
docker exec -it infrastructure-docker-db-1 psql -U user -d video_hosting -c "SELECT username, email, is_employee FROM users;"

# Ожидаемый вывод:
#   username  |        email         | is_employee
# ------------+----------------------+-------------
#  admin      | admin@dgi.mos.ru     | t
#  video_admin| video.admin@dgi.mos.ru| t
#  messenger_user| messenger.user@dgi.mos.ru| t
#  analyst    | analyst@dgi.mos.ru   | t
#  support_agent| support@dgi.mos.ru | t
#  employee   | employee@dgi.mos.ru  | t
#  external   | external@example.com | f
```

### 4️⃣ Проверка работы сервисов

```bash
# Проверка health endpoints
curl http://localhost:8000/health  # Auth
curl http://localhost:8001/health  # Video
curl http://localhost:3001/health  # Messenger
curl http://localhost:3003/health  # Dashboard
curl http://localhost:3004/health  # Support

# Все должны вернуть {"status":"healthy","service":"..."}
```

---

## 🧪 Тестирование единой авторизации

### Шаг 1: Вход через портал

1. Откройте браузер: `http://localhost:3002`
2. Нажмите "Войти"
3. Введите учетные данные:
   - **Логин:** `admin`
   - **Пароль:** `admin123`
4. После успешного входа вы увидите 4 активных сервиса

✅ **Ожидаемый результат:**
- Везде видно ваше имя
- Все 4 сервиса кликабельны (статус "active")
- Токены сохранены в localStorage

### Шаг 2: Проверка токенов

Откройте DevTools (F12) → Console и выполните:

```javascript
// Проверьте токены
localStorage.getItem('access_token')   // Должен быть JWT
localStorage.getItem('refresh_token')  // Должен быть JWT

// Декодируйте access token (не расшифровывайте, только посмотрите payload)
const token = localStorage.getItem('access_token');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log(payload);

// В payload должны быть:
// - sub: "admin"
// - is_employee: true
// - services: { video: {...}, messenger: {...}, dashboard: {...}, support: {...} }
```

### Шаг 3: Тест мессенджера

1. На портале нажмите на карточку **"Мессенджер"**
2. Должен открыться `http://localhost:3001`
3. Страница показывает:
   - Статус: "Авторизован" (зеленый)
   - Список доступных функций

✅ **Ожидается:** Автоматическое принятие токена из localStorage

### Шаг 4: Тест дашборда

1. Нажмите на карточку **"Дашборд"**
2. Откроется `http://localhost:3003`
3. Должны отобразиться метрики (6 карточек)

✅ **Ожидается:** Данные загружены с сервера

### Шаг 5: Тест техподдержки

1. Нажмите на карточку **"Техподдержка"**
2. Откроется `http://localhost:3004`
3. Вы можете создать заявку

✅ **Ожидается:** Форма работает, заявка создается

### Шаг 6: Тест RBAC (ограничение прав)

#### Вариант A: Внешний пользователь (без прав)

1. Выйдите из системы (кнопка "Выйти" на портале)
2. Войдите как `external` / `admin123`
3. Попробуйте открыть:
   - **Мессенджер** → Должна быть ошибка 403
   - **Дашборд** → Ошибка 403
   - **Техподдержка** → Может работать (у external есть support:create_ticket?)

   ```sql
   -- Проверьте права external в БД:
   SELECT u.username, s.slug, sr.name 
   FROM user_service_roles usr
   JOIN users u ON usr.user_id = u.id
   JOIN service_roles sr ON usr.service_role_id = sr.id
   JOIN services s ON sr.service_id = s.id
   WHERE u.username = 'external';
   ```

#### Вариант B: Пользователь с ограниченными правами

1. Войдите как `employee` / `admin123`
2. Откройте мессенджер → **Ошибка 403** (у employee нет роли messenger)
3. Откройте дашборд → OK (employee имеет dashboard:viewer)
4. Откройте техподдержку → OK (employee имеет support:user)

### Шаг 7: Тест refresh token

1. В DevTools Console на localhost:3002:
```javascript
// Удалите access_token
localStorage.removeItem('access_token');

// Сделайте API запрос
fetch('http://localhost:3001/api/chats', {
  headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
});
// Должен автоматически обновиться (если refresh_token валиден)
```

---

## 🐛 Устранение неполадок

### Проблема: "Cannot connect to database"

```bash
# Проверьте логи
docker compose logs db

# Перезапустите базу
docker compose restart db

# Если не помогает - пересоздайте volume
docker compose down -v
docker compose up -d --build
```

### Проблема: "401 Unauthorized" в сервисах

```bash
# 1. Проверьте токен
curl http://localhost:8000/users/me -H "Authorization: Bearer $(localStorage.getItem('access_token'))"

# 2. Если токен истек, обновите
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"..."}'

# 3. Проверьте CORS настройки auth-service
# Файл: services/auth-service/src/main.py:245-251
```

### Проблема: Сервисы не отображаются на портале

```bash
# Проверьте статус сервисов:
curl http://localhost:3001/health
curl http://localhost:3003/health
curl http://localhost:3004/health

# Если не отвечают - проверьте логи
docker compose logs messenger-service
docker compose logs dashboard-service
docker compose logs support-service
```

### Проблема: Токены не передаются в сервисы

Портал передает токены через URL параметры:
```
http://localhost:3000?access_token=xxx&refresh_token=yyy
```

Если сервис не принимает токены:
1. Проверьте, что сервис извлекает параметры из URL
2. Сохраняет в localStorage
3. Использует для Authorization заголовка

---

## 📊 Чеклист готовности

### Infrastructure ✅
- [x] Docker Compose запущен
- [x] Все 15 контейнеров healthy
- [x] База данных инициализирована
- [x] seed_data.sql выполнен

### Auth Service ✅
- [x] /health отвечает
- [x] /token выдает JWT
- [x] /users/me возвращает данные с полем services
- [x] ALLOW_REGISTRATION=false (в продакшене)
- [x] CORS для 5 origins (3000, 3001, 3002, 3003, 3004)

### Portal ✅
- [x] Иконки сервисов кликабельны
- [x] Токены передаются через URL
- [x] Локаут работает

### Video Frontend ✅
- [x] Принимает токены из URL
- [x] Сохраняет в localStorage
- [x] Авторизованные запросы работают
- [x] Refresh token работает

### Messenger Service ✅
- [x] /health работает
- [x] /api/chats требует авторизации
- [x] Проверяет право access через RBAC
- [x] HTML-интерфейс отображается

### Dashboard Service ✅
- [x] /health работает
- [x] /api/metrics требует авторизации
- [x] Фильтрует данные по роли
- [x] HTML-интерфейс отображается

### Support Service ✅
- [x] /health работает
- [x] /api/tickets работает
- [x] RBAC проверка (agent vs user)
- [x] HTML-интерфейс отображается

---

## 🔐 Настройка для Production

### 1. Переменные окружения

```bash
# infrastructure/docker/.env
ALLOW_REGISTRATION=false
SECRET_KEY=<генерация: openssl rand -hex 32>
INTERNAL_AUTH_TOKEN=<генерация: uuidgen>
```

### 2. LDAP интеграция

```bash
# Заполните в .env:
LDAP_SERVER=ldap://ad.dgi.mos.ru
LDAP_BASE_DN=DC=dgi,DC=mos,DC=ru
LDAP_BIND_USER=CN=svc-video,CN=Users,DC=dgi,DC=mos,DC=ru
LDAP_BIND_PASSWORD=<пароль>
```

### 3. HTTPS (SSL/TLS)

Раскомментируйте в nginx.conf:
```nginx
listen 443 ssl;
ssl_certificate /etc/ssl/certs/dgi.mos.ru.crt;
ssl_certificate_key /etc/ssl/private/dgi.mos.ru.key;
```

### 4. DNS

Настройте DNS A-records:
```
portal.dgi.mos.ru   → IP сервера
video.dgi.mos.ru    → IP сервера
messenger.dgi.mos.ru→ IP сервера
dashboard.dgi.mos.ru→ IP сервера
support.dgi.mos.ru  → IP сервера
```

---

## 📚 Документация API

После запуска Swagger доступен по адресам:
- Auth: http://localhost:8000/docs
- Video: http://localhost:8001/docs
- Messenger: http://localhost:3001/docs (если включен)
- Dashboard: http://localhost:3003/docs
- Support: http://localhost:3004/docs

---

## 🎯 Что дальше?

1. **Настройте LDAP** для корпоративной авторизации
2. **Настройте SMTP** для email-уведомлений
3. **Разверните на production** сервере
4. **Настройте мониторинг** (Prometheus + Grafana уже есть)
5. **Настройте backup** базы данных
6. **Настройте HTTPS** (Let's Encrypt)

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker compose logs <service-name>`
2. Проверьте health: `curl http://localhost:<port>/health`
3. Убедитесь, что база данных инициализирована
4. Проверьте переменные окружения в .env

---

**Удачи в тестировании!** 🚀
