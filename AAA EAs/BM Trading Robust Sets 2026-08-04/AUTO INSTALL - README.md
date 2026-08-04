# One-click MT5 installer

Double-click **INSTALL AND RUN ON ACTIVE MT5.bat** after opening the MT5 account that should run the portfolio.

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

## Important limitations

- The broker must offer all four instruments and allow Expert Advisors.
- Commercial EA licensing or a broker-specific symbol/contract difference can still prevent an EA from starting correctly.
- The original tests used a different broker feed. Run this first on the exact prop firm's demo/free-trial account.
- The static 6% overall drawdown does not remove FundedNext's separate 3% daily equity rule. Floating losses, commissions and swaps count.
- The launcher switches profiles. EAs from the previous profile stop running while the auto profile is active.

The most recent target account, server, data folder, chart symbols and installation time are saved to `_Auto Deploy\LAST INSTALL.txt` after a successful installation.
