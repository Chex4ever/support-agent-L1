# iRidi Omnigent — запуск сервисов
Write-Host "=== iRidi Omnigent ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "TicketDB API:    http://localhost:7987" -ForegroundColor Green
Write-Host "TicketDB WebUI:  http://localhost:7988" -ForegroundColor Green
Write-Host "L1 Agent WebUI:  http://localhost:7989" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$scriptPath = Join-Path $PSScriptRoot "tools\ticketdb\start_api.ps1"
& $scriptPath

# После остановки TicketDB
Write-Host ""
Write-Host "Servers stopped." -ForegroundColor Yellow
