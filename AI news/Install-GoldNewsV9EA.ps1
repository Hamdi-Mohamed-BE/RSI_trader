[CmdletBinding()]
param(
    [switch]$ValidateOnly,
    [switch]$RuntimeOnly,
    [string]$TargetTerminal = '',
    [switch]$IsolatedProfile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
$DedicatedProfileName = 'GOLD NEWS V9 - XAU AUTO'
$ProfileName = $DedicatedProfileName
$ExpertFolderName = 'Gold News V9'
$ExpertBaseName = 'GoldNewsV9EA'
$ApiBaseUrl = 'http://127.0.0.1:8799'
$ApiPort = 8799
$Unicode = [Text.UnicodeEncoding]::new($false, $true)
$NewLine = [Environment]::NewLine
$env:PYTHONDONTWRITEBYTECODE = '1'
$UvPath = ''

function Stop-Install([string]$Message) {
    Write-Host ''
    Write-Host "STOPPED: $Message" -ForegroundColor Red
    exit 1
}

function Write-Stage([string]$Message) {
    Write-Host ''
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Set-IniValue(
    [string]$Path,
    [string]$Section,
    [string]$Key,
    [string]$Value
) {
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -LiteralPath $Path) {
        [void]$lines.Add($line)
    }
    $sectionLine = -1
    $nextSectionLine = $lines.Count
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -ieq "[$Section]") {
            $sectionLine = $i
            for ($j = $i + 1; $j -lt $lines.Count; $j++) {
                if ($lines[$j].Trim().StartsWith('[')) {
                    $nextSectionLine = $j
                    break
                }
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
            if ($lines[$i] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) {
                $keyLine = $i
                break
            }
        }
        if ($keyLine -ge 0) {
            $lines[$keyLine] = "$Key=$Value"
        } else {
            $lines.Insert($nextSectionLine, "$Key=$Value")
        }
    }
    [IO.File]::WriteAllText(
        $Path,
        (($lines -join $NewLine) + $NewLine),
        $Unicode
    )
}

function Get-IniValue(
    [string]$Path,
    [string]$Section,
    [string]$Key
) {
    $insideSection = $false
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ($trimmed -match '^\[(.+)\]$') {
            $insideSection = $Matches[1] -ieq $Section
            continue
        }
        if ($insideSection -and $trimmed -match ('^' + [regex]::Escape($Key) + '\s*=\s*(.*)$')) {
            return $Matches[1].Trim()
        }
    }
    return ''
}

function Test-RuntimeHeartbeat(
    [string]$Path,
    [string]$ExpectedSymbol,
    [int]$MaxAgeSeconds = 120
) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        $line = [string](Get-Content -LiteralPath $Path -TotalCount 1 -ErrorAction Stop)
        $parts = @($line -split "`t", 4)
        if ($parts.Count -lt 3) { return $false }
        [long]$epoch = 0
        if (-not [long]::TryParse($parts[0].Trim(), [ref]$epoch)) { return $false }
        $ageSeconds = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $epoch
        return $ageSeconds -ge -5 -and
            $ageSeconds -le $MaxAgeSeconds -and
            $parts[2].Trim() -ieq $ExpectedSymbol
    } catch {
        return $false
    }
}

function Resolve-Uv([switch]$AllowInstall) {
    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($uv) { return $uv.Source }
    if (-not $AllowInstall) {
        Stop-Install 'uv is required for validation but was not found. Run INSTALL_AND_RUN_GOLD_NEWS_V9.bat once to install it.'
    }

    Write-Host 'uv was not found; installing it now...' -ForegroundColor Yellow
    try {
        $installScript = Invoke-RestMethod -Uri 'https://astral.sh/uv/install.ps1' -TimeoutSec 60
        & ([ScriptBlock]::Create([string]$installScript))
    } catch {
        Stop-Install ("uv could not be installed automatically: {0}" -f $_.Exception.Message)
    }
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
    if (-not $uv) {
        Stop-Install 'uv installation finished, but uv.exe is still unavailable in this session.'
    }
    return $uv.Source
}

function Close-Terminal([int]$ProcessId) {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
        return
    }
    [void]$process.CloseMainWindow()
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    } while ($process -and (Get-Date) -lt $deadline)
    if ($process) {
        Stop-Install 'MT5 did not close cleanly. Close it manually and run the BAT again.'
    }
}

function Test-EaApi {
    try {
        $health = Invoke-RestMethod -Uri "$ApiBaseUrl/api/health" -TimeoutSec 3
        $next = Invoke-RestMethod -Uri "$ApiBaseUrl/api/ea/next?days=1" -TimeoutSec 3
        return $health.status -eq 'ok' -and
            $health.mt5_file_bridge.status -in @('starting', 'ready') -and
            $null -ne $next.status
    } catch {
        return $false
    }
}

function Show-ServerLogs([string]$Stdout, [string]$Stderr) {
    Write-Host ''
    Write-Host '=== Prediction server error log ===' -ForegroundColor Red
    if (Test-Path -LiteralPath $Stderr) {
        $errorText = Get-Content -LiteralPath $Stderr -Raw
        Write-Host ($errorText.Trim())
    } else {
        Write-Host '(no stderr log was created)'
    }
    Write-Host ''
    Write-Host '=== Prediction server output log ===' -ForegroundColor Yellow
    if (Test-Path -LiteralPath $Stdout) {
        $outputText = Get-Content -LiteralPath $Stdout -Raw
        Write-Host ($outputText.Trim())
    } else {
        Write-Host '(no stdout log was created)'
    }
    Write-Host ''
}

function Ensure-LocalApi {
    if (Test-EaApi) {
        Write-Host "Local prediction server is ready at $ApiBaseUrl"
        return
    }

    $listener = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $owner -or [string]$owner.CommandLine -notmatch '(?i)uvicorn.*app:app') {
            Stop-Install "Port $ApiPort is occupied by another application."
        }
        Stop-Process -Id $listener.OwningProcess -Force
        Start-Sleep -Seconds 2
    }

    if (-not $UvPath) { $script:UvPath = Resolve-Uv -AllowInstall }
    $tmp = Join-Path $PackageRoot 'tmp'
    [void](New-Item -ItemType Directory -Path $tmp -Force)
    $stdout = Join-Path $tmp 'gold-news-v9-server.out.log'
    $stderr = Join-Path $tmp 'gold-news-v9-server.err.log'
    [IO.File]::WriteAllText($stdout, '', [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText($stderr, '', [Text.UTF8Encoding]::new($false))

    Write-Host 'Checking that the prediction application imports correctly...'
    Push-Location $PackageRoot
    try {
        & $UvPath run --quiet python -c "import app; print('Prediction application import OK')"
        if ($LASTEXITCODE -ne 0) {
            Stop-Install 'The prediction application could not be imported. The error is shown above.'
        }
    } finally {
        Pop-Location
    }
    $arguments = @(
        'run',
        '--quiet',
        'python',
        '-u',
        '-m',
        'uvicorn',
        'app:app',
        '--host',
        '127.0.0.1',
        '--port',
        [string]$ApiPort
    )
    $serverProcess = Start-Process -FilePath $UvPath -ArgumentList $arguments -WorkingDirectory $PackageRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        if (Test-EaApi) {
            Write-Host "Local prediction server started at $ApiBaseUrl"
            return
        }
        if ($serverProcess.HasExited) {
            Show-ServerLogs $stdout $stderr
            Stop-Install "The prediction server exited with code $($serverProcess.ExitCode)."
        }
    } while ((Get-Date) -lt $deadline)
    Show-ServerLogs $stdout $stderr
    Stop-Install 'The prediction server did not become ready within 30 seconds.'
}

$mq5Source = Join-Path $PackageRoot "mt5\$ExpertBaseName.mq5"
$ex5Source = Join-Path $PackageRoot "mt5\$ExpertBaseName.ex5"
$presetSource = Join-Path $PackageRoot "mt5\$ExpertBaseName-Auto.set"
$probe = Join-Path $PackageRoot 'mt5_installer_probe.py'
$appSource = Join-Path $PackageRoot 'app.py'
$bridgeSource = Join-Path $PackageRoot 'ea_file_bridge.py'
$projectFile = Join-Path $PackageRoot 'pyproject.toml'
$directionModel = Join-Path $PackageRoot 'models\gold_news_v9_direction.joblib'
$moveModel = Join-Path $PackageRoot 'models\gold_news_v8_move_range.joblib'
foreach ($required in @(
    $mq5Source,
    $presetSource,
    $probe,
    $appSource,
    $bridgeSource,
    $projectFile,
    $directionModel,
    $moveModel
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        Stop-Install "Missing package file: $required"
    }
}
$UvPath = Resolve-Uv -AllowInstall:(-not $ValidateOnly)

Write-Stage 'Finding the active MT5 and broker gold symbol'
$tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and
    $_.ExecutablePath -and
    -not ([IO.Path]::GetFullPath($_.ExecutablePath).StartsWith(
        $tempRoot,
        [StringComparison]::OrdinalIgnoreCase
    )) -and
    $_.ExecutablePath -notmatch '(?i)\\_Backtests\\'
})
if ($TargetTerminal) {
    $requestedTerminal = [IO.Path]::GetFullPath($TargetTerminal)
    $running = @($running | Where-Object {
        [IO.Path]::GetFullPath([string]$_.ExecutablePath) -ieq $requestedTerminal
    })
}
if ($running.Count -eq 0) {
    $targetHint = if ($TargetTerminal) { " at $TargetTerminal" } else { '' }
    Stop-Install "No active MT5 was found$targetHint. Open and log into the target account, then run the BAT again."
}
if ($running.Count -gt 1) {
    Write-Host 'More than one MT5 is open:' -ForegroundColor Yellow
    $running | ForEach-Object {
        Write-Host ('  PID {0}: {1}' -f $_.ProcessId, $_.ExecutablePath)
    }
    Stop-Install 'Leave only the target MT5 open, then run the BAT again.'
}

$target = $running[0]
$terminalPath = [IO.Path]::GetFullPath([string]$target.ExecutablePath)
$probeOutput = @(
    & $UvPath run --project $PackageRoot --quiet python $probe --terminal $terminalPath 2>&1
)
if ($LASTEXITCODE -ne 0 -or $probeOutput.Count -eq 0) {
    Stop-Install ('MT5 probe failed: ' + ($probeOutput -join ' '))
}
try {
    $probeResult = ([string]$probeOutput[-1]) | ConvertFrom-Json
} catch {
    Stop-Install ('MT5 probe returned invalid data: ' + ($probeOutput -join ' '))
}
$dataRoot = [IO.Path]::GetFullPath([string]$probeResult.data_path)
$symbol = [string]$probeResult.symbol
Write-Host "Terminal: $terminalPath"
Write-Host "Data:     $dataRoot"
Write-Host "Server:   $($probeResult.server)"
Write-Host "Symbol:   $symbol"
Write-Host "API:      $ApiBaseUrl"
Write-Host "Account:  $($probeResult.account_trade_mode)" -ForegroundColor Yellow
Write-Host 'Trading:  ENABLED on both demo and real accounts' -ForegroundColor Yellow
Write-Host 'Comment:  AI news {event} {buy/sell} {confidence%}'
$env:GOLD_NEWS_MT5_COMMON_PATH = [string]$probeResult.commondata_path

$commonIni = Join-Path $dataRoot 'config\common.ini'
$chartsRoot = Join-Path $dataRoot 'MQL5\Profiles\Charts'
if (-not $IsolatedProfile -and (Test-Path -LiteralPath $commonIni)) {
    $activeProfile = Get-IniValue $commonIni 'Charts' 'ProfileLast'
    $activeProfilePath = if ($activeProfile) { Join-Path $chartsRoot $activeProfile } else { '' }
    $isPlainProfileName = $activeProfile -and ([IO.Path]::GetFileName($activeProfile) -eq $activeProfile)
    if ($isPlainProfileName -and (Test-Path -LiteralPath $activeProfilePath -PathType Container)) {
        $ProfileName = $activeProfile
    }
}
Write-Host "Profile:  $ProfileName"

if ($ValidateOnly) {
    Write-Host ''
    Write-Host 'VALIDATION PASSED: no MT5 files or settings were changed.' -ForegroundColor Green
    exit 0
}

if ($RuntimeOnly) {
    Write-Stage 'Starting the local prediction server'
    Ensure-LocalApi
    Write-Host ''
    Write-Host 'SUCCESS: Gold News V9 prediction runtime is ready.' -ForegroundColor Green
    exit 0
}

Write-Stage 'Compiling the EA'
$metaEditor = Join-Path (Split-Path -Parent $terminalPath) 'MetaEditor64.exe'
if (-not (Test-Path -LiteralPath $metaEditor)) {
    Stop-Install "MetaEditor was not found beside MT5: $metaEditor"
}
$buildRoot = Join-Path $env:LOCALAPPDATA (
    'GoldNewsV9Build-' + (Get-Date -Format 'yyyyMMddHHmmss')
)
[void](New-Item -ItemType Directory -Path $buildRoot)
$buildMq5 = Join-Path $buildRoot "$ExpertBaseName.mq5"
$buildEx5 = Join-Path $buildRoot "$ExpertBaseName.ex5"
$buildLog = Join-Path $buildRoot 'compile.log'
Copy-Item -LiteralPath $mq5Source -Destination $buildMq5
& $metaEditor "/compile:$buildMq5" "/log:$buildLog"
$compileDeadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
} while (
    ((-not (Test-Path -LiteralPath $buildLog)) -or
    (-not (Test-Path -LiteralPath $buildEx5))) -and
    (Get-Date) -lt $compileDeadline
)
if ((-not (Test-Path -LiteralPath $buildLog)) -or
    (-not (Test-Path -LiteralPath $buildEx5))) {
    Stop-Install "MetaEditor did not create the compiled EA. Build folder: $buildRoot"
}
$compileText = Get-Content -LiteralPath $buildLog -Raw
if ($compileText -notmatch 'Result:\s+0 errors,\s+0 warnings') {
    Stop-Install "EA compilation failed. Check $buildLog"
}
Copy-Item -LiteralPath $buildEx5 -Destination $ex5Source -Force
Copy-Item -LiteralPath $buildLog -Destination (Join-Path $PackageRoot 'mt5\compile.log') -Force
Write-Host 'EA compiled with 0 errors and 0 warnings.'

Write-Stage 'Starting the local prediction server'
Ensure-LocalApi

Write-Stage 'Installing the EA and auto-attach profile'
Close-Terminal ([int]$target.ProcessId)
$mql5Root = Join-Path $dataRoot 'MQL5'
$expertsTarget = Join-Path $mql5Root "Experts\$ExpertFolderName"
$presetsTarget = Join-Path $mql5Root 'Profiles\Presets'
$profileTarget = Join-Path $chartsRoot $ProfileName
foreach ($directory in @($expertsTarget, $presetsTarget, $chartsRoot)) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

$chartsRootFull = [IO.Path]::GetFullPath($chartsRoot).TrimEnd('\') + '\'
$profileTargetFull = [IO.Path]::GetFullPath($profileTarget)
if (-not $profileTargetFull.StartsWith(
    $chartsRootFull,
    [StringComparison]::OrdinalIgnoreCase
)) {
    Stop-Install "Unsafe profile target: $profileTargetFull"
}
if ((Test-Path -LiteralPath $profileTargetFull) -and $IsolatedProfile) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileTargetFull -Destination $backup
    Write-Host "Previous profile backed up to: $backup"
} elseif (Test-Path -LiteralPath $profileTargetFull) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Copy-Item -LiteralPath $profileTargetFull -Destination $backup -Recurse
    Write-Host "Existing profile preserved; backup copied to: $backup"
}
[void](New-Item -ItemType Directory -Path $profileTargetFull -Force)

Copy-Item -LiteralPath $mq5Source -Destination (Join-Path $expertsTarget "$ExpertBaseName.mq5") -Force
Copy-Item -LiteralPath $ex5Source -Destination (Join-Path $expertsTarget "$ExpertBaseName.ex5") -Force
Copy-Item -LiteralPath $presetSource -Destination (Join-Path $presetsTarget "$ExpertBaseName-Auto.set") -Force

$setText = Get-Content -LiteralPath $presetSource -Raw
$inputLines = (($setText -split '\r?\n') | Where-Object {
    $_.Trim() -ne ''
}) -join $NewLine
$chartId = [DateTime]::UtcNow.Ticks
$expertPath = "Experts\$ExpertFolderName\$ExpertBaseName.ex5"
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
name=$ExpertBaseName
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
$profileCharts = @(Get-ChildItem -LiteralPath $profileTargetFull -Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object Name)
$goldChart = $profileCharts | Where-Object {
    Select-String -LiteralPath $_.FullName -Pattern '(^|\\)GoldNewsV9EA(?:\.ex5)?$|name=GoldNewsV9EA$' -Quiet
} | Select-Object -First 1
if ($goldChart) {
    $chartName = $goldChart.Name
    Write-Host "Refreshing existing Gold News chart: $chartName"
} else {
    $usedNumbers = @($profileCharts | ForEach-Object {
        if ($_.BaseName -match '^chart(\d+)$') { [int]$Matches[1] }
    })
    $nextChartNumber = if ($usedNumbers.Count -gt 0) { ([int]($usedNumbers | Measure-Object -Maximum).Maximum) + 1 } else { 1 }
    $chartName = 'chart{0:D2}.chr' -f $nextChartNumber
    Write-Host "Adding Gold News chart without removing $($profileCharts.Count) existing chart(s): $chartName"
}
$chartPath = Join-Path $profileTargetFull $chartName
[IO.File]::WriteAllText(
    $chartPath,
    $chartText.TrimStart(),
    $Unicode
)
$orderPath = Join-Path $profileTargetFull 'order.wnd'
$orderEntries = @(
    if (Test-Path -LiteralPath $orderPath) {
        Get-Content -LiteralPath $orderPath | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    } else {
        $profileCharts | Select-Object -ExpandProperty Name
    }
)
if ($chartName -notin $orderEntries) { $orderEntries += $chartName }
[IO.File]::WriteAllText($orderPath, (($orderEntries -join $NewLine) + $NewLine), $Unicode)

if (-not (Test-Path -LiteralPath $commonIni)) {
    Stop-Install "MT5 common.ini was not found: $commonIni"
}
$commonBackup = $commonIni + '.gold-news-v9-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
Copy-Item -LiteralPath $commonIni -Destination $commonBackup -Force
Set-IniValue $commonIni 'Experts' 'Enabled' '1'
Set-IniValue $commonIni 'Experts' 'Account' '0'
Set-IniValue $commonIni 'Experts' 'Profile' '0'
Set-IniValue $commonIni 'Experts' 'Chart' '0'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName

$manifestPath = Join-Path $PackageRoot 'LAST_GOLD_NEWS_V9_INSTALL.txt'
$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $terminalPath
    'Data folder: ' + $dataRoot
    'Server: ' + [string]$probeResult.server
    'Account: ' + [string]$probeResult.login
    'Account mode: ' + [string]$probeResult.account_trade_mode
    'Profile: ' + $ProfileName
    'Profile mode: ' + $(if ($IsolatedProfile) { 'isolated' } else { 'preserve active profile' })
    'Symbol: ' + $symbol
    'Timeframe: M1'
    'EA: ' + $ExpertBaseName + '.ex5'
    'API: ' + $ApiBaseUrl
    'Events: NFP, CPI, FOMC'
    'Trading enabled: true'
    'Demo-account lock: false'
    'Risk: 1% of current balance'
    'Stop: 20.00 USD in gold price'
    'Target: 4.00 USD in gold price'
    'Entry: T-10 seconds'
    'Exit: T+15 minutes'
    'Trade comment: AI news {event} {buy/sell} {confidence%}'
    'common.ini backup: ' + $commonBackup
)
[IO.File]::WriteAllText(
    $manifestPath,
    (($manifest -join $NewLine) + $NewLine),
    [Text.UTF8Encoding]::new($true)
)

Write-Stage 'Opening MT5 with the EA attached'
$runtimeHeartbeat = Join-Path ([string]$probeResult.commondata_path) 'Files\GoldNewsV9EA\runtime.tsv'
Remove-Item -LiteralPath $runtimeHeartbeat -Force -ErrorAction SilentlyContinue
$profileArgument = '/profile:"' + $ProfileName + '"'
Start-Process -FilePath $terminalPath -ArgumentList $profileArgument
$heartbeatDeadline = (Get-Date).AddSeconds(90)
do {
    Start-Sleep -Milliseconds 500
    $runningNow = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and
        $_.ExecutablePath -ieq $terminalPath
    })
    if ($runningNow.Count -eq 0) {
        Stop-Install 'Files were installed, but MT5 did not remain running.'
    }
    $heartbeatReady = Test-RuntimeHeartbeat $runtimeHeartbeat $symbol
} while (-not $heartbeatReady -and (Get-Date) -lt $heartbeatDeadline)
if (-not $heartbeatReady) {
    Stop-Install ("MT5 opened, but Gold News V9 did not publish a fresh runtime heartbeat for broker symbol '{0}'. Check the MT5 Experts journal." -f $symbol)
}
if (-not (Select-String -LiteralPath $chartPath -SimpleMatch '<expert>' -Quiet)) {
    Stop-Install 'MT5 opened, but the chart lost its EA attachment.'
}

Write-Host ''
Write-Host "SUCCESS: Gold News V9 is attached to $symbol M1." -ForegroundColor Green
Write-Host 'Live execution is enabled for both demo and real accounts.' -ForegroundColor Yellow
Write-Host "Local prediction server: $ApiBaseUrl"
Write-Host "Install manifest: $manifestPath"
