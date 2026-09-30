#property copyright "Calyx research: raw 15m RSI mean reversion idea (heyastral.ai/u/lucas_lalk names only; rules are our own)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test (signal timeframe M15 by default):
//   Entry   : RSI(InpRSIPeriod) on the just-closed bar < InpLongBelow -> buy; > InpShortAbove -> sell.
//             Trend filter (optional): long only above EMA(InpTrendEMA), short only below it (just-closed bar close).
//   Exit    : at the next bar once RSI crosses back past InpExitLevel (long: RSI > 50; short: RSI < 50),
//             or after InpMaxHoldBars bars. No take profit.
//   Stop    : InpStopATR x ATR(InpATRPeriod) from entry. One position at a time; 1% risk to the stop.
//   Control : InpEntryMode=1 -> same trend condition and stop, entry on ~InpControlPercent% of bars chosen by a
//             deterministic hash of the bar time (RSI ignored), exit after InpControlHoldBars bars (or stop).

enum ENUM_RSI_ENTRY { RSI_ENTRY_SIGNAL=0, RSI_ENTRY_CONTROL_RANDOM=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1092503;
input bool   InpAdaptivePortfolioControls=false;

input group "RSI mean reversion rules"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input ENUM_RSI_ENTRY  InpEntryMode=RSI_ENTRY_SIGNAL;
input int    InpRSIPeriod=2;
input double InpLongBelow=10.0;
input double InpShortAbove=90.0;
input double InpExitLevel=50.0;
input bool   InpUseTrendFilter=true;
input int    InpTrendEMA=200;
input double InpStopATR=3.0;
input int    InpATRPeriod=14;
input int    InpMaxHoldBars=16;
input int    InpControlPercent=5;
input int    InpControlHoldBars=4;
input double InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_rsi_last_bar=0;
int g_rsi_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpStopATR<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_rsi_handle=iRSI(_Symbol,InpSignalTimeframe,InpRSIPeriod,PRICE_CLOSE);
   g_ema_handle=iMA(_Symbol,InpSignalTimeframe,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_rsi_handle==INVALID_HANDLE || g_ema_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(g_rsi_handle);
   IndicatorRelease(g_ema_handle);
   IndicatorRelease(g_atr_handle);
}

bool RSI_ControlPicks(const datetime bar_time)
{
   ulong x=(ulong)(bar_time/PeriodSeconds(InpSignalTimeframe));
   x=(x*2654435761)%1000003;
   return (int)(x%100)<InpControlPercent;
}

void RSI_ManagePosition(const double rsi)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      int held=Bars(_Symbol,InpSignalTimeframe,(datetime)PositionGetInteger(POSITION_TIME),TimeCurrent())-1;
      bool exit_now;
      if(InpEntryMode==RSI_ENTRY_CONTROL_RANDOM)
         exit_now=held>=InpControlHoldBars;
      else
         exit_now=held>=InpMaxHoldBars ||
                  (type==POSITION_TYPE_BUY && rsi>InpExitLevel) || (type==POSITION_TYPE_SELL && rsi<InpExitLevel);
      if(exit_now)
        {
         AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
         AAA_Trade.PositionClose(ticket);
        }
     }
}

void OnTick()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_rsi_last_bar) || !InpEnableTrading) return;
   double rsi=AAA_BufferValue(g_rsi_handle,0,1);
   double ema=AAA_BufferValue(g_ema_handle,0,1);
   double atr=AAA_BufferValue(g_atr_handle,0,1);
   if(rsi==EMPTY_VALUE || ema==EMPTY_VALUE || atr==EMPTY_VALUE || atr<=0.0) return;
   RSI_ManagePosition(rsi);
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   if(close1<=0.0) return;

   int direction=0;
   if(InpEntryMode==RSI_ENTRY_SIGNAL)
     {
      if(rsi<InpLongBelow && (!InpUseTrendFilter || close1>ema)) direction=1;
      else if(rsi>InpShortAbove && (!InpUseTrendFilter || close1<ema)) direction=-1;
     }
   else if(RSI_ControlPicks(iTime(_Symbol,InpSignalTimeframe,1)))
      direction=(close1>ema ? 1 : -1);
   if(direction==0 || !DTS_EntrySessionAllowed()) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=AAA_Price(_Symbol,entry-direction*InpStopATR*atr);
   if(MathAbs(entry-sl)<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return;
   double lots=AAA_LotsForRisk(_Symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),entry,sl,InpRiskPercent);
   if(lots<=0.0) return;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(20);
   string comment=(InpEntryMode==RSI_ENTRY_SIGNAL ? "RSI15 " : "RSI15 control ")+(direction>0 ? "long" : "short");
   if(direction>0) AAA_Trade.Buy(lots,_Symbol,0.0,sl,0.0,comment);
   else AAA_Trade.Sell(lots,_Symbol,0.0,sl,0.0,comment);
}
