# Сброс кэша Next.js в Docker (когда UI не обновляется после правок в frontend/src).
$ErrorActionPreference = "Stop"
$DockerDir = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "infrastructure\docker"
Set-Location $DockerDir

docker compose stop frontend
docker compose rm -sf frontend
docker volume rm video_dgim_mos_frontend_next 2>$null
docker compose up -d frontend

Write-Host "Frontend пересобран с чистым .next. Откройте http://localhost:3000 и нажмите Ctrl+F5."
