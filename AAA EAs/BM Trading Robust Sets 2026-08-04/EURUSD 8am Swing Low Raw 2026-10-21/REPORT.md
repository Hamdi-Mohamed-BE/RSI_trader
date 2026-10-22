# EURUSD 8am fresh swing low — RAW REPORT (2026-10-21)

**Verdict: REJECTED at the raw gate. Nothing advances to optimisation.**
Both main versions fail. No version reproduces the clip's "held up on the last 12 months". Every version that is positive
over 5 years earned it in 2021–23 and is flat or losing in the last two years. The short mirror does lose, as the clip
says, but so do every-day and random-day longs at the same time; only the "fresh swing low" filter is not an edge after costs.

Rules (frozen before testing): RULES.md. Generated tables: RESULTS.md / RESULTS.json. Graph: balance.png.
Native MT5 Model 4, EURUSD H1, 150 ms, $10k, 1% risk rounded up, study end 2026-10-17 exclusive; 30 native runs, 0 rejects/fails.
Real ticks only from 2026-01-01 (earlier = generated). Clock: server UTC with UK / US DST handled in the EA.

## Main versions (separate native runs)
| Version | Window | Trades | / month | / week | / day | Return | PF | Win % | Consistency | Sharpe | Bal DD | Eq DD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L8 (08:00 London) | 6m | 10 | 1.66 | 0.38 | 0.08 | −0.80% | 0.83 | 40.0 | 42.9% | −0.29 | 4.6% | 4.9% |
| L8 | 1y | 19 | 1.58 | 0.36 | 0.07 | −4.00% | 0.57 | 36.8 | 23.1% | −0.92 | 5.1% | 5.6% |
| L8 | 3y | 65 | 1.81 | 0.42 | 0.08 | +7.63% | 1.28 | 46.2 | 40.5% | 0.43 | 5.7% | 6.5% |
| L8 | 5y | 100 | 1.67 | 0.38 | 0.08 | +3.50% | 1.08 | 44.0 | 37.7% | 0.15 | 8.5% | 10.0% |
| NY8 (08:00 New York) | 6m | 13 | 2.16 | 0.50 | 0.10 | −2.50% | 0.59 | 38.5 | 57.1% | −1.07 | 5.0% | 5.9% |
| NY8 | 1y | 31 | 2.59 | 0.59 | 0.12 | −11.99% | 0.41 | 29.0 | 30.8% | −2.04 | 12.5% | 13.0% |
| NY8 | 3y | 76 | 2.11 | 0.49 | 0.10 | −15.04% | 0.69 | 31.6 | 29.7% | −0.72 | 26.3% | 27.5% |
| NY8 | 5y | 130 | 2.17 | 0.50 | 0.10 | +4.05% | 1.04 | 32.3 | 37.7% | 0.12 | 26.3% | 27.5% |
Streaks, mean R and exit mix per row: RESULTS.md. Frequency 0.4–0.5 per week, below the clip's "once or twice a week".

## Raw gate
| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Beats every-day control | Beats random control | Best day / trade | Verdict |
|---|---|---|---|---|---|---|---|
| L8 | yes | no (5y 1.08) | yes | yes | yes | no (5y flips to −$243) | **FAIL** |
| NY8 | no (3y −15%) | no | yes | yes | yes | no (5y flips to −$1,924) | **FAIL** |

## Controls (5 years)
| Version | Trades | / week | Return | PF | Mean R | Bal DD |
|---|---|---|---|---|---|---|
| Short mirror London / NY | 92 / 159 | 0.35 / 0.61 | −5.43% / −4.18% | 0.89 / 0.95 | −0.050 / +0.008 | 17.0% / 31.8% |
| Every weekday long London / NY | 1,299 / 1,297 | 4.98 / 4.97 | −27.48% / −24.62% | 0.97 / 0.97 | −0.012 / −0.003 | 58.9% / 48.3% |
| Random weekdays London (3 seeds) | 96–116 | 0.37–0.44 | −3.92% to +0.01% | 0.94–1.00 | −0.020 to +0.011 | 13.6–18.7% |
| Random weekdays NY (3 seeds) | 124–142 | 0.48–0.54 | −12.24% to −1.06% | 0.82–0.98 | −0.096 to +0.003 | 19.8–24.8% |

## Sensitivities (declared before testing; not used to pick a winner)
| Version | 5y return / PF / trades per week | Dev 2021-23 | Val 2023-24 | OOS 2024-26 | Last 12 months |
|---|---|---|---|---|---|
| Swing low within last 4 h, London | +65.7% / 1.14 / 2.08 (Bal DD 28.1%) | +60.6% / 1.40 | +5.6% / 1.10 | −2.4% / 0.98 | −23.9% / 0.57 |
| Swing low within last 4 h, NY | +77.8% / 1.12 / 2.97 (Bal DD 41.6%) | +70.0% / 1.34 | +3.8% / 1.03 | +0.8% / 1.01 | +3.7% / 1.05 |
| Fresh lower low, NY | +17.6% / 1.26 / 0.33 | +25.3% / 2.06 | +12.3% / 2.65 | −16.4% / 0.31 | −10.0% / 0.32 |
| 2 h exit, NY | +10.0% / 1.14 / 0.50 | +20.4% / 1.82 | +6.7% / 1.51 | −14.3% / 0.38 | −10.7% / 0.30 |
| 3-bar fractal London / NY | −9.0% / 0.68 ; −7.9% / 0.90 | | | | |
| Fresh lower low London | −2.9% / 0.82 | | | | |
| 2 h exit London / 6 h exit London / 6 h exit NY | +3.6% / 1.10 ; −2.0% / 0.97 ; +1.1% / 1.01 | | | | |
The "within last 4 h" version is the only one matching the clip's frequency; it passes the best-day check but misses PF 1.15
on 5y and made essentially all of its money in 2021–23. Best-day check fails for fresh-lower-low NY and 2 h NY.

## No-stop drift (loggers, every weekday, bid change in ATR(14,H1) units)
- Fresh 2-bar swing low (main): London +0.07 ATR / +1.5 pips after 4 h (t +0.3, n 100); New York −0.23 ATR / −1.9 pips (t −0.8).
- Swing low within last 4 h: London +0.21 ATR / +1.9 pips after 4 h over 5y (t +2.0), but concentrated in 2023–24
  (+0.72 ATR, t +3.2); dev +0.08 (t 0.4), OOS +0.11 (t 0.9). New York +0.10 ATR / +1.4 pips (t +0.9).
- Fresh swing HIGH days also drift up (London +0.13 ATR after 4 h), so "after a fresh swing" is not a directional signal.
- All weekdays: about 0 (London +0.00 ATR after 4 h; New York +0.04 ATR). A ~2-pip average move is close to EURUSD round-trip
  spread + commission, which is why the native results are near break-even.

## Notes / limits
- The clip gives no timezone, swing definition, stop or exit; ours are disclosed defaults (RULES.md). An exact copy of the
  clip's bot is not possible from the description.
- Generated ticks before 2026; Exness Trial16 costs; 1% risk rounded up. Bear review not run: no version passes the raw gate,
  so there is no stage-5 decision to review. Nothing installed, no SET/BAT/live change, no push.
