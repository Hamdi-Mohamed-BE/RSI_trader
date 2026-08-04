# BM Trading $100K portfolio — final safer configuration

Use only these four portfolio files together. Ninja Turtle and The Fisherman are excluded because both lost money in the 2025–2026 validation segment.

| EA | Chart | Final setting | Portfolio file |
|---|---|---:|---|
| Range Breakout | USDJPY M5 | $245 fixed money risk | `PORTFOLIO 100K FINAL - Range Breakout - USDJPY M5 - 245 USD risk.set` |
| Go Long | US30 D1 | 0.50 fixed lot | `PORTFOLIO 100K FINAL - Go Long - US30 D1 - 0.50 lot.set` |
| Turnaround Tuesday | UT100 D1 | 0.24 fixed lot | `PORTFOLIO 100K FINAL - Turnaround Tuesday - UT100 D1 - 0.24 lot.set` |
| ATR Candle Breakout | XAUUSD H1 | $146 fixed money risk | `PORTFOLIO 100K FINAL - ATR Candle Breakout - XAUUSD H1 - 146 USD risk.set` |

Each `.set` file is saved beside its matching EA. A second copy of all four files and the evidence is in `_Optimization Evidence\Portfolio 100K FINAL`.

## Verified result

- Starting balance: **$100,000**
- Final-setting validation: **2025-01-01 through 2026-07-31** (19 completed months)
- MT5 model: **Every Tick, generated ticks (Model 0)**
- Total net profit: **$17,844.91**
- Arithmetic average: **$939.21 per month** (**0.939%** of the initial balance)
- 12-month average projection: **$11,270.47**; this is an arithmetic projection, not a guarantee
- Profitable months: **13 of 19**
- Worst month: **-$1,691.76**
- Best month: **+$4,352.34**
- Maximum merged monthly closed-balance drawdown: **$2,948.67 (2.95%)**
- Stressed drawdown after a 1.25× safety multiplier: **$3,685.84 (3.69%)**
- Global closed-balance drawdown across the full validation period: **$4,318.10 (4.32%)**; the requested limit was applied separately inside each calendar month

The underlying unscaled signal sets were also synchronized over 2023-01-01 through 2026-07-31 (43 completed months). The first 24 months were used for calibration and the later 19 months for validation. The figures above are from separate fresh tests of the exact final scaled `.set` files on the 19-month validation window.

## Risk per trade

- Range Breakout requests **$245** of stop-based money risk. Its largest historical validation deal loss was **$292.94**, showing that execution can exceed the requested amount.
- ATR Candle Breakout requests **$146** of stop-based money risk. Its largest historical validation deal loss was **$146.28**.
- Go Long uses **0.50 fixed lot and has its stop loss disabled** in this strategy. Its largest historical validation deal loss was **$1,108.85**. Risk is therefore not capped at a fixed dollar amount.
- Turnaround Tuesday uses **0.24 fixed lot and has its stop loss disabled**. Its largest historical validation deal loss was **$166.98**. Risk is likewise not capped.

The 3.69% stressed figure is based on a merged closed-deal balance curve. It is not a measurement of simultaneous floating equity, and gaps, slippage, spreads, commissions, broker symbol specifications, or correlated open trades can produce a larger live drawdown. No backtest can guarantee a $939 monthly profit or a 4% live drawdown ceiling.

## Loading the portfolio in MT5

1. Use a **hedging** MT5 account and start on demo first.
2. Open the four charts and timeframes in the table. Broker symbol names may have suffixes; choose the equivalent instrument offered by your broker.
3. Attach the matching EA to each chart, open Inputs, select **Load**, and choose the `PORTFOLIO 100K FINAL` file beside that EA.
4. Confirm Algo Trading is enabled. The four files contain unique magic numbers.
5. Do not also attach Ninja Turtle, The Fisherman, or a second copy of one of these four EAs on the same account.

Review `FINAL 100K monthly results.csv`, `FINAL 100K EA results.csv`, the JSON analysis, and the four MT5 HTML reports in the evidence folder before using the setup.
