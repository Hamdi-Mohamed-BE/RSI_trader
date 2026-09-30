# EMA + VWAP pullback (US100, M3) — raw native results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), M3, Model 4 (real ticks from 2026-01, bars-generated before), 150 ms delay; windows end 2026-09-25. No optimization.
Cell = trades (per month, per trading day Mon-Fri) · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## USTEC

| Period | R2 — EMA/VWAP pullback, 2R target | R1 — EMA/VWAP pullback, 1R target |
|---|---|---|
| 6m | 221 (36.6/mo, 1.67/day) · -27.3% · PF 0.81 · win 32% · DD 31.9% · 1.4/2.9 (4/11) | 228 (37.7/mo, 1.73/day) · -11.6% · PF 0.91 · win 49% · DD 20.4% · 2.0/2.0 (6/7) |
| 1y | 445 (37.1/mo, 1.70/day) · -20.6% · PF 0.93 · win 35% · DD 36.8% · 1.5/2.8 (5/11) | 457 (38.1/mo, 1.75/day) · -12.6% · PF 0.95 · win 50% · DD 24.6% · 2.1/2.1 (7/7) |
| 3y | 1322 (36.7/mo, 1.69/day) · -83.2% · PF 0.76 · win 31% · DD 83.5% · 1.5/3.3 (6/23) | 1364 (37.9/mo, 1.74/day) · -79.5% · PF 0.75 · win 46% · DD 79.8% · 1.9/2.3 (8/11) |
| 5y | 2183 (36.4/mo, 1.67/day) · -95.1% · PF 0.80 · win 31% · DD 95.2% · 1.5/3.3 (6/23) | 2267 (37.8/mo, 1.74/day) · -95.9% · PF 0.72 · win 45% · DD 95.9% · 1.8/2.3 (8/11) |

Trend-only controls (3y, 5y):

| Period | C2 (control for R2) | C1 (control for R1) |
|---|---|---|
| 3y | 1501 (41.7/mo, 1.91/day) · -8.7% · PF 0.99 · win 36% · DD 39.7% · 1.6/2.8 (7/13) | 1537 (42.7/mo, 1.96/day) · -41.3% · PF 0.94 · win 49% · DD 47.8% · 1.9/1.9 (11/13) |
| 5y | 2503 (41.7/mo, 1.92/day) · -37.6% · PF 0.97 · win 36% · DD 60.1% · 1.6/2.8 (7/13) | 2561 (42.7/mo, 1.96/day) · -67.0% · PF 0.92 · win 49% · DD 70.6% · 1.9/2.0 (11/13) |

## Pre-registered gate (step 4)

Pass = positive on 3y and 5y, PF ≥ 1.15 on 3y and 5y, ≥ 30 trades per window, and higher return than its trend-only control on 3y and 5y.

| Symbol | Variant | 3y | 5y | Control 3y | Control 5y | Result |
|---|---|---|---|---|---|---|
| USTEC | R2 | -83.2% PF 0.76 | -95.1% PF 0.80 | -8.7% PF 0.99 | -37.6% PF 0.97 | FAIL: 3y not positive; 3y PF 0.76; 3y not above control; 5y not positive; 5y PF 0.80; 5y not above control |
| USTEC | R1 | -79.5% PF 0.75 | -95.9% PF 0.72 | -41.3% PF 0.94 | -67.0% PF 0.92 | FAIL: 3y not positive; 3y PF 0.75; 3y not above control; 5y not positive; 5y PF 0.72; 5y not above control |

Passed: none
