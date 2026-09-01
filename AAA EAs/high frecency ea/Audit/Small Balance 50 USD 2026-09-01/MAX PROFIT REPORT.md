# OCO small-balance audit — $50

## Decision

Selected configuration: **literal-all**. It survived both months in this MT5 test, but live OCO execution can be materially worse.

## Results

| Period | Net | Final | PF | Win rate | Max equity DD | Minimum balance | Trades | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| July development | $21,348.26 | $21,398.26 | 3.42 | 60.92% | 0.18% | $49.94 | 32,648 | $-1,958.88 |
| August locked | $23,965.57 | $24,015.57 | 3.76 | 61.72% | 1.56% | $49.94 | 32,524 | $-1,951.44 |
| Two months | $45,876.52 | $45,926.52 | 3.56 | 61.24% | 0.18% | $49.94 | 66,435 | $-3,986.10 |

## Exact setting

- Entry offset: $0.40
- Initial stop: $0.50
- Trail starts: $0.80
- Trail distance: $0.45
- Session: all hours
- Direction: both
- Fixed lot: 0.01; no equity scaling; one open position maximum; no martingale.

## Next 30-day statistical estimate

Bootstrap median: **$28,752.82** net; 10th-90th percentile: **$24,617.65 to $32,904.41**; sampled probability of a losing month: **0.00%**.
This is a resampling of August daily P&L, not a forecast or guarantee. Live latency, rejected/cancelled orders, simultaneous fills and broker throttling are not reproduced perfectly.
