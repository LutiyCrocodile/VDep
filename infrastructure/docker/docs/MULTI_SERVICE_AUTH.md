# Multi-Service Authentication Architecture

## Overview

4 микросервиса ДГИ используют общую систему авторизации:
1. **video** - Видеохостинг (текущий проект)
2. **messenger** - Мессенджер
3. **dashboard** - Аналитический дашборд
4. **support** - Техническая поддержка

## Architecture

### Database Schema

```sql
users                    -- Общая таблица пользователей
├── id, username, email
├── password_hash
└── is_active

services                 -- Регистрация сервисов
├── slug: 'video', 'messenger', 'dashboard', 'support'
├── name, description
└── is_active

service_roles            -- Роли внутри каждого сервиса
├── service_id -> services.id
├── name: 'admin', 'user', 'viewer'
└── is_active

service_permissions      -- Разрешения внутри сервиса
├── service_id -> services.id
└── name: 'video:upload', 'messenger:delete'

user_service_roles       -- Назначение ролей пользователям
├── user_id -> users.id
└── service_role_id -> service_roles.id
```

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@dgi.mos.ru",
  "services": {
    "video": {
      "role": "admin",
      "perms": ["upload", "delete", "moderate"]
    },
    "messenger": {
      "role": "user",
      "perms": ["read", "write"]
    }
  },
  "type": "access",
  "exp": 1234567890
}
```

## Modes

### Dev Mode (Standalone)
```bash
AUTH_MODE=standalone
```
- Каждый сервис имеет свой auth-service
- Полная независимость для разработки
- Порт 5432 открыт для pgAdmin

### Prod Mode (Shared)
```bash
AUTH_MODE=shared
SHARED_AUTH_URL=http://auth-service:8000
```
- Один auth-service для всех
- JWT содержит права для всех сервисов
- Порты закрыты, внутренняя сеть Docker

## Internal API Endpoints

### Auth Service
```
GET /internal/users/{user_id}/services/{service_slug}
  → Проверить доступ пользователя к сервису

GET /internal/services/{service_slug}/users
  → Список пользователей сервиса

GET /internal/users/{user_id}/permissions
  → Права пользователя (legacy)
```

## SDK Usage (video-service)

```python
from src.auth_client import auth_client

# Проверить токен
user = await auth_client.verify_token(token)

# Проверить право
has_perm = await auth_client.check_permission(user_id, "video:upload")

# Получить права для этого сервиса
perms = await auth_client.get_user_service_permissions(user_id)
# → { "role": "admin", "permissions": ["upload", "delete"] }
```

## Migration Guide: Dev → Prod

### 1. Database
```bash
# Prod: Убрать порт 5432 из docker-compose.yml
# В dev оставить для pgAdmin
```

### 2. Environment
```bash
# Скопировать и заполнить (из каталога infrastructure/docker)
cp .env.example .env

# Генерация секретов:
openssl rand -hex 32  # SECRET_KEY
uuidgen               # INTERNAL_AUTH_TOKEN
```

### 3. Auth Service
```bash
# Prod: AUTH_MODE=shared
# Dev:  AUTH_MODE=standalone
```

### 4. Security Checklist
- [ ] Поменять все пароли
- [ ] Закрыть порты 5432, 9000, 9001
- [ ] Включить HTTPS
- [ ] Настроить LDAP
- [ ] Rate limiting на nginx

## Service Integration

Для добавления нового сервиса:

1. Добавить в `initialize_services()`:
```python
{"slug": "newservice", "name": "Новый Сервис ДГИ"}
```

2. Создать роли в базе данных

3. Назначить пользователям через API

4. Использовать SDK клиент
