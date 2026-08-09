# One-click MT5 installer

All three BAT launcher names call the same any-balance synchronized installer. Open the target MT5 account and run **INSTALL AND RUN ON ACTIVE MT5.bat**.

The BAT detects the active account, resolves XAUUSD, US30, USTEC and EURUSD broker symbols, asks for `RUN <account number> AUTO`, installs the saved settings and opens a thirteen-chart profile.

## Deployed charts

- ORB Volume Profile — XAUUSD M5, POC/VAH/VAL display enabled
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
- AAA Final News Pulse — XAUUSD M1, force-enabled with the saved robust long-only 1% preset

The default planned risk is 1% per EA trade. LTA and ORB Volume Profile are fixed at their tested 1%; other supported risk inputs adapt to the detected balance. The ORB profile is visual confirmation: its value-area, POC-bias and LVN entry filters remain disabled because they failed the locked final-year comparison. Go Long and Turnaround Tuesday use broker-specific hard stops and lots. News Pulse uses its 9 Aug 2026 robust long-only preset: place one buy-stop 30 seconds before release, $6 entry offset, $6 stop, trail from 1.5R at $15 distance, and force-close at 60 seconds. Its planned event risk is 1% before gaps and slippage; no sell-stop is placed.

The installer does not close positions or delete unrelated profiles. It backs up its previous managed profile and removes stale files only from its own managed folders. Multiple bots can trade simultaneously, so combined account exposure and drawdown can be much higher than 1%.
