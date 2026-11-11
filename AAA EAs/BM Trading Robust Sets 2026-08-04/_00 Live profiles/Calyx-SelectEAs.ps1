# >>> Calyx EA selection (owner 2026-11-11: "make the bat ask me one by one to add or not") >>>
# The package keeps every EA; the installer asks for each one (Enter = install). -SkipEAs slug1,slug2 skips without asking (scripted runs).
# Integrity checks still cover the whole package; only the chosen EAs get charts, symbols and load checks.
function Select-CalyxEntries([object[]]$Entries, [string[]]$Skip, [bool]$NoPrompt, [string]$KeyName = 'slug', [string]$LabelName = 'label', [string]$SymbolName = 'symbol') {
    $skipSet = @(foreach ($s in @($Skip)) { foreach ($part in ([string]$s).Split(',')) { if ($part.Trim()) { $part.Trim().ToLowerInvariant() } } })
    foreach ($s in $skipSet) { if (-not @($Entries | Where-Object { ([string]$_.$KeyName).ToLowerInvariant() -eq $s }).Count) { throw "Unknown EA to skip: $s (use the slug, e.g. uk100-monday-dip)" } }
    $ask = (-not $NoPrompt) -and (-not $skipSet.Count)
    if ($ask) { Write-Host ''; Write-Host 'CHOOSE THE EAs - press Enter (or Y) to install an EA, N to leave it out.' -ForegroundColor Cyan }
    $out = @()
    foreach ($e in $Entries) {
        $key = ([string]$e.$KeyName).ToLowerInvariant(); $label = [string]$e.$LabelName; $symbol = [string]$e.$SymbolName
        if ($skipSet -contains $key) { Write-Host ("  OFF  {0} ({1}) - skipped by -SkipEAs" -f $label, $symbol) -ForegroundColor Yellow; continue }
        if ($ask) {
            $answer = (Read-Host ("  Install {0} ({1})? Y or N [Y]" -f $label, $symbol)).Trim().ToUpperInvariant()
            if ($answer -and $answer -notin @('Y', 'YES', 'N', 'NO')) { throw 'Answer Y or N.' }
            if ($answer -in @('N', 'NO')) { Write-Host ("  OFF  {0}" -f $label) -ForegroundColor Yellow; continue }
        }
        $out += $e
    }
    if (-not $out.Count) { throw 'No EA selected. Nothing was installed.' }
    if ($out.Count -lt $Entries.Count) { Write-Host ("EAs selected: {0} of {1}. The backtests and FTMO simulations were run with all {1}; a smaller set is untested." -f $out.Count, $Entries.Count) -ForegroundColor Yellow }
    else { Write-Host ("EAs selected: all {0}." -f $out.Count) -ForegroundColor Green }
    return $out   # callers collect with @(...)
}
# <<< Calyx EA selection <<<
