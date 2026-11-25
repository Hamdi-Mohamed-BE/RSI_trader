# READY FOR FTMO (owner 2026-11-20: "this bat will auto apply 0.75% risk for EAs, use DI off by default, add all rules we need all together in one place,
# so we just run it on the account and that's all").
# Fixed answers (FTMO 1-Step, the tested Best 1-Step setup):
#   * FTMO 1-Step guard (3% daily, 10% trailing max loss, +10% target with best day <= 50%), all 10 EAs, risk 0.75% per trade, Nasdaq 5M x0.75
#   * Nasdaq 5M DI OFF (tested default); USDJPY London DI stays ON (its tested setting); Nasdaq 5M stop = ATR x6 (current)
#   * open-risk caps 4.5x total / 3x per symbol (defaults)
#   * Weekend / holiday flat ON (FTMO funded: no weekend holds or breaks > 2 h)
#   * News guard: Funded = +-2 min (FTMO funded Standard rule), Challenge = OFF (evaluations are exempt)
#   * No-opposite rule OFF (FTMO only forbids opposite trades ACROSS accounts: run the same EAs on every FTMO account)
#   * news calendar downloaded now + daily Windows task "Calyx News Calendar" (06:00) created / refreshed
# Asked: Challenge or Funded (one key); on Funded also the risk per trade (Enter = 0.5%, the challenge always uses 0.75%). The installer then shows everything and asks you to type a confirmation before it restarts MT5.
[CmdletBinding()]
param([ValidateSet('', 'Challenge', 'Funded')][string]$Phase = '', [double]$FundedRisk = 0, [switch]$ValidateOnly)   # -FundedRisk 0.5 skips the funded risk question
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$news = Join-Path (Split-Path -Parent $here) 'Calyx News Guard'
$updaterBat = Join-Path $news 'Update News Calendar.bat'
$guarded = Join-Path $here '1-Step\Install-Best1Step-1Step.ps1'
foreach ($p in @($updaterBat, (Join-Path $news 'Update-NewsCalendar.ps1'), $guarded)) { if (-not (Test-Path -LiteralPath $p)) { throw "Missing file: $p" } }

Write-Host ''
Write-Host 'READY FOR FTMO - Best 1-Step, 10 EAs, FTMO 1-Step guard, 0.75% risk, all FTMO rules ON' -ForegroundColor Green
Write-Host 'Before you start: MT5 open and logged in on the FTMO account, NO open positions / orders, Algo Trading OFF.' -ForegroundColor Yellow
Write-Host 'After every FTMO reward you get a NEW account (new login): run this file again on the new account.' -ForegroundColor Yellow
Write-Host ''
if (-not $Phase) {
    if ($ValidateOnly) { $Phase = 'Challenge' }
    else {
        $a = (Read-Host 'Is this account the 1 = Challenge or 2 = Funded (FTMO Account)? [1]').Trim()
        if ($a -eq '' -or $a -eq '1') { $Phase = 'Challenge' } elseif ($a -eq '2') { $Phase = 'Funded' } else { throw 'Answer 1 or 2.' }
    }
}
$newsMode = if ($Phase -eq 'Funded') { '2' } else { 'OFF' }
# 2026-11-20 owner: "on funded stage make it ask how much risk we want". Challenge stays 0.75%.
$risk = 0.75
if ($Phase -eq 'Funded') {
    if ($FundedRisk -gt 0) { $risk = $FundedRisk }
    elseif (-not $ValidateOnly) {
        Write-Host ''
        Write-Host 'FUNDED RISK PER TRADE (% of the starting balance, the guard caps every entry to it; Nasdaq 5M gets 0.75x of it):' -ForegroundColor Cyan
        Write-Host '  0.5  = recommended for funded (more room under the 3% daily limit; ~$2.7k/month per $100k in the simulation)'
        Write-Host '  0.75 = same as the challenge (~$4.1k/month per $100k, but the worst day last month came within $242 of the daily limit)'
        Write-Host '  any value between 0.1 and 1.5'
        $a = (Read-Host 'Risk % per trade [0.5]').Trim()
        if (-not $a) { $risk = 0.5 }
        elseif (-not [double]::TryParse($a, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$risk)) { throw 'Type a number with a decimal point, e.g. 0.5' }
    } else { $risk = 0.5 }
    if ($risk -lt 0.1 -or $risk -gt 1.5) { throw 'Funded risk must be between 0.1 and 1.5 %.' }
}
$riskText = $risk.ToString('0.###', [Globalization.CultureInfo]::InvariantCulture)
Write-Host ("Phase {0}: risk {1}% per trade (Nasdaq 5M {2}%), Nasdaq DI OFF, weekend flat ON, news guard {3}, no-opposite OFF." -f $Phase, $riskText,
    ($risk * 0.75).ToString('0.####', [Globalization.CultureInfo]::InvariantCulture), $(if ($newsMode -eq 'OFF') { 'OFF (challenge is exempt)' } else { '+-2 min' })) -ForegroundColor Cyan

# 1. news calendar now (needed on the funded account) + daily task
if (-not $ValidateOnly) {
    Write-Host ''; Write-Host 'STEP 1/3 - news calendar' -ForegroundColor Cyan
    & cmd.exe /c "call `"$updaterBat`" -Quiet"
    if ($LASTEXITCODE -ne 0) {
        if ($Phase -eq 'Funded') { throw 'News calendar download FAILED: the news guard cannot protect a funded account without it. Fix the internet connection and run this again. Nothing installed.' }
        Write-Host 'News calendar download failed (the challenge does not need it). Continuing.' -ForegroundColor Yellow
    }
    Write-Host ''; Write-Host 'STEP 2/3 - daily calendar update task "Calyx News Calendar" (06:00 and 18:00)' -ForegroundColor Cyan
    $null = & (Join-Path $news 'Register-NewsCalendarTask.ps1')   # 2026-11-20: schtasks.exe broke on the space in the path
}

# 2. installer with every answer filled in (non-interactive: all 10 EAs, no per-EA questions)
Write-Host ''; Write-Host 'STEP 3/3 - install' -ForegroundColor Cyan
$args2 = @('-Phase', $Phase, '-RiskMode', 'PERCENT', '-RiskValue', $riskText, '-NasdaqDIFilter', 'OFF', '-UsdJpyDIFilter', 'ON', '-NasdaqStopVersion', 'NEW',
           '-TotalRiskCap', '4.5', '-SymbolRiskCap', '3', '-WeekendFlat', 'ON', '-NoOpposite', 'OFF', '-NewsGuard', $newsMode, '-NasdaqRiskFactor', '0.75')
if ($ValidateOnly) { $args2 += '-ValidateOnly' }
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $guarded @args2
$code = $LASTEXITCODE
Write-Host ''
if ($code -eq 0 -and -not $ValidateOnly) {
    Write-Host 'DONE. In MT5 check: 10 EA charts + Calyx Weekend Flat' $(if ($newsMode -ne 'OFF') { '+ Calyx News Guard' }) '- then turn Algo Trading ON yourself.' -ForegroundColor Green
    Write-Host 'Keep the total size of all FTMO accounts running these EAs at or below $400,000 (FTMO limit per client and per strategy).' -ForegroundColor Yellow
    if ($Phase -eq 'Challenge') { Write-Host 'When the challenge is passed, run this file again on the new FTMO Account and choose 2 = Funded.' -ForegroundColor Yellow }
} elseif ($code -ne 0) { Write-Host ("Installer stopped (exit {0}). Read the message above before running it again." -f $code) -ForegroundColor Red }
exit $code
