# One-click MT5 installer

All three BAT launcher names call the same any-balance synchronized installer. Open the target MT5 account and run **INSTALL AND RUN ON ACTIVE MT5.bat**.

The BAT detects the active account, resolves XAUUSD, US30, USTEC and EURUSD broker symbols, asks for `RUN <account number> AUTO`, installs the exact corrected retest settings and opens an eleven-chart profile.

## Deployed charts

- LTA Volume Profile — XAUUSD M15
- ATR Candle Breakout — XAUUSD H1
- AAA Final Asia Breakout — XAUUSD H1
- AAA Final DmC — XAUUSD H1
- Go Long — US30 D1
- AAA Final EMA3 — XAUUSD H4
- AAA Final XAU Weakness — XAUUSD M15
- Ninja Turtle Scalper — EURUSD M5
- Nasdaq Overnight — USTEC M1
- Turnaround Tuesday — USTEC D1
- AAA Final US100 Weakness — USTEC M15

The default planned risk is 1% per EA trade. LTA is fixed at 1%; other supported risk inputs adapt to the detected balance. Go Long and Turnaround Tuesday use broker-specific hard stops and lots.

The installer does not close positions or delete unrelated profiles. It backs up its previous managed profile and removes stale files only from its own managed folders. Multiple bots can trade simultaneously, so combined account exposure and drawdown can be much higher than 1%.
