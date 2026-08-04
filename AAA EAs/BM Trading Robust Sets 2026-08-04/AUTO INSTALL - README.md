# One-click MT5 installer

Choose the launcher that matches the account:

- **INSTALL AND RUN ON ACTIVE MT5.bat** now uses the USD 900 profile requested for the current account.
- **INSTALL AND RUN ON 900 USD MT5.bat** is an explicitly named copy of the same USD 800-1,200 launcher.
- **INSTALL AND RUN ON 100K MT5.bat** preserves access to the original USD 90,000-110,000 presets.

Open the target MT5 account first, then double-click the matching launcher.

The installer:

1. Detects the running MT5 installation. If none or more than one is running, it asks which installation to use.
2. Reads and displays the logged-in account number, server, balance and equity.
3. Resolves the broker's actual names for USDJPY, XAUUSD, US30 and NDX100/NAS100.
4. Requires the final confirmation `RUN <account number>` because the EAs can place real trades.
5. Closes that MT5 cleanly, copies the four `.ex5` files and final `.set` files, and creates an isolated profile named **BM Trading 100K - AUTO**.
6. Enables Algo Trading, restarts MT5 and loads four charts with the exact final settings already attached.

It does not delete other MT5 profiles and does not close open positions. If the auto profile already exists, the installer moves it to a timestamped backup before rebuilding it.

## Deployed charts

- Range Breakout: USDJPY M5, $245 fixed risk
- ATR Candle Breakout: XAUUSD H1, $146 fixed risk
- Go Long: US30 D1, 0.50 lot
- Turnaround Tuesday: NDX100/NAS100/UT100 D1, 0.24 lot

These sizes were designed for approximately $100,000. For safety, the installer refuses to start the EAs unless the selected account is denominated in USD and its balance is between $90,000 and $110,000. The final account-number confirmation remains mandatory.

## USD 900 profile

The small-account launcher creates a separate profile named **BM Trading 900 - AUTO**. It loads:

- Range Breakout: USDJPY M5, $18 requested fixed stop risk
- ATR Candle Breakout: XAUUSD H1, $18 requested fixed stop risk
- Go Long: US30 D1, 0.01 fixed lot, no hard stop
- Turnaround Tuesday: NDX100/NAS100/UT100 D1, 0.01 fixed lot, no hard stop

The $18 inputs equal 2% of a $900 starting balance. This is not a promise that losses are capped at $18: gaps, slippage and broker minimum volume can exceed the requested risk. The two index EAs have no hard stop at all. If the broker requires more than 0.01 lot for an index, that index EA is skipped instead of silently increasing its position size.

Continue only by typing `RUN <account number> 900` when the installer displays the correct USD account and balance. The launcher intentionally does not install a 10%-risk profile because the historical replay exceeded the account balance at that exposure.

## Important limitations

- The broker must offer all four instruments and allow Expert Advisors.
- Commercial EA licensing or a broker-specific symbol/contract difference can still prevent an EA from starting correctly.
- The original tests used a different broker feed. Run this first on the exact prop firm's demo/free-trial account.
- The static 6% overall drawdown does not remove FundedNext's separate 3% daily equity rule. Floating losses, commissions and swaps count.
- The launcher switches profiles. EAs from the previous profile stop running while the auto profile is active.

The most recent target account, server, data folder, chart symbols and installation time are saved to `_Auto Deploy\LAST INSTALL.txt` after a successful installation.
