# Per-EA kill-switch thresholds

Generated 2026-10-20 14:20 UTC. Method: day-block bootstrap (10,000 paths, 5-day blocks, seed 20261020) of each EA's cached native trades in R (estimated from planned initial-stop risk). WATCH = 95th percentile of the ≈3-month (63 trading days) drawdown / losing streak; KILL = max(99th percentile, worst seen in any 63-trading-day window of the evidence; streak: worst ever). Full-window max DD is in the JSON. Multiply R by the live risk % to get account %: at 1% risk, 10R ≈ 10% of balance.

These are pre-commitments, not forecasts: a KILL flag recommends switching the EA off and reviewing it; the owner decides.

| Phase | EA | Evidence | Trades | /month | Hist worst 3-month DD R | Hist max losing streak | WATCH DD R | KILL DD R | WATCH streak | KILL streak | KILL worst day R |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| live | BTC Top Down FVG Liquidity | 5y | 117 | 2.0 | 5.96 | 9 | 4.95 | **6.14** | 4 | **9** | -2.11 |
| live | DMC Current XAU | 5y | 345 | 5.76 | 16.49 | 12 | 9.83 | **16.49** | 8 | **12** | -1.82 |
| live | DMC Fresh Reaction US100 | 5y | 82 | 1.39 | 3.75 | 3 | 3.68 | **5.04** | 3 | **4** | -1.68 |
| live | DMC Fresh Reaction XAU | 5y | 85 | 1.44 | 5.58 | 11 | 3.73 | **5.58** | 4 | **11** | -1.4 |
| live | EMA3 | 5y | 208 | 3.54 | 8.82 | 6 | 7.01 | **9.28** | 5 | **6** | -3.01 |
| live | Gold News V9 Direction | 1y | 0 | — | — | — | — | — | — | — | — |
| live | Gold Overnight Value Area | 5y | 1027 | 17.11 | 16.4 | 5 | 7.7279 | **16.4** | 5 | **6** | -1.03 |
| live | Nasdaq 5M Candle Momentum | 5y | 923 | 15.4 | 19.81 | 9 | 15.13 | **19.81** | 10 | **12** | -2.54 |
| live | Nasdaq Overnight | 5y | 199 | 5.17 | 4.67 | 7 | 2.75 | **4.67** | 5 | **7** | -1.01 |
| live | News Pulse BTC | 5y | 242 | 4.05 | 23.09 | 14 | 9.79 | **23.09** | 6 | **14** | -7.37 |
| live | News Pulse EURUSD | 5y | 240 | 4.02 | 6.94 | 9 | 6.01 | **8.54** | 6 | **9** | -4.44 |
| live | News Pulse XAG | 5y | 139 | 2.33 | 17.63 | 13 | 14.33 | **20.0** | 5 | **13** | -12.48 |
| live | News Pulse XAU | 5y | 194 | 3.25 | 7.05 | 4 | 4.68 | **8.08** | 4 | **5** | -4.66 |
| live | ORB Volume Profile | 5y | 304 | 5.08 | 5.8 | 6 | 6.32 | **7.94** | 7 | **9** | -1.03 |
| live | ORB Volume Profile Volume Confirmed | 5y | 120 | 2.04 | 3.53 | 7 | 3.92 | **5.17** | 5 | **7** | -1.01 |
| live | US100 H1 ORB 13UTC | 5y | 289 | 4.84 | 11.9 | 8 | 7.31 | **11.9** | 6 | **8** | -1.93 |
| live | US100 Hourly Profiles | 1y | 0 | — | — | — | — | — | — | — | — |
| live | US100 Month End Flow | 5y | 175 | 2.96 | 5.24 | 6 | 6.06 | **7.76** | 5 | **7** | -1.62 |
| live | US100 ORB New York M30 | 5y | 96 | 1.62 | 4.02 | 6 | 4.03 | **5.14** | 4 | **6** | -1.03 |
| live | US100 Selective ORB V3 | 5y | 34 | 0.62 | 1.02 | 2 | 2.82 | **2.84** | 2 | **2** | -2.82 |
| live | US30 Hourly Profiles | 1y | 0 | — | — | — | — | — | — | — | — |
| live | USDJPY London Open Momentum | 5y | 461 | 7.7 | 5.43 | 6 | 6.24 | **8.16** | 7 | **8** | -1.23 |
| live | XAU ORB London NY Overlap M30 | 5y | 134 | 2.25 | 5.55 | 7 | 3.07 | **5.55** | 4 | **7** | -1.04 |
| live | XAU ORB New York M30 | 5y | 84 | 1.43 | 3.35 | 6 | 2.28 | **3.35** | 4 | **6** | -1.0 |
| live | XAU RSI VWAP | 5y | 259 | 4.36 | 5.22 | 3 | 4.82 | **6.45** | 3 | **4** | -2.25 |
| live | XAU Trend Progression | 5y | 214 | 3.64 | 5.02 | 3 | 5.67 | **7.63** | 4 | **5** | -3.19 |
| live | XAU Weakness | 5y | 244 | 4.22 | 9.08 | 9 | 7.71 | **9.92** | 7 | **9** | -1.99 |
| paused | 3 Way Gold | 5y | 682 | 11.39 | 7.57 | 9 | 6.97 | **9.02** | 6 | **9** | -2.49 |
| paused | BTC POC Fibonacci | 5y | 114 | 1.96 | 7.06 | 9 | 5.13 | **7.06** | 5 | **9** | -2.18 |
| paused | LTA Volume Profile | 5y | 609 | 10.53 | 19.45 | 16 | 15.09 | **19.89** | 13 | **17** | -2.12 |
| paused | XAU Regime Switch | 5y | 211 | 3.52 | 11.14 | 9 | 8.65 | **11.23** | 9 | **12** | -2.02 |
| paused | XAU Slow Trend | 5y | 1020 | 17.01 | 14.92 | 8 | 13.369 | **17.16** | 8 | **10** | -2.22 |
| review | Asia Breakout | 5y | 189 | 3.24 | 8.72 | 8 | 7.57 | **9.67** | 6 | **8** | -3.24 |
| review | ETH Top Down FVG Liquidity | 5y | 59 | 1.0 | 4.18 | 6 | 3.14 | **4.22** | 3 | **6** | -1.13 |
| review | Sell Nasdaq 15min | 5y | 268 | 4.53 | 10.9 | 11 | 7.55 | **10.9** | 7 | **11** | -2.02 |
| review | XAU Elliott Wave 1-2-3 | 5y | 116 | 1.97 | 9.35 | 8 | 4.97 | **9.35** | 5 | **8** | -1.96 |
| review | XAU Squeeze Momentum Standard | 5y | 48 | 0.93 | 2.27 | 4 | 1.39 | **2.27** | 2 | **4** | -0.81 |

No threshold (under 30 R-measured trades or no cache): Gold News V9 Direction, US30 Hourly Profiles, US100 Hourly Profiles.
