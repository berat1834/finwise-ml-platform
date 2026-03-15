# GATE 1: RUNTIME STABILITY SMOKE TESTS
# March 6, 2026 - Validate API startup and basic functionality

param(
    [int]$MaxRetries = 30,
    [int]$RetryDelaySeconds = 1
)

$ErrorActionPreference = "Continue"
$results = @{
    health_check = $false
    login = $false
    predictions = @()
    metrics = $false
    errors = @()
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║            GATE 1: RUNTIME STABILITY - SMOKE TESTS         ║" -ForegroundColor Cyan
Write-Host "║                    March 6, 2026 09:00 UTC                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# TEST 1: Health Check (Retry loop)
# ============================================================================
Write-Host "TEST 1: Health Check" -ForegroundColor Green
$retryCount = 0
$healthCheckPassed = $false

while ($retryCount -lt $MaxRetries -and -not $healthCheckPassed) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/health' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        
        if ($health.status -eq "up") {
            Write-Host "  ✓ Status: $($health.status)" -ForegroundColor Green
            Write-Host "  ✓ Routing Mode: $($health.routing_mode)" -ForegroundColor Green
            Write-Host "  ✓ Canary Loaded: $($health.canary_loaded)" -ForegroundColor Green
            $results.health_check = $true
            $healthCheckPassed = $true
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $MaxRetries) {
            Write-Host "  ⏳ Retry $retryCount/$MaxRetries in ${RetryDelaySeconds}s..." -ForegroundColor Yellow
            Start-Sleep -Seconds $RetryDelaySeconds
        } else {
            Write-Host "  ✗ FAILED: Health check did not respond after $MaxRetries retries" -ForegroundColor Red
            $results.errors += "Health endpoint unresponsive"
            exit 1
        }
    }
}

Write-Host ""

# ============================================================================
# TEST 2: Login Endpoint
# ============================================================================
Write-Host "TEST 2: Login Authentication" -ForegroundColor Green
$loginPassed = $false

try {
    $loginBody = @{ username='admin'; password='admin123' } | ConvertTo-Json
    $login = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/auth/login' `
        -ContentType 'application/json' -Body $loginBody -TimeoutSec 5 -ErrorAction Stop
    
    if ($login.access_token) {
        Write-Host "  ✓ Login successful" -ForegroundColor Green
        Write-Host "  ✓ Token obtained (length: $($login.access_token.Length))" -ForegroundColor Green
        $token = $login.access_token
        $results.login = $true
        $loginPassed = $true
    } else {
        throw "No access_token in response"
    }
} catch {
    Write-Host "  ✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $results.errors += "Login failed: $($_.Exception.Message)"
    exit 1
}

Write-Host ""

# ============================================================================
# TEST 3-12: 10 Predictions with Varied Input
# ============================================================================
Write-Host "TEST 3-12: 10 Prediction Requests" -ForegroundColor Green

for ($i = 1; $i -le 10; $i++) {
    try {
        $evalBody = @{
            person_age = 25 + ($i * 3)
            person_income = 50000 + ($i * 5000)
            person_emp_length = 1 + $i
            loan_amnt = 20000
            loan_int_rate = 10.5
            loan_percent_income = 40.0
            cb_person_cred_hist_length = 5
            person_home_ownership = "RENT"
            loan_intent = "PERSONAL"
            loan_grade = "B"
            cb_person_default_on_file = "N"
        } | ConvertTo-Json
        
        $eval = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/degerlendir' `
            -Headers @{ Authorization = "Bearer $token" } `
            -ContentType 'application/json' `
            -Body $evalBody `
            -TimeoutSec 10 -ErrorAction Stop
        
        if ($eval.application_id -and $eval.tahmin) {
            $modelUsed = $eval.model_routing.served_by
            Write-Host "  ✓ Pred $i | App: $($eval.application_id) | Decision: $($eval.tahmin) | Model: $modelUsed" -ForegroundColor Green
            
            $results.predictions += @{
                test_num = $i
                app_id = $eval.application_id
                decision = $eval.tahmin
                risk_pct = $eval.red_olasiligi
                model_used = $modelUsed
                has_shap = ($null -ne $eval.shap_top_features)
                has_adverse_action = ($null -ne $eval.adverse_action_notice)
            }
        } else {
            throw "Missing application_id or tahmin in response"
        }
    } catch {
        Write-Host "  ✗ Pred $i FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $results.errors += "Prediction $i failed: $($_.Exception.Message)"
    }
}
Write-Host ""

# ============================================================================
# TEST 13: Metrics Endpoint (Prometheus)
# ============================================================================
Write-Host "TEST 13: Metrics Endpoint" -ForegroundColor Green
try {
    $metrics = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/metrics' -UseBasicParsing -TimeoutSec 5
    
    if ($metrics -match 'finwise_model_route_total') {
        Write-Host "  ✓ Prometheus metrics endpoint responding" -ForegroundColor Green
        Write-Host "  ✓ Found routing metrics (finwise_model_route_total)" -ForegroundColor Green
        $results.metrics = $true
    } else {
        throw "Metrics not in Prometheus format"
    }
} catch {
    Write-Host "  ✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $results.errors += "Metrics endpoint failed: $($_.Exception.Message)"
}
Write-Host ""

# ============================================================================
# FINAL REPORT
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    GATE 1 FINAL REPORT                     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$total = 13

# Count passes
if ($results.health_check) { $passed++ } else { Write-Host "✗ Test 1 (Health): FAILED" -ForegroundColor Red }
if ($results.login) { $passed++ } else { Write-Host "✗ Test 2 (Login): FAILED" -ForegroundColor Red }

if ($results.predictions.Count -eq 10) {
    $passed += 10
    Write-Host "✓ Tests 3-12 (Predictions): 10/10 PASSED" -ForegroundColor Green
} else {
    Write-Host "✗ Tests 3-12 (Predictions): $($results.predictions.Count)/10 PASSED" -ForegroundColor Red
}

if ($results.metrics) { $passed++ } else { Write-Host "✗ Test 13 (Metrics): FAILED" -ForegroundColor Red }

Write-Host ""
Write-Host "Summary:"
Write-Host "  Total Tests: $total"
Write-Host "  Passed: $passed"
Write-Host "  Failed: $($total - $passed)"
Write-Host "  Success Rate: $(($passed / $total * 100).ToString('F1'))%"
Write-Host ""

if ($results.predictions.Count -gt 0) {
    $allSingleMode = $results.predictions | Where-Object { $_.model_used -eq "primary" } | Measure-Object | ForEach-Object { $_.Count }
    Write-Host "Predictions Summary:"
    Write-Host "  Total created: $($results.predictions.Count)"
    Write-Host "  Served by primary: $allSingleMode"
    Write-Host "  All have SHAP: $(($results.predictions | Where-Object { $_.has_shap } | Measure-Object | ForEach-Object { $_.Count }))"
    Write-Host "  All have ECOA notice: $(($results.predictions | Where-Object { $_.has_adverse_action } | Measure-Object | ForEach-Object { $_.Count }))"
}

Write-Host ""
if ($results.errors.Count -gt 0) {
    Write-Host "Errors encountered:" -ForegroundColor Red
    foreach ($err in $results.errors) {
        Write-Host "  • $err" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($passed -eq $total) {
    Write-Host "🎉 GATE 1: RUNTIME STABILITY ✓✓✓ PASSED ✓✓✓" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "✓ API started successfully"
    Write-Host "✓ All 13 smoke tests completed"
    Write-Host "✓ 10 applications created with valid predictions"
    Write-Host "✓ Metrics endpoint operational"
    Write-Host "✓ Ready for GATE 2 (Model Routing Logic)"
    exit 0
} else {
    Write-Host "❌ GATE 1: RUNTIME STABILITY ✗ FAILED" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "Fix errors above and retry."
    exit 1
}
