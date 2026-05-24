# Тест отправки письма через notification-service
param(
    [string]$To = "moren280806@yandex.ru",
    [string]$Token = "internal-secret-token"
)

$body = @{ to_email = $To } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8003/internal/test-email" `
        -Method POST `
        -Headers @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" } `
        -Body $body
    Write-Host "OK: $($r | ConvertTo-Json)"
} catch {
    Write-Host "FAILED: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}
