# Pure roster selection only. Importing this file never accesses a terminal/account.
function Get-FTMOProfileEntries(
    [object]$Manifest,
    [ValidateSet('FTMO17','PROP_READY9')][string]$PortfolioVariant='FTMO17'
) {
    $entries=@($Manifest.entries)
    if($entries.Count -ne 17 -or @($entries | Group-Object slug | Where-Object Count -ne 1).Count){
        throw 'Expected the unchanged, unique 17-EA FTMO source package.'
    }
    if($PortfolioVariant -eq 'FTMO17'){return $entries}
    $slugs=@(
        'nasdaq-5m-candle-momentum',
        'usdjpy-london-open-momentum',
        'us100-month-end-flow',
        'xau-rsi-vwap',
        'us100-h1-orb-13utc',
        'us100-orb-new-york-m30',
        'us100-selective-orb-v3',
        'xau-orb-new-york-m30',
        'xau-orb-london-ny-overlap-m30'
    )
    # Retain source manifest order, including simultaneous-entry priority.
    $selectedEntries=@($entries | Where-Object slug -in $slugs)
    if($selectedEntries.Count -ne $slugs.Count){throw 'Prop ready requires all nine selected EAs exactly once.'}
    return $selectedEntries
}
