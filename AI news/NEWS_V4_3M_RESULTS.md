# Gold News Direction V4 - Frozen Three-Month Replay

Only NFP, CPI, and FOMC are supported. PPI and GDP are excluded from the live V4 pipeline.

The model and all gates were selected using data before May 8, 2026. The evaluation window is May 8 through August 7, 2026. August 7 uses the exact T-15 feature snapshot saved before NFP.

## Summary

| Measure | Legacy forced direction | V4 final call | V4 shadow bias |
|---|---:|---:|---:|
| Accuracy | 55.56% | 100.00% | 55.56% |
| Calls / events | 9 / 9 | 1 / 9 | 9 / 9 |
| Coverage | 100.00% | 11.11% | 100.00% |

## Event Replay

| Date | Event | Legacy | V4 T-30 | V4 final T-15 | Shadow bias | Actual | Move |
|---|---|---|---|---|---|---|---:|
| 2026-05-08 | NFP | NEGATIVE | NO CALL | NO CALL | NEGATIVE | NEGATIVE | -2.236 USD |
| 2026-05-12 | CPI | POSITIVE | NO CALL | NO CALL | POSITIVE | NEGATIVE | -4.053 USD |
| 2026-06-05 | NFP | POSITIVE | POSITIVE | NO CALL | POSITIVE | NEGATIVE | -14.755 USD |
| 2026-06-10 | CPI | POSITIVE | NO CALL | NO CALL | NEGATIVE | POSITIVE | +27.823 USD |
| 2026-06-17 | FOMC | NEGATIVE | NEGATIVE | NEGATIVE | NEGATIVE | NEGATIVE | -31.935 USD |
| 2026-07-02 | NFP | POSITIVE | NO CALL | NO CALL | NEGATIVE | POSITIVE | +52.130 USD |
| 2026-07-14 | CPI | POSITIVE | NEGATIVE | NO CALL | POSITIVE | POSITIVE | +60.540 USD |
| 2026-07-29 | FOMC | NEGATIVE | NO CALL | NO CALL | POSITIVE | POSITIVE | +32.425 USD |
| 2026-08-07 | NFP | NEGATIVE | N/A | NO CALL | POSITIVE | POSITIVE | +43.170 USD |

## Interpretation

V4 made 1 active final call(s). Its 95% Wilson interval is 20.65% to 100.00%, so the tiny holdout cannot prove stability.

A no-call is intentional. The shadow bias is informational and must not be presented as a validated directional call.

The T-30 candidate made three calls, won one, and is not promoted. Live T-30 output is preliminary bias only; the final T-15 gate is required for an active direction.

Historical point-in-time consensus/revision data is not available locally. Forecast and previous values remain context-only until a licensed archive passes chronological validation.
