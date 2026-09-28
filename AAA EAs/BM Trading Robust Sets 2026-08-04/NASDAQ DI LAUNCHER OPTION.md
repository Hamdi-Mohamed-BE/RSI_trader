# Nasdaq 5M DI selection — 28 September 2026

BEST RECOMMENDED and FTMO 10K SWING now ask `Nasdaq 5M DI14 filter ON or OFF [ON]`.
Press Enter for the existing DI-ON setting. OFF disables only `InpRequireDIAgreement`.
The completed 09:30 candle, EMA12, 0.60% price stop, ATR14 x 6 trailing from +1R,
no TP and overnight/weekend holding rules remain unchanged. Other EAs are unaffected.

This is a user-selected runtime setting, not an automatic indicator switch. Run the
BAT again to choose a different configuration. Pulling Git does not change charts
already running in MT5. The stored research presets and published website evidence
remain DI ON; do not treat their results as evidence for a DI-OFF installation.

FTMO keeps News OFF, the 13 guarded EAs, $50 maximum planned stop risk, existing
portfolio/account checks, and Algo Trading OFF after installation. No new FTMO
success-rate estimates are implied by either selection.

For scripted use, pass `-NasdaqDIFilter ON` or `-NasdaqDIFilter OFF`; an explicit
choice suppresses the DI question. Other ordinary launchers continue to default ON
without the additional question. `-ValidateOnly` never asks the DI question and
uses ON unless explicitly overridden. Invalid answers stop before installation.

Verification: offline tests compare all 34 ordinary and 13 FTMO effective presets;
only the Nasdaq DI key may differ. Prompt/default/explicit/invalid paths and FTMO
package integrity are checked without connecting to or restarting the live terminal.
