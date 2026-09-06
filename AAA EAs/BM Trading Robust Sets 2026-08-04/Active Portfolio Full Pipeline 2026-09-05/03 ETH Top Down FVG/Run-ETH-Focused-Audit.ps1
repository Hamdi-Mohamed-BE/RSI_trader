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
$expertSource = Join-Path $packageRoot 'Top Down FVG Liquidity Research 2026-08-27\EA\Top Down FVG Liquidity EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\03 ETH Top Down FVG Liquidity - DYNAMIC 50-20 - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905'
$expertName = 'ETH Top Down FVG Liquidity Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-eth-' + $Stage.ToLowerInvariant()
$configFolder = Join-Path $testerRoot ('backtest-configs\' + $runName)
$reportFolder = Join-Path $testerRoot ('reports\' + $runName)
$outputFolder = Join-Path $auditRoot ('Backtest Reports\' + $Stage)
$savedSetFolder = Join-Path $auditRoot ('Sets\' + $Stage)

foreach ($path in @($expertTargetFolder, $setTargetFolder, $configFolder, $reportFolder, $outputFolder, $savedSetFolder)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath $expertSource -Destination (Join-Path $expertTargetFolder ($expertName + '.ex5')) -Force

function Upsert-Input([string]$text, [string]$key, [string]$value) {
    $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
    if ([regex]::IsMatch($text, $pattern)) { return [regex]::Replace($text, $pattern, ($key + '=' + $value)) }
    return $text.TrimEnd() + "`r`n" + $key + '=' + $value + "`r`n"
}

$cases = [Collections.Generic.List[object]]::new()
function Add-Case([string]$case,[string]$group,[string]$rr='3.00',[string]$buffer='0.10',[string]$minStop='0.30',[string]$be='0.00',[string]$hold='96',[string]$dynamic='false',[string]$trigger='0.50',[string]$lock='0.20',[string]$session='0',[string]$safe='false') {
    [void]$cases.Add([pscustomobject]@{ Case=$case; Group=$group; RR=$rr; Buffer=$buffer; MinStop=$minStop; BE=$be; Hold=$hold; Dynamic=$dynamic; Trigger=$trigger; Lock=$lock; Session=$session; Safe=$safe })
}

foreach ($rr in @('0.50','0.75','1.00','1.25','1.50','2.00','2.50','3.00','4.00','5.00')) {
    Add-Case ('rr-' + ($rr -replace '\.','')) 'reward-risk' $rr
}
foreach ($row in @(
    @('stop-b002-min020','0.02','0.20'), @('stop-b005-min030','0.05','0.30'),
    @('stop-b010-min030','0.10','0.30'), @('stop-b010-min050','0.10','0.50'),
    @('stop-b015-min050','0.15','0.50'), @('stop-b025-min050','0.25','0.50'),
    @('stop-b020-min075','0.20','0.75')
)) { Add-Case $row[0] 'stop' '3.00' $row[1] $row[2] }

Add-Case 'manage-native' 'management'
Add-Case 'manage-current-dynamic5020' 'management' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20'
Add-Case 'manage-be050' 'management' '3.00' '0.10' '0.30' '0.50'
Add-Case 'manage-be100' 'management' '3.00' '0.10' '0.30' '1.00'
Add-Case 'manage-be150' 'management' '3.00' '0.10' '0.30' '1.50'
Add-Case 'manage-hold48' 'management' '3.00' '0.10' '0.30' '0.00' '48'
Add-Case 'manage-hold192' 'management' '3.00' '0.10' '0.30' '0.00' '192'
Add-Case 'manage-dynamic6020' 'management' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.60' '0.20'
Add-Case 'manage-dynamic7525' 'management' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.75' '0.25'

foreach ($row in @(@('session-all','0'),@('session-asia','1'),@('session-london','2'),@('session-new-york','3'),@('session-overlap','4'))) {
    Add-Case $row[0] 'session' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20' $row[1]
}
Add-Case 'safe-off' 'safe-filter' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20' '0' 'false'
Add-Case 'safe-on' 'safe-filter' '3.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20' '0' 'true'
Add-Case 'combo-rr4-stop025-native' 'combined-finalist' '4.00' '0.25' '0.50'
Add-Case 'combo-rr4-dynamic5020' 'combined-finalist' '4.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20'
Add-Case 'combo-rr4-dynamic5020-safe' 'combined-finalist' '4.00' '0.10' '0.30' '0.00' '96' 'true' '0.50' '0.20' '0' 'true'
Add-Case 'combo-stop025-dynamic5020' 'combined-finalist' '3.00' '0.25' '0.50' '0.00' '96' 'true' '0.50' '0.20'
Add-Case 'combo-rr4-stop025-dynamic5020' 'combined-finalist' '4.00' '0.25' '0.50' '0.00' '96' 'true' '0.50' '0.20'
Add-Case 'combo-rr4-stop025-safe' 'combined-finalist' '4.00' '0.25' '0.50' '0.00' '96' 'false' '0.50' '0.20' '0' 'true'

if ($OnlyCases.Count -gt 0) { $cases = [Collections.Generic.List[object]]@($cases | Where-Object { $_.Case -in $OnlyCases }) }
if ($cases.Count -eq 0) { throw 'No matching ETH audit cases.' }

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
        @('InpRewardRisk',$case.RR), @('InpStopBufferATR',$case.Buffer), @('InpMinimumStopATR',$case.MinStop),
        @('InpBreakEvenAtR',$case.BE), @('InpMaximumHoldingBars',$case.Hold), @('InpRiskPercent','1.00'),
        @('InpUseDynamicTrailingSL',$case.Dynamic), @('InpDynamicTriggerFraction',$case.Trigger),
        @('InpDynamicLockFraction',$case.Lock), @('InpResearchSession',$case.Session),
        @('InpResearchBrokerUtcOffsetMinutes','0'), @('InpUseMarkovRegimeFilter',$case.Safe),
        @('InpMarkovReturnWindow','40'), @('InpMarkovThreshold','0.05'), @('InpMarkovSignalGate','0.05'),
        @('InpMarkovMinLabels','252'), @('InpMarkovHistoryBars','2600'), @('InpMagic',[string](86280000+$index))
    )) { $setText = Upsert-Input $setText $setting[0] $setting[1] }

    $setName = ('ETH Audit {0} {1}.set' -f $Stage,$case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName),$setText,[Text.UTF8Encoding]::new($false))
    $reportBase = ('eth-{0}-{1}' -f $Stage.ToLowerInvariant(),$case.Case)
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
Symbol=ETHUSD
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
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ('START {0} / {1}' -f $Stage,$case.Case) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop } catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw ('MT5 timed out on '+$case.Case) }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw ('No MT5 report for '+$case.Case) }
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase+'*') | Copy-Item -Destination $outputFolder -Force
    } else { Write-Host ('SKIP COMPLETED '+$case.Case) -ForegroundColor DarkGray }
    [void]$manifest.Add([pscustomobject]@{
        case=$case.Case; group=$case.Group; stage=$Stage; report=$completedPath; from=$window.From; to=$window.To; model=$window.Model;
        reward_risk=$case.RR; stop_buffer_atr=$case.Buffer; minimum_stop_atr=$case.MinStop; break_even_at_r=$case.BE;
        maximum_holding_bars=$case.Hold; dynamic=$case.Dynamic; dynamic_trigger=$case.Trigger; dynamic_lock=$case.Lock;
        session=$case.Session; safe_filter=$case.Safe; risk_percent='1.00'
    })
}
$manifestPath = Join-Path $outputFolder 'manifest.json'
if ($OnlyCases.Count -gt 0 -and (Test-Path -LiteralPath $manifestPath)) {
    $existingManifest = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
    $newCaseNames = @($manifest | ForEach-Object { $_.case })
    $preservedManifest = @($existingManifest | Where-Object { $_.case -notin $newCaseNames })
    $newManifest = @($manifest | ForEach-Object { $_ })
    $combinedManifest = @($preservedManifest) + @($newManifest)
    $combinedManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
} else {
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
Write-Host ('Completed {0} ETH audit cases.' -f $cases.Count) -ForegroundColor Green
