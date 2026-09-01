[CmdletBinding()]
param(
    [ValidateSet('Development','Locked','LastYear')]
    [string]$Stage = 'Development',
    [string[]]$VariantIds = @(),
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\US100 Momentum Continuation 20260831'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runSlug=('us100-momentum-continuation-'+$Stage.ToLowerInvariant())
$configRoot=Join-Path $testerRoot ('backtest-configs\'+$runSlug)
$testerReportRoot=Join-Path $testerRoot ('reports\'+$runSlug)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$Stage)
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\US100 Momentum Continuation Research EA.ex5') -Destination (Join-Path $expertRoot 'US100 Momentum Continuation Research EA.ex5') -Force

function Set-OrAddInput {
    param([string]$Text,[string]$Name,[object]$Value)
    $rendered=if($Value -is [bool]){$Value.ToString().ToLowerInvariant()}else{[string]$Value}
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if([regex]::IsMatch($Text,$pattern)){
        return [regex]::Replace($Text,$pattern,($Name+'='+$rendered),1)
    }
    return $Text.TrimEnd()+[Environment]::NewLine+$Name+'='+$rendered+[Environment]::NewLine
}

$variants=@(
    [pscustomobject]@{Id='baseline-active';Mode=0;Gate=$false;Long=$true;Short=$true;Mom=.50;Range=.75;Slope=1;SL=4.0;Trail=6.0;Start=1.0;Hold=120;Risk=1.0;Close=$true},
    [pscustomobject]@{Id='ny-long-only';Mode=0;Gate=$false;Long=$true;Short=$false;Mom=.50;Range=.75;Slope=1;SL=4.0;Trail=6.0;Start=1.0;Hold=120;Risk=1.0;Close=$true},
    [pscustomobject]@{Id='ny-gate-loose';Mode=0;Gate=$true;Long=$true;Short=$false;Mom=.25;Range=.65;Slope=1;SL=4.0;Trail=6.0;Start=1.0;Hold=120;Risk=1.0;Close=$true},
    [pscustomobject]@{Id='ny-gate-exact';Mode=0;Gate=$true;Long=$true;Short=$false;Mom=.50;Range=.75;Slope=1;SL=4.0;Trail=6.0;Start=1.0;Hold=120;Risk=1.0;Close=$true},
    [pscustomobject]@{Id='ny-gate-strict';Mode=0;Gate=$true;Long=$true;Short=$false;Mom=1.00;Range=.85;Slope=5;SL=4.0;Trail=6.0;Start=1.0;Hold=120;Risk=1.0;Close=$true},
    [pscustomobject]@{Id='h1-exact';Mode=1;Gate=$false;Long=$true;Short=$false;Mom=.50;Range=.75;Slope=1;SL=2.5;Trail=2.5;Start=0.0;Hold=120;Risk=1.0;Close=$false},
    [pscustomobject]@{Id='h1-tight';Mode=1;Gate=$false;Long=$true;Short=$false;Mom=.50;Range=.75;Slope=1;SL=2.0;Trail=2.0;Start=0.0;Hold=120;Risk=1.0;Close=$false},
    [pscustomobject]@{Id='h1-wide';Mode=1;Gate=$false;Long=$true;Short=$false;Mom=.50;Range=.75;Slope=1;SL=3.0;Trail=3.0;Start=0.0;Hold=120;Risk=1.0;Close=$false}
)
if($VariantIds.Count -gt 0){
    $variants=@($variants | Where-Object {$VariantIds -contains $_.Id})
    if($variants.Count -ne $VariantIds.Count){throw 'One or more requested VariantIds do not exist.'}
}

$period=if($Stage -eq 'Development'){@{From='2019.07.16';To='2024.12.31';Model=1}}
        elseif($Stage -eq 'Locked'){@{From='2025.01.01';To='2026.08.27';Model=0}}
        else{@{From='2025.08.28';To='2026.08.27';Model=0}}
$baseSet=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE ACTIVE - USTEC M5 - 1pct.set')
$manifest=New-Object System.Collections.Generic.List[object]

foreach($variant in $variants){
    $setText=$baseSet
    $inputs=[ordered]@{
        InpMomentumModel=$variant.Mode
        InpSignalTimeframe=5
        InpEMAPeriod=12
        InpAllowLong=$variant.Long
        InpAllowShort=$variant.Short
        InpUseH1ContinuationGate=$variant.Gate
        InpContinuationTimeframe=16385
        InpMomentumLookback=24
        InpMinimumMomentumATR=$variant.Mom
        InpRangeLookback=48
        InpMinimumRangePosition=$variant.Range
        InpTrendEMAPeriod=100
        InpTrendSlopeBars=$variant.Slope
        InpMaximumHoldingBars=$variant.Hold
        InpATRPeriod=14
        InpInitialStopATR=$variant.SL
        InpTrailingATR=$variant.Trail
        InpTrailStartR=$variant.Start
        InpCloseAtSessionEnd=$variant.Close
        InpRiskPercent=$variant.Risk
        InpMaximumSpreadATR=0
        InpMagic=(863100+[array]::IndexOf($variants,$variant))
    }
    foreach($item in $inputs.GetEnumerator()){$setText=Set-OrAddInput $setText $item.Key $item.Value}
    $setName=('US100 MOMENTUM {0} {1}.set' -f $Stage.ToUpperInvariant(),$variant.Id)
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path (Join-Path $researchRoot 'Sets') $setName),$setText,[Text.UTF8Encoding]::new($false))

    $configPath=Join-Path $configRoot ($variant.Id+'.ini')
    $reportPath=Join-Path $testerReportRoot ($variant.Id+'.htm')
    $relativeReport=('reports\{0}\{1}.htm' -f $runSlug,$variant.Id)
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\US100 Momentum Continuation Research EA
ExpertParameters=$setName
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($period.Model)
ExecutionMode=1
Optimization=0
FromDate=$($period.From)
ToDate=$($period.To)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($variant.Id+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0} {1} to {2}' -f $variant.Id,$period.From,$period.To) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $($variant.Id)"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "NO REPORT $($variant.Id)"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($variant.Id+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Variant=$variant;Stage=$Stage;From=$period.From;To=$period.To;Report=(Join-Path $outputRoot ($variant.Id+'.htm'))})
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
& (Get-Command python.exe -ErrorAction Stop).Source (Join-Path $researchRoot 'Analyze-Reports.py') $outputRoot (Join-Path $researchRoot ($Stage.ToLowerInvariant()+'-results'))
if($LASTEXITCODE -ne 0){throw 'Report analysis failed.'}
Write-Host ('Completed '+$Stage+' research tests.') -ForegroundColor Green
