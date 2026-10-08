CALYX CURRENT14 + ORB05 — one-file MT5 launcher

Double-click current14_orb05.bat. Its compiled EAs, presets and installer are
embedded; copying that BAT alone to another Windows PC is sufficient for the
package files. Account inspection needs uv, or Python with MetaTrader5.
The EAs themselves do not need Python once installed.

Setup asks for fixed USD or dynamic percentage risk and its value, followed by
separate Nasdaq 5M and USDJPY DI ON/OFF choices (default ON). Percentage risk
defaults to 0.5% of current equity. Risk applies per trade, not to the complete
portfolio. Each of 3-Way Gold's modules receives that risk. USDJPY's ADX20 filter
is retained regardless of the DI choice. DI OFF is not the tested DI-ON preset.

15 unique EAs: all 14 current FTMO strategy-input variants, WITHOUT the FTMO
guard, plus Gold New York ORB at 0.5R. Existing US100 H1 and Gold London–NY ORBs
are changed to 0.5R rather than duplicated. Selective US100 V3 is excluded: its
previously accepted result used 2R, not 0.5R. No news or hourly-timed EAs added.

Included roster (current inputs except the two indicated ORB target changes):
  1. XAU RSI VWAP
  2. Gold Overnight Value Area
  3. XAU Squeeze Momentum Standard
  4. DMC Fresh Reaction US100
  5. EMA3 Gold
  6. XAU Trend Progression
  7. XAU ORB London-NY Overlap M30 — target changed to 0.5R
  8. Nasdaq Overnight
  9. US100 H1 ORB 13UTC — target changed to 0.5R
 10. USDJPY London Open Momentum — DI prompt; ADX20 retained
 11. US100 Month End Flow
 12. DMC Current XAU
 13. Nasdaq 5M Candle Momentum — DI prompt
 14. 3-Way Gold — selected risk is per module trade
 15. XAU ORB New York M30 — added with 0.5R target

Compatibility: MT5 demo and live HEDGING accounts, any account balance/broker
that supplies tradable XAUUSD, US100/USTEC and USDJPY contracts. Broker suffixes
are mapped automatically. MT4/netting, portable/tester/custom-config terminals
are not supported by this automatic installer. Percentage works in the account
currency. Fixed USD on non-USD accounts needs a fresh direct USD/account-currency
FX quote; otherwise the EA skips a new entry rather than assuming a conversion.
Cent/non-standard currencies must use percentage risk.

There is NO shared daily $400/$450 loss stop, total-loss limit, profit target,
FTMO phase, $50 fixed clamp or account-size restriction in this package.
It is NOT the previously simulated guarded portfolio. Its performance and
funding probabilities have not been established by those earlier simulations.
Native lot minimum/rounding policies, leverage limits, fees and gaps can make
actual losses differ from the chosen target. Native stops/management are
preserved except the three explicit ORB target changes.

Setup only affects the chosen running terminal, keeps login/Algo Trading
preferences unchanged, and restarts MT5 after confirmation. It creates its own
profile and recoverable backups. Existing positions are NOT closed; switching
profiles stops excluded EAs from managing their positions. Review those trades
first. If Algo Trading was already enabled, entries may occur after activation.
The installed EAs bind to the selected account/server/symbol; rerun the BAT to
configure another account. The package is not tied to FTMO or one licensed login.

Safe offline check (no MT5/API access):
  current14_orb05.bat -ValidateOnly

Read-only account preflight plus Market Watch subscriptions, no restart:
  current14_orb05.bat -PreflightOnly

Example unattended choices (still requires a running compatible terminal):
  current14_orb05.bat -RiskMode PERCENT -RiskValue 0.5 -NasdaqDIFilter ON -UsdJpyDIFilter OFF

Building this package did not install it or access any live account.
