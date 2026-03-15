# FinWise-ML Backend Ensure Script
# Usage: .\ensure_backend.ps1
# Behavior:
# 1) If backend is healthy, exits 0
# 2) If unhealthy, restarts backend via start_backend.ps1
# 3) Verifies health and exits non-zero on failure

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Test-Health {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method Get -TimeoutSec 2
        return ($resp.status -eq "up")
    } catch {
        return $false
    }
}

function Sync-PidFile {
    try {
        $conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn -and $conn.OwningProcess) {
            Set-Content -Path (Join-Path $root "app_v2_secure.pid") -Value ([string]$conn.OwningProcess) -Encoding ascii
        }
    } catch {
        # no-op
    }
}

if (Test-Health) {
    Sync-PidFile
    Write-Host "OK: Backend already healthy." -ForegroundColor Green
    exit 0
}

Write-Host "INFO: Backend unhealthy, restarting..." -ForegroundColor Yellow
& .\stop_backend.ps1 | Out-Null
& .\start_backend.ps1

if (Test-Health) {
    Sync-PidFile
    Write-Host "OK: Backend recovered and healthy." -ForegroundColor Green
    exit 0
}

Write-Host "ERROR: Backend recovery failed." -ForegroundColor Red
exit 1
