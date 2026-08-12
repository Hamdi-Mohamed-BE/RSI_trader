#property copyright "Research reproduction of the Mechanical Forex Keltner breakout"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

input group "Published strategy"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_D1;
input int    InpKeltnerMAPeriod=250;
input int    InpKeltnerATRPeriod=10;
input double InpKeltnerATRMultiplier=2.5;
input int    InpExitMAPeriod=175;
input int    InpStopATRPeriod=14;
input double InpStopATRMultiplier=2.0;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input long   InpMagic=861101;
input int    InpMaxDeviationPoints=50;

datetime g_last_bar=0;
int g_mid_handle=INVALID_HANDLE;
int g_channel_atr_handle=INVALID_HANDLE;
int g_exit_handle=INVALID_HANDLE;
int g_stop_atr_handle=INVALID_HANDLE;

int OnInit()
{
   g_mid_handle=iMA(_Symbol,InpSignalTimeframe,InpKeltnerMAPeriod,0,MODE_SMA,PRICE_TYPICAL);
   g_channel_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpKeltnerATRPeriod);
   g_exit_handle=iMA(_Symbol,InpSignalTimeframe,InpExitMAPeriod,0,MODE_SMA,PRICE_CLOSE);
   g_stop_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpStopATRPeriod);
   if(g_mid_handle==INVALID_HANDLE || g_channel_atr_handle==INVALID_HANDLE ||
      g_exit_handle==INVALID_HANDLE || g_stop_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_mid_handle!=INVALID_HANDLE) IndicatorRelease(g_mid_handle);
   if(g_channel_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_channel_atr_handle);
   if(g_exit_handle!=INVALID_HANDLE) IndicatorRelease(g_exit_handle);
   if(g_stop_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_stop_atr_handle);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   double mid=RT_Buffer(g_mid_handle,0,1);
   double channel_atr=RT_Buffer(g_channel_atr_handle,0,1);
   double exit_ma=RT_Buffer(g_exit_handle,0,1);
   double stop_atr=RT_Buffer(g_stop_atr_handle,0,1);
   if(close1<=0.0 || mid==EMPTY_VALUE || channel_atr<=0.0 || exit_ma==EMPTY_VALUE || stop_atr<=0.0) return;

   long direction=RT_PositionDirection(_Symbol,InpMagic);
   if(direction==POSITION_TYPE_BUY && close1<exit_ma) { RT_CloseAll(_Symbol,InpMagic,InpMaxDeviationPoints); return; }
   if(direction==POSITION_TYPE_SELL && close1>exit_ma) { RT_CloseAll(_Symbol,InpMagic,InpMaxDeviationPoints); return; }
   if(direction>=0) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double upper=mid+InpKeltnerATRMultiplier*channel_atr;
   double lower=mid-InpKeltnerATRMultiplier*channel_atr;
   if(InpEnableLong && close1>upper && close1>exit_ma)
   {
      double stop=RT_Price(_Symbol,tick.ask-InpStopATRMultiplier*stop_atr);
      double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,stop,InpRiskPercent);
      if(lots>0.0 && !ResearchTrade.Buy(lots,_Symbol,0.0,stop,0.0,"Keltner long"))
         Print("Keltner buy failed: ",ResearchTrade.ResultRetcodeDescription());
   }
   else if(InpEnableShort && close1<lower && close1<exit_ma)
   {
      double stop=RT_Price(_Symbol,tick.bid+InpStopATRMultiplier*stop_atr);
      double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_SELL,tick.bid,stop,InpRiskPercent);
      if(lots>0.0 && !ResearchTrade.Sell(lots,_Symbol,0.0,stop,0.0,"Keltner short"))
         Print("Keltner sell failed: ",ResearchTrade.ResultRetcodeDescription());
   }
}
