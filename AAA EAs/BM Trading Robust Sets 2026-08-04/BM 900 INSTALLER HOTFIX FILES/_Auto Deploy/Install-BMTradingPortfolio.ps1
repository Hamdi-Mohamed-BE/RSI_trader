[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [ValidateSet('100K', '900')]
    [string]$AccountProfile = '100K',
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PackageRoot = Split-Path -Parent $PSScriptRoot
$IsSmallAccount = $AccountProfile -eq '900'
$ProfileName = if ($IsSmallAccount) { 'BM Trading 900 - AUTO' } else { 'BM Trading 100K - AUTO' }
$ExpertFolderName = $ProfileName
$ProbePath = Join-Path $PSScriptRoot 'Probe-MT5.py'
$Unicode = New-Object System.Text.UnicodeEncoding($false, $true)

function Write-Stage([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Stop-WithMessage([string]$Message, [int]$Code = 1) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit $Code
}

function Get-PortfolioItems {
    $rangeSet = if ($IsSmallAccount) {
        'Range Breakout EA\PORTFOLIO 900 - Range Breakout - USDJPY M5 - 18 USD risk.set'
    } else {
        'Range Breakout EA\PORTFOLIO 100K FINAL - Range Breakout - USDJPY M5 - 245 USD risk.set'
    }
    $atrSet = if ($IsSmallAccount) {
        'ATR Candle Breakout EA\PORTFOLIO 900 - ATR Candle Breakout - XAUUSD H1 - 18 USD risk.set'
    } else {
        'ATR Candle Breakout EA\PORTFOLIO 100K FINAL - ATR Candle Breakout - XAUUSD H1 - 146 USD risk.set'
    }
    $goLongSet = if ($IsSmallAccount) {
        'Go Long EA\PORTFOLIO 900 - Go Long - US30 D1 - 0.01 lot.set'
    } else {
        'Go Long EA\PORTFOLIO 100K FINAL - Go Long - US30 D1 - 0.50 lot.set'
    }
    $turnaroundSet = if ($IsSmallAccount) {
        'Turnaround Tuesday EA\PORTFOLIO 900 - Turnaround Tuesday - UT100 D1 - 0.01 lot.set'
    } else {
        'Turnaround Tuesday EA\PORTFOLIO 100K FINAL - Turnaround Tuesday - UT100 D1 - 0.24 lot.set'
    }

    $items = @(
        [pscustomobject]@{
            Label = 'Range Breakout'; Canonical = 'USDJPY'; Aliases = @('USDJPY')
            Period = 5; Expert = 'Range Breakout EA.ex5'
            ExpertSource = 'Range Breakout EA\Range Breakout EA.ex5'
            SetSource = $rangeSet; SmallDynamicRisk = $false
        },
        [pscustomobject]@{
            Label = 'ATR Candle Breakout'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'ATR Candle Breakout EA.ex5'
            ExpertSource = 'ATR Candle Breakout EA\ATR Candle Breakout EA.ex5'
            SetSource = $atrSet; SmallDynamicRisk = $false
        },
        [pscustomobject]@{
            Label = 'Go Long'; Canonical = 'US30'; Aliases = @('US30', 'DJ30', 'WS30', 'DJI30', 'DOW30', 'DOWJONES')
            Period = 1440; Expert = 'Go Long EA.ex5'
            ExpertSource = 'Go Long EA\Go Long EA.ex5'
            SetSource = $goLongSet; SmallDynamicRisk = $true
        },
        [pscustomobject]@{
            Label = 'Turnaround Tuesday'; Canonical = 'NDX100'; Aliases = @('NDX100', 'NAS100', 'USTEC', 'US100', 'UT100', 'NASDAQ100', 'NQ100')
            Period = 1440; Expert = 'Turnaround Tuesday EA.ex5'
            ExpertSource = 'Turnaround Tuesday EA\Turnaround Tuesday EA.ex5'
            SetSource = $turnaroundSet; SmallDynamicRisk = $true
        }
    )

    foreach ($item in $items) {
        $item | Add-Member -NotePropertyName ExpertFullPath -NotePropertyValue (Join-Path $PackageRoot $item.ExpertSource)
        $item | Add-Member -NotePropertyName SetFullPath -NotePropertyValue (Join-Path $PackageRoot $item.SetSource)
    }
    return $items
}

function Get-Mt5Candidates {
    $result = @()
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -and
        -not ([IO.Path]::GetFullPath($_.ExecutablePath).StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase))
    })

    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if (Test-Path -LiteralPath $terminalRoot) {
        foreach ($originFile in @(Get-ChildItem -LiteralPath $terminalRoot -Recurse -Filter origin.txt -File -ErrorAction SilentlyContinue)) {
            $installRoot = (Get-Content -LiteralPath $originFile.FullName -Raw).Trim()
            $installRootFull = [IO.Path]::GetFullPath($installRoot)
            if ($installRootFull.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
            foreach ($exeName in @('terminal64.exe', 'terminal.exe')) {
                $exe = Join-Path $installRoot $exeName
                if (Test-Path -LiteralPath $exe) {
                    $matches = @($running | Where-Object { $_.ExecutablePath -ieq $exe })
                    $result += [pscustomobject]@{
                        Path = $exe
                        DataRoot = $originFile.DirectoryName
                        Running = ($matches.Count -gt 0)
                        ProcessIds = @($matches | ForEach-Object { $_.ProcessId })
                    }
                    break
                }
            }
        }
    }

    foreach ($process in $running) {
        if (-not @($result | Where-Object { $_.Path -ieq $process.ExecutablePath })) {
            $result += [pscustomobject]@{
                Path = $process.ExecutablePath
                DataRoot = ''
                Running = $true
                ProcessIds = @($process.ProcessId)
            }
        }
    }

    return @($result | Sort-Object -Property @{Expression = 'Running'; Descending = $true}, Path -Unique)
}

function Select-Mt5Candidate([object[]]$Candidates) {
    if ($TargetTerminal) {
        $requested = [IO.Path]::GetFullPath($TargetTerminal)
        $candidate = @($Candidates | Where-Object { [IO.Path]::GetFullPath($_.Path) -ieq $requested }) | Select-Object -First 1
        if (-not $candidate) {
            if (-not (Test-Path -LiteralPath $requested)) {
                Stop-WithMessage "The requested MT5 terminal does not exist: $requested"
            }
            return [pscustomobject]@{ Path = $requested; DataRoot = ''; Running = $false; ProcessIds = @() }
        }
        return $candidate
    }

    $running = @($Candidates | Where-Object { $_.Running })
    if ($running.Count -eq 1) {
        return $running[0]
    }

    $choices = if ($running.Count -gt 1) { $running } else { $Candidates }
    if ($choices.Count -eq 0) {
        Stop-WithMessage 'No installed MetaTrader 5 terminal was found.'
    }
    if ($choices.Count -eq 1) {
        return $choices[0]
    }

    Write-Host 'Choose the MT5 installation that contains the account you want to use:' -ForegroundColor Yellow
    for ($i = 0; $i -lt $choices.Count; $i++) {
        $state = if ($choices[$i].Running) { 'RUNNING' } else { 'closed' }
        Write-Host ('  [{0}] {1} ({2})' -f ($i + 1), $choices[$i].Path, $state)
    }
    $answer = Read-Host 'Enter number'
    $number = 0
    if (-not [int]::TryParse($answer, [ref]$number) -or $number -lt 1 -or $number -gt $choices.Count) {
        Stop-WithMessage 'No valid MT5 installation was selected.'
    }
    return $choices[$number - 1]
}

function Normalize-Symbol([string]$Name) {
    return ($Name.ToUpperInvariant() -replace '[^A-Z0-9]', '')
}

function Find-BrokerSymbol([object[]]$Symbols, [string[]]$Aliases, [switch]$AllowFutures) {
    $best = $null
    $bestScore = [int]::MaxValue
    foreach ($symbol in $Symbols) {
        if ([int]$symbol.trade_mode -eq 0) { continue }
        if (-not $AllowFutures -and [string]$symbol.path -match '(?i)future') { continue }
        $normalized = Normalize-Symbol ([string]$symbol.name)
        for ($aliasIndex = 0; $aliasIndex -lt $Aliases.Count; $aliasIndex++) {
            $alias = Normalize-Symbol $Aliases[$aliasIndex]
            $matchScore = $null
            if ($normalized -eq $alias) {
                $matchScore = 0
            } elseif ($normalized.StartsWith($alias) -or $normalized.EndsWith($alias)) {
                $matchScore = 100
            } elseif ($normalized.Contains($alias)) {
                $matchScore = 200
            }
            if ($null -eq $matchScore) { continue }
            $visibilityPenalty = if ([bool]$symbol.visible) { 0 } else { 5 }
            $score = ($matchScore * 1000) + ($aliasIndex * 10) + $visibilityPenalty + ($normalized.Length - $alias.Length)
            if ($score -lt $bestScore) {
                $best = $symbol
                $bestScore = $score
            }
        }
    }
    return $best
}

function Read-SetInputs([string]$Path) {
    $result = New-Object System.Collections.Specialized.OrderedDictionary
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith(';') -or $trimmed.StartsWith('#')) { continue }
        $equals = $trimmed.IndexOf('=')
        if ($equals -lt 1) { continue }
        $key = $trimmed.Substring(0, $equals).Trim()
        $rawValue = $trimmed.Substring($equals + 1)
        $separator = $rawValue.IndexOf('||')
        $value = if ($separator -ge 0) { $rawValue.Substring(0, $separator) } else { $rawValue }
        $result[$key] = $value
    }
    return $result
}

function Get-EffectiveInputs([object]$Item) {
    $inputs = Read-SetInputs $Item.SetFullPath
    if ($IsSmallAccount) {
        if ($inputs.Contains('RiskMoney')) { $inputs['RiskMoney'] = '40' }
        if ($inputs.Contains('InpRiskAmount')) { $inputs['InpRiskAmount'] = '40' }
        if ([bool]$Item.SmallDynamicRisk) {
            $inputs['Volume'] = '0'
            $inputs['Lots'] = ([double]$Item.EffectiveLot).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['RiskPercent'] = '4.44444444'
            $inputs['SlCalcMode'] = '1'
            $inputs['SlValue'] = ([double]$Item.EffectiveStopPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['Commentary'] = 'BM900-DYNAMIC-40USD-HARD-SL'
        }
    }
    return $inputs
}

function New-ChartText([object]$Item, [string]$Symbol, [long]$Id, [int]$Index) {
    $inputs = Get-EffectiveInputs $Item
    $inputLines = @($inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $inputs[$_] }) -join "`r`n"
    $left = if (($Index % 2) -eq 0) { 0 } else { 800 }
    $top = if ($Index -lt 2) { 0 } else { 450 }
    $right = $left + 800
    $bottom = $top + 450
    $expertPath = 'Experts\' + $ExpertFolderName + '\' + $Item.Expert
    $expertName = [IO.Path]::GetFileNameWithoutExtension($Item.Expert)

    return @"
<chart>
id=$Id
symbol=$Symbol
description=$Symbol
period_type=0
period_size=$($Item.Period)
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
        if ($keyLine -ge 0) {
            $lines[$keyLine] = "$Key=$Value"
        } else {
            $lines.Insert($nextSectionLine, "$Key=$Value")
        }
    }
    [IO.File]::WriteAllText($Path, (($lines -join "`r`n") + "`r`n"), $Unicode)
}

function Close-TargetTerminal([string]$ExecutablePath) {
    $targets = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $ExecutablePath
    })
    foreach ($target in $targets) {
        $process = Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
        if ($process) { [void]$process.CloseMainWindow() }
    }
    if ($targets.Count -gt 0) {
        $deadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 500
            $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
                $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $ExecutablePath
            })
        } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)
        if ($remaining.Count -gt 0) {
            Stop-WithMessage 'MT5 did not close cleanly. Nothing was installed. Close that terminal and run this file again.'
        }
    }
}

Write-Stage 'Checking portfolio files'
$portfolio = @(Get-PortfolioItems)
foreach ($item in $portfolio) {
    if (-not (Test-Path -LiteralPath $item.ExpertFullPath)) { Stop-WithMessage "Missing EA: $($item.ExpertFullPath)" }
    if (-not (Test-Path -LiteralPath $item.SetFullPath)) { Stop-WithMessage "Missing settings: $($item.SetFullPath)" }
    $inputs = Read-SetInputs $item.SetFullPath
    if ($inputs.Count -eq 0) { Stop-WithMessage "No settings could be read from: $($item.SetFullPath)" }
    Write-Host ('OK  {0}: {1} inputs' -f $item.Label, $inputs.Count)
}

Write-Stage 'Finding MT5'
$candidates = @(Get-Mt5Candidates)
if ($ValidateOnly) {
    if ($candidates.Count -eq 0) { Stop-WithMessage 'Portfolio files are valid, but no normal MT5 installation was found.' }
    foreach ($candidate in $candidates) {
        $state = if ($candidate.Running) { 'running' } else { 'closed' }
        Write-Host ('{0} [{1}]' -f $candidate.Path, $state)
    }
    Write-Host "`nValidation passed. No terminal, profile, account or file was changed." -ForegroundColor Green
    exit 0
}

$selected = Select-Mt5Candidate $candidates
$terminalPath = [IO.Path]::GetFullPath($selected.Path)
Write-Host "Selected: $terminalPath"

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { Stop-WithMessage 'Python is required for safe account and broker-symbol detection, but it was not found.' }
if (-not (Test-Path -LiteralPath $ProbePath)) { Stop-WithMessage "Missing account probe: $ProbePath" }

Write-Stage 'Reading the active account and broker symbols'
$savedErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $probeOutput = @(& $python.Source $ProbePath --terminal $terminalPath 2>&1)
    $probeExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $savedErrorPreference
}
$probeText = $probeOutput -join "`n"
if ($probeExit -ne 0) {
    try { $probeError = ($probeText | ConvertFrom-Json).error } catch { $probeError = $probeText }
    Stop-WithMessage $probeError
}
try { $probe = $probeText | ConvertFrom-Json } catch { Stop-WithMessage "MT5 returned unreadable account data: $probeText" }
if (-not $probe.ok) { Stop-WithMessage ([string]$probe.error) }

$dataRoot = [IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))) {
    Stop-WithMessage "MT5 reported an invalid data folder: $dataRoot"
}

$login = [string]$probe.account.login
Write-Host ('Account: {0}' -f $login) -ForegroundColor Yellow
Write-Host ('Server:  {0}' -f $probe.account.server)
Write-Host ('Broker:  {0}' -f $probe.account.company)
Write-Host ('Balance: {0:N2} {1}' -f [double]$probe.account.balance, $probe.account.currency)
Write-Host ('Equity:  {0:N2} {1}' -f [double]$probe.account.equity, $probe.account.currency)
Write-Host ('Data:    {0}' -f $dataRoot)

if (-not [bool]$probe.terminal.connected) { Stop-WithMessage 'The selected MT5 terminal is not connected to its trading server.' }
if (-not [bool]$probe.account.trade_allowed) { Stop-WithMessage 'Trading is not allowed on the selected account.' }
if (-not [bool]$probe.account.trade_expert) { Stop-WithMessage 'This account currently blocks Expert Advisor trading.' }

$symbols = @($probe.symbols)
foreach ($item in $portfolio) {
    $match = Find-BrokerSymbol $symbols $item.Aliases
    if (-not $match -and $IsSmallAccount) {
        $match = Find-BrokerSymbol $symbols $item.Aliases -AllowFutures
    }
    if (-not $match) {
        $hints = @($symbols | Where-Object {
            $name = ([string]$_.name).ToUpperInvariant()
            $name -match 'JPY|XAU|GOLD|US30|DOW|NAS|NDX|USTEC|US100|UT100'
        } | Select-Object -First 30 -ExpandProperty name) -join ', '
        Stop-WithMessage "No tradable broker symbol matched $($item.Canonical). Possible symbols: $hints"
    }
    $item | Add-Member -NotePropertyName BrokerSymbol -NotePropertyValue ([string]$match.name)
    $brokerMinimum = [double]$match.volume_min
    $item | Add-Member -NotePropertyName BrokerVolumeMinimum -NotePropertyValue $brokerMinimum
    if ($IsSmallAccount -and [bool]$item.SmallDynamicRisk) {
        $price = [Math]::Max([Math]::Max([double]$match.bid, [double]$match.ask), [double]$match.reference_price)
        $tickSize = [Math]::Abs([double]$match.trade_tick_size)
        $tickValue = [Math]::Max([Math]::Abs([double]$match.trade_tick_value_loss), [Math]::Abs([double]$match.trade_tick_value))
        $volumeStep = [Math]::Abs([double]$match.volume_step)
        $volumeMaximum = [double]$match.volume_max
        if ($price -le 0 -or $tickSize -le 0 -or $tickValue -le 0 -or $brokerMinimum -le 0 -or $volumeStep -le 0) {
            Stop-WithMessage "Cannot calculate a broker-specific USD 40 stop for $($item.Label) on $($item.BrokerSymbol). Quote or contract data is missing."
        }

        $targetRisk = 40.0
        $preferredStopPercent = 0.75
        $preferredDistance = $price * ($preferredStopPercent / 100.0)
        $riskPerLot = ($preferredDistance / $tickSize) * $tickValue
        $rawLot = $targetRisk / $riskPerLot
        $steps = [Math]::Round(($rawLot - $brokerMinimum) / $volumeStep, 0, [MidpointRounding]::AwayFromZero)
        $effectiveLot = $brokerMinimum + ([Math]::Max(0, $steps) * $volumeStep)
        $effectiveLot = [Math]::Min($volumeMaximum, [Math]::Max($brokerMinimum, $effectiveLot))
        $effectiveLot = [Math]::Round($effectiveLot, 8)
        $effectiveStopPercent = (($targetRisk * $tickSize) / ($tickValue * $effectiveLot * $price)) * 100.0
        if ($effectiveStopPercent -le 0) {
            Stop-WithMessage "The calculated hard stop for $($item.Label) is invalid."
        }
        $item | Add-Member -NotePropertyName EffectiveLot -NotePropertyValue $effectiveLot
        $item | Add-Member -NotePropertyName EffectiveStopPercent -NotePropertyValue $effectiveStopPercent
        $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue $targetRisk
        Write-Host ('{0,-22} {1,-8} -> {2}; lot {3}, hard SL {4:N4}%, target ${5:N0}' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $effectiveLot, $effectiveStopPercent, $targetRisk) -ForegroundColor Yellow
    } else {
        Write-Host ('{0,-22} {1,-8} -> {2}; requested stop risk $40' -f $item.Label, $item.Canonical, $item.BrokerSymbol)
    }
}

$balance = [double]$probe.account.balance
if ([string]$probe.account.currency -ine 'USD') {
    Stop-WithMessage "Refusing to run: these fixed-money settings require a USD account, but account $login uses $($probe.account.currency)."
}
if ($IsSmallAccount) {
    if ($balance -lt 800 -or $balance -gt 1200) {
        Stop-WithMessage "Refusing to run: the small-account settings are for roughly USD 900, but account $login has a balance of $($balance.ToString('N2')) $($probe.account.currency). Use an account between USD 800 and USD 1,200."
    }
} elseif ($balance -lt 90000 -or $balance -gt 110000) {
    Stop-WithMessage "Refusing to run: these settings are for a USD 100,000 account, but account $login has a balance of $($balance.ToString('N2')) $($probe.account.currency). Log into the correct 100K account and run the BAT again."
}

Write-Host "`nThis will close and restart the selected MT5, enable Algo Trading, switch to a new" -ForegroundColor Yellow
Write-Host "$($portfolio.Count)-chart profile, and the EAs may place REAL TRADES immediately." -ForegroundColor Yellow
if ($IsSmallAccount) {
    Write-Host 'SMALL ACCOUNT: all four EAs target approximately $40 loss per stopped trade.' -ForegroundColor Red
    Write-Host 'The installer adds broker-specific hard stops to the two index EAs; gaps can still lose more.' -ForegroundColor Red
}
Write-Host 'It does not delete your existing profiles or close any open positions.' -ForegroundColor Yellow
$expected = if ($IsSmallAccount) { "RUN $login 900" } else { "RUN $login" }
$confirmation = Read-Host "Type exactly '$expected' to continue"
if ($confirmation -cne $expected) { Stop-WithMessage 'Confirmation did not match. No portfolio files were installed.' }

Write-Stage 'Closing MT5 cleanly'
Close-TargetTerminal $terminalPath

Write-Stage 'Installing EAs, settings and isolated chart profile'
$mql5Root = Join-Path $dataRoot 'MQL5'
$expertsTarget = Join-Path (Join-Path $mql5Root 'Experts') $ExpertFolderName
$testerTarget = Join-Path (Join-Path $mql5Root 'Profiles\Tester') $ProfileName
$chartsRoot = Join-Path $mql5Root 'Profiles\Charts'
$profileTarget = Join-Path $chartsRoot $ProfileName

foreach ($directory in @($expertsTarget, $testerTarget, $chartsRoot)) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

$chartsRootFull = [IO.Path]::GetFullPath($chartsRoot).TrimEnd('\') + '\'
$profileTargetFull = [IO.Path]::GetFullPath($profileTarget)
if (-not $profileTargetFull.StartsWith($chartsRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-WithMessage "Refusing to replace an unsafe profile path: $profileTargetFull"
}
if (Test-Path -LiteralPath $profileTargetFull) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileTargetFull -Destination $backup
    Write-Host "Previous auto profile backed up to: $backup"
}
[void](New-Item -ItemType Directory -Path $profileTargetFull -Force)

for ($i = 0; $i -lt $portfolio.Count; $i++) {
    $item = $portfolio[$i]
    Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $expertsTarget $item.Expert) -Force
    if ($IsSmallAccount) {
        $effectiveInputs = Get-EffectiveInputs $item
        $effectiveSetText = (@($effectiveInputs.Keys | ForEach-Object { '{0}={1}' -f $_, $effectiveInputs[$_] }) -join "`r`n") + "`r`n"
        $safeLabel = $item.Label -replace '[^A-Za-z0-9 -]', ''
        $effectiveSetName = "LAST INSTALLED 900 - $safeLabel - $($item.BrokerSymbol).set"
        $effectiveSetSource = Join-Path (Split-Path -Parent $item.SetFullPath) $effectiveSetName
        [IO.File]::WriteAllText($effectiveSetSource, $effectiveSetText, [Text.UTF8Encoding]::new($true))
        Copy-Item -LiteralPath $effectiveSetSource -Destination (Join-Path $testerTarget $effectiveSetName) -Force
        $item | Add-Member -NotePropertyName EffectiveSetPath -NotePropertyValue $effectiveSetSource
    } else {
        Copy-Item -LiteralPath $item.SetFullPath -Destination (Join-Path $testerTarget ([IO.Path]::GetFileName($item.SetFullPath))) -Force
    }
    $chartName = 'chart{0:D2}.chr' -f ($i + 1)
    $chartPath = Join-Path $profileTargetFull $chartName
    $chartText = New-ChartText $item $item.BrokerSymbol ([DateTime]::UtcNow.Ticks + $i) $i
    [IO.File]::WriteAllText($chartPath, $chartText.TrimStart(), $Unicode)
    Write-Host ('Installed {0} on {1}, period {2}' -f $item.Label, $item.BrokerSymbol, $item.Period)
}

$orderText = ((1..$portfolio.Count | ForEach-Object { 'chart{0:D2}.chr' -f $_ }) -join "`r`n") + "`r`n"
[IO.File]::WriteAllText((Join-Path $profileTargetFull 'order.wnd'), $orderText, $Unicode)

$commonIni = Join-Path $dataRoot 'config\common.ini'
if (-not (Test-Path -LiteralPath $commonIni)) { Stop-WithMessage "MT5 common settings were not found: $commonIni" }
$commonBackup = $commonIni + '.bm-auto-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
Copy-Item -LiteralPath $commonIni -Destination $commonBackup
Set-IniValue $commonIni 'Experts' 'Enabled' '1'
Set-IniValue $commonIni 'Experts' 'Account' '0'
Set-IniValue $commonIni 'Experts' 'Profile' '0'
Set-IniValue $commonIni 'Experts' 'Chart' '0'

$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $terminalPath
    'Data folder: ' + $dataRoot
    'Profile: ' + $ProfileName
    'Account preset: ' + $AccountProfile
    'Account: ' + $login
    'Balance at install: ' + $balance.ToString('N2') + ' ' + [string]$probe.account.currency
    'Server: ' + [string]$probe.account.server
    ''
    'Charts:'
) + @($portfolio | ForEach-Object {
    if ($IsSmallAccount -and [bool]$_.SmallDynamicRisk) {
        '{0}: {1}, period {2}, {3}; lot {4}; hard SL {5:N4}%; target risk USD {6:N2}; set {7}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveLot, $_.EffectiveStopPercent, $_.EffectiveRisk, $_.EffectiveSetPath
    } elseif ($IsSmallAccount) {
        '{0}: {1}, period {2}, {3}; requested stop risk USD 40; set {4}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveSetPath
    } else {
        '{0}: {1}, period {2}, {3}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert
    }
})
$manifestPath = Join-Path $PSScriptRoot 'LAST INSTALL.txt'
[IO.File]::WriteAllText($manifestPath, (($manifest -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($true))

Write-Stage "Starting the $($portfolio.Count)-EA profile"
$arguments = '/profile:"' + $ProfileName + '"'
Start-Process -FilePath $terminalPath -ArgumentList $arguments
Start-Sleep -Seconds 12

$runningNow = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $terminalPath
})
if ($runningNow.Count -eq 0) { Stop-WithMessage 'The files were installed, but MT5 did not remain running.' }

$missingExperts = @()
foreach ($chartFile in @(Get-ChildItem -LiteralPath $profileTargetFull -Filter 'chart*.chr' -File)) {
    if (-not (Select-String -LiteralPath $chartFile.FullName -SimpleMatch '<expert>' -Quiet)) {
        $missingExperts += $chartFile.Name
    }
}
if ($missingExperts.Count -gt 0) {
    Stop-WithMessage ('MT5 opened, but these charts lost their EA attachment: ' + ($missingExperts -join ', '))
}

Write-Host "`nSUCCESS: MT5 is running the '$ProfileName' profile on account $login." -ForegroundColor Green
Write-Host "Install record: $manifestPath"
Write-Host 'Verify the four chart faces show the EA name and the toolbar Algo Trading button is green.' -ForegroundColor Yellow
