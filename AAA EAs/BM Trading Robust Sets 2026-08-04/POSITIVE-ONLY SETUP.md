# Strict +20% MT5 setup

The automatic setup now launches only the six EAs whose independent one-year test returned at least +20%.

| Included EA | Symbol / chart | One-year return | Equity max DD | Profit factor |
|---|---|---:|---:|---:|
| ATR Candle Breakout | XAUUSD H1 | +109.34% | 15.45% | 1.43 |
| Go Long | US30 D1 | +31.71% | 28.61% | 1.13 |
| AAA Final EMA3 | XAUUSD H4 | +58.63% | 7.80% | 2.79 |
| AAA Final Asia Breakout | XAUUSD H1 | +29.00% | 30.86% | 1.15 |
| AAA Final Weekend Direction | XAUUSD M15 | +88.32% | 20.84% | 1.64 |
| AAA Final XAU Weakness | XAUUSD M15 | +24.41% | 44.84% | 1.03 |

Removed from automatic launch for returning less than +20%: AMD, US100 Weakness, News Pulse, DmC, XAU Grid, XAU/US100 Research, Ninja Turtle, Range Breakout, The Fisherman, and Turnaround Tuesday. DmC on US100 and US30 also failed the threshold.

The BAT deletes stale lower-performing EX5 and SET files only from its own managed MT5 folders when it installs the new profile. Source projects and backtest reports remain available as recovery and audit evidence.

The four native AAA settings files are automatically loaded with 1% live risk. ATR and Go Long continue to use the account-specific risk handling already built into the installer. “Auto-selected” means the BAT installs the saved selected configuration automatically; it does not re-optimize against the latest history every time it starts.

Important: Weekend Direction required its provisional mode to be enabled for the +88.32% test. XAU Weakness previously carried a failed-validation gate and produced 44.84% equity drawdown. Both are now enabled only because the requested rule was strictly based on return being at least +20%.

Run `INSTALL AND RUN ON ACTIVE MT5.bat` to install the six-chart profile. The installer still performs account, symbol, EA, settings, and managed-path safety validation before changing MT5.
