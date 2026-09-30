# Completion review — 28 September 2026

## Completed scope

- 176 unique main native MT5 cases: 11 assets × 4 frozen variants × 4 overlapping windows (6m, 1y, 3y, 5y).
- Four additional engineering smoke cases; all 180 completed cases passed the final verifier.
- Ten boundary checks, 10,616,996 decision records and 166,583 closed test positions audited. These totals aggregate overlapping runs; they are not independent market observations.
- All eight frozen build/source/configuration/dependency hashes still match `BUILD.json`.
- One additional battery-sleep-interrupted attempt was rejected, preserved and retried with identical settings. It is not counted as a completed case. See `INTERRUPTIONS.md`.

## Decision

Zero of the 22 A/B asset/setup combinations passes the predeclared 3y-and-5y profitability/control gate. Every A/B combination lost money in both long windows. No candidate is selected for parameter optimization, FTMO testing or deployment. This conclusion applies to these frozen rules, not to every possible RSI/MACD strategy.

The most profitable latest-year RSI candidate was BTC B (+15.19%, 53.08% net wins, net PF 1.09, 454 positions), but it lost 31.64% over three years and 64.13% over five years. The highest latest-year candidate win rate was USDCAD A (55.22%), which still lost 1.84%. Full results, controls, costs, drawdown, frequency, streaks and data-quality details are in `REPORT.md` and `RESULTS.json`.

## Interpretation limits

This uses Exness CFD research history, native bid/ask fills, simulated 150 ms execution delay and recorded broker costs, not FTMO fills. Model 4 does not mean all historical ticks were real; missing older ticks can be generated from minute history. All windows overlap and have now been inspected. None is untouched out-of-sample evidence. Requested risk was 1% current equity; shared lot-rounding and broker minimum sizes can exceed that amount. Indicator/clock/ledger checks do not establish live profitability, and ATR was checked from native snapshots rather than independently reconstructed.

## Delivery and live-account boundary

The separate Nasdaq DI ON/OFF launcher change was tested (82 focused tests) and pushed to `new-telegram-copy`, final commit `53d4a171db59371248810cc3560a1dc185e6e1e4` (implementation commit `dd5b449530e66ec6fd6858787e635aaacafa7cff`). BEST RECOMMENDED and FTMO ask for DI ON/OFF, default ON. OFF changes only Nasdaq's DI condition; shared portfolio interactions may still change. FTMO News remains OFF. Pulling code does not change already-running MT5 charts.

This research remains local. No production presets, website results or live account settings were replaced by RSI/MACD candidates. The normal MT5 terminal was not restarted, and the native research grid has exited successfully. Prior PD-sweep and liquidity-continuation work already reached completed rejection decisions; the user-cancelled DI comparison remains cancelled.
