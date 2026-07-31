# FOMC Regime Walk-Forward

Each prediction is generated before its meeting and models are refit only after that meeting is complete.

| Policy | Calls | Correct | Accuracy | Coverage | 95% interval |
|---|---:|---:|---:|---:|---:|
| history | 79 | 49 | 62.03% | 100.00% | 51.00-71.93% |
| v1_model | 79 | 41 | 51.90% | 100.00% | 41.05-62.57% |
| regime_model | 79 | 36 | 45.57% | 100.00% | 35.05-56.50% |
| v1_history_agreement | 37 | 24 | 64.86% | 46.84% | 48.76-78.17% |
| regime_history_agreement | 32 | 19 | 59.38% | 40.51% | 42.26-74.48% |
| regime_history_conf60 | 23 | 13 | 56.52% | 29.11% | 36.81-74.37% |
| dual_model_history_union | 52 | 33 | 63.46% | 65.82% | 49.87-75.20% |
