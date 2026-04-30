<#
.SYNOPSIS
    Start the BattleCells World development server.
.DESCRIPTION
    Activates the virtual environment and launches Flask in debug mode.
    Set the SECRET_KEY environment variable before running in production.

    Usage:
        .\start.ps1             # debug mode (default)
        .\start.ps1 -Prod       # production-style (no reloader, no debugger)
        .\start.ps1 -Port 8080  # custom port
#>

param(
    [switch]$Prod,
    [int]$Port = 7856
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run  .\setup.ps1  first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "battlecells.db")) {
    Write-Host "Database not found. Run  .\setup.ps1  first." -ForegroundColor Red
    exit 1
}

$env:FLASK_APP = "app"

if ($Prod) {
    Write-Host "Starting BattleCells World on port $Port (production mode)..." -ForegroundColor Cyan
    & ".venv\Scripts\flask.exe" --app app run --host 0.0.0.0 --port $Port
}
else {
    $env:FLASK_DEBUG = "1"
    Write-Host "Starting BattleCells World on http://127.0.0.1:$Port (debug mode)..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
    & ".venv\Scripts\flask.exe" --app app run --debug --port $Port
}