[CmdletBinding()]
param(
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
$ProfileName = 'GOLD NEWS V9 - XAU AUTO'
$ExpertFolderName = 'Gold News V9'
$ExpertBaseName = 'GoldNewsV9EA'
$ApiBaseUrl = 'http://127.0.0.1:8799'
$ApiPort = 8799
$Unicode = [Text.UnicodeEncoding]::new($false, $true)
$NewLine = [Environment]::NewLine

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
        return $health.status -eq 'ok' -and $null -ne $next.status
    } catch {
        return $false
    }
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

    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
    if (-not $uv) {
        Stop-Install 'uv is not available after dependency setup.'
    }
    $tmp = Join-Path $PackageRoot 'tmp'
    [void](New-Item -ItemType Directory -Path $tmp -Force)
    $stdout = Join-Path $tmp 'gold-news-v9-server.out.log'
    $stderr = Join-Path $tmp 'gold-news-v9-server.err.log'
    $arguments = @(
        'run',
        'uvicorn',
        'app:app',
        '--host',
        '127.0.0.1',
        '--port',
        [string]$ApiPort
    )
    Start-Process -FilePath $uv.Source -ArgumentList $arguments -WorkingDirectory $PackageRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        if (Test-EaApi) {
            Write-Host "Local prediction server started at $ApiBaseUrl"
            return
        }
    } while ((Get-Date) -lt $deadline)
    Stop-Install "The prediction server did not start. Check $stderr"
}

$mq5Source = Join-Path $PackageRoot "mt5\$ExpertBaseName.mq5"
$ex5Source = Join-Path $PackageRoot "mt5\$ExpertBaseName.ex5"
$presetSource = Join-Path $PackageRoot "mt5\$ExpertBaseName-Auto.set"
$probe = Join-Path $PackageRoot 'mt5_installer_probe.py'
foreach ($required in @($mq5Source, $presetSource, $probe)) {
    if (-not (Test-Path -LiteralPath $required)) {
        Stop-Install "Missing package file: $required"
    }
}

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
if ($running.Count -eq 0) {
    Stop-Install 'No active MT5 was found. Open and log into the target demo account, then run the BAT again.'
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
    & uv run --quiet python $probe --terminal $terminalPath 2>&1
)
if ($LASTEXITCODE -ne 0 -or $probeOutput.Count -eq 0) {
    Stop-Install ('MT5 probe failed: ' + ($probeOutput -join ' '))
}
try {
    $probeResult = ([string]$probeOutput[-1]) | ConvertFrom-Json
} catch {
    Stop-Install ('MT5 probe returned invalid data: ' + ($probeOutput -join ' '))
}
if ($probeResult.account_trade_mode -ne 'DEMO') {
    Stop-Install "The active account is not demo. Detected mode: $($probeResult.account_trade_mode)"
}

$dataRoot = [IO.Path]::GetFullPath([string]$probeResult.data_path)
$symbol = [string]$probeResult.symbol
Write-Host "Terminal: $terminalPath"
Write-Host "Data:     $dataRoot"
Write-Host "Server:   $($probeResult.server)"
Write-Host "Symbol:   $symbol"
Write-Host "API:      $ApiBaseUrl"
Write-Host 'Trading:  ENABLED, with the demo-account lock enabled' -ForegroundColor Yellow
Write-Host 'Comment:  AI news {event} {buy/sell} {confidence%}'

if ($ValidateOnly) {
    Write-Host ''
    Write-Host 'VALIDATION PASSED: no MT5 files or settings were changed.' -ForegroundColor Green
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
$chartsRoot = Join-Path $mql5Root 'Profiles\Charts'
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
if (Test-Path -LiteralPath $profileTargetFull) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileTargetFull -Destination $backup
    Write-Host "Previous profile backed up to: $backup"
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
[IO.File]::WriteAllText(
    (Join-Path $profileTargetFull 'chart01.chr'),
    $chartText.TrimStart(),
    $Unicode
)
[IO.File]::WriteAllText(
    (Join-Path $profileTargetFull 'order.wnd'),
    ('chart01.chr' + $NewLine),
    $Unicode
)

$commonIni = Join-Path $dataRoot 'config\common.ini'
if (-not (Test-Path -LiteralPath $commonIni)) {
    Stop-Install "MT5 common.ini was not found: $commonIni"
}
$commonBackup = $commonIni + '.gold-news-v9-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
Copy-Item -LiteralPath $commonIni -Destination $commonBackup -Force
Set-IniValue $commonIni 'Experts' 'Enabled' '1'
Set-IniValue $commonIni 'Experts' 'Account' '0'
Set-IniValue $commonIni 'Experts' 'Profile' '0'
Set-IniValue $commonIni 'Experts' 'Chart' '0'
Set-IniValue $commonIni 'Experts' 'WebRequest' '1'
Set-IniValue $commonIni 'Experts' 'WebRequestUrl' $ApiBaseUrl

$manifestPath = Join-Path $PackageRoot 'LAST_GOLD_NEWS_V9_INSTALL.txt'
$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $terminalPath
    'Data folder: ' + $dataRoot
    'Server: ' + [string]$probeResult.server
    'Account: ' + [string]$probeResult.login
    'Account mode: ' + [string]$probeResult.account_trade_mode
    'Profile: ' + $ProfileName
    'Symbol: ' + $symbol
    'Timeframe: M1'
    'EA: ' + $ExpertBaseName + '.ex5'
    'API: ' + $ApiBaseUrl
    'Events: NFP, CPI, FOMC'
    'Trading enabled: true'
    'Demo-account lock: true'
    'Risk: 1% of current balance'
    'Stop: 4.00 USD in gold price'
    'Entry: T-5 seconds'
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
$profileArgument = '/profile:"' + $ProfileName + '"'
Start-Process -FilePath $terminalPath -ArgumentList $profileArgument
Start-Sleep -Seconds 12
$runningNow = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and
    $_.ExecutablePath -ieq $terminalPath
})
if ($runningNow.Count -eq 0) {
    Stop-Install 'Files were installed, but MT5 did not remain running.'
}
$chartPath = Join-Path $profileTargetFull 'chart01.chr'
if (-not (Select-String -LiteralPath $chartPath -SimpleMatch '<expert>' -Quiet)) {
    Stop-Install 'MT5 opened, but the chart lost its EA attachment.'
}

Write-Host ''
Write-Host "SUCCESS: Gold News V9 is attached to $symbol M1." -ForegroundColor Green
Write-Host 'Live execution is enabled and locked to demo accounts.' -ForegroundColor Yellow
Write-Host "Local prediction server: $ApiBaseUrl"
Write-Host "Install manifest: $manifestPath"
