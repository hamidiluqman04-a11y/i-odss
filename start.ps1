# Start I-ODSS. Double-click start.bat, or run:
#     powershell -ExecutionPolicy Bypass -File start.ps1
#
# Opens two windows (backend and frontend) and then your browser.
# To stop I-ODSS, close those two windows.

param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$healthUrl = "http://127.0.0.1:8000/api/health/"

function Fail($text) { Write-Host ""; Write-Host "I-ODSS DID NOT START: $text" -ForegroundColor Red; exit 1 }
function BackendHealthy {
    try { (Invoke-WebRequest $healthUrl -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { $false }
}

# ── 1. Was setup run? ────────────────────────────────────────────────────
$missing = @()
if (-not (Test-Path $python)) { $missing += "Python environment" }
if (-not (Test-Path (Join-Path $root "backend\.env"))) { $missing += "backend\.env" }
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) { $missing += "frontend packages" }
if ($missing) { Fail "setup has not been run yet (missing: $($missing -join ', ')). Double-click setup.bat first." }

# ── 2. Is PostgreSQL running? ────────────────────────────────────────────
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService -and $pgService.Status -ne "Running") {
    Fail "PostgreSQL ($($pgService.Name)) is not running. Start it in the Windows 'Services' app, then try again."
}

# ── 3. Backend (Django) ──────────────────────────────────────────────────
if (BackendHealthy) {
    Write-Host "Backend is already running."
} else {
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
        Fail "port 8000 is used by another program. Close it (or restart the computer) and try again."
    }
    Write-Host "Starting the backend..."
    $backendCmd = "`$Host.UI.RawUI.WindowTitle = 'I-ODSS backend (close to stop)'; " +
                  "Set-Location '$root\backend'; " +
                  "& '$python' manage.py migrate --noinput; " +
                  "& '$python' manage.py runserver 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $backendCmd | Out-Null

    # Wait until Django answers, so the page never opens on "server not responding".
    $deadline = (Get-Date).AddSeconds(90)
    while (-not (BackendHealthy)) {
        if ((Get-Date) -gt $deadline) { Fail "the backend did not start within 90 seconds. Look at the 'I-ODSS backend' window for the error." }
        Start-Sleep -Milliseconds 700
    }
    Write-Host "Backend ready." -ForegroundColor Green
}

# ── 4. Frontend (React) — Vite opens the browser on whichever port it gets ──
Write-Host "Starting the frontend..."
$open = if ($NoBrowser) { "" } else { " -- --open" }
$frontendCmd = "`$Host.UI.RawUI.WindowTitle = 'I-ODSS frontend (close to stop)'; " +
               "Set-Location '$root\frontend'; npm run dev$open"
Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $frontendCmd | Out-Null

Write-Host ""
Write-Host "I-ODSS is starting. Your browser will open in a few seconds." -ForegroundColor Green
Write-Host "Log in with DEMO_USER_EMAIL / DEMO_USER_PASSWORD from backend\.env."
Write-Host "To stop I-ODSS, close the 'I-ODSS backend' and 'I-ODSS frontend' windows."
