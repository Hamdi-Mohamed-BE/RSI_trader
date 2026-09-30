#property copyright "Calyx research: crypto/stock edge screen (published anomalies, raw rules)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test. One mode per run; long-only in every mode.
//   TSMOM     (C1): at each new D1 bar, hold long while close[1] > close[1+InpMomLookback]; flat otherwise.
//                   Control: always long (same stop, re-entered after a stop-out at the next D1 bar).
//   VBO       (C2): trigger = today's D1 open + InpVboK x yesterday's range; buy once when ask >= trigger;
//                   stop = today's open; close at the next D1 open. Control: buy at every D1 open, same stop
//                   distance (K x yesterday's range), close at the next D1 open.
//   OVERNIGHT (S1): buy at InpNightEntry NY time on weekdays, close at InpNightExit NY time on the next trading day.
//                   Control (INTRADAY): buy at InpNightExit NY, close at InpNightEntry NY the same day.
//   RSI2      (S2): at each new D1 bar, if close[1] > SMA(200) and RSI(2) < InpRsiBelow -> buy; exit at a new D1
//                   bar when close[1] > SMA(5) or after InpRsiMaxDays days. Control: close[1] > SMA(200) and a
//                   deterministic hash picks ~InpControlPercent% of days; exit after InpControlDays days.
//   Sizing: 1% of equity to a catastrophe stop of InpStopATR x ATR(14, D1) (VBO: the breakout stop), lots rounded up.

enum ENUM_EDGE_MODE
  {
   EDGE_TSMOM=0,
   EDGE_TSMOM_CONTROL=1,
   EDGE_VBO=2,
   EDGE_VBO_CONTROL=3,
   EDGE_OVERNIGHT=4,
   EDGE_INTRADAY_CONTROL=5,
   EDGE_RSI2=6,
   EDGE_RSI2_CONTROL=7
  };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1092504;
input bool   InpAdaptivePortfolioControls=false;
input bool   InpServerClockEET=false;          // Exness server clock is UTC; true only for EET brokers

input group "Edge screen"
input ENUM_EDGE_MODE InpMode=EDGE_TSMOM;
input double InpStopATR=3.0;
input int    InpMomLookback=20;
input double InpVboK=0.5;
input int    InpNightEntryHour=15;
input int    InpNightEntryMinute=50;
input int    InpNightExitHour=9;
input int    InpNightExitMinute=35;
input double InpRsiBelow=10.0;
input int    InpRsiMaxDays=10;
input int    InpControlPercent=5;
input int    InpControlDays=3;

#include "AAA_Final_Common.mqh"

datetime g_edge_last_day=0;
int g_last_entry_key=0;
int g_rsi=INVALID_HANDLE, g_sma200=INVALID_HANDLE, g_sma5=INVALID_HANDLE, g_atr=INVALID_HANDLE;

int OnInit()
{
   AAA_TesterServerOffsetMode=(InpServerClockEET ? 1 : 0);
   g_rsi=iRSI(_Symbol,PERIOD_D1,2,PRICE_CLOSE);
   g_sma200=iMA(_Symbol,PERIOD_D1,200,0,MODE_SMA,PRICE_CLOSE);
   g_sma5=iMA(_Symbol,PERIOD_D1,5,0,MODE_SMA,PRICE_CLOSE);
   g_atr=iATR(_Symbol,PERIOD_D1,14);
   if(g_rsi==INVALID_HANDLE || g_sma200==INVALID_HANDLE || g_sma5==INVALID_HANDLE || g_atr==INVALID_HANDLE) return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(g_rsi); IndicatorRelease(g_sma200); IndicatorRelease(g_sma5); IndicatorRelease(g_atr);
}

bool Edge_Buy(const double stop,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double sl=AAA_Price(_Symbol,stop);
   if(sl<=0.0 || sl>=tick.ask) { PrintFormat("EDGE skip %s: stop %.5f not below ask %.5f",comment,sl,tick.ask); return false; }
   if(tick.ask-sl<3.0*(tick.ask-tick.bid)) { PrintFormat("EDGE skip %s: stop inside 3x spread",comment); return false; }
   double lots=AAA_LotsForRisk(_Symbol,ORDER_TYPE_BUY,tick.ask,sl,InpRiskPercent);
   if(lots<=0.0) { PrintFormat("EDGE skip %s: lot size 0 (contract data unavailable)",comment); return false; }
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(50);
   return AAA_Trade.Buy(lots,_Symbol,0.0,sl,0.0,comment);
}

void Edge_CloseAll()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
      AAA_Trade.PositionClose(ticket);
     }
}

int Edge_HeldDays()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      return Bars(_Symbol,PERIOD_D1,(datetime)PositionGetInteger(POSITION_TIME),TimeCurrent())-1;
     }
   return 0;
}

bool Edge_HashPicks(const datetime day)
{
   ulong x=(ulong)(day/86400);
   x=(x*2654435761)%1000003;
   return (int)(x%100)<InpControlPercent;
}

double Edge_ATR() { return AAA_BufferValue(g_atr,0,1); }

void Edge_DailyModes()
{
   if(!AAA_NewBar(_Symbol,PERIOD_D1,g_edge_last_day)) return;
   double atr=Edge_ATR();
   if(atr==EMPTY_VALUE || atr<=0.0) return;
   bool has=AAA_HasPosition(_Symbol,InpMagic);
   double c1=iClose(_Symbol,PERIOD_D1,1);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;

   if(InpMode==EDGE_TSMOM || InpMode==EDGE_TSMOM_CONTROL)
     {
      double past=iClose(_Symbol,PERIOD_D1,1+InpMomLookback);
      bool want=(InpMode==EDGE_TSMOM_CONTROL) || (past>0.0 && c1>past);
      if(has && !want) Edge_CloseAll();
      if(!has && want) Edge_Buy(tick.ask-InpStopATR*atr,(InpMode==EDGE_TSMOM ? "TSMOM" : "TSMOM control"));
      return;
     }
   if(InpMode==EDGE_VBO || InpMode==EDGE_VBO_CONTROL)
     {
      if(has) Edge_CloseAll();   // exit at the next D1 open
      if(InpMode==EDGE_VBO_CONTROL)
        {
         double range=iHigh(_Symbol,PERIOD_D1,1)-iLow(_Symbol,PERIOD_D1,1);
         if(range>0.0) Edge_Buy(tick.ask-InpVboK*range,"VBO control");
        }
      return;
     }
   if(InpMode==EDGE_RSI2 || InpMode==EDGE_RSI2_CONTROL)
     {
      double sma200=AAA_BufferValue(g_sma200,0,1), sma5=AAA_BufferValue(g_sma5,0,1), rsi=AAA_BufferValue(g_rsi,0,1);
      if(sma200==EMPTY_VALUE || sma5==EMPTY_VALUE || rsi==EMPTY_VALUE) return;
      if(has)
        {
         int held=Edge_HeldDays();
         bool exit_now=(InpMode==EDGE_RSI2 ? (c1>sma5 || held>=InpRsiMaxDays) : held>=InpControlDays);
         if(exit_now) Edge_CloseAll();
         return;
        }
      bool want=(c1>sma200) && (InpMode==EDGE_RSI2 ? rsi<InpRsiBelow : Edge_HashPicks(iTime(_Symbol,PERIOD_D1,0)));
      if(want) Edge_Buy(tick.ask-InpStopATR*atr,(InpMode==EDGE_RSI2 ? "RSI2 D1" : "RSI2 control"));
     }
}

void Edge_VboIntraday()
{
   if(InpMode!=EDGE_VBO || AAA_HasPosition(_Symbol,InpMagic)) return;
   datetime day=iTime(_Symbol,PERIOD_D1,0);
   int key=(int)(day/86400);
   if(key==g_last_entry_key) return;
   double open0=iOpen(_Symbol,PERIOD_D1,0);
   double range=iHigh(_Symbol,PERIOD_D1,1)-iLow(_Symbol,PERIOD_D1,1);
   if(open0<=0.0 || range<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(tick.ask>=open0+InpVboK*range)
     {
      g_last_entry_key=key;   // one attempt per day
      Edge_Buy(open0,"VBO");
     }
}

void Edge_SessionModes()
{
   datetime ny=AAA_ToNewYork(TimeCurrent());
   MqlDateTime p;
   TimeToStruct(ny,p);
   if(p.day_of_week==0 || p.day_of_week==6) return;
   int minute=p.hour*60+p.min;
   int entry_minute=(InpMode==EDGE_OVERNIGHT ? InpNightEntryHour*60+InpNightEntryMinute : InpNightExitHour*60+InpNightExitMinute);
   int exit_minute=(InpMode==EDGE_OVERNIGHT ? InpNightExitHour*60+InpNightExitMinute : InpNightEntryHour*60+InpNightEntryMinute);
   int day_key=p.year*10000+p.mon*100+p.day;
   static int seen_day=0, first_min=0, last_min=0;
   if(day_key!=seen_day)
     {
      if(seen_day!=0) PrintFormat("EDGE session %d: NY ticks %02d:%02d-%02d:%02d",seen_day,first_min/60,first_min%60,last_min/60,last_min%60);
      seen_day=day_key; first_min=minute;
     }
   last_min=minute;
   bool has=AAA_HasPosition(_Symbol,InpMagic);
   if(has)
     {
      datetime opened=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong t=PositionGetTicket(i);
         if(t!=0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
            opened=(datetime)PositionGetInteger(POSITION_TIME);
        }
      MqlDateTime o;
      TimeToStruct(AAA_ToNewYork(opened),o);
      int opened_key=o.year*10000+o.mon*100+o.day;
      bool later_day=(day_key!=opened_key);
      // Overnight exits on a later NY day; intraday control exits the same day.
      if(minute>=exit_minute && (InpMode==EDGE_OVERNIGHT ? later_day : true)) Edge_CloseAll();
      return;
     }
   if(day_key==g_last_entry_key || minute<entry_minute || minute>entry_minute+5) return;
   double atr=Edge_ATR();
   if(atr==EMPTY_VALUE || atr<=0.0) { PrintFormat("EDGE skip session entry: D1 ATR unavailable (%s)",TimeToString(TimeCurrent())); g_last_entry_key=day_key; return; }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   g_last_entry_key=day_key;
   Edge_Buy(tick.ask-InpStopATR*atr,(InpMode==EDGE_OVERNIGHT ? "Overnight" : "Intraday control"));
}

void OnTick()
{
   if(!InpEnableTrading) return;
   if(InpMode==EDGE_OVERNIGHT || InpMode==EDGE_INTRADAY_CONTROL) { Edge_SessionModes(); return; }
   Edge_DailyModes();
   if(InpMode==EDGE_VBO) Edge_VboIntraday();
}
