# One-Hour Opening Range Breakout — Final Audit

## Decision

**US100 passes for demo-forward testing. XAU and XAG do not pass the untouched-year validation.** Do not add any H1 ORB to live BATs or the website yet.

## Final market comparison

| Market/configuration | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC P95 DD | 3Y return | 3Y PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAU 13:00 UTC, 1.5R | -0.26% | 0.99 | 48.28% | 10.01% | 145 | -0.10 | -0.02 | -14.03% | 17.96% | +41.56% | 1.36 |
| XAU 09:30 NY, 0.5R | +0.58% | 1.09 | 64.71% | 2.04% | 34 | 2.03 | 0.28 | -2.00% | 3.20% | +12.07% | 2.10 |
| XAG 18:00 NY, 0.5R | -2.13% | 0.92 | 60.00% | 7.78% | 95 | -2.77 | -0.27 | -10.34% | 12.24% | +1.52% | 1.06 |
| XAG 00:00 UTC, 2R | -11.54% | 0.71 | 41.18% | 15.27% | 102 | -5.00 | -0.75 | -22.89% | 24.29% | -8.02% | 0.84 |
| US100 08:20 NY, 2R | +1.04% | 1.02 | 58.05% | 10.06% | 174 | 0.37 | 0.09 | -18.15% | 23.58% | +47.74% | 1.24 |
| **US100 13:00 UTC, 6R** | **+23.00%** | **1.72** | **50.70%** | **6.81%** | **71** | **9.22** | **3.25** | **+0.12%** | **11.25%** | **+107.21%** | **1.96** |

## US100 demo configuration

- Instrument: Exness USTEC CFD.
- Opening range: 13:00–14:00 UTC, exactly 60 minutes.
- Entry window: 14:00–15:00 UTC only.
- Signal: M15 direct breakout; candle body at least 55%; 0.03 H1-ATR breakout buffer.
- Confirmation: permissive relative tick volume, opening >= 0.50 and breakout >= 0.70; no EMA, VWAP or profile filter.
- Stop: opposite side of the range plus 0.10 H1 ATR, capped at 3 H1 ATR.
- Nominal target: 6R; flat at 20:00 UTC; no break-even, trailing, Dynamic 50/20 or Safe filter.
- Risk: fixed 1% of current equity.

The locked-year realized average win/loss ratio was **1.68:1**, not 6:1, because many positions were closed by the 20:00 UTC session flat before reaching the distant nominal target. Average win was $151.95, average loss $-90.58, and historical expectancy was $32.39 per trade on the $10,000 test account.

## Robustness

- RR was tested from 0.5R through 10R. Development peaked at 6R and declined at 8R/10R.
- Locked year: +23.00%, PF 1.72, 50.70% win rate, 6.81% DD, 71 trades.
- Three-year Every Tick: +107.21%, PF 1.96, 54.19% win rate, 6.81% DD, 179 trades.
- Monte Carlo: 95.2% profitable paths, +0.12% return P5, +21.85% median, 11.25% P95 DD, 8.79% probability of >=10% DD, 0.06% probability of >=20% DD, and 0% simulated ruin.

## XAU and XAG verdict

XAU and XAG are rejected for this exact one-hour ORB concept. Gold's attractive development result failed in the locked year, and silver was negative in the locked year. Their positive full-period figures must not override the untouched validation failure.

## Integrity

- All parameter selection occurred on 2023-09-01 through 2025-08-31 before reading the locked 2025-09-01 through 2026-09-01 results.
- Safe mode used the existing completed-D1, no-lookahead Markov gate and was rejected independently for these candidates.
- Exness symbols are CFDs; volume is broker tick activity, not centralized exchange volume.
- No BAT, installed EA, selected portfolio set or website record was changed.
- The recommendation is demo-forward testing only; historical backtests and Monte Carlo are not guarantees.

## Artifacts

- Final graph: `Charts/H1 ORB FINAL DECISION AND MONTE CARLO.png`
- Final data: `FINAL AUDIT.json`, `FINAL AUDIT.csv`, `US100 RR6 VALIDATION.json`
- RR extension: `RR EXTENSION RESULTS.json`
- Demo set: `Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set`
