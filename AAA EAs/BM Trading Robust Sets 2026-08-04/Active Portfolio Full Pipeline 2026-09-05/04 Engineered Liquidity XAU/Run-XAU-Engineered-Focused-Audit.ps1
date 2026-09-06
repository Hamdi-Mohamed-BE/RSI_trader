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
$expertSource = Join-Path $packageRoot 'Engineered Liquidity Sweep Research 2026-08-30\EA\Engineered Liquidity Sweep EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\04 Engineered Liquidity XAU - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905'
$expertName = 'Engineered Liquidity XAU Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-engineered-xau-' + $Stage.ToLowerInvariant()
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
function Add-Case(
    [string]$case,[string]$group,[string]$minimumRR='2.00',[string]$stopBuffer='0.08',
    [string]$holdingBars='24',[string]$tradesPerDay='2',[string]$dynamic='true',
    [string]$trigger='0.50',[string]$lock='0.20',[string]$session='0',[string]$safe='false',
    [string]$allowLong='true',[string]$allowShort='true'
) {
    [void]$cases.Add([pscustomobject]@{
        Case=$case; Group=$group; MinimumRR=$minimumRR; StopBuffer=$stopBuffer; HoldingBars=$holdingBars;
        TradesPerDay=$tradesPerDay; Dynamic=$dynamic; Trigger=$trigger; Lock=$lock; Session=$session;
        Safe=$safe; AllowLong=$allowLong; AllowShort=$allowShort
    })
}

Add-Case 'current-dynamic5020' 'baseline'
Add-Case 'current-native' 'baseline' '2.00' '0.08' '24' '2' 'false'
foreach ($rr in @('0.50','0.75','1.00','1.25','1.50','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' $rr
}
foreach ($buffer in @('0.00','0.03','0.05','0.08','0.12','0.20','0.30')) {
    Add-Case ('stop-buffer-' + ($buffer -replace '\.','')) 'stop' '2.00' $buffer
}
Add-Case 'manage-native' 'management' '2.00' '0.08' '24' '2' 'false'
Add-Case 'manage-dynamic5020' 'management'
Add-Case 'manage-dynamic5010' 'management' '2.00' '0.08' '24' '2' 'true' '0.50' '0.10'
Add-Case 'manage-dynamic5030' 'management' '2.00' '0.08' '24' '2' 'true' '0.50' '0.30'
Add-Case 'manage-dynamic6020' 'management' '2.00' '0.08' '24' '2' 'true' '0.60' '0.20'
Add-Case 'manage-dynamic7525' 'management' '2.00' '0.08' '24' '2' 'true' '0.75' '0.25'
foreach ($hold in @('12','24','48','96')) { Add-Case ('hold-' + $hold) 'holding' '2.00' '0.08' $hold }
foreach ($frequency in @('1','2','3')) { Add-Case ('max-trades-' + $frequency) 'frequency' '2.00' '0.08' '24' $frequency }
foreach ($row in @(@('session-all','0'),@('session-asia','1'),@('session-london','2'),@('session-new-york','3'),@('session-overlap','4'))) {
    Add-Case $row[0] 'session' '2.00' '0.08' '24' '2' 'true' '0.50' '0.20' $row[1]
}
Add-Case 'safe-off' 'safe-filter'
Add-Case 'safe-on' 'safe-filter' '2.00' '0.08' '24' '2' 'true' '0.50' '0.20' '0' 'true'
Add-Case 'direction-both' 'direction'
Add-Case 'direction-long-only' 'direction' '2.00' '0.08' '24' '2' 'true' '0.50' '0.20' '0' 'false' 'true' 'false'
Add-Case 'direction-short-only' 'direction' '2.00' '0.08' '24' '2' 'true' '0.50' '0.20' '0' 'false' 'false' 'true'

# Combined finalists are chosen only from the development window. Keep these cases here so later
# locked and three-year runs remain reproducible after the development decision is documented.
Add-Case 'candidate-native-rr2' 'combined-finalist' '2.00' '0.08' '24' '2' 'false'
Add-Case 'candidate-dynamic-rr2' 'combined-finalist'
Add-Case 'combo-rr25-stop000-dyn6020' 'combined-finalist' '2.50' '0.00' '24' '2' 'true' '0.60' '0.20'
Add-Case 'combo-rr25-stop000-dyn6020-safe' 'combined-finalist' '2.50' '0.00' '24' '2' 'true' '0.60' '0.20' '0' 'true'
Add-Case 'combo-rr25-stop000-dyn6020-long' 'combined-finalist' '2.50' '0.00' '24' '2' 'true' '0.60' '0.20' '0' 'false' 'true' 'false'
Add-Case 'combo-rr25-stop000-dyn6020-long-safe' 'combined-finalist' '2.50' '0.00' '24' '2' 'true' '0.60' '0.20' '0' 'true' 'true' 'false'
Add-Case 'combo-rr25-stop003-dyn6020' 'combined-finalist' '2.50' '0.03' '24' '2' 'true' '0.60' '0.20'
Add-Case 'combo-rr25-stop003-dyn6020-safe' 'combined-finalist' '2.50' '0.03' '24' '2' 'true' '0.60' '0.20' '0' 'true'
Add-Case 'combo-rr25-stop003-dyn6020-long' 'combined-finalist' '2.50' '0.03' '24' '2' 'true' '0.60' '0.20' '0' 'false' 'true' 'false'
Add-Case 'combo-rr25-stop003-dyn6020-long-safe' 'combined-finalist' '2.50' '0.03' '24' '2' 'true' '0.60' '0.20' '0' 'true' 'true' 'false'

if ($OnlyCases.Count -gt 0) {
    $filtered = @($cases | Where-Object { $_.Case -in $OnlyCases })
    $cases = [Collections.Generic.List[object]]::new()
    foreach ($item in $filtered) { [void]$cases.Add($item) }
}
if ($cases.Count -eq 0) { throw 'No matching Engineered Liquidity XAU audit cases.' }

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
    foreach ($setting in @(
        @('InpMinimumRewardRisk',$case.MinimumRR),@('InpStopBufferATR',$case.StopBuffer),
        @('InpMaximumHoldingBars',$case.HoldingBars),@('InpMaximumTradesPerDay',$case.TradesPerDay),
        @('InpAllowLong',$case.AllowLong),@('InpAllowShort',$case.AllowShort),@('InpRiskMode','0'),
        @('InpRiskPercent','1.00'),@('InpUseDynamicTrailingSL',$case.Dynamic),
        @('InpDynamicTriggerFraction',$case.Trigger),@('InpDynamicLockFraction',$case.Lock),
        @('InpResearchSession',$case.Session),@('InpResearchBrokerUtcOffsetMinutes','0'),
        @('InpUseMarkovRegimeFilter',$case.Safe),@('InpMarkovReturnWindow','40'),
        @('InpMarkovThreshold','0.05'),@('InpMarkovSignalGate','0.05'),
        @('InpMarkovMinLabels','252'),@('InpMarkovHistoryBars','2600'),@('InpMagic',[string](86400000+$index))
    )) { $setText = Upsert-Input $setText $setting[0] $setting[1] }

    $setName = ('Engineered XAU Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    $reportBase = ('engineered-xau-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
    $reportPath = Join-Path $reportFolder ($reportBase+'.htm')
    $completedPath = Join-Path $outputFolder ($reportBase+'.htm')
    $configPath = Join-Path $configFolder ($reportBase+'.ini')
    $relativeReport = 'reports\'+$runName+'\'+$reportBase+'.htm'
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
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ('START {0} / {1}' -f $Stage,$case.Case) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw ('MT5 timed out on '+$case.Case) }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw ('No MT5 report for '+$case.Case) }
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase+'*') | Copy-Item -Destination $outputFolder -Force
    } else { Write-Host ('SKIP COMPLETED '+$case.Case) -ForegroundColor DarkGray }
    [void]$manifest.Add([pscustomobject]@{
        case=$case.Case; group=$case.Group; stage=$Stage; report=$completedPath; from=$window.From; to=$window.To;
        model=$window.Model; minimum_reward_risk=$case.MinimumRR; stop_buffer_atr=$case.StopBuffer;
        maximum_holding_bars=$case.HoldingBars; maximum_trades_per_day=$case.TradesPerDay;
        dynamic=$case.Dynamic; dynamic_trigger=$case.Trigger; dynamic_lock=$case.Lock; session=$case.Session;
        safe_filter=$case.Safe; allow_long=$case.AllowLong; allow_short=$case.AllowShort; risk_percent='1.00'
    })
}

$manifestPath = Join-Path $outputFolder 'manifest.json'
if ($OnlyCases.Count -gt 0 -and (Test-Path -LiteralPath $manifestPath)) {
    $existing = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
    $newNames = @($manifest | ForEach-Object { $_.case })
    $preserved = @($existing | Where-Object { $_.case -notin $newNames })
    $newRows = @($manifest | ForEach-Object { $_ })
    (@($preserved) + @($newRows)) | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
} else {
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
Write-Host ('Completed {0} Engineered Liquidity XAU audit cases.' -f $cases.Count) -ForegroundColor Green
