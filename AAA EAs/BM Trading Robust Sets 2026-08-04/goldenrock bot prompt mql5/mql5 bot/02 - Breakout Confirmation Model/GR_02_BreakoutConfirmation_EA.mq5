#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
#include "..\common\GR_Common.mqh"

input long MagicNumber=510002;
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

input ENUM_TIMEFRAMES RangeTF=PERIOD_M15; input ENUM_TIMEFRAMES EntryTF=PERIOD_M5; input int LookbackBars=20; input int ATRPeriod=14; input double BufferATR=0.10; input double RewardRisk=2.0; datetime lastBar=0; CTrade trade; int hATR=INVALID_HANDLE; int OnInit(){GR_InitTrade(trade,MagicNumber,MaxSlippagePoints); hATR=iATR(_Symbol,EntryTF,ATRPeriod); return hATR==INVALID_HANDLE?INIT_FAILED:INIT_SUCCEEDED;} void OnDeinit(const int reason){if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR);} double ATR(){double b[]; ArraySetAsSeries(b,true); return CopyBuffer(hATR,0,1,1,b)==1?b[0]:0;} void OnTick(){ if(!GR_IsNewBar(lastBar,EntryTF)||!GR_SpreadOK(MaxSpreadPoints)||(OnePositionPerSymbol&&GR_HasPosition(_Symbol,MagicNumber))) return; MqlRates r[]; ArraySetAsSeries(r,true); int need=LookbackBars+3; if(CopyRates(_Symbol,RangeTF,0,need,r)<need) return; double hh=r[1].high,ll=r[1].low; for(int i=2;i<=LookbackBars;i++){ hh=MathMax(hh,r[i].high); ll=MathMin(ll,r[i].low);} double atr=ATR(); if(atr<=0) return; MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return; double buf=BufferATR*atr; if(r[1].close>hh+buf){ double sl=ll-0.2*atr; double tp=t.ask+RewardRisk*(t.ask-sl); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,t.ask-sl,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.ask,sl,tp,ORDER_TYPE_BUY)) GR_Open(trade,ORDER_TYPE_BUY,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"BreakoutConfirmation"); } if(r[1].close<ll-buf){ double sl=hh+0.2*atr; double tp=t.bid-RewardRisk*(sl-t.bid); double lots=GR_LotsFromRisk(_Symbol,RiskPercent,sl-t.bid,UseEquityRisk); if(lots>0&&GR_CheckStops(_Symbol,t.bid,sl,tp,ORDER_TYPE_SELL)) GR_Open(trade,ORDER_TYPE_SELL,lots,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"BreakoutConfirmation"); } }

/* SOURCE PROMPT SNIPPET
============================================================
GOLDENROCK - MQL5 EXPERT ADVISOR GENERATION PROMPT
============================================================

STRATEGY:
Breakout Confirmation Model

CATEGORY:
Momentum / Volatility

DIFFICULTY:
Beginner / Intermediate

AUTOMATION DIFFICULTY:
Medium

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
Breakout Confirmation Model
Category:
Momentum / Volatility
Trading Style:
Intraday
Setup Type:
Breakout
Markets:
Indices / Gold / FX
Timeframes:
M5 / M15 / H1
Difficulty:
Beginner / Intermediate
Automation Difficulty:
Medium

# PRIMARY MISSION
Convert this strategy into ONE complete MetaTrader 5 Expert Advisor written in native MQL5.
The first implementation should be deterministic, measurable, compilable, backtestable, configurable, debuggable, non-repainting, and suitable as a research baseline.

# STRICT RESPONSE BEHAVIOR
The coding AI MUST generate implementation immediately; not ask clarification questions first; not return a tutorial; not return pseudocode; not merely describe architecture; not stop at a specification; not provide Pine Script; not provide MQL4.

# AVAILABLE SETUP VARIANTS
- Range Breakout + Close Confirmation
- Breakout + Retest Acceptance
- Volatility Compression Expansion

- Range Breakout + Close Confirmation
  Setup type: Breakout
  Difficulty: Beginner / Intermediate
  Automation difficulty: Medium
  Best markets: Indices / Gold / FX
  Best timeframes: M5 / M15 / H1
  Best sessions: Best during London open or New York open.
  Market regime: Directional or expanding market with sufficient liquidity
  Entry trigger: Range Breakout + Close Confirmation: Enter after price breaks a key consolidation range or structure zone. Encode the trigger as a completed-bar boolean condition with no hindsight labels.
  Confirmation trigger: Wait for a candle close outside the range and retest or acceptance. Require a completed candle and one objective structure, close, or retest event before entry.
  Stop logic: Place the stop behind the breakout structure or retest low/high.
  Target logic: Target the expansion leg, next liquidity pool, or a 1:2 / 1:3 risk/reward scenario.
  Trade management: Scale partially at 1R and trail the remaining position.
  Avoid conditions: Avoid dead sessions and noisy low-volume ranges.
  Data requirements: Reliable OHLCV, session timestamps, spread/slippage assumptions, and enough history for regime-separated testing.
  Common weaknesses: false close outside range; spread spikes; weak breakout volume; choppy retest
  Failure modes: Signal failure: false close outside range. Log the condition and suppress duplicate entries.; Signal failure: spread spikes. Log the condition and suppress duplicate entries.; Signal failure: weak breakout volume. Log the condition and suppress duplicate entries.; Signal failure: choppy retest. Log the condition and suppress duplicate entries.
  Optimization risks: Do not tune thresholds for maximum historical profit. Freeze a baseline, constrain parameters, and reserve unseen data.
  Backtest rules: Use completed bars; one signal per setup; model spread, commission and slippage; separate regimes and sessions; report rejected signals and out-of-sample results.
  Minimum backtest sample: 100
  First-code objective: Generate a clean, backtestable baseline for Range Breakout + Close Confirmation with explicit entries, ex
*/
