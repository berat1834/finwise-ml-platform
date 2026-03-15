# FinWise-ML Backend Stopper Script
# Usage: .\stop_backend.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pidFile = Join-Path $root "app_v2_secure.pid"
$stopped = $false

if (Test-Path $pidFile) {
    try {
        $pid = [int](Get-Content $pidFile | Select-Object -First 1)
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pid -Force
            $stopped = $true
        }
    } catch {
        # fallback below
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -match 'app_v2_secure.py'
}
foreach ($p in $existing) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    $stopped = $true
}

if ($stopped) {
    Write-Host "OK: Backend stopped." -ForegroundColor Green
} else {
    Write-Host "INFO: No running backend process found." -ForegroundColor Yellow
}
