"""Generate NewsGuard-Functions.ps1 (installer functions for the Calyx News Guard chart) from the tested Calyx Weekend Flat functions, with asserted
substitutions only, plus NEWS_GUARD.json (EX5 hash the installers verify). python make_functions.py"""
import hashlib, json
from pathlib import Path

H = Path(__file__).resolve().parent; W = H.parent / 'Calyx Weekend Flat' / 'WeekendFlat-Functions.ps1'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    src = W.read_text(encoding='utf-8').replace('\r\n', '\n')
    a = src.index('function Get-CalyxWeekendFlatExpert'); b = src.index('# <<< Calyx Weekend Flat <<<')
    body = src[a:b]
    old_inputs = body[body.index('<inputs>\n'):body.index('</inputs>') + len('</inputs>')]
    new_inputs = ('<inputs>\nInpEnabled=true\nInpBeforeMinutes=$Mode\nInpAfterMinutes=$Mode\nInpCloseLeadSeconds=90\nInpImpacts=High\nInpCalendarFile=CalyxNewsCalendar.csv\n'
                  'InpStaleHours=36\nInpIncludeManual=false\nInpDeletePending=true\nInpTimerSeconds=2\nInpTestEvents=\nInpTestOpen=false\n</inputs>')
    edits = [(old_inputs, new_inputs),
             ("    if ($Mode -ne 'ON') { Write-Host 'Weekend/holiday flat: OFF - EAs may hold trades over weekends and holidays.' -ForegroundColor Yellow; return }",
              "    if ($Mode -eq 'OFF') { Write-Host 'News guard: OFF - EAs may trade through news releases (fine in FTMO challenges / Swing, NOT on FTMO funded Standard, The5ers or FundingPips Master).' -ForegroundColor Yellow; return }"),
             ('$id = [DateTime]::UtcNow.Ticks + 999', '$id = [DateTime]::UtcNow.Ticks + 1999'),
             ('    Write-Host ("Weekend/holiday flat: ON - added {0} (Calyx Weekend Flat on {1} H1). It closes EA trades before weekends and holiday closures." -f $name, $Symbol) -ForegroundColor Green\n',
              '    Write-Host ("News guard: ON (+-{2} min) - added {0} (Calyx News Guard on {1} H1). It closes EA trades and blocks EA entries around high-impact news." -f $name, $Symbol, $Mode) -ForegroundColor Green\n'
              '    $updater = Join-Path (Split-Path -Parent $source) \'Update-NewsCalendar.ps1\'\n'
              '    if (Test-Path -LiteralPath $updater) { try { & $updater } catch { Write-Host (\'News calendar download FAILED: {0}. Run Update News Calendar.bat before trading.\' -f $_.Exception.Message) -ForegroundColor Red } }\n'
              '    else { Write-Host \'Update-NewsCalendar.ps1 not found next to Calyx News Guard.ex5: run Update News Calendar.bat before trading.\' -ForegroundColor Red }\n'
              '    Write-Host \'IMPORTANT: run "Update News Calendar.bat" (_00 Live profiles\\Calyx News Guard) once a day, e.g. with Windows Task Scheduler. Without a fresh calendar the guard warns on its chart and cannot block anything.\' -ForegroundColor Yellow\n'),
             ('WEEKEND_FLAT.json', 'NEWS_GUARD.json'), ('Get-CalyxWeekendFlatExpert', 'Get-CalyxNewsGuardExpert'), ('Test-CalyxWeekendFlatChart', 'Test-CalyxNewsGuardChart'),
             ('Add-CalyxWeekendFlatChart', 'Add-CalyxNewsGuardChart'), ('Calyx Weekend Flat', 'Calyx News Guard')]
    for x, y in edits:
        n = body.count(x); assert n >= 1, x[:80]; body = body.replace(x, y)
    assert 'Weekend' not in body and 'weekend' not in body.replace('weekends', ''), 'leftover weekend text'
    head = r'''# >>> Calyx News Guard (owner 2026-11-18: "respect all the trading rules") >>>
# FTMO funded Standard: no execution 2 min before / after selected news (entries, TP, SL, pending orders) - challenges / Swing are exempt.
# The5ers High Stakes: no trades 2 min around high-impact news. FundingPips Master: 5 min (profit removed).
# ON adds one extra chart running "Calyx News Guard": before each High-impact release in Common\Files\CalyxNewsCalendar.csv it closes EA positions
# and deletes EA pending orders on the affected symbols and blocks new EA entries until the window ends. Source: _00 Live profiles\Calyx News Guard.
function Read-CalyxNewsGuard([string]$Current, [bool]$NoPrompt, [string]$Default) {
    if ($Current) { if ($Current -notin @('OFF','2','5')) { throw 'News guard must be OFF, 2 or 5.' }; return $Current }
    if ($NoPrompt) { return $Default }
    Write-Host ''
    Write-Host 'NEWS GUARD - close EA trades and block EA entries around high-impact news?' -ForegroundColor Cyan
    Write-Host '  2   = +-2 minutes: FTMO funded Standard account (no entry / TP / SL inside the window) and The5ers High Stakes.'
    Write-Host '  5   = +-5 minutes: FundingPips Master account (news profits are removed) - also covers the 2-minute firms.'
    Write-Host '  OFF = no news handling: fine in FTMO challenges and FTMO Swing, NOT on the accounts above.'
    Write-Host '  It needs a fresh calendar: "Update News Calendar.bat" (run daily). Trades held at news time are closed ~90 s before the window.'
    Write-Host '  The backtests behind this profile were run WITHOUT the news close.' -ForegroundColor Yellow
    $answer = (Read-Host "News guard: OFF, 2 or 5 [$Default]").Trim().ToUpperInvariant()
    if (-not $answer) { $answer = $Default }
    if ($answer -notin @('OFF','2','5')) { throw 'Answer OFF, 2 or 5.' }
    Write-Host ("News guard: {0}" -f $answer)
    return $answer
}
'''
    out = head + body + '# <<< Calyx News Guard <<<\n'
    (H / 'NewsGuard-Functions.ps1').write_text(out, encoding='utf-8')
    (H / 'NEWS_GUARD.json').write_text(json.dumps(dict(ex5_sha256=sha(H / 'Calyx News Guard.ex5'), source_sha256=sha(H / 'Calyx News Guard.mq5'), built='2026-11-18', version='1.00',
                                                       functions_sha256=sha(H / 'NewsGuard-Functions.ps1')), indent=2) + '\n', encoding='utf-8')
    print('written NewsGuard-Functions.ps1', len(out.splitlines()), 'lines')


if __name__ == '__main__':
    main()
