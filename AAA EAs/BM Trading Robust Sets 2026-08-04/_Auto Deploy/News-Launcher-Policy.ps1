# 2026-10-02 owner instruction: no non-gold news EAs in any managed BAT.
# This only filters an installer manifest; it never touches a running terminal.
function Select-XauNewsOnlyItems {
    param([object[]]$Items)
    foreach ($item in $Items) {
        $isNews = ([string]$item.Label -match '(?i)news') -or ([string]$item.Expert -match '(?i)news')
        if (-not $isNews) { $item; continue }
        if ([string]$item.Label -notin @('News Pulse XAU', 'Gold News V9 Direction')) { continue }
        if ($item.PSObject.Properties['Canonical'] -and [string]$item.Canonical -ne 'XAUUSD') {
            throw "Gold-only news policy: invalid canonical symbol for $($item.Label)."
        }
        $item
    }
}
