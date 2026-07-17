#Requires -Version 5.1
<#
.SYNOPSIS
    SprayLine final_version_0718_v2 — Docker startup script

.DESCRIPTION
    Modes (-Mode):
      start   - Build and start all services (default)
      restart - Rebuild API container only
      status  - Show current service status
      down    - Stop all services (keep volume data)
      reset   - DANGER: full reset, deletes all DB data

.PARAMETER Mode
    Execution mode (default: start)

.PARAMETER WithData
    Also start the dataprocess service (--profile data)

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Mode status
    .\start.ps1 -Mode restart
    .\start.ps1 -Mode start -WithData
    .\start.ps1 -Mode reset
    .\start.ps1 -Mode down
#>

param(
    [ValidateSet("start", "restart", "status", "down", "reset")]
    [string]$Mode = "start",
    [switch]$WithData
)

$SCRIPT_DIR   = $PSScriptRoot
$COMPOSE_FILE = Join-Path $SCRIPT_DIR "docker-compose.yml"
$DOCKERFILE   = Join-Path $SCRIPT_DIR "Dockerfile"
$REQUIREMENTS = Join-Path $SCRIPT_DIR "requirements.txt"

$DB_PORT       = 5433
$API_PORT      = 8011
$FRONTEND_PORT = 8012
$ENGINEER_PORT = 8013

function Write-Header([string]$text) {
    Write-Host ""
    Write-Host ("=" * 58) -ForegroundColor Cyan
    Write-Host "  [SprayLine] $text" -ForegroundColor Cyan
    Write-Host ("=" * 58) -ForegroundColor Cyan
}
function Write-Step([string]$text)  { Write-Host "  >> $text" -ForegroundColor Yellow }
function Write-OK([string]$text)    { Write-Host "  [OK] $text" -ForegroundColor Green }
function Write-Warn([string]$text)  { Write-Host "  [!!] $text" -ForegroundColor Yellow }
function Write-Fail([string]$text)  { Write-Host "  [XX] $text" -ForegroundColor Red }
function Write-Info([string]$text)  { Write-Host "       $text" -ForegroundColor DarkGray }

function Invoke-Validate {
    Write-Header "Environment Validation"
    $allOk = $true

    Write-Step "Docker daemon..."
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-OK "Docker daemon is running" }
    else { Write-Fail "Docker daemon is not running."; $allOk = $false }

    Write-Step "docker compose..."
    docker compose version | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-OK "docker compose is available" }
    else { Write-Fail "docker compose not found"; $allOk = $false }

    Write-Step "Required files..."
    foreach ($f in @($COMPOSE_FILE, $DOCKERFILE, $REQUIREMENTS)) {
        if (Test-Path $f) { Write-OK (Split-Path $f -Leaf) }
        else { Write-Fail "Not found: $f"; $allOk = $false }
    }

    if (-not $allOk) { Write-Host ""; Write-Fail "Validation failed."; exit 1 }
    Write-OK "All checks passed."
}

function Show-Status {
    Write-Header "Service Status"
    docker compose ps
    Write-Host ""
    Write-Info "Manager UI    : http://localhost:$FRONTEND_PORT"
    Write-Info "Engineer UI   : http://localhost:$ENGINEER_PORT"
    Write-Info "API Swagger   : http://localhost:$API_PORT/docs"
    Write-Info "DB connection : localhost:$DB_PORT  user=postgres  db=sprayline"
}

function Invoke-Down {
    Write-Header "Stop Services (data preserved)"
    docker compose down
    if ($LASTEXITCODE -eq 0) { Write-OK "All containers stopped"; Write-OK "External DB volume [final_version_0627_sprayline_pgdata] kept" }
    else { Write-Fail "docker compose down failed"; exit 1 }
}

function Confirm-Reset {
    Write-Host ""
    Write-Host ("  " + ("!" * 48)) -ForegroundColor Red
    Write-Host "  !! WARNING - RESET MODE !!" -ForegroundColor Red
    Write-Host ("  " + ("!" * 48)) -ForegroundColor Red
    Write-Host ""
    Write-Host "  This will permanently delete all DB data." -ForegroundColor Red
    Write-Host "  Type  YES DELETE ALL DATA  to confirm:" -ForegroundColor Yellow
    $confirm = Read-Host "  Confirm"
    if ($confirm -ne "YES DELETE ALL DATA") { Write-Warn "Cancelled."; exit 0 }
    docker compose down --volumes
    if ($LASTEXITCODE -ne 0) { Write-Fail "docker compose down --volumes failed"; exit 1 }
    Write-OK "All data cleared"
}

function Wait-DbHealthy([int]$maxSec = 90) {
    Write-Step "Waiting for DB health check (max ${maxSec}s)..."
    $elapsed = 0
    while ($elapsed -lt $maxSec) {
        $psOut = docker compose ps db 2>$null | Out-String
        if ($psOut -match "healthy") { Write-OK "DB is ready"; return $true }
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Info "  ... ${elapsed}s / ${maxSec}s"
    }
    Write-Fail "DB health check timed out."
    return $false
}

function Wait-DbSetup([int]$maxSec = 60) {
    Write-Step "Waiting for db-setup to finish (max ${maxSec}s)..."
    $psOut = docker compose --profile setup ps -a db-setup 2>$null | Out-String
    if ($psOut -match "Exited \(0\)") { Write-OK "db-setup completed"; return $true }
    $elapsed = 0
    while ($elapsed -lt $maxSec) {
        $psOut = docker compose --profile setup ps -a db-setup 2>$null | Out-String
        if ($psOut -match "Exited \(0\)") { Write-OK "db-setup completed"; return $true }
        if (($psOut -match "Exited") -and ($psOut -notmatch "Exited \(0\)")) {
            Write-Fail "db-setup failed. Run: docker compose --profile setup logs db-setup"
            return $false
        }
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Info "  ... ${elapsed}s / ${maxSec}s"
    }
    Write-Fail "db-setup timed out."
    return $false
}

function Invoke-Start {
    Write-Header "Start 0718_v2 Services (existing 0627 database)"

    Write-Info "Step 1/2: Starting external PostgreSQL volume (no db-setup)"
    docker compose up -d db
    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to start db."; exit 1 }

    $dbOk = Wait-DbHealthy -maxSec 90
    if (-not $dbOk) { exit 1 }

    Write-Warn "0718_v2 is configured for final_version_0627_sprayline_pgdata."
    Write-Warn "Normal start will NOT run db-setup and will NOT start dataprocess."

    Write-Info "Step 2/2: Build and start api + frontend + engineer"
    docker compose up -d --build api frontend engineer
    if ($LASTEXITCODE -ne 0) { Write-Fail "docker compose up failed."; exit 1 }

    if ($WithData) {
        Write-Warn "-WithData was ignored to protect the teammate's existing database."
    }

    Write-Header "Startup Complete"
    docker compose ps
    Write-Host ""
    Write-OK "Manager UI    : http://localhost:$FRONTEND_PORT"
    Write-OK "Engineer UI   : http://localhost:$ENGINEER_PORT"
    Write-OK "API endpoint  : http://localhost:$API_PORT"
    Write-OK "Swagger UI    : http://localhost:$API_PORT/docs"
    Write-OK "DB connection : localhost:$DB_PORT  user=postgres  db=sprayline"
    Write-OK "Existing DB volume preserved; db-setup/dataprocess not started"
}

function Invoke-Restart {
    Write-Header "Restart API + Engineer UI"
    docker compose up -d --build api engineer
    if ($LASTEXITCODE -ne 0) { Write-Fail "Restart failed."; exit 1 }
    Write-OK "API restarted: http://localhost:$API_PORT"
    Write-OK "Engineer UI restarted: http://localhost:$ENGINEER_PORT"
}

Set-Location $SCRIPT_DIR
switch ($Mode) {
    "status"  { Invoke-Validate; Show-Status }
    "down"    { Invoke-Validate; Invoke-Down }
    "reset"   { Invoke-Validate; Write-Fail "Reset is disabled in 0718_v2 to protect final_version_0627_sprayline_pgdata."; exit 1 }
    "restart" { Invoke-Validate; Invoke-Restart }
    "start"   { Invoke-Validate; Invoke-Start }
}
