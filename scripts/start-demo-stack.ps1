param(
    [string]$JetsonHost = "100.108.243.35",
    [string]$JetsonUser = "jarvis",
    [switch]$SkipPull,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$commandCenterDir = Join-Path $repoRoot "command_center"
$sshTarget = "$JetsonUser@$JetsonHost"
$healthUrl = "http://$JetsonHost`:8000/health"

function Start-TerminalWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $wrappedCommand = "`$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    Start-Process powershell.exe `
        -WorkingDirectory $repoRoot `
        -ArgumentList @("-NoExit", "-Command", $wrappedCommand) | Out-Null
}

if (-not (Test-Path $commandCenterDir)) {
    throw "Could not find command_center at $commandCenterDir"
}

Write-Host "[launcher] Close any stale backend/listener terminals first to avoid duplicate Jetson processes." -ForegroundColor Yellow

if (-not $SkipPull) {
    Write-Host "[launcher] Pulling latest code on Jetson..." -ForegroundColor Cyan
    & ssh -t $sshTarget "cd ~/JARVIS_repo && git pull --ff-only"
}

$backendRemote = 'cd ~/JARVIS_repo/base_station && source .venv/bin/activate && while true; do python -m uvicorn api.main:app --host 0.0.0.0 --port 8000; echo "[AUTO] Backend exited; retrying in 2s"; sleep 2; done'
$listenerRemote = 'cd ~/JARVIS_repo/base_station && source .venv/bin/activate && set -a && source .env && set +a && while true; do python headless/serial_ptt_listener.py; echo "[AUTO] Listener exited; retrying in 2s"; sleep 2; done'
$frontendCommand = "Set-Location '$commandCenterDir'; npm run dev"

$backendCommand = "ssh -t $sshTarget '$backendRemote'"
$listenerCommand = "ssh -t $sshTarget '$listenerRemote'"

Write-Host "[launcher] Opening Jetson backend terminal..." -ForegroundColor Cyan
Start-TerminalWindow -Title "JARVIS Jetson Backend" -Command $backendCommand

$backendReady = $false
Write-Host "[launcher] Waiting for Jetson backend health at $healthUrl ..." -ForegroundColor Cyan
for ($attempt = 1; $attempt -le 45; $attempt++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            $backendReady = $true
            break
        }
    } catch {
        if ($attempt % 5 -eq 0) {
            Write-Host "[launcher] Still waiting for backend (attempt $attempt/45)..." -ForegroundColor DarkYellow
        }
    }
}

if ($backendReady) {
    Write-Host "[launcher] Backend is healthy. Opening listener and frontend..." -ForegroundColor Green
} else {
    Write-Warning "Backend health check did not succeed in time. Opening remaining terminals anyway."
}

Start-TerminalWindow -Title "JARVIS Jetson Listener" -Command $listenerCommand
Start-TerminalWindow -Title "JARVIS Frontend" -Command $frontendCommand

if ($OpenBrowser) {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5173" | Out-Null
}

Write-Host "[launcher] Demo stack terminals opened." -ForegroundColor Green
Write-Host "[launcher] If SSH key auth is not configured, enter the Jetson password in the backend and listener windows." -ForegroundColor Yellow
