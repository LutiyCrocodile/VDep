#!/usr/bin/env python3
"""
Скрипт для загрузки тестового видео в систему.
Использование: python upload_test_video.py <путь_к_видео> [заголовок] [описание]
"""

import sys
import os
import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

# Конфигурация
AUTH_SERVICE_URL = "http://localhost:8000"
VIDEO_SERVICE_URL = "http://localhost:8001"
AUTH_CREDENTIALS = {
    "username": "testuser",
    "password": "password"
}

def make_request(url, data=None, headers=None, method="GET"):
    """Выполнение HTTP запроса"""
    req = Request(url, data=data, method=method)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    
    try:
        # Отключаем SSL verification для localhost
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with urlopen(req, context=context, timeout=30) as response:
            return response.status, response.read().decode()
    except HTTPError as e:
        return e.code, e.read().decode()
    except URLError as e:
        return 0, str(e.reason)

def get_token():
    """Получение JWT токена"""
    data = urlencode(AUTH_CREDENTIALS).encode()
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    status, response = make_request(
        f"{AUTH_SERVICE_URL}/token",
        data=data,
        headers=headers,
        method="POST"
    )
    
    if status == 200:
        result = json.loads(response)
        return result.get("access_token")
    else:
        print(f"❌ Ошибка авторизации: {status}")
        print(f"Ответ: {response}")
        print("Пытаемся создать пользователя...")
        return None

def create_user():
    """Создание тестового пользователя"""
    user_data = {
        "username": AUTH_CREDENTIALS["username"],
        "email": "test@test.com",
        "password": AUTH_CREDENTIALS["password"]
    }
    
    data = json.dumps(user_data).encode()
    headers = {'Content-Type': 'application/json'}
    
    status, response = make_request(
        f"{AUTH_SERVICE_URL}/register",
        data=data,
        headers=headers,
        method="POST"
    )
    
    if status in [200, 201]:
        print("✅ Пользователь создан")
        return True
    elif status == 400 and "already" in response.lower():
        print("ℹ️ Пользователь уже существует")
        return True
    else:
        print(f"❌ Ошибка создания пользователя: {status}")
        print(f"Ответ: {response}")
        return False

def upload_video(video_path, title, description=""):
    """Загрузка видео с использованием curl"""
    import subprocess
    
    token = get_token()
    if not token:
        if not create_user():
            return False
        token = get_token()
        if not token:
            print("❌ Не удалось получить токен после создания пользователя")
            return False
    
    print(f"📤 Загрузка видео: {title}")
    print(f"📁 Файл: {video_path}")
    
    # Используем curl для multipart/form-data загрузки
    try:
        curl_cmd = [
            "curl", "-X", "POST",
            f"{VIDEO_SERVICE_URL}/upload",
            "-H", f"Authorization: Bearer {token}",
            "-F", f"file=@{video_path}",
            "-F", f"title={title}",
            "-F", f"description={description}",
            "-F", "is_public=true",
            "-s", "-w", "\nHTTP_CODE: %{http_code}",
            "--connect-timeout", "30",
            "-m", "120"
        ]
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=150)
        output = result.stdout
        
        # Получаем HTTP код
        if "HTTP_CODE:" in output:
            code_line = [line for line in output.split('\n') if line.startswith('HTTP_CODE:')][-1]
            http_code = int(code_line.replace('HTTP_CODE:', '').strip())
            
            if http_code in [200, 201]:
                print(f"✅ Видео успешно загружено! (HTTP {http_code})")
                # Попытаемся получить ID из ответа
                json_part = output.split('\nHTTP_CODE:')[0].strip()
                if json_part:
                    try:
                        result = json.loads(json_part)
                        print(f"🎬 ID: {result.get('id')}")
                        print(f"🔗 URL: http://localhost:3001/watch?v={result.get('id')}")
                    except:
                        pass
                return True
            else:
                print(f"❌ Ошибка загрузки: HTTP {http_code}")
                print(f"Ответ: {output}")
                return False
        else:
            print(f"❌ Ошибка: {output}")
            return False
            
    except FileNotFoundError:
        print("❌ curl не найден. Попытка через Python...")
        return upload_video_python(video_path, title, description, token)
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при загрузке")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def upload_video_python(video_path, title, description, token):
    """Загрузка видео через Python без curl"""
    import mimetypes
    
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    
    # Читаем файл
    with open(video_path, 'rb') as f:
        file_content = f.read()
    
    # Создаем multipart данные
    body = []
    
    # Поле title
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="title"'.encode())
    body.append(b'')
    body.append(title.encode())
    
    # Поле description
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="description"'.encode())
    body.append(b'')
    body.append(description.encode())
    
    # Поле is_public
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="is_public"'.encode())
    body.append(b'')
    body.append(b'true')
    
    # Поле file
    filename = Path(video_path).name
    content_type = mimetypes.guess_type(video_path)[0] or 'video/mp4'
    
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
    body.append(f'Content-Type: {content_type}'.encode())
    body.append(b'')
    body.append(file_content)
    
    body.append(f'--{boundary}--'.encode())
    
    data = b'\r\n'.join(body)
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }
    
    status, response = make_request(
        f"{VIDEO_SERVICE_URL}/upload",
        data=data,
        headers=headers,
        method="POST"
    )
    
    if status in [200, 201]:
        print(f"✅ Видео успешно загружено! (HTTP {status})")
        try:
            result = json.loads(response)
            print(f"🎬 ID: {result.get('id')}")
            print(f"🔗 URL: http://localhost:3001/watch?v={result.get('id')}")
        except:
            pass
        return True
    else:
        print(f"❌ Ошибка загрузки: HTTP {status}")
        print(f"Ответ: {response}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Использование: python upload_test_video.py <путь_к_видео> [заголовок] [описание]")
        print("Пример: python upload_test_video.py test.mp4 'Мое видео' 'Описание видео'")
        sys.exit(1)
    
    video_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else Path(video_path).stem
    description = sys.argv[3] if len(sys.argv) > 3 else "Тестовое видео загружено автоматически"
    
    print("=" * 50)
    print("🎬 Загрузка тестового видео")
    print("=" * 50)
    
    success = upload_video(video_path, title, description)
    
    if success:
        print("\n✅ Готово! Видео доступно в системе.")
    else:
        print("\n❌ Загрузка не удалась.")
        sys.exit(1)

if __name__ == "__main__":
    main()
