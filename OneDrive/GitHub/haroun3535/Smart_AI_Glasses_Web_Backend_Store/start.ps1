Set-Location $PSScriptRoot

if (-not (Test-Path ".\venv311\Scripts\python.exe")) {
    py -3.11 -m venv venv311
}

& .\venv311\Scripts\python.exe -m pip install --upgrade pip
& .\venv311\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "Open http://localhost:8000" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000/backend" -ForegroundColor Cyan
Write-Host "Products: http://localhost:8000/products" -ForegroundColor Cyan
& .\venv311\Scripts\python.exe run.py
