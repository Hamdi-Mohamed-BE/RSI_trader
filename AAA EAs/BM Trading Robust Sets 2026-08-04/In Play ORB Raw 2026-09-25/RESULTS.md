# In-play ORB — raw native results

Isolated MT5 tester (Exness-MT5Trial16), $10,000, 1% risk per trade, M5, 150 ms delay; windows end 2026-09-25. Screen = Model 1 (1-minute OHLC) on 3y/5y; confirmation = Model 4 (real ticks from 2026-01).
Cell = trades (per month, per trading day Mon-Fri) · return · PF · win · max equity DD · avg win/loss streak (max).

## Screen (Model 1)

| Variant | 3y | 3y control (random symbols) | 5y | 5y control | Gate |
|---|---|---|---|---|---|
| S_BOTH: Stocks: top-2 in-play, both directions, exit end of day | 454 (12.6/mo, 0.58/day) · -28.3% · PF 0.77 · win 44% · DD 34.5% · 1.7/2.3 (5/11) | 1325 (36.8/mo, 1.69/day) · -47.3% · PF 0.84 · win 46% · DD 55.8% · 1.8/2.2 (7/11) | 724 (12.1/mo, 0.56/day) · -35.8% · PF 0.82 · win 44% · DD 39.6% · 1.8/2.3 (7/11) | 2241 (37.4/mo, 1.72/day) · -67.6% · PF 0.86 · win 46% · DD 74.3% · 1.8/2.3 (8/13) | FAIL: 3y not positive; 3y PF 0.77; 5y not positive; 5y PF 0.82 |
| S_CONT: Stocks: top-2 in-play, continuation (break with the gap), end of day | 264 (7.3/mo, 0.34/day) · -18.3% · PF 0.76 · win 46% · DD 23.0% · 1.7/2.1 (5/9) | 669 (18.6/mo, 0.85/day) · -17.1% · PF 0.91 · win 48% · DD 22.7% · 1.8/2.2 (8/8) | 409 (6.8/mo, 0.31/day) · -27.4% · PF 0.77 · win 44% · DD 31.7% · 1.8/2.3 (10/17) | 1110 (18.5/mo, 0.85/day) · -35.0% · PF 0.88 · win 48% · DD 42.5% · 1.9/2.2 (8/10) | FAIL: 3y not positive; 3y PF 0.76; 3y not above control; 5y not positive; 5y PF 0.77 |
| S_EXH: Stocks: top-2 in-play, exhaustion (break against the gap), end of day | 189 (5.2/mo, 0.24/day) · -12.3% · PF 0.77 · win 42% · DD 18.1% · 1.8/2.5 (6/10) | 647 (18.0/mo, 0.83/day) · -34.6% · PF 0.81 · win 45% · DD 44.5% · 1.9/2.4 (7/10) | 313 (5.2/mo, 0.24/day) · -8.6% · PF 0.91 · win 43% · DD 18.1% · 1.9/2.5 (6/10) | 1111 (18.5/mo, 0.85/day) · -48.0% · PF 0.83 · win 45% · DD 55.2% · 1.9/2.4 (8/10) | FAIL: 3y not positive; 3y PF 0.77; 5y not positive; 5y PF 0.91 |
| S_BOTH2R: Stocks: top-2 in-play, both directions, 2R target | 454 (12.6/mo, 0.58/day) · -27.6% · PF 0.78 · win 44% · DD 34.4% · 1.7/2.2 (5/11) | 1325 (36.8/mo, 1.69/day) · -41.5% · PF 0.87 · win 46% · DD 48.0% · 1.8/2.2 (7/11) | 724 (12.1/mo, 0.56/day) · -37.2% · PF 0.81 · win 44% · DD 41.5% · 1.7/2.3 (7/11) | 2241 (37.4/mo, 1.72/day) · -62.7% · PF 0.87 · win 47% · DD 68.5% · 1.9/2.3 (8/13) | FAIL: 3y not positive; 3y PF 0.78; 5y not positive; 5y PF 0.81 |
| I_BOTH: Indices (macro days): top-1 in-play of US500/USTEC/US30, both directions, end of day | 159 (4.4/mo, 0.20/day) · -20.1% · PF 0.69 · win 42% · DD 26.4% · 1.7/2.3 (5/9) | 752 (20.9/mo, 0.96/day) · -0.2% · PF 1.00 · win 46% · DD 25.3% · 1.8/2.1 (8/11) | 191 (3.2/mo, 0.15/day) · -20.9% · PF 0.73 · win 43% · DD 26.3% · 1.7/2.3 (5/9) | 1244 (20.7/mo, 0.95/day) · -7.6% · PF 0.98 · win 46% · DD 26.4% · 1.8/2.1 (8/11) | FAIL: 3y not positive; 3y PF 0.69; 3y not above control; 5y not positive; 5y PF 0.73; 5y not above control |

Advancing to Model 4: none

