# Gold VWAP-EMA Regime - raw MT5 results

The code reproduces Bhatti (2026), SSRN 6650958, without parameter optimization. The paper's headline result is a calibrated outcome simulation, not a historical bar-by-bar test; these native MT5 results are therefore the first direct broker-data falsification check.

| Window | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| paper-2024 | +4.82% | 1.34 | 42.11% | 4.18% | 38 | 5.66 | 1.12 |
| latest-1y | +0.10% | 1.01 | 30.43% | 6.25% | 46 | 0.12 | 0.02 |
| recent-3y | +10.06% | 1.21 | 35.20% | 6.62% | 125 | 3.82 | 1.35 |
| full-5y | -4.08% | 0.95 | 31.49% | 18.41% | 235 | -0.91 | -0.22 |

## Paper claim versus direct replication

| 2024 result | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|
| Paper's calibrated simulation | +102.20% | 1.76 | 45.30% | 5.10% | 247 |
| Native MT5 broker-data replication | +4.82% | 1.34 | 42.11% | 4.18% | 38 |

## Raw rules implemented

- XAUUSD M15; session VWAP from 13:30 to 20:00 UTC using typical price and tick volume; this Exness tester export uses UTC strategy timestamps.
- 200 EMA regime with a 0.1% ambiguity exclusion zone.
- 50 EMA pullback/touch plus quantified pin-bar or engulfing rejection.
- Tick volume above 1.1x its 20-bar average and candle range at least 0.8 ATR(14).
- Initial stop beyond the signal extreme by 0.5 ATR, 3R target, 1% dynamic-equity risk.
- Exit only after an adverse M15 close through EMA50; switch to EMA20 beyond 2.5R.
- Five-bar compressed VWAP behavior reduces half; three losses or 3% realized session loss blocks new entries.
- Paper news exclusion and an explicit 20:00 UTC intraday flattening failsafe.

## Audit verdict

FAIL / do not add to the portfolio in raw form. The latest year is effectively flat and the five-year result is negative. The paper headline is not a historical trade-by-trade result, so it cannot validate the EA.

The 2024 row is the closest paper-sample reproduction and uses a reconstructed 2024 NFP/CPI/FOMC/GDP calendar. Longer rows are supplemental robustness checks: the paper does not supply a multi-year event file, and the static news exclusion is not extended outside 2024. The compressed-VWAP partial and the 20:00 UTC flatten are explicit implementation resolutions for omissions or contradictions in the paper.

No website, installer, BAT or active portfolio file was changed.
