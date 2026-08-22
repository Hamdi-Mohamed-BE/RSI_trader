[CmdletBinding()]
param(
    [string]$FromDate = '2020.01.01',
    [string]$ToDate = '2024.12.31',
    [int]$Model = 1,
    [int]$TimeoutSeconds = 600,
    [string]$CaseRegex = '',
    [string]$OutputFolder = 'Training',
    [string]$RunName = 'gemini-bos-training-20260820'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$validationRoot = $PSScriptRoot
$geminiRoot = Split-Path -Parent $validationRoot
$packageRoot = Split-Path -Parent $geminiRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\Gemini BOS Retest'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot ('backtest-configs\' + $RunName)
$testerReportRoot = Join-Path $testerRoot ('reports\' + $RunName)
$outputRoot = Join-Path $validationRoot ('Reports\' + $OutputFolder)
$outputSetRoot = Join-Path $outputRoot 'Sets'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$outputSetRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
$expertName = 'Breakout Retest Rejection (gemini)'
Copy-Item -LiteralPath (Join-Path $geminiRoot ($expertName + '.ex5')) -Destination (Join-Path $expertRoot ($expertName + '.ex5')) -Force

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=[^\r\n]*$'
    if (-not [regex]::IsMatch($Text,$pattern)) { throw "Input $Name was not found." }
    $rendered = if ($Value -is [bool]) { ([string]$Value).ToLowerInvariant() } else { [string]$Value }
    return [regex]::Replace($Text,$pattern,($Name + '=' + $rendered),1)
}

$cases = New-Object System.Collections.Generic.List[object]
function Add-Case {
    param([string]$Slug,[hashtable]$Parameters)
    $cases.Add([pscustomobject]@{Strategy='Gemini BOS Retest';Slug=$Slug;Symbol='XAUUSD';Expert=$expertName;Parameters=$Parameters})
}

Add-Case 'original-default-fixed001' @{
    InpFixedLot=0.01; InpSwingLeft=5; InpSwingRight=2; InpRetestTolerance=150;
    InpPinBarWickRatio=1.0; InpMarubozuBodyRatio=0.80; InpMaxCandleATRMult=2.5;
    InpAtrPeriod=21; InpAtrMultiplier=0.20; InpRiskRewardRatio=2.0
}

foreach ($left in @(3,5,8)) {
    foreach ($tolerance in @(50,150,300)) {
        foreach ($pin in @(0.40,0.55)) {
            foreach ($rr in @(1.5,2.0)) {
                foreach ($atrPeriod in @(14,21)) {
                    $slug = 'risk1-left' + $left + '-tol' + $tolerance + '-pin' + ([string]$pin).Replace('.','') + '-rr' + ([string]$rr).Replace('.','') + '-atr' + $atrPeriod
                    Add-Case $slug @{
                        InpFixedLot=0.0; InpSwingLeft=$left; InpSwingRight=2; InpRetestTolerance=$tolerance;
                        InpPinBarWickRatio=$pin; InpMarubozuBodyRatio=0.80; InpMaxCandleATRMult=2.0;
                        InpAtrPeriod=$atrPeriod; InpAtrMultiplier=0.20; InpRiskRewardRatio=$rr
                    }
                }
            }
        }
    }
}

if ($CaseRegex) {
    $selected = New-Object System.Collections.Generic.List[object]
    foreach ($case in $cases) { if ($case.Slug -match $CaseRegex) { $selected.Add($case) } }
    $cases = $selected
    if ($cases.Count -eq 0) { throw "CaseRegex selected no cases: $CaseRegex" }
}

$baseSet = Join-Path $validationRoot 'Sets\BASE - Gemini BOS Retest - XAUUSD H1 - 1pct.set'
$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $setText = Get-Content -Raw -LiteralPath $baseSet
    foreach ($name in $case.Parameters.Keys) { $setText = Set-InputValue $setText $name $case.Parameters[$name] }
    $setName = 'GEMINI ' + $case.Slug + '.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $outputSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\' + $RunName + '\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$($case.Expert)
ExpertParameters=$setName
Symbol=XAUUSD
Period=H1
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
    Write-Host ('START {0}' -f $case.Slug) -ForegroundColor Cyan
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
    Write-Host ('DONE  {0}' -f $case.Slug) -ForegroundColor Green
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed {0} of {1} cases.' -f (($manifest | Where-Object Status -eq 'complete').Count),$cases.Count) -ForegroundColor Green
