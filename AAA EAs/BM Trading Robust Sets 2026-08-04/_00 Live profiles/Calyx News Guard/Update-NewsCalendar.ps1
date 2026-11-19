# Calyx News Guard calendar updater v2 (2026-11-20). Windows PowerShell 5.1, no Python needed.
# Writes %APPDATA%\MetaQuotes\Terminal\Common\Files\CalyxNewsCalendar.csv (utc_epoch,currency,impact,title) for the "Calyx News Guard" chart,
# which acts on impact "High".
# Source (owner 2026-11-20: "use the FTMO calendar, if it fails then ForexFactory if possible"):
#   1. FTMO public economic calendar (https://gw2.ftmo.com/public-api/v1/economic-calendar, the data behind ftmo.com/en/calendar/), fetched week by week
#      (the API refuses long ranges). Only FTMO's RESTRICTED events (the news FTMO restricts on funded Standard accounts) are written as "High";
#      every other FTMO event is written as "ftmo-<impact>" so the guard ignores it. Currencies are taken from FTMO's "instrument" field
#      (e.g. "USD + US Indices + XAUUSD + DXY" -> USD).
#   2. If FTMO cannot be reached: the ForexFactory weekly feed (High-impact events), merged with the existing file (the previous behaviour).
# Run daily (the installers create the Windows task "Calyx News Calendar"). Sends only plain GETs, no account data.
[CmdletBinding()]
param([string]$Out = '', [ValidateSet('Auto', 'FTMO', 'ForexFactory')][string]$Source = 'Auto',
      [string]$Feed = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json', [switch]$Quiet)   # -Quiet: no pause in the BAT (scheduled task)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not $Out) {
    $dir = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
    [void](New-Item -ItemType Directory -Path $dir -Force)
    $Out = Join-Path $dir 'CalyxNewsCalendar.csv'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$inv = [Globalization.CultureInfo]::InvariantCulture

function Save-Calendar([object[]]$Rows, [string]$SourceText) {
    $kept = @($Rows | Where-Object { [long]$_[0] -ge ($now - 14 * 86400) } | Sort-Object { [long]$_[0] })
    $lines = @("# Calyx News Guard calendar; source $SourceText; fetched_utc=$now", 'utc_epoch,currency,impact,title') + @($kept | ForEach-Object { $_ -join ',' })
    $tmp = "$Out.tmp"
    [IO.File]::WriteAllLines($tmp, [string[]]$lines, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Out -Force
    $up = @($kept | Where-Object { [long]$_[0] -ge $now -and $_[2] -eq 'High' })
    Write-Host ("Calendar written ({0}): {1}  ({2} events, {3} upcoming blocked events)" -f $SourceText, $Out, $kept.Count, $up.Count) -ForegroundColor Green
    foreach ($r in ($up | Select-Object -First 8)) { Write-Host ('  {0:ddd yyyy-MM-dd HH:mm} UTC  {1}  {2}' -f [DateTimeOffset]::FromUnixTimeSeconds([long]$r[0]).UtcDateTime, $r[1], $r[3]) }
}

function Get-FtmoRows {
    $rows = @(); $ok = 0; $start = [DateTime]::UtcNow.Date.AddDays(-14)
    for ($k = 0; $k -lt 4; $k++) {                      # 4 weeks: last 2 weeks, this week, next week (empty until FTMO publishes it)
        $a = $start.AddDays(7 * $k); $b = $a.AddDays(7).AddSeconds(-1)
        $u = 'https://gw2.ftmo.com/public-api/v1/economic-calendar?dateFrom={0}%2B00:00&dateTo={1}%2B00:00&timezone=UTC' -f $a.ToString('yyyy-MM-ddTHH:mm:ss', $inv), $b.ToString('yyyy-MM-ddTHH:mm:ss', $inv)
        $j = Invoke-RestMethod -Uri $u -UserAgent 'calyx-news-guard/1.1' -TimeoutSec 30
        if ($null -eq $j -or -not ($j.PSObject.Properties.Name -contains 'items')) { throw "unexpected FTMO response for $($a.ToString('yyyy-MM-dd'))" }
        $ok++
        foreach ($e in @($j.items)) {
            $when = [DateTimeOffset]::MinValue
            if (-not [DateTimeOffset]::TryParse([string]$e.date, $inv, [Globalization.DateTimeStyles]::None, [ref]$when)) { continue }
            $codes = @([regex]::Matches(([string]$e.instrument).ToUpperInvariant(), '\b[A-Z]{3}\b') | ForEach-Object { $_.Value } | Where-Object { $_ -notin @('DXY', 'DAX') } | Select-Object -Unique)
            if (-not $codes) { $codes = @(([string]$e.instrument) -replace '[^A-Za-z]', '') }      # e.g. Crude Oil / NATGAS: kept, no symbol matches it
            $impact = if ($e.restriction -eq $true) { 'High' } else { 'ftmo-' + ([string]$e.impact).Trim().ToLowerInvariant() }
            $title = ([string]$e.title).Replace(',', ' ').Trim()
            foreach ($c in $codes) { $rows += , @([string]$when.ToUnixTimeSeconds(), $c, $impact, $title) }
        }
    }
    if ($ok -eq 0 -or $rows.Count -eq 0) { throw 'FTMO calendar returned no events' }
    return , $rows
}

function Get-ForexFactoryRows {
    $map = @{}
    if (Test-Path -LiteralPath $Out) {
        foreach ($line in Get-Content -LiteralPath $Out) {
            if (-not $line -or $line.StartsWith('#') -or $line.StartsWith('utc_epoch')) { continue }
            $p = $line.Split(',', 4)
            if ($p.Count -ge 3 -and -not $p[2].StartsWith('ftmo-')) { $t = if ($p.Count -gt 3) { $p[3] } else { '' }; $map["$($p[0])|$($p[1])|$t"] = $p }
        }
    }
    $events = Invoke-RestMethod -Uri $Feed -UserAgent 'calyx-news-guard/1.1' -TimeoutSec 30
    foreach ($e in @($events)) {
        $when = [DateTimeOffset]::MinValue
        if (-not [DateTimeOffset]::TryParse([string]$e.date, $inv, [Globalization.DateTimeStyles]::None, [ref]$when)) { continue }
        $ccy = ([string]$e.country).Trim().ToUpperInvariant(); if ($ccy.Length -ne 3) { continue }
        $impact = ([string]$e.impact).Trim(); if (-not $impact) { continue }
        $title = ([string]$e.title).Replace(',', ' ').Trim()
        $map["$($when.ToUnixTimeSeconds())|$ccy|$title"] = @([string]$when.ToUnixTimeSeconds(), $ccy, $impact, $title)
    }
    return , @($map.Values)
}

$done = $false
if ($Source -in @('Auto', 'FTMO')) {
    try { Save-Calendar (Get-FtmoRows) 'FTMO restricted news (gw2.ftmo.com public calendar)'; $done = $true }
    catch {
        Write-Host ("FTMO calendar unavailable: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        if ($Source -eq 'FTMO') { throw }
    }
}
if (-not $done) {
    Write-Host 'Using the ForexFactory calendar instead (High-impact news; close to, but not exactly, FTMO''s restricted list).' -ForegroundColor Yellow
    Save-Calendar (Get-ForexFactoryRows) "ForexFactory High impact ($Feed)"
}
