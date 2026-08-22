#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
#include "..\common\GR_Common.mqh"

input long MagicNumber=510003;
input int MaxSpreadPoints=35;
input int MaxSlippagePoints=10;
input bool OnePositionPerSymbol=true;
input double RiskPercent=0.5;
input bool UseEquityRisk=true;
input double RewardRisk=2.0;
input bool UseSessionFilter=false;
input int SessionStartHourUTC=7;
input int SessionEndHourUTC=17;
input bool UseManualNewsFilter=false;
input string BlockedNewsTimesServer="";
input int NewsBlockMinutes=30;

input ENUM_TIMEFRAMES LiquidityTF=PERIOD_M15; input ENUM_TIMEFRAMES EntryTF=PERIOD_M5; input int LookbackBars=180; input int ATRPeriod=14; input double EqualToleranceATR=0.12; input double SweepATR=0.08; input double WickPercent=45.0; datetime lastBar=0,lastSignal=0; CTrade trade; int hATR=INVALID_HANDLE; int OnInit(){GR_InitTrade(trade,MagicNumber,MaxSlippagePoints); hATR=iATR(_Symbol,EntryTF,ATRPeriod); return hATR==INVALID_HANDLE?INIT_FAILED:INIT_SUCCEEDED;} void OnDeinit(const int reason){if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR);} double ATR(){double b[]; ArraySetAsSeries(b,true); return CopyBuffer(hATR,0,1,1,b)==1?b[0]:0;} bool HighPool(double &p){ MqlRates r[]; ArraySetAsSeries(r,true); int n=CopyRates(_Symbol,LiquidityTF,0,LookbackBars,r); if(n<30) return false; for(int i=10;i<n-10;i++){ bool h=true; for(int j=1;j<=3;j++) if(r[i].high<=r[i-j].high||r[i].high<=r[i+j].high) h=false; if(h){ p=r[i].high; return true; } } return false; } bool LowPool(double &p){ MqlRates r[]; ArraySetAsSeries(r,true); int n=CopyRates(_Symbol,LiquidityTF,0,LookbackBars,r); if(n<30) return false; for(int i=10;i<n-10;i++){ bool l=true; for(int j=1;j<=3;j++) if(r[i].low>=r[i-j].low||r[i].low>=r[i+j].low) l=false; if(l){ p=r[i].low; return true; } } return false; } void OnTick(){ if(!GR_IsNewBar(lastBar,EntryTF)||!GR_SpreadOK(MaxSpreadPoints)||(UseManualNewsFilter&&GR_ManualNewsBlackout(BlockedNewsTimesServer,NewsBlockMinutes))||(OnePositionPerSymbol&&GR_HasPosition(_Symbol,MagicNumber))) return; MqlRates r[]; ArraySetAsSeries(r,true); if(CopyRates(_Symbol,EntryTF,0,4,r)<4) return; double atr=ATR(); if(atr<=0) return; MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return; double hp,lp; bool hasH=HighPool(hp), hasL=LowPool(lp); if(hasH && r[1].high>hp+SweepATR*atr && r[1].close<hp && r[1].time!=lastSignal){ double wick=(r[1].high-MathMax(r[1].open,r[1].close))/MathMax(r[1].high-r[1].low,_Point)*100.0; if(wick>=WickPercent){ double sl=hp+0.2*atr; double tp=t.bid-RewardRisk*(sl-t.bid); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,sl-t.bid,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.bid,sl,tp,ORDER_TYPE_SELL)){ GR_Open(trade,ORDER_TYPE_SELL,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"LiquiditySweepReversal"); lastSignal=r[1].time; } } } if(hasL && r[1].low<lp-SweepATR*atr && r[1].close>lp && r[1].time!=lastSignal){ double wick=(MathMin(r[1].open,r[1].close)-r[1].low)/MathMax(r[1].high-r[1].low,_Point)*100.0; if(wick>=WickPercent){ double sl=lp-0.2*atr; double tp=t.ask+RewardRisk*(t.ask-sl); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,t.ask-sl,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.ask,sl,tp,ORDER_TYPE_BUY)){ GR_Open(trade,ORDER_TYPE_BUY,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"LiquiditySweepReversal"); lastSignal=r[1].time; } } } }

/* SOURCE PROMPT SNIPPET
============================================================
GOLDENROCK - MQL5 EXPERT ADVISOR GENERATION PROMPT
============================================================

STRATEGY:
Liquidity Sweep Reversal

CATEGORY:
Liquidity / Reversal

DIFFICULTY:
Intermediate

AUTOMATION DIFFICULTY:
Hard

TARGET:
MetaTrader 5 / MQL5 Expert Advisor

OUTPUT MODE:
Direct Complete Code

VERSION:
Baseline V1
============================================================

You are a senior quantitative trading-system architect, institutional market-structure researcher, execution engineer, and senior MQL5 developer specializing in MetaTrader 5 Expert Advisors.

You combine discretionary trading logic with deterministic systematic implementation.

Your responsibility is to convert the strategy specification below into a complete, compilable, testable MT5 Expert Advisor.

Do not ask me questions before the first implementation.
If any strategy component remains subjective or underspecified, choose a conservative deterministic baseline implementation, expose the meaningful threshold as an MQL5 input when appropriate, document the assumption briefly in the source code, and continue.
Generate the complete Expert Advisor now.
Do not return pseudocode.
Do not return an implementation plan instead of code.
Do not leave TODO sections.
Do not omit functions because they are complex.
Do not silently invent unavailable market data.
Return a complete baseline .mq5 Expert Advisor suitable for compilation and Strategy Tester research.

FINAL RESPONSE CONTRACT

Return exactly:
1. Filename
2. One complete MQL5 code block
3. Compact Implementation Notes only if technically necessary

The MQL5 source code is the primary deliverable.
Do not provide a long explanation before the code.
Do not ask clarification questions.
Do not provide pseudocode.
Do not provide incomplete fragments.
Do not use TODO placeholders.

# STRATEGY IDENTITY
Strategy Name:
Liquidity Sweep Reversal
Category:
Liquidity / Reversal
Trading Style:
Intraday / Swing
Setup Type:
Liquidity Sweep
Markets:
Gold / FX / US30
Timeframes:
M5 / M15 / H1
Difficulty:
Intermediate
Automation Difficulty:
Hard

# PRIMARY MISSION
Convert this strategy into ONE complete MetaTrader 5 Expert Advisor written in native MQL5.
The first implementation should be deterministic, measurable, compilable, backtestable, configurable, debuggable, non-repainting, and suitable as a research baseline.

# STRICT RESPONSE BEHAVIOR
The coding AI MUST generate implementation immediately; not ask clarification questions first; not return a tutorial; not return pseudocode; not merely describe architecture; not stop at a specification; not provide Pine Script; not provide MQL4.

# AVAILABLE SETUP VARIANTS
- Buy-Side Liquidity Sweep Sell
- Sell-Side Liquidity Sweep Buy
- Sweep + Market Structure Shift + Retest
- Double Sweep Reversal

- Buy-Side Liquidity Sweep Sell
  Setup type: Liquidity Sweep
  Difficulty: Intermediate
  Automation difficulty: Hard
  Best markets: Gold / FX / US30
  Best timeframes: M5 / M15 / H1
  Best sessions: Best during London and New York high-liquidity sessions.
  Market regime: Extended or liquidity-seeking market with confirmed rejection
  Entry trigger: Buy-Side Liquidity Sweep Sell: Look for a sweep of external liquidity above highs or below lows, followed by rejection. Encode the trigger as a completed-bar boolean condition with no hindsight labels.
  Confirmation trigger: Wait for a reclaim of internal structure or a break in the opposite direction. Require a completed candle and one objective structure, close, or retest event before entry.
  Stop logic: Place the stop beyond the sweep extreme.
  Target logic: Target internal liquidity first, then opposite-side liquidity.
  Trade management: Take a partial at the first target and hold the remainder for a structure move.
  Avoid conditions: Avoid random mid-range entries without a clear sweep.
  Data requirements: Reliable OHLCV, session timestamps, spread/slippage assumptions, and enough history for regime-separated testing.
  Common weaknesses: sweep becomes real breakout; unclear rejection; early short before confirmation
  Failure modes: Signal failure: sweep becomes real breakout. Log the condition and suppress duplicate entries.; Signal failure: unclear rejection. Log the condition and suppress duplicate entries.; Signal failure: early short before confirmation. Log the condition and suppress duplicate entries.
  Optimization risks: Do not tune thresholds for maximum historical profit. Freeze a baseline, constrain parameters, and reserve unseen data.
  Backtest rules: Use completed bars; one signal per setup; model spread, commission and slippage; separate regimes and sessions; report rejected signals and out-of-sample results.
  Minimum backtest sample: 100
  First-code objective: Generate a clean, backtestable baseline for Buy-Side Liquidity Sweep Sell with explicit entries, exits, stops, targets, session filters, and diagnostic 
*/
