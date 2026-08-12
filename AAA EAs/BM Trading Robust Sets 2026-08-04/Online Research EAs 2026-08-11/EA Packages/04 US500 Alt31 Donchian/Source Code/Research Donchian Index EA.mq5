#property copyright "Research reproduction of public Alt22 (USTEC) and Alt31 (US500) Pine strategies"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

enum DonchianVariant { ALT22_PARABOLIC=0, ALT31_FRACTIONAL=1 };

input group "Published strategy"
#ifndef RESEARCH_DONCHIAN_DEFAULT
   #define RESEARCH_DONCHIAN_DEFAULT ALT22_PARABOLIC
#endif
input DonchianVariant InpVariant=RESEARCH_DONCHIAN_DEFAULT;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_D1;
input int    InpEntryLength=55;
input int    InpATRPeriod=20;
input double InpInitialStopATR=2.0;
input double InpAddEveryATR=0.5;
input int    InpMaximumUnits=4;
input double InpTarget1ATR=3.0;
input double InpTarget2ATR=6.0;
input double InpTarget3ATR=9.0;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;

input group "Alt22 parabolic trail"
input double InpSARStep=0.02;
input double InpSARMaximum=0.20;

input group "Alt31 chandelier and break-even"
input int    InpChandelierLength=22;
input double InpChandelierATR=3.0;
input double InpBreakEvenAfterATR=2.0;

input group "Risk and execution"
input double InpRiskPercentPerFirstUnit=1.0;
input long   InpMagic=861104;
input int    InpMaxDeviationPoints=100;

datetime g_last_bar=0;
int g_atr_handle=INVALID_HANDLE;
int g_sar_handle=INVALID_HANDLE;
long g_direction=-1;
double g_entry=0.0,g_n=0.0,g_initial_stop=0.0,g_next_add=0.0,g_base_lot=0.0;
int g_units=0;
bool g_t1=false,g_t2=false,g_t3=false;

void ResetCampaign()
{
   g_direction=-1;
   g_entry=0.0; g_n=0.0; g_initial_stop=0.0; g_next_add=0.0; g_base_lot=0.0;
   g_units=0; g_t1=false; g_t2=false; g_t3=false;
}

double UnitFraction(const int unit_number)
{
   if(InpVariant==ALT22_PARABOLIC) return 1.0;
   if(unit_number<=1) return 1.0;
   if(unit_number==2) return 0.75;
   if(unit_number==3) return 0.50;
   return 0.25;
}

bool OpenUnit(const long direction,const double stop,const double fraction,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   ENUM_ORDER_TYPE order_type=(direction==POSITION_TYPE_BUY ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(direction==POSITION_TYPE_BUY ? tick.ask : tick.bid);
   double lots=RT_LotsForRisk(_Symbol,order_type,entry,
                              direction==POSITION_TYPE_BUY ? entry-InpInitialStopATR*g_n : entry+InpInitialStopATR*g_n,
                              InpRiskPercentPerFirstUnit*fraction);
   if(lots<=0.0) return false;
   bool ok=(direction==POSITION_TYPE_BUY ? ResearchTrade.Buy(lots,_Symbol,0.0,RT_Price(_Symbol,stop),0.0,comment)
                                        : ResearchTrade.Sell(lots,_Symbol,0.0,RT_Price(_Symbol,stop),0.0,comment));
   if(ok && g_units==0) g_base_lot=lots;
   if(!ok) Print("Donchian order failed: ",ResearchTrade.ResultRetcodeDescription());
   return ok;
}

int OnInit()
{
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_sar_handle=iSAR(_Symbol,InpSignalTimeframe,InpSARStep,InpSARMaximum);
   if(g_atr_handle==INVALID_HANDLE || g_sar_handle==INVALID_HANDLE) return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_sar_handle!=INVALID_HANDLE) IndicatorRelease(g_sar_handle);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   double n1=RT_Buffer(g_atr_handle,0,1);
   if(close1<=0.0 || n1<=0.0) return;
   int count=RT_PositionCount(_Symbol,InpMagic);
   if(count==0)
   {
      ResetCampaign();
      double prior_high=RT_Highest(_Symbol,InpSignalTimeframe,2,InpEntryLength);
      double prior_low=RT_Lowest(_Symbol,InpSignalTimeframe,2,InpEntryLength);
      if(prior_high==EMPTY_VALUE || prior_low==EMPTY_VALUE) return;
      MqlTick tick;
      if(!SymbolInfoTick(_Symbol,tick)) return;
      if(InpEnableLong && close1>prior_high)
      {
         g_direction=POSITION_TYPE_BUY; g_entry=tick.ask; g_n=n1;
         g_initial_stop=g_entry-InpInitialStopATR*g_n;
         if(OpenUnit(g_direction,g_initial_stop,1.0,"Donchian unit 1"))
         {
            g_units=1;
            g_next_add=g_entry+InpAddEveryATR*g_n;
         }
         else ResetCampaign();
      }
      else if(InpEnableShort && close1<prior_low)
      {
         g_direction=POSITION_TYPE_SELL; g_entry=tick.bid; g_n=n1;
         g_initial_stop=g_entry+InpInitialStopATR*g_n;
         if(OpenUnit(g_direction,g_initial_stop,1.0,"Donchian unit 1"))
         {
            g_units=1;
            g_next_add=g_entry-InpAddEveryATR*g_n;
         }
         else ResetCampaign();
      }
      return;
   }

   if(g_direction<0) g_direction=RT_PositionDirection(_Symbol,InpMagic);
   if(g_n<=0.0) g_n=n1;
   if(g_entry<=0.0)
   {
      for(int i=PositionsTotal()-1;i>=0;i--)
      {
         if(PositionGetTicket(i)>0 && RT_IsOurPosition(_Symbol,InpMagic)) { g_entry=PositionGetDouble(POSITION_PRICE_OPEN); break; }
      }
      g_initial_stop=(g_direction==POSITION_TYPE_BUY ? g_entry-InpInitialStopATR*g_n : g_entry+InpInitialStopATR*g_n);
   }

   double favorable=(g_direction==POSITION_TYPE_BUY ? close1-g_entry : g_entry-close1);
   double trailing=g_initial_stop;
   if(InpVariant==ALT22_PARABOLIC)
   {
      double sar=RT_Buffer(g_sar_handle,0,1);
      if(sar!=EMPTY_VALUE)
         trailing=(g_direction==POSITION_TYPE_BUY ? MathMax(trailing,sar) : MathMin(trailing,sar));
   }
   else
   {
      if(g_direction==POSITION_TYPE_BUY)
      {
         double chandelier=RT_Highest(_Symbol,InpSignalTimeframe,1,InpChandelierLength)-InpChandelierATR*n1;
         trailing=MathMax(trailing,chandelier);
         if(favorable>=InpBreakEvenAfterATR*g_n) trailing=MathMax(trailing,g_entry);
      }
      else
      {
         double chandelier=RT_Lowest(_Symbol,InpSignalTimeframe,1,InpChandelierLength)+InpChandelierATR*n1;
         trailing=MathMin(trailing,chandelier);
         if(favorable>=InpBreakEvenAfterATR*g_n) trailing=MathMin(trailing,g_entry);
      }
   }
   RT_ModifyAllStops(_Symbol,InpMagic,trailing);

   if(!g_t1 && favorable>=InpTarget1ATR*g_n)
   {
      RT_CloseVolume(_Symbol,InpMagic,g_base_lot,InpMaxDeviationPoints);
      g_t1=true;
   }
   if(RT_PositionCount(_Symbol,InpMagic)==0) { ResetCampaign(); return; }
   if(!g_t2 && favorable>=InpTarget2ATR*g_n)
   {
      RT_CloseVolume(_Symbol,InpMagic,g_base_lot,InpMaxDeviationPoints);
      g_t2=true;
   }
   if(RT_PositionCount(_Symbol,InpMagic)==0) { ResetCampaign(); return; }
   if(!g_t3 && favorable>=InpTarget3ATR*g_n)
   {
      RT_CloseVolume(_Symbol,InpMagic,g_base_lot,InpMaxDeviationPoints);
      g_t3=true;
   }
   if(RT_PositionCount(_Symbol,InpMagic)==0) { ResetCampaign(); return; }

   while(g_units<InpMaximumUnits &&
         (g_direction==POSITION_TYPE_BUY ? close1>=g_next_add : close1<=g_next_add))
   {
      int next_unit=g_units+1;
      if(!OpenUnit(g_direction,trailing,UnitFraction(next_unit),"Donchian pyramid")) break;
      g_units=next_unit;
      g_next_add+=(g_direction==POSITION_TYPE_BUY ? InpAddEveryATR*g_n : -InpAddEveryATR*g_n);
   }
}
