# Helpdesk dev server (MySQL from Open Server Panel / OSPanel only)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$ospanelMysql = "C:\OSPanel\modules\database\MySQL-8.0-Win10\bin"
$ospanelIni   = "C:\OSPanel\modules\database\MySQL-8.0-Win10\my.ini"

function Test-OspanelMysql {
    $conn = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $false }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    return $proc.Path -like "*ospanel*"
}

function Start-OspanelMysql {
    if (-not (Test-Path $ospanelMysql)) {
        throw "OSPanel MySQL not found: $ospanelMysql"
    }
    if (Test-Path "d:\api\mysql-data") {
        Write-Warning "d:\api\mysql-data is a test DB folder. Use OSPanel MySQL only."
    }
    $foreign = Get-Process mysqld -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "*ospanel*" }
    if ($foreign) {
        Write-Warning "Stopping non-OSPanel mysqld: $($foreign.Path -join ', ')"
        $foreign | Stop-Process -Force
        Start-Sleep -Seconds 2
    }
    if (-not (Test-OspanelMysql)) {
        Write-Host "Starting OSPanel MySQL..."
        Start-Process -FilePath "$ospanelMysql\mysqld.exe" -ArgumentList "--defaults-file=`"$ospanelIni`"","--standalone" -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $deadline) {
            if (Test-OspanelMysql) { break }
            Start-Sleep -Seconds 1
        }
        if (-not (Test-OspanelMysql)) {
            throw "OSPanel MySQL did not start. Enable MySQL in OSPanel tray menu."
        }
    }
    Write-Host "OSPanel MySQL OK (port 3306)"
}

function Initialize-HelpdeskDb {
    & "$ospanelMysql\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS helpdesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot connect to OSPanel MySQL. Check root password in .env"
    }
}

Start-OspanelMysql
Initialize-HelpdeskDb

Write-Host "App: http://127.0.0.1:8000"
& ".\.venv\Scripts\uvicorn.exe" main:app --host 127.0.0.1 --port 8000 --reload
