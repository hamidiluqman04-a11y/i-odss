# Creates the PostgreSQL user and database described in backend\.env.
#
# Run from the backend folder:
#     powershell -ExecutionPolicy Bypass -File scripts\setup_db.ps1
#
# psql will ask for the password of the "postgres" admin account (the one
# you chose when installing PostgreSQL). Safe to run more than once.

$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) { throw "backend\.env not found. Copy .env.example to .env first." }

# Read KEY=VALUE lines from .env
$cfg = @{}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z_]+)\s*=\s*(.*)\s*$') { $cfg[$Matches[1]] = $Matches[2] }
}
foreach ($key in "DB_NAME", "DB_USER", "DB_PASSWORD") {
    if (-not $cfg[$key] -or $cfg[$key] -eq "change-me") { throw "Set $key in backend\.env first." }
}
# Only allow simple names/passwords so they can be placed safely in SQL.
if ($cfg.DB_NAME -notmatch '^[a-z_][a-z0-9_]*$' -or $cfg.DB_USER -notmatch '^[a-z_][a-z0-9_]*$') {
    throw "DB_NAME and DB_USER may only contain lowercase letters, digits and underscores."
}
if ($cfg.DB_PASSWORD -notmatch '^[A-Za-z0-9_\-]+$') {
    throw "DB_PASSWORD may only contain letters, digits, '_' and '-'."
}

$psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $psql) { throw "psql.exe not found under C:\Program Files\PostgreSQL." }

$dbHost = if ($cfg.DB_HOST) { $cfg.DB_HOST } else { "localhost" }
$dbPort = if ($cfg.DB_PORT) { $cfg.DB_PORT } else { "5432" }

# CREATEDB lets Django create a temporary database when running tests.
$sql = @'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{0}') THEN
    CREATE ROLE {0} LOGIN CREATEDB PASSWORD '{1}';
  ELSE
    ALTER ROLE {0} WITH LOGIN CREATEDB PASSWORD '{1}';
  END IF;
END
$$;
SELECT 'CREATE DATABASE {2} OWNER {0}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{2}')\gexec
'@ -f $cfg.DB_USER, $cfg.DB_PASSWORD, $cfg.DB_NAME

Write-Host "Using $($psql.FullName)"
Write-Host "Creating user '$($cfg.DB_USER)' and database '$($cfg.DB_NAME)' on ${dbHost}:${dbPort}..."
$sql | & $psql.FullName -U postgres -h $dbHost -p $dbPort -d postgres -v ON_ERROR_STOP=1 -q
if ($LASTEXITCODE -ne 0) { throw "psql failed (exit code $LASTEXITCODE)." }
Write-Host "Done. Next: ..\.venv\Scripts\python manage.py migrate"
