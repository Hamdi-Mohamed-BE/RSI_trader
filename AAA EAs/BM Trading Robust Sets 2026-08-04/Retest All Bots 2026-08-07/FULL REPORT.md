# All-bot Exness retest — strict +20% selection

## Method

- Broker: Exness Technologies Ltd (`Exness-MT5Trial16`)
- Window: 2025-08-07 through 2026-08-06
- Initial balance: USD 10,000 per independent EA test
- Risk: 1% planned risk per trade; fixed-lot index strategies use a hard stop calibrated near USD 100
- Model: MT5 Every Tick generated from Exness M1 history, with random execution delay
- Selection: each bot's best saved configuration; DmC uses the best of XAUUSD, USTEC, and US30
- Gate: keep only independently tested bots with return of at least +20.00%

## Best result per bot

| Status | EA | Symbol / chart | Final | Net | Return | Equity DD | PF | Win rate | Trades | History |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KEEP | LTA Volume Profile | XAUUSD M15 | $18,204.75 | $8,204.75 | +82.05% | 14.39% | 1.37 | 32.11% | 246 | 99% |
| KEEP | ATR Candle Breakout | XAUUSD H1 | $13,020.35 | $3,020.35 | +30.20% | 8.77% | 1.40 | 26.50% | 117 | 99% |
| KEEP | AAA Final Asia Breakout | XAUUSD H1 | $12,140.45 | $2,140.45 | +21.40% | 12.66% | 1.27 | 37.29% | 118 | 99% |
| KEEP | AAA Final DmC (XAUUSD) | XAUUSD H1 | $12,089.81 | $2,089.81 | +20.90% | 9.82% | 1.15 | 41.20% | 233 | 99% |
| REMOVE | Go Long | US30 D1 | $11,724.47 | $1,724.47 | +17.24% | 8.29% | 1.20 | 50.64% | 312 | 100% |
| REMOVE | AAA Final EMA3 | XAUUSD H4 | $11,575.60 | $1,575.60 | +15.76% | 3.93% | 2.14 | 61.54% | 39 | 99% |
| REMOVE | AAA Final XAU Weakness | XAUUSD M15 | $10,919.35 | $919.35 | +9.19% | 17.89% | 1.05 | 35.74% | 277 | 99% |
| REMOVE | Ninja Turtle Scalper | EURUSD M5 | $10,847.66 | $847.66 | +8.48% | 8.54% | 1.13 | 79.89% | 353 | 100% |
| REMOVE | Nasdaq Overnight Negative Day | USTEC M1 | $10,785.28 | $785.28 | +7.85% | 2.39% | 1.85 | 57.75% | 71 | 100% |
| REMOVE | Turnaround Tuesday | USTEC D1 | $10,328.73 | $328.73 | +3.29% | 6.11% | 1.20 | 36.67% | 30 | 100% |
| REMOVE | AAA Final US100 Weakness | USTEC M15 | $10,326.78 | $326.78 | +3.27% | 6.04% | 1.15 | 42.86% | 70 | 100% |
| REMOVE | AAA Final Weekend Direction | XAUUSD M15 | $10,000.00 | $0.00 | +0.00% | 0.00% | 0.00 | 0.00% | 0 | 99% |
| REMOVE | AAA Final XAU US100 Research | XAUUSD M15 | $10,000.00 | $0.00 | +0.00% | 0.00% | 0.00 | 0.00% | 0 | 0% |
| REMOVE | The Fisherman | EURUSD H1 | $9,988.06 | $-11.94 | -0.12% | 1.00% | 0.68 | 50.00% | 6 | 100% |
| REMOVE | AAA Final US100 Weakness Exact | USTEC M15 | $9,928.15 | $-71.85 | -0.72% | 10.21% | 0.95 | 49.09% | 55 | 100% |
| REMOVE | AAA Final AMD | XAUUSD M15 | $9,616.17 | $-383.83 | -3.84% | 15.96% | 0.96 | 36.54% | 156 | 99% |
| REMOVE | AAA Final XAU Grid | XAUUSD M15 | $9,585.70 | $-414.30 | -4.14% | 7.01% | 0.92 | 30.74% | 257 | 99% |
| REMOVE | AAA Final News Pulse | XAUUSD M1 | $9,495.12 | $-504.88 | -5.05% | 6.16% | 0.00 | 0.00% | 11 | 99% |
| REMOVE | Range Breakout | USDJPY M5 | $7,039.22 | $-2,960.78 | -29.61% | 49.13% | 0.83 | 30.08% | 256 | 100% |

## All DmC symbol candidates

| Symbol / chart | Net | Return | Equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD H1 | $2,089.81 | +20.90% | 9.82% | 1.15 | 41.20% | 233 |
| USTEC H1 | $-4,084.40 | -40.84% | 45.11% | 0.73 | 31.41% | 277 |
| US30 H1 | $-353.67 | -3.54% | 29.02% | 0.98 | 37.99% | 279 |

## Included in synchronized BAT

- LTA Volume Profile — XAUUSD M15: +82.05% return, 14.39% equity DD, 246 trades
- ATR Candle Breakout — XAUUSD H1: +30.20% return, 8.77% equity DD, 117 trades
- AAA Final Asia Breakout — XAUUSD H1: +21.40% return, 12.66% equity DD, 118 trades
- AAA Final DmC (XAUUSD) — XAUUSD H1: +20.90% return, 9.82% equity DD, 233 trades

## Interpretation

Passing +20% is a historical filter, not a profit guarantee. These are independent EA tests, not a shared-account portfolio simulation; simultaneous open positions can stack risk and create a materially larger account-level drawdown.

Every native MT5 HTML report and graph is stored in `MT5 Reports`; every tested SET file is stored in `Settings`.
