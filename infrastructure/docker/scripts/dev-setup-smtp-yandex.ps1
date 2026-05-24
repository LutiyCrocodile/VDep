# Настройка Yandex SMTP для dev и перезапуск notification-service.
# Пароль приложения: https://id.yandex.ru/security/app-passwords
#
#   .\dev-setup-smtp-yandex.ps1 -AppPassword "ваш_пароль_приложения"
#
param(
    [Parameter(Mandatory = $true)]
    [string]$AppPassword,
    [string]$Email = "lutcrocodil@yandex.ru"
)

$ErrorActionPreference = "Stop"
$DockerDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $DockerDir

$envFile = Join-Path $DockerDir ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $DockerDir ".env.example") $envFile
}

$content = Get-Content $envFile -Raw
$replacements = @{
    'SMTP_SERVER=.*' = 'SMTP_SERVER=smtp.yandex.ru'
    'SMTP_PORT=.*' = 'SMTP_PORT=465'
    'SMTP_USE_SSL=.*' = 'SMTP_USE_SSL=true'
    'SMTP_USERNAME=.*' = "SMTP_USERNAME=$Email"
    'SMTP_PASSWORD=.*' = "SMTP_PASSWORD=$AppPassword"
    'SMTP_FROM_EMAIL=.*' = "SMTP_FROM_EMAIL=$Email"
}
foreach ($pattern in $replacements.Keys) {
    if ($content -match "(?m)^$pattern") {
        $content = $content -replace $pattern, $replacements[$pattern]
    } else {
        $content += "`n$($replacements[$pattern])"
    }
}
Set-Content -Path $envFile -Value $content.TrimEnd() -Encoding UTF8

Write-Host "Applied Yandex SMTP to .env (username/from: $Email)"

docker compose up -d notification-service
Write-Host "notification-service restarted. Test: subscribe dev_viewer, publish video or start stream."
