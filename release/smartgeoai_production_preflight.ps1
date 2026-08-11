param(
    [string]$Python = ".\venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==============================================="
Write-Host " SmartGeoAI v1.0 FINAL - Production Preflight"
Write-Host "==============================================="
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "[FAIL] Python topilmadi: $Python"
    exit 1
}

$fail = 0

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host ">>> $Name"
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] $Name"
            $script:fail += 1
        } else {
            Write-Host "[PASS] $Name"
        }
    }
    catch {
        Write-Host "[FAIL] $Name"
        Write-Host $_
        $script:fail += 1
    }
}

Run-Step "Django system check" {
    & $Python manage.py check
}

Run-Step "Django deployment security check" {
    & $Python manage.py check --deploy
}

Run-Step "Migrations check" {
    & $Python manage.py migrate --check
}

Run-Step "Final audit" {
    & $Python manage.py smartgeoai_final_audit
}

Run-Step "Final smoke test" {
    & $Python manage.py smartgeoai_smoke_test
}

Write-Host ""
Write-Host ">>> Static files"
if (Test-Path ".\static") {
    Write-Host "[PASS] static papka mavjud"
} else {
    Write-Host "[FAIL] static papka topilmadi"
    $fail += 1
}

Write-Host ""
Write-Host ">>> Media files"
if (Test-Path ".\media") {
    Write-Host "[PASS] media papka mavjud"
} else {
    Write-Host "[WARN] media papka topilmadi yoki hali ishlatilmagan"
}

Write-Host ""
Write-Host ">>> Important artifacts"

$files = @(
    ".\data\gsor\gsor_evaluation.json",
    ".\data\gsor\gsor_predictions.csv",
    ".\data\problem_datasets\verified_routing_dataset.csv",
    ".\data\final_audit\smartgeoai_final_audit.json",
    ".\data\final_audit\smartgeoai_smoke_test.json"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        $size = (Get-Item $f).Length
        Write-Host "[PASS] $f ($size bytes)"
    } else {
        Write-Host "[WARN] $f topilmadi"
    }
}

Write-Host ""
Write-Host "==============================================="

if ($fail -eq 0) {
    Write-Host " STATUS: PRODUCTION PREFLIGHT PASSED"
    Write-Host " Keyingi qadam: deploy + manual E2E test"
    exit 0
} else {
    Write-Host " STATUS: TUZATISHLAR KERAK"
    Write-Host " FAIL soni: $fail"
    exit 1
}
