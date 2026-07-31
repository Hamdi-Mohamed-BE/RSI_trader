# FOMC Gold Direction Pipeline

This is a prediction-only, leakage-safe FOMC direction layer.
Each event is replayed using only earlier data. The design itself was created after the July 29 miss, so these are retrospective results, not a pristine untouched test.

## Honest replay

| Window | FOMC events | History | T-30 model | Agreement calls | Agreement accuracy |
|---|---:|---:|---:|---:|---:|
| 2021-2024 broad | 23 | 65.22% | 56.52% | 13 | 69.23% |
| 2024-2026 recent | 17 | 64.71% | 58.82% | 4 | 100.00% |
| Combined | 40 | 65.00% | 57.50% | 17 | 76.47% |

Agreement coverage is intentionally selective. Its combined 95% interval is 52.74% to 90.45%.

## July 29, 2026 forensic check

- History component: **NEGATIVE**
- T-30 model: **POSITIVE**
- FedWatch resolver: **POSITIVE**
- Final low-confidence output: **POSITIVE**
- Actual release-minute gold impact: **POSITIVE** (+32.425 USD)

The single pricing-resolved example is not counted as proof. A licensed or user-supplied point-in-time FedWatch history is still required to validate that resolver.
