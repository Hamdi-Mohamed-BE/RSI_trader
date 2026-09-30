#property copyright "Calyx research: raw VWAP + 9/21 EMA trend-pullback (US100, M3)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test (user: "EMA and VWAP strategy on the 3 min time frame for US100"):
//   VWAP   : session VWAP anchored 09:30 New York, typical price x tick volume, completed bars only.
//   Trend  : long when close[1] > VWAP and EMA(9) > EMA(21); short mirror.
//   Setup  : pullback - one of bars 2..4 touched EMA(21) (low <= EMA21 for longs), closes of bars 1..3 stayed beyond VWAP.
//   Trigger: bar[1] closes back beyond EMA(9) after bar[2] closed on the other side -> market entry at the next bar.
//   Stop   : beyond the extreme of bars 1..4 +/- 0.1 ATR(14); skip if > 3 ATR or < 3 x spread.
//   Target : InpRewardRisk x risk. Entries 09:45-15:30 NY, flat 15:55 NY, one position, max InpMaxTradesPerDay.
//   Control: InpSignalMode=1 -> enter on the first bar that meets the trend condition (no pullback/trigger), same stop/target.

enum ENUM_EV_SIGNAL { EV_SIGNAL_PULLBACK=0, EV_SIGNAL_CONTROL_TREND_ONLY=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpRewardRisk=2.0;
input long   InpMagic=1092506;
input bool   InpAdaptivePortfolioControls=false;
input bool   InpServerClockEET=false;      // Exness server clock is UTC

input group "EMA + VWAP rules"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M3;
input ENUM_EV_SIGNAL  InpSignalMode=EV_SIGNAL_PULLBACK;
input int    InpFastEMA=9;
input int    InpSlowEMA=21;
input int    InpATRPeriod=14;
input double InpStopBufferATR=0.1;
input double InpMaxStopATR=3.0;
input int    InpMaxTradesPerDay=2;
input int    InpEntryStartMinuteNY=585;    // 09:45
input int    InpEntryEndMinuteNY=930;      // 15:30
input int    InpFlatMinuteNY=955;          // 15:55
input double InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_ev_last_bar=0;
int g_fast=INVALID_HANDLE, g_slow=INVALID_HANDLE, g_atr=INVALID_HANDLE;

int OnInit()
{
   AAA_TesterServerOffsetMode=(InpServerClockEET ? 1 : 0);
   if(InpRewardRisk<=0.0 || InpRiskPercent<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_fast=iMA(_Symbol,InpSignalTimeframe,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow=iMA(_Symbol,InpSignalTimeframe,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast==INVALID_HANDLE || g_slow==INVALID_HANDLE || g_atr==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(g_fast); IndicatorRelease(g_slow); IndicatorRelease(g_atr);
}

int EV_MinuteNY(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(AAA_ToNewYork(server_time),p);
   return p.hour*60+p.min;
}

// Session start (09:30 NY today) in server time.
datetime EV_SessionStart(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(AAA_ToNewYork(server_time),p);
   p.hour=9; p.min=30; p.sec=0;
   return AAA_NewYorkToServer(StructToTime(p));
}

bool EV_VWAP(const datetime start,const datetime last_closed_open,double &vwap)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   int n=CopyRates(_Symbol,InpSignalTimeframe,start,last_closed_open,bars);
   if(n<=0) return false;
   double pv=0.0, v=0.0;
   for(int i=0;i<n;i++)
     {
      double w=(double)MathMax(bars[i].tick_volume,1);
      pv+=(bars[i].high+bars[i].low+bars[i].close)/3.0*w;
      v+=w;
     }
   if(v<=0.0) return false;
   vwap=pv/v;
   return true;
}

int EV_TradesToday(const datetime session_start)
{
   if(!HistorySelect(session_start,TimeCurrent())) return 0;
   int count=0;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
     {
      ulong d=HistoryDealGetTicket(i);
      if(d==0) continue;
      if(HistoryDealGetString(d,DEAL_SYMBOL)==_Symbol && HistoryDealGetInteger(d,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN) count++;
     }
   return count;
}

void EV_CloseAll()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
      AAA_Trade.PositionClose(t);
     }
}

void OnTick()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_ev_last_bar) || !InpEnableTrading) return;
   datetime now=TimeCurrent();
   MqlDateTime d; TimeToStruct(AAA_ToNewYork(now),d);
   if(d.day_of_week==0 || d.day_of_week==6) return;
   int minute=EV_MinuteNY(now);
   if(minute>=InpFlatMinuteNY) { if(AAA_HasPosition(_Symbol,InpMagic)) EV_CloseAll(); return; }
   if(minute<InpEntryStartMinuteNY || minute>InpEntryEndMinuteNY) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   datetime session=EV_SessionStart(now);
   if(EV_TradesToday(session)>=InpMaxTradesPerDay) return;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,6,r)<6) return;
   double vwap=0.0;
   if(!EV_VWAP(session,r[1].time,vwap)) return;
   double fast[],slow[],atrv[];
   ArraySetAsSeries(fast,true); ArraySetAsSeries(slow,true); ArraySetAsSeries(atrv,true);
   if(CopyBuffer(g_fast,0,0,6,fast)<6 || CopyBuffer(g_slow,0,0,6,slow)<6 || CopyBuffer(g_atr,0,1,1,atrv)<1) return;
   double atr=atrv[0];
   if(atr<=0.0) return;

   int trend=0;
   if(r[1].close>vwap && fast[1]>slow[1]) trend=1;
   else if(r[1].close<vwap && fast[1]<slow[1]) trend=-1;
   if(trend==0) return;

   bool go=false;
   if(InpSignalMode==EV_SIGNAL_CONTROL_TREND_ONLY)
      go=true;
   else
     {
      bool touched=false, held=true;
      for(int i=2;i<=4;i++)
         if((trend>0 && r[i].low<=slow[i]) || (trend<0 && r[i].high>=slow[i])) touched=true;
      for(int i=1;i<=3;i++)
         if((trend>0 && r[i].close<=vwap) || (trend<0 && r[i].close>=vwap)) held=false;
      bool trigger=(trend>0 ? (r[1].close>fast[1] && r[2].close<=fast[2]) : (r[1].close<fast[1] && r[2].close>=fast[2]));
      go=touched && held && trigger;
     }
   if(!go) return;

   double extreme=(trend>0 ? r[1].low : r[1].high);
   for(int i=2;i<=4;i++) extreme=(trend>0 ? MathMin(extreme,r[i].low) : MathMax(extreme,r[i].high));
   double stop=extreme-trend*InpStopBufferATR*atr;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(trend>0 ? tick.ask : tick.bid);
   double risk=trend*(entry-stop);
   if(risk<=0.0 || risk>InpMaxStopATR*atr || risk<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return;
   AAA_SendMarket(_Symbol,trend,stop,InpRewardRisk,InpRiskPercent,InpMagic,
                  (InpSignalMode==EV_SIGNAL_PULLBACK ? "EMAVWAP " : "EMAVWAP control ")+(trend>0 ? "long" : "short"));
}
