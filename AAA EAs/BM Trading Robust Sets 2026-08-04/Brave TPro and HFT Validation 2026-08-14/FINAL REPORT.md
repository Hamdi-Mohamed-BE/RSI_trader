# Brave TPro and HFT source validation

## Decision

No new EA from this batch qualifies for the active MT5 installer.

- The TPRO video does not disclose a complete algorithm. It is an update/teaser and says a later part will contain the finished indicators and live trading. Building an "exact" 91% win-rate EA from this source would require inventing the missing rules.
- The HFT video is a systems-architecture explanation, not a trading strategy. It describes exchange-native infrastructure that a retail MT5 CFD EA cannot reproduce.
- The closest legal, data-backed HFT proxy already present in this workspace was rerun against its frozen BTCUSDT holdout. It failed after fees and slippage.

The synchronized BAT, active charts, and active EAs were not changed.

## Source 1 — TPRO / DMC video

Source: https://www.youtube.com/watch?v=XAynkl5rRw4&t=1s

The video publicly states the following:

- NQ, one contract per trade.
- A DMC-based system with a daily long/short bias.
- Three entry families: market-open/one-hour-candle entry, four-hour-close entry, and a pullback/reclaim into trend.
- The speaker's current mechanical DMC approximation had roughly four trades per week, about 22 NQ points per trade, a 42% win rate, and a maximum drawdown claim of about 400 points.
- The new TPRO idea is described as a cyclical accumulation/distribution classifier that decides whether to follow or counter trend.
- TPRO claims: 173 trades, nine stops, about 91% wins, and PF 3.1.

Critical omissions:

- No numerical definition of accumulation, distribution, daily bias, or phase transitions.
- No exact entry, stop, target, time window, exit, commission, slippage, test period, or data source.
- The presenter says the live-tested sample covers only the previous couple of days and that the final working indicators/live-trading part is still coming.

### Nearest reproducible DMC evidence already tested

The earlier public DMC framework was already implemented transparently as `AAA Final DmC Video EA` and tested with native MT5 Every Tick/random delay. It is not claimed to be TPRO.

| Test | Return | PF | Win rate | Trades | Max equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---|
| USTEC development selection | +16.36% | 1.22 | 40.00% | 105 | 7.08% | Development only |
| USTEC untouched 2026-04-07 to 2026-08-06 | -3.16% | 0.92 | 31.03% | 58 | 11.16% | Reject |
| USTEC frozen full-year reference | +14.51% | 1.12 | 37.20% | 164 | 11.59% | Not deployable because holdout lost |

This is the honest benchmark until the creator publishes deterministic TPRO rules.

## Sources 2 and 3 — HFT architecture and strategy catalogue

Sources:

- https://www.youtube.com/watch?v=iwRaNYa8yTw
- https://www.daytrading.com/hft-strategies

The video explains an HFT pipeline: direct multicast exchange feeds, ultra-low-latency NICs/kernel bypass, in-memory replicated order books, lock-free event streams, nanosecond clocks, optional FPGA tick-to-trade logic, strategy engines, pre-trade risk, smart order routing, order management, and latency monitoring.

The article lists strategy families such as market making, cross-market/latency arbitrage, order-flow prediction, order-book imbalance, liquidity/iceberg detection, mean reversion, and pair trading. It also notes that these methods depend on market microstructure and specialized infrastructure.

None of that becomes an honest HFT EA merely by running MQL5 quickly. A broker CFD terminal normally lacks exchange queue position, deterministic passive fills, multi-venue routing, nanosecond event timestamps, and co-location.

## Rerun: BTCUSDT order-flow proxy

The closest testable, legal subset used public Binance futures data:

- Liquidity sweep and close-back-inside reversal.
- Taker-flow/CVD confirmation.
- Aggregate depth imbalance and replenishment proxies.
- M15 decisions, next-bar entry, 1% equity risk, maximum 3x notional leverage.
- 0.05% taker fee per side, 0.01% slippage per side, and actual historical funding.
- Training: 2024-08-11 through 2026-02-10.
- Untouched holdout: 2026-02-11 through 2026-08-10.

### Training selection

The least-bad configuration returned +12.88%, PF 4.36, 78.95% wins, and 1.91% maximum drawdown, but only 19 trades. No candidate passed the predeclared robustness gate.

### Untouched holdout rerun

| Model | Return | Final balance | PF | Win rate | Trades | Max DD | Fees | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Full order-flow filter | 0.00% | $10,000.00 | N/A | N/A | 0 | 0.00% | $0.00 | Failed: signal disappeared |
| CVD without depth filter | -44.50% | $5,550.17 | 0.46 | 37.43% | 187 | 45.09% | $3,794.34 | Reject |
| Price sweep only | -67.06% | $3,293.99 | 0.49 | 37.74% | 371 | 67.52% | $5,706.03 | Reject |

The flat full-filter curve is not a safe result; it means the frozen signal produced no unseen trades.

## What would be required for a genuine next test

1. Wait for the promised final TPRO video or obtain the exact deterministic rules and original trade log.
2. For HFT/order-book research, record at least 8–12 weeks of tick-by-tick L2 book deltas, trades, cancellations, exchange timestamps, local receive timestamps, order acknowledgements, and fills.
3. Validate in event time with queue-aware passive-fill simulation and an untouched forward period.
4. Use exchange-native execution for any genuine HFT design. MT5 can receive a slower signal or act as a CFD copier, but it cannot supply the original exchange-latency edge.

## Evidence locations

- DMC implementation and native reports: `../DMC Video Update 2026-08-11/`
- BTC order-flow code, data audit, trade files, and equity graph: `../BTC Order Flow Research 2026-08-13/`
- Compact source/result mapping: `source-and-result-mapping.csv`

