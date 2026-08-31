[CmdletBinding()]
param(
    [ValidateSet('development','locked','all')][string]$Phase='all',
    [string[]]$OnlyCases=@(),
    [int]$TimeoutSeconds=1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$compiled=Join-Path $researchRoot 'EA\LTA POC First Retest EA.ex5'
$expertFolder='AAA Research\LTA POC First Retest 20260831'
$expertName='LTA POC First Retest EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\lta-poc-improvement-20260831'
$terminalReportRoot=Join-Path $testerRoot 'reports\lta-poc-improvement-20260831'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$savedSetRoot=Join-Path $researchRoot 'Sets'
$baseSet=Join-Path $packageRoot 'LTA volume profile\Best Settings\RETEST PASSED 2026-08-07 - LTA - XAUUSD M15 - 1pct.set'
foreach($path in @($expertRoot,$setRoot,$configRoot,$terminalReportRoot,$outputRoot,$savedSetRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\SafeRegimeFilter.mqh') -Destination (Join-Path $expertRoot 'SafeRegimeFilter.mqh') -Force

$cases=@(
    [pscustomobject]@{Slug='baseline';Transcript='false';Edge='true';First='true';Departure='1.0';Barrier='false';RR='3.0';Supply='true'},
    [pscustomobject]@{Slug='edge-rr3';Transcript='true';Edge='true';First='true';Departure='1.0';Barrier='false';RR='3.0';Supply='false'},
    [pscustomobject]@{Slug='edge-rr2';Transcript='true';Edge='true';First='true';Departure='1.0';Barrier='false';RR='2.0';Supply='false'},
    [pscustomobject]@{Slug='center-rr2';Transcript='true';Edge='false';First='true';Departure='1.0';Barrier='false';RR='2.0';Supply='false'},
    [pscustomobject]@{Slug='edge-barrier';Transcript='true';Edge='true';First='true';Departure='1.0';Barrier='true';RR='3.0';Supply='false'}
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
foreach($case in $cases){
    if($OnlyCases.Count -gt 0 -and $case.Slug -notin $OnlyCases){continue}
    foreach($window in $phases){
        if($Phase -ne 'all' -and $window.Name -ne $Phase){continue}
        $sequence++
        $id="xauusd--$($case.Slug)--$($window.Name)"
        $setName="LTA-POC-$id.set"
        $set=Get-Content -LiteralPath $baseSet -Raw
        $set=Set-Input $set 'InpUseTranscriptPOCMode' $case.Transcript
        $set=Set-Input $set 'InpUseHeavyVolumeZoneEdge' $case.Edge
        $set=Set-Input $set 'InpRequireFirstRetest' $case.First
        $set=Set-Input $set 'InpMinimumDepartureATR' $case.Departure
        $set=Set-Input $set 'InpRetestSignalBars' '5'
        $set=Set-Input $set 'InpUseProfileBarrierTarget' $case.Barrier
        $set=Set-Input $set 'InpMinimumBarrierRR' '1.0'
        $set=Set-Input $set 'InpHeavyZoneVolumeFraction' '0.65'
        $set=Set-Input $set 'InpRewardRisk' $case.RR
        $set=Set-Input $set 'InpUseSupplyDemandZones' $case.Supply
        $set=Set-Input $set 'InpUseSwingProfile' 'false'
        $set=Set-Input $set 'InpUsePreviousDayProfile' 'true'
        $set=Set-Input $set 'InpUsePreviousWeekProfile' 'true'
        $set=Set-Input $set 'InpUseMarkovRegimeFilter' 'false'
        $set=Set-Input $set 'InpMagicNumber' ([string](7268000+$sequence))
        [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText((Join-Path $savedSetRoot ($id+'.set')),$set,[Text.UTF8Encoding]::new($false))

        $configPath=Join-Path $configRoot ($id+'.ini')
        $reportRelative='reports\lta-poc-improvement-20260831\'+$id+'.htm'
        $reportPath=Join-Path $terminalReportRoot ($id+'.htm')
        $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=XAUUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$($window.From)
ToDate=$($window.To)
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
        [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
        Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ("START {0} {1}" -f $case.Slug,$window.Name) -ForegroundColor Cyan
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
& $python (Join-Path $researchRoot 'Analyze-POC.py')
if($LASTEXITCODE -ne 0){throw 'POC analysis failed'}
