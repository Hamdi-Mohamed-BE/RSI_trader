$ErrorActionPreference = 'Stop'

$chartPath = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\BM Trading ANY BALANCE - AUTO\chart13.chr'
$backupPath = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\BM Trading ANY BALANCE - AUTO.backup-20260809-222440\chart13.before-news-pulse-a60.chr'

if (-not (Test-Path -LiteralPath $chartPath)) {
    throw "Active News Pulse chart was not found: $chartPath"
}

$text = Get-Content -LiteralPath $chartPath -Raw
$changes = [ordered]@{
    'InpPlacementLeadSeconds=60' = 'InpPlacementLeadSeconds=30'
    'InpEntryOffsetPrice=12' = 'InpEntryOffsetPrice=6'
    'InpStopLossPrice=10' = 'InpStopLossPrice=6'
    'InpTrailStartR=3' = 'InpTrailStartR=1.5'
    'InpTrailDistancePrice=10' = 'InpTrailDistancePrice=15'
    'InpForceCloseSecondsAfterEvent=120' = 'InpForceCloseSecondsAfterEvent=60'
}

foreach ($old in $changes.Keys) {
    $count = ([regex]::Matches($text, [regex]::Escape($old))).Count
    if ($count -ne 1) {
        throw "Expected one active-chart value '$old', found $count. Nothing was written."
    }
    $text = $text.Replace($old, $changes[$old])
}

Copy-Item -LiteralPath $chartPath -Destination $backupPath -Force
Set-Content -LiteralPath $chartPath -Value $text -Encoding Unicode -NoNewline
Write-Output "UPDATED=$chartPath"
Write-Output "BACKUP=$backupPath"
