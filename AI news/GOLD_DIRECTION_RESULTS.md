# Gold Direction Prediction Results

The system predicts information only: **POSITIVE for gold** or **NEGATIVE for gold**. It does not issue trade calls.

## Selected configuration

- T-30 early view: `100%` event history and `0%` `extra_trees` / `t30_macro`.
- T-15 final view: `100%` event history and `0%` `hist_gradient_boosting` / `t15`.

## Frozen results

| Window | Events | Correct | Accuracy | 95% interval | Majority baseline | Momentum baseline |
|---|---:|---:|---:|---:|---:|---:|
| Broad holdout | 84 | 49 | 58.33% | 47.65-68.29% | 58.33% | 48.81% |
| Recent holdout | 8 | 6 | 75.00% | 40.93-92.85% | 75.00% | 37.50% |

## Recent releases

| Date | Event | Forecast | Confidence | Actual | Gold move | Correct |
|---|---|---|---:|---|---:|---|
| 2026-06-05 | NFP | NEGATIVE | 56.8% | NEGATIVE | -14.755 | YES |
| 2026-06-10 | CPI | POSITIVE | 56.8% | POSITIVE | +27.823 | YES |
| 2026-06-11 | PPI | POSITIVE | 56.8% | POSITIVE | +2.952 | YES |
| 2026-06-17 | FOMC | NEGATIVE | 56.8% | NEGATIVE | -31.935 | YES |
| 2026-07-02 | NFP | NEGATIVE | 56.8% | POSITIVE | +52.130 | NO |
| 2026-07-14 | CPI | POSITIVE | 56.8% | POSITIVE | +60.540 | YES |
| 2026-07-15 | PPI | POSITIVE | 56.8% | POSITIVE | +8.750 | YES |
| 2026-07-29 | FOMC | NEGATIVE | 56.8% | POSITIVE | +32.425 | NO |

Confidence is calibrated from chronological out-of-fold correctness. It is uncertainty information, not a trade instruction.
