# OCO small-balance audit — $50

## Decision

Selected configuration: **literal-ny-full**. It survived both months in this MT5 test, but live OCO execution can be materially worse.

## Results

| Period | Net | Final | PF | Win rate | Max equity DD | Minimum balance | Trades | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| July development | $9,229.84 | $9,279.84 | 3.93 | 62.34% | 0.22% | $49.37 | 11,955 | $-717.30 |
| August locked | $11,105.48 | $11,155.48 | 4.62 | 64.51% | 0.16% | $49.94 | 12,184 | $-731.04 |
| Two months | $20,648.50 | $20,698.50 | 4.25 | 63.37% | 0.09% | $49.37 | 24,637 | $-1,478.22 |

## Exact setting

- Entry offset: $0.40
- Initial stop: $0.50
- Trail starts: $0.80
- Trail distance: $0.45
- Session: 13:00-21:00 UTC
- Direction: both
- Fixed lot: 0.01; no equity scaling; one open position maximum; no martingale.

## Next 30-day statistical estimate

Bootstrap median: **$13,755.51** net; 10th-90th percentile: **$11,401.52 to $16,439.28**; sampled probability of a losing month: **0.00%**.
This is a resampling of August daily P&L, not a forecast or guarantee. Live latency, rejected/cancelled orders, simultaneous fills and broker throttling are not reproduced perfectly.
