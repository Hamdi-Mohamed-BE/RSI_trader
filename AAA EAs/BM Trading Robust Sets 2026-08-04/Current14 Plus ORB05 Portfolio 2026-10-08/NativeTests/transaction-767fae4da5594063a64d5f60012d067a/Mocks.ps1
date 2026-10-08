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

function New-ChartText([object]$Item, [string]$Symbol, [long]$Id, [int]$Index) {
    $inputs = Get-EffectiveInputs $Item
    $inputLines = @($inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $inputs[$_] }) -join "`r`n"
    $columns = 4
    $width = 480
    $height = 280
    $left = ($Index % $columns) * $width
    $top = [Math]::Floor($Index / $columns) * $height
    $right = $left + $width
    $bottom = $top + $height
    $expertPath = 'Experts\' + $ExpertFolderName + '\' + $Item.Expert
    $expertName = [IO.Path]::GetFileNameWithoutExtension($Item.Expert)
    $periodType = if ($Item.Period -lt 60) { 0 } elseif ($Item.Period -lt 1440) { 1 } else { 2 }
    $periodSize = if ($periodType -eq 0) { $Item.Period } elseif ($periodType -eq 1) { [int]($Item.Period / 60) } else { [int]($Item.Period / 1440) }

    return @"
<chart>
id=$Id
symbol=$Symbol
description=$Symbol
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

function Test-ManagedProfile([string]$ProfilePath, [object[]]$ExpectedPortfolio, [string]$Stage) {
    $chartFiles = @(Get-ChildItem -LiteralPath $ProfilePath -Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object Name)
    if ($chartFiles.Count -ne $ExpectedPortfolio.Count) {
        Stop-WithMessage ("{0}: profile contains {1} chart files, but {2} were expected." -f $Stage, $chartFiles.Count, $ExpectedPortfolio.Count)
    }

    $problems = [Collections.Generic.List[string]]::new()
    for ($index = 0; $index -lt $ExpectedPortfolio.Count; $index++) {
        $item = $ExpectedPortfolio[$index]
        $chartName = 'chart{0:D2}.chr' -f ($index + 1)
        $chartPath = Join-Path $ProfilePath $chartName
        if (-not (Test-Path -LiteralPath $chartPath)) {
            [void]$problems.Add("$chartName is missing")
            continue
        }
        $text = Get-Content -LiteralPath $chartPath -Raw
        $expectedName = [IO.Path]::GetFileNameWithoutExtension([string]$item.Expert)
        $expectedPath = 'Experts\' + $ExpertFolderName + '\' + [string]$item.Expert
        $expectedPeriodType = if ($item.Period -lt 60) { 0 } elseif ($item.Period -lt 1440) { 1 } else { 2 }
        $expectedPeriodSize = if ($expectedPeriodType -eq 0) { $item.Period } elseif ($expectedPeriodType -eq 1) { [int]($item.Period / 60) } else { [int]($item.Period / 1440) }
        $checks = @(
            @{ Label = 'symbol'; Token = "symbol=$($item.BrokerSymbol)" },
            @{ Label = 'period type'; Token = "period_type=$expectedPeriodType" },
            @{ Label = 'period'; Token = "period_size=$expectedPeriodSize" },
            @{ Label = 'EA name'; Token = "name=$expectedName" },
            @{ Label = 'EA path'; Token = "path=$expectedPath" },
            @{ Label = 'enabled expert mode'; Token = 'expertmode=1' },
            @{ Label = 'expert attachment'; Token = '<expert>' }
        )
        foreach ($check in $checks) {
            if (-not $text.Contains([string]$check.Token)) {
                [void]$problems.Add(("{0}: wrong or missing {1} (expected '{2}')" -f $chartName, $check.Label, $check.Token))
            }
        }
    }
    if ($problems.Count -gt 0) {
        Stop-WithMessage ("$Stage profile verification failed:`n - " + ($problems -join "`n - "))
    }
    Write-Host ("{0}: verified all {1} exact symbol, timeframe and EA attachments." -f $Stage, $ExpectedPortfolio.Count) -ForegroundColor Green
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

function Write-Stage([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Stop-WithMessage([string]$Message, [int]$Code = 1) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit $Code
}
function Get-Mt5Candidates { return $MockCandidate }
function Assert-RunningTerminal { }
function Invoke-AccountProbe { return $MockProbe }
function Close-TargetTerminal { $script:Closed++ }
function Read-Host([string]$Prompt) {
 if($MockMode -eq 'DEFAULTS' -and $Prompt -match 'Risk mode|Percentage per trade|DI filter'){return ''}
 throw "Unexpected interactive prompt in offline test: $Prompt"
}
function Start-Profile([string]$Terminal,[string]$Name) {
 $script:Started+=@($Name)
 if($Name -ne 'Calyx CURRENT14 ORB05'){return}
 if($MockMode -eq 'FAIL'){throw 'Injected restart failure - offline test'}
 foreach($item in $portfolio){
  $cash=if($RiskMode -eq 'FIXED_USD'){$RiskValue}else{50.0};$mode=if($RiskMode -eq 'FIXED_USD'){'1'}else{'0'}
  $parts=@([DateTimeOffset]::UtcNow.ToUnixTimeSeconds(),$ActiveLogin,$ActiveServer,$item.BrokerSymbol,$item.Magic,$InstallNonce,$mode,$cash)
  [IO.File]::WriteAllText((Join-Path $MockProbe.terminal.commondata_path "Files\CalyxCurrent14ORB05-$($item.Magic).tsv"),($parts -join "`t")+"`n")
 }
}