# IVB US100 quote-count proxy

RAW REAL-TICK BASELINE REJECTED

| Window | Return | Net PF | Win rate | Native equity DD | Trades | Closed Sharpe | Max win/loss run | Tick evidence |
|---|---|---|---|---|---|---|---|---|
| real-2026 | -2.83% | 0.797 | 50.0% | 8.60% | 30 | -0.65 | 4/5 | 100% real ticks |
| 6m | -4.07% | 0.621 | 42.9% | 8.05% | 21 | -1.4 | 4/5 | 100% real ticks |
| 1y | -9.57% | 0.698 | 46.2% | 12.38% | 65 | -1.33 | 4/5 | 75% real ticks |
| 3y | -9.78% | 0.878 | 50.6% | 20.41% | 172 | -0.46 | 5/6 | 25% real ticks |
| 5y | -9.78% | 0.878 | 50.6% | 20.41% | 172 | -0.36 | 5/6 | 15% real ticks |

- User explicitly requested Exness US100 rather than paid NQ history. This is a bid-quote uptick-count minus downtick-count proxy. It is NOT aggressor-side contract volume, footprint delta, or independent proof of Fabio Valentini’s model.
- NY08:30–09:00 range, first later completed M5 close above high and quote-count delta>=200; long only. Cumulative delta filter OFF. One qualifying attempt/day. Next-tick entry, SL range low, fixed1:1 target from entry quote. No trailing, BE, optimisation or extra filters.
- Corrected the published code’s entry-at-EOD sequencing hazard by requiring entry strictly before14:00 NY and closing at14:00/session pre-close. Source this-bar-close fill replaced by causal next-tick market order. $10k/1% balance sizing is not a fixed1NQ-contract reproduction.
- Older history uses GENERATED TICKS. Their price paths manufacture up/down counts, so1/3/5year results are diagnostics only, not validation of this filter. Primary evidence is2026 real ticks and latest6months, each100% real ticks. These are small, overlapping samples, not independent holdouts.
- Native Model4,150ms delay, CFD spreads/commission/swap included. Broker-measured incremental-cost stress missing. The broker may emit same-bid/ask-only events: those contribute zero; seed is last completed M1 bid close before signal.
- Signal-bar quote counts independently recomputed from exported ticks; timestamps, range snapshots, stops/targets, risk-budget sizing and net-ledger sums verified. Opening-range snapshots and preceding-bid seed were exported by the EA, not independently recovered from a separate historical data source.
- 460 closed positions across overlapping windows checked; 3,361,327 quote ticks recounted. Maximum filled stop-risk/budget ratio: 1.041×. The 1% setting is requested pre-cost risk, not an absolute loss guarantee; adverse fills/fees/gaps can exceed it.
- Native equity DD includes floating losses. Closed-balance plots exclude them; floating plot is sampled once/minute and is not the exact tick-path DD.10,000 block-bootstrap paths/block5 are diagnostics, not profit or FTMO pass/payout forecasts.
- No prospective forward test, calibration or live promotion. Prior IVB/FRVP source is a different model and remains unchanged. Active MT5 account, EAs, BATs, website and Git remote untouched; no paid data downloaded.
