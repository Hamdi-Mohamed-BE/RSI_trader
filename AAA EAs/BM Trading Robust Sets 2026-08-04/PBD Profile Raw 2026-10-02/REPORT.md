# PBD Exness CFD profile proxy — raw results

RAW WATCHLIST ONLY

## 1y

| Asset | Version | Return | Net PF | Win rate | Equity DD | Trades | Closed Sharpe | Max W/L run | Tick quality |
|---|---|---|---|---|---|---|---|---|---|
| US100 | Value-area reclaim | -7.25% | 0.764 | 38.3% | 16.77% | 47 | -0.78 | 3/7 | 75% real ticks |
| US100 | Weak-breakout fade | -1.10% | 0.784 | 50.0% | 2.88% | 10 | -0.34 | 2/2 | 75% real ticks |
| US100 | Strong breakout | +4.44% | 4.223 | 75.0% | 2.39% | 8 | — | 2/1 | 75% real ticks |
| US100 | Combined | -2.25% | 0.938 | 46.0% | 14.74% | 63 | -0.18 | 6/7 | 75% real ticks |
| Gold | Value-area reclaim | +6.04% | 1.238 | 45.8% | 10.34% | 48 | 0.67 | 7/5 | 75% real ticks |
| Gold | Weak-breakout fade | +1.80% | 1.883 | 77.8% | 1.70% | 9 | — | 4/1 | 75% real ticks |
| Gold | Strong breakout | +3.86% | 2.454 | 44.4% | 2.29% | 9 | — | 1/2 | 75% real ticks |
| Gold | Combined | +11.97% | 1.391 | 50.0% | 10.03% | 66 | 1.07 | 8/6 | 75% real ticks |
| Bitcoin | Value-area reclaim | -10.64% | 0.736 | 38.1% | 16.04% | 63 | -1.10 | 5/10 | 75% real ticks |
| Bitcoin | Weak-breakout fade | +2.07% | 1.489 | 60.0% | 2.48% | 10 | 0.58 | 3/2 | 75% real ticks |
| Bitcoin | Strong breakout | -5.45% | 0.384 | 35.3% | 7.02% | 17 | -1.51 | 2/3 | 75% real ticks |
| Bitcoin | Combined | -12.65% | 0.754 | 40.4% | 16.09% | 89 | -1.21 | 3/5 | 75% real ticks |

## 6m

| Asset | Version | Return | Net PF | Win rate | Equity DD | Trades | Closed Sharpe | Max W/L run | Tick quality |
|---|---|---|---|---|---|---|---|---|---|
| US100 | Value-area reclaim | -10.96% | 0.503 | 24.1% | 16.78% | 29 | -2.17 | 2/7 | 100% real ticks |
| US100 | Weak-breakout fade | +0.86% | No losses | 100.0% | 0.05% | 1 | — | 1/0 | 100% real ticks |
| US100 | Strong breakout | +1.43% | 5.346 | 80.0% | 1.82% | 5 | — | 2/1 | 100% real ticks |
| US100 | Combined | -7.98% | 0.635 | 35.3% | 14.75% | 34 | -1.46 | 3/7 | 100% real ticks |
| Gold | Value-area reclaim | +12.66% | 2.077 | 54.2% | 5.39% | 24 | 2.20 | 7/5 | 100% real ticks |
| Gold | Weak-breakout fade | +0.41% | 1.401 | 75.0% | 1.72% | 4 | — | 2/1 | 100% real ticks |
| Gold | Strong breakout | +4.20% | 3.821 | 50.0% | 1.48% | 6 | — | 1/1 | 100% real ticks |
| Gold | Combined | +17.58% | 2.179 | 55.9% | 5.48% | 34 | 2.45 | 8/6 | 100% real ticks |
| Bitcoin | Value-area reclaim | -11.49% | 0.435 | 31.0% | 15.54% | 29 | -2.80 | 2/10 | 100% real ticks |
| Bitcoin | Weak-breakout fade | -0.07% | 0.977 | 50.0% | 2.49% | 6 | — | 2/2 | 100% real ticks |
| Bitcoin | Strong breakout | -2.52% | 0.458 | 40.0% | 4.20% | 10 | -1.24 | 1/2 | 100% real ticks |
| Bitcoin | Combined | -12.72% | 0.522 | 36.4% | 16.10% | 44 | -2.61 | 2/5 | 100% real ticks |

## Profile attribution within combined runs (not standalone)

| Asset | Profile group | Trades | Net contribution | PF | Win rate |
|---|---|---|---|---|---|
| US100 | P/b clip core | 24 | $+123.71 | 1.094 | 50.0% |
| US100 | D extension | 39 | $-349.03 | 0.851 | 43.6% |
| Gold | P/b clip core | 20 | $+486.89 | 1.683 | 65.0% |
| Gold | D extension | 46 | $+710.20 | 1.302 | 43.5% |
| Bitcoin | P/b clip core | 22 | $-625.10 | 0.524 | 40.9% |
| Bitcoin | D extension | 67 | $-639.94 | 0.832 | 40.3% |

## Limitations

- This is our frozen operationalisation of an incomplete clip, not a verified champion model. The D balance/reclaim rules are an explicit extension; the clip did not define them. It does not establish that P/b shapes imply aggressive buyers/sellers.
- All three Exness CFDs use broker quote tick-volume counts. Historical M1 real_volume is zero in every exported profile input. The profile spreads each M1 count uniformly over its high-low interval, not actual exchange volume-at-price. A real-tick execution-quality label does not fix this signal-data limitation.
- Profile freezes 09:30–10:30 New York, 64 bins and 70% value area. P/b require POC/centroid skew and directional net movement; D requires a centred distribution. Other days are excluded. Identical NY window for all assets; Bitcoin also trades weekends. This does NOT promise a setup every day.
- Reclaim targets the opposite value-area edge; weak P/b breakout fade targets POC; high-activity breakout targets 2R. M5 signals, causal next-tick fills, prior ATR14/prior20 activity, stop buffer .1 ATR, entry before 15:30 and flat at 16:00/pre-close. No optimisation, trailing or break-even.
- Each asset/version has an independent $10,000 balance with 1% requested balance risk, floor lot step and no minimum-lot override. Combined means modules share a single position slot on ONE asset; the three asset accounts are NOT a shared portfolio. Do not sum their percentages into a portfolio backtest.
- The last-year window is 2 Oct 2025–1 Oct 2026; latest6m is a fresh independent-start account over 2 Apr–1 Oct 2026, not a clipped compounded ledger. Windows overlap and are not untouched holdouts. Native tick coverage/quality and cost details are preserved in raw evidence.
- Exact native equity DD includes open positions. Closed-balance charts omit floating losses; the separate floating chart samples once/minute and is not a complete tick path. Closed Sharpe is based on daily realized balance changes with calendar-day annualisation; it is not an intraday equity Sharpe.
- Independent Python reconstruction checked 665 positions across overlapping runs and 317,760 exported M1 inputs, plus every profile classification and signal. It shares the broker history source, not a second data vendor. Max filled stop-risk / requested budget 1.197×; fills, fees and gaps can exceed nominal risk.
- 10,000 block5 bootstrap paths and DSR12 are historical diagnostics, not forward probabilities or FTMO pass/payout forecasts. Twelve current candidates and prior profile/strategy idea selection create bias. Measured extra-cost stress, random controls, pristine holdout and prospective demo are absent; 0.05R extra-cost sensitivity is illustrative only.
- Sparse weak-fade trades, no-loss samples and high winning streaks are not reliable evidence of an edge. No live deployment, active-account change, website/BAT update, paid data or Git push.
