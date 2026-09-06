[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$ResultsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$rows = @(Import-Csv -LiteralPath $ResultsPath)
if ($rows.Count -eq 0) {
    throw "Research market gate failed: '$ResultsPath' has no result rows."
}

$candidateColumns = @('symbol', 'market', 'instrument', 'asset', 'pair')
$availableColumns = @($rows[0].PSObject.Properties.Name)
$marketColumn = $candidateColumns |
    Where-Object { $availableColumns -contains $_ } |
    Select-Object -First 1

if (-not $marketColumn) {
    throw "Research market gate failed: '$ResultsPath' needs a symbol, market, instrument, asset, or pair column."
}

$silverRows = @(
    $rows | Where-Object {
        $value = [string]($_.$marketColumn)
        $normalized = ($value -replace '[^A-Za-z0-9]', '').ToUpperInvariant()
        $normalized -match 'XAG' -or $normalized -match 'SILVER'
    }
)

if ($silverRows.Count -eq 0) {
    throw "Research market gate failed: XAG validation is missing from '$ResultsPath'."
}

[pscustomobject]@{
    Status = 'PASS'
    Results = (Resolve-Path -LiteralPath $ResultsPath).Path
    MarketColumn = $marketColumn
    XAGRows = $silverRows.Count
    Message = 'Mandatory XAG validation evidence is present.'
}
