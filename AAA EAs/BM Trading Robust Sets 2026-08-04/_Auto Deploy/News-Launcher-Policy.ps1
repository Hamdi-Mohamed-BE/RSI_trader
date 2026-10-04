# 2026-10-03: restore all five selected news EAs in NORMAL portfolio BATs.
# The separate FTMO roster stays news-free. Ava retains its separate policy.
function Select-NormalNewsItems {
    param([object[]]$Items)
    $approved = @{
        'News Pulse XAU'='XAUUSD'; 'News Pulse XAG'='XAGUSD';
        'News Pulse BTC'='BTCUSD'; 'News Pulse EURUSD'='EURUSD';
        'Gold News V9 Direction'='XAUUSD'
    }
    foreach ($item in $Items) {
        $isNews = ([string]$item.Label -match '(?i)news') -or ([string]$item.Expert -match '(?i)news')
        if (-not $isNews) { $item; continue }
        if (-not $approved.ContainsKey([string]$item.Label)) { continue }
        if ($item.PSObject.Properties['Canonical'] -and [string]$item.Canonical -ne $approved[[string]$item.Label]) {
            throw "Normal news policy: invalid canonical symbol for $($item.Label)."
        }
        $item
    }
}

# Legacy helper is retained solely for the separate Ava futures launcher.
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
