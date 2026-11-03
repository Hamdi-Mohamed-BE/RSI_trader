//+------------------------------------------------------------------+
//| TrendSpider "QLD Claude AI Scalper" raw research EA (2026-11-03)  |
//| Long-only M30 breakout of the prior 30-bar high with a 1.75x      |
//| volume spike on a bullish bar; exit after 16 bars if PnL < 0.5%,  |
//| else after 60 bars. Rules frozen in RULES.md. Research only.      |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input int    InpSessionMode=1;            // 0 = every bar, 1 = New York regular session bars 09:30-15:30 opens
input int    InpRangeBars=30;
input int    InpVolPeriod=20;
input double InpVolMult=1.75;             // 0 disables the volume filter
input bool   InpRequireBullish=true;
input int    InpMinHoldBars=16;
input double InpMinHoldPnlPct=0.5;
input int    InpMaxHoldBars=60;
input double InpNotionalPct=100.0;        // position value as % of equity at entry
input double InpRandomProb=0.0;           // >0: control, random entries per flat session bar instead of the signal
input int    InpSeed=1;
input int    InpMaximumDeviationPoints=100000;
input long   InpMagic=11032026;

CTrade   trade;
datetime lastBar=0;
bool     pendingEntry=false,pendingExit=false,exitDue=false;
datetime entryDueBar=0;
string   exitWhy="";
int      barsHeld=0;
double   entryPrice=0;
long     nSessionBars=0,nFlatBars=0,nSignals=0,nEntries=0,nSkips=0,nExits16=0,nExits60=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
int NyOffset(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return (utc>=on&&utc<off)?-4*3600:-5*3600;}
// Exness server time is UTC+0 (as in the other studies on this tester).
bool SessionBar(datetime t)
  {
   if(InpSessionMode==0) return true;
   datetime ny=t+NyOffset(t);MqlDateTime d;TimeToStruct(ny,d);
   if(d.day_of_week<1||d.day_of_week>5) return false;
   int m=d.hour*60+d.min;
   return m>=9*60+30 && m<16*60;
  }

bool InPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk!=0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
     }
   return false;
  }

// Session bars only, newest first starting at shift 1 (the completed bar). Returns how many were found.
int SessionBars(int need,double &hi[],double &op[],double &cl[],double &vol[])
  {
   ArrayResize(hi,0);ArrayResize(op,0);ArrayResize(cl,0);ArrayResize(vol,0);
   int found=0,total=Bars(_Symbol,PERIOD_M30);
   for(int s=1;s<total&&found<need&&s<need*20+200;s++)
     {
      datetime t=iTime(_Symbol,PERIOD_M30,s);
      if(!SessionBar(t)) continue;
      ArrayResize(hi,found+1);ArrayResize(op,found+1);ArrayResize(cl,found+1);ArrayResize(vol,found+1);
      hi[found]=iHigh(_Symbol,PERIOD_M30,s);op[found]=iOpen(_Symbol,PERIOD_M30,s);cl[found]=iClose(_Symbol,PERIOD_M30,s);
      vol[found]=(double)iVolume(_Symbol,PERIOD_M30,s);found++;
     }
   return found;
  }

bool Signal()
  {
   double hi[],op[],cl[],vol[];
   int need=MathMax(InpRangeBars+1,InpVolPeriod);
   if(SessionBars(need,hi,op,cl,vol)<need) return false;
   double top=-DBL_MAX;for(int i=1;i<=InpRangeBars;i++) top=MathMax(top,hi[i]);     // the 30 bars before the signal bar
   if(!(cl[0]>top)) return false;
   if(InpVolMult>0)
     {
      double sum=0;for(int i=0;i<InpVolPeriod;i++) sum+=vol[i];                      // SMA includes the signal bar
      if(!(vol[0]>=InpVolMult*sum/InpVolPeriod)) return false;
     }
   if(InpRequireBullish&&!(cl[0]>op[0])) return false;
   return true;
  }

bool Retry(uint rc){return rc==TRADE_RETCODE_MARKET_CLOSED||rc==TRADE_RETCODE_PRICE_OFF||rc==TRADE_RETCODE_REQUOTE||rc==TRADE_RETCODE_PRICE_CHANGED||rc==TRADE_RETCODE_TRADE_DISABLED;}
// returns true when no further attempt is needed this bar (filled, or skipped for a non-transient reason)
bool Enter()
  {
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),cs=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double lots=AccountInfoDouble(ACCOUNT_EQUITY)*InpNotionalPct/100.0/(ask*cs);
   lots=MathFloor(lots/step+1e-9)*step;lots=MathMin(lots,mx);
   if(lots<mn){nSkips++;PrintFormat("TSBV_SKIP lots %.4f below minimum",lots);return true;}
   if(trade.Buy(lots,_Symbol,0,0,0,"TSBV long")&&trade.ResultRetcode()==TRADE_RETCODE_DONE)
     {
      nEntries++;barsHeld=0;entryPrice=trade.ResultPrice()>0?trade.ResultPrice():ask;return true;
     }
   return !Retry(trade.ResultRetcode());
  }

// exits are mandatory: retried on every tick until the position is gone
bool Exit()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk!=0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic) trade.PositionClose(tk);
     }
   if(InPosition()) return false;
   if(exitWhy=="max") nExits60++; else nExits16++;
   PrintFormat("TSBV_EXIT %s bars=%d",exitWhy,barsHeld);
   return true;
  }

int OnInit()
  {
   if(InpRangeBars<2||InpVolPeriod<2||InpMinHoldBars<1||InpMaxHoldBars<InpMinHoldBars||InpNotionalPct<=0) return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   MathSrand(InpSeed);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   datetime b0=iTime(_Symbol,PERIOD_M30,0);
   static datetime lastTry=0;
   if(exitDue&&TimeCurrent()-lastTry>=10){lastTry=TimeCurrent();if(Exit()) exitDue=false;}   // retry at most every 10 s (closed-market spam)
   if(entryDueBar!=0)
     {
      if(b0!=entryDueBar) entryDueBar=0;                     // "trade by open": a missed bar is not chased
      else if(!exitDue&&!InPosition()&&TimeCurrent()-lastTry>=10){lastTry=TimeCurrent();if(Enter()) entryDueBar=0;}
     }
   if(b0==0||b0==lastBar) return;
   bool first=(lastBar==0);lastBar=b0;
   if(first) return;
   datetime b1=iTime(_Symbol,PERIOD_M30,1);
   bool inPos=InPosition();
   if(SessionBar(b1))
     {
      nSessionBars++;
      if(inPos)
        {
         barsHeld++;
         double pnl=(iClose(_Symbol,PERIOD_M30,1)/entryPrice-1.0)*100.0;
         if(!exitDue&&barsHeld>=InpMaxHoldBars){pendingExit=true;exitWhy="max";}
         else if(!exitDue&&barsHeld>=InpMinHoldBars&&pnl<InpMinHoldPnlPct){pendingExit=true;exitWhy="min";}
        }
      else if(!pendingEntry)
        {
         nFlatBars++;
         bool fire=InpRandomProb>0 ? (MathRand()/32768.0<InpRandomProb) : Signal();
         if(fire){pendingEntry=true;nSignals++;}
        }
     }
   if(SessionBar(b0))
     {
      if(pendingExit&&inPos){exitDue=!Exit();}
      pendingExit=false;
      if(pendingEntry){entryDueBar=b0;if(!exitDue&&!InPosition()&&Enter()) entryDueBar=0;}
      pendingEntry=false;
     }
  }

void OnDeinit(const int reason)
  {
   PrintFormat("TSBV_SUMMARY sym=%s sessionbars=%I64d flatbars=%I64d signals=%I64d entries=%I64d skips=%I64d exit16=%I64d exit60=%I64d",
               _Symbol,nSessionBars,nFlatBars,nSignals,nEntries,nSkips,nExits16,nExits60);
  }
