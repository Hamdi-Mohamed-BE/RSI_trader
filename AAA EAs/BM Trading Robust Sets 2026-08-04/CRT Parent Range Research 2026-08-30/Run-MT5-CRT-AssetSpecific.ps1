[CmdletBinding()]
param([string]$From='2025.08.29',[string]$To='2026.08.28',[int]$TimeoutSeconds=1200)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\CRT Parent Range'
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\crt-parent-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\crt-parent-20260830'
$destination=Join-Path $researchRoot 'Backtest Reports\Asset-Specific Locked 2025-2026'
[void](New-Item -ItemType Directory -Path $destination -Force)
Get-ChildItem -LiteralPath $destination -File -ErrorAction SilentlyContinue | Remove-Item -Force
$cases=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd';Variant='h4-core'},
    [pscustomobject]@{Symbol='USDJPY';Slug='usdjpy';Variant='h4-core'}
)
foreach($case in $cases){
    $caseId="$($case.Slug)--$($case.Variant)--assetlocked"
    $setName="CRT-$($case.Slug)--$($case.Variant)--development.set"
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\crt-parent-20260830\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\CRT Parent Range EA
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=M15
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
    Write-Host ("START asset-specific locked {0} {1}" -f $case.Symbol,$case.Variant) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $destination -Force
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-CRT-AssetSpecific.py') --reports $destination --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'Asset-specific analysis failed'}
Write-Host 'Completed asset-specific CRT locked checks.' -ForegroundColor Green
