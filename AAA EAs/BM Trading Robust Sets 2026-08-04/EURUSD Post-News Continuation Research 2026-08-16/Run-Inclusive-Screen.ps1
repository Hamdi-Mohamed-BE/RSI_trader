[CmdletBinding()]
param([int]$TimeoutSeconds=180)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\eurusd-post-news-20260816\inclusive'
$reportRoot=Join-Path $testerRoot 'reports\eurusd-post-news-20260816\inclusive'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Inclusive Training Screen'
foreach($path in @($configRoot,$reportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}

function Set-InputValue([string]$Text,[string]$Name,[object]$Value){
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name not found."}
    return [regex]::Replace($Text,$pattern,($Name+'='+[string]$Value),1)
}

$base=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASELINE - EURUSD M1 - 0.50pct.set')
$cases=New-Object System.Collections.Generic.List[object]
foreach($delay in @(3,5)){
    foreach($body in @(0.35,0.50)){
        foreach($retrace in @(0.20,0.30,0.40)){
            $slug=('d{0}-b{1}-r{2}' -f $delay,[int]($body*100),[int]($retrace*100))
            $cases.Add([pscustomobject]@{slug=$slug;delay=$delay;body=$body;retrace=$retrace;rr=1.5})
        }
    }
}

foreach($case in $cases){
    $set=$base
    foreach($change in @{
        InpSignalDelayMinutes=$case.delay
        InpMinBodyFraction=$case.body
        InpRetraceFraction=$case.retrace
        InpMaxImpulseATR=50
        InpMaxStopATR=50
        InpEntryExpiryMinutes=30
        InpRewardRisk=$case.rr
        InpBreakEvenAtR=0
    }.GetEnumerator()){$set=Set-InputValue $set $change.Key $change.Value}
    $setName='PNC INCLUSIVE '+$case.slug+'.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($false))
    $configPath=Join-Path $configRoot ($case.slug+'.ini')
    $relativeReport='reports\eurusd-post-news-20260816\inclusive\'+$case.slug+'.htm'
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\EURUSD Post-News Continuation\EURUSD Post-News Continuation EA
ExpertParameters=$setName
Symbol=EURUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=0
FromDate=2021.08.11
ToDate=2024.12.31
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    $testerReport=Join-Path $reportRoot ($case.slug+'.htm')
    if(Test-Path -LiteralPath $testerReport){Remove-Item -LiteralPath $testerReport -Force}
    Write-Host ('START '+$case.slug)
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw ($case.slug+' timed out')}
    if(-not (Test-Path -LiteralPath $testerReport)){throw ($case.slug+' did not create a report')}
    Copy-Item -LiteralPath $testerReport -Destination (Join-Path $outputRoot ($case.slug+'.htm')) -Force
}
$cases | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed '+$cases.Count+' cases.')
