$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

Write-Host "Reinstalling greenlet + playwright..."
uv pip install --force-reinstall "greenlet>=3.1.1" "playwright>=1.45.0"

Write-Host "Installing Playwright Chromium..."
uv run playwright install chromium

Write-Host "Verifying imports..."
uv run python -c "import greenlet; from playwright.sync_api import sync_playwright; print('OK:', greenlet.__version__)"

Write-Host "Done. If greenlet still fails, install Microsoft Visual C++ 2015-2022 Redistributable (x64)."
