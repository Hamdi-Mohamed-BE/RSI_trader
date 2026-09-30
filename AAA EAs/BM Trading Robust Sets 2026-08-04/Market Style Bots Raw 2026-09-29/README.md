# Market-style research bots

One compiled MT5 research EA implements four rule sets. Six named presets select the six tested asset/model pairings. It deliberately refuses to initialize outside Strategy Tester. This is not a production or funded-account deployment package.

| Preset | Exact tested broker symbol | Model |
|---|---|---|
| nasdaq-trend.set | USTEC | Trend pullback |
| bitcoin-reversal.set | BTCUSD | Shock reversal |
| gold-volatility.set | XAUUSD | Volatility-state momentum |
| eurusd-range.set | EURUSD | Range fade |
| gbpusd-range.set | GBPUSD | Range fade |
| usdjpy-range.set | USDJPY | Range fade |

The backtest feed was Exness-MT5Trial16. These are broker CFDs, not exchange futures or crypto spot. Different broker symbols, spreads, trading sessions, specifications, data or execution models can change the results.

## Reproduce in an isolated Strategy Tester

Load `MarketStyles.ex5` and the appropriate preset on the listed symbol. Indicators always use completed H1 data internally. The native tests used the M1 tester period, a $10,000 USD deposit, 1:2000 leverage and 150ms execution delay. Model 1 was the preliminary long-history screen; Model 4 was used for recent periods and the qualified gold long-history confirmation. Recorded real ticks begin in January 2026; earlier history is generated, not recorded real ticks.

Choose a trading start date with `InpTradeFrom`, start the tester 90 calendar days earlier for warmup, and use an exclusive end date. The bundled presets start trading on 2021-09-27; the comparison ends on 2026-09-27. Full dates and rules are in `RULES.md` and `run-config.json`.

All presets target 1% equity stop risk, with volume rounded UP to the broker's minimum/step. That is not a hard 1% loss cap: rounding, gaps, fills and costs can increase the loss. No martingale or averaging is used. The Nasdaq bot had historical overnight/session exceptions; those results are retained and explicitly flagged, not approved for deployment.

`InpControl=true` replaces the signal's direction with the frozen random-direction comparator. It does not randomize entry times. Do not mix control results with the raw bot's results.

Read `REPORT.md` for qualification, all windows, controls and limitations. `comparison.png` shows recent-year closed balance, not intratrade drawdown. No rule or threshold was optimized after inspecting these outcomes. A raw shortlist pass is not an untouched out-of-sample or full-pipeline pass.

The shareable ZIP includes source, binary, presets, rules, report, chart, results and verification metadata. It excludes account configuration, tester INIs and credentials. Full local price data and native evidence remain in the study directory.
