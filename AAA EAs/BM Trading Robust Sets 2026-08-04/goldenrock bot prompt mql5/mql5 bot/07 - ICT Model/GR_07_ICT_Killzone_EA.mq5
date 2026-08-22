#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
#include "..\common\GR_Common.mqh"

input long MagicNumber=510007;
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

input ENUM_TIMEFRAMES EntryTF=PERIOD_M5; input int SessionStartUTC=7; input int SessionEndUTC=11; input int ATRPeriod=14; int hATR=INVALID_HANDLE; datetime lastBar=0; CTrade trade; int OnInit(){GR_InitTrade(trade,MagicNumber,MaxSlippagePoints); hATR=iATR(_Symbol,EntryTF,ATRPeriod); return hATR==INVALID_HANDLE?INIT_FAILED:INIT_SUCCEEDED;} void OnDeinit(const int reason){if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR);} double ATR(){double b[]; ArraySetAsSeries(b,true); return CopyBuffer(hATR,0,1,1,b)==1?b[0]:0;} void OnTick(){ if(!GR_IsNewBar(lastBar,EntryTF)||!GR_SessionUTC(SessionStartUTC,SessionEndUTC)||!GR_SpreadOK(MaxSpreadPoints)||(OnePositionPerSymbol&&GR_HasPosition(_Symbol,MagicNumber))) return; MqlRates r[]; ArraySetAsSeries(r,true); if(CopyRates(_Symbol,EntryTF,0,4,r)<4) return; double atr=ATR(); if(atr<=0) return; MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return; if(r[1].close>r[2].high && r[1].close>r[1].open){ double sl=r[1].low-0.2*atr; double tp=t.ask+RewardRisk*(t.ask-sl); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,t.ask-sl,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.ask,sl,tp,ORDER_TYPE_BUY)) GR_Open(trade,ORDER_TYPE_BUY,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"ICT_Killzone"); } if(r[1].close<r[2].low && r[1].close<r[1].open){ double sl=r[1].high+0.2*atr; double tp=t.bid-RewardRisk*(sl-t.bid); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,sl-t.bid,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.bid,sl,tp,ORDER_TYPE_SELL)) GR_Open(trade,ORDER_TYPE_SELL,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"ICT_Killzone"); } }

/* SOURCE PROMPT SNIPPET
============================================================
GOLDENROCK - MQL5 EXPERT ADVISOR GENERATION PROMPT
============================================================

STRATEGY:
ICT Model

CATEGORY:
ICT / Time-Based Liquidity

DIFFICULTY:
Advanced / Institutional

AUTOMATION DIFFICULTY:
Very Hard

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
ICT Model
Category:
ICT / Time-Based Liquidity
Trading Style:
Intraday
Setup Type:
ICT
Markets:
Gold / Indices / FX
Timeframes:
Daily to M5
Difficulty:
Advanced / Institutional
Automation Difficulty:
Very Hard

# PRIMARY MISSION
Convert this strategy into ONE complete MetaTrader 5 Expert Advisor written in native MQL5.
The first implementation should be deterministic, measurable, compilable, backtestable, configurable, debuggable, non-repainting, and suitable as a research baseline.

# STRICT RESPONSE BEHAVIOR
The coding AI MUST generate implementation immediately; not ask clarification questions first; not return a tutorial; not return pseudocode; not merely describe architecture; not stop at a specification; not provide Pine Script; not provide MQL4.

# AVAILABLE SETUP VARIANTS
- Kill Zone Sweep + FVG
- Draw on Liquidity + Displacement
- OTE + Market Structure Shift
- Session Manipulation + Expansion

- Kill Zone Sweep + FVG
  Setup type: ICT
  Difficulty: Advanced / Institutional
  Automation difficulty: Very Hard
  Best markets: Gold / Indices / FX
  Best timeframes: Daily to M5
  Best sessions: London kill zone / New York kill zone.
  Market regime: Extended or liquidity-seeking market with confirmed rejection
  Entry trigger: Kill Zone Sweep + FVG: Identify the draw on liquidity, wait for kill-zone manipulation and displacement, then enter near an FVG or optimal trade entry zone. Encode the trigger as a completed-bar boolean condition with no hindsight labels.
  Confirmation trigger: Require a liquidity sweep, displacement, FVG formation, and market-structure shift. Require a completed candle and one objective structure, close, or retest event before entry.
  Stop logic: Place the stop beyond the manipulation extreme or invalidation swing.
  Target logic: Target opposing liquidity, the session-range objective, or next draw on liquidity.
  Trade management: Scale at liquidity targets and avoid holding through high-impact events without a plan.
  Avoid conditions: Avoid random FVG entries without draw-on-liquidity and timing context.
  Data requirements: Reliable OHLCV, session timestamps, spread/slippage assumptions, and enough history for regime-separated testing.
  Common weaknesses: time-window dependency; subjective draw on liquidity; random FVG entries; fails when session does not expand; hard to automate without strict definitions
  Failure modes: Signal failure: time-window dependency. Log the condition and suppress duplicate entries.; Signal failure: subjective draw on liquidity. Log the condition and suppress duplicate entries.; Signal failure: random FVG entries. Log the condition and suppress duplicate entries.; Signal failure: fails when session does not expand. Log the condition and suppress duplicate entries.; Signal failure: hard to automate without strict definitions. Log the condition and suppress duplicate entries.
  Optimization risks: Do not tune thresholds for maximum historical profit. Freeze a baseline, constrain parameters, and reserve unseen data.
  Backtest rules: 
*/
