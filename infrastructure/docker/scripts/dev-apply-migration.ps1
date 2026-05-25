# Применить SQL-миграцию к dev БД
param(
    [Parameter(Mandatory = $true)]
    [string]$MigrationFile
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$sqlPath = Join-Path $RepoRoot "infrastructure\database\migrations\$MigrationFile"
if (-not (Test-Path $sqlPath)) {
    Write-Error "Not found: $sqlPath"
}
Get-Content -Raw $sqlPath | docker exec -i video_dgim_mos-db-1 psql -U user -d video_hosting
Write-Host "Applied: $MigrationFile"
