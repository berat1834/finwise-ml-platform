# GATE 1 Smoke Tests - March 6 2026

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    GATE 1: RUNTIME STABILITY - SMOKE TESTS" -ForegroundColor Cyan  
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# Test 1: Health Check
Write-Host "TEST 1 - Health Check" -ForegroundColor Green
for ($retry = 1; $retry -le 30; $retry++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/health' -UseBasicParsing -TimeoutSec 3
        if ($health.status -eq "up") {
            Write-Host "  OK - Status: up" -ForegroundColor Green
            Write-Host "  OK - Routing Mode: $($health.routing_mode)" -ForegroundColor Green  
            Write-Host "  OK - Canary Loaded: $($health.canary_loaded)" -ForegroundColor Green
            $passed++
            break
        }
    } catch {
        if ($retry -lt 30) {
            Write-Host "  Retry $retry/30..." -ForegroundColor Yellow
            Start-Sleep -Seconds 1
        } else {
            Write-Host "  FAILED" -ForegroundColor Red
            $failed++
        }
    }
}
Write-Host ""

# Test 2: Login
Write-Host "TEST 2 - Login" -ForegroundColor Green
$token = ""
try {
    $loginBody = '{"username":"admin","password":"admin123"}'
    $login = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/auth/login' -ContentType 'application/json' -Body $loginBody -TimeoutSec 5
    if ($login.access_token) {
        $token = $login.access_token
        Write-Host "  OK - Token obtained length $($token.Length)" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  FAILED - No token" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Tests 3-12: 10 Predictions
Write-Host "TESTS 3-12 - 10 Predictions" -ForegroundColor Green
$predCount = 0
$ages = @(28, 31, 34, 37, 40, 43, 46, 49, 52, 55)
$incomes = @(55000, 60000, 65000, 70000, 75000, 80000, 85000, 90000, 95000, 100000)

for ($i = 0; $i -lt 10; $i++) {
    try {
        $body = @{
            person_age = $ages[$i]
            person_income = $incomes[$i]
            person_emp_length = $i + 2
            loan_amnt = 20000
            loan_int_rate = 10.5
            loan_percent_income = 40.0
            cb_person_cred_hist_length = 5
            person_home_ownership = "RENT"
            loan_intent = "PERSONAL"
            loan_grade = "B"
            cb_person_default_on_file = "N"
        } | ConvertTo-Json -Compress
        
        $eval = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:5000/degerlendir' -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json' -Body $body -TimeoutSec 10
        
        if ($eval.application_id) {
            $predCount++
            $model = $eval.model_routing.served_by
            $num = $i + 1
            $appid = $eval.application_id
            $decision = $eval.tahmin
            Write-Host "  OK - Pred $num | App $appid | $decision | Model $model" -ForegroundColor Green
        }
    } catch {
        Write-Host "  FAILED - Pred $($i+1) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

$passed += $predCount
$failed += (10 - $predCount)
Write-Host ""

# Test 13: Metrics
Write-Host "TEST 13 - Metrics Endpoint" -ForegroundColor Green
try {
    $metrics = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/metrics' -UseBasicParsing -TimeoutSec 5
    if ($metrics -match 'finwise_model_route_total') {
        Write-Host "  OK - Prometheus metrics present" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  FAILED - No routing metrics" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Summary
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    GATE 1 RESULTS" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Total: 13 tests"
Write-Host "  Passed: $passed" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor Red
$successRate = [math]::Round($passed / 13 * 100, 1)
Write-Host "  Success Rate: $successRate%"
Write-Host ""

if ($passed -eq 13) {
    Write-Host "SUCCESS - GATE 1: RUNTIME STABILITY PASSED" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "OK - API started successfully"
    Write-Host "OK - All 13 smoke tests completed"  
    Write-Host "OK - 10 applications created"
    Write-Host "OK - Metrics endpoint operational"
    Write-Host "OK - Ready for GATE 2 (Model Routing Logic)"
    exit 0
} else {
    Write-Host "FAILED - GATE 1 (failed tests: $failed)" -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Cyan
    exit 1
}
