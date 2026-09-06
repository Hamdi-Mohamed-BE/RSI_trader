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
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\02 BTC Top Down FVG Liquidity - CURRENT - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905'
$expertName = 'BTC Top Down FVG Liquidity Audit'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runName = 'active-reaudit-btc-' + $Stage.ToLowerInvariant()
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
    if ([regex]::IsMatch($text, $pattern)) {
        return [regex]::Replace($text, $pattern, ($key + '=' + $value))
    }
    return $text.TrimEnd() + "`r`n" + $key + '=' + $value + "`r`n"
}

$cases = [Collections.Generic.List[object]]::new()
foreach ($rr in @('0.50','0.75','1.00','1.25','1.50','2.00','2.50','3.00','4.00')) {
    [void]$cases.Add([pscustomobject]@{ Case = ('rr-' + ($rr -replace '\.','')); Group = 'reward-risk'; RR = $rr; Buffer = '0.10'; MinStop = '0.30'; BE = '0.00'; Hold = '96'; Dynamic = 'false'; Session = '0' })
}
foreach ($row in @(
    @('stop-b002-min020','0.02','0.20'),
    @('stop-b005-min030','0.05','0.30'),
    @('stop-b010-min030','0.10','0.30'),
    @('stop-b010-min050','0.10','0.50'),
    @('stop-b015-min050','0.15','0.50'),
    @('stop-b025-min050','0.25','0.50'),
    @('stop-b020-min075','0.20','0.75')
)) {
    [void]$cases.Add([pscustomobject]@{ Case = $row[0]; Group = 'stop'; RR = '2.00'; Buffer = $row[1]; MinStop = $row[2]; BE = '0.00'; Hold = '96'; Dynamic = 'false'; Session = '0' })
}
foreach ($row in @(
    @('manage-current','0.00','96','false'),
    @('manage-be050','0.50','96','false'),
    @('manage-be100','1.00','96','false'),
    @('manage-hold48','0.00','48','false'),
    @('manage-hold192','0.00','192','false'),
    @('manage-dynamic5020','0.00','96','true')
)) {
    [void]$cases.Add([pscustomobject]@{ Case = $row[0]; Group = 'management'; RR = '2.00'; Buffer = '0.10'; MinStop = '0.30'; BE = $row[1]; Hold = $row[2]; Dynamic = $row[3]; Session = '0' })
}
foreach ($row in @(
    @('session-all','0'),
    @('session-asia','1'),
    @('session-london','2'),
    @('session-new-york','3'),
    @('session-overlap','4')
)) {
    [void]$cases.Add([pscustomobject]@{ Case = $row[0]; Group = 'session'; RR = '2.00'; Buffer = '0.10'; MinStop = '0.30'; BE = '0.00'; Hold = '96'; Dynamic = 'false'; Session = $row[1] })
}
[void]$cases.Add([pscustomobject]@{ Case = 'combo-asia-dynamic5020'; Group = 'combined-finalist'; RR = '2.00'; Buffer = '0.10'; MinStop = '0.30'; BE = '0.00'; Hold = '96'; Dynamic = 'true'; Session = '1' })
[void]$cases.Add([pscustomobject]@{ Case = 'combo-asia-be100'; Group = 'combined-finalist'; RR = '2.00'; Buffer = '0.10'; MinStop = '0.30'; BE = '1.00'; Hold = '96'; Dynamic = 'false'; Session = '1' })

if ($OnlyCases.Count -gt 0) {
    $cases = [Collections.Generic.List[object]]@($cases | Where-Object { $_.Case -in $OnlyCases })
}
if ($cases.Count -eq 0) { throw 'No matching BTC audit cases.' }

$window = switch ($Stage) {
    'Development' { [pscustomobject]@{ From = '2023.09.01'; To = '2025.08.31'; Model = 1 } }
    'Locked'      { [pscustomobject]@{ From = '2025.09.01'; To = '2026.09.01'; Model = 0 } }
    'ThreeYear'   { [pscustomobject]@{ From = '2023.09.01'; To = '2026.09.01'; Model = 0 } }
}

$manifest = [Collections.Generic.List[object]]::new()
$index = 0
foreach ($case in $cases) {
    $index++
    $setText = Get-Content -LiteralPath $setSource -Raw
    $setText = Upsert-Input $setText 'InpRewardRisk' $case.RR
    $setText = Upsert-Input $setText 'InpStopBufferATR' $case.Buffer
    $setText = Upsert-Input $setText 'InpMinimumStopATR' $case.MinStop
    $setText = Upsert-Input $setText 'InpBreakEvenAtR' $case.BE
    $setText = Upsert-Input $setText 'InpMaximumHoldingBars' $case.Hold
    $setText = Upsert-Input $setText 'InpRiskPercent' '1.00'
    $setText = Upsert-Input $setText 'InpUseDynamicTrailingSL' $case.Dynamic
    $setText = Upsert-Input $setText 'InpDynamicTriggerFraction' '0.50'
    $setText = Upsert-Input $setText 'InpDynamicLockFraction' '0.20'
    $setText = Upsert-Input $setText 'InpResearchSession' $case.Session
    $setText = Upsert-Input $setText 'InpResearchBrokerUtcOffsetMinutes' '0'
    $setText = Upsert-Input $setText 'InpMagic' ([string](86279000 + $index))

    $setName = ('BTC Audit {0} {1}.set' -f $Stage, $case.Case)
    [IO.File]::WriteAllText((Join-Path $setTargetFolder $setName), $setText, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $savedSetFolder $setName), $setText, [Text.UTF8Encoding]::new($false))

    $reportBase = ('btc-{0}-{1}' -f $Stage.ToLowerInvariant(), $case.Case)
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
Symbol=BTCUSD
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
    [IO.File]::WriteAllText($configPath, $config, [Text.UnicodeEncoding]::new($false, $true))

    if (-not (Test-Path -LiteralPath $completedPath)) {
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ('START {0} / {1}' -f $Stage, $case.Case) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
        try {
            Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        } catch {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw ('MT5 timed out on ' + $case.Case)
        }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw ('No MT5 report for ' + $case.Case) }
        Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') | Copy-Item -Destination $outputFolder -Force
    } else {
        Write-Host ('SKIP COMPLETED {0}' -f $case.Case) -ForegroundColor DarkGray
    }
    [void]$manifest.Add([pscustomobject]@{
        case = $case.Case; group = $case.Group; stage = $Stage; report = $completedPath
        from = $window.From; to = $window.To; model = $window.Model
        reward_risk = $case.RR; stop_buffer_atr = $case.Buffer; minimum_stop_atr = $case.MinStop
        break_even_at_r = $case.BE; maximum_holding_bars = $case.Hold
        dynamic = $case.Dynamic; session = $case.Session; risk_percent = '1.00'
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputFolder 'manifest.json') -Encoding utf8
Write-Host ('Completed {0} BTC audit cases.' -f $cases.Count) -ForegroundColor Green
