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
$expertSource = Join-Path $auditRoot 'EA\AAA Final Asia Breakout Audit.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\06 Asia Breakout - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905\Asia Breakout XAU Audit'
$expertName = 'AAA Final Asia Breakout Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-asia-xau-' + $Stage.ToLowerInvariant()
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
function Add-Case([string]$case,[string]$group,[hashtable]$values) {
    [void]$cases.Add([pscustomobject]@{ Case=$case; Group=$group; Values=$values })
}
function V([hashtable]$extra) {
    $values = @{
        InpRiskPercent='1.00'; InpRewardRisk='3.00'; InpAsiaBufferPercent='0.03';
        InpAsiaSignalTimeframe='16385'; InpAsiaEntryStartUTC='8'; InpAsiaEntryEndUTC='13';
        InpAsiaStopMode='0'; InpAsiaStopBufferPercent='0.00'; InpUseTrailing='true';
        InpAsiaUseNativeTrailing='true'; InpAsiaTrailStartR='2.00'; InpAsiaTrailDistanceR='0.50';
        InpUseDynamicTrailingSL='true'; InpDynamicTriggerFraction='0.50'; InpDynamicLockFraction='0.20';
        InpResearchSession='0'; InpResearchBrokerUtcOffsetMinutes='0';
        InpUseMarkovRegimeFilter='false'; InpMarkovReturnWindow='40'; InpMarkovThreshold='0.05';
        InpMarkovSignalGate='0.05'; InpMarkovMinLabels='252'; InpMarkovHistoryBars='2600'
    }
    foreach ($key in $extra.Keys) { $values[$key] = [string]$extra[$key] }
    return $values
}

Add-Case 'deployed-safe-dynamic-native' 'baseline' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'standard-dynamic-native' 'baseline' (V @{})
Add-Case 'standard-native-only' 'baseline' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'standard-no-management' 'baseline' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})

foreach ($rr in @('0.50','0.75','1.00','1.50','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' (V @{InpRewardRisk=$rr})
}
foreach ($buffer in @('0.00','0.01','0.03','0.05','0.10')) {
    Add-Case ('breakout-buffer-' + ($buffer -replace '\.','')) 'breakout-buffer' (V @{InpAsiaBufferPercent=$buffer})
}
foreach ($row in @(
    @('midpoint','0','0.00'),@('opposite-b000','1','0.00'),@('opposite-b003','1','0.03'),
    @('opposite-b010','1','0.10'),@('signal-b000','2','0.00'),@('signal-b003','2','0.03'),@('signal-b010','2','0.10')
)) {
    Add-Case ('stop-' + $row[0]) 'stop' (V @{InpAsiaStopMode=$row[1];InpAsiaStopBufferPercent=$row[2]})
}

Add-Case 'manage-none' 'management' (V @{InpUseDynamicTrailingSL='false';InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'manage-native-200-050' 'management' (V @{InpUseDynamicTrailingSL='false';InpAsiaTrailStartR='2.00';InpAsiaTrailDistanceR='0.50'})
Add-Case 'manage-native-150-075' 'management' (V @{InpUseDynamicTrailingSL='false';InpAsiaTrailStartR='1.50';InpAsiaTrailDistanceR='0.75'})
Add-Case 'manage-native-100-050' 'management' (V @{InpUseDynamicTrailingSL='false';InpAsiaTrailStartR='1.00';InpAsiaTrailDistanceR='0.50'})
Add-Case 'manage-dynamic5020-only' 'management' (V @{InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'manage-dynamic6020-only' 'management' (V @{InpUseTrailing='false';InpAsiaUseNativeTrailing='false';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'manage-dynamic7525-only' 'management' (V @{InpUseTrailing='false';InpAsiaUseNativeTrailing='false';InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})
Add-Case 'manage-dynamic5020-native' 'management' (V @{})
Add-Case 'manage-dynamic6020-native' 'management' (V @{InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})

foreach ($row in @(@('all','0'),@('asia','1'),@('london','2'),@('new-york','3'),@('overlap','4'))) {
    Add-Case ('session-' + $row[0]) 'session' (V @{InpResearchSession=$row[1]})
}
foreach ($row in @(@('h1','16385'),@('m30','30'),@('m15','15'))) {
    Add-Case ('timeframe-' + $row[0]) 'timeframe' (V @{InpAsiaSignalTimeframe=$row[1]})
}
foreach ($row in @(@('0800-1000','8','10'),@('0800-1200','8','12'),@('0800-1300','8','13'),@('0800-1500','8','15'))) {
    Add-Case ('window-' + $row[0]) 'entry-window' (V @{InpAsiaEntryStartUTC=$row[1];InpAsiaEntryEndUTC=$row[2]})
}
Add-Case 'safe-off' 'safe-filter' (V @{})
Add-Case 'safe-on' 'safe-filter' (V @{InpUseMarkovRegimeFilter='true'})

# Reproducible neighborhoods for later locked/three-year validation.
Add-Case 'final-current-standard' 'combined-finalist' (V @{})
Add-Case 'final-current-safe' 'combined-finalist' (V @{InpUseMarkovRegimeFilter='true'})
Add-Case 'final-rr3-dynamic5020-only' 'combined-finalist' (V @{InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'final-rr3-native-only' 'combined-finalist' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'final-rr25-dynamic5020-only' 'combined-finalist' (V @{InpRewardRisk='2.50';InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'combo-opposite010-rr200' 'combined-finalist' (V @{InpRewardRisk='2.00';InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10'})
Add-Case 'combo-opposite010-rr250' 'combined-finalist' (V @{InpRewardRisk='2.50';InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10'})
Add-Case 'combo-opposite010-rr300' 'combined-finalist' (V @{InpRewardRisk='3.00';InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10'})
Add-Case 'combo-opposite010-rr400' 'combined-finalist' (V @{InpRewardRisk='4.00';InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10'})
Add-Case 'combo-opposite010-rr300-safe' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpUseMarkovRegimeFilter='true'})
Add-Case 'combo-opposite010-native-only' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpUseDynamicTrailingSL='false'})
Add-Case 'combo-opposite010-dynamic-only' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'combo-opposite010-no-management' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpUseDynamicTrailingSL='false';InpUseTrailing='false';InpAsiaUseNativeTrailing='false'})
Add-Case 'combo-opposite010-buffer000' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpAsiaBufferPercent='0.00'})
Add-Case 'combo-opposite010-buffer000-safe' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpAsiaBufferPercent='0.00';InpUseMarkovRegimeFilter='true'})
Add-Case 'combo-opposite010-window0812' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpAsiaEntryEndUTC='12'})
Add-Case 'combo-opposite010-window0812-safe' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.10';InpAsiaEntryEndUTC='12';InpUseMarkovRegimeFilter='true'})
Add-Case 'combo-opposite003-standard' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.03'})
Add-Case 'combo-opposite003-safe' 'combined-finalist' (V @{InpAsiaStopMode='1';InpAsiaStopBufferPercent='0.03';InpUseMarkovRegimeFilter='true'})

if ($OnlyCases.Count -gt 0) {
    $chosen = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $chosen) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching Asia Breakout cases.' }

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
    $case.Values['InpMagic'] = [string](86600000 + $index)
    foreach ($key in $case.Values.Keys) { $setText = Upsert-Input $setText $key $case.Values[$key] }
    $setName = ('Asia XAU Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))

    $reportBase = ('asia-xau-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
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
Symbol=XAUUSD
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
        Write-Host ('START {0} / {1}' -f $Stage,$case.Case) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw ('MT5 timed out on ' + $case.Case) }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw ('No MT5 report for ' + $case.Case) }
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') | Copy-Item -Destination $outputFolder -Force
    } else { Write-Host ('SKIP COMPLETED ' + $case.Case) -ForegroundColor DarkGray }
    [void]$manifest.Add([pscustomobject]@{
        case=$case.Case; group=$case.Group; stage=$Stage; report=$completedPath; from=$window.From; to=$window.To;
        model=$window.Model; risk_percent='1.00'; settings=$case.Values
    })
}

$manifestPath = Join-Path $outputFolder 'manifest.json'
if ($OnlyCases.Count -gt 0 -and (Test-Path -LiteralPath $manifestPath)) {
    $existing = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
    $newNames = @($manifest | ForEach-Object { $_.case })
    $preserved = @($existing | Where-Object { $_.case -notin $newNames })
    $newRows = @($manifest | ForEach-Object { $_ })
    (@($preserved) + @($newRows)) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
} else {
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
Write-Host ('Completed {0} Asia Breakout XAU audit cases.' -f $cases.Count) -ForegroundColor Green
