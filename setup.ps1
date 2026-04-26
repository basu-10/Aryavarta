<#
.SYNOPSIS
    First-time project setup: creates a virtual environment, installs dependencies,
    and initialises + seeds the database.
.DESCRIPTION
    Safe to run multiple times:
      - Skips venv creation if .venv already exists.
      - flask init-db uses CREATE TABLE IF NOT EXISTS -- no data loss.
      - flask seed-world is guarded: skips if forts/camps already exist in the DB.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "=== BattleCells World - Setup ===" -ForegroundColor Cyan

# 1. Virtual environment
if (Test-Path ".venv") {
    Write-Host "[1/4] Virtual environment already exists - skipping creation." -ForegroundColor Green
} else {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "      Done." -ForegroundColor Green
}

# 2. Install dependencies
Write-Host "[2/4] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".venv\Scripts\pip.exe" install --quiet -r requirements.txt
Write-Host "      Done." -ForegroundColor Green

# 3. Init database
Write-Host "[3/4] Initialising database (CREATE TABLE IF NOT EXISTS -- safe to re-run)..." -ForegroundColor Yellow
$env:FLASK_APP = "app"
& ".venv\Scripts\flask.exe" --app app init-db
Write-Host "      Done." -ForegroundColor Green

# 4. Seed world
Write-Host "[4/4] Seeding world map (skips automatically if already seeded)..." -ForegroundColor Yellow
& ".venv\Scripts\flask.exe" --app app seed-world
Write-Host "      Done." -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete. Run  .\start.ps1  to launch the server." -ForegroundColor Cyan
Write-Host ""