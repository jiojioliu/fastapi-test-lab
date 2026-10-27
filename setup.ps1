param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$toolDir = Join-Path $projectRoot ".tools"
$uvPath = Join-Path $toolDir "uv.exe"
New-Item -ItemType Directory -Force -Path $toolDir | Out-Null

if (-not (Test-Path -LiteralPath $uvPath)) {
    Write-Host "Downloading the local uv runtime launcher..." -ForegroundColor Cyan
    $zipPath = Join-Path $toolDir "uv.zip"
    Invoke-WebRequest `
        -Uri "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" `
        -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $toolDir -Force
    Remove-Item -LiteralPath $zipPath
}

$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot ".uv-python"

Write-Host "Installing Python and project dependencies..." -ForegroundColor Cyan
& $uvPath sync --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Dependency setup failed."
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run .\start.ps1 or double-click start.bat."

