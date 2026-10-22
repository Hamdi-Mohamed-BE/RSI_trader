FTMO GUARDED - CURRENT 14

Run: FTMO guarded - Current 14.bat
  FTMO USD 10K Swing hedging only. Requested risk is capped at USD50 per trade. Existing daily/exposure/phase guards stay unchanged. No news or hourly EAs.

Run: FTMO guarded - Current 14 - ANY BROKER TEST.bat
  Owner test build (2026-10-22): the same 17 FTMO-guarded EAs and settings with the broker-neutral Prop Ready guard. Any MT5 hedging account, broker and currency; risk capped at 0.5% of saved initial balance with scaled daily/exposure guards. Asks Challenge/Verification/continuous mode (default continuous). Not the tested FTMO build: no FTMO pass rate or firm compliance is inherited.

Check files offline (no MT5): append -ValidateOnly to the BAT.

FTMO account build - 17 EAs - installs from _00 Live profiles/Packages/FTMO (FTMO17-ORB05-LIVE-PROMPTS-20261012)
  FTMO account build\EAs\ and FTMO account build\Sets\ are exact copies of what is installed (hashes in PORTFOLIO.json).
  The installer applies your risk/DI choices and the account binding; the copies are the base presets.
   1. XAU RSI VWAP                           XAUUSD  H1   FTMO13-xau-rsi-vwap.ex5  |  FTMO13-xau-rsi-vwap.set
   2. Gold Overnight Value Area              XAUUSD  M5   FTMO13-gold-overnight-value-area.ex5  |  FTMO13-gold-overnight-value-area.set
   3. XAU Squeeze Momentum Standard          XAUUSD  H1   FTMO13-xau-squeeze-momentum-standard.ex5  |  FTMO13-xau-squeeze-momentum-standard.set
   4. DMC Fresh Reaction US100               USTEC   H1   FTMO13-dmc-fresh-reaction-us100.ex5  |  FTMO13-dmc-fresh-reaction-us100.set
   5. EMA3                                   XAUUSD  H4   FTMO13-ema3.ex5  |  FTMO13-ema3.set
   6. XAU Trend Progression                  XAUUSD  H4   FTMO13-xau-trend-progression.ex5  |  FTMO13-xau-trend-progression.set
   7. XAU ORB London NY Overlap M30          XAUUSD  M30  FTMO13-xau-orb-london-ny-overlap-m30.ex5  |  FTMO13-xau-orb-london-ny-overlap-m30.set
   8. Nasdaq Overnight                       USTEC   M1   FTMO13-nasdaq-overnight.ex5  |  FTMO13-nasdaq-overnight.set
   9. US100 H1 ORB 13UTC                     USTEC   M15  FTMO13-us100-h1-orb-13utc.ex5  |  FTMO13-us100-h1-orb-13utc.set
  10. USDJPY London Open Momentum            USDJPY  M15  FTMO13-usdjpy-london-open-momentum.ex5  |  FTMO13-usdjpy-london-open-momentum.set
  11. US100 Month End Flow                   USTEC   M30  FTMO13-us100-month-end-flow.ex5  |  FTMO13-us100-month-end-flow.set
  12. DMC Current XAU                        XAUUSD  H1   FTMO13-dmc-current-xau.ex5  |  FTMO13-dmc-current-xau.set
  13. Nasdaq 5M Candle Momentum              USTEC   M5   FTMO13-nasdaq-5m-candle-momentum.ex5  |  FTMO13-nasdaq-5m-candle-momentum.set
  14. 3 Way Gold                             XAUUSD  M15  FTMO13-3-way-gold.ex5  |  FTMO13-3-way-gold.set
  15. US100 ORB New York M30                 USTEC   M30  FTMO13-us100-orb-new-york-m30.ex5  |  FTMO13-us100-orb-new-york-m30.set
  16. US100 Selective ORB V3                 USTEC   M5   FTMO13-us100-selective-orb-v3.ex5  |  FTMO13-us100-selective-orb-v3.set
  17. XAU ORB New York M30                   XAUUSD  M30  FTMO13-xau-orb-new-york-m30.ex5  |  FTMO13-xau-orb-new-york-m30.set

Any broker test build - 17 EAs - installs from _00 Live profiles/Packages/FTMO-AnyBroker (FTMO17-ANY-BROKER-TEST-20261022)
  Any broker test build\EAs\ and Any broker test build\Sets\ are exact copies of what is installed (hashes in PORTFOLIO.json).
  The installer applies your risk/DI choices and the account binding; the copies are the base presets.
   1. XAU RSI VWAP                           XAUUSD  H1   FTMO13-xau-rsi-vwap.ex5  |  FTMO13-xau-rsi-vwap.set
   2. Gold Overnight Value Area              XAUUSD  M5   FTMO13-gold-overnight-value-area.ex5  |  FTMO13-gold-overnight-value-area.set
   3. XAU Squeeze Momentum Standard          XAUUSD  H1   FTMO13-xau-squeeze-momentum-standard.ex5  |  FTMO13-xau-squeeze-momentum-standard.set
   4. DMC Fresh Reaction US100               USTEC   H1   FTMO13-dmc-fresh-reaction-us100.ex5  |  FTMO13-dmc-fresh-reaction-us100.set
   5. EMA3                                   XAUUSD  H4   FTMO13-ema3.ex5  |  FTMO13-ema3.set
   6. XAU Trend Progression                  XAUUSD  H4   FTMO13-xau-trend-progression.ex5  |  FTMO13-xau-trend-progression.set
   7. XAU ORB London NY Overlap M30          XAUUSD  M30  FTMO13-xau-orb-london-ny-overlap-m30.ex5  |  FTMO13-xau-orb-london-ny-overlap-m30.set
   8. Nasdaq Overnight                       USTEC   M1   FTMO13-nasdaq-overnight.ex5  |  FTMO13-nasdaq-overnight.set
   9. US100 H1 ORB 13UTC                     USTEC   M15  FTMO13-us100-h1-orb-13utc.ex5  |  FTMO13-us100-h1-orb-13utc.set
  10. USDJPY London Open Momentum            USDJPY  M15  FTMO13-usdjpy-london-open-momentum.ex5  |  FTMO13-usdjpy-london-open-momentum.set
  11. US100 Month End Flow                   USTEC   M30  FTMO13-us100-month-end-flow.ex5  |  FTMO13-us100-month-end-flow.set
  12. DMC Current XAU                        XAUUSD  H1   FTMO13-dmc-current-xau.ex5  |  FTMO13-dmc-current-xau.set
  13. Nasdaq 5M Candle Momentum              USTEC   M5   FTMO13-nasdaq-5m-candle-momentum.ex5  |  FTMO13-nasdaq-5m-candle-momentum.set
  14. 3 Way Gold                             XAUUSD  M15  FTMO13-3-way-gold.ex5  |  FTMO13-3-way-gold.set
  15. US100 ORB New York M30                 USTEC   M30  FTMO13-us100-orb-new-york-m30.ex5  |  FTMO13-us100-orb-new-york-m30.set
  16. US100 Selective ORB V3                 USTEC   M5   FTMO13-us100-selective-orb-v3.ex5  |  FTMO13-us100-selective-orb-v3.set
  17. XAU ORB New York M30                   XAUUSD  M30  FTMO13-xau-orb-new-york-m30.ex5  |  FTMO13-xau-orb-new-york-m30.set
