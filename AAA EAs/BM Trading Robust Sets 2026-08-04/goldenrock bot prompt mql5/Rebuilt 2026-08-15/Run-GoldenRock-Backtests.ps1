param(
    [string]$FromDate = '2021.08.15',
    [string]$ToDate = '2026.08.14',
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$portfolioRoot = Split-Path (Split-Path $researchRoot -Parent) -Parent
$tester = Join-Path $portfolioRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $tester 'terminal64.exe'
$source = Join-Path $researchRoot 'Source'
$expertTarget = Join-Path $tester 'MQL5\Experts\GoldenRock Rebuilt 2026-08-15'
$setTarget = Join-Path $tester 'MQL5\Profiles\Tester'
$configRoot = Join-Path $researchRoot 'Test Configs'
$reportRoot = Join-Path $researchRoot 'Reports\MT5 Exness XAUUSD 2021-08-15 to 2026-08-14'
$testerReportRoot = Join-Path $tester 'reports\goldenrock-20260815'
$presetSource = Join-Path $researchRoot 'Presets\GoldenRock Baseline - XAUUSD - 1pct.set'
$presetName = 'GoldenRock Baseline - XAUUSD - 1pct.set'

foreach ($path in @($terminal, $source, $presetSource)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required path does not exist: $path" }
}
New-Item -ItemType Directory -Force -Path $expertTarget,$setTarget,$configRoot,$reportRoot,$testerReportRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'GR_GoldenRockEngine.mqh') -Destination $expertTarget -Force
Get-ChildItem -LiteralPath $source -Filter 'GR_*.mq5' | Copy-Item -Destination $expertTarget -Force
Get-ChildItem -LiteralPath $source -Filter 'GR_*.ex5' | Copy-Item -Destination $expertTarget -Force
Copy-Item -LiteralPath $presetSource -Destination (Join-Path $setTarget $presetName) -Force

$cases = @(
    [pscustomobject]@{ Id='01-trend-following'; Label='GR 01 Trend Following Starter'; Expert='GR_01_TrendFollowingStarter_EA'; Period='M15' },
    [pscustomobject]@{ Id='02-breakout-confirmation'; Label='GR 02 Breakout Confirmation'; Expert='GR_02_BreakoutConfirmation_EA'; Period='M15' },
    [pscustomobject]@{ Id='03-liquidity-sweep'; Label='GR 03 Liquidity Sweep Reversal'; Expert='GR_03_LiquiditySweepReversal_EA'; Period='M15' },
    [pscustomobject]@{ Id='04-mtf-institutional'; Label='GR 04 MTF Institutional'; Expert='GR_04_MTF_Institutional_EA'; Period='M15' },
    [pscustomobject]@{ Id='06-smc-bos-ob'; Label='GR 06 SMC BOS OB'; Expert='GR_06_SMC_BOS_OB_EA'; Period='M15' },
    [pscustomobject]@{ Id='07-ict-killzone'; Label='GR 07 ICT Killzone'; Expert='GR_07_ICT_Killzone_EA'; Period='M15' },
    [pscustomobject]@{ Id='08-crt'; Label='GR 08 Candle Range Theory'; Expert='GR_08_CRT_EA'; Period='H1' },
    [pscustomobject]@{ Id='09-snr-ict'; Label='GR 09 SNR ICT'; Expert='GR_09_SNR_ICT_EA'; Period='M15' },
    [pscustomobject]@{ Id='10-smc-liquidity-sweep'; Label='GR 10 SMC Liquidity Sweep'; Expert='GR_10_SMC_LiquiditySweep_EA'; Period='M15' }
)

$manifest = @()
foreach ($case in $cases) {
    $compiled = Join-Path $expertTarget ($case.Expert + '.ex5')
    if (-not (Test-Path -LiteralPath $compiled)) { throw "EA is not compiled: $compiled" }
    $configPath = Join-Path $configRoot ($case.Id + '.ini')
    $relativeReport = 'reports\goldenrock-20260815\' + $case.Id + '.htm'
    $testerReport = Join-Path $tester $relativeReport
    $destinationReport = Join-Path $reportRoot ($case.Id + '.htm')
    $destinationChart = Join-Path $reportRoot ($case.Id + '.png')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=GoldenRock Rebuilt 2026-08-15\$($case.Expert)
ExpertParameters=$presetName
Symbol=XAUUSD
Period=$($case.Period)
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    if (Test-Path -LiteralPath $destinationReport) {
        Write-Host ("SKIP  {0} (saved report already exists)" -f $case.Label) -ForegroundColor DarkYellow
    }
    else {
        Remove-Item -LiteralPath $testerReport -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath ([IO.Path]::ChangeExtension($testerReport,'.png')) -Force -ErrorAction SilentlyContinue
        Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        # Some MT5 builds hand the config to a second terminal process and let
        # the Start-Process handle exit early. The report is the reliable test
        # completion signal, so wait for it instead of trusting that first PID.
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while (-not (Test-Path -LiteralPath $testerReport) -and (Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 2
        }
        if (-not (Test-Path -LiteralPath $testerReport)) {
            Get-Process terminal64 -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -eq $terminal } |
                Stop-Process -Force -ErrorAction SilentlyContinue
            throw "$($case.Label) exceeded $TimeoutSeconds seconds without creating a report."
        }
        Start-Sleep -Seconds 2
        Copy-Item -LiteralPath $testerReport -Destination $destinationReport -Force
        $testerChart = [IO.Path]::ChangeExtension($testerReport,'.png')
        if (Test-Path -LiteralPath $testerChart) { Copy-Item -LiteralPath $testerChart -Destination $destinationChart -Force }
    }
    $manifest += [pscustomobject]@{
        id=$case.Id; label=$case.Label; symbol='XAUUSD'; period=$case.Period;
        from=$FromDate; to=$ToDate; report=$destinationReport; chart=$destinationChart
    }
    Write-Host ("DONE  {0}" -f $case.Label) -ForegroundColor Green
}
$manifestPath = Join-Path $reportRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Manifest: $manifestPath" -ForegroundColor Green
