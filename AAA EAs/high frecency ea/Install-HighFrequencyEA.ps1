[CmdletBinding()]
param(
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
$ProfileName = 'HIGH FREQUENCY OCO - XAUUSD M1'
$ExpertFolderName = 'High Frequency OCO'
$ExpertName = 'XAU M1 Current Price OCO EA.ex5'
$SourceName = 'XAU M1 Current Price OCO EA.mq5'
$CoreName = 'XAU M1 OCO Core.mqh'
$TemplateSetName = 'DEFAULT - XAUUSD M1 - Current Price OCO.set'
$GeneratedSetName = 'LAST INSTALLED - XAUUSD M1 - Current Price OCO.set'
$Invariant = [Globalization.CultureInfo]::InvariantCulture
$Unicode = [Text.UnicodeEncoding]::new($false, $true)

function Stop-Install([string]$Message) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit 1
}

function Write-Stage([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Set-IniValue([string]$Path, [string]$Section, [string]$Key, [string]$Value) {
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -LiteralPath $Path) { [void]$lines.Add($line) }
    $sectionLine = -1
    $nextSectionLine = $lines.Count
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -ieq "[$Section]") {
            $sectionLine = $i
            for ($j = $i + 1; $j -lt $lines.Count; $j++) {
                if ($lines[$j].Trim().StartsWith('[')) { $nextSectionLine = $j; break }
            }
            break
        }
    }
    if ($sectionLine -lt 0) {
        [void]$lines.Add("[$Section]")
        [void]$lines.Add("$Key=$Value")
    } else {
        $keyLine = -1
        for ($i = $sectionLine + 1; $i -lt $nextSectionLine; $i++) {
            if ($lines[$i] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) { $keyLine = $i; break }
        }
        if ($keyLine -ge 0) { $lines[$keyLine] = "$Key=$Value" }
        else { $lines.Insert($nextSectionLine, "$Key=$Value") }
    }
    [IO.File]::WriteAllText($Path, (($lines -join "`r`n") + "`r`n"), $Unicode)
}

function Resolve-DataRoot([string]$TerminalPath, [string]$CommandLine) {
    $installRoot = [IO.Path]::GetFullPath((Split-Path -Parent $TerminalPath)).TrimEnd('\')
    if ($CommandLine -match '(?i)(^|\s)/portable(\s|$)' -and (Test-Path -LiteralPath (Join-Path $installRoot 'MQL5'))) {
        return $installRoot
    }
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    $matches = @()
    if (Test-Path -LiteralPath $terminalRoot) {
        foreach ($origin in @(Get-ChildItem -LiteralPath $terminalRoot -Recurse -Filter origin.txt -File -ErrorAction SilentlyContinue)) {
            $originRoot = [IO.Path]::GetFullPath((Get-Content -LiteralPath $origin.FullName -Raw).Trim()).TrimEnd('\')
            if ($originRoot -ieq $installRoot -and (Test-Path -LiteralPath (Join-Path $origin.DirectoryName 'MQL5'))) {
                $matches += $origin.DirectoryName
            }
        }
    }
    if ($matches.Count -eq 1) { return [IO.Path]::GetFullPath($matches[0]) }
    if ($matches.Count -gt 1) {
        $ordered = @($matches | Sort-Object { (Get-Item -LiteralPath $_).LastWriteTime } -Descending)
        return [IO.Path]::GetFullPath($ordered[0])
    }
    Stop-Install "Could not resolve the MT5 data folder for $TerminalPath."
}

function Find-GoldSymbol([string]$TerminalPath, [string]$DataRoot) {
    $detector = Join-Path $PackageRoot 'Detect-GoldSymbol.py'
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python -and (Test-Path -LiteralPath $detector)) {
        $detected = @(& $python.Source $detector $TerminalPath 2>$null)
        if ($LASTEXITCODE -eq 0 -and $detected.Count -gt 0) {
            $candidate = ([string]$detected[-1]).Trim()
            if ($candidate -match '^[A-Za-z0-9._-]+$') { return $candidate }
        }
    }
    $chartsRoot = Join-Path $DataRoot 'MQL5\Profiles\Charts'
    if (Test-Path -LiteralPath $chartsRoot) {
        foreach ($chart in @(Get-ChildItem -LiteralPath $chartsRoot -Recurse -Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)) {
            $match = Select-String -LiteralPath $chart.FullName -Pattern '^symbol=(.+)$' | Select-Object -First 1
            if ($match) {
                $candidate = $match.Matches[0].Groups[1].Value.Trim()
                $normalized = ($candidate -replace '[^A-Za-z0-9]', '').ToUpperInvariant()
                if ($normalized.Contains('XAUUSD') -or $normalized.StartsWith('GOLD')) { return $candidate }
            }
        }
    }
    return 'XAUUSD'
}

function Close-Terminal([int]$ProcessId) {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) { return }
    [void]$process.CloseMainWindow()
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    } while ($process -and (Get-Date) -lt $deadline)
    if ($process) { Stop-Install 'MT5 did not close cleanly. Close it manually and run the BAT again.' }
}

$lot = 0.01
$lotText = '0.01'

$expertSource = Join-Path $PackageRoot "EA\$ExpertName"
$mq5Source = Join-Path $PackageRoot "EA\$SourceName"
$coreSource = Join-Path $PackageRoot "EA\$CoreName"
$templateSet = Join-Path $PackageRoot "Settings\$TemplateSetName"
foreach ($required in @($expertSource, $mq5Source, $coreSource, $templateSet)) {
    if (-not (Test-Path -LiteralPath $required)) { Stop-Install "Missing package file: $required" }
}

Write-Stage 'Finding the active MT5'
$tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -and
    -not ([IO.Path]::GetFullPath($_.ExecutablePath).StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) -and
    $_.ExecutablePath -notmatch '(?i)\\_Backtests\\'
})
if ($running.Count -eq 0) { Stop-Install 'No active normal MT5 was found. Open and log into the target MT5, then run this BAT again.' }
if ($running.Count -gt 1) {
    Write-Host 'More than one MT5 is open:' -ForegroundColor Yellow
    $running | ForEach-Object { Write-Host ('  PID {0}: {1}' -f $_.ProcessId, $_.ExecutablePath) }
    Stop-Install 'Leave only the target MT5 open, then run this BAT again.'
}
$target = $running[0]
$terminalPath = [IO.Path]::GetFullPath([string]$target.ExecutablePath)
$dataRoot = Resolve-DataRoot $terminalPath ([string]$target.CommandLine)
$symbol = Find-GoldSymbol $terminalPath $dataRoot
Write-Host "Terminal: $terminalPath"
Write-Host "Data:     $dataRoot"
Write-Host "Symbol:   $symbol"
Write-Host "Fixed lot: $lotText (safer recommended preset; dynamic scaling disabled)" -ForegroundColor Yellow
if ($ValidateOnly) {
    Write-Host "`nVALIDATION PASSED: no MT5, profile, setting or package file was changed." -ForegroundColor Green
    exit 0
}

Write-Stage 'Building the selected settings'
$setText = Get-Content -LiteralPath $templateSet -Raw
$setText = [regex]::Replace($setText, '(?m)^InpBaseLot=.*$', "InpBaseLot=$lotText")
$setText = [regex]::Replace($setText, '(?m)^InpReferenceBalance=.*$', 'InpReferenceBalance=50')
$setText = [regex]::Replace($setText, '(?m)^InpScaleLotWithEquity=.*$', 'InpScaleLotWithEquity=false')
$setText = [regex]::Replace($setText, '(?m)^InpMinimumConfiguredLot=.*$', 'InpMinimumConfiguredLot=0.01')
$setText = [regex]::Replace($setText, '(?m)^InpMaximumConfiguredLot=.*$', 'InpMaximumConfiguredLot=0.01')
$setText = [regex]::Replace($setText, '(?m)^InpUseSessionFilter=.*$', 'InpUseSessionFilter=true')
$setText = [regex]::Replace($setText, '(?m)^InpSessionStartHour=.*$', 'InpSessionStartHour=13')
$setText = [regex]::Replace($setText, '(?m)^InpSessionEndHour=.*$', 'InpSessionEndHour=21')
$setText = [regex]::Replace($setText, '(?m)^InpUseVirtualOCO=.*$', 'InpUseVirtualOCO=true')
$setText = [regex]::Replace($setText, '(?m)^InpUsePreviousBarTriggers=.*$', 'InpUsePreviousBarTriggers=true')
$setText = [regex]::Replace($setText, '(?m)^InpMinimumPreviousRangeATR=.*$', 'InpMinimumPreviousRangeATR=0.5')
$setText = [regex]::Replace($setText, '(?m)^InpMinimumVolumeRatio=.*$', 'InpMinimumVolumeRatio=1.0')
$setText = [regex]::Replace($setText, '(?m)^InpMaximumSpreadPrice=.*$', 'InpMaximumSpreadPrice=0.25')
$setText = [regex]::Replace($setText, '(?m)^InpCooldownAfterWinSeconds=.*$', 'InpCooldownAfterWinSeconds=60')
$setText = [regex]::Replace($setText, '(?m)^InpCooldownAfterLossSeconds=.*$', 'InpCooldownAfterLossSeconds=300')
$setText = [regex]::Replace($setText, '(?m)^InpMaximumTradesPerDay=.*$', 'InpMaximumTradesPerDay=12')
$setText = [regex]::Replace($setText, '(?m)^InpMaximumDailyLossMoney=.*$', 'InpMaximumDailyLossMoney=3.00')
$setText = [regex]::Replace($setText, '(?m)^InpBrokerSafetyBufferPrice=.*$', 'InpBrokerSafetyBufferPrice=0.10')
$setText = [regex]::Replace($setText, '(?m)^InpMinimumTrailStepPrice=.*$', 'InpMinimumTrailStepPrice=0.10')
$generatedLocalSet = Join-Path $PackageRoot "Settings\$GeneratedSetName"
[IO.File]::WriteAllText($generatedLocalSet, $setText.TrimEnd() + "`r`n", [Text.UTF8Encoding]::new($false))
$inputLines = (($setText -split '\r?\n') | Where-Object { $_.Trim() -ne '' }) -join "`r`n"

Write-Stage 'Closing MT5 cleanly'
Close-Terminal ([int]$target.ProcessId)

Write-Stage 'Installing the standalone EA profile'
$mql5Root = Join-Path $dataRoot 'MQL5'
$expertsRoot = Join-Path $mql5Root 'Experts'
$expertsTarget = Join-Path $expertsRoot $ExpertFolderName
$testerTarget = Join-Path $mql5Root 'Profiles\Tester\High Frequency OCO'
$chartsRoot = Join-Path $mql5Root 'Profiles\Charts'
$profileTarget = Join-Path $chartsRoot $ProfileName
foreach ($directory in @($expertsTarget, $testerTarget, $chartsRoot)) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

$chartsRootFull = [IO.Path]::GetFullPath($chartsRoot).TrimEnd('\') + '\'
$profileTargetFull = [IO.Path]::GetFullPath($profileTarget)
if (-not $profileTargetFull.StartsWith($chartsRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-Install "Unsafe profile target: $profileTargetFull"
}
if (Test-Path -LiteralPath $profileTargetFull) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileTargetFull -Destination $backup
    Write-Host "Previous standalone profile backed up to: $backup"
}
[void](New-Item -ItemType Directory -Path $profileTargetFull -Force)

Copy-Item -LiteralPath $expertSource -Destination (Join-Path $expertsTarget $ExpertName) -Force
Copy-Item -LiteralPath $mq5Source -Destination (Join-Path $expertsTarget $SourceName) -Force
Copy-Item -LiteralPath $coreSource -Destination (Join-Path $expertsTarget $CoreName) -Force
Copy-Item -LiteralPath $generatedLocalSet -Destination (Join-Path $testerTarget $GeneratedSetName) -Force

$chartId = [DateTime]::UtcNow.Ticks
$expertPath = "Experts\$ExpertFolderName\$ExpertName"
$chartText = @"
<chart>
id=$chartId
symbol=$symbol
description=Gold vs US Dollar
period_type=0
period_size=1
digits=3
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=0.000000
scale=3
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
askline=1
lastline=0
days=1
descriptions=0
tradelines=1
tradehistory=1
window_left=0
window_top=0
window_right=960
window_bottom=640
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
name=XAU M1 Current Price OCO EA
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
[IO.File]::WriteAllText((Join-Path $profileTargetFull 'chart01.chr'), $chartText.TrimStart(), $Unicode)
[IO.File]::WriteAllText((Join-Path $profileTargetFull 'order.wnd'), "chart01.chr`r`n", $Unicode)

$commonIni = Join-Path $dataRoot 'config\common.ini'
if (Test-Path -LiteralPath $commonIni) {
    $commonBackup = $commonIni + '.hft-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Copy-Item -LiteralPath $commonIni -Destination $commonBackup -Force
    Set-IniValue $commonIni 'Experts' 'Enabled' '1'
    Set-IniValue $commonIni 'Experts' 'Account' '0'
    Set-IniValue $commonIni 'Experts' 'Profile' '0'
    Set-IniValue $commonIni 'Experts' 'Chart' '0'
} else {
    Write-Warning 'common.ini was not found. The EA/profile is installed, but MT5 keeps its current Algo Trading preference.'
}

$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $terminalPath
    'Data folder: ' + $dataRoot
    'Profile: ' + $ProfileName
    'Symbol: ' + $symbol
    'Timeframe: M1'
    'EA: ' + $ExpertName
    'Fixed lot: ' + $lotText
    'Dynamic equity scaling: disabled'
    'Minimum lot: 0.01'
    'Maximum lot: 0.01'
    'Session filter: enabled, 13:00-21:00 server time'
    'Order mode: virtual one-shot OCO; no simultaneous broker pending pair'
    'Trigger: previous M1 high/low plus offset'
    'Range filter: previous M1 range >= 0.5 ATR'
    'Volume filter: previous M1 tick volume >= 1.0x 20-bar average'
    'Maximum spread: 0.25 price units'
    'Cooldown after win/loss: 60 / 300 seconds'
    'Maximum trades/day: 12'
    'Daily loss guard: 3.00 USD'
    'Preset: LIVE GUARD V1.20'
    'Settings: ' + $generatedLocalSet
    'Main portfolio BAT changed: no'
    'EA website changed: no'
)
[IO.File]::WriteAllText((Join-Path $PackageRoot 'LAST INSTALL.txt'), (($manifest -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($true))

Write-Stage 'Starting the standalone profile'
$arguments = '/profile:"' + $ProfileName + '"'
Start-Process -FilePath $terminalPath -ArgumentList $arguments
Start-Sleep -Seconds 12
$runningNow = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $terminalPath
})
if ($runningNow.Count -eq 0) { Stop-Install 'Files were installed, but MT5 did not remain running.' }
$chartPath = Join-Path $profileTargetFull 'chart01.chr'
if (-not (Select-String -LiteralPath $chartPath -SimpleMatch '<expert>' -Quiet)) {
    Stop-Install 'MT5 opened, but the chart lost its EA attachment. Check the Experts journal.'
}
if (-not (Select-String -LiteralPath $chartPath -Pattern '^period_type=0$' -Quiet) -or
    -not (Select-String -LiteralPath $chartPath -Pattern '^period_size=1$' -Quiet)) {
    Stop-Install 'The installed profile is not a valid native M1 chart. The EA files remain installed; attach the EA manually.'
}

Write-Host "`nSUCCESS: '$ProfileName' is running on $symbol M1." -ForegroundColor Green
Write-Host "Safer preset: fixed $lotText lot; dynamic scaling disabled; session 13:00-21:00 server time." -ForegroundColor Yellow
Write-Host 'Verify the Algo Trading button is green and inspect the Experts tab before leaving it unattended.' -ForegroundColor Yellow
