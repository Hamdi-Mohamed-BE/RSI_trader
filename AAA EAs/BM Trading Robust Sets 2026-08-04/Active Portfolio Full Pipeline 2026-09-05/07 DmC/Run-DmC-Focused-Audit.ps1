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
$expertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC EA\AAA Final DmC EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\07 DmC - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905\DmC Audit'
$expertName = 'AAA Final DmC Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-dmc-' + $Stage.ToLowerInvariant()
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
        InpDmCSignalTimeframe='16385'; InpDmCStopMode='0'; InpDmCFixedStopPrice='22.50';
        InpDmCATRPeriod='14'; InpDmCStopATR='1.00'; InpDmCSignalBufferATR='0.10';
        InpUseTrailing='true'; InpTrailStartR='1.50'; InpTrailDistanceR='1.00';
        InpUseDynamicTrailingSL='true'; InpDynamicTriggerFraction='0.50'; InpDynamicLockFraction='0.20';
        InpResearchSession='0'; InpResearchBrokerUtcOffsetMinutes='180';
        InpUseMarkovRegimeFilter='false'; InpMarkovReturnWindow='40'; InpMarkovThreshold='0.05';
        InpMarkovSignalGate='0.05'; InpMarkovMinLabels='252'; InpMarkovHistoryBars='2600'
    }
    foreach ($key in $extra.Keys) { $values[$key] = [string]$extra[$key] }
    return $values
}

Add-Case 'deployed-safe-dynamic-native' 'baseline' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'standard-dynamic-native' 'baseline' 'XAUUSD' (V @{})
Add-Case 'standard-native-only' 'baseline' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'standard-dynamic-only' 'baseline' 'XAUUSD' (V @{InpUseTrailing='false'})
Add-Case 'standard-no-management' 'baseline' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false'})

foreach ($rr in @('0.50','0.75','1.00','1.50','1.70','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' 'XAUUSD' (V @{InpRewardRisk=$rr})
}
foreach ($distance in @('10.00','15.00','22.50','30.00','45.00')) {
    Add-Case ('stop-fixed-' + ($distance -replace '\.','')) 'stop' 'XAUUSD' (V @{InpDmCStopMode='0';InpDmCFixedStopPrice=$distance})
}
foreach ($multiple in @('0.50','0.75','1.00','1.50','2.00','2.50')) {
    Add-Case ('stop-atr-' + ($multiple -replace '\.','')) 'stop' 'XAUUSD' (V @{InpDmCStopMode='1';InpDmCStopATR=$multiple})
}
foreach ($buffer in @('0.00','0.10','0.25','0.50')) {
    Add-Case ('stop-signal-' + ($buffer -replace '\.','')) 'stop' 'XAUUSD' (V @{InpDmCStopMode='2';InpDmCSignalBufferATR=$buffer})
}

Add-Case 'manage-none' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false'})
Add-Case 'manage-native-100-050' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='1.00';InpTrailDistanceR='0.50'})
Add-Case 'manage-native-150-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='1.50';InpTrailDistanceR='1.00'})
Add-Case 'manage-native-200-100' 'management' 'XAUUSD' (V @{InpUseDynamicTrailingSL='false';InpTrailStartR='2.00';InpTrailDistanceR='1.00'})
Add-Case 'manage-dynamic5020-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false'})
Add-Case 'manage-dynamic6020-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'manage-dynamic7525-only' 'management' 'XAUUSD' (V @{InpUseTrailing='false';InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})
Add-Case 'manage-dynamic5020-native' 'management' 'XAUUSD' (V @{})
Add-Case 'manage-dynamic6020-native' 'management' 'XAUUSD' (V @{InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})

foreach ($row in @(@('all','0'),@('asia','1'),@('london','2'),@('new-york','3'),@('overlap','4'))) {
    Add-Case ('session-' + $row[0]) 'session' 'XAUUSD' (V @{InpResearchSession=$row[1]})
}
foreach ($row in @(@('h4','16388'),@('h1','16385'),@('m30','30'),@('m15','15'))) {
    Add-Case ('timeframe-' + $row[0]) 'timeframe' 'XAUUSD' (V @{InpDmCSignalTimeframe=$row[1];InpDmCStopMode='1';InpDmCStopATR='1.00'})
}
Add-Case 'safe-off' 'safe-filter' 'XAUUSD' (V @{})
Add-Case 'safe-on' 'safe-filter' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})

foreach ($row in @(
    @('xau','XAUUSD'),@('xag','XAGUSD'),@('us30','US30'),@('us100','USTEC'),@('btc','BTCUSD'),@('gbpjpy','GBPJPY')
)) {
    Add-Case ('market-' + $row[0]) 'market' $row[1] (V @{InpDmCStopMode='1';InpDmCStopATR='1.00'})
}

foreach ($rr in @('0.75','1.00','1.70','3.00','4.00','5.00')) {
    Add-Case ('combo-h1-asia-fixed-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk=$rr})
}
Add-Case 'combo-h1-asia-fixed-rr400-dynamic-only' 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk='4.00';InpUseTrailing='false'})
Add-Case 'combo-h1-asia-fixed-rr300-safe' 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk='3.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'combo-h1-asia-fixed-rr400-safe' 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk='4.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'combo-h1-asia-signal010-rr400' 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk='4.00';InpDmCStopMode='2';InpDmCSignalBufferATR='0.10'})
Add-Case 'combo-h1-asia-atr050-rr400' 'combined-search' 'XAUUSD' (V @{InpResearchSession='1';InpRewardRisk='4.00';InpDmCStopMode='1';InpDmCStopATR='0.50'})
Add-Case 'combo-h1-london-fixed-rr400' 'combined-search' 'XAUUSD' (V @{InpResearchSession='2';InpRewardRisk='4.00'})
Add-Case 'combo-h1-newyork-fixed-rr400' 'combined-search' 'XAUUSD' (V @{InpResearchSession='3';InpRewardRisk='4.00'})
foreach ($rr in @('0.75','1.70','3.00','4.00')) {
    Add-Case ('combo-m30-atr100-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpDmCSignalTimeframe='30';InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk=$rr})
    Add-Case ('combo-m30-signal010-rr' + ($rr -replace '\.','')) 'combined-search' 'XAUUSD' (V @{InpDmCSignalTimeframe='30';InpDmCStopMode='2';InpDmCSignalBufferATR='0.10';InpRewardRisk=$rr})
}
Add-Case 'combo-m30-asia-atr100-rr400' 'combined-search' 'XAUUSD' (V @{InpDmCSignalTimeframe='30';InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk='4.00';InpResearchSession='1'})
foreach ($rr in @('0.75','1.70','3.00','4.00')) {
    Add-Case ('combo-gbpjpy-atr100-rr' + ($rr -replace '\.','')) 'combined-search' 'GBPJPY' (V @{InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk=$rr})
}
Add-Case 'combo-gbpjpy-asia-atr100-rr170' 'combined-search' 'GBPJPY' (V @{InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk='1.70';InpResearchSession='1'})
Add-Case 'combo-gbpjpy-newyork-atr100-rr170' 'combined-search' 'GBPJPY' (V @{InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk='1.70';InpResearchSession='3'})

# Reproducible finalists. The focused development screen determines which are
# promoted to locked and exact-three-year validation through -OnlyCases.
Add-Case 'final-deployed-safe' 'combined-finalist' 'XAUUSD' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'final-current-standard' 'combined-finalist' 'XAUUSD' (V @{})
Add-Case 'final-atr100-rr170-dynamic' 'combined-finalist' 'XAUUSD' (V @{InpDmCStopMode='1';InpDmCStopATR='1.00';InpUseTrailing='false'})
Add-Case 'final-signal010-rr170-dynamic' 'combined-finalist' 'XAUUSD' (V @{InpDmCStopMode='2';InpDmCSignalBufferATR='0.10';InpUseTrailing='false'})
Add-Case 'final-atr100-rr250-dynamic' 'combined-finalist' 'XAUUSD' (V @{InpDmCStopMode='1';InpDmCStopATR='1.00';InpRewardRisk='2.50';InpUseTrailing='false'})
Add-Case 'final-atr150-rr250-dynamic' 'combined-finalist' 'XAUUSD' (V @{InpDmCStopMode='1';InpDmCStopATR='1.50';InpRewardRisk='2.50';InpUseTrailing='false'})
Add-Case 'final-fixed2250-rr250-dynamic' 'combined-finalist' 'XAUUSD' (V @{InpRewardRisk='2.50';InpUseTrailing='false'})

if ($OnlyCases.Count -gt 0) {
    $chosen = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $chosen) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching DmC cases.' }

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
    $case.Values['InpMagic'] = [string](86700000 + $index)
    foreach ($key in $case.Values.Keys) { $setText = Upsert-Input $setText $key $case.Values[$key] }
    $setName = ('DmC Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))

    $reportBase = ('dmc-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
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
Write-Host ('Completed {0} DmC audit cases.' -f $cases.Count) -ForegroundColor Green
