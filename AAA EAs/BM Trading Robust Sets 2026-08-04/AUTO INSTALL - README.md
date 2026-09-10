# MT5 portfolio installers

Open and connect the target MT5 account before using an installer. All launchers detect the active balance and broker symbols, preserve unrelated profiles, back up the previous managed profile, and require an account-specific confirmation before they can restart MT5.

## Choose a launcher

- **INSTALL AND RUN ON ACTIVE MT5.bat** — Standard mode using the saved default risk configuration.
- **INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat** — the same portfolio with a completed-D1 Markov direction gate enabled independently inside every EA.
- **INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat** — asks for percentage or fixed-USD risk per EA trade, then asks whether to deploy Standard or Full Safe mode.

For Dynamic Config, percentage-risk EAs receive the balance-equivalent percentage calculated at installation, so fixed-USD exposure can drift as equity changes. News Pulse remains hard-locked at 0.75% per pending direction. Broker minimum lots, gaps and slippage can still exceed planned risk.

## Core examples in the current 31-chart portfolio

- LTA Volume Profile — XAUUSD M15 — current exit logic, all day
- BTC Top Down FVG Liquidity — BTCUSD M15 — current exit logic, all day, optional when the broker has no matching symbol
- ETH Top Down FVG Liquidity — ETHUSD M15 — dynamic 50%/20% M15 protection, all day, optional when the broker has no matching symbol
- ORB Volume Profile — XAUUSD M5 — dynamic 50%/20% M15 protection, all day
- Asia Breakout — XAUUSD H1 — dynamic 50%/20% M15 protection, all day
- EMA3 — XAUUSD H4 — dynamic 50%/20% M15 protection, all day
- XAU Weakness — XAUUSD M15 — dynamic 50%/20% M15 protection, all day
- Nasdaq Overnight — USTEC M1 — current exit logic, all day
- Nasdaq 5M Candle Momentum — USTEC M5 — dynamic 50%/20% M15 protection, all day
- News Pulse — XAUUSD M1 — NFP/CPI/FOMC long-only with dynamic 50%/20% M15 protection, all day

This short list documents the original core; the central installer is the source of truth for all 31 current charts. The approved 2026-09-10 exclusions are Engineered Liquidity XAU, ORB Volume Profile High Win 0.75R, XAG Session VWAP Snapback and XAU Squeeze Momentum High Win 0.75R. DMC Current XAU remains active.

The dynamic rule acts only after a completed M15 candle reaches 50% of the original entry-to-target distance. It then moves the stop to lock 20% of that distance. The session experiments were rejected, so no portfolio-wide UTC session gate is active in these selected settings.

Each EA owns its own chart and magic number. Several can trade at the same time, so account-level risk is the sum of open exposure, not the risk chosen for one trade. Demo-forward-test the exact broker, symbols and mode before considering live capital.
