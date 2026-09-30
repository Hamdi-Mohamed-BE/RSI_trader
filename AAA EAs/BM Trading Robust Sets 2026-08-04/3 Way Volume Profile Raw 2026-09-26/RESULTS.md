# 3 Way Volume Profile — raw results (M15, last year)

Window 2025.09.26 → 2026.09.26 (end exclusive). Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk, Model 4 (real ticks from 2026-01; bars-generated before), 150 ms delay. Raw rules, no tuning.
Consistency = profitable months / months in window. Sharpe = annualised daily Sharpe of closed P/L. Streaks = average (max). Balance DD and equity DD from the native MT5 report.

Survivor rule (fixed before testing): return > 0, PF ≥ 1.15, ≥ 30 trades, consistency ≥ 50%, equity DD ≤ 20%.

## Way 1 - POC bounce

| Asset | Trades | /month | /day | Return | PF | Win | Consistency | Avg win/loss streak (max) | Sharpe | Max balance DD | Max equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| USTEC | 46 | 3.8 | 0.18 | +6.8% | 1.22 | 39% | 46% (6/13) | 1.2/2.0 (2/6) | 0.71 | 6.2% | 7.5% | near miss: consistency 46% |
| XAUUSD | 39 | 3.3 | 0.15 | -12.3% | 0.59 | 23% | 23% (3/13) | 1.8/5.0 (3/12) | -1.38 | 15.9% | 16.7% | fail: return ≤ 0; PF 0.59; consistency 23% |
| XAGUSD | 29 | 2.4 | 0.11 | +5.3% | 1.26 | 41% | 46% (6/13) | 1.5/2.4 (2/5) | 0.63 | 5.5% | 5.5% | near miss: 29 trades; consistency 46% |
| BTCUSD | 63 | 5.3 | 0.24 | -0.6% | 0.99 | 35% | 46% (6/13) | 1.4/2.6 (3/6) | 0.00 | 10.6% | 11.3% | fail: return ≤ 0; PF 0.99; consistency 46% |
| ETHUSD | 52 | 4.3 | 0.20 | +0.9% | 1.03 | 37% | 46% (6/13) | 1.4/2.2 (3/10) | 0.14 | 10.6% | 11.3% | fail: PF 1.03; consistency 46% |
| EURUSD | 35 | 2.9 | 0.13 | -0.1% | 1.00 | 31% | 54% (7/13) | 1.8/3.4 (4/9) | 0.04 | 10.9% | 11.1% | fail: return ≤ 0; PF 1.00 |
| USDJPY | 32 | 2.7 | 0.12 | -12.2% | 0.52 | 22% | 31% (4/13) | 1.4/4.2 (3/6) | -1.73 | 12.2% | 12.6% | fail: return ≤ 0; PF 0.52; consistency 31% |
| GBPJPY | 34 | 2.8 | 0.13 | +2.2% | 1.09 | 38% | 38% (5/13) | 1.4/2.6 (5/6) | 0.29 | 6.7% | 7.9% | near miss: PF 1.09; consistency 38% |

## Way 2 - VA reversal

| Asset | Trades | /month | /day | Return | PF | Win | Consistency | Avg win/loss streak (max) | Sharpe | Max balance DD | Max equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| USTEC | 151 | 12.6 | 0.58 | -11.7% | 0.89 | 32% | 38% (5/13) | 1.5/3.1 (4/11) | -0.64 | 22.9% | 23.8% | fail: return ≤ 0; PF 0.89; consistency 38%; equity DD 23.8% |
| XAUUSD | 160 | 13.3 | 0.61 | +9.1% | 1.08 | 36% | 46% (6/13) | 1.6/2.9 (4/9) | 0.51 | 25.7% | 27.3% | near miss: PF 1.08; consistency 46%; equity DD 27.3% |
| XAGUSD | 122 | 10.2 | 0.47 | -22.6% | 0.79 | 27% | 23% (3/13) | 1.2/3.1 (3/10) | -1.01 | 26.7% | 28.0% | fail: return ≤ 0; PF 0.79; consistency 23%; equity DD 28.0% |
| BTCUSD | 208 | 17.3 | 0.80 | +50.5% | 1.29 | 41% | 62% (8/13) | 1.6/2.4 (5/10) | 1.87 | 10.3% | 11.2% | SURVIVES |
| ETHUSD | 226 | 18.8 | 0.87 | +4.3% | 1.03 | 36% | 38% (5/13) | 1.6/2.8 (4/13) | 0.30 | 21.9% | 22.9% | fail: PF 1.03; consistency 38%; equity DD 22.9% |
| EURUSD | 158 | 13.2 | 0.61 | +10.7% | 1.10 | 37% | 62% (8/13) | 1.5/2.6 (6/12) | 0.62 | 17.3% | 18.4% | near miss: PF 1.10 |
| USDJPY | 138 | 11.5 | 0.53 | +12.8% | 1.11 | 38% | 46% (6/13) | 1.6/2.6 (5/13) | 0.72 | 19.9% | 20.2% | near miss: PF 1.11; consistency 46%; equity DD 20.2% |
| GBPJPY | 174 | 14.5 | 0.67 | -33.4% | 0.70 | 28% | 31% (4/13) | 1.5/3.7 (4/11) | -2.07 | 35.0% | 35.8% | fail: return ≤ 0; PF 0.70; consistency 31%; equity DD 35.8% |

## Way 3 - VA breakout

| Asset | Trades | /month | /day | Return | PF | Win | Consistency | Avg win/loss streak (max) | Sharpe | Max balance DD | Max equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| USTEC | 110 | 9.2 | 0.42 | -17.1% | 0.78 | 29% | 38% (5/13) | 1.3/3.1 (3/14) | -1.20 | 20.7% | 20.9% | fail: return ≤ 0; PF 0.78; consistency 38%; equity DD 20.9% |
| XAUUSD | 78 | 6.5 | 0.30 | +19.8% | 1.30 | 41% | 54% (7/13) | 1.7/2.6 (7/7) | 1.20 | 12.9% | 13.4% | SURVIVES |
| XAGUSD | 92 | 7.7 | 0.35 | -2.0% | 0.98 | 33% | 46% (6/13) | 1.5/3.0 (3/10) | 0.00 | 19.0% | 20.6% | fail: return ≤ 0; PF 0.98; consistency 46%; equity DD 20.6% |
| BTCUSD | 144 | 12.0 | 0.55 | +22.2% | 1.20 | 39% | 62% (8/13) | 1.7/2.7 (4/8) | 1.16 | 12.4% | 13.5% | SURVIVES |
| ETHUSD | 132 | 11.0 | 0.51 | +1.3% | 1.01 | 35% | 46% (6/13) | 1.6/3.0 (4/10) | 0.16 | 22.2% | 22.9% | fail: PF 1.01; consistency 46%; equity DD 22.9% |
| EURUSD | 104 | 8.7 | 0.40 | -15.2% | 0.81 | 31% | 38% (5/13) | 1.3/2.9 (2/13) | -0.97 | 24.0% | 24.5% | fail: return ≤ 0; PF 0.81; consistency 38%; equity DD 24.5% |
| USDJPY | 84 | 7.0 | 0.32 | +17.6% | 1.28 | 39% | 46% (6/13) | 1.4/2.3 (4/5) | 1.12 | 11.0% | 12.1% | near miss: consistency 46% |
| GBPJPY | 60 | 5.0 | 0.23 | +4.9% | 1.12 | 38% | 54% (7/13) | 1.8/3.1 (3/5) | 0.47 | 5.4% | 6.8% | near miss: PF 1.12 |

## 3 Way combined

| Asset | Trades | /month | /day | Return | PF | Win | Consistency | Avg win/loss streak (max) | Sharpe | Max balance DD | Max equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| USTEC | 213 | 17.8 | 0.82 | -6.3% | 0.96 | 34% | 46% (6/13) | 1.7/3.4 (5/11) | -0.20 | 15.6% | 16.7% | fail: return ≤ 0; PF 0.96; consistency 46% |
| XAUUSD | 217 | 18.1 | 0.83 | +27.9% | 1.16 | 37% | 46% (6/13) | 1.7/2.8 (6/11) | 1.06 | 22.4% | 23.6% | near miss: consistency 46%; equity DD 23.6% |
| XAGUSD | 147 | 12.3 | 0.56 | +0.5% | 1.00 | 33% | 54% (7/13) | 1.5/2.9 (3/9) | 0.15 | 18.3% | 19.9% | fail: PF 1.00 |
| BTCUSD | 287 | 23.9 | 1.10 | +34.3% | 1.14 | 38% | 69% (9/13) | 1.7/2.9 (6/14) | 1.21 | 18.2% | 19.1% | near miss: PF 1.14 |
| ETHUSD | 276 | 23.0 | 1.06 | +17.7% | 1.09 | 37% | 62% (8/13) | 1.7/2.9 (6/16) | 0.78 | 19.4% | 20.0% | near miss: PF 1.09; equity DD 20.0% |
| EURUSD | 172 | 14.3 | 0.66 | -0.5% | 1.00 | 35% | 69% (9/13) | 1.5/2.7 (3/14) | 0.08 | 20.6% | 22.1% | fail: return ≤ 0; PF 1.00; equity DD 22.1% |
| USDJPY | 164 | 13.7 | 0.63 | +39.7% | 1.29 | 41% | 62% (8/13) | 1.8/2.7 (7/9) | 1.74 | 15.1% | 16.6% | SURVIVES |
| GBPJPY | 130 | 10.8 | 0.50 | -6.2% | 0.93 | 34% | 38% (5/13) | 1.8/3.6 (6/7) | -0.29 | 13.1% | 14.0% | fail: return ≤ 0; PF 0.93; consistency 38% |

## Survivors for the optimization stage

BTCUSD REV, XAUUSD BRK, BTCUSD BRK, USDJPY ALL

Near misses: USTEC POC (consistency 46%), XAGUSD POC (29 trades; consistency 46%), GBPJPY POC (PF 1.09; consistency 38%), XAUUSD REV (PF 1.08; consistency 46%; equity DD 27.3%), EURUSD REV (PF 1.10), USDJPY REV (PF 1.11; consistency 46%; equity DD 20.2%), USDJPY BRK (consistency 46%), GBPJPY BRK (PF 1.12), XAUUSD ALL (consistency 46%; equity DD 23.6%), BTCUSD ALL (PF 1.14), ETHUSD ALL (PF 1.09; equity DD 20.0%)

Balance graph: `balance_curves.png` (closed-trade balance per asset, all four ways).
