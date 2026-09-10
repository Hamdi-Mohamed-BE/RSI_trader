[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [ValidateSet('AUTO', '100K', '900')]
    [string]$AccountProfile = 'AUTO',
    [ValidateRange(0.1, 5.0)]
    [double]$AdaptiveRiskPercent = 1.0,
    [ValidateSet('STANDARD', 'SAFE')]
    [string]$SafetyMode = 'STANDARD',
    [ValidateSet('DEFAULT', 'PERCENT', 'FIXED_USD')]
    [string]$RiskMode = 'DEFAULT',
    [double]$RiskValue = 0.0,
    [switch]$UseRecommendedSelections,
    [switch]$UseAdaptiveProfile,
    [switch]$ValidateOnly,
    [switch]$PreflightOnly,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PackageRoot = Split-Path -Parent $PSScriptRoot
$IsAdaptiveAccount = $AccountProfile -eq 'AUTO'
$IsSmallAccount = $AccountProfile -eq '900'
$IsFullSafe = $SafetyMode -eq 'SAFE'
$UsesDynamicRisk = $RiskMode -ne 'DEFAULT'
$EffectiveAdaptiveRiskPercent = $AdaptiveRiskPercent
$RequestedRiskMoney = 0.0
$ProfileName = if ($UseAdaptiveProfile) {
    if ($IsAdaptiveAccount) { 'Calyx ANY BALANCE - RECOMMENDED ADAPTIVE' } elseif ($IsSmallAccount) { 'Calyx 900 - RECOMMENDED ADAPTIVE' } else { 'Calyx 100K - RECOMMENDED ADAPTIVE' }
} elseif ($UseRecommendedSelections) {
    if ($IsAdaptiveAccount) { 'BM Trading ANY BALANCE - BEST RECOMMENDED' } elseif ($IsSmallAccount) { 'BM Trading 900 - BEST RECOMMENDED' } else { 'BM Trading 100K - BEST RECOMMENDED' }
} elseif ($IsFullSafe) {
    if ($IsAdaptiveAccount) { 'BM Trading ANY BALANCE - FULL SAFE' } elseif ($IsSmallAccount) { 'BM Trading 900 - FULL SAFE' } else { 'BM Trading 100K - FULL SAFE' }
} else {
    if ($IsAdaptiveAccount) { 'BM Trading ANY BALANCE - AUTO' } elseif ($IsSmallAccount) { 'BM Trading 900 - AUTO' } else { 'BM Trading 100K - AUTO' }
}
$ExpertFolderName = $ProfileName
$ProbePath = Join-Path $PSScriptRoot 'Probe-MT5.py'
$GoldNewsRoot = [IO.Path]::GetFullPath((Join-Path $PackageRoot '..\..\AI news'))
$GoldNewsRuntimeInstaller = Join-Path $GoldNewsRoot 'Install-GoldNewsV9EA.ps1'
$Unicode = New-Object System.Text.UnicodeEncoding($false, $true)

function Write-Stage([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Stop-WithMessage([string]$Message, [int]$Code = 1) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit $Code
}

function Get-PortfolioItems {
    # Locked selected portfolio. Each EA owns its selected exit mode:
    # Each strategy keeps its selected exit. The three News Pulse instances
    # use News Pulse v2.13, its native 60-second lifecycle and source-locked
    # 0.75% risk per pending side (1.50% maximum planned event exposure).
    # Live events come from MT5's USD calendar; Strategy Tester schedules are
    # generated from FXMacroData and fail closed outside verified coverage.
    # Gold News V9 uses the local v9 prediction runtime and follows the risk
    # selected for the rest of the non-News-Pulse portfolio.
    # No portfolio-wide session overlay is applied.
    # Risk defaults to 1% planned per EA trade except News Pulse, whose hard
    # event cap cannot be changed by the portfolio risk prompt.
    $items = @(
        [pscustomobject]@{
            Label = 'LTA Volume Profile'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 15; Expert = 'LTA_Concepts_EA.ex5'
            ExpertSource = 'LTA volume profile\EA\LTA_Concepts_EA.ex5'; RecommendedSafe = $true
            SetSource = 'Selected Portfolio Settings 2026-09-01\01 LTA Volume Profile - CURRENT - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0
        },
        [pscustomobject]@{
            Label = 'BTC Top Down FVG Liquidity'; Canonical = 'BTCUSD'; Aliases = @('BTCUSD', 'BITCOIN', 'BTC')
            Period = 15; Expert = 'Top Down FVG Liquidity EA.ex5'
            ExpertSource = 'Top Down FVG Liquidity Research 2026-08-27\EA\Top Down FVG Liquidity EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\02 BTC Top Down FVG Liquidity - CURRENT - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; OptionalSymbol = $true
        },
        [pscustomobject]@{
            Label = 'BTC POC Fibonacci'; Canonical = 'BTCUSD'; Aliases = @('BTCUSD', 'BITCOIN', 'BTC')
            Period = 15; Expert = 'POC Fibonacci Volume Profile EA.ex5'
            ExpertSource = 'POC Fibonacci Volume Profile Research 2026-09-04\EA\POC Fibonacci Volume Profile EA.ex5'
            SetSource = 'POC Fibonacci Volume Profile Research 2026-09-04\Sets\POCFib-btcusd--optimized--locked.set'; SmallDynamicRisk = $false; PercentRisk = $true; OptionalSymbol = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'ETH Top Down FVG Liquidity'; Canonical = 'ETHUSD'; Aliases = @('ETHUSD', 'ETHEREUM', 'ETH')
            Period = 15; Expert = 'Top Down FVG Liquidity EA.ex5'
            ExpertSource = 'Top Down FVG Liquidity Research 2026-08-27\EA\Top Down FVG Liquidity EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\03 ETH Top Down FVG Liquidity - DYNAMIC 50-20 - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; OptionalSymbol = $true
        },
        [pscustomobject]@{
            Label = 'ORB Volume Profile'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 5; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true
        },
        [pscustomobject]@{
            Label = 'ORB Volume Profile Volume Confirmed'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 5; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU ORB New York M30'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 30; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\14 XAU ORB New York M30 - LOCKED STANDALONE.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU ORB London NY Overlap M30'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 30; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'US100 ORB New York M30'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 30; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\16 US100 ORB New York M30 - LOCKED STANDALONE.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'US100 H1 ORB 13UTC'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 15; Expert = 'ORB Volume Data EA.ex5'
            ExpertSource = 'ORB Volume Data EA\ORB Volume Data EA.ex5'
            SetSource = 'ORB H1 Range Research 2026-09-05\Sets\USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'US100 Selective ORB V3'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 5; Expert = 'US100 Selective ORB Retest EA.ex5'
            ExpertSource = 'US100 Selective ORB Research 2026-08-21\EA\US100 Selective ORB Retest EA.ex5'
            SetSource = 'US100 Selective ORB Research 2026-08-21\Sets\BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'AAA Final Asia Breakout'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'AAA Final Asia Breakout EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final Asia Breakout EA\AAA Final Asia Breakout EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\06 Asia Breakout - DYNAMIC 50-20 - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true
        },
        [pscustomobject]@{
            Label = 'DMC Current XAU'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'AAA Final DmC EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final DmC EA\AAA Final DmC EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\07 DmC - ASIA 3R - DYNAMIC 50-20.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'DMC Fresh Reaction XAU'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'Calyx DMC Fresh Reaction EA.ex5'
            ExpertSource = 'AAA Final EAs\Calyx DMC Fresh Reaction EA\Calyx DMC Fresh Reaction EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'DMC Fresh Reaction US100'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 60; Expert = 'Calyx DMC Fresh Reaction EA.ex5'
            ExpertSource = 'AAA Final EAs\Calyx DMC Fresh Reaction EA\Calyx DMC Fresh Reaction EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'AAA Final EMA3'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 240; Expert = 'AAA Final EMA3 EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final EMA3 EA\AAA Final EMA3 EA.ex5'; RecommendedSafe = $true
            SetSource = 'Selected Portfolio Settings 2026-09-01\08 EMA3 - H4 PIVOT 1.7R - DYNAMIC 60-20 ONLY.set'; SmallDynamicRisk = $false; PercentRisk = $true
        },
        [pscustomobject]@{
            Label = 'AAA Final XAU Weakness'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 30; Expert = 'AAA Final XAU Weakness EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final XAU Weakness EA\AAA Final XAU Weakness EA.ex5'; RecommendedSafe = $true
            SetSource = 'Selected Portfolio Settings 2026-09-01\09 XAU Weakness - M30 STRUCTURE 4R - DYNAMIC 50-20.set'; SmallDynamicRisk = $false; PercentRisk = $true
        },
        [pscustomobject]@{
            Label = 'Nasdaq Overnight'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 1; Expert = 'Nasdaq Overnight Negative Day EA.ex5'
            ExpertSource = 'Nasdaq Overnight Negative Day EA\Nasdaq Overnight Negative Day EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\10 Nasdaq Overnight - CURRENT - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'Nasdaq 5M Candle Momentum'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 5; Expert = 'Nasdaq 5M Open EMA ATR EA.ex5'
            ExpertSource = 'Active Portfolio Full Pipeline 2026-09-05\11 Nasdaq 5M Candle Momentum\EA\Nasdaq 5M Candle Momentum Audit EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R - HARD 1PCT.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true
        },
        [pscustomobject]@{
            Label = 'Sell Nasdaq 15min'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 15; Expert = 'Sell Nasdaq 15min EA.ex5'
            ExpertSource = 'Sell Nasdaq 15min Research 2026-09-08\EA\Sell Nasdaq 15min EA.ex5'
            SetSource = 'Sell Nasdaq 15min Research 2026-09-08\Sets\Sell Nasdaq 15min - selected research - 1pct.set'
            SafeSetSource = 'Sell Nasdaq 15min Research 2026-09-08\Sets\Sell Nasdaq 15min - safe London 600-1000 - 1pct.set'
            RecommendedExpertSource = 'Sell Nasdaq 15min Research 2026-09-08\Dynamic Exit Research\EA\Sell Nasdaq 15min Dynamic Exit Research EA.ex5'
            RecommendedSetSource = 'Sell Nasdaq 15min Research 2026-09-08\Dynamic Exit Research\Sets\Sell Nasdaq 15min - london-safe dynamic exit candidate - 1pct.set'; RecommendedDynamic = $true
            SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true; SupportsSafeFilter = $true
        },
        [pscustomobject]@{
            Label = 'USDJPY London Open Momentum'; Canonical = 'USDJPY'; Aliases = @('USDJPY')
            Period = 15; Expert = 'Calyx London Open FX Momentum Pipeline EA.ex5'
            ExpertSource = 'London Open FX Momentum Research 2026-09-08\Pipeline\EA\Calyx London Open FX Momentum Pipeline EA.ex5'
            SetSource = 'London Open FX Momentum Research 2026-09-08\Pipeline\Sets\London Open FX Momentum - USDJPY - pipeline selected - 1pct.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU Squeeze Momentum Standard'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'Calyx XAU Squeeze Momentum Research EA.ex5'
            ExpertSource = 'XAU Squeeze Momentum Research 2026-09-10\EA\Calyx XAU Squeeze Momentum Research EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\23 XAU Squeeze Momentum Standard - ATR3P5 1P5R - 1PCT.set'
            SafeSetSource = 'Selected Portfolio Settings 2026-09-01\23S XAU Squeeze Momentum Safe - ATR3P5 1P5R - 1PCT.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true; SupportsSafeFilter = $true; RecommendedSafe = $true
        },
        [pscustomobject]@{
            Label = 'News Pulse XAU'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 1; Expert = 'AAA Final News Pulse EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'; SmallDynamicRisk = $false; PercentRisk = $false; FixedPercentRisk = 0.75; LockRisk = $true; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'Gold News V9 Direction'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 1; Expert = 'GoldNewsV9EA.ex5'
            ExpertSource = '..\..\AI news\mt5\GoldNewsV9EA.ex5'
            SetSource = '..\..\AI news\mt5\GoldNewsV9EA-Auto.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'News Pulse XAG'; Canonical = 'XAGUSD'; Aliases = @('XAGUSD', 'SILVER', 'XAG')
            Period = 1; Expert = 'AAA Final News Pulse EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set'; SmallDynamicRisk = $false; PercentRisk = $false; FixedPercentRisk = 0.75; LockRisk = $true; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'News Pulse EURUSD'; Canonical = 'EURUSD'; Aliases = @('EURUSD')
            Period = 1; Expert = 'AAA Final News Pulse EA.ex5'
            ExpertSource = 'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\12C News Pulse EURUSD Two Sided - HARD 1.5 TOTAL.set'; SmallDynamicRisk = $false; PercentRisk = $false; FixedPercentRisk = 0.75; LockRisk = $true; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU RSI VWAP'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 60; Expert = 'RSI VWAP Managed EA.ex5'
            ExpertSource = 'RSI VWAP Research 2026-09-02\EA\RSI VWAP Managed EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\13 XAU RSI VWAP - CURRENT - ALL DAY.set'; SmallDynamicRisk = $false; PercentRisk = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU Trend Progression'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 240; Expert = 'Trend Progression EA.ex5'
            ExpertSource = 'Trend Progression Research 2026-09-02\EA\Trend Progression EA.ex5'
            SetSource = 'Trend Progression Research 2026-09-02\Sets\TrendProgression-xauusd--h4--optimized--locked.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU Elliott Wave 1-2-3'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 240; Expert = 'Elliott Wave 123 EA.ex5'
            ExpertSource = 'Elliott Wave Research 2026-09-05\EA\Elliott Wave 123 EA.ex5'
            SetSource = 'Elliott Wave Research 2026-09-05\Sets\ElliottWave-xauusd--h4--optimized--locked.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU Slow Trend'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 240; Expert = 'Calyx Slow Trend EA.ex5'
            ExpertSource = 'Slow Multi Asset Trend Research 2026-09-06\EA\Calyx Slow Trend EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\17 XAU Slow Trend H4 - LOCKED 6R - HARD 1PCT.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'XAU Regime Switch'; Canonical = 'XAUUSD'; Aliases = @('XAUUSD', 'GOLD')
            Period = 5; Expert = 'Calyx XAU Regime Switch EA.ex5'
            ExpertSource = 'Regime Switch Overlay Research 2026-09-06\EA\Calyx XAU Regime Switch EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\20 XAU Regime Switch - DEMO - HARD 1PCT.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; ForceEnable = $true; SupportsSafeFilter = $false
        },
        [pscustomobject]@{
            Label = 'US100 Month End Flow'; Canonical = 'USTEC'; Aliases = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ')
            Period = 30; Expert = 'Calyx Month End Flow EA.ex5'
            ExpertSource = 'Month End Institutional Flow Research 2026-09-06\EA\Calyx Month End Flow EA.ex5'
            SetSource = 'Selected Portfolio Settings 2026-09-01\19 US100 Month End Flow M30 - FIRST3 NY - LOCKED 2P5R - HARD 1PCT.set'; SmallDynamicRisk = $false; PercentRisk = $true; FixedPercentRisk = 1.0; SupportsSafeFilter = $false
        }
    )

    foreach ($item in $items) {
        if (-not $item.PSObject.Properties['FixedPercentRisk']) {
            $item | Add-Member -NotePropertyName FixedPercentRisk -NotePropertyValue 0.0
        }
        if (-not $item.PSObject.Properties['VolumeRiskMoney']) {
            $item | Add-Member -NotePropertyName VolumeRiskMoney -NotePropertyValue $false
        }
        if (-not $item.PSObject.Properties['ForceEnable']) {
            $item | Add-Member -NotePropertyName ForceEnable -NotePropertyValue $false
        }
        if (-not $item.PSObject.Properties['OptionalSymbol']) {
            $item | Add-Member -NotePropertyName OptionalSymbol -NotePropertyValue $false
        }
        if (-not $item.PSObject.Properties['SupportsSafeFilter']) {
            $item | Add-Member -NotePropertyName SupportsSafeFilter -NotePropertyValue $true
        }
        if (-not $item.PSObject.Properties['SafeSetSource']) {
            $item | Add-Member -NotePropertyName SafeSetSource -NotePropertyValue ''
        }
        if (-not $item.PSObject.Properties['RecommendedSafe']) {
            $item | Add-Member -NotePropertyName RecommendedSafe -NotePropertyValue $false
        }
        if (-not $item.PSObject.Properties['RecommendedDynamic']) {
            $item | Add-Member -NotePropertyName RecommendedDynamic -NotePropertyValue $false
        }
        if (-not $item.PSObject.Properties['RecommendedExpertSource']) {
            $item | Add-Member -NotePropertyName RecommendedExpertSource -NotePropertyValue ''
        }
        if (-not $item.PSObject.Properties['RecommendedSetSource']) {
            $item | Add-Member -NotePropertyName RecommendedSetSource -NotePropertyValue ''
        }
        if (-not $item.PSObject.Properties['LockRisk']) {
            $item | Add-Member -NotePropertyName LockRisk -NotePropertyValue $false
        }
        $adaptiveBaseMultiplier = if ($UseAdaptiveProfile -and $item.Label -eq 'Nasdaq 5M Candle Momentum') { 0.25 } else { 1.0 }
        $item | Add-Member -NotePropertyName AdaptiveBaseMultiplier -NotePropertyValue $adaptiveBaseMultiplier
        $safeByDesign = [bool]$UseRecommendedSelections -and [bool]$item.RecommendedSafe
        $dynamicByDesign = [bool]$UseRecommendedSelections -and -not $IsFullSafe -and -not $safeByDesign -and [bool]$item.RecommendedDynamic -and [bool]$item.RecommendedSetSource
        $usesDedicatedSafePreset = [bool]$item.SafeSetSource -and ($IsFullSafe -or $safeByDesign)
        $selectedSetSource = if ($usesDedicatedSafePreset) { [string]$item.SafeSetSource } elseif ($dynamicByDesign) { [string]$item.RecommendedSetSource } else { [string]$item.SetSource }
        $selectedExpertSource = if ($dynamicByDesign -and [bool]$item.RecommendedExpertSource) { [string]$item.RecommendedExpertSource } else { [string]$item.ExpertSource }
        $item | Add-Member -NotePropertyName UsesDedicatedSafePreset -NotePropertyValue $usesDedicatedSafePreset
        $item | Add-Member -NotePropertyName SafeByDesign -NotePropertyValue $safeByDesign
        $item | Add-Member -NotePropertyName DynamicByDesign -NotePropertyValue $dynamicByDesign
        $item | Add-Member -NotePropertyName ExpertFullPath -NotePropertyValue (Join-Path $PackageRoot $selectedExpertSource)
        $item | Add-Member -NotePropertyName SetFullPath -NotePropertyValue (Join-Path $PackageRoot $selectedSetSource)
    }
    return @($items)
}

function Get-Mt5Candidates {
    $result = @()
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $running = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -and
        -not ([IO.Path]::GetFullPath($_.ExecutablePath).StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase))
    })

    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if (Test-Path -LiteralPath $terminalRoot) {
        foreach ($originFile in @(Get-ChildItem -LiteralPath $terminalRoot -Recurse -Filter origin.txt -File -ErrorAction SilentlyContinue)) {
            $installRoot = (Get-Content -LiteralPath $originFile.FullName -Raw).Trim()
            $installRootFull = [IO.Path]::GetFullPath($installRoot)
            if ($installRootFull.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
            foreach ($exeName in @('terminal64.exe', 'terminal.exe')) {
                $exe = Join-Path $installRoot $exeName
                if (Test-Path -LiteralPath $exe) {
                    $matches = @($running | Where-Object { $_.ExecutablePath -ieq $exe })
                    $result += [pscustomobject]@{
                        Path = $exe
                        DataRoot = $originFile.DirectoryName
                        Running = ($matches.Count -gt 0)
                        ProcessIds = @($matches | ForEach-Object { $_.ProcessId })
                    }
                    break
                }
            }
        }
    }

    foreach ($process in $running) {
        if (-not @($result | Where-Object { $_.Path -ieq $process.ExecutablePath })) {
            $result += [pscustomobject]@{
                Path = $process.ExecutablePath
                DataRoot = ''
                Running = $true
                ProcessIds = @($process.ProcessId)
            }
        }
    }

    return @($result | Sort-Object -Property @{Expression = 'Running'; Descending = $true}, Path -Unique)
}

function Select-Mt5Candidate([object[]]$Candidates) {
    if ($TargetTerminal) {
        $requested = [IO.Path]::GetFullPath($TargetTerminal)
        $candidate = @($Candidates | Where-Object { [IO.Path]::GetFullPath($_.Path) -ieq $requested }) | Select-Object -First 1
        if (-not $candidate) {
            if (-not (Test-Path -LiteralPath $requested)) {
                Stop-WithMessage "The requested MT5 terminal does not exist: $requested"
            }
            return [pscustomobject]@{ Path = $requested; DataRoot = ''; Running = $false; ProcessIds = @() }
        }
        return $candidate
    }

    $running = @($Candidates | Where-Object { $_.Running })
    if ($running.Count -eq 1) {
        return $running[0]
    }

    $choices = if ($running.Count -gt 1) { $running } else { $Candidates }
    if ($choices.Count -eq 0) {
        Stop-WithMessage 'No installed MetaTrader 5 terminal was found.'
    }
    if ($choices.Count -eq 1) {
        return $choices[0]
    }

    Write-Host 'Choose the MT5 installation that contains the account you want to use:' -ForegroundColor Yellow
    for ($i = 0; $i -lt $choices.Count; $i++) {
        $state = if ($choices[$i].Running) { 'RUNNING' } else { 'closed' }
        Write-Host ('  [{0}] {1} ({2})' -f ($i + 1), $choices[$i].Path, $state)
    }
    $answer = Read-Host 'Enter number'
    $number = 0
    if (-not [int]::TryParse($answer, [ref]$number) -or $number -lt 1 -or $number -gt $choices.Count) {
        Stop-WithMessage 'No valid MT5 installation was selected.'
    }
    return $choices[$number - 1]
}

function Normalize-Symbol([string]$Name) {
    return ($Name.ToUpperInvariant() -replace '[^A-Z0-9]', '')
}

function Find-BrokerSymbol([object[]]$Symbols, [string[]]$Aliases, [switch]$AllowFutures) {
    $best = $null
    $bestScore = [int]::MaxValue
    foreach ($symbol in $Symbols) {
        if ([int]$symbol.trade_mode -eq 0) { continue }
        if (-not $AllowFutures -and [string]$symbol.path -match '(?i)future') { continue }
        $normalized = Normalize-Symbol ([string]$symbol.name)
        for ($aliasIndex = 0; $aliasIndex -lt $Aliases.Count; $aliasIndex++) {
            $alias = Normalize-Symbol $Aliases[$aliasIndex]
            $matchScore = $null
            if ($normalized -eq $alias) {
                $matchScore = 0
            } elseif ($normalized.StartsWith($alias) -or $normalized.EndsWith($alias)) {
                $matchScore = 100
            } elseif ($normalized.Contains($alias)) {
                $matchScore = 200
            }
            if ($null -eq $matchScore) { continue }
            $visibilityPenalty = if ([bool]$symbol.visible) { 0 } else { 5 }
            $score = ($matchScore * 1000) + ($aliasIndex * 10) + $visibilityPenalty + ($normalized.Length - $alias.Length)
            if ($score -lt $bestScore) {
                $best = $symbol
                $bestScore = $score
            }
        }
    }
    return $best
}

function Read-SetInputs([string]$Path) {
    $result = New-Object System.Collections.Specialized.OrderedDictionary
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith(';') -or $trimmed.StartsWith('#')) { continue }
        $equals = $trimmed.IndexOf('=')
        if ($equals -lt 1) { continue }
        $key = $trimmed.Substring(0, $equals).Trim()
        $rawValue = $trimmed.Substring($equals + 1)
        $separator = $rawValue.IndexOf('||')
        $value = if ($separator -ge 0) { $rawValue.Substring(0, $separator) } else { $rawValue }
        $result[$key] = $value
    }
    return $result
}

    function Get-EffectiveInputs([object]$Item) {
    $inputs = Read-SetInputs $Item.SetFullPath
    if ([bool]$Item.ForceEnable -and $inputs.Contains('InpEnableTrading')) {
        $inputs['InpEnableTrading'] = 'true'
    }
    if ($IsAdaptiveAccount) {
        $riskAmount = ([double]$Item.EffectiveRisk).ToString('0.00', [Globalization.CultureInfo]::InvariantCulture)
        $riskPercent = ([double]$Item.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        if ($inputs.Contains('RiskMoney')) { $inputs['RiskMoney'] = $riskAmount }
        if ($inputs.Contains('InpRiskAmount')) { $inputs['InpRiskAmount'] = $riskAmount }
        if ([bool]$Item.VolumeRiskMoney) {
            if ($inputs.Contains('VolumeMode')) { $inputs['VolumeMode'] = '1' }
            if ($inputs.Contains('Volume')) { $inputs['Volume'] = $riskAmount }
        }
        if ([bool]$Item.PercentRisk -and $inputs.Contains('InpRiskPercent')) { $inputs['InpRiskPercent'] = $riskPercent }
        if ([bool]$Item.SmallDynamicRisk) {
            $inputs['Volume'] = '0'
            $inputs['Lots'] = ([double]$Item.EffectiveLot).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['RiskPercent'] = $riskPercent
            $inputs['SlCalcMode'] = '1'
            $inputs['SlValue'] = ([double]$Item.EffectiveStopPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['Commentary'] = ('BM-AUTO-{0}PCT-HARD-SL' -f $riskPercent)
        }
    } elseif ($IsSmallAccount) {
        if ($inputs.Contains('RiskMoney')) { $inputs['RiskMoney'] = '40' }
        if ($inputs.Contains('InpRiskAmount')) { $inputs['InpRiskAmount'] = '40' }
        if ([bool]$Item.VolumeRiskMoney) {
            if ($inputs.Contains('VolumeMode')) { $inputs['VolumeMode'] = '1' }
            if ($inputs.Contains('Volume')) { $inputs['Volume'] = '40' }
        }
        if ([bool]$Item.SmallDynamicRisk) {
            $inputs['Volume'] = '0'
            $inputs['Lots'] = ([double]$Item.EffectiveLot).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['RiskPercent'] = '4.44444444'
            $inputs['SlCalcMode'] = '1'
            $inputs['SlValue'] = ([double]$Item.EffectiveStopPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
            $inputs['Commentary'] = 'BM900-DYNAMIC-40USD-HARD-SL'
        }
    }
    if ([double]$Item.FixedPercentRisk -gt 0 -and (-not $UsesDynamicRisk -or [bool]$Item.LockRisk)) {
        $fixedRisk = ([double]$Item.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        foreach ($key in @('InpRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent', 'InpAbsoluteRiskCapPercent')) {
            if ($inputs.Contains($key)) { $inputs[$key] = $fixedRisk }
        }
    }
    if ($UsesDynamicRisk -and -not [bool]$Item.LockRisk) {
        $dynamicPercent = ([double]$Item.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        $dynamicMoney = ([double]$Item.EffectiveRisk).ToString('0.00', [Globalization.CultureInfo]::InvariantCulture)
        foreach ($key in @('InpRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent', 'InpAbsoluteRiskCapPercent', 'RiskPercent')) {
            if ($inputs.Contains($key)) { $inputs[$key] = $dynamicPercent }
        }
        foreach ($key in @('RiskMoney', 'InpRiskAmount')) {
            if ($inputs.Contains($key)) { $inputs[$key] = $dynamicMoney }
        }
        if ($inputs.Contains('InpRiskMode')) {
            $inputs['InpRiskMode'] = if ($RiskMode -eq 'FIXED_USD') { '1' } else { '0' }
        }
        if ($inputs.Contains('InpFixedRiskMoney')) { $inputs['InpFixedRiskMoney'] = $dynamicMoney }
        if ([bool]$Item.VolumeRiskMoney) {
            if ($inputs.Contains('VolumeMode')) { $inputs['VolumeMode'] = '1' }
            if ($inputs.Contains('Volume')) { $inputs['Volume'] = $dynamicMoney }
        }
    }
    if (($IsFullSafe -or [bool]$Item.SafeByDesign) -and [bool]$Item.SupportsSafeFilter -and -not [bool]$Item.UsesDedicatedSafePreset) {
        $inputs['InpUseMarkovRegimeFilter'] = 'true'
        $inputs['InpMarkovReturnWindow'] = '40'
        $inputs['InpMarkovThreshold'] = '0.05'
        $inputs['InpMarkovSignalGate'] = '0.05'
        $inputs['InpMarkovMinLabels'] = '252'
        $inputs['InpMarkovHistoryBars'] = '2600'
    }
    return $inputs
}

function Assert-EffectiveRiskInputs([object[]]$Items) {
    $percentKeys = @(
        'InpRiskPercent',
        'InpMomentumRiskPercent',
        'InpContrarianRiskPercent',
        'InpAbsoluteRiskCapPercent',
        'RiskPercent'
    )
    foreach ($item in $Items) {
        $inputs = Get-EffectiveInputs $item
        $presentPercentKeys = @($percentKeys | Where-Object { $inputs.Contains($_) })
        $isNews = $item.Label -like 'News Pulse *'
        if ($presentPercentKeys.Count -eq 0 -and -not $inputs.Contains('RiskMoney') -and -not $inputs.Contains('InpRiskAmount')) {
            Stop-WithMessage "Risk audit failed for $($item.Label): its selected SET has no supported risk input."
        }

        $expectedPercent = [double]$item.EffectiveRiskPercent
        foreach ($key in $presentPercentKeys) {
            $actual = 0.0
            if (-not [double]::TryParse([string]$inputs[$key], [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$actual)) {
                Stop-WithMessage "Risk audit failed for $($item.Label): $key is not numeric."
            }
            if ([Math]::Abs($actual - $expectedPercent) -gt 0.0000001) {
                Stop-WithMessage ("Risk audit failed for {0}: {1} is {2}, expected {3}." -f $item.Label, $key, $actual, $expectedPercent)
            }
        }

        if ($isNews -and -not [bool]$item.LockRisk) {
            Stop-WithMessage "Risk audit failed for $($item.Label): News Pulse must remain locked at 0.75% per pending stop."
        }
        if (-not $isNews -and [bool]$item.LockRisk) {
            Stop-WithMessage "Risk audit failed for $($item.Label): a non-News EA must follow the user's selected risk."
        }
    }
    $modeText = if ($UsesDynamicRisk) { ('selected {0:N4}%' -f $EffectiveAdaptiveRiskPercent) } else { 'default 1.0000%' }
    $adaptiveText = if ($UseAdaptiveProfile) { '; Nasdaq 5M is correctly reduced to 0.25x' } else { '' }
    Write-Host ("Risk audit passed: every non-News EA uses {0}{1}; all News Pulse entries remain 0.7500% per pending stop." -f $modeText, $adaptiveText) -ForegroundColor Green
}

function New-ChartText([object]$Item, [string]$Symbol, [long]$Id, [int]$Index) {
    $inputs = Get-EffectiveInputs $Item
    $inputLines = @($inputs.Keys | ForEach-Object { '{0}={1}' -f $_, $inputs[$_] }) -join "`r`n"
    $columns = 4
    $width = 480
    $height = 280
    $left = ($Index % $columns) * $width
    $top = [Math]::Floor($Index / $columns) * $height
    $right = $left + $width
    $bottom = $top + $height
    $expertPath = 'Experts\' + $ExpertFolderName + '\' + $Item.Expert
    $expertName = [IO.Path]::GetFileNameWithoutExtension($Item.Expert)
    $periodType = if ($Item.Period -lt 60) { 0 } elseif ($Item.Period -lt 1440) { 1 } else { 2 }
    $periodSize = if ($periodType -eq 0) { $Item.Period } elseif ($periodType -eq 1) { [int]($Item.Period / 60) } else { [int]($Item.Period / 1440) }

    return @"
<chart>
id=$Id
symbol=$Symbol
description=$Symbol
period_type=$periodType
period_size=$periodSize
digits=5
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=0.000000
scale=8
mode=1
fore=0
grid=1
volume=0
scroll=1
shift=1
shift_size=20.000000
fixed_pos=0.000000
ticker=1
ohlc=1
one_click=0
one_click_btn=1
bidline=1
askline=0
lastline=0
days=1
descriptions=0
tradelines=1
tradehistory=1
window_left=$left
window_top=$top
window_right=$right
window_bottom=$bottom
window_type=1
floating=0
floating_left=0
floating_top=0
floating_right=0
floating_bottom=0
floating_type=1
floating_toolbar=1
floating_tbstate=
background_color=0
foreground_color=16777215
barup_color=65280
bardown_color=255
bullcandle_color=65280
bearcandle_color=255
chartline_color=65280
volumes_color=5592405
grid_color=2236962
bidline_color=8421504
askline_color=255
lastline_color=8421504
stops_color=255
windows_total=1

<expert>
name=$expertName
path=$expertPath
expertmode=1
<inputs>
$inputLines
</inputs>
</expert>

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1
</indicator>
</window>
</chart>
"@
}

function Test-ManagedProfile([string]$ProfilePath, [object[]]$ExpectedPortfolio, [string]$Stage) {
    $chartFiles = @(Get-ChildItem -LiteralPath $ProfilePath -Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object Name)
    if ($chartFiles.Count -ne $ExpectedPortfolio.Count) {
        Stop-WithMessage ("{0}: profile contains {1} chart files, but {2} were expected." -f $Stage, $chartFiles.Count, $ExpectedPortfolio.Count)
    }

    $problems = [Collections.Generic.List[string]]::new()
    for ($index = 0; $index -lt $ExpectedPortfolio.Count; $index++) {
        $item = $ExpectedPortfolio[$index]
        $chartName = 'chart{0:D2}.chr' -f ($index + 1)
        $chartPath = Join-Path $ProfilePath $chartName
        if (-not (Test-Path -LiteralPath $chartPath)) {
            [void]$problems.Add("$chartName is missing")
            continue
        }
        $text = Get-Content -LiteralPath $chartPath -Raw
        $expectedName = [IO.Path]::GetFileNameWithoutExtension([string]$item.Expert)
        $expectedPath = 'Experts\' + $ExpertFolderName + '\' + [string]$item.Expert
        $expectedPeriodType = if ($item.Period -lt 60) { 0 } elseif ($item.Period -lt 1440) { 1 } else { 2 }
        $expectedPeriodSize = if ($expectedPeriodType -eq 0) { $item.Period } elseif ($expectedPeriodType -eq 1) { [int]($item.Period / 60) } else { [int]($item.Period / 1440) }
        $checks = @(
            @{ Label = 'symbol'; Token = "symbol=$($item.BrokerSymbol)" },
            @{ Label = 'period type'; Token = "period_type=$expectedPeriodType" },
            @{ Label = 'period'; Token = "period_size=$expectedPeriodSize" },
            @{ Label = 'EA name'; Token = "name=$expectedName" },
            @{ Label = 'EA path'; Token = "path=$expectedPath" },
            @{ Label = 'enabled expert mode'; Token = 'expertmode=1' },
            @{ Label = 'expert attachment'; Token = '<expert>' }
        )
        foreach ($check in $checks) {
            if (-not $text.Contains([string]$check.Token)) {
                [void]$problems.Add(("{0}: wrong or missing {1} (expected '{2}')" -f $chartName, $check.Label, $check.Token))
            }
        }
    }
    if ($problems.Count -gt 0) {
        Stop-WithMessage ("$Stage profile verification failed:`n - " + ($problems -join "`n - "))
    }
    Write-Host ("{0}: verified all {1} exact symbol, timeframe and EA attachments." -f $Stage, $ExpectedPortfolio.Count) -ForegroundColor Green
}

function Set-IniValue([string]$Path, [string]$Section, [string]$Key, [string]$Value) {
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -LiteralPath $Path) { [void]$lines.Add($line) }
    $sectionLine = -1
    $nextSectionLine = $lines.Count
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -ieq "[$Section]") {
            $sectionLine = $i
            for ($j = $i + 1; $j -lt $lines.Count; $j++) {
                if ($lines[$j].Trim().StartsWith('[')) { $nextSectionLine = $j; break }
            }
            break
        }
    }
    if ($sectionLine -lt 0) {
        [void]$lines.Add("[$Section]")
        [void]$lines.Add("$Key=$Value")
    } else {
        $keyLine = -1
        for ($i = $sectionLine + 1; $i -lt $nextSectionLine; $i++) {
            if ($lines[$i] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) { $keyLine = $i; break }
        }
        if ($keyLine -ge 0) {
            $lines[$keyLine] = "$Key=$Value"
        } else {
            $lines.Insert($nextSectionLine, "$Key=$Value")
        }
    }
    [IO.File]::WriteAllText($Path, (($lines -join "`r`n") + "`r`n"), $Unicode)
}

function Close-TargetTerminal([string]$ExecutablePath) {
    $targets = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $ExecutablePath
    })
    foreach ($target in $targets) {
        $process = Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
        if ($process) { [void]$process.CloseMainWindow() }
    }
    if ($targets.Count -gt 0) {
        $deadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 500
            $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
                $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $ExecutablePath
            })
        } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)
        if ($remaining.Count -gt 0) {
            Stop-WithMessage 'MT5 did not close cleanly. Nothing was installed. Close that terminal and run this file again.'
        }
    }
}

Write-Stage 'Checking portfolio files'
$portfolio = @(Get-PortfolioItems)
foreach ($item in $portfolio) {
    if (-not (Test-Path -LiteralPath $item.ExpertFullPath)) { Stop-WithMessage "Missing EA: $($item.ExpertFullPath)" }
    if (-not (Test-Path -LiteralPath $item.SetFullPath)) { Stop-WithMessage "Missing settings: $($item.SetFullPath)" }
    $inputs = Read-SetInputs $item.SetFullPath
    if ($inputs.Count -eq 0) { Stop-WithMessage "No settings could be read from: $($item.SetFullPath)" }
    Write-Host ('OK  {0}: {1} inputs' -f $item.Label, $inputs.Count)
}
if ($IsFullSafe) {
    $embeddedCount = @($portfolio | Where-Object { $_.SupportsSafeFilter -and -not $_.UsesDedicatedSafePreset }).Count
    $dedicatedCount = @($portfolio | Where-Object { $_.UsesDedicatedSafePreset }).Count
    Write-Host ("FULL SAFE: the completed-D1 Markov gate will be enabled independently inside {0} compatible EA charts." -f $embeddedCount) -ForegroundColor Green
    if ($dedicatedCount -gt 0) {
        Write-Host ("{0} EA uses its own audited Safe preset instead of the Markov gate." -f $dedicatedCount) -ForegroundColor Green
    }
}
if ($UseRecommendedSelections) {
    $recommendedSafe = @($portfolio | Where-Object { $_.SafeByDesign })
    $recommendedCount = $recommendedSafe.Count
    $recommendedDynamic = @($portfolio | Where-Object { $_.DynamicByDesign })
    Write-Host 'BEST RECOMMENDED: selected per-EA portfolio settings are active; each EA keeps its own configured session.' -ForegroundColor Green
    if ($recommendedCount -gt 0) {
        Write-Host ("{0} evidence-selected EAs default to Safe mode: {1}." -f $recommendedCount, (($recommendedSafe | ForEach-Object { $_.Label }) -join ', ')) -ForegroundColor Green
    }
    if ($recommendedDynamic.Count -gt 0) {
        Write-Host ("{0} evidence-selected EA defaults to its Dynamic mode: {1}." -f $recommendedDynamic.Count, (($recommendedDynamic | ForEach-Object { $_.Label }) -join ', ')) -ForegroundColor Green
    }
}

Write-Stage 'Finding MT5'
$candidates = @(Get-Mt5Candidates)
if ($ValidateOnly) {
    if ($candidates.Count -eq 0) { Stop-WithMessage 'Portfolio files are valid, but no normal MT5 installation was found.' }
    foreach ($candidate in $candidates) {
        $state = if ($candidate.Running) { 'running' } else { 'closed' }
        Write-Host ('{0} [{1}]' -f $candidate.Path, $state)
    }
    Write-Host "`nValidation passed. No terminal, profile, account or file was changed." -ForegroundColor Green
    exit 0
}

$selected = Select-Mt5Candidate $candidates
$terminalPath = [IO.Path]::GetFullPath($selected.Path)
Write-Host "Selected: $terminalPath"

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { Stop-WithMessage 'Python is required for safe account and broker-symbol detection, but it was not found.' }
if (-not (Test-Path -LiteralPath $ProbePath)) { Stop-WithMessage "Missing account probe: $ProbePath" }

Write-Stage 'Reading the active account and broker symbols'
$savedErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $probeOutput = @(& $python.Source $ProbePath --terminal $terminalPath 2>&1)
    $probeExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $savedErrorPreference
}
$probeText = $probeOutput -join "`n"
if ($probeExit -ne 0) {
    try { $probeError = ($probeText | ConvertFrom-Json).error } catch { $probeError = $probeText }
    Stop-WithMessage $probeError
}
try { $probe = $probeText | ConvertFrom-Json } catch { Stop-WithMessage "MT5 returned unreadable account data: $probeText" }
if (-not $probe.ok) { Stop-WithMessage ([string]$probe.error) }

$dataRoot = [IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))) {
    Stop-WithMessage "MT5 reported an invalid data folder: $dataRoot"
}
$commonIni = Join-Path $dataRoot 'config\common.ini'
if (-not (Test-Path -LiteralPath $commonIni)) {
    Write-Warning "MT5 common.ini was not found at $commonIni. The portfolio will still be installed, and MT5 will keep its current Algo Trading settings."
    $commonIni = $null
}

$login = [string]$probe.account.login
Write-Host ('Account: {0}' -f $login) -ForegroundColor Yellow
Write-Host ('Server:  {0}' -f $probe.account.server)
Write-Host ('Broker:  {0}' -f $probe.account.company)
Write-Host ('Balance: {0:N2} {1}' -f [double]$probe.account.balance, $probe.account.currency)
Write-Host ('Equity:  {0:N2} {1}' -f [double]$probe.account.equity, $probe.account.currency)
Write-Host ('Data:    {0}' -f $dataRoot)

if (-not [bool]$probe.terminal.connected) { Stop-WithMessage 'The selected MT5 terminal is not connected to its trading server.' }
if (-not [bool]$probe.account.trade_allowed) { Stop-WithMessage 'Trading is not allowed on the selected account.' }
if (-not [bool]$probe.account.trade_expert) { Stop-WithMessage 'This account currently blocks Expert Advisor trading.' }
$balance = [double]$probe.account.balance
if ($balance -le 0) { Stop-WithMessage "Account $login has no positive balance to size risk from." }
if ($UsesDynamicRisk) {
    if ($RiskValue -le 0.0) { Stop-WithMessage 'Dynamic risk must be greater than zero.' }
    if ($RiskMode -eq 'PERCENT') {
        if ($RiskValue -gt 10.0) { Stop-WithMessage 'Dynamic percentage risk cannot exceed 10% per EA trade.' }
        $EffectiveAdaptiveRiskPercent = $RiskValue
        $RequestedRiskMoney = [Math]::Round($balance * ($RiskValue / 100.0), 2)
    } else {
        $RequestedRiskMoney = $RiskValue
        $EffectiveAdaptiveRiskPercent = ($RiskValue / $balance) * 100.0
        if ($EffectiveAdaptiveRiskPercent -gt 10.0) { Stop-WithMessage ('The chosen fixed risk is {0:N2}% of this balance. The dynamic installer caps planned risk at 10% per EA trade.' -f $EffectiveAdaptiveRiskPercent) }
    }
    Write-Host ('Dynamic risk: {0:N2} {1} per EA trade, equivalent to {2:N4}% of the current balance.' -f $RequestedRiskMoney, [string]$probe.account.currency, $EffectiveAdaptiveRiskPercent) -ForegroundColor Cyan
    if ($RiskMode -eq 'FIXED_USD') {
        Write-Host 'Exact fixed cash is used where the EA supports it; percentage-only EAs receive the current-balance equivalent and will drift as equity changes.' -ForegroundColor Yellow
    }
}
if ([string]$probe.account.currency -ine 'USD' -and -not $IsAdaptiveAccount) {
    Stop-WithMessage "Refusing to run: the legacy fixed-money settings require a USD account, but account $login uses $($probe.account.currency)."
}

$symbols = @($probe.symbols)
$resolvedPortfolio = [Collections.Generic.List[object]]::new()
foreach ($item in $portfolio) {
    $match = Find-BrokerSymbol $symbols $item.Aliases
    if (-not $match -and ($IsAdaptiveAccount -or $IsSmallAccount)) {
        $match = Find-BrokerSymbol $symbols $item.Aliases -AllowFutures
    }
    if (-not $match) {
        if ([bool]$item.OptionalSymbol) {
            Write-Warning ("SKIPPED {0}: no tradable broker symbol matched {1}. The remaining EAs will still install." -f $item.Label, $item.Canonical)
            continue
        }
        $hints = @($symbols | Where-Object {
            $name = ([string]$_.name).ToUpperInvariant()
            $name -match 'JPY|XAU|XAG|GOLD|SILVER|US30|DOW|NAS|NDX|USTEC|US100|UT100|BTC|BITCOIN|ETH|ETHEREUM|US500|SPX|NVDA|AAPL|MSFT|AMZN|GOOG|META|AVGO|AMD|INTC|TSLA|JPM'
        } | Select-Object -First 30 -ExpandProperty name) -join ', '
        Stop-WithMessage "No tradable broker symbol matched $($item.Canonical). Possible symbols: $hints"
    }
    $item | Add-Member -NotePropertyName BrokerSymbol -NotePropertyValue ([string]$match.name)
    $brokerMinimum = [double]$match.volume_min
    $item | Add-Member -NotePropertyName BrokerVolumeMinimum -NotePropertyValue $brokerMinimum
    $basePercent = if ([bool]$item.LockRisk) { [double]$item.FixedPercentRisk } elseif ($UsesDynamicRisk) { $EffectiveAdaptiveRiskPercent } elseif ([double]$item.FixedPercentRisk -gt 0) { [double]$item.FixedPercentRisk } else { $AdaptiveRiskPercent }
    $effectiveItemRiskPercent = $basePercent * [double]$item.AdaptiveBaseMultiplier
    $targetRisk = if ([bool]$item.LockRisk) {
        [Math]::Round($balance * ($effectiveItemRiskPercent / 100.0), 2)
    } elseif ($UsesDynamicRisk -and $RiskMode -eq 'FIXED_USD') {
        [Math]::Round($RequestedRiskMoney * [double]$item.AdaptiveBaseMultiplier, 2)
    } elseif ($IsAdaptiveAccount) {
        [Math]::Round($balance * ($effectiveItemRiskPercent / 100.0), 2)
    } elseif ($IsSmallAccount) {
        [Math]::Round(40.0 * [double]$item.AdaptiveBaseMultiplier, 2)
    } else { 0.0 }
    $item | Add-Member -NotePropertyName EffectiveRiskPercent -NotePropertyValue $effectiveItemRiskPercent
    if ($IsAdaptiveAccount) {
        $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue $targetRisk
    }
    if (($IsAdaptiveAccount -or $IsSmallAccount) -and [bool]$item.SmallDynamicRisk) {
        $price = [Math]::Max([Math]::Max([double]$match.bid, [double]$match.ask), [double]$match.reference_price)
        $tickSize = [Math]::Abs([double]$match.trade_tick_size)
        $tickValue = [Math]::Max([Math]::Abs([double]$match.trade_tick_value_loss), [Math]::Abs([double]$match.trade_tick_value))
        $volumeStep = [Math]::Abs([double]$match.volume_step)
        $volumeMaximum = [double]$match.volume_max
        if ($price -le 0 -or $tickSize -le 0 -or $tickValue -le 0 -or $brokerMinimum -le 0 -or $volumeStep -le 0) {
            Stop-WithMessage "Cannot calculate a broker-specific adaptive stop for $($item.Label) on $($item.BrokerSymbol). Quote or contract data is missing."
        }

        $preferredStopPercent = 0.75
        $preferredDistance = $price * ($preferredStopPercent / 100.0)
        $riskPerLot = ($preferredDistance / $tickSize) * $tickValue
        $rawLot = $targetRisk / $riskPerLot
        $steps = [Math]::Round(($rawLot - $brokerMinimum) / $volumeStep, 0, [MidpointRounding]::AwayFromZero)
        $effectiveLot = $brokerMinimum + ([Math]::Max(0, $steps) * $volumeStep)
        $effectiveLot = [Math]::Min($volumeMaximum, [Math]::Max($brokerMinimum, $effectiveLot))
        $effectiveLot = [Math]::Round($effectiveLot, 8)
        $effectiveStopPercent = (($targetRisk * $tickSize) / ($tickValue * $effectiveLot * $price)) * 100.0
        $point = [Math]::Abs([double]$match.point)
        $stopsLevel = [Math]::Max(0, [double]$match.trade_stops_level)
        $minimumStopDistance = [Math]::Max($tickSize, $point * $stopsLevel)
        $minimumStopPercent = ($minimumStopDistance / $price) * 100.0
        if ($effectiveStopPercent -lt $minimumStopPercent) {
            $effectiveStopPercent = $minimumStopPercent
        }
        if ($effectiveStopPercent -le 0) {
            Stop-WithMessage "The calculated hard stop for $($item.Label) is invalid."
        }
        $effectiveRisk = (($price * ($effectiveStopPercent / 100.0)) / $tickSize) * $tickValue * $effectiveLot
        $item | Add-Member -NotePropertyName EffectiveLot -NotePropertyValue $effectiveLot
        $item | Add-Member -NotePropertyName EffectiveStopPercent -NotePropertyValue $effectiveStopPercent
        if ($IsAdaptiveAccount) { $item.EffectiveRisk = $effectiveRisk } else { $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue $effectiveRisk }
        $riskPctOfBalance = ($effectiveRisk / $balance) * 100.0
        Write-Host ('{0,-28} {1,-8} -> {2}; lot {3}, hard SL {4:N4}%, planned {5:N2} {6} ({7:N2}%)' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $effectiveLot, $effectiveStopPercent, $effectiveRisk, [string]$probe.account.currency, $riskPctOfBalance) -ForegroundColor Yellow
        if ($effectiveRisk -gt ($targetRisk * 1.05)) {
            Write-Host ('  Broker minimum lot/stop raises this above the {0:N2} {1} target.' -f $targetRisk, [string]$probe.account.currency) -ForegroundColor Red
        }
    } elseif ($UsesDynamicRisk -and -not [bool]$item.LockRisk) {
        $exactText = if ($RiskMode -eq 'FIXED_USD') { 'current-balance percent equivalent' } else { 'dynamic equity percentage' }
        Write-Host ('{0,-42} {1,-8} -> {2}; {3:N2} {4} ({5:N4}%), {6}' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $targetRisk, [string]$probe.account.currency, $effectiveItemRiskPercent, $exactText) -ForegroundColor Cyan
    } elseif ([double]$item.FixedPercentRisk -gt 0) {
        $fixedRiskText = ([double]$item.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        if ($item.Label -like 'News Pulse *') {
            Write-Host ('{0,-42} {1,-8} -> {2}; HARD {3}% per pending stop / 1.50% total event cap' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $fixedRiskText) -ForegroundColor Yellow
        } else {
            Write-Host ('{0,-42} {1,-8} -> {2}; fixed equity risk {3}%' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $fixedRiskText) -ForegroundColor Yellow
        }
    } elseif (($IsAdaptiveAccount -or $IsSmallAccount) -and [bool]$item.PercentRisk) {
        $percentInputs = Read-SetInputs $item.SetFullPath
        $riskText = if ($IsAdaptiveAccount) { $effectiveItemRiskPercent.ToString('0.########', [Globalization.CultureInfo]::InvariantCulture) } elseif ($percentInputs.Contains('InpRiskPercent')) { [string]$percentInputs['InpRiskPercent'] } else { 'default' }
        Write-Host ('{0,-42} {1,-8} -> {2}; equity risk {3}%' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $riskText)
    } elseif ($IsAdaptiveAccount) {
        Write-Host ('{0,-28} {1,-8} -> {2}; planned stop risk {3:N2} {4} ({5:N2}%)' -f $item.Label, $item.Canonical, $item.BrokerSymbol, $targetRisk, [string]$probe.account.currency, $EffectiveAdaptiveRiskPercent)
    } else {
        Write-Host ('{0,-22} {1,-8} -> {2}; requested stop risk $40' -f $item.Label, $item.Canonical, $item.BrokerSymbol)
    }
    [void]$resolvedPortfolio.Add($item)
}
$portfolio = @($resolvedPortfolio)
if ($portfolio.Count -eq 0) { Stop-WithMessage 'No portfolio symbols were available on this broker.' }

Assert-EffectiveRiskInputs $portfolio

if ($IsAdaptiveAccount) {
    $hasDynamicRiskItems = $UsesDynamicRisk -and @($portfolio | Where-Object { -not [bool]$_.LockRisk }).Count -gt 0
    if ($hasDynamicRiskItems) {
        Write-Host ('Adaptive balance accepted: {0:N2} {1}; Dynamic Config targets {2:N4}% or approximately {3:N2} {1} per EA trade.' -f $balance, [string]$probe.account.currency, $EffectiveAdaptiveRiskPercent, $RequestedRiskMoney) -ForegroundColor Green
    } else {
        Write-Host ('Adaptive balance accepted: {0:N2} {1}; adaptive EAs target {2:N2}% ({3:N2} {1} at installation), while preset-fixed entries remain at their configured risk.' -f $balance, [string]$probe.account.currency, $AdaptiveRiskPercent, ($balance * $AdaptiveRiskPercent / 100.0)) -ForegroundColor Green
    }
} elseif ($IsSmallAccount) {
    if ($balance -lt 800 -or $balance -gt 1200) {
        Stop-WithMessage "Refusing to run: the small-account settings are for roughly USD 900, but account $login has a balance of $($balance.ToString('N2')) $($probe.account.currency). Use an account between USD 800 and USD 1,200."
    }
} elseif ($balance -lt 90000 -or $balance -gt 110000) {
    Stop-WithMessage "Refusing to run: these settings are for a USD 100,000 account, but account $login has a balance of $($balance.ToString('N2')) $($probe.account.currency). Log into the correct 100K account and run the BAT again."
}

if ($PreflightOnly) {
    Write-Host "`nAdaptive preflight passed. No terminal, profile, account or file was changed." -ForegroundColor Green
    exit 0
}

Write-Host "`nThis will close and restart the selected MT5, enable Algo Trading, switch to a new" -ForegroundColor Yellow
Write-Host "$($portfolio.Count)-chart profile, and the EAs may place REAL TRADES immediately." -ForegroundColor Yellow
Write-Host "$($portfolio.Count)-EA SET: locked per-EA signal, exit and session selections; rejected EAs removed." -ForegroundColor Red
$modeMessage = if ($IsFullSafe) {
    'MODE: FULL SAFE - independent completed-D1 Markov gates enabled in every eligible strategy.'
} elseif ($UseRecommendedSelections) {
    'MODE: BEST RECOMMENDED - each EA uses its evidence-selected Standard, Safe or Dynamic input preset.'
} else {
    'MODE: STANDARD - current default/selective configuration.'
}
Write-Host $modeMessage -ForegroundColor Red
if ($IsAdaptiveAccount) {
    if ($UsesDynamicRisk) {
        Write-Host ('DYNAMIC RISK: target {0:N2} {1} ({2:N4}% of detected balance) per EA trade.' -f $RequestedRiskMoney, [string]$probe.account.currency, $EffectiveAdaptiveRiskPercent) -ForegroundColor Red
    } else {
        Write-Host ('AUTO BALANCE: adaptive EAs target {0:N2}% of the detected balance; preset-fixed entries keep their supplied risk.' -f $AdaptiveRiskPercent) -ForegroundColor Red
    }
    Write-Host 'Adaptive percentage-risk EA inputs are rebuilt from the active balance.' -ForegroundColor Red
} elseif ($IsSmallAccount) {
    Write-Host 'SMALL ACCOUNT: eligible EAs use their configured percentage or installer-adjusted risk.' -ForegroundColor Red
    Write-Host 'Gaps and execution slippage can still exceed planned risk.' -ForegroundColor Red
}
Write-Host 'It does not delete your existing profiles or close any open positions.' -ForegroundColor Yellow
$modeToken = if ($IsFullSafe) { ' SAFE' } else { '' }
$expected = "RUN $login"
$legacyExpected = if ($IsAdaptiveAccount) { "RUN $login AUTO$modeToken" } elseif ($IsSmallAccount) { "RUN $login 900$modeToken" } else { "RUN $login$modeToken" }
$confirmation = if ($Yes) { $expected } else { Read-Host "Type exactly '$expected' to continue" }
$confirmation = $confirmation.Trim()
if ($confirmation -ine $expected -and $confirmation -ine $legacyExpected) { Stop-WithMessage "Confirmation did not match. Type '$expected'. No portfolio files were installed." }

Write-Stage 'Starting Gold News V9 prediction service'
if (-not (Test-Path -LiteralPath $GoldNewsRuntimeInstaller)) {
    Stop-WithMessage "Missing Gold News runtime installer: $GoldNewsRuntimeInstaller"
}
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $GoldNewsRuntimeInstaller -RuntimeOnly -TargetTerminal $terminalPath
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage 'Gold News V9 prediction service did not start. MT5 and its profiles were not changed.'
}

Write-Stage 'Closing MT5 cleanly'
Close-TargetTerminal $terminalPath

Write-Stage 'Installing EAs, settings and isolated chart profile'
$mql5Root = Join-Path $dataRoot 'MQL5'
$expertsTarget = Join-Path (Join-Path $mql5Root 'Experts') $ExpertFolderName
$testerTarget = Join-Path (Join-Path $mql5Root 'Profiles\Tester') $ProfileName
$chartsRoot = Join-Path $mql5Root 'Profiles\Charts'
$profileTarget = Join-Path $chartsRoot $ProfileName

foreach ($directory in @($expertsTarget, $testerTarget, $chartsRoot)) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

# These two folders are owned by this installer. Delete stale files from EAs
# that are no longer in the user-selected portfolio before rebuilding them.
$expertsRootFull = [IO.Path]::GetFullPath((Join-Path $mql5Root 'Experts')).TrimEnd('\') + '\'
$expertsTargetFull = [IO.Path]::GetFullPath($expertsTarget)
$testerRootFull = [IO.Path]::GetFullPath((Join-Path $mql5Root 'Profiles\Tester')).TrimEnd('\') + '\'
$testerTargetFull = [IO.Path]::GetFullPath($testerTarget)
if (-not $expertsTargetFull.StartsWith($expertsRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-WithMessage "Refusing to clean an unsafe managed EA path: $expertsTargetFull"
}
if (-not $testerTargetFull.StartsWith($testerRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-WithMessage "Refusing to clean an unsafe managed settings path: $testerTargetFull"
}
$retainedExpertNames = @($portfolio | ForEach-Object { $_.Expert })
foreach ($staleExpert in @(Get-ChildItem -LiteralPath $expertsTargetFull -File -ErrorAction SilentlyContinue)) {
    if ($staleExpert.Name -notin $retainedExpertNames) {
        Remove-Item -LiteralPath $staleExpert.FullName -Force
        Write-Host "Deleted stale managed EA: $($staleExpert.Name)"
    }
}
foreach ($staleSet in @(Get-ChildItem -LiteralPath $testerTargetFull -File -ErrorAction SilentlyContinue)) {
    Remove-Item -LiteralPath $staleSet.FullName -Force
    Write-Host "Deleted stale managed setting: $($staleSet.Name)"
}

$chartsRootFull = [IO.Path]::GetFullPath($chartsRoot).TrimEnd('\') + '\'
$profileTargetFull = [IO.Path]::GetFullPath($profileTarget)
if (-not $profileTargetFull.StartsWith($chartsRootFull, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-WithMessage "Refusing to replace an unsafe profile path: $profileTargetFull"
}
if (Test-Path -LiteralPath $profileTargetFull) {
    $backup = $profileTargetFull + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $profileTargetFull -Destination $backup
    Write-Host "Previous auto profile backed up to: $backup"
}
[void](New-Item -ItemType Directory -Path $profileTargetFull -Force)

for ($i = 0; $i -lt $portfolio.Count; $i++) {
    $item = $portfolio[$i]
    Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $expertsTarget $item.Expert) -Force
    if ($IsAdaptiveAccount -or $IsSmallAccount) {
        $effectiveInputs = Get-EffectiveInputs $item
        $effectiveSetText = (@($effectiveInputs.Keys | ForEach-Object { '{0}={1}' -f $_, $effectiveInputs[$_] }) -join "`r`n") + "`r`n"
        $safeLabel = $item.Label -replace '[^A-Za-z0-9 -]', ''
        $setProfileLabel = if ($IsAdaptiveAccount) { 'AUTO BALANCE' } else { '900' }
        $effectiveSetName = "LAST INSTALLED $setProfileLabel - $safeLabel - $($item.BrokerSymbol).set"
        $effectiveSetSource = Join-Path (Split-Path -Parent $item.SetFullPath) $effectiveSetName
        [IO.File]::WriteAllText($effectiveSetSource, $effectiveSetText, [Text.UTF8Encoding]::new($false))
        Copy-Item -LiteralPath $effectiveSetSource -Destination (Join-Path $testerTarget $effectiveSetName) -Force
        $item | Add-Member -NotePropertyName EffectiveSetPath -NotePropertyValue $effectiveSetSource
    } else {
        Copy-Item -LiteralPath $item.SetFullPath -Destination (Join-Path $testerTarget ([IO.Path]::GetFileName($item.SetFullPath))) -Force
        $item | Add-Member -NotePropertyName EffectiveSetPath -NotePropertyValue $item.SetFullPath
    }
    $chartName = 'chart{0:D2}.chr' -f ($i + 1)
    $chartPath = Join-Path $profileTargetFull $chartName
    $chartText = New-ChartText $item $item.BrokerSymbol ([DateTime]::UtcNow.Ticks + $i) $i
    [IO.File]::WriteAllText($chartPath, $chartText.TrimStart(), $Unicode)
    Write-Host ('Installed {0} on {1}, period {2}' -f $item.Label, $item.BrokerSymbol, $item.Period)
}

$orderText = ((1..$portfolio.Count | ForEach-Object { 'chart{0:D2}.chr' -f $_ }) -join "`r`n") + "`r`n"
[IO.File]::WriteAllText((Join-Path $profileTargetFull 'order.wnd'), $orderText, $Unicode)

Test-ManagedProfile $profileTargetFull $portfolio 'Before MT5 start'

if ($commonIni) {
    $commonBackup = $commonIni + '.bm-auto-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Copy-Item -LiteralPath $commonIni -Destination $commonBackup
    Set-IniValue $commonIni 'Experts' 'Enabled' '1'
    Set-IniValue $commonIni 'Experts' 'Account' '0'
    Set-IniValue $commonIni 'Experts' 'Profile' '0'
    Set-IniValue $commonIni 'Experts' 'Chart' '0'
} else {
    Write-Warning 'Skipped automatic Algo Trading preference update because common.ini is unavailable. EA installation remains complete.'
}

$manifest = @(
    'Installed: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    'Terminal: ' + $terminalPath
    'Data folder: ' + $dataRoot
    'Profile: ' + $ProfileName
    'Account preset: ' + $AccountProfile
    'Safety mode: ' + $SafetyMode
    'Recommended selections: ' + [bool]$UseRecommendedSelections
    'Recommended adaptive profile: ' + [bool]$UseAdaptiveProfile
    'Recommended Safe EAs: ' + ((@($portfolio | Where-Object { $_.SafeByDesign }) | ForEach-Object { $_.Label }) -join ', ')
    'Recommended Dynamic EAs: ' + ((@($portfolio | Where-Object { $_.DynamicByDesign }) | ForEach-Object { $_.Label }) -join ', ')
    'Risk mode: ' + $RiskMode
    'Requested risk value: ' + $RiskValue.ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
    'Account: ' + $login
    'Balance at install: ' + $balance.ToString('N2') + ' ' + [string]$probe.account.currency
    'Server: ' + [string]$probe.account.server
    'Gold News runtime: http://127.0.0.1:8799'
    ''
    'Charts:'
) + @($portfolio | ForEach-Object {
    if ($UsesDynamicRisk) {
        '{0}: {1}, period {2}, {3}; dynamic target {4:N2} {5} ({6:N4}% at install); set {7}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveRisk, [string]$probe.account.currency, $_.EffectiveRiskPercent, $_.EffectiveSetPath
    } elseif (($IsAdaptiveAccount -or $IsSmallAccount) -and [bool]$_.SmallDynamicRisk) {
        '{0}: {1}, period {2}, {3}; lot {4}; hard SL {5:N4}%; target risk {6:N2} {7}; set {8}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveLot, $_.EffectiveStopPercent, $_.EffectiveRisk, [string]$probe.account.currency, $_.EffectiveSetPath
    } elseif ([double]$_.FixedPercentRisk -gt 0) {
        $fixedRiskText = ([double]$_.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        '{0}: {1}, period {2}, {3}; fixed equity risk {4}%; set {5}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $fixedRiskText, $_.EffectiveSetPath
    } elseif (($IsAdaptiveAccount -or $IsSmallAccount) -and [bool]$_.PercentRisk) {
        $riskInputs = Read-SetInputs $_.SetFullPath
        $riskText = if ($IsAdaptiveAccount) { ([double]$_.EffectiveRiskPercent).ToString('0.########', [Globalization.CultureInfo]::InvariantCulture) } elseif ($riskInputs.Contains('InpRiskPercent')) { [string]$riskInputs['InpRiskPercent'] } else { 'default' }
        '{0}: {1}, period {2}, {3}; equity risk {4}%; set {5}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $riskText, $_.EffectiveSetPath
    } elseif ($IsAdaptiveAccount) {
        '{0}: {1}, period {2}, {3}; planned stop risk {4:N2} {5} ({6:N2}%); set {7}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveRisk, [string]$probe.account.currency, $_.EffectiveRiskPercent, $_.EffectiveSetPath
    } elseif ($IsSmallAccount) {
        '{0}: {1}, period {2}, {3}; requested stop risk USD 40; set {4}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert, $_.EffectiveSetPath
    } else {
        '{0}: {1}, period {2}, {3}' -f $_.Label, $_.BrokerSymbol, $_.Period, $_.Expert
    }
})
$manifestPath = Join-Path $PSScriptRoot 'LAST INSTALL.txt'
[IO.File]::WriteAllText($manifestPath, (($manifest -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($true))

Write-Stage "Starting the $($portfolio.Count)-EA profile"
$arguments = '/profile:"' + $ProfileName + '"'
Start-Process -FilePath $terminalPath -ArgumentList $arguments
Start-Sleep -Seconds 12

$runningNow = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^terminal(64)?\.exe$' -and $_.ExecutablePath -ieq $terminalPath
})
if ($runningNow.Count -eq 0) { Stop-WithMessage 'The files were installed, but MT5 did not remain running.' }

Test-ManagedProfile $profileTargetFull $portfolio 'After MT5 start'

Write-Host "`nSUCCESS: MT5 is running the '$ProfileName' profile on account $login." -ForegroundColor Green
Write-Host "Install record: $manifestPath"
Write-Host "Verify all $($portfolio.Count) chart faces show the EA name and the toolbar Algo Trading button is green." -ForegroundColor Yellow
