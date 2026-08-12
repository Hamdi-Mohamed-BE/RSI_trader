# Current active BAT — complete five-year Exness backtest

## Combined result

| Initial | Final | Net / return | Realized balance DD | PF | Win rate | Wins / losses | Trades |
|---:|---:|---:|---:|---:|---:|---:|---:|
| $10,000.00 | $29,552.64* | $19,552.64* / +195.53%* | $17,424.02 / 154.57% | 1.06 | 36.39% | 2663 / 4654 | 7317 |

**Portfolio verdict: FAIL.** The merged curve fell to **$-6,151.72**. A real USD 10,000 account would have reached ruin/margin stop-out, so the starred final balance and return are only a later arithmetic recovery and are not achievable live.

The combined line chronologically merges all realized deal cash flows onto one USD 10,000 balance. It is a useful capital-normalized overlay, but it is not a native multi-EA MT5 run: MT5 cannot attach these proprietary EX5 files simultaneously in one Strategy Tester pass. Floating equity DD, shared-equity position resizing, simultaneous margin use, and cross-EA execution contention are therefore not captured. The reported combined DD is realized-balance DD and can understate live floating-equity drawdown.

## One-by-one results

| Status | EA | Symbol / TF | Final | Net / return | Equity DD | PF | Win rate | Trades | Quality |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| PROFIT | ATR Candle Breakout | XAUUSD H1 | $17,203.97 | $7,203.97 / +72.04% | $4,311.94 / 23.66% | 1.14 | 23.43% | 670 | 98% |
| PROFIT | AAA Final News Pulse — long only | XAUUSD M1 | $16,251.23 | $6,251.23 / +62.51% | $225.72 / 1.46% | 41.00 | 84.21% | 19 | 98% |
| PROFIT | ORB Volume Profile | XAUUSD M5 | $15,706.82 | $5,706.82 / +57.07% | $930.21 / 6.31% | 1.41 | 41.53% | 301 | 98% |
| PROFIT | AAA Final EMA3 | XAUUSD H4 | $13,209.85 | $3,209.85 / +32.10% | $1,013.50 / 8.70% | 1.36 | 49.73% | 187 | 98% |
| PROFIT | LTA Volume Profile | XAUUSD M15 | $12,619.36 | $2,619.36 / +26.19% | $4,381.10 / 42.84% | 1.04 | 26.64% | 1160 | 98% |
| PROFIT | AAA Final Asia Breakout | XAUUSD H1 | $10,791.11 | $791.11 / +7.91% | $3,675.70 / 35.03% | 1.02 | 34.39% | 660 | 98% |
| PROFIT | Nasdaq Overnight | USTEC M1 | $10,783.80 | $783.80 / +7.84% | $500.43 / 4.82% | 1.28 | 56.08% | 189 | 98% |
| PROFIT | Go Long | US30 D1 | $10,073.83 | $73.83 / +0.74% | $3,469.72 / 34.38% | 1.00 | 46.37% | 1555 | 98% |
| LOSS | Turnaround Tuesday | USTEC D1 | $9,564.15 | -$435.85 / -4.36% | $1,561.03 / 15.59% | 0.93 | 30.41% | 148 | 98% |
| LOSS | AAA Final DmC | XAUUSD H1 | $8,348.43 | -$1,651.57 / -16.52% | $3,776.85 / 37.08% | 0.93 | 37.41% | 572 | 98% |
| LOSS | AAA Final US100 Weakness | USTEC M15 | $7,889.60 | -$2,110.40 / -21.10% | $2,724.19 / 26.83% | 0.81 | 34.86% | 370 | 98% |
| LOSS | AAA Final XAU Weakness | XAUUSD M15 | $7,110.49 | -$2,889.51 / -28.90% | $6,229.48 / 58.49% | 0.96 | 35.06% | 1486 | 98% |

## Five-year annualized view

Arithmetic-overlay CAGR: **+24.20% per year**. This is not tradable because the combined curve crossed below zero.

| EA | Symbol / TF | 5Y return | CAGR | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| ATR Candle Breakout | XAUUSD H1 | +72.04% | +11.46% | 23.66% | 1.14 | 23.43% | 670 |
| AAA Final News Pulse — long only | XAUUSD M1 | +62.51% | +10.20% | 1.46% | 41.00 | 84.21% | 19 |
| ORB Volume Profile | XAUUSD M5 | +57.07% | +9.45% | 6.31% | 1.41 | 41.53% | 301 |
| AAA Final EMA3 | XAUUSD H4 | +32.10% | +5.73% | 8.70% | 1.36 | 49.73% | 187 |
| LTA Volume Profile | XAUUSD M15 | +26.19% | +4.76% | 42.84% | 1.04 | 26.64% | 1160 |
| AAA Final Asia Breakout | XAUUSD H1 | +7.91% | +1.53% | 35.03% | 1.02 | 34.39% | 660 |
| Nasdaq Overnight | USTEC M1 | +7.84% | +1.52% | 4.82% | 1.28 | 56.08% | 189 |
| Go Long | US30 D1 | +0.74% | +0.15% | 34.38% | 1.00 | 46.37% | 1555 |
| Turnaround Tuesday | USTEC D1 | -4.36% | -0.89% | 15.59% | 0.93 | 30.41% | 148 |
| AAA Final DmC | XAUUSD H1 | -16.52% | -3.55% | 37.08% | 0.93 | 37.41% | 572 |
| AAA Final US100 Weakness | USTEC M15 | -21.10% | -4.63% | 26.83% | 0.81 | 34.86% | 370 |
| AAA Final XAU Weakness | XAUUSD M15 | -28.90% | -6.59% | 58.49% | 0.96 | 35.06% | 1486 |

## Test conditions

- Source of truth: current `_Auto Deploy/Install-BMTradingPortfolio.ps1` invoked by `INSTALL AND RUN ON ACTIVE MT5.bat`.
- Broker: Exness `Exness-MT5Trial16`; account currency USD.
- Period: 2021-08-11 through 2026-08-10, the latest complete five-year window.
- Initial balance: USD 10,000 per independent EA test; leverage 1:2000.
- Model: MT5 Every Tick generated from synchronized broker M1 history; reported history quality 98% for all 12 valid tests.
- Execution: random execution delay.
- Settings: exact current BAT source presets, including the current long-only robust News Pulse set.
- Planned risk: approximately 1% per EA trade. Because every EA has its own allowance, aggregate open risk can exceed 1% when bots hold positions simultaneously.

## Files

- `MT5 Reports`: native report and equity-chart artifacts for every test.
- `individual-results.csv`: all one-by-one statistics.
- `combined-realized-balance.csv`: chronological combined cash-flow curve.
- `portfolio-results.json`: machine-readable full result.
- `Charts/combined-realized-balance.png`: combined graph.
