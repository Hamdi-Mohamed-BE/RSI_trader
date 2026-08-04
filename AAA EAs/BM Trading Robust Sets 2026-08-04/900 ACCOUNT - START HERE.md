# BM Trading USD 900 launcher

Use **INSTALL AND RUN ON 900 USD MT5.bat** for a USD account with a balance between $800 and $1,200.

The launcher is separate from the original $100K launcher. It verifies the active account, checks the broker's symbol names and minimum index lot sizes, installs the small-account settings, and opens the **BM Trading 900 - AUTO** profile.

## Installed exposure

| EA | Chart | Small-account input |
|---|---|---:|
| Range Breakout | USDJPY M5 | $18 requested stop risk |
| ATR Candle Breakout | XAUUSD H1 | $18 requested stop risk |
| Go Long | US30 D1 | 0.01 fixed lot; no hard stop |
| Turnaround Tuesday | UT100/NAS100 D1 | 0.01 fixed lot; no hard stop |

The $18 risk equals 2% of $900 for the two EAs that use stop-based money sizing. It can be exceeded by gaps, slippage and minimum lot rounding. Go Long and Turnaround Tuesday cannot be described as 2%-risk trades because their strategy settings have no hard stop.

The historical 19-month replay of these approximate sizes averaged $58.55 per month, had a worst month of -$154.11, and produced a $260.95 maximum monthly closed-balance drawdown ($326.19 with the prior 1.25x stress factor). The global closed-balance drawdown was $462.40. These figures exclude simultaneous floating-equity drawdown and do not guarantee future results.

Do not use the original **INSTALL AND RUN ON ACTIVE MT5.bat** on this account. It remains locked to $100K accounts because its position sizes are approximately 100 times too large.
