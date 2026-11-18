# >>> Calyx News Guard (owner 2026-11-18: "respect all the trading rules") >>>
# FTMO funded Standard: no execution 2 min before / after selected news (entries, TP, SL, pending orders) - challenges / Swing are exempt.
# The5ers High Stakes: no trades 2 min around high-impact news. FundingPips Master: 5 min (profit removed).
# ON adds one extra chart running "Calyx News Guard": before each High-impact release in Common\Files\CalyxNewsCalendar.csv it closes EA positions
# and deletes EA pending orders on the affected symbols and blocks new EA entries until the window ends. Source: _00 Live profiles\Calyx News Guard.
function Read-CalyxNewsGuard([string]$Current, [bool]$NoPrompt, [string]$Default) {
    if ($Current) { if ($Current -notin @('OFF','2','5')) { throw 'News guard must be OFF, 2 or 5.' }; return $Current }
    if ($NoPrompt) { return $Default }
    Write-Host ''
    Write-Host 'NEWS GUARD - close EA trades and block EA entries around high-impact news?' -ForegroundColor Cyan
    Write-Host '  2   = +-2 minutes: FTMO funded Standard account (no entry / TP / SL inside the window) and The5ers High Stakes.'
    Write-Host '  5   = +-5 minutes: FundingPips Master account (news profits are removed) - also covers the 2-minute firms.'
    Write-Host '  OFF = no news handling: fine in FTMO challenges and FTMO Swing, NOT on the accounts above.'
    Write-Host '  It needs a fresh calendar: "Update News Calendar.bat" (run daily). Trades held at news time are closed ~90 s before the window.'
    Write-Host '  The backtests behind this profile were run WITHOUT the news close.' -ForegroundColor Yellow
    $answer = (Read-Host "News guard: OFF, 2 or 5 [$Default]").Trim().ToUpperInvariant()
    if (-not $answer) { $answer = $Default }
    if ($answer -notin @('OFF','2','5')) { throw 'Answer OFF, 2 or 5.' }
    Write-Host ("News guard: {0}" -f $answer)
    return $answer
}
function Get-CalyxNewsGuardExpert([string]$Root) {
    $candidates = @()
    foreach ($base in @($Root, $PSScriptRoot) | Where-Object { $_ }) {
        $candidates += @((Join-Path $base 'Calyx News Guard.ex5'), (Join-Path $base 'Calyx News Guard\Calyx News Guard.ex5'),
                         (Join-Path $base '..\Calyx News Guard\Calyx News Guard.ex5'), (Join-Path $base '..\..\Calyx News Guard\Calyx News Guard.ex5'),
                         (Join-Path $base '..\_00 Live profiles\Calyx News Guard\Calyx News Guard.ex5'))
    }
    foreach ($path in $candidates) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $full = [IO.Path]::GetFullPath($path)
        $manifest = Join-Path (Split-Path -Parent $full) 'NEWS_GUARD.json'
        if (Test-Path -LiteralPath $manifest) {
            $want = [string](Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).ex5_sha256
            $have = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($want -and $have -ne $want.ToLowerInvariant()) { throw "Calyx News Guard.ex5 hash mismatch ($full). Rebuild or restore it." }
        }
        return $full
    }
    throw 'Calyx News Guard.ex5 was not found next to this installer or in _00 Live profiles\Calyx News Guard.'
}
function Test-CalyxNewsGuardChart([string]$Path) {
    try { return ([string](Get-Content -LiteralPath $Path -Raw)).Contains('path=Experts\Calyx News Guard\') } catch { return $false }
}
function Add-CalyxNewsGuardChart([string]$Mode, [string]$ChartDir, [string]$DataRoot, [string]$Symbol, [string]$ExpertRoot) {
    if ($Mode -eq 'OFF') { Write-Host 'News guard: OFF - EAs may trade through news releases (fine in FTMO challenges / Swing, NOT on FTMO funded Standard, The5ers or FundingPips Master).' -ForegroundColor Yellow; return }
    $source = Get-CalyxNewsGuardExpert $ExpertRoot
    $target = Join-Path $DataRoot 'MQL5\Experts\Calyx News Guard'
    [void](New-Item -ItemType Directory -Path $target -Force)
    Copy-Item -LiteralPath $source -Destination (Join-Path $target 'Calyx News Guard.ex5') -Force
    $existing = @(Get-ChildItem -LiteralPath $ChartDir -Filter 'chart*.chr' -File | Where-Object { -not (Test-CalyxNewsGuardChart $_.FullName) })
    $name = 'chart{0:D2}.chr' -f ($existing.Count + 1)
    $id = [DateTime]::UtcNow.Ticks + 1999
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
name=Calyx News Guard
path=Experts\Calyx News Guard\Calyx News Guard.ex5
expertmode=1
<inputs>
InpEnabled=true
InpBeforeMinutes=$Mode
InpAfterMinutes=$Mode
InpCloseLeadSeconds=90
InpImpacts=High
InpCalendarFile=CalyxNewsCalendar.csv
InpStaleHours=36
InpIncludeManual=false
InpDeletePending=true
InpTimerSeconds=2
InpTestEvents=
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
    Write-Host ("News guard: ON (+-{2} min) - added {0} (Calyx News Guard on {1} H1). It closes EA trades and blocks EA entries around high-impact news." -f $name, $Symbol, $Mode) -ForegroundColor Green
    $updater = Join-Path (Split-Path -Parent $source) 'Update-NewsCalendar.ps1'
    if (Test-Path -LiteralPath $updater) { try { & $updater } catch { Write-Host ('News calendar download FAILED: {0}. Run Update News Calendar.bat before trading.' -f $_.Exception.Message) -ForegroundColor Red } }
    else { Write-Host 'Update-NewsCalendar.ps1 not found next to Calyx News Guard.ex5: run Update News Calendar.bat before trading.' -ForegroundColor Red }
    Write-Host 'IMPORTANT: run "Update News Calendar.bat" (_00 Live profiles\Calyx News Guard) once a day, e.g. with Windows Task Scheduler. Without a fresh calendar the guard warns on its chart and cannot block anything.' -ForegroundColor Yellow
}
# <<< Calyx News Guard <<<
