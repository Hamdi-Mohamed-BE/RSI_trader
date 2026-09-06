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
$expertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final EMA3 EA\AAA Final EMA3 EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\08 EMA3 - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905\EMA3 Audit'
$expertName = 'AAA Final EMA3 Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-ema3-' + $Stage.ToLowerInvariant()
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
        InpEnableTrading='true'; InpRiskPercent='1.00'; InpRewardRisk='1.70';
        InpPivotBars='5'; InpTrendEMA='200'; InpTrendSlopeBars='6';
        InpEMA3SignalTimeframe='16388'; InpEMA3StopMode='0'; InpEMA3ATRPeriod='14';
        InpEMA3StopATR='1.50'; InpEMA3SignalBufferATR='0.10'; InpEMA3FixedStopPrice='22.50';
        InpEMA3FastEMA='20'; InpEMA3MediumEMA='50';
        InpUseTrailing='true'; InpTrailStartR='1.50'; InpTrailDistanceR='1.00';
        InpUseDynamicTrailingSL='true'; InpDynamicTriggerFraction='0.50'; InpDynamicLockFraction='0.20';
        InpResearchSession='0'; InpResearchBrokerUtcOffsetMinutes='180';
        InpUseMarkovRegimeFilter='false'; InpMarkovReturnWindow='40'; InpMarkovThreshold='0.05';
        InpMarkovSignalGate='0.05'; InpMarkovMinLabels='252'; InpMarkovHistoryBars='2600'
    }
    foreach ($key in $extra.Keys) { $values[$key] = [string]$extra[$key] }
    return $values
}

Add-Case 'deployed-standard-dynamic-native' 'baseline' 'XAUUSD' (V @{})
Add-Case 'deployed-safe-dynamic-native' 'baseline' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'standard-native-only' 'baseline' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'standard-dynamic-only' 'baseline' 'XAUUSD' (V @{InpUseTrailing='false'})
Add-Case 'standard-no-management' 'baseline' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false'})

foreach ($rr in @('0.50','0.75','1.00','1.25','1.50','1.70','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' 'XAUUSD' (V @{InpRewardRisk=$rr})
}
foreach ($pivot in @('2','3','5','8','10','15')) {
    Add-Case ('stop-pivot-' + $pivot) 'stop' 'XAUUSD' (V @{InpEMA3StopMode='0';InpPivotBars=$pivot})
}
foreach ($multiple in @('0.50','0.75','1.00','1.25','1.50','2.00','2.50','3.00')) {
    Add-Case ('stop-atr-' + ($multiple -replace '\.','')) 'stop' 'XAUUSD' (V @{InpEMA3StopMode='1';InpEMA3StopATR=$multiple})
}
foreach ($buffer in @('0.00','0.10','0.25','0.50')) {
    Add-Case ('stop-signal-' + ($buffer -replace '\.','')) 'stop' 'XAUUSD' (V @{InpEMA3StopMode='2';InpEMA3SignalBufferATR=$buffer})
}
foreach ($distance in @('10.00','15.00','22.50','30.00','45.00')) {
    Add-Case ('stop-fixed-' + ($distance -replace '\.','')) 'stop' 'XAUUSD' (V @{InpEMA3StopMode='3';InpEMA3FixedStopPrice=$distance})
}

Add-Case 'manage-none' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false'})
Add-Case 'manage-native-100-050' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='1.00';InpTrailDistanceR='0.50'})
Add-Case 'manage-native-150-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='1.50';InpTrailDistanceR='1.00'})
Add-Case 'manage-native-200-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='2.00';InpTrailDistanceR='1.00'})
Add-Case 'manage-dynamic5020-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false'})
Add-Case 'manage-dynamic6020-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'manage-dynamic6020-only-safe' 'safe-filter' 'XAUUSD' (V @{InpUseTrailing='false';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20';InpUseMarkovRegimeFilter='true'})
Add-Case 'manage-dynamic7525-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false';InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})
Add-Case 'manage-dynamic5020-native' 'management' 'XAUUSD' (V @{})
Add-Case 'manage-dynamic6020-native' 'management' 'XAUUSD' (V @{InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})

foreach ($row in @(@('all','0'),@('asia','1'),@('london','2'),@('new-york','3'),@('overlap','4'))) {
    Add-Case ('session-' + $row[0]) 'session' 'XAUUSD' (V @{InpResearchSession=$row[1]})
}
foreach ($row in @(@('h4','16388'),@('h1','16385'),@('m30','30'),@('m15','15'))) {
    Add-Case ('timeframe-' + $row[0] + '-pivot') 'timeframe' 'XAUUSD' (V @{InpEMA3SignalTimeframe=$row[1]})
    Add-Case ('timeframe-' + $row[0] + '-atr150') 'timeframe' 'XAUUSD' (V @{InpEMA3SignalTimeframe=$row[1];InpEMA3StopMode='1';InpEMA3StopATR='1.50'})
}

foreach ($trend in @('100','150','200','250')) {
    Add-Case ('trend-ema-' + $trend) 'signal-filter' 'XAUUSD' (V @{InpTrendEMA=$trend})
}
foreach ($slope in @('3','6','9','12')) {
    Add-Case ('trend-slope-' + $slope) 'signal-filter' 'XAUUSD' (V @{InpTrendSlopeBars=$slope})
}
foreach ($row in @(@('10-30','10','30'),@('20-50','20','50'),@('30-75','30','75'),@('50-100','50','100'))) {
    Add-Case ('fast-medium-' + $row[0]) 'signal-filter' 'XAUUSD' (V @{InpEMA3FastEMA=$row[1];InpEMA3MediumEMA=$row[2]})
}
Add-Case 'safe-off' 'safe-filter' 'XAUUSD' (V @{})
Add-Case 'safe-on' 'safe-filter' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})

foreach ($row in @(@('xau','XAUUSD'),@('xag','XAGUSD'),@('us30','US30'),@('us100','USTEC'),@('btc','BTCUSD'),@('gbpjpy','GBPJPY'))) {
    Add-Case ('market-' + $row[0]) 'market' $row[1] (V @{InpEMA3StopMode='1';InpEMA3StopATR='1.50'})
}

foreach ($session in @(@('all','0'),@('asia','1'),@('london','2'),@('newyork','3'),@('overlap','4'))) {
    foreach ($rr in @('1.00','1.50','1.70','2.00','2.50','3.00','4.00')) {
        Add-Case ('combo-' + $session[0] + '-pivot-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpResearchSession=$session[1];InpRewardRisk=$rr})
    }
}
foreach ($rr in @('1.00','1.50','1.70','2.00','2.50','3.00','4.00')) {
    Add-Case ('combo-all-atr100-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpEMA3StopMode='1';InpEMA3StopATR='1.00';InpRewardRisk=$rr})
    Add-Case ('combo-all-atr150-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpEMA3StopMode='1';InpEMA3StopATR='1.50';InpRewardRisk=$rr})
    Add-Case ('combo-all-signal010-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpEMA3StopMode='2';InpEMA3SignalBufferATR='0.10';InpRewardRisk=$rr})
}
foreach ($tf in @(@('h1','16385'),@('m30','30'))) {
    foreach ($rr in @('1.00','1.70','2.50','3.00')) {
        Add-Case ('combo-' + $tf[0] + '-atr150-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpEMA3SignalTimeframe=$tf[1];InpEMA3StopMode='1';InpEMA3StopATR='1.50';InpRewardRisk=$rr})
    }
}

if ($OnlyCases.Count -gt 0) {
    $chosen = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $chosen) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching EMA3 cases.' }

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
    $case.Values['InpMagic'] = [string](86800000 + $index)
    foreach ($key in $case.Values.Keys) { $setText = Upsert-Input $setText $key $case.Values[$key] }
    $setName = ('EMA3 Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))

    $reportBase = ('ema3-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
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
Period=H1
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
Write-Host ('Completed {0} EMA3 audit cases.' -f $cases.Count) -ForegroundColor Green
