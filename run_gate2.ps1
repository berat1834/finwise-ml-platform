# GATE 2: MODEL ROUTING LOGIC VALIDATION
# March 6, 2026 - Test single/shadow/canary modes

param(
    [string]$Mode = "all"  # all | single | shadow | canary
)

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    GATE 2: MODEL ROUTING LOGIC VALIDATION" -ForegroundColor Cyan  
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$results = @{
    single = @{ passed = $false; latency_ms = 0; errors = @() }
    shadow = @{ passed = $false; latency_ms = 0; correlation = 0; errors = @() }
    canary = @{ passed = $false; primary_count = 0; canary_count = 0; errors = @() }
}

# Helper: Update .env file
function Set-RoutingMode {
    param([string]$RoutingMode, [int]$CanaryPercent = 0)
    
    Write-Host "Updating .env: MODE=$RoutingMode, CANARY_PERCENT=$CanaryPercent" -ForegroundColor Yellow
    
    $envContent = Get-Content .env
    $envContent = $envContent -replace 'MODEL_ROUTING_MODE=.*', "MODEL_ROUTING_MODE=$RoutingMode"
    $envContent = $envContent -replace 'CANARY_PERCENT=.*', "CANARY_PERCENT=$CanaryPercent"
    $envContent | Set-Content .env
    
    Start-Sleep -Seconds 1
}

# Helper: Restart API
function Restart-API {
    Write-Host "Restarting API..." -ForegroundColor Yellow
    
    # Kill existing
    Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.MainWindowTitle -match 'app_v2' } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Start new
    Start-Process python -ArgumentList 'app_v2_secure.py' -WindowStyle Hidden -RedirectStandardOutput 'api_gate2.log' -RedirectStandardError 'api_gate2_err.log'
    Start-Sleep -Seconds 5
    
    # Verify
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/health' -UseBasicParsing -TimeoutSec 5
        Write-Host "  OK - API started (mode: $($health.routing_mode))" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  FAILED - API not responding" -ForegroundColor Red
        return $false
    }
}

# Helper: Get JWT token
function Get-AuthToken {
    $loginBody = '{"username":"admin","password":"admin123"}'
    $login = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/auth/login' -ContentType 'application/json' -Body $loginBody -TimeoutSec 5
    return $login.access_token
}

# Helper: Make prediction
function Invoke-Prediction {
    param([string]$Token, [int]$Age, [int]$Income)
    
    $body = @{
        person_age = $Age
        person_income = $Income
        person_emp_length = 5
        loan_amnt = 20000
        loan_int_rate = 10.5
        loan_percent_income = 30.0
        cb_person_cred_hist_length = 5
        person_home_ownership = "RENT"
        loan_intent = "PERSONAL"
        loan_grade = "B"
        cb_person_default_on_file = "N"
    } | ConvertTo-Json -Compress
    
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $eval = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/degerlendir' -Headers @{ Authorization = "Bearer $Token" } -ContentType 'application/json' -Body $body -TimeoutSec 10
    $sw.Stop()
    
    return @{
        response = $eval
        latency_ms = $sw.ElapsedMilliseconds
    }
}

# ============================================================================
# TEST MODE 1: SINGLE (Baseline)
# ============================================================================
if ($Mode -eq "all" -or $Mode -eq "single") {
    Write-Host ""
    Write-Host "TEST 1: SINGLE MODE (Baseline)" -ForegroundColor Green
    Write-Host "-----------------------------------------------"
    
    Set-RoutingMode -RoutingMode "single" -CanaryPercent 0
    
    if (Restart-API) {
        try {
            $token = Get-AuthToken
            $latencies = @()
            
            Write-Host "Running 20 predictions..."
            for ($i = 1; $i -le 20; $i++) {
                $pred = Invoke-Prediction -Token $token -Age (30 + $i) -Income (60000 + $i * 1000)
                $latencies += $pred.latency_ms
                
                $served = $pred.response.model_routing.served_by
                if ($served -ne "primary") {
                    $results.single.errors += "Prediction $i served by $served (expected: primary)"
                }
                
                Write-Host "  Pred $i | Latency: $($pred.latency_ms)ms | Model: $served"
            }
            
            $avgLatency = ($latencies | Measure-Object -Average).Average
            $p50 = ($latencies | Sort-Object)[9]
            $p95 = ($latencies | Sort-Object)[18]
            
            Write-Host ""
            Write-Host "  Avg Latency: $([math]::Round($avgLatency, 1))ms" -ForegroundColor Cyan
            Write-Host "  P50 Latency: ${p50}ms" -ForegroundColor Cyan
            Write-Host "  P95 Latency: ${p95}ms" -ForegroundColor Cyan
            
            $results.single.latency_ms = $avgLatency
            
            if ($results.single.errors.Count -eq 0) {
                $results.single.passed = $true
                Write-Host "  RESULT: PASSED" -ForegroundColor Green
            } else {
                Write-Host "  RESULT: FAILED ($($results.single.errors.Count) errors)" -ForegroundColor Red
            }
        } catch {
            $results.single.errors += $_.Exception.Message
            Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        $results.single.errors += "API failed to start"
    }
}

# ============================================================================
# TEST MODE 2: SHADOW (Comparison)
# ============================================================================
if ($Mode -eq "all" -or $Mode -eq "shadow") {
    Write-Host ""
    Write-Host "TEST 2: SHADOW MODE (Both Models Scored)" -ForegroundColor Green
    Write-Host "-----------------------------------------------"
    
    Set-RoutingMode -RoutingMode "shadow" -CanaryPercent 0
    
    if (Restart-API) {
        try {
            $token = Get-AuthToken
            $latencies = @()
            $shadowCount = 0
            
            Write-Host "Running 20 predictions..."
            for ($i = 1; $i -le 20; $i++) {
                $pred = Invoke-Prediction -Token $token -Age (30 + $i) -Income (60000 + $i * 1000)
                $latencies += $pred.latency_ms
                
                $served = $pred.response.model_routing.served_by
                $hasShadow = $null -ne $pred.response.model_routing.shadow_comparison
                
                if ($served -ne "primary") {
                    $results.shadow.errors += "Prediction $i served by $served (expected: primary)"
                }
                
                if ($hasShadow) {
                    $shadowCount++
                }
                
                Write-Host "  Pred $i | Latency: $($pred.latency_ms)ms | Shadow: $hasShadow"
            }
            
            $avgLatency = ($latencies | Measure-Object -Average).Average
            $shadowPercent = ($shadowCount / 20 * 100)
            
            Write-Host ""
            Write-Host "  Avg Latency: $([math]::Round($avgLatency, 1))ms" -ForegroundColor Cyan
            Write-Host "  Shadow Scored: $shadowCount/20 ($shadowPercent%)" -ForegroundColor Cyan
            
            $latencyOverhead = $avgLatency / $results.single.latency_ms
            Write-Host "  Latency Overhead: $([math]::Round($latencyOverhead, 2))x vs single" -ForegroundColor Cyan
            
            $results.shadow.latency_ms = $avgLatency
            
            if ($shadowPercent -ge 95 -and $latencyOverhead -le 3.0) {
                $results.shadow.passed = $true
                Write-Host "  RESULT: PASSED" -ForegroundColor Green
            } else {
                $results.shadow.errors += "Shadow coverage: $shadowPercent% (expected >=95%), overhead: ${latencyOverhead}x (expected <=3.0x)"
                Write-Host "  RESULT: FAILED" -ForegroundColor Red
            }
        } catch {
            $results.shadow.errors += $_.Exception.Message
            Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        $results.shadow.errors += "API failed to start"
    }
}

# ============================================================================
# TEST MODE 3: CANARY (Traffic Split)
# ============================================================================
if ($Mode -eq "all" -or $Mode -eq "canary") {
    Write-Host ""
    Write-Host "TEST 3: CANARY MODE (10% Traffic Split)" -ForegroundColor Green
    Write-Host "-----------------------------------------------"
    
    Set-RoutingMode -RoutingMode "canary" -CanaryPercent 10
    
    if (Restart-API) {
        try {
            $token = Get-AuthToken
            $primaryCount = 0
            $canaryCount = 0
            
            Write-Host "Running 100 predictions (expect ~10 canary, ~90 primary)..."
            for ($i = 1; $i -le 100; $i++) {
                $pred = Invoke-Prediction -Token $token -Age (30 + $i) -Income (60000 + $i * 100)
                
                $served = $pred.response.model_routing.served_by
                
                if ($served -eq "primary") {
                    $primaryCount++
                } elseif ($served -eq "fair_v2") {
                    $canaryCount++
                } else {
                    $results.canary.errors += "Prediction $i served by unknown model: $served"
                }
                
                if ($i % 10 -eq 0) {
                    Write-Host "  Progress: $i/100 | Primary: $primaryCount | Canary: $canaryCount"
                }
            }
            
            $canaryPercent = $canaryCount / 100 * 100
            
            Write-Host ""
            Write-Host "  Primary: $primaryCount/100 ($($primaryCount)%)" -ForegroundColor Cyan
            Write-Host "  Canary: $canaryCount/100 ($canaryPercent%)" -ForegroundColor Cyan
            
            $results.canary.primary_count = $primaryCount
            $results.canary.canary_count = $canaryCount
            
            # Accept 5-15% canary (target 10% +/- 5%)
            if ($canaryPercent -ge 5 -and $canaryPercent -le 15) {
                $results.canary.passed = $true
                Write-Host "  RESULT: PASSED (within 5-15% range)" -ForegroundColor Green
            } else {
                $results.canary.errors += "Canary: $canaryPercent% (expected 5-15%)"
                Write-Host "  RESULT: FAILED (outside 5-15% range)" -ForegroundColor Red
            }
        } catch {
            $results.canary.errors += $_.Exception.Message
            Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        $results.canary.errors += "API failed to start"
    }
}

# ============================================================================
# FINAL REPORT
# ============================================================================
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    GATE 2 FINAL RESULTS" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$passedCount = 0
$totalCount = 0

if ($Mode -eq "all" -or $Mode -eq "single") {
    $totalCount++
    if ($results.single.passed) {
        Write-Host "  SINGLE MODE: PASSED (avg ${results.single.latency_ms}ms)" -ForegroundColor Green
        $passedCount++
    } else {
        Write-Host "  SINGLE MODE: FAILED" -ForegroundColor Red
        foreach ($err in $results.single.errors) {
            Write-Host "    - $err" -ForegroundColor Red
        }
    }
}

if ($Mode -eq "all" -or $Mode -eq "shadow") {
    $totalCount++
    if ($results.shadow.passed) {
        Write-Host "  SHADOW MODE: PASSED (avg $([math]::Round($results.shadow.latency_ms, 1))ms)" -ForegroundColor Green
        $passedCount++
    } else {
        Write-Host "  SHADOW MODE: FAILED" -ForegroundColor Red
        foreach ($err in $results.shadow.errors) {
            Write-Host "    - $err" -ForegroundColor Red
        }
    }
}

if ($Mode -eq "all" -or $Mode -eq "canary") {
    $totalCount++
    if ($results.canary.passed) {
        Write-Host "  CANARY MODE: PASSED (primary: $($results.canary.primary_count), canary: $($results.canary.canary_count))" -ForegroundColor Green
        $passedCount++
    } else {
        Write-Host "  CANARY MODE: FAILED" -ForegroundColor Red
        foreach ($err in $results.canary.errors) {
            Write-Host "    - $err" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "Summary: $passedCount/$totalCount tests passed"
Write-Host ""

if ($passedCount -eq $totalCount) {
    Write-Host "SUCCESS - GATE 2: MODEL ROUTING LOGIC PASSED" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "OK - All routing modes functional"
    Write-Host "OK - Single mode: baseline established"
    Write-Host "OK - Shadow mode: both models scoring"
    Write-Host "OK - Canary mode: traffic split working"
    Write-Host "OK - Ready for GATE 3 (Fairness Metrics Collection)"
    
    # Reset to single mode
    Set-RoutingMode -RoutingMode "single" -CanaryPercent 0
    Write-Host ""
    Write-Host "NOTE: .env reset to MODEL_ROUTING_MODE=single" -ForegroundColor Yellow
    
    exit 0
} else {
    Write-Host "FAILED - GATE 2 ($($totalCount - $passedCount) tests failed)" -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Cyan
    exit 1
}
