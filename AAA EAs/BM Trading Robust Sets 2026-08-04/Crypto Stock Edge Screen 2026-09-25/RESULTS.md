# Crypto/stock edge screen — results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk to a catastrophe stop (lots rounded up), long only. Screen = Model 1 (1-minute OHLC); windows 3y (2023-09-01) and 5y (2021-09-01) to 2026-09-01. No optimization.
Cell = trades · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## C1 — Crypto time-series momentum (20-day return > 0, long/flat)
Evidence: Liu & Tsyvinski (2021), Risks and Returns of Cryptocurrency, RFS. Control: always long.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| BTCUSD | 64 · +14.6% · PF 1.81 · win 27% · DD 8.4% · 1.4/3.9 (2/14) | 1 · +16.1% · PF 7337.50 · win 100% · DD 25.7% | 104 · +15.3% · PF 1.50 · win 28% · DD 8.4% · 1.2/3.1 (2/14) | 7 · +5.9% · PF 1.67 · win 14% · DD 23.1% | FAIL: 3y not above control |
| ETHUSD | 67 · +8.4% · PF 1.58 · win 30% · DD 9.7% · 1.4/3.4 (3/9) | 2 · -1.6% · PF 0.50 · win 50% · DD 16.9% | 112 · +3.8% · PF 1.15 · win 29% · DD 9.7% · 1.3/3.3 (3/9) | 4 · -2.4% · PF 0.28 · win 25% · DD 9.0% | PASS |

Breadth: 2/2 symbols positive over 5y.

## C2 — Crypto volatility breakout (open + 0.5 x prior range, exit next open)
Evidence: Larry Williams range breakout; common crypto practice. Control: buy every daily open.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| BTCUSD | 458 · +35.6% · PF 1.12 · win 40% · DD 25.5% · 1.7/2.5 (6/9) | 1096 · +69.2% · PF 1.08 · win 43% · DD 34.1% | 754 · +23.8% · PF 1.06 · win 39% · DD 25.5% · 1.6/2.4 (6/16) | 1826 · +11.9% · PF 1.01 · win 41% · DD 49.8% | FAIL: 3y PF 1.12; 3y not above control; 5y PF 1.06 |
| ETHUSD | 463 · +6.0% · PF 1.02 · win 36% · DD 25.7% · 1.4/2.5 (5/11) | 1096 · +26.8% · PF 1.05 · win 43% · DD 29.6% | 774 · +4.0% · PF 1.01 · win 38% · DD 27.3% · 1.5/2.4 (5/11) | 1825 · -17.3% · PF 0.97 · win 42% · DD 45.1% | FAIL: 3y PF 1.02; 3y not above control; 5y PF 1.01 |

Breadth: 2/2 symbols positive over 5y.

## S1 — Overnight drift (buy 15:40 NY, sell 09:35 NY next session)
Evidence: Kelly & Clark (2011); Lou, Polk & Skouras (2019), JFE. Control: intraday 09:35-15:40 NY.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| US500 | 743 · +3.5% · PF 1.07 · win 53% · DD 4.3% · 2.1/1.9 (8/8) | 764 · -5.9% · PF 0.90 · win 52% · DD 7.7% | 1242 · -6.5% · PF 0.92 · win 52% · DD 11.8% · 2.1/2.0 (11/9) | 1278 · -9.4% · PF 0.91 · win 51% · DD 11.1% | FAIL: 3y PF 1.07; 5y not positive; 5y PF 0.92 |
| US30 | 743 · +2.8% · PF 1.06 · win 52% · DD 4.9% · 2.1/2.0 (7/8) | 764 · -1.3% · PF 0.98 · win 53% · DD 6.0% | 1242 · -4.8% · PF 0.94 · win 50% · DD 11.1% · 2.1/2.1 (8/9) | 1278 · -5.5% · PF 0.95 · win 53% · DD 9.7% | FAIL: 3y PF 1.06; 5y not positive; 5y PF 0.94 |
| USTEC | 743 · +5.7% · PF 1.12 · win 53% · DD 4.5% · 2.0/1.9 (8/9) | 765 · -3.9% · PF 0.94 · win 52% · DD 6.2% | 1242 · -3.8% · PF 0.95 · win 50% · DD 11.1% · 2.0/2.0 (11/9) | 1279 · -4.9% · PF 0.95 · win 52% · DD 7.9% | FAIL: 3y PF 1.12; 5y not positive; 5y PF 0.95 |
| AAPL | 506 · -1.9% · PF 0.94 · win 51% · DD 6.1% · 2.1/2.0 (10/7) | 509 · -1.5% · PF 0.96 · win 54% · DD 7.2% | 845 · -6.9% · PF 0.87 · win 50% · DD 11.6% · 2.0/2.0 (10/7) | 848 · -0.9% · PF 0.99 · win 53% · DD 7.8% | FAIL: 3y not positive; 3y PF 0.94; 3y not above control; 5y not positive; 5y PF 0.87; 5y not above control |
| AMD | 506 · +2.2% · PF 1.06 · win 49% · DD 8.1% · 1.9/2.0 (6/8) | 511 · -10.2% · PF 0.79 · win 44% · DD 18.6% | 845 · -8.4% · PF 0.85 · win 47% · DD 17.9% · 1.8/2.1 (6/11) | 852 · -14.6% · PF 0.81 · win 46% · DD 19.1% | FAIL: 3y PF 1.06; 5y not positive; 5y PF 0.85 |
| AMZN | 506 · -0.8% · PF 0.98 · win 48% · DD 4.0% · 1.9/2.1 (8/10) | 507 · -2.2% · PF 0.94 · win 49% · DD 5.9% | 845 · -3.9% · PF 0.93 · win 49% · DD 7.4% · 2.0/2.1 (8/10) | 850 · -7.6% · PF 0.89 · win 49% · DD 9.7% | FAIL: 3y not positive; 3y PF 0.98; 5y not positive; 5y PF 0.93 |
| AVGO | 506 · +7.3% · PF 1.19 · win 54% · DD 3.4% · 2.2/1.9 (9/10) | 495 · +0.8% · PF 1.02 · win 48% · DD 7.5% | 845 · -2.1% · PF 0.97 · win 49% · DD 12.1% · 2.0/2.0 (9/10) | 829 · +1.7% · PF 1.02 · win 49% · DD 7.2% | FAIL: 5y not positive; 5y PF 0.97; 5y not above control |
| GOOGL | 506 · -0.4% · PF 0.99 · win 49% · DD 4.2% · 2.0/2.0 (6/6) | 494 · -3.6% · PF 0.91 · win 53% · DD 11.3% | 845 · -7.7% · PF 0.88 · win 48% · DD 10.4% · 1.9/2.1 (6/11) | 829 · -9.7% · PF 0.86 · win 51% · DD 16.1% | FAIL: 3y not positive; 3y PF 0.99; 5y not positive; 5y PF 0.88 |
| INTC | 506 · -5.7% · PF 0.85 · win 45% · DD 13.1% · 1.8/2.4 (5/14) | 509 · -14.6% · PF 0.65 · win 45% · DD 15.5% | 845 · -19.5% · PF 0.67 · win 43% · DD 25.9% · 1.8/2.6 (6/14) | 850 · -25.6% · PF 0.63 · win 46% · DD 25.9% | FAIL: 3y not positive; 3y PF 0.85; 5y not positive; 5y PF 0.67 |
| JPM | 506 · -1.7% · PF 0.95 · win 48% · DD 4.6% · 1.8/1.9 (7/6) | 494 · -2.8% · PF 0.94 · win 54% · DD 7.0% | 845 · -5.6% · PF 0.91 · win 48% · DD 9.2% · 1.9/2.1 (7/7) | 830 · -12.3% · PF 0.83 · win 52% · DD 13.1% | FAIL: 3y not positive; 3y PF 0.95; 5y not positive; 5y PF 0.91 |
| META | 506 · -3.1% · PF 0.92 · win 48% · DD 6.5% · 2.0/2.2 (5/13) | 506 · -0.8% · PF 0.98 · win 47% · DD 9.3% | 845 · -8.1% · PF 0.87 · win 47% · DD 9.0% · 2.0/2.3 (5/13) | 848 · -4.4% · PF 0.94 · win 49% · DD 9.6% | FAIL: 3y not positive; 3y PF 0.92; 3y not above control; 5y not positive; 5y PF 0.87; 5y not above control |
| MSFT | 506 · -0.4% · PF 0.99 · win 47% · DD 5.5% · 1.8/2.1 (8/10) | 511 · -11.1% · PF 0.76 · win 51% · DD 15.8% | 845 · -4.7% · PF 0.92 · win 47% · DD 9.2% · 1.9/2.2 (11/10) | 853 · -13.8% · PF 0.82 · win 51% · DD 18.2% | FAIL: 3y not positive; 3y PF 0.99; 5y not positive; 5y PF 0.92 |
| NFLX | 506 · -13.7% · PF 0.61 · win 43% · DD 13.8% · 1.8/2.5 (6/10) | 510 · -9.2% · PF 0.81 · win 51% · DD 11.8% | 845 · -27.7% · PF 0.52 · win 40% · DD 28.0% · 1.7/2.7 (6/10) | 852 · -21.2% · PF 0.73 · win 51% · DD 22.6% | FAIL: 3y not positive; 3y PF 0.61; 3y not above control; 5y not positive; 5y PF 0.52; 5y not above control |
| NVDA | 506 · +4.2% · PF 1.14 · win 52% · DD 2.6% · 2.0/1.9 (8/10) | 509 · +0.2% · PF 1.00 · win 52% · DD 8.8% | 845 · +0.3% · PF 1.01 · win 49% · DD 8.1% · 1.9/2.0 (8/10) | 850 · +1.7% · PF 1.02 · win 51% · DD 8.5% | FAIL: 3y PF 1.14; 5y PF 1.01; 5y not above control |
| TSLA | 506 · +5.0% · PF 1.14 · win 53% · DD 2.7% · 2.1/1.9 (10/7) | 508 · -5.6% · PF 0.88 · win 49% · DD 10.6% | 844 · +8.6% · PF 1.15 · win 53% · DD 3.9% · 2.1/1.9 (10/7) | 850 · -6.8% · PF 0.92 · win 49% · DD 12.0% | FAIL: 3y PF 1.14 |

Breadth: 2/15 symbols positive over 5y.

## S2 — Daily RSI(2) pullback above SMA200 (exit close > SMA5 or 10 days)
Evidence: Connors & Alvarez, Short Term Trading Strategies That Work (2008); many SPY replications. Control: random ~5% of days above SMA200, 3-day hold.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| US500 | 37 · +6.7% · PF 3.44 · win 84% · DD 1.6% · 6.2/1.2 (13/2) | 22 · -2.2% · PF 0.53 · win 41% · DD 2.7% | 55 · +7.5% · PF 2.59 · win 73% · DD 1.7% · 3.3/1.2 (13/2) | 31 · -2.2% · PF 0.62 · win 42% · DD 3.4% | PASS |
| US30 | 42 · +1.2% · PF 1.16 · win 67% · DD 3.9% · 3.1/1.6 (7/3) | 21 · -1.6% · PF 0.62 · win 43% · DD 2.9% | 63 · +1.7% · PF 1.16 · win 65% · DD 4.4% · 2.9/1.5 (7/3) | 32 · -2.9% · PF 0.55 · win 44% · DD 4.0% | PASS |
| USTEC | 42 · +5.3% · PF 2.27 · win 71% · DD 2.3% · 4.3/1.7 (9/3) | 23 · -1.0% · PF 0.79 · win 52% · DD 2.4% | 61 · +9.3% · PF 2.88 · win 72% · DD 2.4% · 4.0/1.4 (9/3) | 32 · -1.3% · PF 0.80 · win 50% · DD 3.3% | PASS |
| AAPL | 33 · +1.1% · PF 1.24 · win 64% · DD 2.0% · 2.6/1.7 (5/3) | 19 · -2.9% · PF 0.52 · win 26% · DD 4.8% | 53 · -0.6% · PF 0.94 · win 58% · DD 3.4% · 2.2/1.6 (5/3) | 30 · -2.3% · PF 0.71 · win 37% · DD 4.8% | FAIL: 5y not positive; 5y PF 0.94 |
| AMD | 26 · +3.3% · PF 1.82 · win 73% · DD 2.2% · 3.8/1.4 (6/2) | 18 · -2.3% · PF 0.62 · win 28% · DD 3.5% | 41 · +4.9% · PF 1.82 · win 73% · DD 2.1% · 3.3/1.2 (6/2) | 27 · -3.5% · PF 0.58 · win 30% · DD 5.1% | PASS |
| AMZN | 30 · -2.5% · PF 0.65 · win 57% · DD 3.9% · 1.9/1.4 (4/3) | 20 · -0.2% · PF 0.94 · win 55% · DD 2.5% | 35 · -1.9% · PF 0.74 · win 60% · DD 3.9% · 1.9/1.4 (4/3) | 25 · +0.1% · PF 1.04 · win 56% · DD 2.5% | FAIL: 3y not positive; 3y PF 0.65; 3y not above control; 5y not positive; 5y PF 0.74; 5y not above control |
| AVGO | 32 · +2.7% · PF 1.49 · win 62% · DD 3.8% · 3.3/1.7 (11/4) | 22 · -0.2% · PF 0.97 · win 32% · DD 3.6% | 47 · +3.4% · PF 1.42 · win 66% · DD 3.7% · 3.4/1.6 (11/4) | 33 · -0.0% · PF 1.00 · win 42% · DD 3.6% | PASS |
| GOOGL | 33 · +0.4% · PF 1.06 · win 70% · DD 3.4% · 2.6/1.1 (6/2) | 23 · -2.1% · PF 0.71 · win 48% · DD 4.1% | 47 · +2.2% · PF 1.24 · win 66% · DD 3.4% · 2.4/1.2 (6/3) | 30 · -2.2% · PF 0.75 · win 47% · DD 4.1% | FAIL: 3y PF 1.06 |
| INTC | 20 · +0.8% · PF 1.28 · win 70% · DD 1.5% · 3.5/1.2 (6/2) | 15 · -2.3% · PF 0.41 · win 33% · DD 2.3% | 24 · +0.4% · PF 1.11 · win 71% · DD 1.9% · 3.4/1.2 (6/2) | 20 · -3.1% · PF 0.40 · win 35% · DD 3.3% | FAIL: 5y PF 1.11; 5y 24 trades |
| JPM | 23 · +1.9% · PF 1.40 · win 61% · DD 3.1% · 2.3/1.5 (5/3) | 21 · -3.4% · PF 0.47 · win 38% · DD 4.1% | 40 · +4.2% · PF 1.54 · win 62% · DD 3.0% · 2.5/1.5 (5/3) | 31 · -3.2% · PF 0.62 · win 48% · DD 4.3% | PASS |
| META | 29 · -1.2% · PF 0.77 · win 55% · DD 4.2% · 1.8/1.3 (2/2) | 16 · +1.2% · PF 1.46 · win 44% · DD 2.9% | 40 · +1.1% · PF 1.15 · win 55% · DD 4.4% · 2.0/1.5 (4/3) | 22 · +1.4% · PF 1.41 · win 50% · DD 2.9% | FAIL: 3y not positive; 3y PF 0.77; 3y not above control; 5y not above control |
| MSFT | 17 · -0.8% · PF 0.71 · win 41% · DD 2.7% · 2.3/2.5 (5/5) | 14 · -2.5% · PF 0.42 · win 50% · DD 3.4% | 33 · +2.4% · PF 1.55 · win 64% · DD 2.7% · 2.9/1.9 (5/5) | 22 · -2.4% · PF 0.56 · win 45% · DD 3.9% | FAIL: 3y not positive; 3y PF 0.71; 3y 17 trades |
| NFLX | 25 · +1.3% · PF 1.27 · win 72% · DD 2.4% · 3.6/1.4 (8/2) | 16 · +1.8% · PF 2.03 · win 56% · DD 1.1% | 42 · +0.2% · PF 1.03 · win 71% · DD 4.0% · 3.8/1.5 (8/3) | 25 · +2.6% · PF 1.97 · win 56% · DD 1.1% | FAIL: 3y not above control; 5y PF 1.03; 5y not above control |
| NVDA | 34 · +3.4% · PF 1.71 · win 68% · DD 2.0% · 2.6/1.2 (5/2) | 21 · -0.2% · PF 0.95 · win 57% · DD 2.2% | 49 · +3.8% · PF 1.51 · win 71% · DD 2.3% · 2.7/1.2 (6/2) | 30 · -1.4% · PF 0.75 · win 53% · DD 2.9% | PASS |
| TSLA | 25 · -0.8% · PF 0.88 · win 48% · DD 2.9% · 1.7/1.6 (3/4) | 14 · -1.6% · PF 0.55 · win 36% · DD 2.5% | 38 · +2.9% · PF 1.37 · win 63% · DD 3.2% · 2.7/1.6 (11/4) | 20 · -1.6% · PF 0.66 · win 35% · DD 3.3% | FAIL: 3y not positive; 3y PF 0.88 |
| BTCUSD | 29 · +2.4% · PF 1.50 · win 76% · DD 4.6% · 3.1/1.2 (7/2) | 15 · -0.2% · PF 0.94 · win 47% · DD 2.9% | 47 · +1.9% · PF 1.21 · win 72% · DD 4.6% · 3.1/1.2 (7/2) | 23 · -0.0% · PF 1.00 · win 57% · DD 4.1% | PASS |
| ETHUSD | 19 · +0.6% · PF 1.22 · win 58% · DD 2.2% · 1.8/1.3 (4/3) | 12 · +1.2% · PF 1.78 · win 67% · DD 2.0% | 36 · -0.4% · PF 0.93 · win 58% · DD 3.1% · 2.1/1.4 (6/3) | 20 · +1.1% · PF 1.37 · win 65% · DD 2.6% | FAIL: 3y 19 trades; 3y not above control; 5y not positive; 5y PF 0.93; 5y not above control |

Breadth: 14/17 symbols positive over 5y.

## Advancing to the Model 4 real-tick test

C1 ETHUSD, S2 US500, S2 US30, S2 USTEC, S2 AMD, S2 AVGO, S2 JPM, S2 NVDA, S2 BTCUSD

## Model 4 real-tick confirmation (all periods)

| Edge | Symbol | 6m | 1y | 3y | 5y | Control 3y | Control 5y |
|---|---|---|---|---|---|---|---|
| S2 | AMD | 4 · +1.6% · PF 370.65 · win 100% · DD 0.7% · 4.0/0.0 (4/0) | 12 · +1.9% · PF 2.19 · win 83% · DD 1.9% · 3.3/1.0 (6/1) | 26 · +3.3% · PF 1.82 · win 73% · DD 2.1% · 3.8/1.4 (6/2) | 41 · +4.9% · PF 1.82 · win 73% · DD 2.1% · 3.3/1.2 (6/2) | 18 · -2.3% · PF 0.62 · win 28% · DD 3.5% | 27 · -3.5% · PF 0.58 · win 30% · DD 5.1% |
| S2 | AVGO | 3 · -0.9% · PF 0.00 · win 0% · DD 1.9% · 0.0/3.0 (0/3) | 10 · -0.5% · PF 0.70 · win 40% · DD 2.1% · 2.0/2.0 (3/4) | 32 · +2.7% · PF 1.49 · win 62% · DD 3.8% · 3.3/1.7 (11/4) | 47 · +3.4% · PF 1.42 · win 66% · DD 3.7% · 3.4/1.6 (11/4) | 22 · -0.2% · PF 0.97 · win 32% · DD 3.6% | 33 · -0.3% · PF 0.96 · win 42% · DD 3.6% |
| S2 | BTCUSD | 0 · +0.0% · PF 0.00 · win 0% · DD 0.0% · 0.0/0.0 (0/0) | 3 · +0.1% · PF 2.10 · win 67% · DD 1.1% · 2.0/1.0 (2/1) | 29 · +2.4% · PF 1.50 · win 76% · DD 4.6% · 3.1/1.2 (7/2) | 47 · +1.9% · PF 1.21 · win 72% · DD 4.6% · 3.1/1.2 (7/2) | 15 · -0.2% · PF 0.94 · win 47% · DD 2.9% | 23 · -0.0% · PF 1.00 · win 57% · DD 4.1% |
| C1 | ETHUSD | 13 · +4.3% · PF 4.67 · win 38% · DD 1.5% · 1.7/2.7 (2/4) | 27 · +1.0% · PF 1.22 · win 30% · DD 4.1% · 1.6/3.8 (2/9) | 67 · +8.4% · PF 1.58 · win 30% · DD 9.7% · 1.4/3.4 (3/9) | 112 · +3.8% · PF 1.15 · win 29% · DD 9.7% · 1.3/3.3 (3/9) | 2 · -1.6% · PF 0.50 · win 50% · DD 16.9% | 4 · -2.4% · PF 0.28 · win 25% · DD 9.0% |
| S2 | JPM | 2 · +0.2% · PF 19.61 · win 50% · DD 0.4% · 1.0/1.0 (1/1) | 7 · +1.1% · PF 1.92 · win 57% · DD 1.3% · 2.0/1.0 (2/1) | 23 · +1.9% · PF 1.40 · win 61% · DD 3.1% · 2.3/1.5 (5/3) | 40 · +3.8% · PF 1.46 · win 62% · DD 3.0% · 2.5/1.5 (5/3) | 21 · -3.4% · PF 0.47 · win 38% · DD 4.1% | 31 · -3.2% · PF 0.62 · win 48% · DD 4.3% |
| S2 | NVDA | 6 · +1.4% · PF 8.52 · win 83% · DD 0.6% · 2.5/1.0 (4/1) | 12 · +2.0% · PF 4.17 · win 75% · DD 1.1% · 3.0/1.0 (4/1) | 34 · +3.4% · PF 1.71 · win 68% · DD 2.0% · 2.6/1.2 (5/2) | 49 · +3.8% · PF 1.49 · win 71% · DD 2.4% · 2.7/1.2 (6/2) | 21 · -0.3% · PF 0.93 · win 57% · DD 2.3% | 30 · -1.5% · PF 0.74 · win 53% · DD 3.0% |
| S2 | US30 | 6 · +1.8% · PF 33.20 · win 83% · DD 1.0% · 5.0/1.0 (5/1) | 16 · +4.2% · PF 14.80 · win 81% · DD 1.0% · 4.3/1.0 (7/1) | 42 · +1.2% · PF 1.15 · win 67% · DD 3.9% · 3.1/1.6 (7/3) | 63 · +1.7% · PF 1.16 · win 65% · DD 4.4% · 2.9/1.5 (7/3) | 21 · -1.6% · PF 0.62 · win 43% · DD 2.9% | 32 · -2.9% · PF 0.55 · win 44% · DD 4.0% |
| S2 | US500 | 3 · +0.1% · PF 2.00 · win 33% · DD 1.2% · 1.0/2.0 (1/2) | 12 · +2.2% · PF 20.93 · win 83% · DD 1.2% · 10.0/2.0 (10/2) | 37 · +6.7% · PF 3.45 · win 84% · DD 1.6% · 6.2/1.2 (13/2) | 55 · +7.5% · PF 2.60 · win 73% · DD 1.7% · 3.3/1.2 (13/2) | 22 · -2.2% · PF 0.53 · win 41% · DD 2.7% | 31 · -2.2% · PF 0.62 · win 42% · DD 3.4% |
| S2 | USTEC | 5 · +1.1% · PF 8.09 · win 60% · DD 1.3% · 3.0/2.0 (3/2) | 13 · +1.8% · PF 3.46 · win 62% · DD 1.5% · 4.0/2.5 (5/3) | 42 · +5.4% · PF 2.28 · win 71% · DD 2.3% · 4.3/1.7 (9/3) | 61 · +9.3% · PF 2.88 · win 72% · DD 2.4% · 4.0/1.4 (9/3) | 23 · -1.0% · PF 0.79 · win 52% · DD 2.4% | 32 · -1.3% · PF 0.80 · win 50% · DD 3.3% |
