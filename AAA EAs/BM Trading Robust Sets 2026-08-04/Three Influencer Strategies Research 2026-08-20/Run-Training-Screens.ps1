[CmdletBinding()]
param(
    [string]$FromDate = '2020.01.01',
    [string]$ToDate = '2024.12.31',
    [int]$Model = 1,
    [int]$TimeoutSeconds = 600,
    [string]$CaseRegex = '',
    [string]$OutputFolder = 'Training',
    [string]$RunName = 'three-influencers-training-20260820'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\Three Influencer Strategies'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = $RunName
$configRoot = Join-Path $testerRoot ('backtest-configs\' + $runName)
$testerReportRoot = Join-Path $testerRoot ('reports\' + $runName)
$outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $OutputFolder)
$outputSetRoot = Join-Path $outputRoot 'Sets'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'
foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$outputSetRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
foreach ($name in @('Strategy 1 - NQ 10AM AMD FVG EA','Strategy 2 - Influencer 1M ORB EA','Strategy 3 - Asia Second Hour Sweep EA')) {
    Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\' + $name + '.ex5')) -Destination (Join-Path $expertRoot ($name + '.ex5')) -Force
}

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=[^\r\n]*$'
    if (-not [regex]::IsMatch($Text,$pattern)) { throw "Input $Name was not found." }
    $rendered = if ($Value -is [bool]) { ([string]$Value).ToLowerInvariant() } else { [string]$Value }
    return [regex]::Replace($Text,$pattern,($Name + '=' + $rendered),1)
}

$cases = New-Object System.Collections.Generic.List[object]
function Add-Case {
    param([string]$Strategy,[string]$Slug,[string]$Symbol,[string]$Expert,[string]$BaseSet,[hashtable]$Parameters)
    $cases.Add([pscustomobject]@{Strategy=$Strategy;Slug=$Slug;Symbol=$Symbol;Expert=$Expert;BaseSet=$BaseSet;Parameters=$Parameters})
}

$s1Base = 'BASE - Strategy 1 - NQ 10AM AMD FVG - USTEC M1 - 1pct.set'
foreach ($fvg in @($true,$false)) {
    foreach ($body in @(0.4,0.6,0.8)) {
        $slug = 's1-fvg' + [int]$fvg + '-body' + ([string]$body).Replace('.','') + '-rr20'
        Add-Case '10AM AMD FVG' $slug 'USTEC' 'Strategy 1 - NQ 10AM AMD FVG EA' $s1Base @{
            InpRequireFVG=$fvg; InpRequireSMT=$false; InpDisplacementBodyATR=$body; InpFallbackRewardRisk=2.0
        }
    }
}
foreach ($body in @(0.4,0.6)) {
    $slug = 's1-smt-fvg1-body' + ([string]$body).Replace('.','') + '-rr20'
    Add-Case '10AM AMD FVG' $slug 'USTEC' 'Strategy 1 - NQ 10AM AMD FVG EA' $s1Base @{
        InpRequireFVG=$true; InpRequireSMT=$true; InpDisplacementBodyATR=$body; InpFallbackRewardRisk=2.0
    }
}
foreach ($rr in @(1.5,2.5)) {
    $slug = 's1-fvg1-body06-rr' + ([string]$rr).Replace('.','')
    Add-Case '10AM AMD FVG' $slug 'USTEC' 'Strategy 1 - NQ 10AM AMD FVG EA' $s1Base @{
        InpRequireFVG=$true; InpRequireSMT=$false; InpDisplacementBodyATR=0.6; InpFallbackRewardRisk=$rr
    }
}

$s2Base = 'BASE - Strategy 2 - Influencer 1M ORB - USTEC M1 - 1pct.set'
foreach ($entry in @(0,1)) {
    foreach ($rv in @(0.8,1.1)) {
        foreach ($range in @(0.02,0.05)) {
            foreach ($rr in @(1.5,2.0)) {
                $slug = 's2-entry' + $entry + '-rv' + ([string]$rv).Replace('.','') + '-range' + ([string]$range).Replace('.','') + '-rr' + ([string]$rr).Replace('.','')
                Add-Case '09:30 1M ORB' $slug 'USTEC' 'Strategy 2 - Influencer 1M ORB EA' $s2Base @{
                    InpEntryMode=$entry; InpMinBreakoutRelativeVolume=$rv; InpMinRangeATR=$range; InpRewardRisk=$rr
                }
            }
        }
    }
}

$s3Base = 'BASE - Strategy 3 - Asia Second Hour Sweep - M1 - 1pct.set'
foreach ($symbol in @('XAUUSD','GBPJPY')) {
    foreach ($hour in @(0,1,2)) {
        foreach ($drive in @(15,20)) {
            foreach ($efficiency in @(0.50,0.65)) {
                $slug = 's3-' + $symbol.ToLowerInvariant() + '-h' + $hour + '-drive' + $drive + '-eff' + ([string]$efficiency).Replace('.','')
                Add-Case 'Asia Second Hour Sweep' $slug $symbol 'Strategy 3 - Asia Second Hour Sweep EA' $s3Base @{
                    InpSecondHourUTC=$hour; InpMinimumDriveMinutes=$drive; InpMinimumDriveEfficiency=$efficiency
                }
            }
        }
    }
}

if ($CaseRegex) {
    $selectedCases = New-Object System.Collections.Generic.List[object]
    foreach ($case in $cases) {
        if ($case.Slug -match $CaseRegex) { $selectedCases.Add($case) }
    }
    $cases = $selectedCases
    if ($cases.Count -eq 0) { throw "CaseRegex selected no cases: $CaseRegex" }
}

$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $setText = Get-Content -Raw -LiteralPath (Join-Path $researchRoot ('Sets\' + $case.BaseSet))
    foreach ($name in $case.Parameters.Keys) { $setText = Set-InputValue $setText $name $case.Parameters[$name] }
    $setName = 'TRAIN ' + $case.Slug + '.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $outputSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\' + $runName + '\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$($case.Expert)
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$Model
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0} / {1}' -f $case.Strategy,$case.Slug) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add([pscustomobject]@{Strategy=$case.Strategy;Slug=$case.Slug;Symbol=$case.Symbol;Parameters=$case.Parameters;Status='timeout';Report=$null})
        Write-Warning ('TIMEOUT ' + $case.Slug)
        continue
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        $manifest.Add([pscustomobject]@{Strategy=$case.Strategy;Slug=$case.Slug;Symbol=$case.Symbol;Parameters=$case.Parameters;Status='no-report';Report=$null})
        Write-Warning ('NO REPORT ' + $case.Slug)
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Strategy=$case.Strategy;Slug=$case.Slug;Symbol=$case.Symbol;Parameters=$case.Parameters;Status='complete';Report=(Join-Path $outputRoot ($case.Slug + '.htm'))})
    Write-Host ('DONE  ' + $case.Slug) -ForegroundColor Green
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed {0} of {1} screens.' -f (($manifest | Where-Object Status -eq 'complete').Count),$cases.Count) -ForegroundColor Green
