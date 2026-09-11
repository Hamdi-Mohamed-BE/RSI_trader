$ErrorActionPreference = 'Stop'

$metaEditor = 'C:\Program Files\MetaTrader 5\MetaEditor64.exe'
$packageRoot = $PSScriptRoot
$sources = @(
    'LTA volume profile\EA\LTA_Concepts_EA.mq5',
    'Top Down FVG Liquidity Research 2026-08-27\EA\Top Down FVG Liquidity EA.mq5',
    'POC Fibonacci Volume Profile Research 2026-09-04\EA\POC Fibonacci Volume Profile EA.mq5',
    'ORB Volume Data EA\ORB Volume Data EA.mq5',
    'US100 Selective ORB Research 2026-08-21\EA\US100 Selective ORB Retest EA.mq5',
    'AAA Final EAs\AAA Final Asia Breakout EA\AAA Final Asia Breakout EA.mq5',
    'AAA Final EAs\AAA Final DmC EA\AAA Final DmC EA.mq5',
    'AAA Final EAs\Calyx DMC Fresh Reaction EA\Calyx DMC Fresh Reaction EA.mq5',
    'AAA Final EAs\AAA Final EMA3 EA\AAA Final EMA3 EA.mq5',
    'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.mq5',
    'AAA Final EAs\AAA Final XAU Weakness EA\AAA Final XAU Weakness EA.mq5',
    'Active Portfolio Full Pipeline 2026-09-05\11 Nasdaq 5M Candle Momentum\EA\Nasdaq 5M Candle Momentum Audit EA.mq5',
    'Elliott Wave Research 2026-09-05\EA\Elliott Wave 123 EA.mq5',
    'London Open FX Momentum Research 2026-09-08\Pipeline\EA\Calyx London Open FX Momentum Pipeline EA.mq5',
    'Month End Institutional Flow Research 2026-09-06\EA\Calyx Month End Flow EA.mq5',
    'Nasdaq Overnight Negative Day EA\Nasdaq Overnight Negative Day EA.mq5',
    'Regime Switch Overlay Research 2026-09-06\EA\Calyx XAU Regime Switch EA.mq5',
    'RSI VWAP Research 2026-09-02\EA\RSI VWAP Managed EA.mq5',
    'Sell Nasdaq 15min Research 2026-09-08\Dynamic Exit Research\EA\Sell Nasdaq 15min Dynamic Exit Research EA.mq5',
    'Sell Nasdaq 15min Research 2026-09-08\EA\Sell Nasdaq 15min EA.mq5',
    'Slow Multi Asset Trend Research 2026-09-06\EA\Calyx Slow Trend EA.mq5',
    'Trend Progression Research 2026-09-02\EA\Trend Progression EA.mq5',
    'XAU Squeeze Momentum Research 2026-09-10\EA\Calyx XAU Squeeze Momentum Research EA.mq5',
    '..\..\AI news\mt5\GoldNewsV9EA.mq5'
)

$results = foreach ($relativeSource in $sources) {
    $source = [IO.Path]::GetFullPath((Join-Path $packageRoot $relativeSource))
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing source: $source"
    }
    $log = [IO.Path]::ChangeExtension($source, '.risk-policy.compile.log')
    $process = Start-Process -FilePath $metaEditor `
        -ArgumentList ('/compile:"{0}"' -f $source), ('/log:"{0}"' -f $log) `
        -Wait -WindowStyle Hidden -PassThru
    $logText = if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Raw } else { '' }
    $summary = $logText -split "`r?`n" | Where-Object { $_ -match 'Result:' } | Select-Object -Last 1
    [pscustomobject]@{
        EA = [IO.Path]::GetFileName($source)
        ExitCode = $process.ExitCode
        Summary = $summary
        Log = $log
    }
}

$failed = @($results | Where-Object { $_.Summary -notmatch '0 errors' })
$results | Format-Table -AutoSize
if ($failed.Count -gt 0) {
    throw "$($failed.Count) active EA compile(s) failed."
}

# MetaEditor commonly returns process code 1 even when its own compile log says
# there are zero errors. The verified log summaries above are authoritative.
exit 0
