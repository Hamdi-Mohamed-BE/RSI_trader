# FOMC Frozen Temporal Holdout

The T-30 model is frozen before each future block and cannot learn from any outcome inside that block.

| Test block | Train events | Test events | History | Frozen model | Agreement calls | Agreement accuracy |
|---|---:|---:|---:|---:|---:|---:|
| 2016-07-30 to 2019-07-30 | 39 | 23 | 60.87% | 60.87% | 9 | 77.78% |
| 2019-07-30 to 2021-07-30 | 62 | 16 | 56.25% | 37.50% | 11 | 45.45% |
| 2021-07-30 to 2024-07-30 | 78 | 23 | 65.22% | 47.83% | 11 | 63.64% |
| 2024-07-30 to 2026-07-30 | 101 | 17 | 64.71% | 64.71% | 5 | 100.00% |

## Overall

- History rule: **49/79 (62.03%)**
- Frozen T-30 model: **42/79 (53.16%)**
- Agreement only: **24/36 (66.67%)**, coverage **45.57%**
- Agreement 95% interval: **50.33% to 79.79%**

The 2019-2021 block failed at 45.45% on agreement calls. This confirms regime sensitivity and supports a 65% confidence cap, not 70% or higher.
