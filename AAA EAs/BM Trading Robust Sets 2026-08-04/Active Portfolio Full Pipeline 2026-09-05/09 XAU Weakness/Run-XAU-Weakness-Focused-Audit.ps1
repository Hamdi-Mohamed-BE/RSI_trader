[CmdletBinding()]
param(
    [ValidateSet('Development','Locked','ThreeYear')][string]$Stage = 'Development',
    [string[]]$OnlyCases = @(),
    [int]$TimeoutSeconds = 1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$auditRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent (Split-Path -Parent $auditRoot)
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final XAU Weakness EA\AAA Final XAU Weakness EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\09 XAU Weakness - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905\XAU Weakness Audit'
$expertName = 'AAA Final XAU Weakness Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-xau-weakness-' + $Stage.ToLowerInvariant()
$configFolder = Join-Path $testerRoot ('backtest-configs\' + $runName)
$reportFolder = Join-Path $testerRoot ('reports\' + $runName)
$outputFolder = Join-Path $auditRoot ('Backtest Reports\' + $Stage)
$savedSetFolder = Join-Path $auditRoot ('Sets\' + $Stage)

foreach ($path in @($expertTargetFolder,$setTargetFolder,$configFolder,$reportFolder,$outputFolder,$savedSetFolder)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath $expertSource -Destination (Join-Path $expertTargetFolder ($expertName + '.ex5')) -Force

function Upsert-Input([string]$text,[string]$key,[string]$value) {
    $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
    if ([regex]::IsMatch($text,$pattern)) { return [regex]::Replace($text,$pattern,($key + '=' + $value)) }
    return $text.TrimEnd() + "`r`n" + $key + '=' + $value + "`r`n"
}

$cases = [Collections.Generic.List[object]]::new()
function Add-Case([string]$case,[string]$group,[string]$symbol,[hashtable]$values) {
    [void]$cases.Add([pscustomobject]@{ Case=$case; Group=$group; Symbol=$symbol; Values=$values })
}
function V([hashtable]$extra) {
    $values = @{
        InpEnableTrading='true'; InpRiskPercent='1.00'; InpRewardRisk='2.00';
        InpUseTrailing='false'; InpTrailStartR='1.50'; InpTrailDistanceR='1.00';
        InpUseDynamicTrailingSL='true'; InpDynamicTriggerFraction='0.50'; InpDynamicLockFraction='0.20';
        InpResearchSession='0'; InpResearchBrokerUtcOffsetMinutes='180';
        InpUseMarkovRegimeFilter='false'; InpMarkovReturnWindow='40'; InpMarkovThreshold='0.05';
        InpMarkovSignalGate='0.05'; InpMarkovMinLabels='252'; InpMarkovHistoryBars='2600';
        InpWeaknessTimeframe='15'; InpWeaknessATRPeriod='14'; InpWeaknessATRImpulse='2.00';
        InpWeaknessToleranceATR='0.20'; InpWeaknessBreakoutBufferATR='0.05';
        InpWeaknessStopMode='0'; InpWeaknessStopATR='1.50';
        InpWeaknessNewerMinBars='4'; InpWeaknessNewerMaxBars='16';
        InpWeaknessMinSeparationBars='4'; InpWeaknessMaxSpanBars='16';
        InpWeaknessLookbackBars='30'; InpWeaknessExpiryBars='8';
        InpWeaknessAllowLong='true'; InpWeaknessAllowShort='true'
    }
    foreach ($key in $extra.Keys) { $values[$key] = [string]$extra[$key] }
    return $values
}

Add-Case 'legacy-standard-dynamic5020' 'baseline' 'XAUUSD' (V @{})
Add-Case 'legacy-safe-dynamic5020' 'baseline' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'no-management' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'native-100-050' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='true';InpTrailStartR='1.00';InpTrailDistanceR='0.50'})
Add-Case 'native-150-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='true';InpTrailStartR='1.50';InpTrailDistanceR='1.00'})
Add-Case 'native-200-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='true';InpTrailStartR='2.00';InpTrailDistanceR='1.00'})
Add-Case 'dynamic-600-200' 'management' 'XAUUSD' (V @{InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'dynamic-750-250' 'management' 'XAUUSD' (V @{InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})
Add-Case 'dynamic500-native150' 'management' 'XAUUSD' (V @{InpUseTrailing='true'})

foreach ($rr in @('0.50','0.75','1.00','1.25','1.50','1.75','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' 'XAUUSD' (V @{InpRewardRisk=$rr})
}
Add-Case 'stop-structure' 'stop' 'XAUUSD' (V @{})
foreach ($multiple in @('0.50','0.75','1.00','1.25','1.50','2.00','2.50','3.00')) {
    Add-Case ('stop-atr-' + ($multiple -replace '\.','')) 'stop' 'XAUUSD' (V @{InpWeaknessStopMode='1';InpWeaknessStopATR=$multiple})
}
Add-Case 'stop-signal-candle' 'stop' 'XAUUSD' (V @{InpWeaknessStopMode='2'})

foreach ($row in @(@('all','0'),@('asia','1'),@('london','2'),@('new-york','3'),@('overlap','4'))) {
    Add-Case ('session-' + $row[0]) 'session' 'XAUUSD' (V @{InpResearchSession=$row[1]})
}
foreach ($row in @(@('m5','5'),@('m15','15'),@('m30','30'),@('h1','16385'))) {
    Add-Case ('timeframe-' + $row[0]) 'timeframe' 'XAUUSD' (V @{InpWeaknessTimeframe=$row[1]})
}
foreach ($impulse in @('0.75','1.00','1.25','1.50','2.00','2.50','3.00')) {
    Add-Case ('impulse-' + ($impulse -replace '\.','')) 'signal' 'XAUUSD' (V @{InpWeaknessATRImpulse=$impulse})
}
foreach ($tolerance in @('0.05','0.10','0.15','0.20','0.25','0.30','0.40')) {
    Add-Case ('tolerance-' + ($tolerance -replace '\.','')) 'signal' 'XAUUSD' (V @{InpWeaknessToleranceATR=$tolerance})
}
foreach ($buffer in @('0.00','0.02','0.05','0.10','0.20')) {
    Add-Case ('buffer-' + ($buffer -replace '\.','')) 'signal' 'XAUUSD' (V @{InpWeaknessBreakoutBufferATR=$buffer})
}
Add-Case 'long-only' 'direction' 'XAUUSD' (V @{InpWeaknessAllowShort='false'})
Add-Case 'short-only' 'direction' 'XAUUSD' (V @{InpWeaknessAllowLong='false'})
foreach ($expiry in @('2','4','8','12','16')) {
    Add-Case ('expiry-' + $expiry) 'signal' 'XAUUSD' (V @{InpWeaknessExpiryBars=$expiry})
}
Add-Case 'window-tight' 'signal' 'XAUUSD' (V @{InpWeaknessNewerMaxBars='10';InpWeaknessMaxSpanBars='10';InpWeaknessLookbackBars='20'})
Add-Case 'window-wide' 'signal' 'XAUUSD' (V @{InpWeaknessNewerMaxBars='24';InpWeaknessMaxSpanBars='24';InpWeaknessLookbackBars='48'})
Add-Case 'safe-off' 'safe-filter' 'XAUUSD' (V @{})
Add-Case 'safe-on' 'safe-filter' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})

foreach ($row in @(@('xau','XAUUSD'),@('xag','XAGUSD'),@('us30','US30'),@('us100','USTEC'),@('btc','BTCUSD'),@('gbpjpy','GBPJPY'))) {
    Add-Case ('market-' + $row[0] + '-structure') 'market' $row[1] (V @{})
    Add-Case ('market-' + $row[0] + '-atr150') 'market' $row[1] (V @{InpWeaknessStopMode='1';InpWeaknessStopATR='1.50'})
}

foreach ($rr in @('0.75','1.00','1.25','1.50','1.75','2.00','2.50','3.00')) {
    Add-Case ('combo-atr100-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpWeaknessStopMode='1';InpWeaknessStopATR='1.00';InpRewardRisk=$rr})
    Add-Case ('combo-atr150-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpWeaknessStopMode='1';InpWeaknessStopATR='1.50';InpRewardRisk=$rr})
}
foreach ($session in @(@('asia','1'),@('london','2'),@('newyork','3'),@('overlap','4'))) {
    foreach ($rr in @('1.00','1.50','2.00','2.50')) {
        Add-Case ('combo-' + $session[0] + '-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpResearchSession=$session[1];InpRewardRisk=$rr})
    }
}
foreach ($rr in @('1.50','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('combo-imp150-structure-rr' + ($rr -replace '\.','')) 'refined-search' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpRewardRisk=$rr})
    Add-Case ('combo-imp150-atr300-rr' + ($rr -replace '\.','')) 'refined-search' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpWeaknessStopMode='1';InpWeaknessStopATR='3.00';InpRewardRisk=$rr})
    Add-Case ('combo-m30-structure-rr' + ($rr -replace '\.','')) 'refined-search' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk=$rr})
}
foreach ($rr in @('1.50','2.00','2.50','3.00')) {
    Add-Case ('combo-m30-imp150-rr' + ($rr -replace '\.','')) 'refined-search' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpWeaknessATRImpulse='1.50';InpRewardRisk=$rr})
    Add-Case ('combo-overlap-atr300-rr' + ($rr -replace '\.','')) 'refined-search' 'XAUUSD' (V @{InpResearchSession='4';InpWeaknessStopMode='1';InpWeaknessStopATR='3.00';InpRewardRisk=$rr})
}
Add-Case 'final-m30-structure-rr500' 'finalist' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='5.00'})
Add-Case 'final-m30-structure-rr500-safe' 'finalist' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='5.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'final-m30-structure-rr400' 'finalist' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00'})
Add-Case 'final-imp150-structure-rr500' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpRewardRisk='5.00'})
Add-Case 'final-imp150-structure-rr500-safe' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpRewardRisk='5.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'final-imp150-structure-rr250' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpRewardRisk='2.50'})
Add-Case 'final-imp150-atr300-rr200' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpWeaknessStopMode='1';InpWeaknessStopATR='3.00';InpRewardRisk='2.00'})
Add-Case 'final-imp150-atr300-rr200-safe' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpWeaknessStopMode='1';InpWeaknessStopATR='3.00';InpRewardRisk='2.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'final-imp150-atr300-rr250' 'finalist' 'XAUUSD' (V @{InpWeaknessATRImpulse='1.50';InpWeaknessStopMode='1';InpWeaknessStopATR='3.00';InpRewardRisk='2.50'})
Add-Case 'final-overlap-structure-rr150' 'finalist' 'XAUUSD' (V @{InpResearchSession='4';InpRewardRisk='1.50'})
Add-Case 'final-overlap-structure-rr200' 'finalist' 'XAUUSD' (V @{InpResearchSession='4';InpRewardRisk='2.00'})
Add-Case 'final-newyork-structure-rr150' 'finalist' 'XAUUSD' (V @{InpResearchSession='3';InpRewardRisk='1.50'})
Add-Case 'selected-m30-rr400-dynamic5020' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00'})
Add-Case 'selected-m30-rr400-dynamic6020' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'selected-m30-rr400-dynamic7525' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})
Add-Case 'selected-m30-rr400-none' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpUseDynamicTrailingSL='false'})
Add-Case 'selected-m30-rr400-native150' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpUseDynamicTrailingSL='false';InpUseTrailing='true';InpTrailStartR='1.50';InpTrailDistanceR='1.00'})
Add-Case 'selected-m30-rr400-safe5020' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'selected-m30-rr400-safe6020' 'selected-management' 'XAUUSD' (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20';InpUseMarkovRegimeFilter='true'})
foreach ($row in @(@('xau','XAUUSD'),@('xag','XAGUSD'),@('us30','US30'),@('us100','USTEC'),@('btc','BTCUSD'),@('gbpjpy','GBPJPY'))) {
    Add-Case ('selected-market-' + $row[0] + '-m30-rr400') 'selected-market' $row[1] (V @{InpWeaknessTimeframe='30';InpRewardRisk='4.00'})
}

if ($OnlyCases.Count -gt 0) {
    $chosen = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $chosen) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching XAU Weakness cases.' }

$window = switch ($Stage) {
    'Development' { [pscustomobject]@{ From='2023.09.01'; To='2025.08.31'; Model=1 } }
    'Locked' { [pscustomobject]@{ From='2025.09.01'; To='2026.09.01'; Model=0 } }
    'ThreeYear' { [pscustomobject]@{ From='2023.09.01'; To='2026.09.01'; Model=0 } }
}

$manifest = [Collections.Generic.List[object]]::new()
$index = 0
foreach ($case in $cases) {
    $index++
    $setText = Get-Content -LiteralPath $setSource -Raw
    $case.Values['InpMagic'] = [string](86900000 + $index)
    foreach ($key in $case.Values.Keys) { $setText = Upsert-Input $setText $key $case.Values[$key] }
    $setName = ('XAU Weakness Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))

    $reportBase = ('xau-weakness-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
    $reportPath = Join-Path $reportFolder ($reportBase + '.htm')
    $completedPath = Join-Path $outputFolder ($reportBase + '.htm')
    $configPath = Join-Path $configFolder ($reportBase + '.ini')
    $relativeReport = 'reports\' + $runName + '\' + $reportBase + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($window.Model)
ExecutionMode=1
Optimization=0
FromDate=$($window.From)
ToDate=$($window.To)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UnicodeEncoding]::new($false,$true))
    if (-not (Test-Path -LiteralPath $completedPath)) {
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ('START {0} / {1} / {2}' -f $Stage,$case.Case,$case.Symbol) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw ('MT5 timed out on ' + $case.Case) }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw ('No MT5 report for ' + $case.Case) }
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') | Copy-Item -Destination $outputFolder -Force
    } else { Write-Host ('SKIP COMPLETED ' + $case.Case) -ForegroundColor DarkGray }
    [void]$manifest.Add([pscustomobject]@{
        case=$case.Case; group=$case.Group; symbol=$case.Symbol; stage=$Stage; report=$completedPath;
        from=$window.From; to=$window.To; model=$window.Model; risk_percent='1.00'; settings=$case.Values
    })
}

$manifestPath = Join-Path $outputFolder 'manifest.json'
if ($OnlyCases.Count -gt 0 -and (Test-Path -LiteralPath $manifestPath)) {
    $existing = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
    $newNames = @($manifest | ForEach-Object { $_.case })
    $preserved = @($existing | Where-Object { $_.case -notin $newNames })
    (@($preserved) + @($manifest | ForEach-Object { $_ })) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
} else {
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
Write-Host ('Completed {0} XAU Weakness audit cases.' -f $cases.Count) -ForegroundColor Green
