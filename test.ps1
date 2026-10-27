$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot ".uv-python"

& (Join-Path $projectRoot ".tools\uv.exe") run pytest

