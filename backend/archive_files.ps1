$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path 'c:\src\FinWise-ML-Projem\backend\archive'
$files = @(
    'c:\src\FinWise-ML-Projem\backend\api_routes.py',
    'c:\src\FinWise-ML-Projem\backend\routes_v2.py',
    'c:\src\FinWise-ML-Projem\backend\dashboard.py',
    'c:\src\FinWise-ML-Projem\backend\monitoring.py',
    'c:\src\FinWise-ML-Projem\backend\monitoring_advanced.py',
    'c:\src\FinWise-ML-Projem\backend\sla_monitoring.py',
    'c:\src\FinWise-ML-Projem\backend\payment_processor.py',
    'c:\src\FinWise-ML-Projem\backend\payment_processor_v2.py',
    'c:\src\FinWise-ML-Projem\backend\add_features.py',
    'c:\src\FinWise-ML-Projem\backend\extract_assets.py',
    'c:\src\FinWise-ML-Projem\backend\eval.py'
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Move-Item -Path $f -Destination 'c:\src\FinWise-ML-Projem\backend\archive\' -Force
        Write-Host "Moved $f to archive"
    } else {
        Write-Host "File not found: $f"
    }
}
Write-Host "Task completed."
