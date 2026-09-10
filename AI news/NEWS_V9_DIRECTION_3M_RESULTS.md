# Gold News V9 - Three-Month Direction and Execution Replay

> V9 promotes the frozen V5/V6 event-specific bias to a full direction and retains the original gate as TRADE versus LOW_CONFIDENCE. The execution replay uses exact MT5 bid/ask ticks.

## Direction Results

| Policy | Calls | Wins | Accuracy | Coverage |
|---|---:|---:|---:|---:|
| V7 baseline | 8 | 5 | 62.50% | 100.00% |
| V9 all directions | 8 | 6 | 75.00% | 100.00% |
| V9 TRADE tier | 4 | 3 | 75.00% | 50.00% |
| V9 LOW_CONFIDENCE tier | 4 | 3 | 75.00% | 50.00% |

## Execution Results

| Sizing | Start | End | Net P/L | Wins | Win rate | Profit factor | Max realized DD | Max tick DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed 0.08 lot | $100.00 | $2888.31 | $+2788.31 | 6/8 | 75.00% | 33.54 | 4.68% | 39.63% |
| 0.06 per complete $100 | $100.00 | $246006.97 | $+245906.97 | 6/8 | 75.00% | 15.89 | 34.56% | 54.56% |

## Prediction and Dynamic Simulation Table

| Date | Event | V7 | V9 | Tier | Confidence | Actual | Result | Lot | Captured | P/L | Balance |
|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|
| 2026-06-10 | CPI | POSITIVE | POSITIVE | TRADE | 68.00% | POSITIVE | WIN | 0.06 | +22.930 USD | $+137.58 | $237.58 |
| 2026-06-17 | FOMC | NEGATIVE | NEGATIVE | TRADE | 65.00% | NEGATIVE | WIN | 0.12 | +94.534 USD | $+1134.41 | $1371.99 |
| 2026-07-02 | NFP | POSITIVE | NEGATIVE | LOW_CONFIDENCE | 54.91% | POSITIVE | LOSS | 0.78 | -6.079 USD | $-474.16 | $897.83 |
| 2026-07-14 | CPI | POSITIVE | POSITIVE | TRADE | 68.00% | POSITIVE | WIN | 0.48 | +63.360 USD | $+3041.28 | $3939.11 |
| 2026-07-29 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | 54.29% | POSITIVE | WIN | 2.34 | +37.020 USD | $+8662.68 | $12601.79 |
| 2026-08-07 | NFP | NEGATIVE | POSITIVE | LOW_CONFIDENCE | 56.46% | POSITIVE | WIN | 7.56 | +59.767 USD | $+45183.85 | $57785.64 |
| 2026-08-12 | CPI | POSITIVE | POSITIVE | TRADE | 68.00% | NEGATIVE | LOSS | 34.62 | -4.633 USD | $-16039.45 | $41746.19 |
| 2026-09-04 | NFP | NEGATIVE | NEGATIVE | LOW_CONFIDENCE | 54.99% | NEGATIVE | WIN | 25.02 | +81.639 USD | $+204260.78 | $246006.97 |

## Honesty Notes

- V9 improves this retrospective eight-event table from 5/8 to 6/8 by correcting July 29 FOMC and August 7 NFP, while changing July 2 NFP from correct to wrong.
- V5/V6 was designed after part of this period was visible. Therefore 75% is not an untouched forward result and cannot establish a stable improvement.
- Point-in-time consensus history is incomplete. Consensus, official nowcasts, and macro-regime candidates remain context-only when their chronological validation does not beat the frozen direction rule.
- Dynamic compounding magnifies one changed prediction dramatically. Commission, latency, rejection, and large-order market-depth slippage are unavailable historically.
