#property copyright "Calyx research: raw 'no-wick candle' entry model from an Instagram reel (@italian_founder); rules are our own reading"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test (reel transcript supplied by the user):
//   Trend  : bullish when close[1] > EMA(InpTrendSlow) and EMA(InpTrendFast) > EMA(InpTrendSlow); bearish mirror.
//   Signal : bullish trend + bullish candle[1] with no bottom wick (open - low <= tolerance);
//            bearish trend + bearish candle[1] with no top wick (high - open <= tolerance).
//            tolerance = max(1 point, InpWickTolerancePct % of the candle range).
//   Entry  : limit at candle[1] open (price must come back to it); cancelled after InpExpiryBars bars.
//   Stop   : most recent swing beyond the entry = lowest low (highest high) of the last InpSwingLookback bars
//            before the signal candle that is below (above) the entry, -/+ InpStopBufferATR x ATR.
//   Target : InpRewardRisk x risk (reel: roughly 1:1). One setup/position at a time.
//   Control: InpSignalMode=1 -> any candle in the trend direction (wick ignored), same entry/stop/target.

enum ENUM_NW_SIGNAL { NW_SIGNAL_NO_WICK=0, NW_SIGNAL_CONTROL_ANY_CANDLE=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpRewardRisk=1.0;
input long   InpMagic=1092505;
input bool   InpAdaptivePortfolioControls=false;

input group "No-wick rules"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input ENUM_NW_SIGNAL  InpSignalMode=NW_SIGNAL_NO_WICK;
input int    InpTrendFast=50;
input int    InpTrendSlow=200;
input double InpWickTolerancePct=2.0;
input int    InpSwingLookback=10;
input double InpStopBufferATR=0.2;
input int    InpATRPeriod=14;
input int    InpExpiryBars=20;
input double InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_nw_last_bar=0;
int g_fast=INVALID_HANDLE, g_slow=INVALID_HANDLE, g_atr=INVALID_HANDLE;

int OnInit()
{
   if(InpRewardRisk<=0.0 || InpRiskPercent<=0.0 || InpSwingLookback<2) return INIT_PARAMETERS_INCORRECT;
   g_fast=iMA(_Symbol,InpSignalTimeframe,InpTrendFast,0,MODE_EMA,PRICE_CLOSE);
   g_slow=iMA(_Symbol,InpSignalTimeframe,InpTrendSlow,0,MODE_EMA,PRICE_CLOSE);
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast==INVALID_HANDLE || g_slow==INVALID_HANDLE || g_atr==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(g_fast); IndicatorRelease(g_slow); IndicatorRelease(g_atr);
}

void NW_CancelExpired()
{
   int seconds=InpExpiryBars*PeriodSeconds(InpSignalTimeframe);
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      if(TimeCurrent()-(datetime)OrderGetInteger(ORDER_TIME_SETUP)>=seconds)
        {
         AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
         AAA_Trade.OrderDelete(ticket);
        }
     }
}

bool NW_PlaceLimit(const int direction,const double entry,const double stop,const string comment)
{
   if(!DTS_EntrySessionAllowed()) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double price=AAA_Price(_Symbol,entry);
   double sl=AAA_Price(_Symbol,stop);
   double risk=MathAbs(price-sl);
   if(risk<=0.0 || risk<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return false;
   if(direction>0 && (sl>=price || price>=tick.ask)) return false;
   if(direction<0 && (sl<=price || price<=tick.bid)) return false;
   double tp=AAA_Price(_Symbol,price+direction*risk*InpRewardRisk);
   double lots=AAA_LotsForRisk(_Symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),price,sl,InpRiskPercent);
   if(lots<=0.0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   if(direction>0) return AAA_Trade.BuyLimit(lots,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
   return AAA_Trade.SellLimit(lots,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
}

void OnTick()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_nw_last_bar) || !InpEnableTrading) return;
   NW_CancelExpired();
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   double fast=AAA_BufferValue(g_fast,0,1), slow=AAA_BufferValue(g_slow,0,1), atr=AAA_BufferValue(g_atr,0,1);
   if(fast==EMPTY_VALUE || slow==EMPTY_VALUE || atr==EMPTY_VALUE || atr<=0.0) return;
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int need=InpSwingLookback+3;
   if(CopyRates(_Symbol,InpSignalTimeframe,0,need,r)<need) return;

   int trend=0;
   if(r[1].close>slow && fast>slow) trend=1;
   else if(r[1].close<slow && fast<slow) trend=-1;
   if(trend==0) return;

   double range=r[1].high-r[1].low;
   if(range<=0.0) return;
   double tolerance=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),range*InpWickTolerancePct/100.0);
   bool bullish=r[1].close>r[1].open, bearish=r[1].close<r[1].open;
   bool signal=false;
   if(trend>0 && bullish) signal=(InpSignalMode==NW_SIGNAL_CONTROL_ANY_CANDLE) || (r[1].open-r[1].low<=tolerance);
   if(trend<0 && bearish) signal=(InpSignalMode==NW_SIGNAL_CONTROL_ANY_CANDLE) || (r[1].high-r[1].open<=tolerance);
   if(!signal) return;

   double entry=r[1].open;
   double swing=0.0;
   bool found=false;
   for(int i=2;i<2+InpSwingLookback;i++)
     {
      double level=(trend>0 ? r[i].low : r[i].high);
      if(trend>0 && level<entry && (!found || level<swing)) { swing=level; found=true; }
      if(trend<0 && level>entry && (!found || level>swing)) { swing=level; found=true; }
     }
   if(!found) return;
   double stop=swing-trend*InpStopBufferATR*atr;
   string comment=(InpSignalMode==NW_SIGNAL_NO_WICK ? "NoWick " : "NoWick control ")+(trend>0 ? "long" : "short");
   NW_PlaceLimit(trend,entry,stop,comment);
}
