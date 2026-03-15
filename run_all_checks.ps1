<#
.SYNOPSIS
Automated test pipeline for FinWise ML production system.

.DESCRIPTION
Runs comprehensive tests across all system components with configurable quality gates.

.PARAMETER SkipApiTests
Skip API integration tests (useful when API server already validated).

.PARAMETER Strict
Enable strict mode to fail on warning patterns (not just errors).

.PARAMETER StrictLevel
Set strictness level when -Strict is enabled:
  - Lenient:  Only fail on critical errors (exceptions, pipeline failures)
  - Balanced: Fail on critical errors + quality gates (model AUC, thresholds) [DEFAULT]
  - Maximum:  Fail on everything including warnings (deprecations, overfitting alerts)

.EXAMPLE
.\run_all_checks.ps1
Run all tests with no quality gates.

.EXAMPLE
.\run_all_checks.ps1 -Strict
Run with balanced quality gates (catches model quality issues).

.EXAMPLE
.\run_all_checks.ps1 -Strict -StrictLevel Maximum
Run with maximum strictness (fails on all warnings).

.EXAMPLE
.\run_all_checks.ps1 -Strict -StrictLevel Lenient -SkipApiTests
Run only module self-tests, fail only on critical errors.
#>

param(
    [switch]$SkipApiTests,
    [switch]$Strict,
    [ValidateSet('Lenient', 'Balanced', 'Maximum')]
    [string]$StrictLevel = 'Balanced'
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python executable not found: $pythonExe" -ForegroundColor Red
    exit 1
}

$script:results = @()
$serverProcess = $null

# Strict mode patterns with severity levels
# Critical: Always fail (exceptions, pipeline errors)
$criticalPatterns = @(
    'Traceback \(most recent call last\):',
    'Pipeline error:',
    'Error:.*occurred',
    'FAILED.*test'
)

# QualityGate: Model/data quality thresholds
$qualityGatePatterns = @(
    'Cannot promote:',
    'below threshold',
    'AUC.*below',
    'Insufficient.*data'
)

# CodeQuality: Warnings and best practices
$codeQualityPatterns = @(
    'DeprecationWarning',
    'Possible overfitting',
    'FutureWarning',
    'UserWarning:.*important'
)

# Select patterns based on strictness level
$strictPatterns = if ($Strict) {
    switch ($StrictLevel) {
        'Lenient'  { $criticalPatterns }
        'Balanced' { $criticalPatterns + $qualityGatePatterns }
        'Maximum'  { $criticalPatterns + $qualityGatePatterns + $codeQualityPatterns }
    }
} else {
    @()  # No strict patterns if -Strict not specified
}

function Add-Result {
    param(
        [string]$Step,
        [bool]$Passed,
        [int]$ExitCode,
        [string]$Notes
    )

    $script:results += [PSCustomObject]@{
        Step = $Step
        Passed = $Passed
        ExitCode = $ExitCode
        Notes = $Notes
    }
}

function Run-Step {
    param(
        [string]$StepName,
        [string]$File,
        [string[]]$Arguments
    )

    Write-Host "`n==== $StepName ====" -ForegroundColor Cyan
    Write-Host "$File $($Arguments -join ' ')"

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $proc = Start-Process -FilePath $File -ArgumentList $Arguments -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $code = $proc.ExitCode

        $stdoutText = if (Test-Path $stdoutPath) { Get-Content -Path $stdoutPath -Raw } else { "" }
        $stderrText = if (Test-Path $stderrPath) { Get-Content -Path $stderrPath -Raw } else { "" }
        $combined = ($stdoutText + "`n" + $stderrText).Trim()

        if ($stdoutText) { Write-Host $stdoutText }
        if ($stderrText) { Write-Host $stderrText }

        $strictHit = $false
        $strictMatch = ""
        if ($Strict -and $combined) {
            foreach ($pattern in $strictPatterns) {
                if ($combined -match $pattern) {
                    $strictHit = $true
                    $strictMatch = $pattern
                    break
                }
            }
        }

        if ($code -eq 0 -and -not $strictHit) {
            Write-Host "PASS: $StepName" -ForegroundColor Green
            Add-Result -Step $StepName -Passed $true -ExitCode $code -Notes "OK"
        }
        else {
            if ($strictHit) {
                Write-Host "FAIL: $StepName (strict mode pattern matched: $strictMatch)" -ForegroundColor Red
                Add-Result -Step $StepName -Passed $false -ExitCode 2 -Notes "Strict mode pattern matched: $strictMatch"
                return 2
            }
            Write-Host "FAIL: $StepName (exit code: $code)" -ForegroundColor Red
            Add-Result -Step $StepName -Passed $false -ExitCode $code -Notes "Command failed"
        }

        return $code
    }
    finally {
        Remove-Item -Path $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
    }
}

function Wait-For-Health {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

try {
    Write-Host "Starting FinWise check pipeline..." -ForegroundColor Yellow
    if ($Strict) {
        Write-Host "Strict mode: ENABLED (Level: $StrictLevel)" -ForegroundColor Yellow
        $lenientColor = if ($StrictLevel -eq 'Lenient') { 'Green' } else { 'Gray' }
        $balancedColor = if ($StrictLevel -eq 'Balanced') { 'Green' } else { 'Gray' }
        $maximumColor = if ($StrictLevel -eq 'Maximum') { 'Green' } else { 'Gray' }
        Write-Host "  - Lenient:  Critical errors only" -ForegroundColor $lenientColor
        Write-Host "  - Balanced: Critical errors + quality gates" -ForegroundColor $balancedColor
        Write-Host "  - Maximum:  All warnings and errors" -ForegroundColor $maximumColor
    } else {
        Write-Host "Strict mode: DISABLED (only exit codes matter)" -ForegroundColor Gray
    }

    if (-not $SkipApiTests) {
        Write-Host "`nStarting API server in background..." -ForegroundColor Yellow
        $serverProcess = Start-Process -FilePath $pythonExe -ArgumentList "app_v2_secure.py" -PassThru -WindowStyle Hidden

        if (Wait-For-Health -Url "http://127.0.0.1:5000/health" -TimeoutSeconds 35) {
            Write-Host "API health check is ready." -ForegroundColor Green
            Add-Result -Step "API startup" -Passed $true -ExitCode 0 -Notes "Health endpoint returned 200"
        }
        else {
            Write-Host "API did not become healthy in time." -ForegroundColor Red
            Add-Result -Step "API startup" -Passed $false -ExitCode 1 -Notes "Health endpoint timeout"
            throw "API startup failed"
        }

        $apiExit = Run-Step -StepName "API integration tests" -File $pythonExe -Arguments @("-m", "pytest", "-q", "test_api_v2.py")
    }

    $slaExit = Run-Step -StepName "SLA module self-test" -File $pythonExe -Arguments @("sla_monitoring.py")
    $driftExit = Run-Step -StepName "Drift/retraining self-test" -File $pythonExe -Arguments @("drift_detection_retraining.py")
    $mtExit = Run-Step -StepName "Multi-tenant training self-test" -File $pythonExe -Arguments @("multi_tenant_training.py")
}
catch {
    $message = $_.Exception.Message
    Write-Host "`nPipeline error: $message" -ForegroundColor Red
    Add-Result -Step "Pipeline runtime" -Passed $false -ExitCode 99 -Notes $message
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Write-Host "`nStopping API server..." -ForegroundColor Yellow
        Stop-Process -Id $serverProcess.Id -Force
    }

    Write-Host "`n==== SUMMARY ====" -ForegroundColor Cyan
    $script:results | Format-Table -AutoSize

    $failed = @($script:results | Where-Object { -not $_.Passed }).Count
    if ($failed -gt 0) {
        Write-Host "`nCompleted with $failed failed step(s)." -ForegroundColor Red
        exit 1
    }

    Write-Host "`nAll checks passed." -ForegroundColor Green
    exit 0
}
