#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
#include "..\common\GR_Common.mqh"

input long MagicNumber=510004;
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

input ENUM_TIMEFRAMES ContextTF=PERIOD_H4; input ENUM_TIMEFRAMES EntryTF=PERIOD_M15; input int FastEMAPeriod=20; input int SlowEMAPeriod=50; input int ATRPeriod=14; int hFast=INVALID_HANDLE,hSlow=INVALID_HANDLE,hATR=INVALID_HANDLE; datetime lastBar=0; CTrade trade; int OnInit(){GR_InitTrade(trade,MagicNumber,MaxSlippagePoints); hFast=iMA(_Symbol,ContextTF,FastEMAPeriod,0,MODE_EMA,PRICE_CLOSE); hSlow=iMA(_Symbol,ContextTF,SlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE); hATR=iATR(_Symbol,EntryTF,ATRPeriod); return(hFast==INVALID_HANDLE||hSlow==INVALID_HANDLE||hATR==INVALID_HANDLE)?INIT_FAILED:INIT_SUCCEEDED;} void OnDeinit(const int reason){if(hFast!=INVALID_HANDLE)IndicatorRelease(hFast); if(hSlow!=INVALID_HANDLE)IndicatorRelease(hSlow); if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR);} int Bias(){double f[],s[]; ArraySetAsSeries(f,true); ArraySetAsSeries(s,true); if(CopyBuffer(hFast,0,1,1,f)!=1||CopyBuffer(hSlow,0,1,1,s)!=1) return 0; return f[0]>s[0]?1:f[0]<s[0]?-1:0;} double ATR(){double b[]; ArraySetAsSeries(b,true); return CopyBuffer(hATR,0,1,1,b)==1?b[0]:0;} void OnTick(){ if(!GR_IsNewBar(lastBar,EntryTF)||!GR_SpreadOK(MaxSpreadPoints)||(OnePositionPerSymbol&&GR_HasPosition(_Symbol,MagicNumber))) return; int b=Bias(); if(b==0) return; MqlRates r[]; ArraySetAsSeries(r,true); if(CopyRates(_Symbol,EntryTF,0,5,r)<5) return; double atr=ATR(); if(atr<=0) return; MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return; double mid=(r[1].high+r[1].low+r[1].close)/3.0; if(b>0 && r[1].low<=mid && r[1].close>r[1].open){ double sl=r[1].low-0.2*atr; double tp=t.ask+RewardRisk*(t.ask-sl); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,t.ask-sl,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.ask,sl,tp,ORDER_TYPE_BUY)) GR_Open(trade,ORDER_TYPE_BUY,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"MTFInstitutional"); } if(b<0 && r[1].high>=mid && r[1].close<r[1].open){ double sl=r[1].high+0.2*atr; double tp=t.bid-RewardRisk*(sl-t.bid); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,sl-t.bid,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.bid,sl,tp,ORDER_TYPE_SELL)) GR_Open(trade,ORDER_TYPE_SELL,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"MTFInstitutional"); } }

/* SOURCE PROMPT SNIPPET
============================================================
GOLDENROCK - MQL5 EXPERT ADVISOR GENERATION PROMPT
============================================================

STRATEGY:
Multi-Timeframe Institutional Setup

CATEGORY:
Institutional Structure

DIFFICULTY:
Advanced

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
Multi-Timeframe Institutional Setup
Category:
Institutional Structure
Trading Style:
Intraday / Swing
Setup Type:
Institutional Structure
Markets:
Gold / FX / Indices
Timeframes:
H4 to M5 stack
Difficulty:
Advanced
Automation Difficulty:
Hard

# PRIMARY MISSION
Convert this strategy into ONE complete MetaTrader 5 Expert Advisor written in native MQL5.
The first implementation should be deterministic, measurable, compilable, backtestable, configurable, debuggable, non-repainting, and suitable as a research baseline.

# STRICT RESPONSE BEHAVIOR
The coding AI MUST generate implementation immediately; not ask clarification questions first; not return a tutorial; not return pseudocode; not merely describe architecture; not stop at a specification; not provide Pine Script; not provide MQL4.

# AVAILABLE SETUP VARIANTS
- HTF Bias + LTF Execution Shift
- Premium / Discount + Structure Confirmation
- Liquidity Zone + Session Trigger

- HTF Bias + LTF Execution Shift
  Setup type: Institutional Structure
  Difficulty: Advanced
  Automation difficulty: Hard
  Best markets: Gold / FX / Indices
  Best timeframes: H4 to M5 stack
  Best sessions: Trade only in planned high-liquidity sessions.
  Market regime: Directional or expanding market with sufficient liquidity
  Entry trigger: HTF Bias + LTF Execution Shift: Trade with higher-timeframe bias after price reaches premium/discount or a major liquidity zone. Encode the trigger as a completed-bar boolean condition with no hindsight labels.
  Confirmation trigger: Require a break of structure, displacement, or lower-timeframe reclaim. Require a completed candle and one objective structure, close, or retest event before entry.
  Stop logic: Place the stop beyond the execution swing or invalidation zone.
  Target logic: Target liquidity pools, imbalance completion, or the next HTF objective.
  Trade management: Reduce exposure into news and manage by structure progression.
  Avoid conditions: Avoid entries without HTF and LTF alignment.
  Data requirements: Reliable OHLCV, session timestamps, spread/slippage assumptions, and enough history for regime-separated testing.
  Common weaknesses: conflicting timeframes; delayed confirmation; too much discretionary interpretation; hard automation if HTF bias is vague
  Failure modes: Signal failure: conflicting timeframes. Log the condition and suppress duplicate entries.; Signal failure: delayed confirmation. Log the condition and suppress duplicate entries.; Signal failure: too much discretionary interpretation. Log the condition and suppress duplicate entries.; Signal failure: hard automation if HTF bias is vague. Log the condition and suppress duplicate entries.
  Optimization risks: Do not tune thresholds for maximum historical profit. Freeze a baseline, constrain parameters, and reserve unseen data.
  Backtest rules: Use completed bars; one signal per setup; model spread, commission and slippage; separate regimes and sessions; report rejected signals and out-of-sample results.
  Minimum backtest sample: 100
  Fir
*/
