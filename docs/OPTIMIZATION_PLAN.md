# План оптимизации

**Цель:** микросервисный видеохостинг; **auth-service** — соприкосновение сервисов; **portal** — вход пользователя. Монолит не рассматривается.

Подробный чеклист регрессии: [OPTIMIZATION_CHECKLIST.md](./OPTIMIZATION_CHECKLIST.md)  
Обмен сообщениями: [MESSAGING.md](./MESSAGING.md)

## Фазы

| # | Статус | Содержание |
|---|--------|------------|
| 0 | ✅ | Чеклист, MESSAGING.md |
| 1 | ✅ | portal-url, поиск :8004, `{results,total}`, internal index после транскодинга |
| 2 | ✅ | N+1 list_videos, batch notifications, `018_indexes.sql`, httpx pool |
| 3 | ✅ video / ✅ streaming / ⏳ auth | `video-service`: routers + `schemas`, `deps`, `access`, `storage`. `streaming-service`: `routers` (`health`, `internal`, `streams`), `archive`, `rtmp`, `stream_helpers`, `http_client` |
| 4 | план | Redis presence; RabbitMQ domain events (без ломания HTTP) |
| 5 | план | poetry.lock, интеграционные тесты |
| 6 | с вами | Prod: секреты, nginx TLS, LDAP |

Заготовки **messenger / dashboard / support** не удаляются; код подключится позже через auth (+ опционально RabbitMQ).

## После фазы 1 (пересборка)

```powershell
cd infrastructure\docker
docker compose up -d --build search-service video-service celery-worker frontend
```

Переиндексация существующих ready-видео (опционально):

```powershell
# для каждого video_id со status=ready
Invoke-RestMethod -Uri "http://localhost:8004/internal/search/index/{VIDEO_ID}" -Method POST -Headers @{ Authorization = "Bearer internal-secret-token" }
```
