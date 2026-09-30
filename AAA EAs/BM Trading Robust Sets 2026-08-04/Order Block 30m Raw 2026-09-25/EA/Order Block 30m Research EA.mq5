#property copyright "Calyx research: raw 30m order block idea (heyastral.ai/u/lucas_lalk names only; rules are our own)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test (signal timeframe M30 by default):
//   Swing   : fractal high/low with InpSwingBars bars on each side, confirmed before the break bar.
//   Break   : bar[1] closes beyond the most recent swing high (low) and bar[2] had not closed beyond it.
//   Impulse : leg from its extreme (lowest low / highest high since the swing) to bar[1] close >= InpImpulseATR x ATR.
//   OB      : last opposite-colour candle at or up to InpOBSearchBars before the leg extreme; zone = its high..low,
//             size InpOBMinATR..InpOBMaxATR x ATR.
//   Entry   : limit at the near edge of the OB (first return); cancelled after InpExpiryBars bars. One setup at a time.
//   Stop    : far edge of the OB -/+ InpStopBufferATR x ATR. Target: InpRewardRisk x risk.
//   Control : InpEntryMode=1 -> same break/impulse, limit at the 50% pullback of the leg, stop beyond the leg extreme.
//   Guard   : skip when the stop is closer than InpMinStopSpreadMultiple x current spread.

enum ENUM_OB_ENTRY { OB_ENTRY_ORDER_BLOCK=0, OB_ENTRY_CONTROL_HALF_LEG=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpRewardRisk=1.0;
input long   InpMagic=1092502;
input bool   InpAdaptivePortfolioControls=false;

input group "Order block rules"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M30;
input ENUM_OB_ENTRY   InpEntryMode=OB_ENTRY_ORDER_BLOCK;
input int    InpSwingBars=3;
input int    InpSwingLookback=100;
input double InpImpulseATR=1.5;
input int    InpOBSearchBars=5;
input double InpOBMinATR=0.2;
input double InpOBMaxATR=2.0;
input double InpStopBufferATR=0.1;
input int    InpExpiryBars=48;
input int    InpATRPeriod=14;
input double InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_ob_last_bar=0;

bool OB_IsSwingHigh(MqlRates &r[],const int j,const int n)
{
   for(int k=1;k<=n;k++)
      if(r[j-k].high>=r[j].high || r[j+k].high>r[j].high) return false;
   return true;
}

bool OB_IsSwingLow(MqlRates &r[],const int j,const int n)
{
   for(int k=1;k<=n;k++)
      if(r[j-k].low<=r[j].low || r[j+k].low<r[j].low) return false;
   return true;
}

void OB_CancelExpired()
{
   int seconds=InpExpiryBars*PeriodSeconds(InpSignalTimeframe);
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      if(TimeCurrent()-(datetime)OrderGetInteger(ORDER_TIME_SETUP)>=seconds)
        {
         AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
         AAA_Trade.OrderDelete(ticket);
        }
     }
}

bool OB_PlaceLimit(const int direction,const double entry,const double stop,const string comment)
{
   if(!DTS_EntrySessionAllowed()) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double price=AAA_Price(_Symbol,entry);
   double sl=AAA_Price(_Symbol,stop);
   double risk=MathAbs(price-sl);
   if(risk<=0.0 || risk<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return false;
   if(direction>0 && (sl>=price || price>=tick.ask)) return false;   // limit must sit below the market
   if(direction<0 && (sl<=price || price<=tick.bid)) return false;
   double tp=AAA_Price(_Symbol,price+direction*risk*InpRewardRisk);
   double lots=AAA_LotsForRisk(_Symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),price,sl,InpRiskPercent);
   if(lots<=0.0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   if(direction>0) return AAA_Trade.BuyLimit(lots,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
   return AAA_Trade.SellLimit(lots,price,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
}

int OnInit()
{
   if(InpRewardRisk<=0.0 || InpRiskPercent<=0.0 || InpSwingBars<1) return INIT_PARAMETERS_INCORRECT;
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_ob_last_bar) || !InpEnableTrading) return;
   OB_CancelExpired();
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   int n=InpSwingBars;
   int count=InpSwingLookback+n+InpOBSearchBars+5;
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,count,r)<count) return;
   double atr=AAA_ATR(_Symbol,InpSignalTimeframe,InpATRPeriod,1);
   if(atr==EMPTY_VALUE || atr<=0.0) return;

   // Most recent confirmed swing high/low strictly before the break bar (needs n bars after it, all before bar[1]).
   int sh=-1,sl=-1;
   for(int j=n+2;j<=InpSwingLookback && (sh<0 || sl<0);j++)
     {
      if(sh<0 && OB_IsSwingHigh(r,j,n)) sh=j;
      if(sl<0 && OB_IsSwingLow(r,j,n)) sl=j;
     }

   for(int direction=1;direction>=-1;direction-=2)
     {
      int s=(direction>0 ? sh : sl);
      if(s<0) continue;
      double level=(direction>0 ? r[s].high : r[s].low);
      bool broke=(direction>0 ? (r[1].close>level && r[2].close<=level) : (r[1].close<level && r[2].close>=level));
      if(!broke) continue;
      // Leg extreme between the swing and the break bar.
      int k=1;
      for(int i=1;i<s;i++)
         if((direction>0 && r[i].low<r[k].low) || (direction<0 && r[i].high>r[k].high)) k=i;
      double origin=(direction>0 ? r[k].low : r[k].high);
      if(MathAbs(r[1].close-origin)<InpImpulseATR*atr) continue;

      double entry=0.0,stop=0.0;
      string comment;
      if(InpEntryMode==OB_ENTRY_ORDER_BLOCK)
        {
         int ob=-1;
         for(int i=k;i<=k+InpOBSearchBars && i<count;i++)
            if((direction>0 && r[i].close<r[i].open) || (direction<0 && r[i].close>r[i].open)) { ob=i; break; }
         if(ob<0) continue;
         double size=r[ob].high-r[ob].low;
         if(size<InpOBMinATR*atr || size>InpOBMaxATR*atr) continue;
         entry=(direction>0 ? r[ob].high : r[ob].low);
         stop=(direction>0 ? r[ob].low-InpStopBufferATR*atr : r[ob].high+InpStopBufferATR*atr);
         comment=(direction>0 ? "OB30 long" : "OB30 short");
        }
      else
        {
         entry=origin+0.5*(r[1].close-origin);
         stop=origin-direction*InpStopBufferATR*atr;
         comment=(direction>0 ? "OB30 control long" : "OB30 control short");
        }
      if(OB_PlaceLimit(direction,entry,stop,comment)) return;
     }
}
