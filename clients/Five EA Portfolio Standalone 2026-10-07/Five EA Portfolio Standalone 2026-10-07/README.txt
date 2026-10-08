CALYX FIVE EA PORTFOLIO - STANDALONE

Unzip the whole package into any folder. Keep its files together.
Open your normal MT5 terminal and log in to the account you want to use.
Double-click five_eas_portfolio.bat.
Choose 1 for fixed USD risk target per trade, or 2 for a percentage recalculated at every entry.
Enter the amount. Percentage defaults to 1%.
If several normal MT5 terminals are running, choose the intended terminal.
Review the detected account and five broker symbols, then confirm installation.

Included only:
  US30 Hourly Profiles - M1
  US100 Hourly Profiles - M1
  Nasdaq 5M Momentum - M5, DI enabled
  RSI VWAP Gold - H1
  EMA3 Gold - H4

Entry/exit settings match the five-EA backtest. No news or other EAs are included.
This follows that five-EA test, not the separate Recommended Adaptive portfolio: adaptive daily/drawdown/loss-streak overlays are OFF. Existing BATs and production EAs are not modified.
The three stop-based EAs have true fixed-cash allocation support, not an install-time percentage conversion.
Percentage sizing uses current equity for Nasdaq/RSI/EMA3 and current balance for the two unchanged hourly systems.
The old Nasdaq hard 1% allocation ceiling is replaced by the selected percentage in this package only (maximum 10%). Its trading logic is unchanged.
Fixed USD requires a USD account. All five require hedging; normal non-portable/non-tester MT5 only.

IMPORTANT
Risk is PER TRADE, PER EA, not a shared portfolio cap. Concurrent trades stack exposure.
The hourly EAs have NO stop-loss. They size against historical adverse-move references (US30 611.53 / US100 358.71 points), not a maximum future loss.
Current broker-minimum/rounding policies are retained and can exceed the selected risk target.
This is real trading software. Spreads, fees, slippage and gaps can exceed planned stop risk.
Recent backtest selection is not untouched out-of-sample evidence and does not guarantee profit.

The installer creates and selects a separate Calyx FIVE EA PORTFOLIO profile. Previous profiles are preserved.
Switching profiles stops excluded EAs managing open trades. Existing positions are NOT closed.
Existing positions owned by one of these five matching magic IDs can be managed by the new profile.
MT5 restarts once. Algo Trading preferences stay unchanged; MT5's profile-change protection can switch it OFF. Check the toolbar and enable it yourself when ready.
The five new chart instances are bound to the selected login, server and broker symbol. Switching accounts will not silently trade a new account.
An initialization check confirms all five EAs actually loaded with the install nonce. This is not proof of trading permission or future execution.
Backups and installation receipts are stored in the selected MT5 data folder, not in this distribution.

Runtime requirements: Windows, normal MT5, and either uv, or Python 3 with the MetaTrader5 package.
uv resolves Python 3.12 and the supported MetaTrader5 Python API automatically when needed (internet may be needed on the first run). No passwords are requested or stored.
Validation without account access: powershell -NoProfile -ExecutionPolicy Bypass -File Install-FivePortfolio.ps1 -ValidateOnly
Advanced noninteractive options: -RiskMode PERCENT -RiskValue 1 -TargetTerminal "C:\...\terminal64.exe" -Yes
-PreflightOnly detects the account/symbols and writes nothing to its data folder; the API may subscribe needed Market Watch symbols.

This package was built and tested offline/in the isolated Strategy Tester. It was not run against your live account during creation.
