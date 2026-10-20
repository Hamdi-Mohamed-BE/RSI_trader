# Calyx ops monitor (2026-10-20)

Built after the owner's "do them all" on the AI Trading Library review: kill switches, a go-live checklist and the weekly/monthly reviews.

- **Read-only.** No orders, no EA attachment, no SET/BAT/guard changes, no MT5 start or restart.
- **Normal terminal only when already running.** `fetch_live.py` attaches to the normal terminal only if it is already running, and it never touches Ava.
- **Backtests stay isolated.** They run only on the isolated tester `_Backtests/MT5-DMC-20260811`, one at a time.

Run everything from `AAA EAs/EA store` with `uv run python "../BM Trading Robust Sets 2026-08-04/_Ops Monitor/<tool>.py" …`. Use `PYTHONIOENCODING=utf-8` on Windows consoles.

## Weekly routine (about 30 min, mostly unattended)

1. **Snapshot the demo account.** `fetch_live.py --since 2026-09-01`
   - Saves a masked login, the account state, Algo Trading state, deals and open positions to `output/live/` (git-ignored).
2. **Backtest the same week.** `debrief_backtest.py --start <Mon> --end <next Mon>`
   - Every non-news EA, frozen EX5 + SET, isolated tester.
   - Long-warm-up EAs (Month End, 3 Way Gold) take about 20 minutes each.
3. **Refresh the event sheet.** `event_sheet.py --past-start <date> --past-end <≤ FXMacroData latest> --ahead 14`
   - Official NFP/CPI/FOMC times, with a count check, timezone lines and a DST-gap flag.
   - Includes a demo news-entry timing audit.
   - `--extend-tester` writes a research copy of the verified tester calendar.
   - Fail-closed: it refuses a window past the provider's latest verified date.
4. **Compare and write the memo.** `live_debrief.py --start <Mon> --end <next Mon> --risk-pct <live %>`
   - Matches backtest trades with demo trades per EA (MATCH, TIMING, EXIT_DIFF, OPEN_ON_DEMO, MISSED, EXTRA).
   - Flags off-roster EAs and gives each EA a kill-switch status.
   - Ends with **one proposed change**; the owner decides.
   - Output: `output/debrief/<window>/DEBRIEF.md`.

## Monthly and when evidence changes

- `kill_switch.py`: per-EA WATCH/KILL thresholds in R from a day-block bootstrap of the cached native evidence.
  - WATCH = p95 of the 3-month drawdown or losing streak.
  - KILL = max(p99, worst 63-day window in history).
  - Output: `output/KILL_SWITCHES.md`.
- `go_live.py monthly --month YYYY-MM`: KEEP / ENFORCE / QUESTION / WATCH / KILL / OFF-ROSTER per EA. At most one switch-off and one re-wire per month.
- `go_live.py checklist`: the six go-live questions per EA. Questions 5 (allowed in writing) and 6 (owned) are for the owner.
- `dependence_audit.py`: best-day / best-trade dependence for every catalogue EA (5y / 3y / 1y).
- `report_dependence.py --study <folder>`: adds the best-day section to a study report.

## Related

- [`Calyx Research Pipeline/robustness.py`](../../Calyx%20Research%20Pipeline/robustness.py): shared module, tested in `test_robustness.py`.
- [`FTMO Dial Study 2026-10-20/REPORT.md`](../FTMO%20Dial%20Study%202026-10-20/REPORT.md): sizing by room to the FTMO floor.
- `/bear-review`: project skill at `ai trader/.claude/skills/bear-review/`. Run it in a fresh session before optimisation or promotion decisions.
- `PIPELINE.md`: amended 2026-10-20 (stage 4 best-day falsifier and Bear review, stage 9 monitoring).
