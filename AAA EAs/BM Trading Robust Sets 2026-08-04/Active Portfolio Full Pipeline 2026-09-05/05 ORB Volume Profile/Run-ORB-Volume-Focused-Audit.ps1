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
$expertSource = Join-Path $packageRoot 'ORB Volume Data EA\ORB Volume Data EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905'
$expertName = 'ORB Volume Profile XAU Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-orb-volume-xau-' + $Stage.ToLowerInvariant()
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
        InpRiskPercent='1.00'; InpUseMarkovRegimeFilter='false';
        InpMarkovReturnWindow='40'; InpMarkovThreshold='0.05'; InpMarkovSignalGate='0.05';
        InpMarkovMinLabels='252'; InpMarkovHistoryBars='2600';
        InpResearchSession='0'; InpResearchBrokerUtcOffsetMinutes='0'
    }
    foreach ($key in $extra.Keys) { $values[$key] = [string]$extra[$key] }
    return $values
}

Add-Case 'current-dynamic5020' 'baseline' (V @{})
Add-Case 'current-original-be1' 'baseline' (V @{InpUseDynamicTrailingSL='false'})
Add-Case 'no-management' 'baseline' (V @{InpUseDynamicTrailingSL='false';InpBreakEvenAtR='0';InpTrailStartAtR='0'})

foreach ($rr in @('0.50','0.75','1.00','1.50','2.00','2.50','3.00','4.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' (V @{InpRewardRisk=$rr})
}

foreach ($row in @(
    @('signal-b005-max15','0','0.05','1.50'),@('signal-b010-max20','0','0.10','2.00'),
    @('signal-b015-max25','0','0.15','2.50'),@('opposite-b005-max15','1','0.05','1.50'),
    @('opposite-b010-max20','1','0.10','2.00'),@('opposite-b015-max25','1','0.15','2.50')
)) {
    Add-Case ('stop-' + $row[0]) 'stop' (V @{InpStopMode=$row[1];InpStopBufferATR=$row[2];InpMaximumStopATR=$row[3]})
}

Add-Case 'manage-none' 'management' (V @{InpBreakEvenAtR='0';InpTrailStartAtR='0';InpUseDynamicTrailingSL='false'})
Add-Case 'manage-be050' 'management' (V @{InpBreakEvenAtR='0.50';InpTrailStartAtR='0';InpUseDynamicTrailingSL='false'})
Add-Case 'manage-be100' 'management' (V @{InpBreakEvenAtR='1.00';InpTrailStartAtR='0';InpUseDynamicTrailingSL='false'})
Add-Case 'manage-trail050' 'management' (V @{InpBreakEvenAtR='0';InpTrailStartAtR='0.50';InpUseDynamicTrailingSL='false'})
Add-Case 'manage-trail100' 'management' (V @{InpBreakEvenAtR='0';InpTrailStartAtR='1.00';InpUseDynamicTrailingSL='false'})
Add-Case 'manage-dynamic5020-be1' 'management' (V @{})
Add-Case 'manage-dynamic5020-no-be' 'management' (V @{InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.50';InpDynamicLockFraction='0.20'})
Add-Case 'manage-dynamic6020-no-be' 'management' (V @{InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'manage-dynamic7525-no-be' 'management' (V @{InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.75';InpDynamicLockFraction='0.25'})

foreach ($row in @(@('all','0'),@('asia','1'),@('london','2'),@('new-york','3'),@('overlap','4'))) {
    Add-Case ('session-' + $row[0]) 'session' (V @{InpResearchSession=$row[1]})
}

foreach ($row in @(
    @('ny0915-or15-m5','9','15','15','5'),@('ny0930-or05-m5','9','30','5','5'),
    @('ny0930-or15-m5','9','30','15','5'),@('ny0930-or30-m5','9','30','30','5'),
    @('ny0930-or15-m15','9','30','15','15'),@('ny0930-or30-m15','9','30','30','15'),
    @('ny0930-or30-m30','9','30','30','30')
)) {
    Add-Case ('structure-' + $row[0]) 'structure' (V @{
        InpSessionHour=$row[1];InpSessionMinute=$row[2];InpOpeningRangeMinutes=$row[3];InpSignalTimeframe=$row[4]
    })
}

Add-Case 'entry-direct' 'entry' (V @{InpEntryMode='0'})
Add-Case 'entry-retest' 'entry' (V @{InpEntryMode='1'})
foreach ($minutes in @('30','60','120','180')) {
    Add-Case ('window-' + $minutes) 'trade-window' (V @{InpTradeWindowMinutes=$minutes})
}

Add-Case 'profile-none' 'profile' (V @{InpUseProfileValueArea='false';InpUseProfilePOCBias='false';InpUseProfileBoundaryLVN='false'})
Add-Case 'profile-value-area' 'profile' (V @{InpUseProfileValueArea='true';InpUseProfilePOCBias='false';InpUseProfileBoundaryLVN='false'})
Add-Case 'profile-poc' 'profile' (V @{InpUseProfileValueArea='false';InpUseProfilePOCBias='true';InpUseProfileBoundaryLVN='false'})
Add-Case 'profile-lvn' 'profile' (V @{InpUseProfileValueArea='false';InpUseProfilePOCBias='false';InpUseProfileBoundaryLVN='true'})
Add-Case 'profile-va-poc' 'profile' (V @{InpUseProfileValueArea='true';InpUseProfilePOCBias='true';InpUseProfileBoundaryLVN='false'})
Add-Case 'profile-va-lvn' 'profile' (V @{InpUseProfileValueArea='true';InpUseProfilePOCBias='false';InpUseProfileBoundaryLVN='true'})

Add-Case 'confirmation-permissive' 'confirmation' (V @{InpMinOpeningRelativeVolume='0.60';InpMinBreakoutRelativeVolume='0.80';InpRequireVWAP='false';InpUseEMATrend='false'})
Add-Case 'confirmation-volume' 'confirmation' (V @{InpMinOpeningRelativeVolume='0.80';InpMinBreakoutRelativeVolume='1.10';InpRequireVWAP='false';InpUseEMATrend='false'})
Add-Case 'confirmation-ema' 'confirmation' (V @{InpRequireVWAP='false';InpUseEMATrend='true'})
Add-Case 'confirmation-vwap' 'confirmation' (V @{InpRequireVWAP='true';InpUseEMATrend='false'})
Add-Case 'confirmation-strict' 'confirmation' (V @{InpMinOpeningRelativeVolume='0.80';InpMinBreakoutRelativeVolume='1.10';InpRequireVWAP='true';InpUseEMATrend='true'})

Add-Case 'safe-off' 'safe-filter' (V @{})
Add-Case 'safe-on' 'safe-filter' (V @{InpUseMarkovRegimeFilter='true'})

# Finalists are deliberately explicit so locked and three-year runs remain reproducible.
# These are a robust neighborhood around the currently deployed configuration and can be
# narrowed with -OnlyCases after inspecting development evidence.
Add-Case 'final-current' 'combined-finalist' (V @{})
Add-Case 'final-rr2-native-no-be' 'combined-finalist' (V @{InpRewardRisk='2.00';InpBreakEvenAtR='0';InpUseDynamicTrailingSL='false'})
Add-Case 'final-rr25-dyn5020-no-be' 'combined-finalist' (V @{InpRewardRisk='2.50';InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.50';InpDynamicLockFraction='0.20'})
Add-Case 'final-rr25-dyn6020-no-be' 'combined-finalist' (V @{InpRewardRisk='2.50';InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20'})
Add-Case 'final-rr25-dyn6020-no-be-safe' 'combined-finalist' (V @{InpRewardRisk='2.50';InpBreakEvenAtR='0';InpUseDynamicTrailingSL='true';InpDynamicTriggerFraction='0.60';InpDynamicLockFraction='0.20';InpUseMarkovRegimeFilter='true'})

if ($OnlyCases.Count -gt 0) {
    $chosen = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $chosen) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching ORB Volume Profile cases.' }

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
    $case.Values['InpMagic'] = [string](86500000 + $index)
    foreach ($key in $case.Values.Keys) { $setText = Upsert-Input $setText $key $case.Values[$key] }
    $setName = ('ORB Volume XAU Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))

    $reportBase = ('orb-volume-xau-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
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
Period=M5
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
        case=$case.Case; group=$case.Group; stage=$Stage; report=$completedPath;
        from=$window.From; to=$window.To; model=$window.Model; risk_percent='1.00';
        settings_json=($case.Values | ConvertTo-Json -Compress)
    })
}

$manifestPath = Join-Path $outputFolder 'manifest.json'
if ($OnlyCases.Count -gt 0 -and (Test-Path -LiteralPath $manifestPath)) {
    $existing = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
    $newNames = @($manifest | ForEach-Object { $_.case })
    $preserved = @($existing | Where-Object { $_.case -notin $newNames })
    (@($preserved) + @($manifest)) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
} else {
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
Write-Host ('Completed {0} ORB Volume Profile XAU audit cases.' -f $cases.Count) -ForegroundColor Green

