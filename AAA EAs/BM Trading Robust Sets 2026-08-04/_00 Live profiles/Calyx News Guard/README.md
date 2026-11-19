# Calyx News Guard (2026-11-18)

Owner 2026-11-18: "respect all the trading rules". A helper EA on one extra chart (like Calyx Weekend Flat) that keeps the EAs out of high-impact news windows.

Why (firm answers by email, 2026-11-17/18):
- FTMO funded Standard: no execution (market, TP, SL, pending fill) from 2 min before to 2 min after selected news. Challenges and FTMO Swing are exempt.
- The5ers High Stakes: no trades 2 min around high-impact news.
- FundingPips Master: closing a trade within 5 min of news is a soft breach (profit removed).

What it does:
- Reads `%APPDATA%\MetaQuotes\Terminal\Common\Files\CalyxNewsCalendar.csv` (`utc_epoch,currency,impact,title`).
- A symbol is affected when its base or profit currency equals the event currency (XAUUSD / USTEC / US30 by USD, UK100 by GBP, USDJPY by USD and JPY).
- 90 s before the window (`InpCloseLeadSeconds`) it closes EA positions (magic != 0; manual trades only with `InpIncludeManual=true`) and deletes EA pending orders on
  affected symbols, then sets global variable `CNB_<symbol>` = window end (server time). EAs built with the Calyx No Opposite shim v2 refuse new entries while
  `InpCalyxNewsBlock=true` and `CNB_<symbol>` is in the future (guarded Best 1-Step: checked inside the FTMO 1-Step guard lock).
- Missing or stale calendar (fetched > `InpStaleHours` 36 h ago) -> hourly journal warning; events that are not in the file are never blocked.

Files: `Calyx News Guard.mq5/.ex5` (compiled 0/0), `Update-NewsCalendar.ps1` + `Update News Calendar.bat` (ForexFactory public weekly feed, plain GET, keeps 14 days),
`make_functions.py` -> `NewsGuard-Functions.ps1` (installer functions, generated from the weekend-flat functions with asserted edits) + `NEWS_GUARD.json` (hashes the installers check).

Installer question (Best 1-Step, both BATs): `News guard: OFF, 2 or 5` (`-NewsGuard OFF|2|5`). Guarded default: Funded phase 2, Challenge OFF. No guard default 5.

Tests:
- `test/run_test.py` (native Model 4, XAUUSD M5, 2 test USD events): positions closed at 15:23:30 / 18:53:30 (lead 90 s before the -5 min window), 0 opens inside the block,
  opens resume after it -> PASS (`test/RESULTS.json`).
- Installer functions (sandbox, fake data folder, APPDATA redirected): chart written with the chosen minutes, EX5 copied, calendar downloaded, OFF adds nothing -> PASS.
- Not tested natively: the block read by a strategy EA (the tester runs one EA, so guard + strategy cannot share global variables there). Code path: same key, same broker symbol.

Limits:
- Run `Update News Calendar.bat` every day (Task Scheduler). ForexFactory "High" is not FTMO's exact "selected news" list.
- Backtests and FTMO simulations behind the profiles were run WITHOUT news closes; the effect on results is unknown (no long news history in the repo).
- Positions are closed at market ~90 s before the window: spread and slippage cost is not modelled.

## 2026-11-20 v2: FTMO calendar first, ForexFactory fallback (owner: "use the FTMO calendar, if it fails then ForexFactory if possible")
- `Update-NewsCalendar.ps1` now reads FTMO's public calendar API (https://gw2.ftmo.com/public-api/v1/economic-calendar, the data behind ftmo.com/en/calendar/;
  week-by-week requests, the API refuses long ranges). Only events with `restriction: true` (FTMO's restricted news) are written as "High"; the rest as
  "ftmo-<impact>" (ignored). Currency from FTMO's "instrument" field (e.g. "USD + US Indices + XAUUSD + DXY" -> USD). If FTMO cannot be reached it falls back to
  the ForexFactory weekly High-impact feed (old behaviour). `-Source FTMO|ForexFactory|Auto`. No change to the EA (it acts on impact "High").
- Tested 2026-11-20: FTMO 253 events / 20 restricted (e.g. FOMC Minutes USD, UK Core CPI GBP); forced ForexFactory OK; FTMO unreachable -> fallback OK.
- `Register-NewsCalendarTask.ps1`: daily task "Calyx News Calendar" via the ScheduledTasks module (06:00 + 18:00, catch-up after the PC was off). The old
  schtasks.exe call failed on the space in the path ("Invalid argument/option - 'EAs\BM'"). Used by Ready for FTMO and the all-in-one setup. Registered and
  run once on this PC (result 0; the real calendar file now comes from FTMO).
- FTMO's "instrument" can also be e.g. Crude Oil / DAX: written as their own code, no traded symbol matches it.
