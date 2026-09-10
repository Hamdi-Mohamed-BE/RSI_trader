[CmdletBinding()]
param([switch]$Yes)

$ErrorActionPreference = 'Stop'
$TerminalPath = 'C:\Program Files\Ava Trade MT5 Terminal\terminal64.exe'
$ProfileName = 'Calyx-Ava-EAs'
$ExpertFolderName = 'Calyx Ava Futures'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Utf8 = [Text.UTF8Encoding]::new($false)
$Unicode = [Text.UnicodeEncoding]::new($false, $true)

function Stop-Install([string]$Message) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit 1
}

function Resolve-AvaDataRoot {
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    foreach ($origin in @(Get-ChildItem -LiteralPath $terminalRoot -Filter origin.txt -Recurse -File -ErrorAction SilentlyContinue)) {
        $installed = (Get-Content -LiteralPath $origin.FullName -Raw -ErrorAction SilentlyContinue).Trim()
        if ($installed -and ((Join-Path $installed 'terminal64.exe') -ieq $TerminalPath)) {
            return $origin.DirectoryName
        }
    }
    Stop-Install 'The Ava MT5 data folder could not be identified. Start Ava MT5 once, close it, then run this installer again.'
}

function Read-SetInputs([string]$Path, [bool]$SafeMode) {
    $inputs = [ordered]@{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -notmatch '^([^;#][^=]*)=(.*)$') { continue }
        $key = $matches[1].Trim()
        $value = ($matches[2] -split '\|\|', 2)[0].Trim()
        if ($key) { $inputs[$key] = $value }
    }
    if ($SafeMode) {
        $safeInputs = [ordered]@{
            InpUseMarkovRegimeFilter = 'true'
            InpMarkovReturnWindow = '40'
            InpMarkovThreshold = '0.05'
            InpMarkovSignalGate = '0.05'
            InpMarkovMinLabels = '252'
            InpMarkovHistoryBars = '2600'
        }
        foreach ($entry in $safeInputs.GetEnumerator()) {
            $inputs[$entry.Key] = $entry.Value
        }
    }
    return $inputs
}

function New-ChartText([object]$Item, [long]$Id, [int]$Index) {
    $inputs = Read-SetInputs $Item.SetSource ([bool]$Item.SafeMode)
    $inputLines = @($inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $inputs[$_] }) -join "`r`n"
    $columns = 4
    $width = 480
    $height = 280
    $left = ($Index % $columns) * $width
    $top = [Math]::Floor($Index / $columns) * $height
    $right = $left + $width
    $bottom = $top + $height
    $expertName = [IO.Path]::GetFileNameWithoutExtension([string]$Item.Expert)
    $expertPath = 'Experts\' + $ExpertFolderName + '\' + $Item.Expert
    $periodType = if ($Item.Period -lt 60) { 0 } elseif ($Item.Period -lt 1440) { 1 } else { 2 }
    $periodSize = if ($periodType -eq 0) { $Item.Period } elseif ($periodType -eq 1) { [int]($Item.Period / 60) } else { [int]($Item.Period / 1440) }
    return @"
<chart>
id=$Id
symbol=$($Item.Symbol)
description=$($Item.Symbol)
period_type=$periodType
period_size=$periodSize
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
window_left=$left
window_top=$top
window_right=$right
window_bottom=$bottom
window_type=1
floating=0
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
name=$expertName
path=$expertPath
expertmode=1
<inputs>
$inputLines
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
}

function Close-AvaTerminal {
    $targets = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $TerminalPath
    })
    foreach ($target in $targets) {
        $process = Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
        if ($process) { [void]$process.CloseMainWindow() }
    }
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $TerminalPath
        })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 500
    }
    $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $TerminalPath
    })
    foreach ($target in $remaining) {
        Write-Warning "Ava MT5 process $($target.ProcessId) ignored the clean-close request; forcing only this verified Ava terminal to stop."
        Stop-Process -Id $target.ProcessId -Force -ErrorAction Stop
    }
    Start-Sleep -Seconds 2
    $stillRunning = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $TerminalPath
    })
    if ($stillRunning.Count -gt 0) { Stop-Install 'The verified Ava MT5 process could not be stopped.' }
}

if (-not (Test-Path -LiteralPath $TerminalPath)) { Stop-Install "Ava MT5 is missing at $TerminalPath" }
$DataRoot = Resolve-AvaDataRoot

$portfolio = @(
    [pscustomobject]@{ Label='News Pulse XAG'; Symbol='SILZ26'; Period=1; Expert='AAA Final News Pulse EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\News Pulse\AAA Final News Pulse EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set'); SafeMode=$false },
    [pscustomobject]@{ Label='News Pulse XAU'; Symbol='MGCZ26'; Period=1; Expert='AAA Final News Pulse EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\News Pulse\AAA Final News Pulse EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'); SafeMode=$false },
    [pscustomobject]@{ Label='XAU Trend Progression'; Symbol='MGCZ26'; Period=240; Expert='Trend Progression EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\Trend Progression\Trend Progression EA.ex5'); SetSource=(Join-Path $PackageRoot 'Trend Progression Research 2026-09-02\Sets\TrendProgression-xauusd--h4--optimized--locked.set'); SafeMode=$false },
    [pscustomobject]@{ Label='Safe LTA Volume Profile'; Symbol='MGCZ26'; Period=15; Expert='LTA_Concepts_EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\LTA\LTA_Concepts_EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\01 LTA Volume Profile - CURRENT - ALL DAY.set'); SafeMode=$true },
    [pscustomobject]@{ Label='DMC Fresh Reaction XAU'; Symbol='MGCZ26'; Period=60; Expert='Calyx DMC Fresh Reaction EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\DMC Fresh Reaction\Calyx DMC Fresh Reaction EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set'); SafeMode=$false },
    [pscustomobject]@{ Label='XAU ORB London NY Overlap M30'; Symbol='MGCZ26'; Period=30; Expert='ORB Volume Data EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\ORB Volume Data\ORB Volume Data EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set'); SafeMode=$false },
    [pscustomobject]@{ Label='US100 H1 ORB 13UTC'; Symbol='MNQZ26'; Period=15; Expert='ORB Volume Data EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\ORB Volume Data\ORB Volume Data EA.ex5'); SetSource=(Join-Path $PackageRoot 'ORB H1 Range Research 2026-09-05\Sets\USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set'); SafeMode=$false },
    [pscustomobject]@{ Label='Safe XAU Weakness'; Symbol='MGCZ26'; Period=30; Expert='AAA Final XAU Weakness EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\XAU Weakness\AAA Final XAU Weakness EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\09 XAU Weakness - M30 STRUCTURE 4R - DYNAMIC 50-20.set'); SafeMode=$true },
    [pscustomobject]@{ Label='US100 ORB New York M30'; Symbol='MNQZ26'; Period=30; Expert='ORB Volume Data EA.ex5'; ExpertSource=(Join-Path $PSScriptRoot 'EA\ORB Volume Data\ORB Volume Data EA.ex5'); SetSource=(Join-Path $PackageRoot 'Selected Portfolio Settings 2026-09-01\16 US100 ORB New York M30 - LOCKED STANDALONE.set'); SafeMode=$false }
)

foreach ($item in $portfolio) {
    if (-not (Test-Path -LiteralPath $item.ExpertSource)) { Stop-Install "Missing Ava EA build: $($item.ExpertSource)" }
    if (-not (Test-Path -LiteralPath $item.SetSource)) { Stop-Install "Missing settings: $($item.SetSource)" }
}

Write-Host "`nCalyx Ava EAs - current futures PF 1.40+ plus DMC" -ForegroundColor Cyan
Write-Host "Account data: $DataRoot"
Write-Host 'Sizing: exactly one broker-minimum contract per entry. No 1% target is forced.' -ForegroundColor Yellow
Write-Host 'News Pulse v2.13: MT5 live calendar, FXMacroData-verified tester calendar, hard 0.75% per pending side.' -ForegroundColor Cyan
Write-Host 'Important: one minimum contract can risk more than 1%. News Pulse can maintain two pending stops for an event.' -ForegroundColor Yellow
Write-Host 'Ava netting guard: only one Calyx EA may own a given contract at a time.' -ForegroundColor Green
foreach ($item in $portfolio) {
    $mode = if ($item.SafeMode) { 'SAFE' } else { 'STANDARD' }
    Write-Host ('  {0,-36} {1,-7} {2}' -f $item.Label, $item.Symbol, $mode)
}

$expected = 'INSTALL AVA MINIMUM CONTRACTS'
$confirmation = if ($Yes) { $expected } else { Read-Host "Type exactly '$expected' to continue" }
if ($confirmation.Trim() -ine $expected) { Stop-Install 'Confirmation did not match. No files were installed.' }

Close-AvaTerminal

$mql5Root = Join-Path $DataRoot 'MQL5'
$expertsTarget = Join-Path (Join-Path $mql5Root 'Experts') $ExpertFolderName
$testerTarget = Join-Path (Join-Path $mql5Root 'Profiles\Tester') $ProfileName
$chartsRoot = Join-Path $mql5Root 'Profiles\Charts'
$profileTarget = Join-Path $chartsRoot $ProfileName
foreach ($directory in @($expertsTarget, $testerTarget, $chartsRoot)) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

foreach ($source in @($portfolio | Select-Object -ExpandProperty ExpertSource -Unique)) {
    Copy-Item -LiteralPath $source -Destination (Join-Path $expertsTarget ([IO.Path]::GetFileName($source))) -Force
}
foreach ($item in $portfolio) {
    $setName = (($item.Label -replace '[^A-Za-z0-9 -]', '') + ' - ' + $item.Symbol + '.set')
    $inputs = Read-SetInputs $item.SetSource ([bool]$item.SafeMode)
    $setText = (@($inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $inputs[$_] }) -join "`r`n") + "`r`n"
    [IO.File]::WriteAllText((Join-Path $testerTarget $setName), $setText, $Utf8)
}

$profileFull = [IO.Path]::GetFullPath($profileTarget)
$chartsFull = [IO.Path]::GetFullPath($chartsRoot).TrimEnd('\') + '\'
if (-not $profileFull.StartsWith($chartsFull, [StringComparison]::OrdinalIgnoreCase)) { Stop-Install 'Unsafe profile path.' }
if (Test-Path -LiteralPath $profileFull) {
    $backup = $profileFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileFull -Destination $backup
    Write-Host "Previous Ava profile backed up to $backup"
}
[void](New-Item -ItemType Directory -Path $profileFull -Force)

for ($i=0; $i -lt $portfolio.Count; $i++) {
    $chartPath = Join-Path $profileFull ('chart{0:D2}.chr' -f ($i+1))
    $chartText = New-ChartText $portfolio[$i] ([DateTime]::UtcNow.Ticks+$i) $i
    [IO.File]::WriteAllText($chartPath, $chartText.TrimStart(), $Unicode)
}
$orderText = ((1..$portfolio.Count | ForEach-Object { 'chart{0:D2}.chr' -f $_ }) -join "`r`n") + "`r`n"
[IO.File]::WriteAllText((Join-Path $profileFull 'order.wnd'), $orderText, $Unicode)

$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $TerminalPath
    'Data folder: ' + $DataRoot
    'Profile: ' + $ProfileName
    'Sizing: exactly one broker-minimum contract per entry; no 1% target forced'
    'Netting protection: Calyx Ava per-contract ownership guard enabled'
    'Contract rollover: MGCZ26, SILZ26 and MNQZ26 must be reviewed before expiry'
    ''
    'Charts:'
) + @($portfolio | ForEach-Object { '{0}: {1}, period {2}, {3}, {4}' -f $_.Label,$_.Symbol,$_.Period,$_.Expert,$(if ($_.SafeMode) {'SAFE'} else {'STANDARD'}) })
$manifestPath = Join-Path $PSScriptRoot 'LAST AVA FUTURES INSTALL.txt'
[IO.File]::WriteAllText($manifestPath, (($manifest -join "`r`n") + "`r`n"), $Utf8)

Start-Process -FilePath $TerminalPath -ArgumentList ('/profile:"' + $ProfileName + '"')
Start-Sleep -Seconds 12
$running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $TerminalPath
})
if ($running.Count -eq 0) { Stop-Install 'Files were installed, but Ava MT5 did not remain running.' }

Write-Host "`nSUCCESS: Ava MT5 is running the '$ProfileName' profile with $($portfolio.Count) charts." -ForegroundColor Green
Write-Host "Install record: $manifestPath"
Write-Host 'Before each futures expiry, update the three contract symbols and rerun this installer.' -ForegroundColor Yellow
