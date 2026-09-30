# Calyx — verified repository navigation inventory

Snapshot: 2026-09-23. Static inspection only. No installer or EA was executed.

Root: `C:\Users\hama101\Desktop\geek\ai trader`
Origin observed: https://github.com/Hamdi-Mohamed-BE/RSI_trader.git
Branch observed: `new-telegram-copy`; HEAD: `f7f2523a6`.
Research root below means `AAA EAs/BM Trading Robust Sets 2026-08-04`.

## 1. Canonical installer roster: 34 entries

Extracted from `_Auto Deploy/Install-BMTradingPortfolio.ps1` as source text, not by
dot-sourcing/executing the script. Period is the configured chart period in minutes, not necessarily
the opening-range duration or every internal signal timeframe. USTEC is the canonical alias;
the runtime must discover the broker's actual symbol.

This is a source/package inventory, NOT a list of verified live running charts.
Optional symbol handling and runtime validation can affect actual installation.

| # | Installer label | Canonical symbol | Chart minutes |
|---|---|---|---:|
| 1 | Gold Overnight Value Area | XAUUSD | 5 |
| 2 | LTA Volume Profile | XAUUSD | 15 |
| 3 | BTC Top Down FVG Liquidity | BTCUSD | 15 |
| 4 | BTC POC Fibonacci | BTCUSD | 15 |
| 5 | ETH Top Down FVG Liquidity | ETHUSD | 15 |
| 6 | ORB Volume Profile | XAUUSD | 5 |
| 7 | ORB Volume Profile Volume Confirmed | XAUUSD | 5 |
| 8 | XAU ORB New York M30 | XAUUSD | 30 |
| 9 | XAU ORB London NY Overlap M30 | XAUUSD | 30 |
| 10 | US100 ORB New York M30 | USTEC | 30 |
| 11 | US100 H1 ORB 13UTC | USTEC | 15 |
| 12 | US100 Selective ORB V3 | USTEC | 5 |
| 13 | AAA Final Asia Breakout | XAUUSD | 60 |
| 14 | DMC Current XAU | XAUUSD | 60 |
| 15 | DMC Fresh Reaction XAU | XAUUSD | 60 |
| 16 | DMC Fresh Reaction US100 | USTEC | 60 |
| 17 | AAA Final EMA3 | XAUUSD | 240 |
| 18 | AAA Final XAU Weakness | XAUUSD | 30 |
| 19 | Nasdaq Overnight | USTEC | 1 |
| 20 | Nasdaq 5M Candle Momentum | USTEC | 5 |
| 21 | Sell Nasdaq 15min | USTEC | 15 |
| 22 | USDJPY London Open Momentum | USDJPY | 15 |
| 23 | XAU Squeeze Momentum Standard | XAUUSD | 60 |
| 24 | News Pulse XAU | XAUUSD | 1 |
| 25 | Gold News V9 Direction | XAUUSD | 1 |
| 26 | News Pulse XAG | XAGUSD | 1 |
| 27 | News Pulse BTC | BTCUSD | 1 |
| 28 | News Pulse EURUSD | EURUSD | 1 |
| 29 | XAU RSI VWAP | XAUUSD | 60 |
| 30 | XAU Trend Progression | XAUUSD | 240 |
| 31 | XAU Elliott Wave 1-2-3 | XAUUSD | 240 |
| 32 | XAU Slow Trend | XAUUSD | 240 |
| 33 | XAU Regime Switch | XAUUSD | 5 |
| 34 | US100 Month End Flow | USTEC | 30 |

### Exact default and explicitly selected artifact routes
All paths in this subsection are relative to the research root. `../../AI news` resolves back
to the workspace's separate prediction project. Default SET is not necessarily the final installed
SET after recommended-mode selection, cash/percent sizing and adaptive input updates.
Dedicated Safe/Recommended routes are shown when explicitly present in the item; some Safe
behavior is injected by shared logic rather than represented by a different file here.

#### 1. Gold Overnight Value Area

- ExpertSource: `Gold Overnight Value Area EA/EA/Gold Overnight Value Area EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/24 Gold Overnight Value Area - RAW - 1PCT.set`

#### 2. LTA Volume Profile

- ExpertSource: `LTA volume profile/EA/LTA_Concepts_EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/01 LTA Volume Profile - CURRENT - ALL DAY.set`

#### 3. BTC Top Down FVG Liquidity

- ExpertSource: `Top Down FVG Liquidity Research 2026-08-27/EA/Top Down FVG Liquidity EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/02 BTC Top Down FVG Liquidity - CURRENT - ALL DAY.set`

#### 4. BTC POC Fibonacci

- ExpertSource: `POC Fibonacci Volume Profile Research 2026-09-04/EA/POC Fibonacci Volume Profile EA.ex5`
- SetSource: `POC Fibonacci Volume Profile Research 2026-09-04/Sets/POCFib-btcusd--optimized--locked.set`

#### 5. ETH Top Down FVG Liquidity

- ExpertSource: `Top Down FVG Liquidity Research 2026-08-27/EA/Top Down FVG Liquidity EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/03 ETH Top Down FVG Liquidity - DYNAMIC 50-20 - ALL DAY.set`

#### 6. ORB Volume Profile

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set`

#### 7. ORB Volume Profile Volume Confirmed

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set`

#### 8. XAU ORB New York M30

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/14 XAU ORB New York M30 - LOCKED STANDALONE.set`

#### 9. XAU ORB London NY Overlap M30

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set`

#### 10. US100 ORB New York M30

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/16 US100 ORB New York M30 - LOCKED STANDALONE.set`

#### 11. US100 H1 ORB 13UTC

- ExpertSource: `ORB Volume Data EA/ORB Volume Data EA.ex5`
- SetSource: `ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set`

#### 12. US100 Selective ORB V3

- ExpertSource: `US100 Selective ORB Research 2026-08-21/EA/US100 Selective ORB Retest EA.ex5`
- SetSource: `US100 Selective ORB Research 2026-08-21/Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set`

#### 13. AAA Final Asia Breakout

- ExpertSource: `AAA Final EAs/AAA Final Asia Breakout EA/AAA Final Asia Breakout EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/06 Asia Breakout - DYNAMIC 50-20 - ALL DAY.set`

#### 14. DMC Current XAU

- ExpertSource: `AAA Final EAs/AAA Final DmC EA/AAA Final DmC EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/07 DmC - ASIA 3R - DYNAMIC 50-20.set`

#### 15. DMC Fresh Reaction XAU

- ExpertSource: `AAA Final EAs/Calyx DMC Fresh Reaction EA/Calyx DMC Fresh Reaction EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set`

#### 16. DMC Fresh Reaction US100

- ExpertSource: `AAA Final EAs/Calyx DMC Fresh Reaction EA/Calyx DMC Fresh Reaction EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set`

#### 17. AAA Final EMA3

- ExpertSource: `AAA Final EAs/AAA Final EMA3 EA/AAA Final EMA3 EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/08 EMA3 - H4 PIVOT 1.7R - DYNAMIC 60-20 ONLY.set`

#### 18. AAA Final XAU Weakness

- ExpertSource: `AAA Final EAs/AAA Final XAU Weakness EA/AAA Final XAU Weakness EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/09 XAU Weakness - M30 STRUCTURE 4R - DYNAMIC 50-20.set`

#### 19. Nasdaq Overnight

- ExpertSource: `Nasdaq Overnight Negative Day EA/Nasdaq Overnight Negative Day EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/10 Nasdaq Overnight - CURRENT - ALL DAY.set`

#### 20. Nasdaq 5M Candle Momentum

- ExpertSource: `Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum Audit EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R - HARD 1PCT.set`

#### 21. Sell Nasdaq 15min

- ExpertSource: `Sell Nasdaq 15min Research 2026-09-08/EA/Sell Nasdaq 15min EA.ex5`
- SetSource: `Sell Nasdaq 15min Research 2026-09-08/Sets/Sell Nasdaq 15min - selected research - 1pct.set`
- RecommendedExpertSource: `Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/EA/Sell Nasdaq 15min Dynamic Exit Research EA.ex5`
- RecommendedSetSource: `Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/Sets/Sell Nasdaq 15min - london-safe dynamic exit candidate - 1pct.set`
- SafeSetSource: `Sell Nasdaq 15min Research 2026-09-08/Sets/Sell Nasdaq 15min - safe London 600-1000 - 1pct.set`

#### 22. USDJPY London Open Momentum

- ExpertSource: `London Open FX Momentum Research 2026-09-08/Pipeline/EA/Calyx London Open FX Momentum Pipeline EA.ex5`
- SetSource: `London Open FX Momentum Research 2026-09-08/Pipeline/Sets/London Open FX Momentum - USDJPY - pipeline selected - 1pct.set`

#### 23. XAU Squeeze Momentum Standard

- ExpertSource: `XAU Squeeze Momentum Research 2026-09-10/EA/Calyx XAU Squeeze Momentum Research EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/23 XAU Squeeze Momentum Standard - ATR3P5 1P5R - 1PCT.set`
- SafeSetSource: `Selected Portfolio Settings 2026-09-01/23S XAU Squeeze Momentum Safe - ATR3P5 1P5R - 1PCT.set`

#### 24. News Pulse XAU

- ExpertSource: `AAA Final EAs/AAA Final News Pulse XAU Event Specific EA/AAA Final News Pulse XAU Event Specific EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set`

#### 25. Gold News V9 Direction

- ExpertSource: `../../AI news/mt5/GoldNewsV9EA.ex5`
- SetSource: `../../AI news/mt5/GoldNewsV9EA-Auto.set`

#### 26. News Pulse XAG

- ExpertSource: `AAA Final EAs/AAA Final News Pulse Multi Asset Event EA/AAA Final News Pulse Multi Asset Event EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set`

#### 27. News Pulse BTC

- ExpertSource: `AAA Final EAs/AAA Final News Pulse Multi Asset Event EA/AAA Final News Pulse Multi Asset Event EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set`

#### 28. News Pulse EURUSD

- ExpertSource: `AAA Final EAs/AAA Final News Pulse Multi Asset Event EA/AAA Final News Pulse Multi Asset Event EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/12D News Pulse EURUSD Event Specific - HARD 1.5 TOTAL.set`

#### 29. XAU RSI VWAP

- ExpertSource: `RSI VWAP Research 2026-09-02/EA/RSI VWAP Managed EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/13 XAU RSI VWAP - CURRENT - ALL DAY.set`

#### 30. XAU Trend Progression

- ExpertSource: `Trend Progression Research 2026-09-02/EA/Trend Progression EA.ex5`
- SetSource: `Trend Progression Research 2026-09-02/Sets/TrendProgression-xauusd--h4--optimized--locked.set`

#### 31. XAU Elliott Wave 1-2-3

- ExpertSource: `Elliott Wave Research 2026-09-05/EA/Elliott Wave 123 EA.ex5`
- SetSource: `Elliott Wave Research 2026-09-05/Sets/ElliottWave-xauusd--h4--optimized--locked.set`

#### 32. XAU Slow Trend

- ExpertSource: `Slow Multi Asset Trend Research 2026-09-06/EA/Calyx Slow Trend EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/17 XAU Slow Trend H4 - LOCKED 6R - HARD 1PCT.set`

#### 33. XAU Regime Switch

- ExpertSource: `Regime Switch Overlay Research 2026-09-06/EA/Calyx XAU Regime Switch EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/20 XAU Regime Switch - DEMO - HARD 1PCT.set`

#### 34. US100 Month End Flow

- ExpertSource: `Month End Institutional Flow Research 2026-09-06/EA/Calyx Month End Flow EA.ex5`
- SetSource: `Selected Portfolio Settings 2026-09-01/19 US100 Month End Flow M30 - FIRST3 NY - LOCKED 2P5R - HARD 1PCT.set`


Static path checks: 63 unique referenced executable/SET routes checked;
0 missing. Existence does not establish compile/source parity or performance.


## 2. Maintained normal launchers

Located directly under the research root:
- `RECOMMENDED ADAPTIVE.bat`
- `BEST RECOMMENDED 2026-09-01.bat`
- `INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat`
- `INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat`
- `INSTALL AND RUN ON 100K MT5.bat`
- `INSTALL AND RUN ON 900 USD MT5.bat`
- `INSTALL AND RUN ON ACTIVE MT5.bat`

`AVA EAS.bat` is separate and excluded from normal-account updates unless requested.
Archived/hotfix BATs are not silently included in this maintained set.

## 3. Research and package directory index

182 immediate directories were observed under the research root.
Listing means existence only: inspect each README/RULES/REPORT/manifest and source to determine
completion, coverage, latest variant, approval and deployment status. In particular, a raw retest
directory is not evidence that a requested full pipeline finished.

- `_Auto Deploy`
- `_Backtests`
- `_Optimization Evidence`
- `_Shared`
- `3 way gold Full Optimization 2026-09-13`
- `3 way gold Independent Engines 2026-09-13`
- `3 way gold Raw Research 2026-09-13`
- `AAA Final EAs`
- `Active BAT Backtest 2026-08-12`
- `Active BAT Backtest 5Y 2026-08-12`
- `Active BAT Session Day Filter Research 2026-08-25`
- `active EAs previous flat layout backup 2026-08-10`
- `active EAs with code and saves and charts`
- `Active Portfolio Full Pipeline 2026-09-05`
- `Active Portfolio Reports 2026-08-06`
- `Anchored POC Pullback Research 2026-08-14`
- `Apex Pulse and IVB Research 2026-08-10`
- `Asia Sweep Structure Research 2026-08-29`
- `ATR Candle Breakout EA`
- `Auction and Cross Session Papers Research 2026-09-11`
- `Ava Futures Portfolio Research 2026-09-09`
- `BAT Portfolio Backtest 2026-08-09`
- `Bitcoin OBV Walk Forward Research 2026-09-09`
- `Bitcoin Overnight Sessions Research 2026-09-09`
- `BM 900 INSTALLER HOTFIX FILES`
- `Brave TPro and HFT Validation 2026-08-14`
- `BTC Order Flow Research 2026-08-13`
- `BTC Turn of Candle Research 2026-09-09`
- `Carry Feasibility Research 2026-09-09`
- `Close Drive Intraday Momentum Research 2026-09-06`
- `Conditional FX Momentum Research 2026-09-07`
- `Crazy Horse ORB Raw Research 2026-09-11`
- `Cross Asset Metals Confirmation Research 2026-09-07`
- `Cross Sectional Momentum Rotation Research 2026-09-07`
- `CRT Parent Range Research 2026-08-30`
- `Crypto Hybrid Edge Research 2026-08-30`
- `Crypto Weekend Audit 2026-09-06`
- `D14 H1 M5 Break Retest Raw 2026-09-13`
- `Daily Bias AMD Validation 2026-08-10`
- `Daily Box Theory Research 2026-09-01`
- `Diagnostics`
- `DMC Cheat Sheet Regime Research 2026-09-12`
- `DMC Fresh Reaction Research 2026-09-09`
- `DMC H4 Fresh Ladder Research 2026-09-10`
- `DMC Playlist Deep Review 2026-09-09`
- `DMC Video Update 2026-08-11`
- `DonnFX7 Reel Reconstruction Research 2026-09-10`
- `Dynamic Trailing Session Research 2026-09-01`
- `Elliott Wave Research 2026-09-05`
- `Engineered Liquidity Sweep Research 2026-08-30`
- `EURUSD Post-News Continuation Research 2026-08-16`
- `Fast Alpha Applied BAT Research 2026-08-16`
- `Fast Alpha Strategy Families Research 2026-08-15`
- `FTMO 10K One Attempt Plan 2026-09-19`
- `FTMO Broker Comparison 2026-09-09`
- `FTMO Combination Study 2026-09-19`
- `FTMO Combined Portfolio 2026-09-13`
- `FTMO Loss Escalation Study 2026-09-20`
- `FTMO Reinvestment Plan 2026-09-13`
- `FTMO Swing Challenge Monte Carlo 2026-09-12`
- `FVG Volume Research 2026-08-14`
- `FX Fixing Reversal Research 2026-09-09`
- `gemeni`
- `Global Macro Auction Market Research 2026-08-14`
- `Go Long EA`
- `Gold EMA Cross Breakout Validation 2026-08-14`
- `Gold Liquidity Sweep EA`
- `Gold Overnight Value Area EA`
- `Gold Overnight Value Area Pipeline 2026-09-19`
- `Gold Raw Plus News FTMO Four Month Study 2026-09-19`
- `Gold Raw Plus News FTMO Two Month Study 2026-09-19`
- `Gold Value Area Loss Escalation Research 2026-09-20`
- `Gold VWAP EMA Regime Research 2026-09-08`
- `goldenrock bot prompt mql5`
- `H4 Fair Value Gap Raw Research 2026-09-14`
- `Hedging Demand Intraday Momentum Research 2026-09-08`
- `HTF Paper Trend Portfolio Research 2026-09-07`
- `Hybrid CVD Research 2026-08-12`
- `ICT Macro Liquidity Sweep Research 2026-08-29`
- `ICT SNR Research 2026-08-13`
- `Intraday FX Session Effect Research 2026-09-08`
- `Janus Anti Fragility Raw Research 2026-09-12`
- `John Kurisko Quad Stochastic Validation 2026-08-13`
- `LCE Volume Profile Proxy Research 2026-08-30`
- `Liquidity Clock Confirmation Research 2026-09-07`
- `London Open FX Momentum Research 2026-09-08`
- `London Opening Sweep FVG Raw Research 2026-09-12`
- `LTA AOI Exit Research 2026-09-13`
- `LTA Book Fidelity Research 2026-09-07`
- `LTA volume profile`
- `LuxAlgo Order Flow Research 2026-09-09`
- `LVN Volume Profile Research 2026-09-04`
- `Month End Institutional Flow Research 2026-09-06`
- `Nasdaq 075R Two Month FTMO Replay 2026-09-19`
- `Nasdaq 5M Open EMA ATR Research 2026-08-20`
- `Nasdaq AMD Paper Research 2026-09-09`
- `Nasdaq Overnight Negative Day EA`
- `New York FX Reversal Research 2026-09-08`
- `News Pulse BTC Official 3Y Research 2026-09-11`
- `News Pulse Crypto Extension 2026-09-11`
- `News Pulse Direction Research 2026-09-05`
- `News Pulse Event Parameters Research 2026-09-19`
- `News Pulse Event Replay 2026-09-11`
- `News Pulse Full Coverage 2026-09-12`
- `News Pulse FXMacroData Audit 2026-09-10`
- `News Pulse Multi Asset Event Parameters 2026-09-19`
- `Night Effect Metals Research 2026-09-09`
- `Ninja Turtle Scalper EA`
- `Noise Boundary VWAP Momentum Research 2026-09-09`
- `NQ Drift VWAP Pullback EA`
- `Online Research EAs 2026-08-11`
- `ORB H1 Range Research 2026-09-05`
- `ORB Low RR Two Month Research 2026-09-19`
- `ORB Session Matrix Research 2026-09-04`
- `ORB Session Matrix Research 2026-09-05`
- `ORB Volume Data EA`
- `Overnight Cross-Market Research 2026-08-30`
- `Overnight Profile Raw Comparison 2026-09-19`
- `Overnight Value Area Breakout Research 2026-08-26`
- `P Continuation Failed Auction Research 2026-08-31`
- `Paper 5M ORB US100 Research 2026-09-06`
- `Patrick Nill PBD Fair Value Research 2026-08-29`
- `PEAD Validation 2026-08-10`
- `POC Fibonacci Volume Profile Research 2026-09-04`
- `Portfolio Consistency Audit 2026-09-10`
- `Portfolio Consistency Audit 2026-09-11`
- `Portfolio Daily Guard EA`
- `Portfolio Markov Gate EA`
- `Portfolio Risk Controls Research 2026-08-27`
- `Post-FOMC FX Reversal Research 2026-09-09`
- `Prop Firm Low-DD Research 2026-08-16`
- `QuantConnect Research 2026-09-07`
- `Range Breakout EA`
- `Regime Switch Overlay Research 2026-09-06`
- `Relative Value Pairs Research 2026-09-06`
- `Research Idea Bank`
- `Retest All Bots 2026-08-07`
- `Robert Rother Three VWAP Scalper Research 2026-08-16`
- `Robot Trading Playbook Research 2026-08-25`
- `Robust ORB Research 2026-09-04`
- `RSI VWAP Research 2026-09-02`
- `Selected Portfolio Audit 2026-08-28`
- `Selected Portfolio Settings 2026-09-01`
- `Sell Nasdaq 15min Research 2026-09-08`
- `Session VWAP Snapback Research 2026-09-06`
- `Shooting Star Research 2026-08-14`
- `Slow Multi Asset Trend Research 2026-09-06`
- `SP500 Existing Strategies Retest 2026-09-19`
- `Statistical Triple Print Research 2026-08-31`
- `Stock Auction Market Research 2026-08-14`
- `Stock Auction Market Research Exness 2026-08-14`
- `Sweep Engulf Continuation Research 2026-08-20`
- `The Fisherman EA`
- `Three Influencer Strategies Research 2026-08-20`
- `Time Series Momentum Raw Research 2026-09-09`
- `Time Series Momentum XAU Pipeline 2026-09-09`
- `Top Down FVG Liquidity Research 2026-08-27`
- `Trend Progression Research 2026-09-02`
- `Turnaround Tuesday EA`
- `Two Paper Standalone FTMO Research 2026-09-19`
- `US100 Closing Momentum Raw Research 2026-09-12`
- `US100 Fabio ORB Volatility Target Research 2026-08-26`
- `US100 London Close Reversal Research 2026-08-14`
- `US100 Momentum Continuation Research 2026-08-31`
- `US100 NY VWAP Bounce Research 2026-08-26`
- `US100 Overnight Optimization 2026-09-04`
- `US100 Selective ORB Research 2026-08-21`
- `USDJPY Volatility Adaptive ATR Exit Research 2026-09-09`
- `VAH Engulfing Research 2026-08-14`
- `Volatility Compression Expansion Research 2026-09-06`
- `Volume Profile POC Improvements Research 2026-08-31`
- `VWAP Third Deviation Mean Reversion Research 2026-08-16`
- `Weekend Gap Reversal Research 2026-09-08`
- `XAU Capped Recovery Research 2026-09-13`
- `XAU Closing Momentum Raw Research 2026-09-12`
- `XAU Cross Session Momentum Full Pipeline 2026-09-11`
- `XAU D14 Break Retest Full Pipeline 2026-09-13`
- `XAU Doubling Grid Raw 2026-09-13`
- `XAU M1 OCO Reel Reconstruction Research 2026-09-01`
- `XAU Markov Regime EA`
- `XAU Squeeze Momentum Research 2026-09-10`
- `XAU Weakness Bias Filter Research 2026-08-25`

## 4. Local skill source-file inventory

36 SKILL.md files observed under `C:/Users/hama101/.codex/skills`.
Includes duplicate marketplace copies and Codex system skills; not a unique exposed-skill count.
Bundled plugin-cache skills are discussed separately in CLAUDE_MCP_AND_SKILLS.md.
Do not execute or migrate any skill solely because it appears here.

- `C:/Users/hama101/.codex/skills/.system/imagegen/SKILL.md`
- `C:/Users/hama101/.codex/skills/.system/openai-docs/SKILL.md`
- `C:/Users/hama101/.codex/skills/.system/plugin-creator/SKILL.md`
- `C:/Users/hama101/.codex/skills/.system/review-agent/SKILL.md`
- `C:/Users/hama101/.codex/skills/.system/skill-creator/SKILL.md`
- `C:/Users/hama101/.codex/skills/.system/skill-installer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-comment-drafter/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-content-planner/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-employee-advocacy/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-engager-analytics/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-hook-extractor/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-humanizer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-interviewer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-post-writer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-profile-optimizer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-reply-handler/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-repurposer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/.codex-marketplace/linkedin-skills/skills/linkedin-thread-monitor/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-comment-drafter/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-content-planner/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-employee-advocacy/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-engager-analytics/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-hook-extractor/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-humanizer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-interviewer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-post-writer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-profile-optimizer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-reply-handler/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-repurposer/SKILL.md`
- `C:/Users/hama101/.codex/skills/linkedin-marketing/skills/linkedin-thread-monitor/SKILL.md`
- `C:/Users/hama101/.codex/skills/lpx-set-analyzer/SKILL.md`
- `C:/Users/hama101/.codex/skills/mt5-trading-journal/SKILL.md`
- `C:/Users/hama101/.codex/skills/regime/SKILL.md`
- `C:/Users/hama101/.codex/skills/tokenmaxxer/SKILL.md`

## 5. Documentation and evidence routing

Read in this order on first onboarding:
1. CLAUDE.md
2. CLAUDE_CODE_ONBOARDING.md
3. CLAUDE_MCP_AND_SKILLS.md
4. This file
5. CALYX_ACTIVE_EA_AND_RESEARCH_ROOT.md, applying the explicit newer corrections

Then use the task's primary artifacts:
- Portfolio/risk: canonical installer, _Shared, exact selected SETs, deployment snapshots.
- Website: EA Store README, app/catalog.py, evidence modules, tests and generated manifests.
- Gold raw: Gold Overnight Value Area EA/README.md and its verification artifacts.
- Gold optimization: Gold Overnight Value Area Pipeline 2026-09-19.
- News event settings: the dedicated XAU/v2.17 packages and matching Deployment folders.
- Prediction runtime: AI news/README.md, source/model metadata and bridge logs.
- FTMO progression: FTMO Loss Escalation Study 2026-09-20/REPORT.md and PROTOCOL.md.
- Standalone progression: Gold Value Area Loss Escalation Research 2026-09-20/REPORT.md.
- Statistical audit: AAA EAs/Calyx Research Pipeline/README.md and pipeline-policy.json.
- Crypto plan: AAA crypto arbitage/CRYPTO_ARBITRAGE_MASTER_PLAN.md.
- LTA methodology: LTA/LTA_BASE_TRADING_PROMPT.md and LTA/LTA_AGENT_FINAL_PROMPT.md.
- Social assets: social-content/calyx-ai-quant-carousel-2026-09-20/README.md and PROMPTS.md.

Other root handoffs (`BOT_AGENT_HANDOFF_PROMPT.md`, `AGENT_MCP_SETUP_PROMPT.md`,
`CONVERSATION_HANDOFF.md`, `MASTER_PROMPT.day-box-enabled.snapshot.md`) are legacy
references. Do not let their old settings/commands silently override current source or approval.

## 6. Source fingerprint anchors

SHA-256 values from the read-only handoff inspection. These identify the documentation/code
snapshot; they are NOT hashes for every compiled EA and NOT a full integrity audit.

| Root-relative file | SHA-256 |
|---|---|
| `CALYX_ACTIVE_EA_AND_RESEARCH_ROOT.md` | `1273D886B6729A907D57B7F2286080F8EB4F71A81535D51E61BD59C1CC23C687` |
| `AAA EAs/EA store/README.md` | `4D648C624D3BD9C8071A76ACECDF5254499624B2B696D9BC3902CF91558278AB` |
| `AAA EAs/BM Trading Robust Sets 2026-08-04/_Auto Deploy/Install-BMTradingPortfolio.ps1` | `1A67B53EF08A0854D2D79B5258C71BA6C76532AD5E5BB0D7135A37CEC8B65B27` |
| `AAA EAs/BM Trading Robust Sets 2026-08-04/_Shared/CalyxAdaptivePortfolio.mqh` | `3ADAECF62184CDF1568995C92DA8E6E39A69BB6392BC8BCE735E6F853DAEE06A` |

If these change, inspect the diff and refresh the handoff; do not change source to force the hash
back to this value. Artifact .gitattributes settings can matter for exact byte identity.

## 7. Known scope limitations

- No account/terminal connection or live trade audit.
- No fresh test/optimization/compile and no proof all 34 strategies are bug-free.
- No current remote/VPS/website health or Git fetch check.
- No full recursive inspection of 182 research folders' contents.
- No credentials, model weights, private telemetry or chat archives exported.
- New docs and existing untracked studies need an explicit commit/push or safe transfer to be
  available on another machine. Opening this same local folder needs no physical file move.
