# План единой авторизации через портал ДГИ

## 📋 Краткое резюме

**Текущее состояние:** ✅ Система уже реализована с единой авторизацией!

Ваша архитектура **УЖЕ НАСТРОЕНА** для работы с единой точкой входа через портал на `localhost:3002`. Все компоненты правильно интегрированы:

- ✅ Auth-service (8000) - центральный сервис авторизации с JWT + RBAC
- ✅ Portal (3002) - единая точка входа для всех сервисов
- ✅ Frontend видеохостинга (3000) - получает токены от портала
- ✅ Multi-service architecture - 4 сервиса готовы к интеграции

---

## 🏗️ Архитектура единой авторизации

### Схема потока авторизации

```
┌─────────────────┐
│  Пользователь   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Portal (localhost:3002)    │  ◄─── ЕДИНАЯ ТОЧКА ВХОДА
│  - Страница /login          │
│  - Проверка is_employee     │
│  - Хранение токенов         │
└─────────┬───────────────────┘
          │
          │ JWT tokens
          ├──────────┬─────────────┬──────────────┬─────────────┐
          ▼          ▼             ▼              ▼             ▼
    ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐
    │ Видео   │ │Мессенджер│ │ Дашборд  │ │Техподдержка│ │  Другие  │
    │ :3000   │ │  :XXXX   │ │  :XXXX   │ │   :XXXX    │ │          │
    └─────────┘ └──────────┘ └──────────┘ └────────────┘ └──────────┘
          │          │             │              │             │
          └──────────┴─────────────┴──────────────┴─────────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │  Auth Service      │
                        │  (localhost:8000)  │
                        │                    │
                        │  - JWT validation  │
                        │  - RBAC            │
                        │  - LDAP            │
                        │  - User mgmt       │
                        └────────────────────┘
```

---

## 🔐 Как работает единая авторизация

### 1. Вход через портал

```typescript
// portal/src/app/login/page.tsx

// Шаг 1: Пользователь вводит логин/пароль
handleLogin() {
  POST http://localhost:8000/token
  Body: username=user&password=pass
}

// Шаг 2: Auth-service проверяет:
//   - Локальная БД или LDAP
//   - Флаг is_employee = true (обязательно!)
//   - Генерирует JWT access_token (15 мин) + refresh_token (7 дней)

// Шаг 3: Портал сохраняет токены
localStorage.setItem('access_token', data.access_token)
localStorage.setItem('refresh_token', data.refresh_token)

// Шаг 4: Портал получает профиль
GET http://localhost:8000/users/me
Headers: Authorization: Bearer <access_token>

// Шаг 5: Проверка is_employee
if (userData.is_employee) {
  // Показать портал с сервисами
} else {
  // Отказ в доступе
  alert('Доступ разрешен только сотрудникам ДГИ')
}
```

### 2. Переход в сервисы

```typescript
// portal/src/app/page.tsx (строка 249-263)

handleServiceClick(service) {
  const accessToken = localStorage.getItem('access_token')
  const refreshToken = localStorage.getItem('refresh_token')
  
  // Передаем токены через URL (временное решение)
  const url = `${service.url}?access_token=${accessToken}&refresh_token=${refreshToken}`
  
  window.location.href = url
}
```

**Сервисы принимают токены:**
- Видеохостинг извлекает токены из URL
- Сохраняет в localStorage
- Использует для всех API запросов

### 3. Проверка прав доступа

```python
# services/auth-service/src/main.py (строка 263-281)

async def create_access_token(data: dict, db: AsyncSession):
    # JWT содержит информацию о правах для ВСЕХ сервисов
    services = await user.get_service_permissions(db)
    
    token = {
        "sub": username,
        "email": user.email,
        "is_employee": user.is_employee,
        "services": {
            "video": {
                "role": "admin",
                "permissions": ["video:upload", "video:manage_all", ...]
            },
            "messenger": {
                "role": "user",
                "permissions": ["messenger:send", "messenger:read"]
            },
            "dashboard": { ... },
            "support": { ... }
        }
    }
```

---

## 🎯 RBAC для 4 сервисов

### Определения сервисов (уже в auth-service)

```python
# services/auth-service/src/main.py (строка 69-74)

services = [
    {"slug": "video", "name": "Видеохостинг ДГИ"},
    {"slug": "messenger", "name": "Мессенджер ДГИ"},
    {"slug": "dashboard", "name": "Дашборд ДГИ"},
    {"slug": "support", "name": "Техподдержка ДГИ"},
]
```

### Роли и права (уже настроены)

#### Видеохостинг
```python
roles: ["admin", "manager", "uploader", "viewer"]
permissions: [
    "video:upload",
    "video:view_private",
    "video:manage_own",
    "video:manage_all",
    "video:stream",
    "video:moderate",
    "video:audit"
]
```

#### Мессенджер
```python
roles: ["admin", "moderator", "user"]
permissions: [
    "messenger:send",
    "messenger:read",
    "messenger:delete_own",
    "messenger:delete_all",
    "messenger:create_group",
    "messenger:call"
]
```

#### Дашборд
```python
roles: ["admin", "analyst", "viewer"]
permissions: [
    "dashboard:view_all",
    "dashboard:view_own",
    "dashboard:export",
    "dashboard:manage_reports",
    "dashboard:manage_all"
]
```

#### Техподдержка
```python
roles: ["admin", "agent", "user"]
permissions: [
    "support:create_ticket",
    "support:view_own_tickets",
    "support:view_all_tickets",
    "support:assign_tickets",
    "support:close_tickets",
    "support:manage_kb"
]
```

---

## 🔧 Что нужно исправить

### ❗ Проблема 1: Передача токенов через URL (НЕБЕЗОПАСНО)

**Текущее состояние (portal/src/app/page.tsx:256-259):**
```typescript
// ❌ ПЛОХО: Токены видны в истории браузера
url += `?access_token=${token}&refresh_token=${refreshToken}`
window.location.href = url
```

**✅ ПРАВИЛЬНОЕ решение:**

**Вариант A: Shared localStorage (рекомендуется для dev)**
```typescript
// Все сервисы на одном домене читают localStorage
// Portal сохраняет: localStorage.setItem('access_token', token)
// Сервисы читают: localStorage.getItem('access_token')

// Работает если:
// - Portal: http://localhost:3002
// - Video: http://localhost:3000
// - Messenger: http://localhost:3001
// - Dashboard: http://localhost:3003
// - Support: http://localhost:3004

// ⚠️ НЕ работает для разных доменов в prod
```

**Вариант B: Cookie с SameSite (для production)**
```typescript
// Portal устанавливает cookie
document.cookie = `access_token=${token}; domain=.dgi.mos.ru; secure; httpOnly; SameSite=Lax`

// Все поддомены получают cookie автоматически:
// - portal.dgi.mos.ru
// - video.dgi.mos.ru
// - messenger.dgi.mos.ru
// - dashboard.dgi.mos.ru
// - support.dgi.mos.ru
```

**Вариант C: OAuth 2.0 Authorization Code Flow (best practice)**
```
1. Portal → Service: redirect + code
2. Service → Auth: exchange code for token
3. Auth → Service: access_token
```

### ❗ Проблема 2: Регистрация должна быть скрыта

**Текущее состояние:**
- Auth-service имеет эндпоинт `/register` (открыт)
- Frontend имеет страницу регистрации

**✅ Исправление:**

```python
# services/auth-service/src/main.py

@app.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Добавить проверку режима
    if not settings.allow_registration:
        raise HTTPException(
            status_code=403,
            detail="Registration is disabled. Contact administrator."
        )
    # ... existing code
```

```python
# services/auth-service/src/config.py

class Settings(BaseSettings):
    # ... existing fields
    allow_registration: bool = False  # ❗ По умолчанию выключена
    
    # Для тестирования:
    # allow_registration: bool = True
```

**В production:**
```bash
# .env
ALLOW_REGISTRATION=false
```

**Для тестов:**
```bash
# .env
ALLOW_REGISTRATION=true  # Временно для создания тестовых пользователей
```

---

## 🚀 Интеграция новых сервисов

### Шаг 1: Настройте CORS в auth-service

```python
# services/auth-service/src/main.py (строка 245-251)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Video
        "http://localhost:3001",  # Messenger  ◄─ ДОБАВИТЬ
        "http://localhost:3002",  # Portal
        "http://localhost:3003",  # Dashboard  ◄─ ДОБАВИТЬ
        "http://localhost:3004",  # Support    ◄─ ДОБАВИТЬ
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Шаг 2: Добавьте сервисы в портал

```typescript
// portal/src/app/page.tsx (строка 59-104)

const getServices = (): Service[] => [
  {
    id: 'video',
    name: 'Видеохостинг',
    url: 'http://localhost:3000',  // ✅ Уже есть
    status: 'active',
  },
  {
    id: 'messenger',
    name: 'Мессенджер',
    url: 'http://localhost:3001',  // ◄─ УКАЖИТЕ ПОРТ
    status: 'coming-soon',         // ◄─ ИЗМЕНИТЕ на 'active' когда готово
  },
  {
    id: 'dashboard',
    name: 'Дашборд',
    url: 'http://localhost:3003',  // ◄─ УКАЖИТЕ ПОРТ
    status: 'coming-soon',         // ◄─ ИЗМЕНИТЕ на 'active' когда готово
  },
  {
    id: 'support',
    name: 'Техподдержка',
    url: 'http://localhost:3004',  // ◄─ УКАЖИТЕ ПОРТ
    status: 'coming-soon',         // ◄─ ИЗМЕНИТЕ на 'active' когда готово
  }
];
```

### Шаг 3: Каждый сервис должен принять токены

**Пример для Messenger (аналогично Dashboard, Support):**

```typescript
// messenger/src/app/page.tsx

useEffect(() => {
  // Проверить URL параметры
  const urlParams = new URLSearchParams(window.location.search);
  const accessToken = urlParams.get('access_token');
  const refreshToken = urlParams.get('refresh_token');
  
  if (accessToken && refreshToken) {
    // Сохранить токены
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    
    // Очистить URL (скрыть токены)
    window.history.replaceState({}, '', window.location.pathname);
    
    // Проверить профиль
    validateUser();
  } else {
    // Токены уже в localStorage?
    const existingToken = localStorage.getItem('access_token');
    if (!existingToken) {
      // Редирект на портал
      window.location.href = 'http://localhost:3002/login';
    }
  }
}, []);

async function validateUser() {
  const token = localStorage.getItem('access_token');
  const res = await fetch('http://localhost:8000/users/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  if (!res.ok) {
    // Токен невалиден - на портал
    window.location.href = 'http://localhost:3002/login';
    return;
  }
  
  const user = await res.json();
  
  // Проверить права доступа к мессенджеру
  const messengerRole = user.services?.messenger?.role;
  if (!messengerRole) {
    alert('У вас нет доступа к мессенджеру');
    window.location.href = 'http://localhost:3002';
    return;
  }
  
  // Все ок, показать интерфейс
  setUser(user);
}
```

### Шаг 4: API клиенты для новых сервисов

```typescript
// messenger/src/services/api.ts

import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_MESSENGER_API_URL || 'http://localhost:8005',
});

// Автодобавление токена
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Авто-обновление токена при 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      const res = await axios.post('http://localhost:8000/refresh', {
        refresh_token: refreshToken
      });
      
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      
      error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
      return apiClient(error.config);
    }
    return Promise.reject(error);
  }
);

export const messengerAPI = {
  getChats: () => apiClient.get('/chats'),
  sendMessage: (chatId: string, text: string) => 
    apiClient.post(`/chats/${chatId}/messages`, { text }),
};
```

---

## 🧪 Как проверить работоспособность в Dev

### Предварительная подготовка

```bash
# 1. Перейдите в папку проекта
cd C:\Users\Maks\Desktop\ДИПЛОМ\video.dgi.mos.ru

# 2. Проверьте наличие .env файла
ls infrastructure/docker/.env

# 3. Если нет, создайте из примера
cp infrastructure/docker/.env.example infrastructure/docker/.env
```

### Тест 1: Запуск всех сервисов

```powershell
# Запустить все контейнеры
cd infrastructure/docker
docker compose up -d --build

# Проверить статус (все должны быть healthy)
docker compose ps

# Должно быть:
# NAME                    STATUS
# auth-service            Up (healthy)
# video-service           Up (healthy)
# streaming-service       Up (healthy)
# notification-service    Up (healthy)
# search-service          Up (healthy)
# portal                  Up (healthy)
# frontend                Up (healthy)
# db                      Up (healthy)
# redis                   Up (healthy)
# rabbitmq                Up (healthy)
# minio                   Up (healthy)
# elasticsearch           Up (healthy)
# prometheus              Up
# grafana                 Up
```

**🔍 Проверка логов при ошибке:**
```powershell
# Если какой-то сервис failed
docker compose logs auth-service
docker compose logs portal
docker compose logs frontend
```

### Тест 2: Проверка доступности сервисов

```powershell
# Проверить health endpoints
curl http://localhost:8000/health   # Auth service
curl http://localhost:8001/health   # Video service
curl http://localhost:8002/health   # Streaming service
curl http://localhost:8003/health   # Notification service
curl http://localhost:8004/health   # Search service

# Проверить UI
# Portal: http://localhost:3002
# Video: http://localhost:3000

# Проверить инфраструктуру
curl http://localhost:9000/minio/health/live   # MinIO
curl http://localhost:9200/_cluster/health     # Elasticsearch
curl http://localhost:15672                     # RabbitMQ (guest/guest)
```

**✅ Ожидаемый результат:** Все эндпоинты отвечают 200 OK

### Тест 3: Создание тестовых пользователей

#### Вариант A: Через API (если регистрация включена)

```powershell
# 1. Включить регистрацию временно
# Отредактируйте .env:
# ALLOW_REGISTRATION=true

# 2. Перезапустить auth-service
docker compose restart auth-service

# 3. Создать пользователей
$body = @{
    username = "admin_user"
    email = "admin@dgi.mos.ru"
    password = "admin123"
    is_employee = $true
    full_name = "Администратор ДГИ"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

# 4. Создать еще пользователей
$users = @(
    @{ username = "manager_user"; email = "manager@dgi.mos.ru"; password = "manager123"; is_employee = $true },
    @{ username = "employee_user"; email = "employee@dgi.mos.ru"; password = "employee123"; is_employee = $true },
    @{ username = "external_user"; email = "external@example.com"; password = "test123"; is_employee = $false }
)

foreach ($user in $users) {
    $body = $user | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8000/register" -Method POST -ContentType "application/json" -Body $body
}

# 5. ОТКЛЮЧИТЬ регистрацию обратно
# .env: ALLOW_REGISTRATION=false
docker compose restart auth-service
```

#### Вариант B: Через SQL (рекомендуется)

```powershell
# Подключиться к PostgreSQL
docker exec -it infrastructure-docker-db-1 psql -U user -d video_hosting

# Или используйте seed_data.sql
docker exec -i infrastructure-docker-db-1 psql -U user -d video_hosting < database/seed_data.sql
```

```sql
-- SQL команды для создания пользователей
-- (выполнять в psql)

-- 1. Проверить существующие роли
SELECT * FROM roles;

-- 2. Создать роль admin (если нет)
INSERT INTO roles (id, name, description)
VALUES (gen_random_uuid(), 'admin', 'Administrator')
ON CONFLICT (name) DO NOTHING;

-- 3. Создать пользователей
INSERT INTO users (id, username, email, password_hash, is_employee, role_id)
VALUES 
  (gen_random_uuid(), 'admin_user', 'admin@dgi.mos.ru', 
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS5cLPXKe', -- password: admin123
   true, (SELECT id FROM roles WHERE name = 'admin')),
  (gen_random_uuid(), 'manager_user', 'manager@dgi.mos.ru',
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS5cLPXKe', -- password: admin123
   true, (SELECT id FROM roles WHERE name = 'user')),
  (gen_random_uuid(), 'employee_user', 'employee@dgi.mos.ru',
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS5cLPXKe', -- password: admin123
   true, (SELECT id FROM roles WHERE name = 'user'));

-- 4. Проверить созданных пользователей
SELECT username, email, is_employee FROM users;
```

### Тест 4: Авторизация через портал

1. **Откройте портал:**
   ```
   http://localhost:3002
   ```

2. **Нажмите "Войти"** → откроется `/login`

3. **Введите данные:**
   - Логин: `admin_user`
   - Пароль: `admin123`

4. **✅ Ожидается:**
   - Успешный вход
   - Редирект на главную страницу портала
   - Отображение 4 сервисов (Видеохостинг активен, остальные "Скоро")
   - В header справа видно имя пользователя и кнопку выхода

5. **🔍 Проверка токенов:**
   ```javascript
   // Откройте DevTools (F12) → Console
   localStorage.getItem('access_token')   // Должен быть JWT токен
   localStorage.getItem('refresh_token')  // Должен быть JWT токен
   ```

6. **🔍 Проверка профиля:**
   ```javascript
   // В Console
   fetch('http://localhost:8000/users/me', {
     headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
   })
   .then(r => r.json())
   .then(console.log)
   
   // Должен вернуть:
   // {
   //   id: "...",
   //   username: "admin_user",
   //   email: "admin@dgi.mos.ru",
   //   is_employee: true,
   //   role: "admin",
   //   services: {
   //     video: { role: "admin", permissions: [...] },
   //     messenger: { ... },
   //     ...
   //   }
   // }
   ```

### Тест 5: Переход в видеохостинг

1. **На портале кликните на карточку "Видеохостинг"**

2. **✅ Ожидается:**
   - Переход на `http://localhost:3000?access_token=...&refresh_token=...`
   - URL очищается (токены скрываются)
   - Видеохостинг открывается с авторизацией
   - Header показывает пользователя

3. **🔍 Проверка:**
   ```javascript
   // DevTools Console на localhost:3000
   localStorage.getItem('access_token')  // Токены скопированы из портала
   ```

4. **Попробуйте функции:**
   - Открыть список видео
   - Загрузить видео (кнопка Upload)
   - Открыть профиль

### Тест 6: Проверка ограничений is_employee

1. **Создайте пользователя БЕЗ флага is_employee:**
   ```sql
   INSERT INTO users (id, username, email, password_hash, is_employee)
   VALUES (gen_random_uuid(), 'external', 'external@test.com',
           '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS5cLPXKe', false);
   ```

2. **Попробуйте войти:**
   - Логин: `external`
   - Пароль: `admin123`

3. **✅ Ожидается:**
   - Ошибка: "Доступ разрешен только сотрудникам ДГИ"
   - Токены НЕ сохраняются
   - Редирект НЕ происходит

### Тест 7: Проверка RBAC (права доступа)

```powershell
# Назначить роль video:admin пользователю
docker exec -i infrastructure-docker-db-1 psql -U user -d video_hosting
```

```sql
-- Получить ID пользователя и роли
SELECT u.id as user_id, u.username,
       s.id as service_id, s.slug,
       sr.id as role_id, sr.name as role_name
FROM users u, services s, service_roles sr
WHERE u.username = 'admin_user'
  AND s.slug = 'video'
  AND sr.name = 'admin'
  AND sr.service_id = s.id;

-- Назначить роль
INSERT INTO user_service_roles (user_id, service_role_id)
VALUES (
  (SELECT id FROM users WHERE username = 'admin_user'),
  (SELECT sr.id FROM service_roles sr 
   JOIN services s ON sr.service_id = s.id
   WHERE s.slug = 'video' AND sr.name = 'admin')
);

-- Проверить назначение
SELECT u.username, s.slug as service, sr.name as role
FROM user_service_roles usr
JOIN users u ON usr.user_id = u.id
JOIN service_roles sr ON usr.service_role_id = sr.id
JOIN services s ON sr.service_id = s.id
WHERE u.username = 'admin_user';
```

**🔍 Проверка в токене:**
```javascript
// После повторного входа
const token = localStorage.getItem('access_token');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log(payload.services.video);
// Должно показать:
// { role: "admin", permissions: ["video:upload", "video:manage_all", ...] }
```

### Тест 8: Проверка работы refresh token

```javascript
// DevTools Console
async function testRefresh() {
  // 1. Удалить access_token (симулируем истечение)
  localStorage.removeItem('access_token');
  
  // 2. Сделать запрос (должен использовать refresh)
  const res = await fetch('http://localhost:8001/videos', {
    headers: { 
      Authorization: `Bearer ${localStorage.getItem('access_token')}` 
    }
  });
  
  // 3. Проверить - должен был обновиться
  console.log(localStorage.getItem('access_token')); // Новый токен
}

testRefresh();
```

### Тест 9: Проверка мониторинга

```
1. Prometheus: http://localhost:9090
   - Targets: http://localhost:9090/targets (все должны быть UP)

2. Grafana: http://localhost:3001
   - Логин: admin / admin
   - Должны быть преднастроенные дашборды

3. RabbitMQ: http://localhost:15672
   - Логин: guest / guest
   - Проверить queues

4. MinIO: http://localhost:9001
   - Логин: minioadmin / minioadmin
   - Bucket "videos" должен существовать
```

---

## 📊 Чеклист проверки

### ✅ Базовая инфраструктура
- [ ] Все контейнеры запущены (`docker compose ps`)
- [ ] Health checks проходят (все healthy)
- [ ] PostgreSQL доступна (psql подключается)
- [ ] Redis доступен (`redis-cli ping`)
- [ ] MinIO доступен (консоль открывается)
- [ ] Elasticsearch доступен (кластер healthy)

### ✅ Auth Service
- [ ] Эндпоинт /health отвечает 200
- [ ] POST /token работает (выдает токены)
- [ ] GET /users/me работает с токеном
- [ ] POST /refresh работает (обновляет токены)
- [ ] Проверка is_employee работает (external отклоняется)
- [ ] RBAC инициализирован (4 сервиса в БД)

### ✅ Portal
- [ ] Страница http://localhost:3002 открывается
- [ ] Страница /login открывается
- [ ] Форма авторизации работает
- [ ] После входа показываются 4 сервиса
- [ ] Клик по "Видеохостинг" переходит в frontend
- [ ] Header показывает пользователя
- [ ] Кнопка "Выйти" работает

### ✅ Video Frontend
- [ ] Страница http://localhost:3000 открывается
- [ ] Принимает токены из URL
- [ ] Токены сохраняются в localStorage
- [ ] API запросы работают с токеном
- [ ] Refresh token работает при 401
- [ ] Список видео загружается

### ✅ Единая авторизация
- [ ] Вход через портал
- [ ] Токены передаются в сервисы
- [ ] Токены работают во всех сервисах
- [ ] Logout на портале = logout везде
- [ ] Refresh работает автоматически

---

## 🐛 Типичные проблемы и решения

### Проблема 1: "Cannot connect to database"

```bash
# Проверить статус
docker compose ps db

# Проверить логи
docker compose logs db

# Решение:
# 1. Подождать 30 секунд (инициализация)
# 2. Перезапустить
docker compose restart db

# 3. Если не помогает, пересоздать
docker compose down -v
docker compose up -d
```

### Проблема 2: "401 Unauthorized" на портале

```javascript
// Проверить токены
localStorage.getItem('access_token')  // null?

// Решение:
// 1. Перелогиниться
// 2. Проверить auth-service работает
curl http://localhost:8000/health

// 3. Проверить CORS настройки в auth-service
```

### Проблема 3: Портал не переходит в видеохостинг

```javascript
// Проверить URL
// Должен быть: http://localhost:3000?access_token=...

// Если редирект не работает, проверьте:
// portal/src/app/page.tsx строка 250-263

// Временное решение:
// Открыть DevTools Console на портале
const token = localStorage.getItem('access_token');
const refresh = localStorage.getItem('refresh_token');
window.open(`http://localhost:3000?access_token=${token}&refresh_token=${refresh}`);
```

### Проблема 4: "Service unavailable" на frontend

```bash
# Проверить video-service
docker compose logs video-service

# Проверить URL в frontend
# frontend/.env.local должен иметь:
NEXT_PUBLIC_VIDEO_API_URL=http://localhost:8001
NEXT_PUBLIC_API_URL=http://localhost:8000

# Перезапустить frontend
docker compose restart frontend
```

### Проблема 5: Токены не работают в video-service

```javascript
// Проверить формат токена
const token = localStorage.getItem('access_token');
console.log(token); // Должен начинаться с "eyJ"

// Декодировать и проверить
const payload = JSON.parse(atob(token.split('.')[1]));
console.log(payload);
// Должно содержать:
// - sub: username
// - exp: timestamp (будущее время)
// - services: { video: {...}, ... }
// - is_employee: true

// Если exp в прошлом, нужен refresh:
const refresh = localStorage.getItem('refresh_token');
fetch('http://localhost:8000/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token: refresh })
})
.then(r => r.json())
.then(data => {
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
});
```

---

## 🚀 Следующие шаги

### Краткосрочные (для dev)

1. ✅ **Протестировать текущую систему** (используя чеклист выше)
2. ✅ **Создать тестовых пользователей** для каждой роли
3. ✅ **Проверить RBAC** - назначить роли для всех 4 сервисов
4. ⚠️ **Исправить передачу токенов** через URL → использовать localStorage/cookies

### Среднесрочные (интеграция команды)

1. 🔌 **Интегрировать Мессенджер:**
   - Добавить CORS для messenger
   - Реализовать прием токенов
   - Проверить права `messenger:send`, `messenger:read`
   
2. 🔌 **Интегрировать Дашборд:**
   - Добавить CORS для dashboard
   - Реализовать прием токенов
   - Проверить права `dashboard:view_all`
   
3. 🔌 **Интегрировать Техподдержку:**
   - Добавить CORS для support
   - Реализовать прием токенов
   - Проверить права `support:create_ticket`

### Долгосрочные (production)

1. 🔐 **Безопасность:**
   - Использовать HTTPS (Let's Encrypt)
   - Использовать httpOnly cookies вместо localStorage
   - Включить LDAP интеграцию (Active Directory ДГИ)
   - Настроить rate limiting
   
2. 🏗️ **Масштабирование:**
   - Kubernetes вместо Docker Compose
   - Несколько инстансов каждого сервиса
   - Load balancer (Nginx → HAProxy/Traefik)
   - CDN для статики
   
3. 📊 **Мониторинг:**
   - Настроить алерты в Grafana
   - Логирование (ELK Stack)
   - APM (Application Performance Monitoring)
   - Backup базы данных

---

## 📚 Полезные ссылки

### Документация проекта
- `README.md` - Быстрый старт
- `ARCHITECTURE.md` - Архитектура системы
- `DEPLOYMENT_GUIDE.md` - Инструкция по деплою
- `docs/FRONTEND_BACKEND_INTEGRATION.md` - API интеграция

### API документация (Swagger)
- Auth: http://localhost:8000/docs
- Video: http://localhost:8001/docs
- Streaming: http://localhost:8002/docs
- Notification: http://localhost:8003/docs
- Search: http://localhost:8004/docs

### Инструменты
- PostgreSQL: `psql -h localhost -U user -d video_hosting`
- Redis: `redis-cli -h localhost`
- MinIO Console: http://localhost:9001
- RabbitMQ Management: http://localhost:15672
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## 🎓 Заключение

**Ваша система УЖЕ имеет единую авторизацию!** ✅

Основные преимущества текущей реализации:

1. ✅ **Централизованный auth-service** - все проверки в одном месте
2. ✅ **JWT с RBAC** - токены содержат права для всех сервисов
3. ✅ **Portal как единая точка входа** - пользователи начинают здесь
4. ✅ **Multi-service architecture** - готовность к 4+ сервисам
5. ✅ **LDAP ready** - можно подключить Active Directory
6. ✅ **Refresh tokens** - автоматическое обновление
7. ✅ **Employee check** - доступ только для сотрудников ДГИ

Что нужно улучшить:

1. ⚠️ **Заменить передачу токенов через URL** на cookies (production)
2. ⚠️ **Скрыть регистрацию** (оставить для тестов)
3. 🔧 **Добавить CORS** для новых сервисов команды
4. 🔧 **Интегрировать 3 сервиса** (мессенджер, дашборд, техподдержка)

**Следуйте чеклистам выше для тестирования!** 🚀
