# Strict +20% MT5 setup

The automatic setup now launches seven EAs whose independent one-year tests returned at least +20%, including the user-selected fixed-1% LTA profile.

| Included EA | Symbol / chart | One-year return | Equity max DD | Profit factor |
|---|---|---:|---:|---:|
| ATR Candle Breakout | XAUUSD H1 | +109.34% | 15.45% | 1.43 |
| Go Long | US30 D1 | +31.71% | 28.61% | 1.13 |
| AAA Final EMA3 | XAUUSD H4 | +58.63% | 7.80% | 2.79 |
| AAA Final Asia Breakout | XAUUSD H1 | +29.00% | 30.86% | 1.15 |
| AAA Final Weekend Direction | XAUUSD M15 | +88.32% | 20.84% | 1.64 |
| AAA Final XAU Weakness | XAUUSD M15 | +24.41% | 44.84% | 1.03 |
| LTA Volume Profile | XAUUSD M15 | +92.15% | 14.82% | 1.41 |

Removed from automatic launch for returning less than +20%: AMD, US100 Weakness, News Pulse, DmC, XAU Grid, XAU/US100 Research, Ninja Turtle, Range Breakout, The Fisherman, and Turnaround Tuesday. DmC on US100 and US30 also failed the threshold.

The BAT deletes stale lower-performing EX5 and SET files only from its own managed MT5 folders when it installs the new profile. Source projects and backtest reports remain available as recovery and audit evidence.

The installer now accepts any positive account balance. By default, adaptive EAs target 1% of the balance detected at installation. Fixed-money inputs, lot sizes, and the Go Long hard stop are regenerated from the live balance and broker contract data. LTA is deliberately pinned to 1.00% equity risk per trade even if `-AdaptiveRiskPercent` is changed. For example, a $10,000 balance targets approximately $100 at a 1% planned stop; a $900 balance targets approximately $9. Broker minimum lots and stop distances can force a higher real minimum, which the preflight prints before installation.

The BAT automatically installs the selected strategy configuration. “Auto-selected” does not mean it re-optimizes against the latest history every time it starts; doing that would encourage overfitting. An advanced user can change the adaptive risk by passing `-AdaptiveRiskPercent`, from 0.1% through 5%.

Important: Weekend Direction required its provisional mode to be enabled for the +88.32% test. XAU Weakness previously carried a failed-validation gate and produced 44.84% equity drawdown. Both are now enabled only because the requested rule was strictly based on return being at least +20%.

Run `INSTALL AND RUN ON ACTIVE MT5.bat` to install the seven-chart profile. All three launcher names are synchronized through the same portfolio installer. The installer still performs account, symbol, EA, settings, and managed-path safety validation before changing MT5.
