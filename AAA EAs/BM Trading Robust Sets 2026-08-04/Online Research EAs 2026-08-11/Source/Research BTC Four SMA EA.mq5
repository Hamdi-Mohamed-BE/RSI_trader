#property copyright "Research implementation of the Four-SMA Crossover in Mathematics 2026 14(1) 69"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

input group "Paper parameters (all optimized in the published ranges)"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int    InpLongFastSMA=10;
input int    InpLongSlowSMA=40;
input int    InpShortFastSMA=20;
input int    InpShortSlowSMA=80;
input double InpLongTakeProfitFactor=1.03;
input double InpLongStopLossFactor=0.97;
input double InpShortTakeProfitFactor=0.97;
input double InpShortStopLossFactor=1.03;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input long   InpMagic=861103;
input int    InpMaxDeviationPoints=200;

datetime g_last_bar=0;
int g_lf=INVALID_HANDLE,g_ls=INVALID_HANDLE,g_sf=INVALID_HANDLE,g_ss=INVALID_HANDLE;
double g_extreme=0.0;
double g_trailing_tp=0.0;
double g_trailing_sl=0.0;
long g_tracked_direction=-1;

void ResetTradeState()
{
   g_extreme=0.0;
   g_trailing_tp=0.0;
   g_trailing_sl=0.0;
   g_tracked_direction=-1;
}

int OnInit()
{
   g_lf=iMA(_Symbol,InpSignalTimeframe,InpLongFastSMA,0,MODE_SMA,PRICE_CLOSE);
   g_ls=iMA(_Symbol,InpSignalTimeframe,InpLongSlowSMA,0,MODE_SMA,PRICE_CLOSE);
   g_sf=iMA(_Symbol,InpSignalTimeframe,InpShortFastSMA,0,MODE_SMA,PRICE_CLOSE);
   g_ss=iMA(_Symbol,InpSignalTimeframe,InpShortSlowSMA,0,MODE_SMA,PRICE_CLOSE);
   if(g_lf==INVALID_HANDLE || g_ls==INVALID_HANDLE || g_sf==INVALID_HANDLE || g_ss==INVALID_HANDLE) return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_lf!=INVALID_HANDLE) IndicatorRelease(g_lf);
   if(g_ls!=INVALID_HANDLE) IndicatorRelease(g_ls);
   if(g_sf!=INVALID_HANDLE) IndicatorRelease(g_sf);
   if(g_ss!=INVALID_HANDLE) IndicatorRelease(g_ss);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   if(close1<=0.0) return;
   long direction=RT_PositionDirection(_Symbol,InpMagic);

   if(direction>=0)
   {
      if(g_tracked_direction!=direction || g_extreme<=0.0)
      {
         double entry=0.0;
         for(int i=PositionsTotal()-1;i>=0;i--)
         {
            if(PositionGetTicket(i)>0 && RT_IsOurPosition(_Symbol,InpMagic)) { entry=PositionGetDouble(POSITION_PRICE_OPEN); break; }
         }
         g_tracked_direction=direction;
         g_extreme=entry;
         if(direction==POSITION_TYPE_BUY)
         {
            g_trailing_tp=entry*InpLongTakeProfitFactor;
            g_trailing_sl=entry*InpLongStopLossFactor;
         }
         else
         {
            g_trailing_tp=entry*InpShortTakeProfitFactor;
            g_trailing_sl=entry*InpShortStopLossFactor;
         }
      }

      bool exit_now=(direction==POSITION_TYPE_BUY ? (close1>=g_trailing_tp || close1<=g_trailing_sl)
                                                   : (close1<=g_trailing_tp || close1>=g_trailing_sl));
      if(exit_now)
      {
         RT_CloseAll(_Symbol,InpMagic,InpMaxDeviationPoints);
         ResetTradeState();
         return;
      }

      if(direction==POSITION_TYPE_BUY && close1>g_extreme)
      {
         g_extreme=close1;
         g_trailing_tp=g_extreme*InpLongTakeProfitFactor;
         g_trailing_sl=g_extreme*InpLongStopLossFactor;
         RT_ModifyAllStops(_Symbol,InpMagic,g_trailing_sl);
      }
      else if(direction==POSITION_TYPE_SELL && close1<g_extreme)
      {
         g_extreme=close1;
         g_trailing_tp=g_extreme*InpShortTakeProfitFactor;
         g_trailing_sl=g_extreme*InpShortStopLossFactor;
         RT_ModifyAllStops(_Symbol,InpMagic,g_trailing_sl);
      }
      return;
   }

   ResetTradeState();
   double lf1=RT_Buffer(g_lf,0,1),lf2=RT_Buffer(g_lf,0,2);
   double ls1=RT_Buffer(g_ls,0,1),ls2=RT_Buffer(g_ls,0,2);
   double sf1=RT_Buffer(g_sf,0,1),sf2=RT_Buffer(g_sf,0,2);
   double ss1=RT_Buffer(g_ss,0,1),ss2=RT_Buffer(g_ss,0,2);
   if(lf1==EMPTY_VALUE || ls1==EMPTY_VALUE || sf1==EMPTY_VALUE || ss1==EMPTY_VALUE) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;

   if(InpEnableLong && lf2<=ls2 && lf1>ls1)
   {
      double stop=RT_Price(_Symbol,tick.ask*InpLongStopLossFactor);
      double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,stop,InpRiskPercent);
      if(lots>0.0 && ResearchTrade.Buy(lots,_Symbol,0.0,stop,0.0,"BTC Four-SMA long"))
      {
         g_tracked_direction=POSITION_TYPE_BUY;
         g_extreme=tick.ask;
         g_trailing_tp=tick.ask*InpLongTakeProfitFactor;
         g_trailing_sl=stop;
      }
   }
   else if(InpEnableShort && sf2>=ss2 && sf1<ss1)
   {
      double stop=RT_Price(_Symbol,tick.bid*InpShortStopLossFactor);
      double lots=RT_LotsForRisk(_Symbol,ORDER_TYPE_SELL,tick.bid,stop,InpRiskPercent);
      if(lots>0.0 && ResearchTrade.Sell(lots,_Symbol,0.0,stop,0.0,"BTC Four-SMA short"))
      {
         g_tracked_direction=POSITION_TYPE_SELL;
         g_extreme=tick.bid;
         g_trailing_tp=tick.bid*InpShortTakeProfitFactor;
         g_trailing_sl=stop;
      }
   }
}
