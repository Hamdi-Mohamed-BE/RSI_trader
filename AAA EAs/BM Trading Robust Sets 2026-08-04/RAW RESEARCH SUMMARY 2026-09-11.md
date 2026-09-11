# Raw research decisions — 11 September 2026

No full optimization pipeline was run. No EA, website record, BAT file or live MT5 deployment was changed.

## 1. Treasury Auction-Conditioned FX

Core rule: after a coupon Treasury note/bond auction, hold an equal-weight portfolio long EURUSD, long GBPUSD and short USDJPY from 17:00 New York to 17:00 New York on the immediately following qualifying U.S. macro day.

| Cost model | Events / legs | Return | PF | Win rate | Max DD | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Paper-style gross | 151 / 453 | +2.68% | 1.10 | 44.37% | 5.94% | 0.55 |
| Exness Raw Spread + commission + swap | 151 / 453 | -1.95% | 0.94 | 42.38% | 7.19% | -0.34 |
| Broker costs + 0.5-pip stress | 151 / 453 | -2.54% | 0.92 | 41.72% | 7.34% | -0.46 |

Recommendation: **skip the pipeline**. The recent gross effect is weak and execution costs erase it. The accessible official calendar is a conservative core subset (CPI, Employment Situation, GDP and Initial Claims), so this does not claim exact parity with the paper's private Bloomberg calendar.

## 2. Crazy Horse ORB — XAU and US100

The stated-minimum reconstruction uses the 09:30–09:45 New York opening range, first M5 body close outside, next-bar entry without a retest, opposite range edge as stop, 1R target, no undefined shelf trail, one trade per day and 16:00 close. The companion interpretation uses H1 EMA200 as a transparent proxy for the missing proprietary HTF signal.

| Symbol | Interpretation | 5Y trades | 5Y return | PF | Win rate | Max DD | Latest 1Y |
|---|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | Stated minimum | 1,143 | -21.03% | 0.95 | 48.99% | 36.61% | +3.81%, PF 1.06 |
| XAUUSD | H1 EMA200 proxy | 619 | -24.07% | 0.89 | 47.50% | 35.90% | +7.89%, PF 1.27 |
| USTEC | Stated minimum | 1,161 | -43.66% | 0.89 | 51.51% | 46.18% | -5.96%, PF 0.91 |
| USTEC | H1 EMA200 proxy | 591 | -7.13% | 0.97 | 53.30% | 22.27% | -1.11%, PF 0.98 |

Recommendation: **skip the pipeline for now**. No five-year raw row is profitable and the best win rate is 53.30%, not 80%. Reconsider only if the exact proprietary HTF signal, auto-stop, overextension threshold and shelf trailing are supplied.

## 3. Gold/Silver Cross-Session Momentum

Paper rule reconstructed: UTC sessions Asia 00:00–08:00, Europe 08:00–14:30 and US 14:30–24:00; hold long for the next session when the immediately preceding session return is positive, otherwise remain flat. Weekend signals reset.

| Symbol | Window | Trades | Return after broker costs | PF | Win rate | Max DD | Sharpe |
|---|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | Paper sample, 2024-07-22–2026-08-07 | 365 | +52.62% | 1.46 | 40.82% | 15.51% | 1.44 |
| XAUUSD | Five-year transfer | 906 | +63.34% | 1.24 | 36.75% | 15.51% | 0.81 |
| XAGUSD | Paper sample, 2024-07-22–2026-08-07 | 368 | +24.23% | 1.13 | 40.76% | 30.82% | 0.46 |
| XAGUSD | Five-year transfer | 917 | -34.13% | 0.94 | 35.55% | 56.10% | -0.23 |

Recommendation after the approved pipeline: **do not deploy XAUUSD; continue to skip XAGUSD**. XAU's selected 1% risk candidate produced +17.70%, PF 1.21 and 13.88% DD on 118 locked trades, but failed robustness because its 10,000-path Monte Carlo P5 was -16.29% and only 50% of nearby settings were profitable. The corrected raw rows above now include rollover swap, which the first raw report omitted.

## Evidence files

- `Auction and Cross Session Papers Research 2026-09-11/RAW RESULTS.md`
- `Auction and Cross Session Papers Research 2026-09-11/treasury-results.csv`
- `Auction and Cross Session Papers Research 2026-09-11/metals-cross-session-results.csv`
- `Crazy Horse ORB Raw Research 2026-09-11/RAW RESULTS.md`
- `Crazy Horse ORB Raw Research 2026-09-11/raw-results.csv`
- `XAU Cross Session Momentum Full Pipeline 2026-09-11/FULL REPORT.md`
