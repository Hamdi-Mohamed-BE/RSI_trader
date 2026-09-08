# Sell Nasdaq 15min — full native MT5 pipeline

## Decision

**WATCH ONLY — positive, but the untouched evidence is not strong enough for the active portfolio.**

## Exact strategy interpretation

- Instrument: Exness USTEC only.
- 09:30–09:45 New York candle must close bearish.
- Optional London condition: the immediately preceding 09:15–09:30 New York M15 candle must also close bearish.
- Entry: sell stop at the first New York candle low, plus any selected downside buffer.
- User baseline: 600-pip SL and 1,000-pip TP. Under the requested display convention, 1 pip = 10 broker points, or roughly 60/100 USTEC index points on this feed.
- One attempted setup per New York day; automatic U.S. daylight-saving conversion.

## Test design

- Development: 2023-09-01 to 2025-09-01, native MT5 1-minute OHLC for sequential search.
- Untouched locked year: 2025-09-01 to 2026-09-01, native MT5 Every Tick with broker costs and random delay.
- Full reference: 2023-09-01 to 2026-09-01, native MT5 Every Tick.
- Starting balance: $10,000; risk: exactly 1% of dynamic equity per filled trade.
- Monte Carlo: 10,000 five-trade block-bootstrap paths from the untouched selected-version trades.
- The New York 09:30 anchor, M15 setup candle and short-only direction were kept fixed so optimization could not rewrite the hypothesis.

## Untouched locked-year results

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw 600/1000 — without London | -0.10% | 1.00 | 38.38% | 10.07% | 99 | -0.07 | -0.01 |
| Raw 600/1000 — with London | +10.54% | 1.33 | 46.30% | 4.52% | 54 | 12.22 | 2.14 |
| Development-selected | +7.07% | 1.14 | 35.62% | 8.75% | 73 | 6.24 | 0.70 |

## Selected three-year Every Tick reference

| Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---:|---:|---:|---:|---:|---:|---:|
| +90.16% | 1.42 | 42.22% | 11.57% | 225 | 14.87 | 4.10 |

## Development selections

- london-condition: `without-london`
- stop: `sl450`
- target: `tp1000`
- entry-buffer: `buffer0`
- entry-window: `window30`
- body: `body00`
- minimum-range: `minrange400`
- maximum-range: `maxrange2400`
- invalidation: `keep-after-high-break`
- management: `none`
- weekdays: `tue-fri`
- joint-neighborhood: `sl450-tp1000`

## Final selected inputs

- London condition: `False`
- Stop / target: `450` / `1000` pips (nominal RR 2.22)
- Entry buffer / expiry: `0` pips / `30` minutes
- Minimum body fraction: `0.00`
- Setup range bounds: `400` to `2400` pips (0 = disabled)
- Cancel if setup high breaks: `False`
- Break-even / trailing / Dynamic 50-20: `0.0` / `0.0` / `False`

## Monte Carlo

- Probability profitable: 72.46%
- Return P5 / median / P95: -12.01% / +6.86% / +26.41%
- Max drawdown median / P95: 9.05% / 18.81%

## Scope

This is research evidence, not a guarantee. The pipeline-selected 450/1000 configuration was later approved for Standard deployment by the user.

## Safe-mode audit

The Safe version uses the same completed-D1, no-lookahead Markov direction veto already used by the Calyx Full Safe system. It does not change the 1% research risk.

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw London Standard — locked | +10.54% | 1.33 | 46.30% | 4.52% | 54 | 12.22 | 2.14 |
| Raw London Standard — full 3y | +32.62% | 1.33 | 45.62% | 6.07% | 160 | 9.33 | 5.23 |
| Raw London Full Safe — locked | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 0.00 |
| Pipeline-selected Full Safe — locked | -2.02% | 0.00 | 0.00% | 4.05% | 2 | -0.14 | -0.49 |
| Raw London Full Safe — full 3y | +2.12% | 1.34 | 45.45% | 2.87% | 11 | 3.21 | 0.71 |
| Pipeline-selected Full Safe — full 3y | -1.38% | 0.89 | 29.41% | 7.97% | 17 | -3.43 | -0.17 |

- Standard raw-London Monte Carlo return P5: -3.62%
- Best Safe Monte Carlo return P5: -2.02%
- Markov Safe decision: **DO NOT PROMOTE THE MARKOV GATE** — it did not clear the independent promotion gate.
- Research decision: **WATCH ONLY** — the raw London-confirmed version is the stronger conservative alternative, but neither branch is a guarantee.

## User-approved deployment mapping

- Standard: pipeline-optimized 450/1000, no prior-London prerequisite, Tuesday-Friday, 30-minute pending-entry window.
- London Safe: original 600/1000 configuration requiring the preceding 09:15-09:30 New York candle to close bearish.
- The rejected Markov gate remains disabled in both deployed presets.
- Both presets follow the non-News risk percentage selected in the BAT; pressing Enter defaults to 1%.
- The EA, dedicated Standard and London Safe SET files, every portfolio BAT, recommended portfolio, website detail comparison and all fixed-period caches were updated after explicit user approval.
