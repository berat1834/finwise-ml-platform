@echo off
REM FinWise Lokal Production Setup - Windows Batch Script

echo.
echo ============================================================
echo FinWise Credit Risk API - Lokal Production
echo ============================================================
echo.

REM Check if .venv exists
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found!
    echo Run: python -m venv .venv
    pause
    exit /b 1
)

REM Menu
:menu
echo.
echo Choose option:
echo.
echo 1. Start API
echo 2. Check environment
echo 3. Run tests
echo 4. Backup database
echo 5. Exit
echo.

set /p choice="Enter option (1-5): "

if "%choice%"=="1" goto start_api
if "%choice%"=="2" goto check_env
if "%choice%"=="3" goto run_tests
if "%choice%"=="4" goto backup_db
if "%choice%"=="5" goto exit

:start_api
echo.
echo Starting FinWise API...
echo Database: finwise_production.db
echo Endpoint: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop
echo.
.venv\Scripts\python.exe app_api.py
goto menu

:check_env
echo.
echo Environment Check:
echo ==================
if exist ".venv\Scripts\python.exe" (
    echo [OK] Python venv
) else (
    echo [FAIL] Python venv
)
if exist "model_production.joblib" (
    echo [OK] Model file
) else (
    echo [FAIL] Model file
)
if exist "app_api.py" (
    echo [OK] API script
) else (
    echo [FAIL] API script
)
if exist "finwise_production.db" (
    echo [OK] Database
) else (
    echo [WARN] Database (will be created)
)
echo.
pause
goto menu

:run_tests
echo.
echo Running API tests...
echo (Make sure API is running on another terminal)
echo.
.venv\Scripts\python.exe test_api_comprehensive.py
echo.
pause
goto menu

:backup_db
if exist "finwise_production.db" (
    echo.
    set "timestamp=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    copy finwise_production.db "finwise_production_backup_%timestamp%.db"
    echo Backup created successfully
    echo.
) else (
    echo Database not found!
    echo.
)
pause
goto menu

:exit
echo.
echo Goodbye!
echo.
exit /b 0
