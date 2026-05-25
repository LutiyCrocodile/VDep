# Переиндексация всех ready-видео в Elasticsearch
param(
    [string]$Token = "internal-secret-token"
)

try {
    $r = Invoke-RestMethod -Uri "http://localhost:8004/internal/search/reindex-ready" `
        -Method POST `
        -Headers @{ Authorization = "Bearer $Token" }
    Write-Host "Reindex done: $($r | ConvertTo-Json -Compress)"
} catch {
    Write-Host "FAILED: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    exit 1
}
