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
