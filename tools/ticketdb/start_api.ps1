param(
    [switch]$Stop,
    [switch]$Install,
    [switch]$Remove
)

$apiPort = 7987
$webPort = 7988
$workingDir = "C:\iridi\omnigent"
$taskName = "OmnigentTicketDB"

$python = (Get-Command python).Source

function Kill-ProcessOnPort($port) {
    try {
        $regex = ":$port\s"
        $found = $false
        netstat -ano 2>$null | Select-String $regex | ForEach-Object {
            $tokens = $_ -split '\s+'
            $pid = $tokens[-1]
            if ($pid -and $pid -ne '0' -and $pid -ne '0.0.0.0') {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  Killed PID $pid on port $port" -ForegroundColor DarkYellow
                $found = $true
            }
        }
        if (-not $found) { Write-Host "  Port $port is free" -ForegroundColor DarkGray }
    } catch {}
}

function Test-Port($port) {
    try {
        $conn = [System.Net.Sockets.TcpClient]::new()
        $conn.ConnectAsync("127.0.0.1", $port).Wait(500)
        if ($conn.Connected) { $conn.Close(); return $true }
        return $false
    } catch { return $false }
}

function Start-One($name, $module, $port) {
    Write-Host "[$name] Force-replacing process on port $port..." -ForegroundColor Cyan
    Kill-ProcessOnPort $port
    Start-Sleep -Milliseconds 300
    $argList = "-m uvicorn $module --host 127.0.0.1 --port $port"
    Write-Host "[$name] python $argList" -ForegroundColor Gray
    $proc = Start-Process -FilePath $python -ArgumentList $argList -WorkingDirectory $workingDir -NoNewWindow -PassThru
    Start-Sleep -Seconds 2
    if (Test-Port $port) {
        Write-Host "[$name] Started on http://127.0.0.1:$port" -ForegroundColor Green
    } else {
        Write-Host "[$name] May still be starting..." -ForegroundColor Yellow
    }
}

function Stop-Servers {
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    Kill-ProcessOnPort $apiPort
    Kill-ProcessOnPort $webPort
    Write-Host "All servers stopped." -ForegroundColor Green
}

function Install-Task {
    $scriptPath = Join-Path $workingDir "tools\ticketdb\start_api.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`"" -WorkingDirectory $workingDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
    Write-Host "Scheduled task '$taskName' created." -ForegroundColor Green
}

function Remove-Task {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Scheduled task '$taskName' removed." -ForegroundColor Yellow
}

if ($Stop)    { Stop-Servers; return }
if ($Install) { Install-Task; Start-One "API" "tools.ticketdb.api:app" $apiPort; Start-One "WebUI" "tools.ticketdb.webui.server:app" $webPort; return }
if ($Remove)  { Remove-Task; Stop-Servers; return }

Start-One "API" "tools.ticketdb.api:app" $apiPort
Start-One "WebUI" "tools.ticketdb.webui.server:app" $webPort
