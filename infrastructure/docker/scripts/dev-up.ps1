# Запуск единого dev-стека (infrastructure/docker).
# Останавливает конфликтующие контейнеры старого проекта "docker" на тех же портах.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$DockerDir = Join-Path $Root "infrastructure\docker"
Set-Location $DockerDir

$conflictNames = @(
  "docker-frontend-1", "docker-video-service-1", "docker-streaming-service-1",
  "docker-portal-1", "docker-nginx-1", "docker-notification-service-1",
  "docker-search-service-1", "docker-mediamtx-1", "docker-auth-service-1"
)
foreach ($n in $conflictNames) {
  docker stop $n 2>$null | Out-Null
}

docker compose --env-file .env up -d `
  db redis rabbitmq minio elasticsearch mediamtx `
  auth-service video-service streaming-service notification-service search-service `
  celery-worker frontend portal

# Миграции превью трансляций (идемпотентные)
foreach ($m in @("019_stream_thumbnail.sql", "020_stream_thumbnail_updated.sql", "021_views_count_fix_and_stream_views.sql")) {
  try {
    & (Join-Path $PSScriptRoot "dev-apply-migration.ps1") -MigrationFile $m
  } catch {
    Write-Warning "Migration $m skipped (is db up?): $_"
  }
}

Write-Host ""
Write-Host "Dev URLs:"
Write-Host "  Portal:    http://localhost:3002"
Write-Host "  Video UI:  http://localhost:3000"
Write-Host "  Auth:      http://localhost:8000"
Write-Host "  Video API: http://localhost:8001"
Write-Host "  Stream API:http://localhost:8002"
Write-Host "  Search API: http://localhost:8004"
Write-Host "  MinIO:     http://localhost:9001 (console)"
Write-Host ""
docker compose ps
