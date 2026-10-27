param(
    [int]$Port = 8000,
    [switch]$Public
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$uvPath = Join-Path $projectRoot ".tools\uv.exe"
if (-not (Test-Path -LiteralPath $uvPath)) {
    & (Join-Path $projectRoot "setup.ps1")
}

$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot ".uv-python"

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".venv\pyvenv.cfg"))) {
    & (Join-Path $projectRoot "setup.ps1")
}

$hostAddress = if ($Public) { "0.0.0.0" } else { "127.0.0.1" }
Write-Host ""
Write-Host "FastAPI Test Lab" -ForegroundColor Cyan
Write-Host "Dashboard : http://127.0.0.1:$Port"
Write-Host "Swagger   : http://127.0.0.1:$Port/docs"
Write-Host "Accounts  : customer/customer123  |  admin/admin123"
Write-Host "Guest     : read-only entry from the login page"
Write-Host "Bind      : ${hostAddress}:$Port"
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

& $uvPath run uvicorn app.main:app --host $hostAddress --port $Port --log-level info

