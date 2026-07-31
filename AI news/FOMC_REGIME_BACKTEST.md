# FOMC Regime Research

Every machine-learning model is frozen before its future test block. The current meeting's official surprise is never an input.

## Overall candidates

| Candidate | Calls | Accuracy | Coverage | 95% interval |
|---|---:|---:|---:|---:|
| direct_lr_history_conf60 | 25 | 72.00% | 31.65% | 52.42-85.72% |
| direct_lr_history_agreement | 30 | 70.00% | 37.97% | 52.12-83.34% |
| triple_lr_consensus | 22 | 68.18% | 27.85% | 47.32-83.64% |
| v1_history_agreement | 36 | 66.67% | 45.57% | 50.33-79.79% |
| direct_lr_history_conf55 | 27 | 66.67% | 34.18% | 47.82-81.36% |
| direct_et_history_agreement | 39 | 64.10% | 49.37% | 48.42-77.26% |
| history | 79 | 62.03% | 100.00% | 51.00-71.93% |
| triple_et_consensus | 22 | 59.09% | 27.85% | 38.73-76.74% |
| majority_lr | 79 | 55.70% | 100.00% | 44.73-66.13% |
| v1_model | 79 | 53.16% | 100.00% | 42.27-63.76% |
| direct_lr | 79 | 53.16% | 100.00% | 42.27-63.76% |
| direct_lr_shock_lr_agreement | 49 | 53.06% | 62.03% | 39.38-66.30% |
| direct_et | 79 | 51.90% | 100.00% | 41.05-62.57% |
| majority_et | 79 | 51.90% | 100.00% | 41.05-62.57% |
| shock_lr | 79 | 50.63% | 100.00% | 39.84-61.37% |
| direct_et_shock_et_agreement | 36 | 44.44% | 45.57% | 29.54-60.42% |
| shock_et | 79 | 43.04% | 100.00% | 32.69-54.03% |

## Best candidate

**direct_lr_history_conf60**: 18/25 correct (72.00%), 31.65% coverage.

The official statement surprise itself is an ex-post diagnostic, not a tradable input: 50/78 (64.10%) matched the immediate gold direction.
