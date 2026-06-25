$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (!(Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Fill TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, and broker settings, then run this script again."
    exit 1
}

.\.venv\Scripts\profit-hacker-bot.exe
