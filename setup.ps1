# I-ODSS one-time setup. Double-click setup.bat, or run:
#     powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Safe to run again at any time: every step checks first and skips what is
# already done. Needs Python 3.13, Node.js 20+ and PostgreSQL installed.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $root ".venv\Scripts\python.exe"
$envFile = Join-Path $backend ".env"

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Ok($text) { Write-Host "    $text" -ForegroundColor Green }
function Fail($text) { Write-Host ""; Write-Host "SETUP STOPPED: $text" -ForegroundColor Red; exit 1 }

# ── 1. Check the tools are installed ─────────────────────────────────────
Step "Checking Python, Node.js and PostgreSQL"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail "Python is not installed (https://www.python.org/downloads/)." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail "Node.js is not installed (https://nodejs.org/)." }
$psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $psql) { Fail "PostgreSQL is not installed (https://www.postgresql.org/download/windows/)." }
Ok "All found."

# ── 2. Python environment and packages ───────────────────────────────────
Step "Python environment (.venv)"
if (-not (Test-Path $python)) {
    python -m venv (Join-Path $root ".venv")
    if ($LASTEXITCODE -ne 0) { Fail "Could not create .venv." }
}
& $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "Installing Python packages failed (see the message above)." }
Ok "Python packages installed."

# ── 3. backend\.env with random secrets ──────────────────────────────────
Step "Settings file (backend\.env)"
if (Test-Path $envFile) {
    Ok "Already exists - left unchanged."
} else {
    # Random values; no special characters so they are safe in SQL and URLs.
    function NewSecret($length) {
        $chars = [char[]]"abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        $bytes = New-Object byte[] $length
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    }
    $text = Get-Content (Join-Path $backend ".env.example") -Raw
    $text = $text -replace "DJANGO_SECRET_KEY=change-me", "DJANGO_SECRET_KEY=$(NewSecret 50)"
    $text = $text -replace "DB_PASSWORD=change-me", "DB_PASSWORD=$(NewSecret 24)"
    $text = $text -replace "DEMO_USER_PASSWORD=change-me", "DEMO_USER_PASSWORD=$(NewSecret 14)"
    [System.IO.File]::WriteAllText($envFile, $text)
    Ok "Created with random secrets (Git never commits this file)."
}

# ── 4. Database (only asks for the postgres password if needed) ──────────
Step "PostgreSQL database"
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService -and $pgService.Status -ne "Running") {
    Fail "The PostgreSQL service ($($pgService.Name)) is not running. Start it from the Windows 'Services' app, then run setup again."
}
Push-Location $backend
try {
    & $python manage.py shell -c "from django.db import connection; connection.ensure_connection()" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Ok "Database already reachable."
    } else {
        Write-Host "    Creating the I-ODSS database. Type the password of your PostgreSQL 'postgres'"
        Write-Host "    admin account (chosen when you installed PostgreSQL); the typing stays hidden."
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $backend "scripts\setup_db.ps1")
        if ($LASTEXITCODE -ne 0) { Fail "Creating the database failed (wrong postgres password?)." }
        Ok "Database created."
    }

    & $python manage.py migrate --noinput | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail "Creating the database tables failed." }
    Ok "Tables up to date."

    & $python manage.py create_demo_user | Out-Null
    if ($LASTEXITCODE -ne 0) { Fail "Creating the demo account failed." }
    Ok "Demo account ready."
} finally {
    Pop-Location
}

# ── 5. Frontend packages ─────────────────────────────────────────────────
Step "Frontend packages (npm)"
Push-Location $frontend
try {
    npm install --no-audit --no-fund --loglevel=error
    if ($LASTEXITCODE -ne 0) { Fail "npm install failed (see the message above)." }
} finally {
    Pop-Location
}
Ok "Installed."

# ── Done ─────────────────────────────────────────────────────────────────
$demo = Get-Content $envFile | Where-Object { $_ -match '^DEMO_USER_(EMAIL|PASSWORD)=' }
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Demo login (also stored in backend\.env):"
$demo | ForEach-Object { Write-Host "    $_" }
Write-Host "Next: double-click start.bat"
