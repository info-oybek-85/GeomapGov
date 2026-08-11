# SmartGeoAI v1.0 FINAL backup helper (PowerShell)
# workflow2 papkasida ishga tushiring.

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$release = "SmartGeoAI_v1_0_FINAL_$stamp"

New-Item -ItemType Directory -Force -Path ".\releases\$release" | Out-Null

# DB
if (Test-Path ".\db.sqlite3") {
    Copy-Item ".\db.sqlite3" ".\releases\$release\db.sqlite3"
}

# .env
if (Test-Path ".\.env") {
    Copy-Item ".\.env" ".\releases\$release\.env"
}

# Important data/model artifacts
New-Item -ItemType Directory -Force -Path ".\releases\$release\data" | Out-Null
if (Test-Path ".\data\gsor") {
    Copy-Item ".\data\gsor" ".\releases\$release\data\gsor" -Recurse
}
if (Test-Path ".\data\problem_datasets") {
    Copy-Item ".\data\problem_datasets" ".\releases\$release\data\problem_datasets" -Recurse
}
if (Test-Path ".\data\final_audit") {
    Copy-Item ".\data\final_audit" ".\releases\$release\data\final_audit" -Recurse
}

# Media
if (Test-Path ".\media") {
    Copy-Item ".\media" ".\releases\$release\media" -Recurse
}

# Requirements snapshot
.\venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 ".\releases\$release\requirements.freeze.txt"

# Django checks
.\venv\Scripts\python.exe manage.py check | Out-File -Encoding utf8 ".\releases\$release\django_check.txt"
.\venv\Scripts\python.exe manage.py showmigrations | Out-File -Encoding utf8 ".\releases\$release\migrations.txt"

Write-Host ""
Write-Host "FINAL backup yaratildi:"
Write-Host ".\releases\$release"
