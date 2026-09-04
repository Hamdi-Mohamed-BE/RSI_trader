[CmdletBinding()]
param(
    [ValidateSet('development','locked','full')][string]$Phase='development',
    [int]$TimeoutSeconds=1800,
    [string[]]$OnlyCases=@()
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$compiled=Join-Path $researchRoot 'EA\LTA POC First Retest EA.ex5'
$expertFolder='AAA Research\LTA Hybrid Confirmation 20260904'
$expertName='LTA POC First Retest EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\lta-hybrid-'+$Phase)
$terminalReportRoot=Join-Path $testerRoot ('reports\lta-hybrid-'+$Phase)
$outputRoot=Join-Path $researchRoot ('Hybrid Backtest Reports\'+$Phase)
$savedSetRoot=Join-Path $researchRoot ('Hybrid Sets\'+$Phase)
$baseSet=Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\01 LTA Volume Profile - CURRENT - ALL DAY.set'
foreach($path in @($expertRoot,$setRoot,$configRoot,$terminalReportRoot,$outputRoot,$savedSetRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\SafeRegimeFilter.mqh') -Destination (Join-Path $expertRoot 'SafeRegimeFilter.mqh') -Force

function Set-Input([string]$Text,[string]$Name,[string]$Value){
    $pattern='(?m)^'+[regex]::Escape($Name)+'=.*$'
    if([regex]::IsMatch($Text,$pattern)){return [regex]::Replace($Text,$pattern,$Name+'='+$Value)}
    return $Text.TrimEnd()+"`r`n$Name=$Value`r`n"
}

$cases=[Collections.Generic.List[object]]::new()
[void]$cases.Add([pscustomobject]@{Slug='baseline';Hybrid='false';Heavy='0.65';Departure='1.00';Bars='5'})
if($Phase -eq 'development'){
    foreach($heavy in @('0.50','0.65','0.80')){
        foreach($departure in @('0.50','1.00','1.50')){
            foreach($bars in @('3','8')){
                $slug='hybrid-h'+($heavy -replace '\.','')+'-d'+($departure -replace '\.','')+'-b'+$bars
                [void]$cases.Add([pscustomobject]@{Slug=$slug;Hybrid='true';Heavy=$heavy;Departure=$departure;Bars=$bars})
            }
        }
    }
} else {
    $selectionPath=Join-Path $researchRoot 'HYBRID DEVELOPMENT SELECTION.json'
    if(-not (Test-Path -LiteralPath $selectionPath)){throw "Run development and Analyze-LTA-Hybrid.py first: $selectionPath"}
    $selected=Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
    foreach($row in $selected.selected){
        [void]$cases.Add([pscustomobject]@{Slug=[string]$row.case;Hybrid='true';Heavy=[string]$row.heavy;Departure=[string]$row.departure;Bars=[string]$row.bars})
    }
}
if($OnlyCases.Count -gt 0){$cases=[Collections.Generic.List[object]]@($cases | Where-Object {$_.Slug -in $OnlyCases})}
if($cases.Count -eq 0){throw 'No hybrid cases selected.'}

$window=switch($Phase){
    'development'{[pscustomobject]@{From='2024.08.29';To='2025.08.28'}}
    'locked'{[pscustomobject]@{From='2025.08.29';To='2026.08.28'}}
    'full'{[pscustomobject]@{From='2024.08.29';To='2026.08.28'}}
}
$sequence=0
foreach($case in $cases){
    $sequence++
    $id="xauusd--$($case.Slug)--$Phase"
    $setName="LTA-Hybrid-$id.set"
    $set=Get-Content -LiteralPath $baseSet -Raw
    $set=Set-Input $set 'InpUseTranscriptPOCMode' 'false'
    $set=Set-Input $set 'InpRequireTranscriptPOCConfirmation' $case.Hybrid
    $set=Set-Input $set 'InpUseHeavyVolumeZoneEdge' 'true'
    $set=Set-Input $set 'InpRequireFirstRetest' 'true'
    $set=Set-Input $set 'InpHeavyZoneVolumeFraction' $case.Heavy
    $set=Set-Input $set 'InpMinimumDepartureATR' $case.Departure
    $set=Set-Input $set 'InpRetestSignalBars' $case.Bars
    $set=Set-Input $set 'InpUseProfileBarrierTarget' 'false'
    $set=Set-Input $set 'InpUseMarkovRegimeFilter' 'false'
    $set=Set-Input $set 'InpMagicNumber' ([string](7269000+$sequence))
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetRoot ($id+'.set')),$set,[Text.UTF8Encoding]::new($false))

    $configPath=Join-Path $configRoot ($id+'.ini')
    $reportRelative='reports\lta-hybrid-'+$Phase+'\'+$id+'.htm'
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
    Write-Host ("START {0} {1}" -f $case.Slug,$Phase) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $id"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
    Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id+'*') | Copy-Item -Destination $outputRoot -Force
}
Write-Host "Completed $sequence native MT5 Every Tick $Phase tests." -ForegroundColor Green
