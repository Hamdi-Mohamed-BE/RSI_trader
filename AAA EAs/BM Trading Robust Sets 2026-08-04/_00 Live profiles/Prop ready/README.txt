PROP READY

Run: Prop ready.bat
  Nine selected EAs; all five ORBs at 0.5R. Broker-neutral demo/live MT5 hedging account; fixed cash uses account currency. Planned risk capped at 0.5% of saved initial balance, with scaled daily/exposure guards. Default continuous mode; no phase profit stop. Other brokers/custom risk/DI choices do not inherit FTMO pass rates or guarantee firm compliance.

Run: Codex_Best_FTMO.bat
  Core 4 plus five 0.5R ORBs; DI ON by default for Nasdaq and USDJPY. Broker-neutral MT5 hedging, any supported account currency/balance; no FTMO-only lock. Ask Challenge/Verification/continuous mode. Cash allocation is in account currency; planned risk capped at 0.5% of saved initial balance. Reuses Prop Ready safety state; different brokers or custom inputs do not inherit historical pass rates.

Check files offline (no MT5): append -ValidateOnly to the BAT.

Prop ready - 9 EAs - installs from _00 Live profiles/Packages/PropReady (PROP-READY9-BROKER-NEUTRAL-20261017)
  EAs\ and Sets\ are exact copies of what is installed (hashes in PORTFOLIO.json).
  The installer applies your risk/DI choices and the account binding; the copies are the base presets.
   1. XAU RSI VWAP                           XAUUSD  H1   FTMO13-xau-rsi-vwap.ex5  |  FTMO13-xau-rsi-vwap.set
   2. XAU ORB London NY Overlap M30          XAUUSD  M30  FTMO13-xau-orb-london-ny-overlap-m30.ex5  |  FTMO13-xau-orb-london-ny-overlap-m30.set
   3. US100 H1 ORB 13UTC                     USTEC   M15  FTMO13-us100-h1-orb-13utc.ex5  |  FTMO13-us100-h1-orb-13utc.set
   4. USDJPY London Open Momentum            USDJPY  M15  FTMO13-usdjpy-london-open-momentum.ex5  |  FTMO13-usdjpy-london-open-momentum.set
   5. US100 Month End Flow                   USTEC   M30  FTMO13-us100-month-end-flow.ex5  |  FTMO13-us100-month-end-flow.set
   6. Nasdaq 5M Candle Momentum              USTEC   M5   FTMO13-nasdaq-5m-candle-momentum.ex5  |  FTMO13-nasdaq-5m-candle-momentum.set
   7. US100 ORB New York M30                 USTEC   M30  FTMO13-us100-orb-new-york-m30.ex5  |  FTMO13-us100-orb-new-york-m30.set
   8. US100 Selective ORB V3                 USTEC   M5   FTMO13-us100-selective-orb-v3.ex5  |  FTMO13-us100-selective-orb-v3.set
   9. XAU ORB New York M30                   XAUUSD  M30  FTMO13-xau-orb-new-york-m30.ex5  |  FTMO13-xau-orb-new-york-m30.set
