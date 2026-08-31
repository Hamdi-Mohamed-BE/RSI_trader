# MT5 portfolio installers

Open and connect the target MT5 account before using an installer. All launchers detect the active balance and broker symbols, preserve unrelated profiles, back up the previous managed profile, and require an account-specific confirmation before they can restart MT5.

## Choose a launcher

- **INSTALL AND RUN ON ACTIVE MT5.bat** — Standard mode using the saved default risk configuration.
- **INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat** — the same portfolio with a completed-D1 Markov direction gate enabled independently inside every eligible EA. XAU Markov is already safe by design.
- **INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat** — asks for percentage or fixed-USD risk per EA trade, then asks whether to deploy Standard or Full Safe mode.

For Dynamic Config, the Engineered Liquidity XAU and BTC EAs support exact fixed cash risk. Percentage-only EAs receive the equivalent percentage calculated from the balance detected at installation, so their dollar exposure will drift as equity changes. Broker minimum lots, gaps and slippage can still exceed the requested risk.

## Current 15-chart portfolio

- LTA Volume Profile — XAUUSD M15
- BTC Top Down FVG Liquidity — BTCUSD M15, optional when the broker has no matching symbol
- ETH Top Down FVG Liquidity — ETHUSD M15, optional when the broker has no matching symbol
- Engineered Liquidity XAU — XAUUSD H1, improved 2R minimum preset
- Engineered Liquidity BTC — BTCUSD M30, improved displacement preset, optional and forward-test status
- ORB Volume Profile — XAUUSD M5
- US100 Fabio ORB 1R — USTEC M5
- XAU Markov Regime — XAUUSD D1
- Asia Breakout — XAUUSD H1
- DmC — XAUUSD H1
- EMA3 — XAUUSD H4
- XAU Weakness — XAUUSD M15
- Nasdaq Overnight — USTEC M1
- Nasdaq 5M Candle Momentum — USTEC M5
- News Pulse — XAUUSD M1, NFP/CPI/FOMC long-only preset

Each EA owns its own chart and magic number. Several can trade at the same time, so account-level risk is the sum of open exposure, not the risk chosen for one trade. Demo-forward-test the exact broker, symbols and mode before considering live capital.
