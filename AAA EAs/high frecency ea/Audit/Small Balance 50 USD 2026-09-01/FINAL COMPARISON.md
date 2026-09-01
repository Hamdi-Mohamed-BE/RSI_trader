# OCO $50 final comparison

## Recommendation

Use **literal NY-full** for a demo/cent-account trial. It gives up headline profit in exchange for materially fewer trades, higher PF and win rate, and lower peak-relative drawdown. Do not treat either backtest as a reliable live-income forecast: the edge depends on sub-dollar XAUUSD moves and extremely frequent pending-order changes.

## Continuous two-month results — 01 July to 31 August 2026

| Option | Final | Net | PF | Win rate | Max equity DD | Minimum realized balance | Trades | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Max profit — all hours | $45,926.52 | $45,876.52 | 3.56 | 61.24% | 0.18% ($30.59) | $49.94 | 66,435 | $-3,986.10 |
| Recommended safer — 13:00-21:00 UTC | $20,698.50 | $20,648.50 | 4.25 | 63.37% | 0.09% ($17.79) | $49.37 | 24,637 | $-1,478.22 |

## Recommended exact settings

- XAUUSD M1; current-price OCO; both long and short.
- Fixed lot 0.01; equity scaling off; one position maximum; no martingale.
- Entry offset $0.40; initial SL $0.50.
- Start trailing after $0.80 favorable movement; trail $0.45 behind price.
- Session filter on: 13:00-21:00 UTC.
- Maximum spread $0.50; replace unfilled OCO orders on each new M1 candle; maximum hold 180 minutes.

## August validation finalists

| Candidate | Net | PF | Win rate | Max DD | Minimum balance | Trades |
|---|---:|---:|---:|---:|---:|---:|
| literal-all | $23,965.57 | 3.76 | 61.72% | 1.56% | $49.94 | 32,524 |
| balanced-all | $22,016.40 | 3.29 | 59.92% | 0.32% | $49.27 | 30,253 |
| protected-all | $16,135.97 | 2.69 | 56.61% | 0.21% | $48.96 | 22,466 |
| wide-all | $11,934.54 | 2.27 | 53.53% | 6.46% | $48.81 | 17,291 |
| literal-ny-full | $11,105.48 | 4.62 | 64.51% | 0.16% | $49.94 | 12,184 |
| balanced-ny-full | $10,446.36 | 4.10 | 63.11% | 0.17% | $49.94 | 11,372 |
| literal-all-long | $9,310.20 | 2.87 | 55.62% | 0.21% | $49.94 | 16,637 |
| literal-all-short | $9,233.25 | 2.83 | 55.53% | 0.21% | $49.94 | 16,812 |

## Next 30-calendar-day model-only estimate

- Recommended safer setup: median **$10,625.95** net; 10th-90th percentile **$8,202.47 to $13,433.08**.
- Maximum-profit setup: median **$23,131.04** net; 10th-90th percentile **$18,654.59 to $27,828.56**.

These are bootstrap resamples of August daily tester P&L with weekend/no-trade days included. They are not credible cash forecasts until forward execution confirms cancellation latency, slippage, rejected modifications, simultaneous fills and broker order-rate tolerance. A defensible live expectation is therefore **unknown**, not the bootstrap median.

## Method

- July screened 31 parameter combinations; August tested only the eight July survivors.
- Continuous two-month reruns used $50 initial balance, 0.01 fixed lot, Exness XAUUSD, MT5 Every Tick, 100% reported history quality, broker spread, random execution delay, commission and swap.
- Active BAT and website were not changed.
