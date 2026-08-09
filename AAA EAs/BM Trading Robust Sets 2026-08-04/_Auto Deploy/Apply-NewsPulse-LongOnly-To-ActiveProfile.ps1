$ErrorActionPreference = 'Stop'

$chartPath = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\BM Trading ANY BALANCE - AUTO\chart13.chr'
$backupPath = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\BM Trading ANY BALANCE - AUTO.backup-20260809-222440\chart13.before-news-pulse-long-only-v211.chr'

if (-not (Test-Path -LiteralPath $chartPath)) {
    throw "Active News Pulse chart was not found: $chartPath"
}

$text = Get-Content -LiteralPath $chartPath -Raw
foreach ($required in @(
    'InpEnableTrading=true',
    'InpRiskPercent=1',
    'InpPlacementLeadSeconds=30',
    'InpEntryOffsetPrice=6',
    'InpStopLossPrice=6',
    'InpTrailStartR=1.5',
    'InpTrailDistancePrice=15',
    'InpForceCloseSecondsAfterEvent=60'
)) {
    if (([regex]::Matches($text, [regex]::Escape($required))).Count -ne 1) {
        throw "Required active-chart value was not found exactly once: $required"
    }
}

if ($text.Contains('InpEnableBuySide=') -or $text.Contains('InpEnableSellSide=')) {
    throw 'Direction inputs already exist; refusing to create duplicates.'
}

$directionInputs = 'InpEnableTrading=true' + [Environment]::NewLine +
                   'InpEnableBuySide=true' + [Environment]::NewLine +
                   'InpEnableSellSide=false'
$text = $text.Replace('InpEnableTrading=true', $directionInputs)
Copy-Item -LiteralPath $chartPath -Destination $backupPath -Force
Set-Content -LiteralPath $chartPath -Value $text -Encoding Unicode -NoNewline
Write-Output "UPDATED=$chartPath"
Write-Output "BACKUP=$backupPath"
