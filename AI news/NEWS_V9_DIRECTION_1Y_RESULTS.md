# Gold News V9 - One-Year Direction Replay

> Window: September 10, 2025 through September 9, 2026. NFP, CPI, and FOMC only. All release features are fitted using data before the test window.

## Version Comparison

| Version | Calls | Wins | Win rate | Coverage |
|---|---:|---:|---:|---:|
| V1 event history | 29 | 18 | 62.07% | 100.00% |
| V2 event rules | 29 | 20 | 68.97% | 100.00% |
| V4 active gate | 5 | 5 | 100.00% | 17.24% |
| V4 shadow direction | 29 | 19 | 65.52% | 100.00% |
| V5/V6 active | 14 | 11 | 78.57% | 48.28% |
| V7/V8 full direction | 29 | 20 | 68.97% | 100.00% |
| V9 full direction | 29 | 21 | 72.41% | 100.00% |
| V9 TRADE tier | 14 | 11 | 78.57% | 48.28% |
| V9 LOW_CONFIDENCE tier | 15 | 10 | 66.67% | 51.72% |

## V9 Event Breakdown

| Event | Releases | Wins | Accuracy | Coverage | TRADE-tier accuracy | TRADE-tier coverage |
|---|---:|---:|---:|---:|---:|---:|
| NFP | 10 | 7 | 70.00% | 100.00% | 0.00% | 0.00% |
| CPI | 11 | 8 | 72.73% | 100.00% | 72.73% | 100.00% |
| FOMC | 8 | 6 | 75.00% | 100.00% | 100.00% | 37.50% |

## Event Replay

| Date | Event | V7/V8 | V9 | Tier | Actual | Result | Gold move |
|---|---|---|---|---|---|---|---:|
| 2025-09-11 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +7.867 USD |
| 2025-09-17 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | NEGATIVE | LOSS | -4.590 USD |
| 2025-10-24 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +29.287 USD |
| 2025-10-29 | FOMC | NEGATIVE | NEGATIVE | TRADE | NEGATIVE | WIN | -6.447 USD |
| 2025-11-20 | NFP | NEGATIVE | POSITIVE | LOW_CONFIDENCE | NEGATIVE | LOSS | -3.955 USD |
| 2025-12-10 | FOMC | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +16.720 USD |
| 2025-12-16 | NFP | POSITIVE | POSITIVE | LOW_CONFIDENCE | POSITIVE | WIN | +4.415 USD |
| 2025-12-18 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +9.758 USD |
| 2026-01-09 | NFP | NEGATIVE | NEGATIVE | LOW_CONFIDENCE | NEGATIVE | WIN | -2.250 USD |
| 2026-01-13 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +9.940 USD |
| 2026-01-28 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | POSITIVE | WIN | +7.313 USD |
| 2026-02-11 | NFP | POSITIVE | NEGATIVE | LOW_CONFIDENCE | NEGATIVE | WIN | -60.002 USD |
| 2026-02-13 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +27.565 USD |
| 2026-03-06 | NFP | POSITIVE | NEGATIVE | LOW_CONFIDENCE | POSITIVE | LOSS | +35.540 USD |
| 2026-03-11 | CPI | POSITIVE | POSITIVE | TRADE | NEGATIVE | LOSS | -3.489 USD |
| 2026-03-18 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | POSITIVE | WIN | +5.766 USD |
| 2026-04-10 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +13.597 USD |
| 2026-04-29 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | NEGATIVE | LOSS | -3.543 USD |
| 2026-05-08 | NFP | NEGATIVE | NEGATIVE | LOW_CONFIDENCE | NEGATIVE | WIN | -2.236 USD |
| 2026-05-12 | CPI | POSITIVE | POSITIVE | TRADE | NEGATIVE | LOSS | -4.053 USD |
| 2026-06-05 | NFP | POSITIVE | NEGATIVE | LOW_CONFIDENCE | NEGATIVE | WIN | -14.755 USD |
| 2026-06-10 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +27.823 USD |
| 2026-06-17 | FOMC | NEGATIVE | NEGATIVE | TRADE | NEGATIVE | WIN | -31.935 USD |
| 2026-07-02 | NFP | POSITIVE | NEGATIVE | LOW_CONFIDENCE | POSITIVE | LOSS | +52.130 USD |
| 2026-07-14 | CPI | POSITIVE | POSITIVE | TRADE | POSITIVE | WIN | +60.540 USD |
| 2026-07-29 | FOMC | NEGATIVE | POSITIVE | LOW_CONFIDENCE | POSITIVE | WIN | +32.425 USD |
| 2026-08-07 | NFP | NEGATIVE | POSITIVE | LOW_CONFIDENCE | POSITIVE | WIN | +46.950 USD |
| 2026-08-12 | CPI | POSITIVE | POSITIVE | TRADE | NEGATIVE | LOSS | -33.192 USD |
| 2026-09-04 | NFP | NEGATIVE | NEGATIVE | LOW_CONFIDENCE | NEGATIVE | WIN | -69.730 USD |

## Limits

- April 3, 2026 NFP is excluded because the XAUUSD archive has no tradable release session for that market holiday.
- This is a chronological replay: model fitting uses only data before the one-year window and event-history inputs update only after each release.
- V9's architecture was designed after some displayed outcomes were known, so this is not a pristine untouched test of the design choice.
- V3 is omitted from the one-year comparison because it was a rejected research candidate and has no frozen one-year production policy.
- Direction accuracy measures the sign of the release-minute XAUUSD midpoint move. It is not a simulated trading return.
