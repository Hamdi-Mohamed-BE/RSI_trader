[CmdletBinding()]
param(
    [string]$DevelopmentFrom='2024.08.29',
    [string]$DevelopmentTo='2025.08.28',
    [string]$LockedFrom='2025.08.29',
    [string]$LockedTo='2026.08.28',
    [int]$TimeoutSeconds=1200,
    [switch]$StocksOnly,
    [switch]$IndicesOnly,
    [string[]]$OnlySymbols=@()
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$sourceRoot=Join-Path $researchRoot 'EA'
$compiledSource=Join-Path $sourceRoot 'Cross-Market Overnight Negative Day EA.ex5'
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\Overnight Cross Market'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\overnight-cross-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\overnight-cross-20260830'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$developmentOutput=Join-Path $outputRoot 'Development 2024-2025'
$lockedOutput=Join-Path $outputRoot 'Locked 2025-2026'
$setOutput=Join-Path $researchRoot 'Sets'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$lockedOutput,$setOutput)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
if(-not $StocksOnly -and -not $IndicesOnly -and $OnlySymbols.Count -eq 0){
    foreach($path in @($developmentOutput,$lockedOutput)){
        Get-ChildItem -LiteralPath $path -File -ErrorAction SilentlyContinue | Remove-Item -Force
    }
}
if(-not (Test-Path -LiteralPath $compiledSource)){throw "Missing overnight EA: $compiledSource"}
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'Cross-Market Overnight Negative Day EA.ex5') -Force

$symbols=@(
    [pscustomobject]@{Symbol='USTEC';Slug='ustec';Group='Index control';CloseHour=15;CloseMinute=59},
    [pscustomobject]@{Symbol='US500';Slug='us500';Group='Index';CloseHour=15;CloseMinute=59},
    [pscustomobject]@{Symbol='US30';Slug='us30';Group='Index';CloseHour=15;CloseMinute=59},
    [pscustomobject]@{Symbol='NVDA';Slug='nvda';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='TSLA';Slug='tsla';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='AAPL';Slug='aapl';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='MSFT';Slug='msft';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='AMZN';Slug='amzn';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='GOOGL';Slug='googl';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='META';Slug='meta';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='AVGO';Slug='avgo';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='AMD';Slug='amd';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='INTC';Slug='intc';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='JPM';Slug='jpm';Group='Stock';CloseHour=15;CloseMinute=29},
    [pscustomobject]@{Symbol='NFLX';Slug='nflx';Group='Stock';CloseHour=15;CloseMinute=29}
)
if($StocksOnly -and $IndicesOnly){throw 'Choose either -StocksOnly or -IndicesOnly, not both.'}
if($StocksOnly){$symbols=@($symbols | Where-Object Group -eq 'Stock')}
if($IndicesOnly){$symbols=@($symbols | Where-Object Group -ne 'Stock')}
if($OnlySymbols.Count -gt 0){$symbols=@($symbols | Where-Object Symbol -in $OnlySymbols)}
if($symbols.Count -eq 0){throw 'No matching symbols were selected.'}

function Write-SetFile([string]$Path,[long]$Magic,[int]$SessionProfile){
    $text=@"
InpEnableTrading=true
InpNegativeDayDefinition=0
InpNegativeDayThresholdPercent=0
InpAllowFridayEntry=true
InpCashOpenHour=9
InpCashOpenMinute=30
InpCashCloseHour=16
InpCashCloseMinute=0
InpExitHour=9
InpExitMinute=29
InpEntryWindowMinutes=10
InpExitWindowMinutes=31
InpMinimumCashSessionBars=300
InpBrokerSessionProfile=$SessionProfile
InpRiskPercent=1
InpEmergencyStopPercent=2
InpMaxSpreadPoints=0
InpMaxDeviationPoints=30
InpMagic=$Magic
InpUseAutomaticLiveServerOffset=true
InpTesterServerUTCOffsetHours=0
InpManualLiveServerUTCOffsetHours=0
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}
function Run-Case([string]$Phase,[object]$SymbolCase,[string]$From,[string]$To,[string]$Destination,[int]$Sequence){
    $caseId="$($SymbolCase.Slug)--$Phase"
    $setName="Overnight-$caseId.set"
    $setPath=Join-Path $testerSetRoot $setName
    $sessionProfile=if($SymbolCase.Group -eq 'Stock'){2}else{1}
    Write-SetFile $setPath (86600000+$Sequence) $sessionProfile
    if($Phase -eq 'locked'){
        Copy-Item -LiteralPath $setPath -Destination (Join-Path $setOutput "$($SymbolCase.Symbol) - Nasdaq Overnight transferred.set") -Force
    }
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\overnight-cross-20260830\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Cross-Market Overnight Negative Day EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$From
ToDate=$To
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1} | {2} to {3}" -f $Phase,$SymbolCase.Symbol,$From,$To) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $Destination -Force
}

$sequence=0
foreach($symbolCase in $symbols){
    $sequence++
    Run-Case 'development' $symbolCase $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
}
foreach($symbolCase in $symbols){
    $sequence++
    Run-Case 'locked' $symbolCase $LockedFrom $LockedTo $lockedOutput $sequence
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-Overnight-CrossMarket.py') --development $developmentOutput --locked $lockedOutput --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'Overnight cross-market report failed'}
Write-Host 'Completed overnight cross-market MT5 audit.' -ForegroundColor Green
