# One-click MT5 installer

All three launcher names now use the same any-balance synchronized installer:

- **INSTALL AND RUN ON ACTIVE MT5.bat**
- **INSTALL AND RUN ON 900 USD MT5.bat**
- **INSTALL AND RUN ON 100K MT5.bat**

Open the target MT5 account first, then double-click the matching launcher.

The installer:

1. Detects the running MT5 installation. If none or more than one is running, it asks which installation to use.
2. Reads and displays the logged-in account number, server, balance and equity.
3. Resolves the broker's actual names for XAUUSD and US30.
4. Requires the final confirmation `RUN <account number> AUTO` because the EAs can place real trades.
5. Closes that MT5 cleanly, copies the seven `.ex5` files and final `.set` files, and creates an isolated synchronized profile.
6. Enables Algo Trading, restarts MT5 and loads seven charts with the exact final settings already attached.

It does not delete other MT5 profiles and does not close open positions. If the auto profile already exists, the installer moves it to a timestamped backup before rebuilding it.

## Deployed charts

- ATR Candle Breakout: XAUUSD H1
- Go Long: US30 D1
- AAA Final EMA3: XAUUSD H4
- AAA Final Asia Breakout: XAUUSD H1
- AAA Final Weekend Direction: XAUUSD M15
- AAA Final XAU Weakness: XAUUSD M15
- LTA Volume Profile: XAUUSD M15, fixed 1.00% equity risk per trade

The synchronized installer accepts any positive account balance. Adaptive EAs use the risk percentage passed to the installer, which defaults to 1%. LTA remains fixed at 1.00% per trade even if that optional adaptive percentage is changed. The final account-number confirmation remains mandatory.

## Risk handling

The installer rebuilds supported fixed-money inputs and the Go Long lot/stop from the detected balance and broker contract data. Broker minimum volume and stop distance can force actual risk above the requested percentage, and the preflight displays that before installation.

LTA loads `XAUUSD M15 - EXNESS FIXED 1.00pct.set`, which fixes its momentum risk, contrarian risk, and absolute risk cap at 1.00%. Multiple simultaneous EA positions can still produce combined account exposure above 1%.

## Important limitations

- The broker must offer XAUUSD and US30 and allow Expert Advisors.
- Commercial EA licensing or a broker-specific symbol/contract difference can still prevent an EA from starting correctly.
- The original tests used a different broker feed. Run this first on the exact prop firm's demo/free-trial account.
- The static 6% overall drawdown does not remove FundedNext's separate 3% daily equity rule. Floating losses, commissions and swaps count.
- The launcher switches profiles. EAs from the previous profile stop running while the auto profile is active.

The most recent target account, server, data folder, chart symbols and installation time are saved to `_Auto Deploy\LAST INSTALL.txt` after a successful installation.
