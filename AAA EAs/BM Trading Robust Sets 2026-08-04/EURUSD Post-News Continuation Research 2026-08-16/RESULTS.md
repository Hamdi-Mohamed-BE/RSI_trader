# EURUSD Post-News Continuation EA — implementation and honest validation

## Decision

The EA is complete and compiles with **0 errors and 0 warnings**, but this candidate is **not approved for the active BAT or a prop-firm challenge**. The selected setup looked good in training, then fell to **PF 0.99 and -0.02%** on the locked unseen period. The 2026 real-tick result is positive but has only five trades, which is far too small to establish an edge.

## Implemented rules

- Symbol/timeframe: EURUSD M1.
- Events: official US CPI and Employment Situation/NFP releases at 08:30 America/New_York.
- Time handling: tester dates are converted from New York time with US daylight-saving rules; live mode reads broker-server timestamps from MT5's economic calendar and does not use the VPS local clock.
- Wait three minutes after the release; never place a pre-news straddle.
- Require the post-release impulse to close outside the preceding 30-minute range and have at least a 50% candle body.
- Place a limit order at a 20% retracement of the impulse; expire it after 30 minutes.
- Stop beyond the impulse origin with an ATR floor; target 1.5R; force close 45 minutes after the event.
- Risk 0.50% of current equity per filled trade; one position/order at a time.
- Absolute and pre-event-relative spread gates are active.

This is a **price-confirmed proxy** for a macro-surprise strategy. It does not pretend to know the original pre-release consensus forecast. A scientifically complete surprise test still needs a point-in-time calendar dataset containing unrevised actual, consensus, revision timestamp, and release timestamp.

## Results on a $10,000 account

| Test | Period | Tick model | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---|---:|---:|---:|---:|---:|
| Training selection | 2021-08-11–2024-12-31 | 1-minute OHLC | +2.73% | 2.65 | 62.50% | 1.06% | 24 |
| **Locked unseen validation** | **2025-01-01–2026-08-10** | **1-minute OHLC** | **-0.02%** | **0.99** | **45.45%** | **1.31%** | **11** |
| Last year | 2025-08-11–2026-08-10 | 1-minute OHLC | +0.23% | 1.25 | 42.86% | 1.02% | 7 |
| 2026 execution check | 2026-01-01–2026-08-10 | Real ticks | +0.85% | 3.55 | 60.00% | 0.41% | 5 |
| Full-period diagnostic | 2021-08-11–2026-08-10 | 1-minute OHLC | +2.69% | 1.92 | 57.14% | 1.86% | 35 |

The full-period diagnostic ended at **$10,269.08**, for **$269.08 net profit**. Gross profit was $561.77, gross loss was -$292.69, the largest win was $74.50, and the largest loss was -$51.00. It is not a clean out-of-sample result because the first part of that period was used for parameter selection.

The 2026 real-tick check ended at **$10,085.20**, for **$85.20 net profit**. Gross profit was $118.56 and gross loss was -$33.36. Five trades cannot support a dependable projection or payout probability.

## Test integrity

- Broker/tester: Exness-MT5Trial16, MT5 build 6090.
- Execution delay: 1 ms tester setting.
- History quality: 100% in all reported runs.
- Historical spread and the broker's commission model are included. The real-tick validation uses the cached Exness bid/ask ticks available for 2026.
- The five-year screen used one-minute OHLC because the local Exness installation does not contain pre-2026 real ticks.
- The strict original 2× ATR ceiling generated zero trades. A bounded parameter screen was run only on the training period; the selected configuration was then frozen before validation.

## Why it is rejected

The decisive number is the locked unseen result, not the attractive training PF. The strategy did not preserve profitability after selection, averages far too few trades to target a four-month challenge, and depends on a price-only proxy rather than point-in-time consensus surprises. Raising risk would increase drawdown without fixing the missing edge.

The active portfolio BAT was deliberately left unchanged.

## Research basis

- [NBER: real-time foreign-exchange response to macro announcements](https://www.nber.org/papers/w8959)
- [Federal Reserve: announcement price effects are largely completed within minutes](https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm)
- [New York Fed: a small subset of US announcements, especially payrolls, have persistent economic significance](https://www.newyorkfed.org/research/current_issues/ci14-6.html)
- [BLS official release calendars](https://www.bls.gov/schedule/)
