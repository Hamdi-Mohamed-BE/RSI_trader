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
