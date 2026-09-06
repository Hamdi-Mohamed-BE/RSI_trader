# Step 8 — News Pulse multi-market audit

The EA already contained independent buy/sell switches and real BuyStop/SellStop execution. This audit calibrates absolute price distances separately for each market and keeps risk fixed at 1% per enabled side.

## Selected configurations

| Market | Direction | Entry / stop | Management | Development return / PF / trades | Locked return / PF / trades | Full return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Random-delay return / PF |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | two-sided | 6 / 6 | native60 | +24.51% / 4.82 / 23 | +43.90% / 16.85 / 10 | +79.02% | 9.02 | 63.64% | 2.39% | 33 | 391.16 | 19.58 | +87.21% / 11.71 |
| XAGUSD | two-sided | 0.08 / 0.08 | native60 | +130.51% / 8.16 / 27 | +100.97% / 23.54 / 10 | +366.10% | 13.78 | 62.16% | 3.30% | 37 | 434.70 | 27.17 | +350.42% / 11.54 |
| USTEC | buy-only | 30 / 30 | native60 | +9.16% / 2.91 / 15 | +15.11% / 7.43 / 7 | +25.67% | 4.49 | 63.64% | 4.27% | 22 | 250.87 | 5.32 | +23.53% / 3.92 |
| EURUSD | two-sided | 0.0006 / 0.0006 | native60 | +32.49% / 6.24 / 24 | +29.66% / 9.74 / 10 | +71.83% | 7.71 | 67.65% | 3.77% | 34 | 455.99 | 13.82 | +74.71% / 8.24 |
| BTCUSD | buy-only | 150 / 150 | native60 | +3.68% / 1.38 / 18 | +2.82% / 2.26 / 6 | +6.65% | 1.56 | 45.83% | 8.44% | 24 | 90.83 | 0.70 | +3.93% / 1.31 |

## Monte Carlo — 10,000 closed-trade resamples

| Market | Probability profitable | Return P5 | Median return | Return P95 | P95 max DD |
|---|---:|---:|---:|---:|---:|
| XAUUSD | 100.0% | +43.36% | +78.15% | +117.69% | 4.36% |
| XAGUSD | 100.0% | +208.29% | +361.66% | +536.79% | 7.50% |
| USTEC | 99.8% | +9.96% | +25.14% | +42.66% | 4.53% |
| EURUSD | 100.0% | +40.82% | +70.99% | +104.28% | 4.32% |
| BTCUSD | 80.4% | -5.42% | +6.47% | +19.81% | 9.36% |

## Deployment decision

| Market | Decision | Reason |
|---|---|---|
| XAUUSD | Keep the existing long-only preset as the production default; demo-test this two-sided preset | The candidate lifts return to +79.02%, but PF falls to 9.02, DD rises to 2.39%, and simultaneous two-sided exposure can approach 2%. The current long-only system is +62.39%, PF 40.78, DD 1.46%, 19 trades. |
| XAGUSD | Demo forward only | Excellent historical and random-delay results, but +366.10% from 37 one-minute news trades is too execution-sensitive to treat as a live expectation. |
| USTEC | Demo forward | Buy-only is the cleanest selection and remains profitable under random delay; the sample is still only 22 trades. |
| EURUSD | Demo forward | Two-sided result is strong in development, locked data, and random delay, but live news spread and rejection risk remain material. |
| BTCUSD | Reject / do not promote | PF 1.56, DD 8.44%, recovery 0.70, and Monte Carlo P5 is -5.42%. |

No BAT or website preset is promoted by this research step. Promotion should follow a review and demo-forward check, especially for XAGUSD and EURUSD.

## Evidence limits

- The Strategy Tester cannot query MT5's live economic calendar. The current EA contains an explicit NFP/CPI/FOMC tester schedule for this audited year only; pretending this is a three-year test would be misleading.
- The locked period is only three months and event counts are small. Large PF values are not stable expectations.
- MT5's reported Sharpe ratios are mechanically inflated for sparse trades that last about one minute, so they are displayed for completeness but were not used as the promotion criterion.
- News execution is gap-, spread- and latency-sensitive. Random-delay testing still cannot reproduce every live rejection or spread shock.
- Two-sided mode keeps 1% risk per triggered side and can therefore expose roughly 2% around one release before slippage.
