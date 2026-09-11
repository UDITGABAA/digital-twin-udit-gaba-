# One command to a demo-ready machine (Windows). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
# Installs deps, runs the tests (stop if red), builds the dashboard so uvicorn alone can serve
# it, then opens API (:8000) and Vite (:5173) in two windows. Fallback URL: http://localhost:8000
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
pip install -r requirements.txt
npm install --prefix dashboard
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "TESTS RED - do not demo"; exit 1 }
npm run build --prefix dashboard
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn server.app:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev --prefix dashboard"
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
Write-Host "Primary: http://localhost:5173   Fallback (API only, serves the built dashboard): http://localhost:8000"
