# Current BAT input verification

Checked on 9 Aug 2026 against `_Auto Deploy/Install-BMTradingPortfolio.ps1`.

Each current BAT settings file was parsed into input-name/value pairs and compared with the settings embedded in the corresponding native Exness test. Comments and MT5 optimization metadata were ignored; trading values were compared exactly.

| BAT EA | Native test settings | Result |
|---|---|---|
| LTA Volume Profile | RETEST 20 | Exact match |
| ORB Volume Profile | Validated XAUUSD baseline/control | Exact match |
| ATR Candle Breakout | RETEST 14 | Exact match |
| AAA Final Asia Breakout | RETEST 02 | Exact match |
| AAA Final DmC XAUUSD | RETEST 03 | Exact match |
| Go Long | RETEST 15 | Exact match |
| AAA Final EMA3 | RETEST 01 | Exact match |
| AAA Final XAU Weakness | RETEST 11 | Exact match |
| Ninja Turtle Scalper | RETEST 16 | Exact match |
| Nasdaq Overnight | RETEST 21 | Exact match |
| Turnaround Tuesday | RETEST 19 | Exact match |
| AAA Final US100 Weakness | RETEST 07 | Exact match |
| AAA Final News Pulse | RETEST 08 | Exact match |

The native reports cover 7 Aug 2025 through 6 Aug 2026 and were generated on 7 Aug 2026 using Exness Every Tick tests with random execution delay. A fresh 9 Aug launch was attempted, but the isolated Exness terminal could not synchronize or authorize during the weekend. No fabricated or partial 9 Aug output was used.
