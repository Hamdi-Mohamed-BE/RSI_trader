# Active BAT portfolio — one complete folder per EA

Source of truth: `../_Auto Deploy/Install-BMTradingPortfolio.ps1`, function `Get-PortfolioItems`.

The 13 numbered folders match the 13 EAs currently listed by `INSTALL AND RUN ON ACTIVE MT5.bat`.

Every numbered EA folder contains:

- `Compiled EA`: the `.ex5` referenced by the BAT portfolio.
- `Save File`: the selected `.set` referenced by the BAT in AUTO balance mode.
- `Chart`: the matching active `.chr` chart from `BM Trading ANY BALANCE - AUTO`.
- `Source Code`: the `.mq5` source plus any local `.mqh` dependencies when source exists.
- `Documentation`: supplied input documentation when the EA is binary-only.

| Folder | BAT EA | Chart |
|---|---|---|
| `01 LTA Volume Profile` | LTA Volume Profile | XAUUSD M15 |
| `02 ORB Volume Profile` | ORB Volume Profile | XAUUSD M5 |
| `03 ATR Candle Breakout` | ATR Candle Breakout | XAUUSD H1 |
| `04 AAA Final Asia Breakout` | AAA Final Asia Breakout | XAUUSD H1 |
| `05 AAA Final DmC` | AAA Final DmC | XAUUSD H1 |
| `06 Go Long` | Go Long | US30 D1 |
| `07 AAA Final EMA3` | AAA Final EMA3 | XAUUSD H4 |
| `08 AAA Final XAU Weakness` | AAA Final XAU Weakness | XAUUSD M15 |
| `09 Ninja Turtle Scalper` | Ninja Turtle Scalper | EURUSD M5 |
| `10 Nasdaq Overnight` | Nasdaq Overnight | USTEC/UT100 M1 |
| `11 Turnaround Tuesday` | Turnaround Tuesday | USTEC/UT100 D1 |
| `12 AAA Final US100 Weakness` | AAA Final US100 Weakness | USTEC/UT100 M15 |
| `13 AAA Final News Pulse` | AAA Final News Pulse — NFP/CPI/FOMC long-only 60s | XAUUSD M1 |

ATR Candle Breakout, Go Long, Ninja Turtle Scalper and Turnaround Tuesday were supplied only as compiled EX5 products. Their genuine MQ5 source is not present, so their `Source Code` folders contain an honest limitation notice instead of invented or decompiled code.
