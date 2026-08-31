[CmdletBinding()]
param([int]$TimeoutSeconds=1800)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$compiled=Join-Path $researchRoot 'EA\Statistical Triple Print EA.ex5'
$expertFolder='AAA Research\Statistical Triple Print 20260831'
$expertName='Statistical Triple Print EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\statistical-triple-print-20260831'
$terminalReportRoot=Join-Path $testerRoot 'reports\statistical-triple-print-20260831'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$savedSetRoot=Join-Path $researchRoot 'Sets'
foreach($path in @($expertRoot,$setRoot,$configRoot,$terminalReportRoot,$outputRoot,$savedSetRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

$markets=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd';Magic=86831100},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd';Magic=86831200},
    [pscustomobject]@{Symbol='US30';Slug='us30';Magic=86831300},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec';Magic=86831400}
)
$profiles=@(
    [pscustomobject]@{Name='normal';Profile=0;RR='2.0';Risk='1.0';MaxTrades=2;MagicOffset=1},
    [pscustomobject]@{Name='prop';Profile=1;RR='1.5';Risk='0.35';MaxTrades=1;MagicOffset=2}
)

function New-SetText($market,$profile){
    $magic=$market.Magic+$profile.MagicOffset
    return @"
InpSignalTimeframe=15
InpStructureLookback=24
InpPullbackLookback=14
InpRequiredValidCandles=3
InpATRPeriod=14
InpMinimumBreakoutATR=0.80
InpStopBufferATR=0.15
InpMinimumWickGapATR=0.03
InpRewardRisk=$($profile.RR)
InpMaximumHoldingBars=48
InpUseTradingWindow=true
InpStartHour=6
InpEndHour=22
InpCloseFriday=true
InpFridayCloseHour=20
InpProfile=$($profile.Profile)
InpNormalRiskPercent=1.0
InpPropRiskPercent=$($profile.Risk)
InpNormalMaximumTradesPerDay=2
InpPropMaximumTradesPerDay=$($profile.MaxTrades)
InpPropDailyLossLimitPercent=1.0
InpPropOverallDrawdownLimitPercent=5.0
InpPropCloseAtEndHour=true
InpAllowLong=true
InpAllowShort=true
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=80
InpMagic=$magic
"@
}

$sequence=0
foreach($market in $markets){
    foreach($profile in $profiles){
        $sequence++
        $id="$($market.Slug)--$($profile.Name)--last-year"
        $setName="STP-$id.set"
        $setText=New-SetText $market $profile
        $testerSet=Join-Path $setRoot $setName
        $savedSet=Join-Path $savedSetRoot ($market.Symbol+' - '+$profile.Name+'.set')
        [IO.File]::WriteAllText($testerSet,$setText,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText($savedSet,$setText,[Text.UTF8Encoding]::new($false))

        $configPath=Join-Path $configRoot ($id+'.ini')
        $reportRelative='reports\statistical-triple-print-20260831\'+$id+'.htm'
        $reportPath=Join-Path $terminalReportRoot ($id+'.htm')
        $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$($market.Symbol)
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=2025.08.29
ToDate=2026.08.28
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
        [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
        Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ("START {0} {1}" -f $market.Symbol,$profile.Name) -ForegroundColor Cyan
        $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw "MT5 timed out: $id"
        }
        if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
        Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id+'*') | Copy-Item -Destination $outputRoot -Force
    }
}

$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-Results.py')
if($LASTEXITCODE -ne 0){throw 'Result analysis failed'}
Write-Host 'Statistical Triple Print audit complete.' -ForegroundColor Green
