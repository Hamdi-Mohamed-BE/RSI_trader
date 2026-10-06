# Owner deployment decisions; only the new reviewed launcher opts into this roster.
function Get-ReviewedManifest {
    $path = Join-Path $PackageRoot 'Reviewed EA Deployment 2026-10-06\selection.json'
    $manifest = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $entries = @($manifest.entries)
    if ($entries.Count -ne 37 -or @($entries.slug | Select-Object -Unique).Count -ne 37 -or @($entries.installer_label | Select-Object -Unique).Count -ne 37) { throw 'Reviewed manifest must contain 37 unique catalogue entries.' }
    if (@($entries | Where-Object phase -eq 'live').Count -ne 25) { throw 'Reviewed manifest must select exactly 25 entries.' }
    return $manifest
}

function Select-ReviewedItems([object[]]$Items) {
    $manifest = Get-ReviewedManifest
    $chosen = @($manifest.entries | Where-Object phase -eq 'live')
    $result = @()
    foreach ($entry in $chosen) {
        $matches = @($Items | Where-Object Label -eq $entry.installer_label)
        if ($matches.Count -ne 1) { throw "Reviewed entry missing/ambiguous in installer: $($entry.installer_label)" }
        $item=$matches[0]
        $item | Add-Member -NotePropertyName ReviewedEntry -NotePropertyValue $entry
        $result += $item
    }
    return $result
}

function Set-ReviewedInputs([object]$Item, [System.Collections.Specialized.OrderedDictionary]$Inputs) {
    $entry=$Item.ReviewedEntry
    if ($entry.PSObject.Properties['input_overrides']) {
        foreach ($p in $entry.input_overrides.PSObject.Properties) {
            if (-not $Inputs.Contains($p.Name)) { throw "Unsupported reviewed input $($p.Name) for $($Item.Label)" }
            $Inputs[$p.Name]=[string]$p.Value
        }
    }
    if ($entry.PSObject.Properties['di_input']) {
        $choice = if ($Item.Label -eq 'Nasdaq 5M Candle Momentum') { $NasdaqDIFilter } elseif ($Item.Label -eq 'USDJPY London Open Momentum') { $UsdJpyDIFilter } else { throw "No DI prompt wired for $($Item.Label)" }
        if (-not $Inputs.Contains([string]$entry.di_input)) { throw "DI input unsupported for $($Item.Label)" }
        $Inputs[[string]$entry.di_input]=if ($choice -eq 'ON') { 'true' } else { 'false' }
    }
}
