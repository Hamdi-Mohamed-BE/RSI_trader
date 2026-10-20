BTC WEEKEND HOLD — RESEARCH ONLY

Original rule: buy BTCUSD Friday17:00 NewYork, sell Sunday17:00 NewYork.
Each wall-clock endpoint independently follows America/New_York daylight saving.
This is the conventional FX weekend; Bitcoin itself does not reopen on Sunday.

Primary reference: $10,000, one-times-current-cash allocation, no borrowing.
It is NOT 1% stop-risk sizing. The original rule has no protective stop.
The search is gross M5 OHLC; native broker-lot-rounded costed replay is separate.

Frozen split:
  Development: 2018-01-01 to2023-10-17 exclusive.
  Older validation: 2023-10-17 to2024-10-17 exclusive.
  Retrospective OOS: 2024-10-17 to2026-10-17 exclusive.
The OOS history was previously inspected. It is NOT untouched data.
October16–18,2026 is incomplete at the end date and must be censored.

Safety:
  EA/BtcWeekend.mq5 refuses non-tester execution.
  Only the fixed isolated portable research terminal may be launched.
  No active account orders, production EA/BAT/site changes or new Git push.
  Private runtime INIs and journals remain local; never publish them.

Reproducibility:
  PLAN-FREEZE locks the original protocol and date split before search.
  SELECTION LOCK fixes the development/older-validation result before OOS.
  FROZEN locks source, data, numerical engines, execution source and selection.
  Every tried unique configuration is counted; inactive fields deduplicate.
  Failed technical runs remain in native/ with their receipts, never overwritten.
  Exporter simulation-start shift was accepted ONLY for no-order CopyRates
  capture with independently verified requested endpoints, not a trading test.
  Native feature warmup is a hashed prefix containing no post-start prices.

Entry points (use an environment with numpy, scipy, bs4, pandas and pytest):
  native.py export                # isolated MT5 source capture, explicit launch
  run_pipeline.py preflight       # all-OHLC, units, bounds and hashes
  run_native.py raw               # pre-OOS native fast screens, explicit launch
  run_pipeline.py development     # refuses a second search after selection lock
  run_pipeline.py freeze          # persist final source/config receipts
  run_pipeline.py evaluate        # final/baseline only, refuses OOS rerun
  run_native.py confirm           # isolated Model4 and parity tests
  run_pipeline.py report          # render existing evidence without reselection

Results.html is the human-readable report. FINAL.json is its complete evidence
input. No missing prices or spreads are invented; unavailable/failed gates stay
unavailable/failed. Conditional complete-week sensitivities are not full-period
proof. Model4 may fall back to generated ticks. Native financing/commission uses
the tester's present contract/account settings, not historical reconstruction.
Monte Carlo is empirical resampling, not a future profit or prop-pass probability.
