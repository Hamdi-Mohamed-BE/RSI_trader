# Current active BAT — complete one-year Exness backtest

## Combined result

| Initial | Final | Net / return | Realized balance DD | PF | Win rate | Wins / losses | Trades |
|---:|---:|---:|---:|---:|---:|---:|---:|
| $10,000.00 | $39,561.18 | $29,561.18 / +295.61% | $2,534.44 / 25.34% | 1.34 | 41.31% | 656 / 932 | 1588 |

The combined line chronologically merges all realized deal cash flows onto one USD 10,000 balance. It is a useful capital-normalized overlay, but it is not a native multi-EA MT5 run: MT5 cannot attach these proprietary EX5 files simultaneously in one Strategy Tester pass. Floating equity DD, shared-equity position resizing, simultaneous margin use, and cross-EA execution contention are therefore not captured. The reported combined DD is realized-balance DD and can understate live floating-equity drawdown.

## One-by-one results

| Status | EA | Symbol / TF | Final | Net / return | Equity DD | PF | Win rate | Trades | Quality |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| PROFIT | LTA Volume Profile | XAUUSD M15 | $18,665.45 | $8,665.45 / +86.65% | $1,973.84 / 14.36% | 1.39 | 32.38% | 244 | 99% |
| PROFIT | AAA Final News Pulse — long only | XAUUSD M1 | $16,251.23 | $6,251.23 / +62.51% | $225.72 / 1.46% | 41.00 | 84.21% | 19 | 99% |
| PROFIT | ATR Candle Breakout | XAUUSD H1 | $13,038.80 | $3,038.80 / +30.39% | $1,158.24 / 8.72% | 1.39 | 26.05% | 119 | 99% |
| PROFIT | AAA Final DmC | XAUUSD H1 | $12,647.62 | $2,647.62 / +26.48% | $1,204.69 / 9.78% | 1.20 | 42.13% | 235 | 99% |
| PROFIT | AAA Final Asia Breakout | XAUUSD H1 | $12,010.03 | $2,010.03 / +20.10% | $1,675.39 / 12.67% | 1.25 | 36.67% | 120 | 99% |
| PROFIT | Go Long | US30 D1 | $11,696.36 | $1,696.36 / +16.96% | $895.74 / 8.24% | 1.20 | 50.64% | 312 | 100% |
| PROFIT | AAA Final EMA3 | XAUUSD H4 | $11,693.65 | $1,693.65 / +16.94% | $328.74 / 2.85% | 2.30 | 64.10% | 39 | 99% |
| PROFIT | AAA Final XAU Weakness | XAUUSD M15 | $11,148.94 | $1,148.94 / +11.49% | $2,228.02 / 17.70% | 1.06 | 35.84% | 279 | 99% |
| PROFIT | ORB Volume Profile | XAUUSD M5 | $10,969.76 | $969.76 / +9.70% | $644.08 / 6.29% | 1.67 | 42.86% | 49 | 99% |
| PROFIT | Nasdaq Overnight | USTEC M1 | $10,776.32 | $776.32 / +7.76% | $260.77 / 2.39% | 1.81 | 58.33% | 72 | 100% |
| PROFIT | AAA Final US100 Weakness | USTEC M15 | $10,334.29 | $334.29 / +3.34% | $657.92 / 6.03% | 1.16 | 42.86% | 70 | 100% |
| PROFIT | Turnaround Tuesday | USTEC D1 | $10,328.73 | $328.73 / +3.29% | $633.40 / 6.11% | 1.20 | 36.67% | 30 | 100% |

## Invalid active BAT entry

- **Ninja Turtle Scalper (EURUSD M5): START FAILURE.** OnInit failed: embedded Donchian Channel resource could not be loaded (MT5 error 4802).

## Test conditions

- Source of truth: current `_Auto Deploy/Install-BMTradingPortfolio.ps1` invoked by `INSTALL AND RUN ON ACTIVE MT5.bat`.
- Broker: Exness `Exness-MT5Trial16`; account currency USD.
- Period: 2025-08-11 through 2026-08-10, the latest complete one-year window.
- Initial balance: USD 10,000 per independent EA test; leverage 1:2000.
- Model: MT5 Every Tick generated from synchronized broker M1 history; reported quality 99–100% for valid tests.
- Execution: random execution delay.
- Settings: exact current BAT source presets, including the current long-only robust News Pulse set.
- Planned risk: approximately 1% per EA trade. Because every EA has its own allowance, aggregate open risk can exceed 1% when bots hold positions simultaneously.

## Files

- `MT5 Reports`: native report and equity-chart artifacts for every test.
- `individual-results.csv`: all one-by-one statistics.
- `combined-realized-balance.csv`: chronological combined cash-flow curve.
- `portfolio-results.json`: machine-readable full result.
- `Charts/combined-realized-balance.png`: combined graph.
