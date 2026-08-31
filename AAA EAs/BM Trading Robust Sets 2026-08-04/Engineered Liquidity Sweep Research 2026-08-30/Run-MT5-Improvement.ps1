[CmdletBinding()]
param(
    [int]$TimeoutSeconds=1200,
    [string[]]$OnlyCases=@(),
    [string[]]$OnlySymbols=@()
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$compiled=Join-Path $researchRoot 'EA\Engineered Liquidity Sweep EA.ex5'
$expertFolder='AAA Research\Engineered Liquidity Improvement'
$expertName='Engineered Liquidity Sweep EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\engineered-liquidity-improvement-20260831'
$reportRoot=Join-Path $testerRoot 'reports\engineered-liquidity-improvement-20260831'
$outputRoot=Join-Path $researchRoot 'Improvement Reports'
foreach($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

$markets=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd';BaseSet=Join-Path $researchRoot 'Sets\XAUUSD - h1-d1-reclaim - locked.set'},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd';BaseSet=Join-Path $researchRoot 'Sets\BTCUSD - m30-h4-reclaim - locked.set'}
)
$cases=@(
    [pscustomobject]@{Slug='base';Safe='false';Displacement='false';MinimumRR='1.5';TradesPerDay='2'},
    [pscustomobject]@{Slug='safe-base';Safe='true';Displacement='false';MinimumRR='1.5';TradesPerDay='2'},
    [pscustomobject]@{Slug='safe-rr2';Safe='true';Displacement='false';MinimumRR='2.0';TradesPerDay='2'},
    [pscustomobject]@{Slug='safe-displacement';Safe='true';Displacement='true';MinimumRR='1.5';TradesPerDay='2'},
    [pscustomobject]@{Slug='displacement';Safe='false';Displacement='true';MinimumRR='1.5';TradesPerDay='2'},
    [pscustomobject]@{Slug='rr2';Safe='false';Displacement='false';MinimumRR='2.0';TradesPerDay='2'},
    [pscustomobject]@{Slug='one-trade';Safe='false';Displacement='false';MinimumRR='1.5';TradesPerDay='1'},
    [pscustomobject]@{Slug='safe-one-trade';Safe='true';Displacement='false';MinimumRR='1.5';TradesPerDay='1'}
)
$phases=@(
    [pscustomobject]@{Name='development';From='2024.08.29';To='2025.08.28'},
    [pscustomobject]@{Name='locked';From='2025.08.29';To='2026.08.28'}
)

function Set-Input([string]$Text,[string]$Name,[string]$Value){
    $pattern='(?m)^'+[regex]::Escape($Name)+'=.*$'
    if([regex]::IsMatch($Text,$pattern)){return [regex]::Replace($Text,$pattern,$Name+'='+$Value)}
    return $Text.TrimEnd()+"`r`n$Name=$Value`r`n"
}

$sequence=0
foreach($market in $markets){
    if($OnlySymbols.Count -gt 0 -and $market.Symbol -notin $OnlySymbols){continue}
    $base=Get-Content -LiteralPath $market.BaseSet -Raw
    foreach($case in $cases){
        if($OnlyCases.Count -gt 0 -and $case.Slug -notin $OnlyCases){continue}
        foreach($phase in $phases){
            $sequence++
            $id="$($market.Slug)--$($case.Slug)--$($phase.Name)"
            $setName="ELS-IMPROVE-$id.set"
            $set=Set-Input $base 'InpUseMarkovRegimeFilter' $case.Safe
            $set=Set-Input $set 'InpRequireDisplacementClose' $case.Displacement
            $set=Set-Input $set 'InpMinimumRewardRisk' $case.MinimumRR
            $set=Set-Input $set 'InpMaximumTradesPerDay' $case.TradesPerDay
            $set=Set-Input $set 'InpRiskMode' '0'
            $set=Set-Input $set 'InpRiskPercent' '1'
            $set=Set-Input $set 'InpMagic' ([string](86839000+$sequence))
            [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($false))
            $configPath=Join-Path $configRoot ($id+'.ini')
            $reportRelative='reports\engineered-liquidity-improvement-20260831\'+$id+'.htm'
            $reportPath=Join-Path $reportRoot ($id+'.htm')
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
FromDate=$($phase.From)
ToDate=$($phase.To)
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
            [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
            Get-ChildItem -LiteralPath $reportRoot -Filter ($id+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
            Write-Host ("START {0} {1} {2}" -f $market.Symbol,$case.Slug,$phase.Name) -ForegroundColor Cyan
            $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
            try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
            catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $id"}
            if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
            Get-ChildItem -LiteralPath $reportRoot -Filter ($id+'*') | Copy-Item -Destination $outputRoot -Force
        }
    }
}

$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-Improvement.py')
if($LASTEXITCODE -ne 0){throw 'Improvement analysis failed'}
Write-Host 'Improvement audit complete.' -ForegroundColor Green
