# iRidi Support Agent — запуск веб-интерфейса
Write-Host "=== iRidi Support Agent L1 ===" -ForegroundColor Cyan
Write-Host "Web interface: http://localhost:7987" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$env:PYTHONIOENCODING = 'utf-8'
python -m web.main
