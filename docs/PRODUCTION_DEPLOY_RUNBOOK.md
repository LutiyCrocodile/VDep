# Runbook: пошаговый деплой на продакшен-сервер

Этот документ описывает процесс так, как его можно выполнить **вручную на чистом Linux-сервере** (Ubuntu 22.04 LTS в примерах). Команды даны построчно с пояснением, что делает каждая. Адаптируйте имена пользователей, домены и пути под свою инфраструктуру.

**Предположения:**

- Репозиторий: `video.dgi.mos.ru` (или ваш fork).
- На сервере будет Docker Engine + Docker Compose V2 (`docker compose`, не устаревший `docker-compose`).
- Доступ по SSH под пользователем с правами `sudo` (или под `root`).
- Один сервер для первого выката (все сервисы из `infrastructure/docker/docker-compose.yml` на одной машине). Масштабирование и отдельные ноды — вне scope этого runbook.

**Путь клона (например `portal-dgim/video.dgi.mos.ru`):** не важно, как называется родительская папка (`portal-dgim` и т.д.). Важно сохранить структуру репозитория: из каталога `.../video.dgi.mos.ru/infrastructure/docker` относительные пути `../../services/*`, `../../frontend`, `../../portal` должны указывать на реальные каталоги внутри того же клона. Команды запуска выполняйте из `infrastructure/docker` (или укажите полный `-f` путь к файлу).

**Имя проекта Compose:** в `docker-compose.yml` задано `name: ${COMPOSE_PROJECT_NAME:-video_dgim_mos}`. Задайте уникальный `COMPOSE_PROJECT_NAME` в `infrastructure/docker/.env` на каждом сервере/копии, иначе при двух стеках с одинаковым имени проекта Docker переиспользует или конфликтует по именованным томам.

**Шаблоны переменных:** для Docker — `infrastructure/docker/.env.example` скопируйте в `infrastructure/docker/.env`. Для локального Next на хосте (UI без Docker): `frontend/.env.example` и `portal/.env.example` → `.env.local` в соответствующих каталогах.

---

## Часть 0. Локальная подготовка (опционально, перед выходом на сервер)

Цель: убедиться, что образы собираются, не коммитить секреты.

```bash
cd /path/to/video.dgi.mos.ru
```

- **`cd`** — перейти в корень клона репозитория на вашей рабочей машине.

```bash
git status
```

- **`git status`** — проверить, что рабочее дерево чистое или осознанно содержит нужные изменения перед деплоем.

```bash
docker compose -f infrastructure/docker/docker-compose.yml config
```

- **`docker compose … config`** — валидировать YAML compose и подставить переменные из `.env` (если файл есть рядом с compose или указан через `--env-file`). Ошибки синтаксиса или неизвестные ключи проявятся здесь.

На сервер эти шаги повторять не обязательно, но полезно один раз прогнать локально.

---

## Часть 1. Первый вход на сервер и базовая ОС

### 1.1 Подключение по SSH

```bash
ssh -i ~/.ssh/id_ed25519 deploy@203.0.113.10
```

- **`ssh`** — клиент Secure Shell.
- **`-i ~/.ssh/id_ed25519`** — приватный ключ аутентификации (путь замените на свой).
- **`deploy@203.0.113.10`** — пользователь на сервере и IP или hostname (замените на реальные).

После входа вы в домашнем каталоге пользователя `deploy` (обычно `/home/deploy`).

### 1.2 Обновление индекса пакетов и установка зависимостей (Ubuntu)

```bash
sudo apt-get update
```

- **`sudo`** — выполнить команду от имени суперпользователя.
- **`apt-get update`** — обновить списки пакетов из репозиториев.

```bash
sudo apt-get install -y ca-certificates curl git ufw
```

- **`apt-get install -y`** — установить пакеты без интерактивных вопросов (`-y`).
- **`ca-certificates`** — корневые сертификаты для HTTPS.
- **`curl`** — HTTP-клиент для health-check и загрузок.
- **`git`** — клонирование репозитория.
- **`ufw`** — простой фаервол (опционально, но рекомендуется).

### 1.3 Установка Docker (официальный скрипт Docker — один из вариантов)

```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
```

- **`curl -fsSL`** — скачать скрипт: следовать редиректам (`-L`), тихий режим (`-s`), сбой при HTTP-ошибке (`-f`).
- **`-o /tmp/get-docker.sh`** — сохранить в файл.

```bash
sudo sh /tmp/get-docker.sh
```

- Запускает установку Docker Engine и плагина Compose (в зависимости от версии скрипта).

```bash
sudo usermod -aG docker deploy
```

- **`usermod -aG docker deploy`** — добавить пользователя `deploy` в группу `docker`, чтобы не вызывать `sudo docker` каждый раз. **Выйдите из SSH и зайдите снова**, чтобы группа применилась.

Проверка:

```bash
docker --version
docker compose version
```

- Убедиться, что установлены Docker и Compose V2.

---

## Часть 2. Каталог приложения и клон репозитория

### 2.1 Создание каталога под приложение

```bash
sudo mkdir -p /opt/video.dgi.mos.ru
```

- **`mkdir -p`** — создать каталог `/opt/video.dgi.mos.ru` и родительские при необходимости.

```bash
sudo chown deploy:deploy /opt/video.dgi.mos.ru
```

- **`chown`** — владелец каталога — пользователь `deploy`, чтобы не править код только через `sudo`.

```bash
cd /opt/video.dgi.mos.ru
```

### 2.2 Клонирование (HTTPS; для приватного репозитория используйте SSH URL или deploy key)

```bash
git clone https://github.com/ORG/video.dgi.mos.ru.git app
```

- **`git clone … app`** — клонировать в подкаталог `app`. Замените URL на ваш.

```bash
cd app
```

- Дальнейшие команды выполняются из **корня репозитория** (`…/app`).

```bash
git checkout main
```

- Переключиться на ветку, которую деплоите (часто `main` или `release/x.y`).

```bash
git pull --ff-only
```

- Подтянуть последние коммиты без merge-коммитов (`--ff-only` падает, если нужен merge — тогда разбирать вручную).

---

## Часть 3. Файл окружения и секреты

### 3.1 Копия примера env для Docker

```bash
cp infrastructure/docker/.env.example infrastructure/docker/.env
```

- **`cp`** — скопировать шаблон в рабочий файл `.env`, который **не должен** попадать в git (убедитесь, что `infrastructure/docker/.env` в `.gitignore`).

### 3.2 Генерация случайных секретов (пример через OpenSSL)

```bash
openssl rand -hex 32
```

- Вывести 32 байта в hex — подойдёт для `SECRET_KEY` или `INTERNAL_AUTH_TOKEN`. Скопируйте вывод в буфер обмена.

Повторите команду второй раз для другого секрета (не используйте один и тот же ключ для JWT и для internal token).

Отредактируйте файл:

```bash
nano infrastructure/docker/.env
```

или

```bash
vi infrastructure/docker/.env
```

**Обязательно задайте (минимум):**

| Переменная | Смысл |
|------------|--------|
| `POSTGRES_PASSWORD` | Пароль пользователя БД PostgreSQL. |
| `SECRET_KEY` | Подпись JWT в auth-service. |
| `INTERNAL_AUTH_TOKEN` | Общий секрет для вызовов `/internal/...` между сервисами. |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Ключи MinIO (не оставляйте `minioadmin` в проде). |
| `MINIO_EXTERNAL_ENDPOINT` | Хост:порт или полный URL, с которого **браузер** достучится до MinIO (например `storage.example.ru` или `https://s3.example.ru`). |
| `CORS_ORIGINS` | Список через запятую: `https://video.example.ru,https://portal.example.ru` — origin фронтов для auth-service. |
| `PUBLIC_HLS_BASE` | Базовый URL HLS для клиента (например `https://video.example.ru/hls` или прямой URL до MediaMTX за nginx). |
| `PUBLIC_RTMP_HOST` | Имя хоста для строки RTMP в OBS (часто тот же публичный хост). |

Строка `DATABASE_URL` в примере должна **совпадать** с `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` и именем сервиса `db` в compose (по умолчанию `postgresql+asyncpg://user:PASSWORD@db:5432/video_hosting` — подставьте свой пароль).

Сохраните файл и выйдите из редактора.

### 3.3 Права на `.env`

```bash
chmod 600 infrastructure/docker/.env
```

- Только владелец может читать/писать файл с секретами.

---

## Часть 4. Сборка и запуск стека

Все команды из корня репозитория (`/opt/video.dgi.mos.ru/app`).

### 4.1 Проверка конфигурации compose

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml config > /tmp/compose-resolved.yml
```

- Явно указать **`--env-file`**, чтобы подтянуть переменные из вашего `.env`.
- **`config`** выводит итоговую конфигурацию; перенаправление в **`/tmp/compose-resolved.yml`** позволяет просмотреть полный результат без прокрутки терминала.

```bash
less /tmp/compose-resolved.yml
```

- Просмотр; **`q`** — выход.

### 4.2 Сборка образов и запуск в фоне

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml build
```

- **`build`** — собрать все образы с директивой `build:` в compose. Первый раз может занять много времени.

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml up -d
```

- **`up -d`** — создать сеть, тома, контейнеры и запустить их в detached-режиме.

### 4.3 Просмотр состояния

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml ps
```

- Список сервисов и статусов портов.

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml logs -f --tail=100 auth-service
```

- **`logs -f`** — поток логов; **`--tail=100`** — последние 100 строк. Останов: **Ctrl+C** (контейнеры не останавливаются).

---

## Часть 5. Инициализация базы данных

Если у вас **первый** запуск с пустым томом `postgres_data`, таблицы часто создаются при старте сервисов (`create_tables`). Для **явного** наполнения тестовыми данными (только для стенда, не для боя с реальными людьми):

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml ps -q db
```

- Получить ID контейнера БД (короткий идентификатор). Удобнее по имени:

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml exec -T db psql -U user -d video_hosting -c "SELECT 1"
```

- **`exec -T`** — выполнить команду внутри контейнера без TTY; **`psql … -c "SELECT 1"`** — проверка подключения к БД `video_hosting` пользователем `user` (замените при смене имён в `.env`).

Прогон миграций/сида (пример — только если вы осознанно применяете SQL из репозитория):

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml exec -T db \
  psql -U user -d video_hosting < database/seed_data.sql
```

- **`< database/seed_data.sql`** — подать файл на stdin `psql` (в bash). **В PowerShell на Windows** этот синтаксис другой; на сервере Linux — как выше.

**На продакшене с реальными пользователями** не используйте сид с паролем `admin123`. См. [Часть 9](#часть-9-после-запуска-очистка-тестовых-учётных-записей).

---

## Часть 6. Проверка health с сервера

Подставьте localhost, если порты проброены на хост (как в текущем compose), или используйте `docker compose exec` + `curl` внутри сети.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health
```

- **`curl -sS`** — тихий режим, но показывать ошибки; **`-o /dev/null`** — не печатать тело; **`-w "%{http_code}\n"`** — напечатать только HTTP-код. Ожидается `200` для auth.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/health
```

- video-service.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8002/health
```

- streaming-service.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8004/health
```

- search-service (если поднят).

---

## Часть 7. Nginx и TLS (обязательно для публичного HTTPS)

Файл **`infrastructure/docker/nginx.conf`** в репозитории — ориентир. На боевом сервере nginx часто ставят **на хосте** или отдельным контейнером (в compose уже есть сервис `nginx` — можно доработать под ваши домены).

### 7.1 Установка nginx и Certbot (пример)

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 7.2 Получение сертификата Let’s Encrypt (пример для одного домена)

```bash
sudo certbot --nginx -d video.example.ru --non-interactive --agree-tos -m admin@example.ru
```

- Замените домен и email. Нужны открытые **80/443** и DNS A-запись на этот сервер.

Дальше в конфиге nginx:

- Проксировать пути к **auth**, **video**, **streaming** согласно вашей схеме URL (см. `DEPLOY_GUIDE.md` в репозитории).
- Для **HLS** (MediaMTX `:8888`) — либо отдельный `location`, либо поддомен `hls.example.ru`.
- Для **RTMP** (порт **1935**) — отдельный listener или другой сервер; TLS для RTMP настраивается иначе, чем для HTTPS.

Проверка синтаксиса nginx:

```bash
sudo nginx -t
```

```bash
sudo systemctl reload nginx
```

---

## Часть 8. Сборка фронтендов с продакшен-переменными

Переменные **`NEXT_PUBLIC_*`** встраиваются в клиентский бандл на этапе **`next build`**. Если вы собираете образы Docker для `frontend` и `portal`, передайте build-args в `Dockerfile` или задайте `ARG`/`ENV` в CI перед `npm run build`.

Пример локальной сборки образа фронта с переопределением (синтаксис зависит от вашего Dockerfile):

```bash
cd /opt/video.dgi.mos.ru/app/frontend
```

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.ru \
  --build-arg NEXT_PUBLIC_VIDEO_API_URL=https://api.example.ru/video \
  --build-arg NEXT_PUBLIC_STREAMING_API_URL=https://api.example.ru/streaming \
  --build-arg NEXT_PUBLIC_HLS_PUBLIC_BASE=https://hls.example.ru \
  --build-arg NEXT_PUBLIC_RTMP_HOST=rtmp.example.ru \
  --build-arg NEXT_PUBLIC_PORTAL_URL=https://portal.example.ru \
  -t video-frontend:prod \
  -f Dockerfile .
```

- Каждый **`--build-arg`** задаёт одну публичную переменную; URL должны совпадать с тем, что реально отдаёт nginx.

Если ваш `Dockerfile` не принимает эти args, сначала обновите Dockerfile или используйте `environment` в compose для **dev**; для **prod** надёжнее build-args + build stage.

После правок:

```bash
cd /opt/video.dgi.mos.ru/app
```

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml up -d --build frontend portal
```

- Пересобрать и перезапустить только указанные сервисы.

---

## Часть 9. После запуска: очистка тестовых учётных записей

Когда проектом начнут пользоваться реальные люди:

1. Отключите публичную регистрацию: в `.env` должно быть `ALLOW_REGISTRATION=false` (и перезапуск auth-service).

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml up -d --force-recreate auth-service
```

2. Смените или удалите тестовых пользователей из сида (`admin`, `employee`, и т.д.). Пример: сгенерировать bcrypt для нового пароля отдельной утилитой, затем:

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml exec -T db \
  psql -U user -d video_hosting -c "UPDATE users SET password_hash = 'NEW_BCRYPT_HASH' WHERE username = 'admin';"
```

- **`UPDATE`** — только при наличии резервной копии и понимании последствий.

3. Удаление тестовых пользователей (жёстко):

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml exec -T db \
  psql -U user -d video_hosting -c "DELETE FROM user_service_roles WHERE user_id IN (SELECT id FROM users WHERE username IN ('admin','employee'));"
```

- Сначала удалить зависимости, затем строки в `users` — порядок FK зависит от вашей схемы; при неуверенности делайте бэкап и правьте в транзакции.

4. Смените пароль Grafana (переменная `GF_SECURITY_ADMIN_PASSWORD` в compose или отдельный secret).

---

## Часть 10. Обновление версии (rolling)

```bash
cd /opt/video.dgi.mos.ru/app
```

```bash
git fetch origin
```

```bash
git checkout main && git pull --ff-only
```

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml build
```

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml up -d
```

- Compose пересоздаст контейнеры, у которых изменился образ или переменные.

---

## Часть 11. Резервное копирование (минимум перед миграциями)

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml exec -T db \
  pg_dump -U user video_hosting | gzip > ~/backup-video_hosting-$(date +%F).sql.gz
```

- **`pg_dump`** — логический дамп БД; **`gzip`** — сжатие; имя файла с датой.

Тома MinIO и записей эфиров — копировать содержимое named volumes (отдельная процедура, зависит от вашей политики хранения).

---

## Часть 12. Откат (coarse)

```bash
cd /opt/video.dgi.mos.ru/app
```

```bash
git checkout <previous_commit_sha>
```

```bash
docker compose --env-file infrastructure/docker/.env -f infrastructure/docker/docker-compose.yml up -d --build
```

---

## Краткий чеклист перед объявлением «прод готов»

- [ ] Все секреты вынесены в `infrastructure/docker/.env`, файл не в git, права `600`.
- [ ] `SECRET_KEY`, `INTERNAL_AUTH_TOKEN`, пароли БД/MinIO/RabbitMQ не дефолтные.
- [ ] `MINIO_EXTERNAL_ENDPOINT`, `PUBLIC_HLS_BASE`, `PUBLIC_RTMP_HOST`, `CORS_ORIGINS` соответствуют публичным URL.
- [ ] Фронты собраны с корректными `NEXT_PUBLIC_*` и `NEXT_PUBLIC_PORTAL_URL`.
- [ ] HTTPS на nginx, редирект HTTP→HTTPS.
- [ ] Health 200 на ключевых сервисах; smoke: логин, список видео, эфир.
- [ ] План удаления/смены тестовых паролей из сида выполнен или запланирован.

---

*Документ отражает состояние репозитория на момент написания. При изменении `docker-compose.yml` или портов обновите команды и переменные соответственно.*
