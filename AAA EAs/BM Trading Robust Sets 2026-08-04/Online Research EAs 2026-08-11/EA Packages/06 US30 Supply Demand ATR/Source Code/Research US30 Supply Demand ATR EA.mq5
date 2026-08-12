#property copyright "Reproducible core reconstruction of the public US30 supply/demand ATR paper"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

input group "Paper core"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H1;
input int    InpATRPeriod=14;
input double InpImpulseBodyATR=1.0;
input double InpMinimumATRPoints=3.0;
input double InpStopBeyondZoneATR=1.0;
input double InpRewardRisk=2.0;
input int    InpSessionStartUTC=7;
input int    InpSessionEndUTC=16;
input int    InpTesterServerUTCOffsetHours=0;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input long   InpMagic=861105;
input int    InpMaxDeviationPoints=100;

datetime g_last_bar=0;
int g_atr_handle=INVALID_HANDLE;
bool g_zone_active=false;
bool g_zone_demand=false;
double g_zone_low=0.0,g_zone_high=0.0;
datetime g_zone_time=0;

int UTCHour(const datetime server_time)
{
   datetime utc=server_time;
   if((bool)MQLInfoInteger(MQL_TESTER)) utc-=InpTesterServerUTCOffsetHours*3600;
   else utc=TimeGMT()+(server_time-TimeCurrent());
   MqlDateTime p;
   TimeToStruct(utc,p);
   return p.hour;
}

bool InSession(const datetime server_time)
{
   int hour=UTCHour(server_time);
   return hour>=InpSessionStartUTC && hour<InpSessionEndUTC;
}

int OnInit()
{
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   double atr1=RT_Buffer(g_atr_handle,0,1);
   double atr2=RT_Buffer(g_atr_handle,0,2);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(atr1<=InpMinimumATRPoints*point || atr2<=0.0) return;

   datetime bar1_time=iTime(_Symbol,InpSignalTimeframe,1);
   double open1=iOpen(_Symbol,InpSignalTimeframe,1),close1=iClose(_Symbol,InpSignalTimeframe,1);
   double high1=iHigh(_Symbol,InpSignalTimeframe,1),low1=iLow(_Symbol,InpSignalTimeframe,1);

   if(g_zone_active && RT_PositionCount(_Symbol,InpMagic)==0 && bar1_time>g_zone_time)
   {
      bool invalid=(g_zone_demand ? close1<g_zone_low : close1>g_zone_high);
      bool touched=(low1<=g_zone_high && high1>=g_zone_low);
      if(invalid) g_zone_active=false;
      else if(touched)
      {
         // The paper specifies the first retest and UTC session; a touch outside
         // the session consumes the zone rather than silently using a later retest.
         g_zone_active=false;
         if(InSession(bar1_time))
         {
            MqlTick tick;
            if(SymbolInfoTick(_Symbol,tick))
            {
               if(g_zone_demand)
               {
                  double stop=RT_Price(_Symbol,g_zone_low-InpStopBeyondZoneATR*atr1);
                  double target=RT_Price(_Symbol,tick.ask+InpRewardRisk*(tick.ask-stop));
                  double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,stop,InpRiskPercent);
                  if(lots>0.0 && !ResearchTrade.Buy(lots,_Symbol,0.0,stop,target,"US30 demand retest"))
                     Print("US30 demand order failed: ",ResearchTrade.ResultRetcodeDescription());
               }
               else
               {
                  double stop=RT_Price(_Symbol,g_zone_high+InpStopBeyondZoneATR*atr1);
                  double target=RT_Price(_Symbol,tick.bid-InpRewardRisk*(stop-tick.bid));
                  double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_SELL,tick.bid,stop,InpRiskPercent);
                  if(lots>0.0 && !ResearchTrade.Sell(lots,_Symbol,0.0,stop,target,"US30 supply retest"))
                     Print("US30 supply order failed: ",ResearchTrade.ResultRetcodeDescription());
               }
            }
         }
      }
   }

   // A newly completed impulsive candle defines the next zone. The candle body
   // threshold is expressed in ATR so it transfers correctly across US30 feeds.
   double open2=iOpen(_Symbol,InpSignalTimeframe,2),close2=iClose(_Symbol,InpSignalTimeframe,2);
   double high2=iHigh(_Symbol,InpSignalTimeframe,2),low2=iLow(_Symbol,InpSignalTimeframe,2);
   if(MathAbs(close2-open2)>=InpImpulseBodyATR*atr2)
   {
      g_zone_demand=(close2>open2);
      if(g_zone_demand) { g_zone_low=low2; g_zone_high=MathMin(open2,close2); }
      else { g_zone_low=MathMax(open2,close2); g_zone_high=high2; }
      g_zone_time=iTime(_Symbol,InpSignalTimeframe,2);
      g_zone_active=(g_zone_high>g_zone_low);
   }
}
