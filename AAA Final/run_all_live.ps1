param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Read-DotEnv {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing environment file: $Path"
    }

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $key, $value = $trimmed.Split("=", 2)
        $values[$key.Trim()] = $value.Trim()
    }
    return $values
}

function Require-Setting {
    param(
        [Parameter(Mandatory)][hashtable]$Values,
        [Parameter(Mandatory)][string]$Key,
        [Parameter(Mandatory)][string]$Expected,
        [Parameter(Mandatory)][string]$Bot
    )

    if (-not $Values.ContainsKey($Key) -or $Values[$Key].ToLowerInvariant() -ne $Expected.ToLowerInvariant()) {
        throw "$Bot is not live-ready: expected $Key=$Expected"
    }
}

$bots = @(
    [pscustomobject]@{
        Name = "Asia Breakout"
        Folder = "asia breakout"
        Launcher = "run_live.bat"
        ProcessMarker = "asia-breakout.exe"
        Required = @{
            ENABLE_TRADING = "true"
            DRY_RUN = "false"
            RISK_PCT = "1.00"
            MAX_LIVE_RISK_PCT = "1.00"
        }
    },
    [pscustomobject]@{
        Name = "AMD"
        Folder = "AMD"
        Launcher = "run_live.bat"
        ProcessMarker = "amd-bot.exe"
        Required = @{
            ENABLE_TRADING = "true"
            DRY_RUN = "false"
            MODEL_APPROVED = "true"
            RISK_PCT = "1.00"
        }
    },
    [pscustomobject]@{
        Name = "DmC"
        Folder = "DmC"
        Launcher = "run_live.bat"
        ProcessMarker = "dmc-bot.exe"
        Required = @{
            ENABLE_TRADING = "true"
            DRY_RUN = "false"
            LIVE_UNLOCK = "I_ACCEPT_DMC_LIVE_RISK"
            RISK_PCT = "1.00"
            LIVE_MAX_RISK_PCT = "1.00"
        }
    },
    [pscustomobject]@{
        Name = "EMA3"
        Folder = "EMA3"
        Launcher = "run_live_bot.bat"
        ProcessMarker = "ema3-live.exe"
        Required = @{
            LIVE_TRADING = "true"
            RISK_PCT_PER_TRADE = "1.00"
            MAX_PORTFOLIO_RISK_PCT = "1.00"
        }
    },
    [pscustomobject]@{
        Name = "US100 Weakness"
        Folder = "US100 weekness"
        Launcher = "run_live.bat"
        ProcessMarker = "nasdaq-weakness.exe"
        Required = @{
            ENABLE_TRADING = "true"
            DRY_RUN = "false"
            LIVE_UNLOCK = "I_ACCEPT_NASDAQ_WEAKNESS_LIVE_RISK"
            RISK_PCT = "1.00"
            MAX_DAILY_RISK_PCT = "1.00"
        }
    }
)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " AAA FINAL - ALL FIVE LIVE WORKERS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($bot in $bots) {
    $folder = Join-Path $Root $bot.Folder
    $launcher = Join-Path $folder $bot.Launcher
    $values = Read-DotEnv -Path (Join-Path $folder ".env")

    if (-not (Test-Path -LiteralPath $launcher)) {
        throw "Missing launcher for $($bot.Name): $launcher"
    }
    foreach ($item in $bot.Required.GetEnumerator()) {
        Require-Setting -Values $values -Key $item.Key -Expected $item.Value -Bot $bot.Name
    }
    Write-Host ("[READY] {0}" -f $bot.Name) -ForegroundColor Green
}

Write-Host ""
Write-Host "Checking the account already connected in MetaTrader 5..."
$accountCheck = @'
import MetaTrader5 as mt5
import sys

if not mt5.initialize():
    print(f"MT5 initialization failed: {mt5.last_error()}")
    sys.exit(2)

account = mt5.account_info()
if account is None:
    print(f"MT5 account unavailable: {mt5.last_error()}")
    mt5.shutdown()
    sys.exit(3)

print(
    f"Account {account.login} | {account.server} | {account.name} | "
    f"balance {account.balance:.2f} {account.currency} | "
    f"equity {account.equity:.2f} | leverage 1:{account.leverage}"
)

if not account.trade_allowed or not account.trade_expert:
    print("Automated trading is not permitted by the connected account/terminal.")
    mt5.shutdown()
    sys.exit(4)

mt5.shutdown()
'@

Push-Location (Join-Path $Root "EMA3")
try {
    $python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "EMA3 virtual environment is missing: $python"
    }
    $accountCheck | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw "Connected MT5 account check failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if ($CheckOnly) {
    Write-Host ""
    Write-Host "All five live environments and the connected MT5 account are ready." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " STARTING WORKERS" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

$processes = @(Get-CimInstance Win32_Process)
foreach ($bot in $bots) {
    $folder = Join-Path $Root $bot.Folder
    $launcher = Join-Path $folder $bot.Launcher
    $alreadyRunning = @(
        $processes | Where-Object {
            $_.CommandLine -and
            $_.CommandLine.Contains($folder) -and
            $_.CommandLine.Contains($bot.ProcessMarker)
        }
    ).Count -gt 0

    if ($alreadyRunning) {
        Write-Host ("[SKIP]  {0} is already running" -f $bot.Name) -ForegroundColor DarkYellow
        continue
    }

    $quotedLauncher = '"' + $launcher + '"'
    $startArguments = @{
        FilePath = $env:ComSpec
        ArgumentList = @("/d", "/c", $quotedLauncher)
        WorkingDirectory = $folder
        WindowStyle = "Hidden"
        PassThru = $true
    }
    $process = Start-Process @startArguments
    Write-Host ("[START] {0} | launcher PID {1}" -f $bot.Name, $process.Id) -ForegroundColor Green
}

Write-Host ""
Write-Host "All five live workers have been started." -ForegroundColor Cyan
Write-Host "Each bot targets 1% risk and uses the broker minimum lot when necessary." -ForegroundColor Cyan
Write-Host "XAU workers share a 4% reserved-risk cap; US100 has its own 1% cap." -ForegroundColor Cyan
Write-Host "Do not launch overlapping copies: the duplicate guard only applies to this master launcher." -ForegroundColor Cyan
