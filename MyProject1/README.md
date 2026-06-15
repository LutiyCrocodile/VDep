# Интерактивная система визуализации отчётов ДГИ

## Технологии
- Python 3.11 + Django 5.2
- React 19 + Vite
- MySQL 8.0

## Установка и запуск

### 1. Клонировать проект
git clone <url> .

### 2. Бэкенд (Django)
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Настроить БД в config/settings.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

### 3. Фронтенд (React)
cd frontend/dgi-frontend
npm install
npm run dev

### 4. Открыть в браузере
http://localhost:5173

## Структура проекта
- backend/ — Django (API, модели, сервисы)
- frontend/dgi-frontend/ — React (интерфейс)