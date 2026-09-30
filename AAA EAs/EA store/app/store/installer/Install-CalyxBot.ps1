<#
.SYNOPSIS
  Installs one Calyx Expert Advisor into a MetaTrader 5 data folder (PowerShell only, no Python).

.DESCRIPTION
  * Finds MT5 data folders under %APPDATA%\MetaQuotes\Terminal\* and shows which terminal each
    belongs to (origin.txt). Folders that belong to Ava, test or tester terminals are refused.
  * Asks for the broker's symbol name (suffixes differ between brokers, e.g. XAUUSD, XAUUSD.r, GOLD).
  * Copies the EX5 to MQL5\Experts\Calyx\, the SET to MQL5\Presets\ and MQL5\Profiles\Tester\,
    and creates a chart profile "Calyx - <bot>" with the EA and its inputs attached.
  * Adds the license server to the WebRequest allow-list in config\common.ini ONLY when that
    terminal is closed; otherwise prints the exact manual steps.
  * Never enables Algo Trading and never starts or stops MetaTrader 5.

.EXAMPLE
  .\Install-CalyxBot.ps1                                   # interactive
  .\Install-CalyxBot.ps1 -ValidateOnly                     # show the plan, change nothing
  .\Install-CalyxBot.ps1 -TargetDataFolder "D:\MT5\Data" -Symbol XAUUSD.r -Yes
#>
[CmdletBinding()]
param(
    [string]$BotName = 'Calyx EA',
    [string]$ExpertFile = '',
    [string]$SetFile = '',
    [string]$DefaultSymbol = 'XAUUSD',
    [ValidateRange(1, 43200)]
    [int]$PeriodMinutes = 60,
    [string]$AllowUrl = 'https://calyx.duckdns.org',
    [string]$TargetDataFolder = '',
    [string]$TerminalRoot = '',
    [string]$Symbol = '',
    [switch]$ValidateOnly,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Unicode = New-Object System.Text.UnicodeEncoding($false, $true)
$RefusePattern = '(?i)(\bava|avatrade|tester|\btest(s|ing)?\b|backtest)'

function Write-Step([string]$Text) { Write-Host "`n== $Text" -ForegroundColor Cyan }
function Stop-Install([string]$Text, [int]$Code = 1) {
    Write-Host "`nSTOPPED: $Text" -ForegroundColor Red
    exit $Code
}

function Read-SetInputs([string]$Path) {
    $result = New-Object System.Collections.Specialized.OrderedDictionary
    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith(';') -or $trimmed.StartsWith('#')) { continue }
        $equals = $trimmed.IndexOf('=')
        if ($equals -lt 1) { continue }
        $key = $trimmed.Substring(0, $equals).Trim()
        $value = $trimmed.Substring($equals + 1)
        $separator = $value.IndexOf('||')
        if ($separator -ge 0) { $value = $value.Substring(0, $separator) }
        $result[$key] = $value
    }
    return $result
}

function Get-Origin([string]$DataFolder) {
    $originFile = Join-Path $DataFolder 'origin.txt'
    if (Test-Path -LiteralPath $originFile) {
        try { return ([IO.File]::ReadAllText($originFile)).Trim() } catch { return '' }
    }
    return ''
}

function Test-Refused([string]$DataFolder, [string]$Origin) {
    $leaf = Split-Path -Leaf $DataFolder
    return ($leaf -match $RefusePattern) -or ($Origin -match $RefusePattern)
}

function Get-TerminalCandidates([string]$Root) {
    $list = @()
    if (-not (Test-Path -LiteralPath $Root)) { return $list }
    foreach ($dir in @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
        if ($dir.Name -in @('Common', 'Community', 'Help')) { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $dir.FullName 'MQL5'))) { continue }
        $origin = Get-Origin $dir.FullName
        $list += [pscustomobject]@{
            Path    = $dir.FullName
            Origin  = $origin
            Refused = (Test-Refused $dir.FullName $origin)
        }
    }
    return $list
}

function Test-TerminalRunning([string]$Origin) {
    # Unknown install location: assume it may be running (safe side, config is then not edited).
    if (-not $Origin) { return $true }
    $installRoot = $Origin.TrimEnd('\')
    foreach ($process in @(Get-Process -Name 'terminal64', 'terminal' -ErrorAction SilentlyContinue)) {
        $path = $null
        try { $path = $process.Path } catch { $path = $null }
        if (-not $path) { return $true }  # cannot inspect (e.g. elevated): be safe
        if ((Split-Path -Parent $path).TrimEnd('\') -ieq $installRoot) { return $true }
    }
    return $false
}

function New-ChartText([string]$ChartSymbol, [int]$Minutes, [string]$ExpertName, [string]$ExpertPath, $Inputs) {
    $inputLines = @($Inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $Inputs[$_] }) -join "`r`n"
    $periodType = if ($Minutes -lt 60) { 0 } elseif ($Minutes -lt 1440) { 1 } else { 2 }
    $periodSize = if ($periodType -eq 0) { $Minutes } elseif ($periodType -eq 1) { [int]($Minutes / 60) } else { [int]($Minutes / 1440) }
    # expertmode=0: the EA is attached but "Allow Algo Trading" stays OFF until the user enables it.
    return @"
<chart>
id=1
symbol=$ChartSymbol
description=$ChartSymbol
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
window_left=0
window_top=0
window_right=960
window_bottom=560
window_type=3
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
name=$ExpertName
path=$ExpertPath
expertmode=0
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

function Update-WebRequestAllowList([string]$IniPath, [string]$Url) {
    $lines = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $IniPath) {
        foreach ($line in [IO.File]::ReadAllLines($IniPath)) { $lines.Add($line) }
        $backup = "$IniPath.calyx-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
        Copy-Item -LiteralPath $IniPath -Destination $backup
    }
    $sectionStart = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].Trim() -ieq '[Experts]') { $sectionStart = $i; break } }
    if ($sectionStart -lt 0) {
        $lines.Add('[Experts]')
        $sectionStart = $lines.Count - 1
    }
    $sectionEnd = $lines.Count
    for ($i = $sectionStart + 1; $i -lt $lines.Count; $i++) { if ($lines[$i].Trim().StartsWith('[')) { $sectionEnd = $i; break } }
    $webIndex = -1
    $urlIndex = -1
    for ($i = $sectionStart + 1; $i -lt $sectionEnd; $i++) {
        if ($lines[$i] -match '^\s*WebRequest\s*=') { $webIndex = $i }
        if ($lines[$i] -match '^\s*WebRequestUrl\s*=') { $urlIndex = $i }
    }
    $changed = $false
    if ($webIndex -ge 0) {
        if ($lines[$webIndex].Trim() -ne 'WebRequest=1') { $lines[$webIndex] = 'WebRequest=1'; $changed = $true }
    } else {
        $lines.Insert($sectionEnd, 'WebRequest=1'); $sectionEnd++; $changed = $true
    }
    if ($urlIndex -ge 0) {
        $current = $lines[$urlIndex].Substring($lines[$urlIndex].IndexOf('=') + 1)
        $urls = @($current -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        if (-not ($urls | Where-Object { $_.TrimEnd('/') -ieq $Url.TrimEnd('/') })) {
            $urls += $Url
            $lines[$urlIndex] = 'WebRequestUrl=' + ($urls -join ';')
            $changed = $true
        }
    } else {
        $lines.Insert($sectionEnd, 'WebRequestUrl=' + $Url); $changed = $true
    }
    if ($changed) { [IO.File]::WriteAllText($IniPath, (($lines -join "`r`n") + "`r`n"), $Unicode) }
    return $changed
}

# ------------------------------------------------------------------ package files
$here = $PSScriptRoot
if (-not $ExpertFile) {
    $found = @(Get-ChildItem -LiteralPath $here -Filter '*.ex5' -File)
    if ($found.Count -ne 1) { Stop-Install 'Expected exactly one .ex5 file next to this installer.' }
    $ExpertFile = $found[0].Name
}
if (-not $SetFile) {
    $found = @(Get-ChildItem -LiteralPath $here -Filter '*.set' -File)
    if ($found.Count -ne 1) { Stop-Install 'Expected exactly one .set file next to this installer.' }
    $SetFile = $found[0].Name
}
$expertSource = Join-Path $here $ExpertFile
$setSource = Join-Path $here $SetFile
if (-not (Test-Path -LiteralPath $expertSource)) { Stop-Install "Missing EA file: $ExpertFile. Extract the whole ZIP first, then run the installer from the extracted folder." }
if (-not (Test-Path -LiteralPath $setSource)) { Stop-Install "Missing SET file: $SetFile. Extract the whole ZIP first." }
if ($AllowUrl -notmatch '^https?://[A-Za-z0-9.-]+(:\d+)?$') { Stop-Install "AllowUrl must be an origin such as https://calyx.duckdns.org (got '$AllowUrl')." }
$inputs = Read-SetInputs $setSource
$licenseKey = if ($inputs.Contains('InpCalyxLicenseKey')) { [string]$inputs['InpCalyxLicenseKey'] } else { '' }

Write-Host "Calyx installer - $BotName" -ForegroundColor Green
Write-Host "EA file : $ExpertFile"
Write-Host "SET file: $SetFile"
if ($licenseKey -match '^CLX-') {
    Write-Host ("License : {0}-****-****-****" -f $licenseKey.Substring(0, [Math]::Min(9, $licenseKey.Length)))
} else {
    Write-Host 'License : NOT FOUND in the SET. Enter InpCalyxLicenseKey in the EA inputs after installation.' -ForegroundColor Yellow
}

# ------------------------------------------------------------------ choose terminal
Write-Step 'MetaTrader 5 data folder'
$target = $null
if ($TargetDataFolder) {
    $full = [IO.Path]::GetFullPath($TargetDataFolder)
    if (-not (Test-Path -LiteralPath (Join-Path $full 'MQL5'))) { Stop-Install "$full is not an MT5 data folder (no MQL5 subfolder). In MT5 use File > Open Data Folder to find it." }
    $origin = Get-Origin $full
    if (Test-Refused $full $origin) { Stop-Install "Refusing $full : it belongs to an Ava/test/tester terminal ($origin)." }
    $target = [pscustomobject]@{ Path = $full; Origin = $origin; Refused = $false }
} else {
    if (-not $TerminalRoot) { $TerminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal' }
    $candidates = @(Get-TerminalCandidates $TerminalRoot)
    $usable = @($candidates | Where-Object { -not $_.Refused })
    foreach ($c in @($candidates | Where-Object { $_.Refused })) {
        Write-Host ("  skipped (Ava/test/tester): {0}  [{1}]" -f $c.Path, $c.Origin) -ForegroundColor DarkYellow
    }
    if ($usable.Count -eq 0) { Stop-Install "No usable MT5 data folder found under $TerminalRoot. Start MT5 once, or pass -TargetDataFolder (MT5: File > Open Data Folder)." }
    for ($i = 0; $i -lt $usable.Count; $i++) {
        $label = if ($usable[$i].Origin) { $usable[$i].Origin } else { '(terminal location unknown)' }
        Write-Host ("  [{0}] {1}" -f ($i + 1), $label)
        Write-Host ("      {0}" -f $usable[$i].Path) -ForegroundColor DarkGray
    }
    if ($Yes) {
        if ($usable.Count -ne 1) { Stop-Install 'Several MT5 terminals found; pass -TargetDataFolder to choose one non-interactively.' }
        $target = $usable[0]
    } else {
        $choice = Read-Host ("Select the terminal to install into [1-{0}]" -f $usable.Count)
        $number = 0
        if (-not [int]::TryParse($choice, [ref]$number) -or $number -lt 1 -or $number -gt $usable.Count) { Stop-Install 'No valid terminal selected.' }
        $target = $usable[$number - 1]
    }
}
Write-Host ("Selected: {0}" -f $target.Path) -ForegroundColor Green
if ($target.Origin) { Write-Host ("Terminal: {0}" -f $target.Origin) }

# ------------------------------------------------------------------ symbol
Write-Step 'Broker symbol'
if (-not $Symbol) {
    if ($Yes) { $Symbol = $DefaultSymbol }
    else {
        Write-Host "Brokers name symbols differently (for example XAUUSD, XAUUSD.r, XAUUSDm, GOLD)."
        Write-Host "Check the exact name in MT5 Market Watch."
        $answer = Read-Host "Symbol name on your broker [$DefaultSymbol]"
        $Symbol = if ($answer) { $answer.Trim() } else { $DefaultSymbol }
    }
}
if ($Symbol -notmatch '^[A-Za-z0-9._#+\-]{2,32}$') { Stop-Install "Symbol '$Symbol' contains unexpected characters." }
Write-Host "Symbol: $Symbol"

# ------------------------------------------------------------------ plan
$mql = Join-Path $target.Path 'MQL5'
$expertDir = Join-Path $mql 'Experts\Calyx'
$presetDir = Join-Path $mql 'Presets'
$testerDir = Join-Path $mql 'Profiles\Tester'
$profileName = ('Calyx - ' + ($BotName -replace '[\\/:*?"<>|]', '-')).Trim()
$profileDir = Join-Path $mql ('Profiles\Charts\' + $profileName)
$iniPath = Join-Path $target.Path 'config\common.ini'
$running = Test-TerminalRunning $target.Origin
$originHost = $AllowUrl

Write-Step 'Plan'
Write-Host "  copy EA     -> $expertDir\$ExpertFile"
Write-Host "  copy SET    -> $presetDir\$SetFile"
Write-Host "  copy SET    -> $testerDir\$SetFile"
Write-Host "  profile     -> $profileDir\chart01.chr ($Symbol, $PeriodMinutes min, EA attached, Algo Trading OFF)"
if ($running) {
    Write-Host "  WebRequest  -> NOT edited: this terminal is running (or its location is unknown). Manual steps below."
} else {
    Write-Host "  WebRequest  -> add $originHost to config\common.ini allow-list (backup kept)"
}
Write-Host "  Algo Trading is never switched on by this installer."

if ($ValidateOnly) {
    Write-Host "`nVALIDATE ONLY: files and target checked, nothing was changed." -ForegroundColor Green
    exit 0
}
if (-not $Yes) {
    $confirm = Read-Host 'Install now? [y/N]'
    if ($confirm -notmatch '^(y|yes)$') { Stop-Install 'Cancelled by user.' 0 }
}

# ------------------------------------------------------------------ install
Write-Step 'Installing'
foreach ($dir in @($expertDir, $presetDir, $testerDir, $profileDir)) {
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}
Copy-Item -LiteralPath $expertSource -Destination (Join-Path $expertDir $ExpertFile) -Force
Copy-Item -LiteralPath $setSource -Destination (Join-Path $presetDir $SetFile) -Force
Copy-Item -LiteralPath $setSource -Destination (Join-Path $testerDir $SetFile) -Force
$expertName = [IO.Path]::GetFileNameWithoutExtension($ExpertFile)
$chart = New-ChartText $Symbol $PeriodMinutes $expertName ('Experts\Calyx\' + $ExpertFile) $inputs
[IO.File]::WriteAllText((Join-Path $profileDir 'chart01.chr'), $chart, $Unicode)
Write-Host '  EA, SET and chart profile copied.' -ForegroundColor Green

$allowListDone = $false
if (-not $running) {
    $configDir = Split-Path -Parent $iniPath
    if (-not (Test-Path -LiteralPath $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }
    $changed = Update-WebRequestAllowList $iniPath $originHost
    $allowListDone = $true
    if ($changed) { Write-Host "  WebRequest allow-list updated ($originHost)." -ForegroundColor Green }
    else { Write-Host "  WebRequest allow-list already contained $originHost." -ForegroundColor Green }
}

# ------------------------------------------------------------------ next steps
Write-Step 'Next steps in MetaTrader 5'
$step = 1
if (-not $allowListDone) {
    Write-Host ("  {0}. Tools > Options > Expert Advisors: tick 'Allow WebRequest for listed URL'," -f $step); $step++
    Write-Host  "     add $originHost and press OK (needed for license activation)."
}
Write-Host ("  {0}. If MT5 was open, restart it (or right-click Navigator > Expert Advisors > Refresh)." -f $step); $step++
Write-Host ("  {0}. File > Profiles > '{1}' opens the {2} chart with the EA attached." -f $step, $profileName, $Symbol); $step++
Write-Host ("  {0}. On the chart press F7 > Common: tick 'Allow Algo Trading' only when you want it to trade." -f $step); $step++
Write-Host ("  {0}. Switch the Algo Trading button in the toolbar on (your decision - this installer never does it)." -f $step); $step++
Write-Host ("  {0}. Check the Experts tab: 'Calyx license: activated for account ...' confirms the license." -f $step); $step++
Write-Host  "  Risk: the EA trades real money on a live account. Backtest results are not a forecast."
exit 0
