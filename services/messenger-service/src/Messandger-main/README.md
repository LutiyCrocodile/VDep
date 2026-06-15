# Messandger — Корпоративный мессенджер ДГИ

Современный мессенджер для внутреннего общения с поддержкой групповых чатов, каналов, голосовых и видеозвонков, опросов, запланированных сообщений и медиа-галерей.

## Возможности

### Общение
- **Личные чаты** и **групповые чаты** с ролями (owner, admin, member, readonly)
- **Новостные каналы** (read-only для подписчиков)
- **Избранное** — сохранение сообщений в личный чат
- **Ответ на сообщения** с кликабельной ссылкой на оригинал
- **Пересылка сообщений** между чатами
- **Копирование текста сообщений** в буфер обмена
- **Удаление сообщений** (soft/hard delete в зависимости от настроек чата)
- **Реакции** эмодзи

### Медиа и файлы
- **Загрузка файлов** (изображения, видео, аудио, документы)
- **Голосовые сообщения** с визуализацией волны
- **Редактор изображений** перед отправкой
- **Медиа-галерея** в чате (Фото / Видео / Файлы / Музыка / Ссылки)
- **Lightbox** — просмотр фото внутри приложения (не в новой вкладке)
- **Контроль скачивания** — отправитель может запретить скачивание вложений

### Опросы
- Создание опросов с вариантами ответов
- Анонимные и публичные опросы
- Мультивыбор (несколько вариантов)
- Закрытие опросов по времени

### Запланированные сообщения
- Отложенная отправка сообщений по расписанию
- Указание даты и времени отправки
- Отображение реальной даты отправки в чате

### Звонки
- **Аудиозвонки** через WebRTC
- **Видеозвонки** через WebRTC
- Входящие/исходящие звонки
- Управление участниками звонка

### Присутствие
- **Онлайн-статус** пользователей (зелёная точка на аватаре)
- **«Был(а) недавно»** с относительным временем
- **Индикатор «печатает»** (без показа самому себе)

### Поиск
- Поиск по сообщениям в чате
- Поиск пользователей по имени, email, должности

### Темы оформления
- **Тёмная тема** (по умолчанию)
- **Светлая тема** с сохранением выбора в localStorage

### Безопасность и управление
- JWT-авторизация
- Ролевая модель (user, head, deputy_head, admin, super_admin)
- Двухфакторная настройка пароля (срок действия 90 дней)
- Замораживание и блокировка аккаунтов
- Запросы на доступ
- Логирование и уведомления

## Стек технологий

### Backend
- **Python 3.11+**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** (async) — ORM
- **SQLite** — база данных
- **WebSockets** — real-time события
- **PyJWT** — токены авторизации
- **python-dateutil** — работа с датами

### Frontend
- **React 18**
- **Vite** — сборщик
- **Zustand** — state management
- **Tailwind CSS** — стили
- **Lucide Icons** — иконки
- **emoji-picker-react** — эмодзи-клавиатура
- **react-hot-toast** — уведомления
- **WebRTC** — звонки

## Установка и запуск

### Требования
- Python 3.11+
- Node.js 18+
- npm или yarn

### Backend

```bash
cd backend

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # на Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Инициализация БД
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"

# Запуск
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск dev-сервера
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`

## Конфигурация

### Backend (.env)

```env
DATABASE_URL=sqlite+aiosqlite:///./messenger.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=./uploads
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

## Структура проекта

```
windsurf-project/
├── backend/
│   ├── app/
│   │   ├── main.py           # Точка входа, worker запланированных сообщений
│   │   ├── config.py         # Конфигурация
│   │   ├── database.py       # База данных и миграции
│   │   ├── models/           # SQLAlchemy модели
│   │   │   ├── user.py
│   │   │   ├── chat.py
│   │   │   └── message.py
│   │   ├── routers/          # API эндпойнты
│   │   │   ├── auth.py       # Авторизация, пользователи
│   │   │   ├── chats.py      # Чаты, сообщения, медиа
│   │   │   ├── calls.py      # Звонки
│   │   │   └── websocket.py  # WebSocket события
│   │   └── services/
│   │       └── auth.py       # JWT логика
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React компоненты
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── Lightbox.jsx
│   │   │   ├── MediaGalleryModal.jsx
│   │   │   └── ...
│   │   ├── store/            # Zustand stores
│   │   │   ├── authStore.js
│   │   │   ├── chatStore.js
│   │   │   ├── websocketStore.js
│   │   │   ├── themeStore.js
│   │   │   ├── presenceStore.js
│   │   │   └── lightboxStore.js
│   │   ├── pages/            # Страницы
│   │   │   ├── LoginPage.jsx
│   │   │   ├── MessengerPage.jsx
│   │   │   └── ...
│   │   ├── api/
│   │   │   └── axios.js       # Axios клиент
│   │   └── main.jsx          # Точка входа
│   ├── index.css
│   ├── tailwind.config.js
│   └── package.json
└── README.md
```

## API Эндпойнты

### Авторизация
- `POST /api/auth/register` — регистрация
- `POST /api/auth/login` — вход
- `GET /api/auth/me` — текущий пользователь
- `GET /api/auth/users?q=...` — поиск пользователей
- `GET /api/auth/users/{id}/presence` — статус онлайн

### Чаты
- `GET /api/chats/` — список чатов
- `POST /api/chats/` — создание чата
- `GET /api/chats/{id}/messages` — сообщения чата
- `POST /api/chats/{id}/messages` — отправка сообщения
- `PUT /api/chats/{id}/messages/{msg_id}` — редактирование
- `DELETE /api/chats/{id}/messages/{msg_id}` — удаление
- `POST /api/chats/{id}/upload` — загрузка файла
- `GET /api/chats/{id}/messages/search?q=...` — поиск
- `GET /api/chats/{id}/media?kind=...` — медиа-галерея
- `POST /api/chats/{id}/messages/{msg_id}/forward` — пересылка
- `POST /api/chats/{id}/read` — отметка о прочтении
- `POST /api/chats/{id}/messages/{msg_id}/reactions` — реакции
- `GET /api/chats/{id}/messages/scheduled` — запланированные
- `POST /api/chats/{id}/messages/schedule` — планирование
- `DELETE /api/chats/{id}/messages/scheduled/{msg_id}` — отмена

### Звонки
- `POST /api/calls/` — создание звонка
- `POST /api/calls/{id}/accept` — принятие
- `POST /api/calls/{id}/reject` — отклонение
- `POST /api/calls/{id}/end` — завершение

### WebSocket
- `ws://host/ws?token=...` — подключение

События:
- `new_message` — новое сообщение
- `typing` / `stop_typing` — индикатор печати
- `read` — прочтение
- `presence` — онлайн-статус
- `call_invite` / `call_accept` / `call_reject` / `call_end` — звонки
- `message_deleted` — удаление сообщения
- `notification` — системные уведомления

## Лицензия

Внутренний проект ДГИ. Все права защищены.
