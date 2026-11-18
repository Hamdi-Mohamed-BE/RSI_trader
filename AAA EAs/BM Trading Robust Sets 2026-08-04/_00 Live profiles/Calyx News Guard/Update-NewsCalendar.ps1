# Calyx News Guard calendar updater (2026-11-18). Windows PowerShell 5.1, no Python needed.
# Downloads this week's economic calendar (ForexFactory public feed) and merges it into
#   %APPDATA%\MetaQuotes\Terminal\Common\Files\CalyxNewsCalendar.csv
# for the "Calyx News Guard" helper chart. Keeps the last 14 days and everything upcoming. Run it daily
# (Update News Calendar.bat, or a Windows Task Scheduler task that you create yourself). Sends only a plain GET.
# FTMO's "selected news" list can differ; the ForexFactory High-impact set covers the big USD / EUR / GBP / JPY releases.
[CmdletBinding()]
param([string]$Out = '', [string]$Feed = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json')
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if (-not $Out) {
    $dir = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
    [void](New-Item -ItemType Directory -Path $dir -Force)
    $Out = Join-Path $dir 'CalyxNewsCalendar.csv'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$rows = @{}
if (Test-Path -LiteralPath $Out) {
    foreach ($line in Get-Content -LiteralPath $Out) {
        if (-not $line -or $line.StartsWith('#') -or $line.StartsWith('utc_epoch')) { continue }
        $p = $line.Split(',', 4)
        if ($p.Count -ge 3) { $t = if ($p.Count -gt 3) { $p[3] } else { '' }; $rows["$($p[0])|$($p[1])|$t"] = $p }
    }
}
$events = Invoke-RestMethod -Uri $Feed -UserAgent 'calyx-news-guard/1.0' -TimeoutSec 30
$new = 0
foreach ($e in @($events)) {
    $when = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse([string]$e.date, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$when)) { continue }
    $ccy = ([string]$e.country).Trim().ToUpperInvariant(); if ($ccy.Length -ne 3) { continue }
    $impact = ([string]$e.impact).Trim(); if (-not $impact) { continue }
    $title = ([string]$e.title).Replace(',', ' ').Trim()
    $epoch = [string]$when.ToUnixTimeSeconds()
    $key = "$epoch|$ccy|$title"; if (-not $rows.ContainsKey($key)) { $new++ }
    $rows[$key] = @($epoch, $ccy, $impact, $title)
}
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$kept = @($rows.Values | Where-Object { [long]$_[0] -ge ($now - 14 * 86400) } | Sort-Object { [long]$_[0] })
$lines = @("# Calyx News Guard calendar; source $Feed; fetched_utc=$now", 'utc_epoch,currency,impact,title') + @($kept | ForEach-Object { $_ -join ',' })
$tmp = "$Out.tmp"
[IO.File]::WriteAllLines($tmp, [string[]]$lines, [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $tmp -Destination $Out -Force
$up = @($kept | Where-Object { [long]$_[0] -ge $now -and $_[2] -eq 'High' })
Write-Host ("Calendar written: {0}  ({1} events, {2} new, {3} upcoming High-impact)" -f $Out, $kept.Count, $new, $up.Count) -ForegroundColor Green
foreach ($r in ($up | Select-Object -First 8)) { Write-Host ('  {0:ddd yyyy-MM-dd HH:mm} UTC  {1}  {2}' -f [DateTimeOffset]::FromUnixTimeSeconds([long]$r[0]).UtcDateTime, $r[1], $r[3]) }
