# Shared install-time choices for every Calyx portfolio installer (owner request 2026-11-03: "add questions that will ask to use
# old or new version of the nasdaq 5m and enable or disable ... all the guards ... use full descriptions").
# Pure functions: no MT5, account or file access. The single source is _00 Live profiles\Calyx-InstallChoices.ps1; package builds
# copy it next to each installer. Defaults always reproduce the current tested behaviour (press Enter to keep it).

function Write-CalyxNasdaqVersionHelp {
    Write-Host ''
    Write-Host 'NASDAQ 5M CANDLE MOMENTUM - which initial stop-loss?' -ForegroundColor Cyan
    Write-Host '  Both versions: same 09:30 New York M5 signal (EMA12 + optional DI14 filter), no take profit, the stop then trails'
    Write-Host '  6 x ATR(14) behind the best price once the trade is +1R, positions may stay open overnight and over weekends.'
    Write-Host '  1 = NEW (default, deployed 2026-11-02): initial stop = 6 x ATR(14) on M5 at entry. It adapts to volatility:'
    Write-Host '      median 0.61% of price, about 0.28% in quiet markets and 1.2% in fast ones. Native MT5 2019-2026, 1% risk:'
    Write-Host '      +164%, worst closed drawdown 24%, worst year -11.6% (2020); last 5 years +113%, last 12 months +31%.'
    Write-Host '  2 = OLD (2026-09-28 to 2026-11-02): initial stop = 0.60% of the entry price, the same distance every day.'
    Write-Host '      Native MT5 2019-2026, 1% risk: +162%, worst closed drawdown 39%, worst year -27.5% (2020);'
    Write-Host '      last 5 years +220% and last 12 months +48% (most of it from the strong 2025 trend).'
    Write-Host '  Backtests are history, not a forecast. The NEW stop is steadier over 2019-2026; the OLD one earned more since late 2021.' -ForegroundColor Yellow
}

function Read-CalyxNasdaqVersion([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('NEW', 'OLD')) { throw 'Nasdaq 5M version must be NEW or OLD.' }; return $Current }
    if ($NoPrompt) { return 'NEW' }
    Write-CalyxNasdaqVersionHelp
    $answer = (Read-Host 'Nasdaq 5M stop version: 1 = NEW ATR(14) x 6, 2 = OLD 0.60% of price [1]').Trim()
    if (-not $answer -or $answer -eq '1') { return 'NEW' }
    if ($answer -eq '2') { return 'OLD' }
    throw 'Choose 1 (NEW) or 2 (OLD).'
}

# Applies the chosen stop to a Nasdaq 5M input table (hashtable / ordered dictionary of SET values). Only these two inputs differ.
function Set-CalyxNasdaqVersion($Inputs, [string]$Version) {
    if (-not $Version) { $Version = 'NEW' }   # integrity checks run before the question: blank = the default NEW stop
    foreach ($key in @('InpStopMode', 'InpInitialStopATR', 'InpInitialStopPercent')) {
        if (-not $Inputs.Contains($key)) { throw "Nasdaq 5M preset lacks $key; cannot apply the stop version." }
    }
    if ($Version -eq 'OLD') {
        if ([double]::Parse([string]$Inputs['InpInitialStopPercent'], [Globalization.CultureInfo]::InvariantCulture) -ne 0.60) { throw 'OLD version needs InpInitialStopPercent=0.60.' }
        $Inputs['InpStopMode'] = '2'; $Inputs['InpInitialStopATR'] = '4.0'
    } elseif ($Version -eq 'NEW') {
        $Inputs['InpStopMode'] = '0'; $Inputs['InpInitialStopATR'] = '6.0'
    } else { throw 'Nasdaq 5M version must be NEW or OLD.' }
}

function Get-CalyxNasdaqVersionText([string]$Version) {
    if ($Version -eq 'OLD') { 'OLD stop: 0.60% of entry price (2026-09-28 preset)' } else { 'NEW stop: 6 x ATR(14) (2026-11-02 preset)' }
}

function Write-CalyxAdaptiveHelp {
    Write-Host ''
    Write-Host 'PORTFOLIO RISK GOVERNOR (Recommended Adaptive) - ON or OFF?' -ForegroundColor Cyan
    Write-Host '  It only changes the risk of NEW entries. Open trades, their stops and targets are never touched.'
    Write-Host '  The five news EAs never use it (they keep their own news risk).'
    Write-Host '  ON (default) - every other EA applies these three rules to itself:'
    Write-Host "    1. Daily stop: no new entries for the rest of the server day once today's CLOSED losses reach 5% of the balance."
    Write-Host '    2. Drawdown taper: entry risk x0.5 while the account is 4% or more below its closed-balance peak, x0.25 at 7% or more.'
    Write-Host '    3. Loss-streak taper: entry risk x0.5 after 3 losing trades in a row of that EA, x0.25 after 5; a win resets it.'
    Write-Host '  OFF - every EA always trades its full chosen risk, including during losing streaks and drawdowns.'
    Write-Host '  The published Full EA / Recommended Adaptive results were built with it ON; OFF is not separately tested.' -ForegroundColor Yellow
}

function Read-CalyxOnOff([string]$Current, [bool]$NoPrompt, [string]$Question, [string]$Default = 'ON') {
    if ($Current) { if ($Current -notin @('ON', 'OFF')) { throw "$Question must be ON or OFF." }; return $Current }
    if ($NoPrompt) { return $Default }
    $answer = (Read-Host ("$Question ON or OFF [$Default]")).Trim().ToUpperInvariant()
    if (-not $answer) { return $Default }
    if ($answer -notin @('ON', 'OFF')) { throw "$Question must be ON or OFF." }
    return $answer
}

function Read-CalyxAdaptiveControls([string]$Current, [bool]$NoPrompt) {
    if (-not $Current -and -not $NoPrompt) { Write-CalyxAdaptiveHelp }
    return Read-CalyxOnOff $Current $NoPrompt 'Portfolio risk governor'
}

# 2026-11-03 owner: "make ask for cap option when installing the bat ... 4.5, 6, 8 and no cap and 3x, no cap per symbol".
# Prop Ready guard family only (Prop ready / Codex, FTMO any-broker, Best Prop 9 / 15). Enter keeps the tested 4.5 R / 3 R.
function Write-CalyxRiskCapHelp {
    Write-Host ''
    Write-Host 'OPEN-RISK CAPS - how much stop-loss risk may be open at the same time?' -ForegroundColor Cyan
    Write-Host '  R = your chosen risk per trade, measured on the starting balance. Every open trade counts its initial stop-loss risk.'
    Write-Host '  TOTAL cap: a new entry waits while all open trades plus the new one would exceed this many R.'
    Write-Host '    1 = 4.5 R (default, tested)   2 = 6 R   3 = 8 R   4 = no total cap'
    Write-Host '  PER-SYMBOL cap: the same rule for the trades on one symbol (gold, Nasdaq or USDJPY).'
    Write-Host '    1 = 3 R (default, tested)   2 = no per-symbol cap'
    Write-Host '  All other guards stay ON. The 3% daily reserve counts each open trade at 1.25 x its risk, so open risk stops near'
    Write-Host '  2.4% of the balance anyway (= 2.4 R at 1% risk, 4.8 R at 0.5%). At 1% risk 4.5 / 6 / 8 / none therefore behave the same.'
    Write-Host '  FTMO $100k replay (2026-11-03): 6 R = same pass rate at 1%, same Monte Carlo but a worse 2021-23 history at 0.5%.' -ForegroundColor Yellow
    Write-Host '  8 R and "no cap" were not tested. Bigger caps allow more trades (often several gold EAs) to lose at the same time.' -ForegroundColor Yellow
}

function Read-CalyxTotalRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('4.5', '6', '8', 'NONE')) { throw 'Total open-risk cap must be 4.5, 6, 8 or NONE.' }; return $Current }
    if ($NoPrompt) { return '4.5' }
    Write-CalyxRiskCapHelp
    $answer = (Read-Host 'Total open-risk cap: 1 = 4.5 R, 2 = 6 R, 3 = 8 R, 4 = no cap [1]').Trim()
    $choice = @{ '' = '4.5'; '1' = '4.5'; '2' = '6'; '3' = '8'; '4' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1, 2, 3 or 4.' }
    return $choice
}

function Read-CalyxSymbolRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('3', 'NONE')) { throw 'Per-symbol cap must be 3 or NONE.' }; return $Current }
    if ($NoPrompt) { return '3' }
    $answer = (Read-Host 'Per-symbol open-risk cap: 1 = 3 R, 2 = no cap [1]').Trim()
    $choice = @{ '' = '3'; '1' = '3'; '2' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1 or 2.' }
    return $choice
}

# Guard input value: the multiple, or 0 = that cap OFF.
function Get-CalyxCapMultiple([string]$Choice) { if ($Choice -eq 'NONE') { '0' } else { $Choice } }

# "450.00 (4.5 R)" or "no cap"; $Unit = one R in account currency.
function Get-CalyxCapText([string]$Choice, [double]$Unit) {
    if ($Choice -eq 'NONE') { return 'no cap' }
    $m = [double]::Parse($Choice, [Globalization.CultureInfo]::InvariantCulture)
    return ('{0:N2} ({1} R)' -f ($Unit * $m), $Choice)
}

# >>> Calyx Weekend Flat (owner 2026-11-11: "update all profiles to go flat before weekend and holidays") >>>
# FTMO Standard / 1-Step FTMO Accounts may not hold positions through market breaks longer than 2 hours (weekends, holiday closures).
# ON (default) adds one extra chart running "Calyx Weekend Flat": it closes the account's EA positions and deletes EA pending orders
# 30 minutes before every break of 2 hours or more (from the broker's own session times) and before US / Christmas / New Year holiday closures.
# It never opens trades and never touches manual trades. Source and rules: _00 Live profiles\Calyx Weekend Flat\README.md
function Write-CalyxWeekendFlatHelp {
    Write-Host ''
    Write-Host 'WEEKEND / HOLIDAY FLAT - close every EA trade before the market closes for the weekend or a holiday?' -ForegroundColor Cyan
    Write-Host '  ON  (default) = one extra chart "Calyx Weekend Flat" closes all EA positions and EA pending orders 30 minutes before any'
    Write-Host '      market break of 2 hours or more (Friday close, broker session gaps) and before US holiday halts (12:00 New York on'
    Write-Host '      MLK, Presidents, Memorial, Juneteenth, July 4, Labor, Thanksgiving + the Friday after) and full closures (12:00 New York'
    Write-Host '      on the trading day before Good Friday, Christmas and New Year). Required on FTMO Standard / 1-Step FTMO Accounts.'
    Write-Host '      Crypto that trades all weekend is not closed for weekends. Manual trades (magic 0) are never touched.'
    Write-Host '  OFF = previous behaviour: EAs may hold trades over weekends and holidays (allowed during FTMO challenges, not on'
    Write-Host '      Standard / 1-Step FTMO Accounts).'
    Write-Host '  The backtests behind every profile were run WITHOUT this close. Closing early changes results (trades cut short).' -ForegroundColor Yellow
}
function Read-CalyxWeekendFlat([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('ON','OFF')) { throw 'Weekend/holiday flat must be ON or OFF.' }; return $Current }
    if ($NoPrompt) { return 'ON' }
    Write-CalyxWeekendFlatHelp
    $answer = (Read-Host 'Close every EA trade before weekends and market holidays? ON or OFF [ON]').Trim().ToUpperInvariant()
    if (-not $answer) { $answer = 'ON' }
    if ($answer -notin @('ON','OFF')) { throw 'Answer ON or OFF.' }
    Write-Host ("Weekend/holiday flat: {0}" -f $answer)
    return $answer
}
function Get-CalyxWeekendFlatExpert([string]$Root) {
    $candidates = @()
    foreach ($base in @($Root, $PSScriptRoot) | Where-Object { $_ }) {
        $candidates += @((Join-Path $base 'Calyx Weekend Flat.ex5'), (Join-Path $base 'Calyx Weekend Flat\Calyx Weekend Flat.ex5'),
                         (Join-Path $base '..\Calyx Weekend Flat\Calyx Weekend Flat.ex5'), (Join-Path $base '..\..\Calyx Weekend Flat\Calyx Weekend Flat.ex5'),
                         (Join-Path $base '..\_00 Live profiles\Calyx Weekend Flat\Calyx Weekend Flat.ex5'))
    }
    foreach ($path in $candidates) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $full = [IO.Path]::GetFullPath($path)
        $manifest = Join-Path (Split-Path -Parent $full) 'WEEKEND_FLAT.json'
        if (Test-Path -LiteralPath $manifest) {
            $want = [string](Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).ex5_sha256
            $have = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($want -and $have -ne $want.ToLowerInvariant()) { throw "Calyx Weekend Flat.ex5 hash mismatch ($full). Rebuild or restore it." }
        }
        return $full
    }
    throw 'Calyx Weekend Flat.ex5 was not found next to this installer or in _00 Live profiles\Calyx Weekend Flat.'
}
function Test-CalyxWeekendFlatChart([string]$Path) {
    try { return ([string](Get-Content -LiteralPath $Path -Raw)).Contains('path=Experts\Calyx Weekend Flat\') } catch { return $false }
}
function Add-CalyxWeekendFlatChart([string]$Mode, [string]$ChartDir, [string]$DataRoot, [string]$Symbol, [string]$ExpertRoot) {
    if ($Mode -ne 'ON') { Write-Host 'Weekend/holiday flat: OFF - EAs may hold trades over weekends and holidays.' -ForegroundColor Yellow; return }
    $source = Get-CalyxWeekendFlatExpert $ExpertRoot
    $target = Join-Path $DataRoot 'MQL5\Experts\Calyx Weekend Flat'
    [void](New-Item -ItemType Directory -Path $target -Force)
    Copy-Item -LiteralPath $source -Destination (Join-Path $target 'Calyx Weekend Flat.ex5') -Force
    $existing = @(Get-ChildItem -LiteralPath $ChartDir -Filter 'chart*.chr' -File | Where-Object { -not (Test-CalyxWeekendFlatChart $_.FullName) })
    $name = 'chart{0:D2}.chr' -f ($existing.Count + 1)
    $id = [DateTime]::UtcNow.Ticks + 999
    $text = @"
<chart>
id=$id
symbol=$Symbol
description=$Symbol
period_type=1
period_size=1
digits=5
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=0.000000
scale=8
mode=1
fore=0
grid=1
volume=0
scroll=1
shift=1
shift_size=20.000000
fixed_pos=0.000000
ticker=1
ohlc=1
one_click=0
one_click_btn=1
bidline=1
askline=0
lastline=0
days=1
descriptions=0
tradelines=1
tradehistory=1
window_left=0
window_top=0
window_right=480
window_bottom=280
window_type=1
floating=0
floating_left=0
floating_top=0
floating_right=0
floating_bottom=0
floating_type=1
floating_toolbar=1
floating_tbstate=
background_color=0
foreground_color=16777215
barup_color=65280
bardown_color=255
bullcandle_color=65280
bearcandle_color=255
chartline_color=65280
volumes_color=5592405
grid_color=2236962
bidline_color=8421504
askline_color=255
lastline_color=8421504
stops_color=255
windows_total=1

<expert>
name=Calyx Weekend Flat
path=Experts\Calyx Weekend Flat\Calyx Weekend Flat.ex5
expertmode=1
<inputs>
InpEnabled=true
InpLeadMinutes=30
InpMinBreakMinutes=120
InpHolidayRules=true
InpHolidayFlatHourNY=12
InpHolidayFile=CalyxHolidayFlat.csv
InpIncludeManual=false
InpDeletePending=true
InpTimerSeconds=5
InpServerUtcOffsetHours=0
InpTestOpen=false
</inputs>
</expert>

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1
</indicator>
</window>
</chart>
"@
    [IO.File]::WriteAllText((Join-Path $ChartDir $name), $text.TrimStart(), [Text.Encoding]::Unicode)
    $orderPath = Join-Path $ChartDir 'order.wnd'
    $order = if (Test-Path -LiteralPath $orderPath) { [IO.File]::ReadAllText($orderPath) } else { '' }
    $lines = @($order -split "`r?`n" | Where-Object { $_ -and $_ -ne $name }) + $name
    [IO.File]::WriteAllText($orderPath, (($lines -join "`r`n") + "`r`n"), [Text.Encoding]::Unicode)
    Write-Host ("Weekend/holiday flat: ON - added {0} (Calyx Weekend Flat on {1} H1). It closes EA trades before weekends and holiday closures." -f $name, $Symbol) -ForegroundColor Green
}
# <<< Calyx Weekend Flat <<<
