# Intraday time-of-day bias: 13-market test

Research as of 29 September 2026. Same-feed Exness CFD five-minute history; 2021-09-27–2026-09-27 (end exclusive).

**0 of 13 selected candidates survived every frozen gate.** This is a historical research screen, not a live strategy recommendation.

The screen used **5,051,182 five-minute bars** and evaluated **10,826 distinct development configurations** after removing duplicate schedules. All 13 selected candidates are shown below; some failed even the development threshold and are included for transparency, not as qualified strategies.

**Closest candidate: gold, long at 23:00 London, hold two elapsed hours.** Its PF was 1.39 / 1.42 / 1.48 across development / validation / holdout, and it remained positive under modeled cost stress. Nevertheless, the 23:30 neighboring start lost money in development, and its final-year evidence did not pass the 13-market multiple-testing correction (adjusted p=0.55). The 22:30 neighbor has very few eligible observations because of market closures/rollover, so it is not a strong comparison by itself. Gold is an interesting unconfirmed observation, not a validated survivor.

## What was tested

Half-hour entry times × 30/60/120-minute holds × long/short × UTC/New York/London clocks. Daylight saving handled. Exactly one development-ranked candidate per instrument; no replacement after validation or holdout. Development ends 26 March 2024, validation ends 26 September 2025, final holdout is 27 September 2025–26 September 2026. Dates overlap prior unrelated research, so this is untouched by this search, not globally pristine data.

Baseline deducts a recorded/development-median spread proxy. Stress doubles that spread and adds two minimum price ticks. Commission is not separately modeled. Windows spanning 17:00 New York or missing bars are excluded. Crypto uses available weekends. UTC half-hour same-day, same-horizon/side average is the time-specificity control, used for evaluation only.

## Final holdout — selected candidates, including failures

Times below belong to the specified clock; NY/London follow DST, not fixed UTC offsets. A positive holdout alone does not pass an earlier failure.

| Market | Selected direction / entry / hold | Dev PF | Validation PF | Holdout PF | Holdout net bps/trade | Stress bps/trade | Trades | Adjusted p | Result |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| US30 | LONG 13:30 UTC / 30m | 1.18 | 0.93 | 0.80 | -2.05 | -3.03 | 257 | 1.0000 | FAIL |
| USTEC | LONG 13:30 America/New_York / 120m | 1.10 | 0.88 | 0.84 | -2.30 | -3.40 | 247 | 1.0000 | FAIL |
| US500 | LONG 13:30 America/New_York / 120m | 1.06 | 0.88 | 0.81 | -2.21 | -3.60 | 247 | 1.0000 | FAIL |
| XAUUSD | LONG 23:00 Europe/London / 120m | 1.39 | 1.42 | 1.48 | 5.68 | 5.39 | 199 | 0.5498 | FAIL |
| BTCUSD | LONG 05:30 America/New_York / 120m | 1.05 | 0.90 | 0.88 | -2.25 | -3.76 | 365 | 1.0000 | FAIL |
| ETHUSD | SHORT 01:30 Europe/London / 120m | 1.04 | 0.91 | 1.00 | -0.03 | -5.10 | 364 | 1.0000 | FAIL |
| EURUSD | SHORT 07:30 America/New_York / 30m | 1.54 | 1.02 | 1.02 | 0.04 | -0.57 | 257 | 1.0000 | FAIL |
| GBPUSD | SHORT 12:30 Europe/London / 30m | 1.28 | 0.77 | 0.76 | -0.70 | -1.24 | 257 | 1.0000 | FAIL |
| USDJPY | LONG 00:00 America/New_York / 120m | 1.28 | 0.73 | 1.00 | -0.01 | -0.53 | 258 | 1.0000 | FAIL |
| AUDUSD | LONG 01:00 UTC / 120m | 1.19 | 1.07 | 0.78 | -1.45 | -2.76 | 258 | 1.0000 | FAIL |
| NZDUSD | SHORT 17:30 UTC / 30m | 1.50 | 0.84 | 0.66 | -1.01 | -2.56 | 258 | 1.0000 | FAIL |
| USDCAD | LONG 11:00 UTC / 120m | 1.16 | 0.93 | 0.77 | -1.02 | -1.68 | 257 | 1.0000 | FAIL |
| USDCHF | LONG 11:30 America/New_York / 120m | 1.13 | 0.99 | 0.96 | -0.18 | -1.19 | 258 | 1.0000 | FAIL |

1 bp = 0.01%. PF = sum of profitable trade returns / absolute sum of losing trade returns. Adjusted p is Holm across 13 finalists, using the worse of net-return and excess-over-control bootstrap tests. It is not the probability the strategy is false.

## Holdout performance at fixed notional, without leverage

Return is cumulative net P&L as a percentage of a constant reference notional; no compounding. Drawdown is five-minute-close mark-to-market, not tick-level maximum drawdown; the finer tick path can contain larger adverse excursions. Trades/day divides by all available UTC trading dates, including partial Sunday reopenings for FX/indices/gold and weekends for crypto. Non-crypto entry rules exclude Sundays, so this ratio is lower than trades per eligible weekday.

| Market | Trades/month | Trades/day | Return % | Win % | Marked DD % | Max W / L streak | First / second half mean bps |
|---|---:|---:|---:|---:|---:|---:|---:|
| US30 | 21.4 | 0.82 | -5.28 | 50.2 | 6.85 | 7 / 7 | -1.15 / -2.95 |
| USTEC | 20.6 | 0.79 | -5.69 | 49.0 | 10.24 | 11 / 10 | -1.13 / -3.45 |
| US500 | 20.6 | 0.79 | -5.45 | 50.6 | 7.96 | 8 / 10 | -1.28 / -3.11 |
| XAUUSD | 16.6 | 0.64 | 11.31 | 53.3 | 4.35 | 8 / 6 | 8.78 / 2.75 |
| BTCUSD | 30.4 | 1.00 | -8.22 | 48.2 | 13.50 | 7 / 10 | -2.78 / -1.72 |
| ETHUSD | 30.4 | 1.00 | -0.10 | 49.5 | 18.72 | 9 / 6 | -2.03 / 2.00 |
| EURUSD | 21.4 | 0.82 | 0.11 | 54.1 | 1.27 | 9 / 6 | -0.53 / 0.61 |
| GBPUSD | 21.4 | 0.82 | -1.81 | 49.8 | 2.59 | 6 / 9 | -1.54 / 0.13 |
| USDJPY | 21.5 | 0.83 | -0.02 | 53.1 | 2.00 | 7 / 7 | 0.88 / -0.88 |
| AUDUSD | 21.5 | 0.83 | -3.75 | 47.3 | 5.59 | 6 / 8 | 0.49 / -3.36 |
| NZDUSD | 21.5 | 0.83 | -2.60 | 49.2 | 2.96 | 8 / 6 | -0.89 / -1.13 |
| USDCAD | 21.4 | 0.82 | -2.62 | 48.2 | 3.30 | 6 / 6 | -1.55 / -0.50 |
| USDCHF | 21.5 | 0.83 | -0.46 | 48.1 | 2.87 | 7 / 11 | -1.62 / 1.24 |

## Why each one passed or failed

- **US30**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -5.05 bps, time-specific excess -4.20 bps.
- **USTEC**: development: PF below 1.15; validation: PF below 1.15; validation: net mean not positive; validation: no time-specific excess; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -5.84 bps, time-specific excess -4.84 bps.
- **US500**: development: PF below 1.15; development: neighbor -30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: no time-specific excess; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -5.19 bps, time-specific excess -3.93 bps.
- **XAUUSD**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net 0.58 bps, time-specific excess 1.21 bps.
- **BTCUSD**: development: PF below 1.15; development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: no time-specific excess; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -6.57 bps, time-specific excess -4.07 bps.
- **ETHUSD**: development: PF below 1.15; development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -8.08 bps, time-specific excess -4.02 bps.
- **EURUSD**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -0.56 bps, time-specific excess -0.03 bps.
- **GBPUSD**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -1.48 bps, time-specific excess -0.97 bps.
- **USDJPY**: validation: PF below 1.15; validation: net mean not positive; validation: no time-specific excess; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -1.17 bps, time-specific excess -1.02 bps.
- **AUDUSD**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: neighbor -30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -3.07 bps, time-specific excess -2.17 bps.
- **NZDUSD**: development: neighbor -30m nonpositive/empty; development: neighbor +30m nonpositive/empty; validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -1.77 bps, time-specific excess -0.22 bps.
- **USDCAD**: validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: no time-specific excess; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -2.20 bps, time-specific excess -1.51 bps.
- **USDCHF**: development: PF below 1.15; validation: PF below 1.15; validation: net mean not positive; validation: neighbor -30m nonpositive/empty; validation: neighbor +30m nonpositive/empty; holdout: PF below 1.15; holdout: net mean not positive; holdout: higher costs erase mean; holdout: losing half-year; holdout: lower confidence bound not positive; holdout: Holm multiple-test threshold. One-sided 95% lower mean bounds: net -1.45 bps, time-specific excess -0.59 bps.

## Data and limitations

All symbols are Exness broker CFDs. US100 = USTEC, SP500 = US500, XAU = XAUUSD; the seven FX majors are EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD and USDCHF. No claim of interchangeability with another broker, index futures or exchange crypto.

M5 spreads are not executable bid/ask tick histories. Zero spreads use development-only positive-spread floors; this is a proxy, not historical spread reconstruction. The higher-cost scenario is hypothetical, not measured slippage. No financing across the excluded rollover; gaps and missing bars are rejected. Fixed-notional return estimates are not a position-sizing or prop-firm model.

The bootstrap uses five-day circular blocks, 10,000 paths. It preserves short local dependence but cannot guarantee future regime stability, rule validity, independent-feed replication or data integrity beyond the checks saved here. One selected candidate per asset is a conservative bounded search; a failed winner does not prove no other intraday strategy exists. No news, weekday, volatility or entry-minute refinements were searched after seeing holdout.

The collector made no orders. These are Python bid-bar replays on native-exported history, **not native strategy backtests**. No survivor is promoted or deployed.

## Evidence files

- RULES.md: protocol frozen before outcomes.
- FINALISTS.json: development-only selection and hashes.
- development-grid.csv: all distinct tested development configurations.
- DATA_AUDIT.json / COLLECTION.json: coverage, cost floors and data hashes.
- selected-trades.csv.gz: full selected-candidate trade ledger.
- period-results.csv / RESULTS.json: detailed three-period metrics, bootstrap results and rejection reasons.
- VERIFICATION.json / TEST_RESULTS.txt: 14 passing unit tests, source-file hashes, independent recalculation of every holdout trade and correction, and live-terminal/production preservation checks. All common OHLC bars in the seven FX archives matched an earlier same-feed export exactly.
- METHODS_SOURCES.md: official broker clock/rollover documentation, bar-spread limitations and the corrected data-collector attempt. No native trading confirmation was run because every frozen candidate failed the research screen.

## Research context

Searching many seasonal trading rules can manufacture impressive in-sample results; this is why this study separates selection, validation and final tests. [Bailey et al., Backtest Overfitting in Financial Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2731886). The paper motivates safeguards; it does not validate any result above.
