FULL EA PORTFOLIO - RECOMMENDED ADAPTIVE

Run: Full EA portfolio - Recommended Adaptive.bat
  37-EA normal adaptive roster. Lower starting allocation: 0.25% non-news, separate 0.10% news per ORDER. Nasdaq uses 0.25x selection. Hourly has no SL; minimum lots/gaps can exceed budgets. Not FTMO-safe.

Check files offline (no MT5): append -ValidateOnly to the BAT.

Full EA portfolio - Recommended Adaptive - 37 EAs - installs from _Auto Deploy/Install-BMTradingPortfolio.ps1 (37 research folders) (NORMAL-37-LIVE-PROMPTS-20261008)
  EAs\ and Sets\ are exact copies of what is installed (hashes in PORTFOLIO.json).
  The installer applies your risk/DI choices and the account binding; the copies are the base presets.
   1. Gold Overnight Value Area              XAUUSD  M5   Gold Overnight Value Area EA.ex5  |  24 Gold Overnight Value Area - RAW - 1PCT.set
   2. LTA Volume Profile                     XAUUSD  M15  LTA_Concepts_EA.ex5  |  01 LTA Volume Profile - CURRENT - ALL DAY.set
   3. BTC Top Down FVG Liquidity             BTCUSD  M15  Top Down FVG Liquidity EA.ex5  |  02 BTC Top Down FVG Liquidity - CURRENT - ALL DAY.set
   4. BTC POC Fibonacci                      BTCUSD  M15  POC Fibonacci Volume Profile EA.ex5  |  POCFib-btcusd--optimized--locked.set
   5. ETH Top Down FVG Liquidity             ETHUSD  M15  Top Down FVG Liquidity EA.ex5  |  03 ETH Top Down FVG Liquidity - DYNAMIC 50-20 - ALL DAY.set
   6. ORB Volume Profile                     XAUUSD  M5   ORB Volume Data EA.ex5  |  05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set
   7. ORB Volume Profile Volume Confirmed    XAUUSD  M5   ORB Volume Data EA.ex5  |  05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set
   8. XAU ORB New York M30                   XAUUSD  M30  ORB Volume Data EA.ex5  |  14 XAU ORB New York M30 - LOCKED STANDALONE.set
   9. XAU ORB London NY Overlap M30          XAUUSD  M30  ORB Volume Data EA.ex5  |  15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set
  10. US100 ORB New York M30                 USTEC   M30  ORB Volume Data EA.ex5  |  16 US100 ORB New York M30 - LOCKED STANDALONE.set
  11. US100 H1 ORB 13UTC                     USTEC   M15  ORB Volume Data EA.ex5  |  USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set
  12. US100 Selective ORB V3                 USTEC   M5   US100 Selective ORB Retest EA.ex5  |  BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set
  13. AAA Final Asia Breakout                XAUUSD  H1   AAA Final Asia Breakout EA.ex5  |  asia-breakout.set
  14. DMC Current XAU                        XAUUSD  H1   AAA Final DmC EA.ex5  |  07 DmC - ASIA 3R - DYNAMIC 50-20.set
  15. DMC Fresh Reaction XAU                 XAUUSD  H1   Calyx DMC Fresh Reaction EA.ex5  |  21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set
  16. DMC Fresh Reaction US100               USTEC   H1   Calyx DMC Fresh Reaction EA.ex5  |  22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set
  17. AAA Final EMA3                         XAUUSD  H4   AAA Final EMA3 EA.ex5  |  ema3.set
  18. AAA Final XAU Weakness                 XAUUSD  M30  AAA Final XAU Weakness EA.ex5  |  09 XAU Weakness - M30 STRUCTURE 4R - DYNAMIC 50-20.set
  19. Nasdaq Overnight                       USTEC   M1   Nasdaq Overnight Negative Day EA.ex5  |  10 Nasdaq Overnight - CURRENT - ALL DAY.set
  20. Nasdaq 5M Candle Momentum              USTEC   M5   Nasdaq 5M DI Wide ATR EA.ex5  |  11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set
  21. Sell Nasdaq 15min                      USTEC   M15  Sell Nasdaq 15min Dynamic Exit Research EA.ex5  |  Sell Nasdaq 15min - london-safe dynamic exit candidate - 1pct.set
  22. USDJPY London Open Momentum            USDJPY  M15  Calyx London Open FX Momentum Pipeline EA.ex5  |  usdjpy-london-open-momentum.set
  23. XAU Squeeze Momentum Standard          XAUUSD  H1   Calyx XAU Squeeze Momentum Research EA.ex5  |  23S XAU Squeeze Momentum Safe - ATR3P5 1P5R - 1PCT.set
  24. News Pulse XAU                         XAUUSD  M1   AAA Final News Pulse XAU Event Specific EA.ex5  |  12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set
  25. Gold News V9 Direction                 XAUUSD  M1   GoldNewsV9EA.ex5  |  GoldNewsV9EA-Auto.set
  26. News Pulse XAG                         XAGUSD  M1   AAA Final News Pulse Multi Asset Event EA.ex5  |  12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set
  27. News Pulse BTC                         BTCUSD  M1   AAA Final News Pulse Multi Asset Event EA.ex5  |  12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set
  28. News Pulse EURUSD                      EURUSD  M1   AAA Final News Pulse Multi Asset Event EA.ex5  |  12D News Pulse EURUSD Event Specific - HARD 1.5 TOTAL.set
  29. XAU RSI VWAP                           XAUUSD  H1   RSI VWAP Managed EA.ex5  |  13 XAU RSI VWAP - CURRENT - ALL DAY.set
  30. XAU Trend Progression                  XAUUSD  H4   Trend Progression EA.ex5  |  xau-trend-progression.set
  31. XAU Elliott Wave 1-2-3                 XAUUSD  H4   Elliott Wave 123 EA.ex5  |  ElliottWave-xauusd--h4--optimized--locked.set
  32. XAU Slow Trend                         XAUUSD  H4   Calyx Slow Trend EA.ex5  |  xau-slow-trend-normal.set
  33. XAU Regime Switch                      XAUUSD  M5   Calyx XAU Regime Switch EA.ex5  |  20 XAU Regime Switch - DEMO - HARD 1PCT.set
  34. US100 Month End Flow                   USTEC   M30  Calyx Month End Flow EA.ex5  |  19 US100 Month End Flow M30 - FIRST3 NY - LOCKED 2P5R - HARD 1PCT.set
  35. 3 Way Gold                             XAUUSD  M15  3 Way Gold EA.ex5  |  25 3 Way Gold - BEST OPTIMISED - 1PCT PER MODULE.set
  36. US30 Hourly Profiles                   US30    M1   CalyxHourlyProfiles History Sized.ex5  |  US30.set
  37. US100 Hourly Profiles                  USTEC   M1   CalyxHourlyProfiles History Sized.ex5  |  US100.set
