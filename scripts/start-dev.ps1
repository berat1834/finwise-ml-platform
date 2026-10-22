# FinWise ML Platform — Development Startup Script (PowerShell)
# Usage: .\scripts\start-dev.ps1 [backend|frontend|all]
# Default: all (starts both backend and frontend)

param(
    [ValidateSet("all", "backend", "frontend")]
    [string]$Component = "all"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FinWise ML Platform — Development Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Helper: find Python from .venv ---
function Get-PythonPath {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    
    $venvPythonUnix = Join-Path $ProjectRoot ".venv/bin/python"
    if (Test-Path $venvPythonUnix) { return $venvPythonUnix }
    
    # Fallback to system python
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if ($systemPython) { return $systemPython.Source }
    
    Write-Host "[ERROR] Python not found. Create a .venv first: python -m venv .venv" -ForegroundColor Red
    exit 1
}

# --- Start Backend ---
function Start-Backend {
    $python = Get-PythonPath
    Write-Host "[Backend] Python: $python" -ForegroundColor Green
    Write-Host "[Backend] Starting Flask on http://localhost:5000 ..." -ForegroundColor Green
    
    # start.py already does os.chdir() to backend/ dir
    $backendStart = Join-Path $ProjectRoot "backend\start.py"
    if (Test-Path $backendStart) {
        Start-Process -NoNewWindow -FilePath $python -ArgumentList $backendStart -WorkingDirectory $ProjectRoot
    } else {
        Start-Process -NoNewWindow -FilePath $python -ArgumentList (Join-Path $ProjectRoot "backend\app_v2_secure.py") -WorkingDirectory (Join-Path $ProjectRoot "backend")
    }
}

# --- Start Frontend ---
function Start-Frontend {
    $frontendDir = Join-Path $ProjectRoot "frontend"
    
    # Check if node_modules exists
    $nodeModules = Join-Path $frontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "[Frontend] Installing dependencies..." -ForegroundColor Yellow
        Push-Location $frontendDir
        npm install
        Pop-Location
    }
    
    Write-Host "[Frontend] Starting Next.js on http://localhost:3000 ..." -ForegroundColor Green
    Push-Location $frontendDir
    npm run dev
    Pop-Location
}

# --- Main ---
switch ($Component) {
    "backend" {
        Start-Backend
        Write-Host "`n[OK] Backend started." -ForegroundColor Green
    }
    "frontend" {
        Start-Frontend
    }
    "all" {
        Start-Backend
        Start-Sleep -Seconds 3  # Give backend time to boot
        Start-Frontend
    }
}
