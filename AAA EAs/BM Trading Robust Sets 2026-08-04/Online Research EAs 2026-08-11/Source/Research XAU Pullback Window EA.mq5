#property copyright "Research reproduction of the public Sunrise Ogle XAU pullback-window rules"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

input group "Published signal and pullback"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int    InpFastEMAPeriod=14;
input int    InpSlowEMAPeriod=24;
input int    InpTrendEMAPeriod=100;
input int    InpATRPeriod=10;
input int    InpBearishPullbackBars=3;
input int    InpBreakoutWindowBars=1;
input double InpChannelPaddingFraction=0.001;
input double InpMinATR=0.0;
input double InpMaxATR=2.0;
input bool   InpUseATRIncrementFilter=true;
input double InpMinATRIncrement=0.2;
input double InpMaxATRIncrement=1.6;

input group "Published exits and risk"
input double InpStopATRMultiplier=4.5;
input double InpTargetATRMultiplier=6.5;
input double InpRiskPercent=1.0;
input long   InpMagic=861102;
input int    InpMaxDeviationPoints=100;

enum PullbackState { SCANNING=0, WAITING_PULLBACK=1, WAITING_BREAKOUT=2 };
PullbackState g_state=SCANNING;
int g_bearish_count=0;
int g_window_age=0;
double g_signal_atr=0.0;
double g_channel_high=0.0;
double g_channel_low=0.0;
datetime g_last_bar=0;
int g_fast_handle=INVALID_HANDLE;
int g_slow_handle=INVALID_HANDLE;
int g_trend_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;

void ResetSetup()
{
   g_state=SCANNING;
   g_bearish_count=0;
   g_window_age=0;
   g_signal_atr=0.0;
   g_channel_high=0.0;
   g_channel_low=0.0;
}

int OnInit()
{
   g_fast_handle=iMA(_Symbol,InpSignalTimeframe,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_slow_handle=iMA(_Symbol,InpSignalTimeframe,InpSlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_trend_handle=iMA(_Symbol,InpSignalTimeframe,InpTrendEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast_handle==INVALID_HANDLE || g_slow_handle==INVALID_HANDLE ||
      g_trend_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_handle);
   if(g_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_handle);
   if(g_trend_handle!=INVALID_HANDLE) IndicatorRelease(g_trend_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   if(RT_PositionCount(_Symbol,InpMagic)>0) { ResetSetup(); return; }

   double open1=iOpen(_Symbol,InpSignalTimeframe,1);
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   double high1=iHigh(_Symbol,InpSignalTimeframe,1);
   double low1=iLow(_Symbol,InpSignalTimeframe,1);
   double fast1=RT_Buffer(g_fast_handle,0,1);
   double fast2=RT_Buffer(g_fast_handle,0,2);
   double slow1=RT_Buffer(g_slow_handle,0,1);
   double slow2=RT_Buffer(g_slow_handle,0,2);
   double trend1=RT_Buffer(g_trend_handle,0,1);
   double atr1=RT_Buffer(g_atr_handle,0,1);
   if(close1<=0.0 || atr1<=0.0 || fast1==EMPTY_VALUE || slow1==EMPTY_VALUE || trend1==EMPTY_VALUE) return;

   if(g_state==SCANNING)
   {
      bool crossed=(fast2<=slow2 && fast1>slow1);
      if(crossed && close1>trend1 && atr1>=InpMinATR && (InpMaxATR<=0.0 || atr1<=InpMaxATR))
      {
         g_state=WAITING_PULLBACK;
         g_signal_atr=atr1;
         g_bearish_count=0;
      }
      return;
   }

   if(g_state==WAITING_PULLBACK)
   {
      if(close1<open1) g_bearish_count++;
      else { ResetSetup(); return; }
      if(g_bearish_count>=InpBearishPullbackBars)
      {
         double range=MathMax(high1-low1,SymbolInfoDouble(_Symbol,SYMBOL_POINT));
         g_channel_high=high1+range*InpChannelPaddingFraction;
         g_channel_low=low1-range*InpChannelPaddingFraction;
         g_window_age=0;
         g_state=WAITING_BREAKOUT;
      }
      return;
   }

   if(g_state!=WAITING_BREAKOUT) return;
   g_window_age++;
   if(low1<=g_channel_low || g_window_age>InpBreakoutWindowBars) { ResetSetup(); return; }
   if(high1<g_channel_high) return;

   double increment=atr1-g_signal_atr;
   if(InpUseATRIncrementFilter && (increment<InpMinATRIncrement || increment>InpMaxATRIncrement))
   {
      ResetSetup();
      return;
   }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) { ResetSetup(); return; }
   double stop=RT_Price(_Symbol,low1-InpStopATRMultiplier*atr1);
   double target=RT_Price(_Symbol,high1+InpTargetATRMultiplier*atr1);
   double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,stop,InpRiskPercent);
   if(lots>0.0 && !ResearchTrade.Buy(lots,_Symbol,0.0,stop,target,"XAU pullback window"))
      Print("XAU pullback buy failed: ",ResearchTrade.ResultRetcodeDescription());
   ResetSetup();
}
