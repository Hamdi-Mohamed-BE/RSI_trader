# Gold News V9 Execution V2 - One-Year Replay

> The V9 direction model is unchanged. Parameters were selected on the first 20 releases only. The final nine releases are untouched holdout data. All NFP, CPI, and FOMC calls are executed.

## Selected Rule

**T-10s entry, 20.0 USD stop, 4.0 USD target, T+900s exit**

## Results

| Window | Trades | Direction accuracy | Trade win rate | PF | Return | End balance | Realized DD | Tick DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 20 | 70.00% | 95.00% | 4.216 | +3.71% | 10371.41 USD | 1.12% | 1.17% |
| Untouched holdout | 9 | 77.78% | 88.89% | 1.883 | +0.89% | 10088.75 USD | 1.00% | 1.02% |
| Full year | 29 | 72.41% | 93.10% | 3.170 | +4.69% | 10468.75 USD | 1.12% | 1.17% |

## Baseline Comparison

| Version | Win rate | PF | Return | End balance | Realized DD | Tick DD |
|---|---:|---:|---:|---:|---:|---:|
| Original | 48.28% | 8.194 | +153.05% | 25305.12 USD | 4.53% | 10.53% |
| Execution V2 | 93.10% | 3.170 | +4.69% | 10468.75 USD | 1.12% | 1.17% |

## Full-Year Trades

| Date | Event | Call | Confidence | Actual | Exit | Captured | P/L | Balance |
|---|---|---|---:|---|---|---:|---:|---:|
| 2025-09-11 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +4.333 USD | +21.67 USD | 10021.67 USD |
| 2025-09-17 | FOMC | POSITIVE | 58.1% | NEGATIVE | TAKE_PROFIT | +4.545 USD | +22.73 USD | 10044.40 USD |
| 2025-10-24 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +8.003 USD | +40.01 USD | 10084.41 USD |
| 2025-10-29 | FOMC | NEGATIVE | 65.0% | NEGATIVE | TAKE_PROFIT | +4.040 USD | +20.20 USD | 10104.61 USD |
| 2025-11-20 | NFP | POSITIVE | 51.7% | NEGATIVE | TAKE_PROFIT | +4.114 USD | +20.57 USD | 10125.18 USD |
| 2025-12-10 | FOMC | POSITIVE | 65.0% | POSITIVE | TAKE_PROFIT | +4.123 USD | +20.62 USD | 10145.80 USD |
| 2025-12-16 | NFP | POSITIVE | 70.1% | POSITIVE | TAKE_PROFIT | +4.143 USD | +20.72 USD | 10166.52 USD |
| 2025-12-18 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +7.163 USD | +35.81 USD | 10202.33 USD |
| 2026-01-09 | NFP | NEGATIVE | 76.1% | NEGATIVE | TAKE_PROFIT | +4.818 USD | +24.09 USD | 10226.42 USD |
| 2026-01-13 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +4.129 USD | +20.64 USD | 10247.06 USD |
| 2026-01-28 | FOMC | POSITIVE | 56.6% | POSITIVE | TAKE_PROFIT | +4.019 USD | +20.10 USD | 10267.16 USD |
| 2026-02-11 | NFP | NEGATIVE | 59.8% | NEGATIVE | TAKE_PROFIT | +5.183 USD | +25.91 USD | 10293.07 USD |
| 2026-02-13 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +8.227 USD | +41.13 USD | 10334.20 USD |
| 2026-03-06 | NFP | NEGATIVE | 54.6% | POSITIVE | STOP_LOSS | -23.096 USD | -115.48 USD | 10218.72 USD |
| 2026-03-11 | CPI | POSITIVE | 68.0% | NEGATIVE | TAKE_PROFIT | +4.742 USD | +23.71 USD | 10242.43 USD |
| 2026-03-18 | FOMC | POSITIVE | 56.4% | POSITIVE | TAKE_PROFIT | +4.218 USD | +21.09 USD | 10263.52 USD |
| 2026-04-10 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +6.292 USD | +31.46 USD | 10294.98 USD |
| 2026-04-29 | FOMC | POSITIVE | 58.3% | NEGATIVE | TAKE_PROFIT | +4.063 USD | +20.32 USD | 10315.30 USD |
| 2026-05-08 | NFP | NEGATIVE | 61.1% | NEGATIVE | TAKE_PROFIT | +7.161 USD | +35.81 USD | 10351.11 USD |
| 2026-05-12 | CPI | POSITIVE | 68.0% | NEGATIVE | TAKE_PROFIT | +4.061 USD | +20.30 USD | 10371.41 USD |
| 2026-06-05 | NFP | NEGATIVE | 50.9% | NEGATIVE | TAKE_PROFIT | +5.381 USD | +26.91 USD | 10398.32 USD |
| 2026-06-10 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +5.687 USD | +28.43 USD | 10426.75 USD |
| 2026-06-17 | FOMC | NEGATIVE | 65.0% | NEGATIVE | TAKE_PROFIT | +5.647 USD | +28.23 USD | 10454.98 USD |
| 2026-07-02 | NFP | NEGATIVE | 58.8% | POSITIVE | STOP_LOSS | -20.104 USD | -100.52 USD | 10354.46 USD |
| 2026-07-14 | CPI | POSITIVE | 68.0% | POSITIVE | TAKE_PROFIT | +4.062 USD | +20.31 USD | 10374.77 USD |
| 2026-07-29 | FOMC | POSITIVE | 56.4% | POSITIVE | TAKE_PROFIT | +4.532 USD | +22.66 USD | 10397.43 USD |
| 2026-08-07 | NFP | POSITIVE | 65.4% | POSITIVE | TAKE_PROFIT | +4.859 USD | +24.29 USD | 10421.72 USD |
| 2026-08-12 | CPI | POSITIVE | 68.0% | NEGATIVE | TAKE_PROFIT | +4.175 USD | +20.87 USD | 10442.59 USD |
| 2026-09-04 | NFP | NEGATIVE | 69.3% | NEGATIVE | TAKE_PROFIT | +5.232 USD | +26.16 USD | 10468.75 USD |

## Limits

- Prediction accuracy is measured at T+15; a correct direction can still lose if price reaches the stop first.
- The holdout is the honest execution test. Full-year performance also contains the development period.
- Spread and tick-gap slippage are included. Commission, network delay, rejections, and market-depth impact are not.
- Twenty development and nine holdout releases are small samples. Results are evidence, not a guarantee.
