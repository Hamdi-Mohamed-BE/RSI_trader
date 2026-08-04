$ErrorActionPreference = 'Stop'

$sourceDir = Join-Path $PSScriptRoot 'presets'
$outputDir = Join-Path $PSScriptRoot 'scaled presets'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

function New-ScaledPreset {
    param(
        [string]$SourceName,
        [string]$OutputName,
        [hashtable]$Replacement
    )
    $sourcePath = Join-Path $sourceDir $SourceName
    $outputPath = Join-Path $outputDir $OutputName
    $text = [IO.File]::ReadAllText($sourcePath, [Text.Encoding]::Unicode)
    $text = "; 100K PORTFOLIO SET - exact scaled validation candidate`r`n; Do not combine with another set for the same EA/chart.`r`n" + $text
    foreach ($key in $Replacement.Keys) {
        $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
        if (-not [regex]::IsMatch($text, $pattern)) { throw "Setting $key was not found in $SourceName" }
        $text = [regex]::Replace($text, $pattern, ($key + '=' + $Replacement[$key]), 1)
    }
    [IO.File]::WriteAllText($outputPath, $text, [Text.Encoding]::Unicode)
    Get-Item -LiteralPath $outputPath
}

New-ScaledPreset -SourceName 'PORT_BASE_RB.set' -OutputName 'PORTFOLIO 100K FINAL - Range Breakout - USDJPY M5 - 245 USD risk.set' -Replacement @{
    RiskMoney = '245||50.0||5.000000||500.000000||N'
    Magic = '910101||111||1||1110||N'
}
New-ScaledPreset -SourceName 'PORT_BASE_GL.set' -OutputName 'PORTFOLIO 100K FINAL - Go Long - US30 D1 - 0.50 lot.set' -Replacement @{
    Lots = '0.50||0.01||0.001000||1.000000||N'
    Magic = '920101||123454321||1||1234543210||N'
}
New-ScaledPreset -SourceName 'PORT_BASE_TT.set' -OutputName 'PORTFOLIO 100K FINAL - Turnaround Tuesday - UT100 D1 - 0.24 lot.set' -Replacement @{
    Lots = '0.24||0.01||0.001000||1.000000||N'
    Magic = '930103||123454321||1||1234543210||N'
}
New-ScaledPreset -SourceName 'PORT_BASE_ATR.set' -OutputName 'PORTFOLIO 100K FINAL - ATR Candle Breakout - XAUUSD H1 - 146 USD risk.set' -Replacement @{
    InpRiskAmount = '146||100.0||10.000000||1000.000000||N'
    InpMagicNumber = '960103||14||1||140||N'
}
