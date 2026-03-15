# FinWise-ML Backend Status Script
# Usage: .\backend_status.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pidFile = Join-Path $root "app_v2_secure.pid"
$pidValue = $null
$pidAlive = $false
$healthUp = $false
$healthPayload = $null

if (Test-Path $pidFile) {
    try {
        $pidValue = [int](Get-Content $pidFile | Select-Object -First 1)
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($proc) { $pidAlive = $true }
    } catch {
        $pidValue = $null
    }
}

try {
    $healthPayload = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method Get -TimeoutSec 2
    $healthUp = ($healthPayload.status -eq "up")
} catch {
    $healthUp = $false
}

$portOwner = $null
try {
    $conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) { $portOwner = $conn.OwningProcess }
} catch {
    $portOwner = $null
}

[PSCustomObject]@{
    pid_file_exists = (Test-Path $pidFile)
    pid = $pidValue
    pid_alive = $pidAlive
    port_5000_owner_pid = $portOwner
    health_up = $healthUp
    routing_mode = if ($healthPayload) { $healthPayload.routing_mode } else { $null }
    canary_loaded = if ($healthPayload) { $healthPayload.canary_loaded } else { $null }
    version = if ($healthPayload) { $healthPayload.version } else { $null }
} | ConvertTo-Json -Depth 4
