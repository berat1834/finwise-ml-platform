# FinWise-ML Backend Starter Script (non-interactive)
# Usage: .\start_backend.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pythonExe = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
	Write-Host "ERROR: Python executable not found: $pythonExe" -ForegroundColor Red
	exit 1
}

$stdoutLog = Join-Path $root "log_server.txt"
$stderrLog = Join-Path $root "log_server_err.txt"
$pidFile = Join-Path $root "app_v2_secure.pid"

# Stop existing app_v2_secure.py python processes
$existing = Get-CimInstance Win32_Process | Where-Object {
	$_.Name -eq 'python.exe' -and $_.CommandLine -match 'app_v2_secure.py'
}
foreach ($p in $existing) {
	Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

# Launch detached server process
$startArgs = @{
	FilePath = $pythonExe
	ArgumentList = "app_v2_secure.py"
	WorkingDirectory = $root
	WindowStyle = "Hidden"
	RedirectStandardOutput = $stdoutLog
	RedirectStandardError = $stderrLog
	PassThru = $true
}
$proc = Start-Process @startArgs

Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii

# Poll health endpoint up to 20 seconds
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
	Start-Sleep -Seconds 1
	try {
		$resp = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method Get -TimeoutSec 2
		if ($resp.status -eq "up") {
			$healthy = $true
			break
		}
	} catch {
		# keep polling
	}
}

if ($healthy) {
	try {
		$conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
		if ($conn -and $conn.OwningProcess) {
			Set-Content -Path $pidFile -Value ([string]$conn.OwningProcess) -Encoding ascii
		}
	} catch {
		# keep starter process pid if owner lookup fails
	}
	Write-Host "OK: Backend is running on http://127.0.0.1:5000 (PID=$($proc.Id))" -ForegroundColor Green
	exit 0
}

Write-Host "ERROR: Backend did not become healthy in time." -ForegroundColor Red
Write-Host "Check logs: $stdoutLog and $stderrLog" -ForegroundColor Yellow
exit 1
