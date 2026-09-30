#property copyright "Calyx research: 'ATR Touch' - long when the lower wick touches a 3.1 x ATR band (IQ Capital reel, trader MNQ)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test (reel: long only, no other filter, resting limit that follows the band):
//   Band   : lower = close[1] - InpBandATR x ATR(InpATRPeriod)[1] on the signal timeframe (recomputed every new bar).
//   Entry  : one buy limit at the band, re-placed at every new bar while flat (the "dynamically updating" limit).
//   Exit   : stop InpStopATR x ATR below the limit price, target InpRewardRisk x that distance, time stop InpMaxBars bars.
//   Control: InpEntryMode=1 -> market buy on ~InpControlPer1000 / 1000 of bars (deterministic hash), same stop/target/time stop.
//   One position at a time; long only; 1% equity risk to the stop (lots rounded up per portfolio policy).

enum ENUM_AT_ENTRY { AT_ENTRY_BAND_LIMIT=0, AT_ENTRY_CONTROL_RANDOM=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1092508;
input bool   InpAdaptivePortfolioControls=false;

input group "ATR touch"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input ENUM_AT_ENTRY   InpEntryMode=AT_ENTRY_BAND_LIMIT;
input int    InpATRPeriod=14;
input double InpBandATR=3.1;
input double InpStopATR=1.0;
input double InpRewardRisk=1.0;
input int    InpMaxBars=48;
input int    InpControlPer1000=10;
input double InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_at_last_bar=0;
int g_atr=INVALID_HANDLE;

int OnInit()
{
   if(InpBandATR<=0.0 || InpStopATR<=0.0 || InpRewardRisk<=0.0 || InpRiskPercent<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   return (g_atr==INVALID_HANDLE ? INIT_FAILED : INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { IndicatorRelease(g_atr); }

void AT_DeleteOrders()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong t=OrderGetTicket(i);
      if(t==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
      AAA_Trade.OrderDelete(t);
     }
}

void AT_TimeStop()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      int held=Bars(_Symbol,InpSignalTimeframe,(datetime)PositionGetInteger(POSITION_TIME),TimeCurrent())-1;
      if(held>=InpMaxBars) { AAA_Trade.SetExpertMagicNumber((ulong)InpMagic); AAA_Trade.PositionClose(t); }
     }
}

bool AT_Hash(const datetime bar_time)
{
   ulong x=(ulong)(bar_time/PeriodSeconds(InpSignalTimeframe));
   x=(x*2654435761)%1000003;
   return (int)(x%1000)<InpControlPer1000;
}

void OnTick()
{
   if(!InpEnableTrading || !AAA_NewBar(_Symbol,InpSignalTimeframe,g_at_last_bar)) return;
   AT_TimeStop();
   if(AAA_HasPosition(_Symbol,InpMagic)) { AT_DeleteOrders(); return; }
   double atr=AAA_BufferValue(g_atr,0,1);
   double c1=iClose(_Symbol,InpSignalTimeframe,1);
   if(atr==EMPTY_VALUE || atr<=0.0 || c1<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double risk=InpStopATR*atr;
   if(risk<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return;

   if(InpEntryMode==AT_ENTRY_CONTROL_RANDOM)
     {
      if(!AT_Hash(iTime(_Symbol,InpSignalTimeframe,1))) return;
      double sl=AAA_Price(_Symbol,tick.ask-risk), tp=AAA_Price(_Symbol,tick.ask+risk*InpRewardRisk);
      double lots=AAA_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,sl,InpRiskPercent);
      if(lots<=0.0) return;
      AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
      AAA_Trade.SetTypeFillingBySymbol(_Symbol);
      AAA_Trade.Buy(lots,_Symbol,0.0,sl,tp,"ATRTouch control");
      return;
     }

   // Re-place the resting limit at the new band level (delete + place keeps sizing consistent with the new stop).
   AT_DeleteOrders();
   double price=AAA_Price(_Symbol,c1-InpBandATR*atr);
   if(price>=tick.ask) return;
   double sl=AAA_Price(_Symbol,price-risk), tp=AAA_Price(_Symbol,price+risk*InpRewardRisk);
   double lots=AAA_LotsForRisk(_Symbol,ORDER_TYPE_BUY,price,sl,InpRiskPercent);
   if(lots<=0.0) return;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.BuyLimit(lots,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,"ATRTouch long");
}
