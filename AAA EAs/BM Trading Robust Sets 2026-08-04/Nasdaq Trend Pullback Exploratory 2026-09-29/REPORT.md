# Nasdaq trend-pullback — exploratory review

**No optimized version survived the frozen evaluation gates.** Status: `REJECTED_RECENT_CONFIRMATION`. The user explicitly authorized this search despite the original raw failure. That raw rejection remains on record. Gold, Bitcoin, GBPUSD and the separately deployed Nasdaq 5-minute bot were not changed.

## Like-for-like evaluation

Historical native MT5 tests on Exness USTEC CFD, USD10,000 per run, nominal 1% equity risk rounded UP, 150ms simulated delay and broker-model spread, swap, commission and fees. Model4 uses recorded ticks where present and generated ticks otherwise. Return is cumulative; PF and win rate are net of recorded costs; equity DD is from the full native tester. /month uses elapsed calendar months; /trading day uses UTC weekdays with archived quotes, irrespective of candidate session. Streaks use net closed positions, not full-risk-loss counts.

### Validation — 2024-03-27 to 2025-09-27 exclusive

| Version / test | Return | PF | Equity DD | Trades | /month | /trading day | Win% | W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original | -9.73% | 0.912 | 20.16% | 185 | 10.26 | 0.473 | 30.8% | 3/15 |
| Candidate A | +2.05% | 1.207 | 3.98% | 39 | 2.16 | 0.100 | 38.5% | 4/7 |
| Candidate B | +2.05% | 1.207 | 3.98% | 39 | 2.16 | 0.100 | 38.5% | 4/7 |
| Candidate C | +2.05% | 1.207 | 3.98% | 39 | 2.16 | 0.100 | 38.5% | 4/7 |

- validation-0: passed the frozen validation thresholds.
- validation-1: passed the frozen validation thresholds.
- validation-2: passed the frozen validation thresholds.

### Recent confirmation — 2025-09-27 to 2026-09-27 exclusive

| Version / test | Return | PF | Equity DD | Trades | /month | /trading day | Win% | W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original | +25.22% | 1.443 | 12.11% | 103 | 8.59 | 0.396 | 45.6% | 6/11 |
| Frozen selected candidate | -0.39% | 0.930 | 3.56% | 27 | 2.25 | 0.104 | 40.7% | 3/5 |

Only the validation-selected version was tested here. No failed candidate was retuned or replaced after viewing this result. This year was previously seen for the baseline and is not called an untouched holdout.

**Why it failed:** the selected version lost money, PF 0.930 missed the frozen 1.15 minimum, and 27 positions fell below the 30-position floor. Lower drawdown came with much lower trading activity and did not establish an improved edge. The original performed better in this recent period, but its earlier raw-gate rejection remains valid; neither version is approved for promotion.

![Nasdaq evaluation comparison](C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Nasdaq Trend Pullback Exploratory 2026-09-29/comparison.png)

Chart lines are hourly samples of recorded equity; the table’s drawdowns come from full native tick paths.

## Development finalists — fitted, not validated

2021-09-27 to 2024-03-27 exclusive, faster Model1 one-minute-OHLC screening. Do not compare these figures with Model4 as if their execution quality were identical.

| Version / test | Return | PF | Equity DD | Trades | /month | /trading day | Win% | W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate A | +31.81% | 3.560 | 2.62% | 66 | 2.20 | 0.102 | 54.5% | 5/5 |
| Candidate B | +31.81% | 3.560 | 2.62% | 66 | 2.20 | 0.102 | 54.5% | 5/5 |
| Candidate C | +31.81% | 3.560 | 2.62% | 66 | 2.20 | 0.102 | 54.5% | 5/5 |

The three finalists have identical development trade ledgers, not three independent edges. They differ only in holding/weekend settings that did not change these trades: A has no elapsed holding limit and allows weekends; B has a 960-minute limit and allows weekends; C has a 480-minute limit and disallows weekends. All retain daily-flat logic. The three validation ledgers are also identical. Candidate A won the deterministic first-in-order tie; later outcomes were not used to break it. No replacements were selected after seeing validation.

## Validation-selected version

- Signal: **H1**, EMA50 versus EMA250, fast-EMA slope over 5 bars, pullback touch at EMA20 within the prior 1 bars, then a close beyond the previous bar and pullback EMA. ATR14; all inputs completed bars.
- Entry: limit retest 10 index points. Stop: 3 ATR. Exit: 3R target. Trailing rule: breakeven at 0.5R. Indicator trails use the last computed closed-bar values and update at new signal bars; BE can update on ticks.
- New-order placement session: 09:30–10:59 New York; direction: both; filter: closed H4 EMA50 agreement; weekday exclusion: none. Pending orders can fill later: expiry is four signal bars after placement, capped by the daily cutoff when enabled.
- Capacity: 1 attempts/day, 1 position slot(s), no extra stop-loss reentry. Holding limit: none. Daily flat: on; cutoff 20:00 UTC; weekend holding allowed. Timed exits execute only when quotes are available.
- Risk: nominal 1% equity across available position slots, rounded UP to lot step; minimum-lot, fills and gaps can cause oversizing. This is not a guaranteed loss cap or prop-firm-safe configuration.

## Search coverage

448 development/plateau screen passes; 454 native passes overall; 418 unique parameter vectors (417 after removing explicitly inactive settings, not after deduplicating historical outcomes). Every repeated, losing, empty and execution-flagged test remains counted. Execution flags appeared in 1 pass(es). Including 68 previous raw-study/Nasdaq-confirmation passes gives 522 observed passes for conservative multiplicity accounting; they are not independent trials.

| Version / test | Return | PF | Equity DD | Trades | /month | /trading day | Win% | W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| timeframe stage leader | +38.68% | 1.182 | 16.00% | 282 | 9.41 | 0.434 | 35.1% | 4/10 |
| entry stage leader | +51.70% | 1.277 | 18.92% | 255 | 8.51 | 0.392 | 38.0% | 7/9 |
| stop stage leader | +50.68% | 1.429 | 8.14% | 255 | 8.51 | 0.392 | 52.5% | 8/8 |
| trailing stage leader | +43.00% | 1.527 | 9.56% | 255 | 8.51 | 0.392 | 38.4% | 7/10 |
| rr_exit stage leader | +43.00% | 1.527 | 9.56% | 255 | 8.51 | 0.392 | 38.4% | 7/10 |
| session stage leader | +27.11% | 2.609 | 3.48% | 71 | 2.37 | 0.109 | 50.7% | 5/5 |
| direction stage leader | +27.11% | 2.609 | 3.48% | 71 | 2.37 | 0.109 | 50.7% | 5/5 |
| filters stage leader | +29.73% | 3.060 | 2.62% | 69 | 2.30 | 0.106 | 52.2% | 5/5 |
| management stage leader | +29.73% | 3.060 | 2.62% | 69 | 2.30 | 0.106 | 52.2% | 5/5 |
| signal stage leader | +31.81% | 3.560 | 2.62% | 66 | 2.20 | 0.102 | 54.5% | 5/5 |

This is a broad staged top-three search, not an exhaustive Cartesian search or a proven global optimum. D1 was excluded as a different daily-clock hypothesis; market-on-close and next-bar-open collapse to the same executable quote; news filtering was excluded without a verified point-in-time historical calendar. See PROTOCOL.md and DIMENSION COMPARISONS.md for the full tested scope.

Joint neighborhood checks (development only):

- Candidate A: axes sl, rr, offset; 100.0% profitable and execution-clean neighbors; median PF 2.459; passed. A plateau does not guarantee later profitability.
- Candidate B: axes sl, rr, offset; 100.0% profitable and execution-clean neighbors; median PF 2.459; passed. A plateau does not guarantee later profitability.
- Candidate C: axes sl, rr, offset; 100.0% profitable and execution-clean neighbors; median PF 2.459; passed. A plateau does not guarantee later profitability.

## Execution, risk and evidence

- Original recent year: native equity DD 12.11%, balance DD 11.09%; initial stop-risk maximum 1.074%; 2 cross-date positions, 2 with swap, 3 delayed timed exits, longest hold 58.00h; execution flags none; partial-close skips 0.
- Original validation: native equity DD 20.16%, balance DD 18.50%; initial stop-risk maximum 1.026%; 7 cross-date positions, 4 with swap, 10 delayed timed exits, longest hold 57.00h; execution flags none; partial-close skips 0.
- validation-0: native equity DD 3.98%, balance DD 3.22%; initial stop-risk maximum 1.025%; 4 cross-date positions, 2 with swap, 6 delayed timed exits, longest hold 55.99h; execution flags none; partial-close skips 0.
- validation-1: native equity DD 3.98%, balance DD 3.22%; initial stop-risk maximum 1.025%; 4 cross-date positions, 2 with swap, 6 delayed timed exits, longest hold 55.99h; execution flags none; partial-close skips 0.
- validation-2: native equity DD 3.98%, balance DD 3.22%; initial stop-risk maximum 1.025%; 4 cross-date positions, 2 with swap, 6 delayed timed exits, longest hold 55.99h; execution flags none; partial-close skips 0.
- Selected recent year: native equity DD 3.56%, balance DD 2.46%; initial stop-risk maximum 1.027%; 1 cross-date positions, 1 with swap, 3 delayed timed exits, longest hold 55.99h; execution flags none; partial-close skips 0.

Delayed-exit diagnostics compare explicit elapsed, daily and Friday cutoffs; they do not reconstruct the historical broker holiday calendar or every session-exit deadline. Quote-gap delays remain in P&L, with no invented calendar-time fills. The exploratory override does not certify a strictly intraday system. Any surviving version with unintended carryovers needs a separately specified execution remedy before such a claim. Negative net breakeven exits count as losses.

Baseline engine parity matched all 103 original recent-year positions and $2,521.70 net. Independent verification passed 324 numerical/causality windows, 103 native baseline signal checks and 454 archived native-case ledgers (72,848 position rows). Compile logs, exact case tables, source/EX5 and native cash reconciliation are retained. Signal checks do not independently reproduce every optional execution branch.

The regime skill influenced past-only state estimation and future-data mutation checks. Its packaged runner was absent; the local optional Markov filter uses 20-bar returns and past transitions as explicitly documented, not GARCH/HMM. An apparent regime or a profitable optimized backtest is not proof of predictive skill.

## Limitations and stop point

Recorded real ticks on this broker feed begin 2026-01-01. Earlier tests use generated ticks, and displayed history percentages include warm-up. Broker fee schedules are not an independently verified historical series; the fixed delay is not measured live slippage. Selection after many variants creates bias. Previously seen baseline periods are not pristine holdouts.

The pipeline stopped at the rejection above. No failed evaluation was optimized again. Any later holdout, full-window candidate confirmation, control, Monte Carlo/deflated-Sharpe, additional-cost stress, FTMO scenario, portfolio integration or deployment not recorded here **was not completed**. A development winner is not a surviving edge.

No normal MT5 session was restarted or configured, and no live orders, production SET, installer, website or Git push were made. Await user review before Bitcoin/GBPUSD.

Method references: [MT5 real/generated ticks](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation), [weekday session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade). Exact artifacts: ALL NATIVE RESULTS.json, SEARCH RESULTS.json, run-config-search.json, PARITY.json, VERIFICATION.json, VERDICT.json and native/. Private connection INIs and raw account-identifying reports are excluded from the review ZIP.
