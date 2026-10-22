#property strict
#property version "1.00"
#property description "Research only (2026-10-22). Turtle breakout portfolio (Revelio adaptation): 20-day-high entry, fixed 2 ATR(20, Wilder) stop,"
#property description "10-day-low trailing exit, long only, 2% of high-water-mark risk, 5 symbols on one account. Optional day-trading schedule. Rules: RULES.md."
#include <Trade/Trade.mqh>

input string InpSymbols="US500,USTEC,XAUUSD,XAGUSD,BTCUSD";
input int    InpEntryDays=20;
input int    InpExitDays=10;
input int    InpAtrDays=20;
input double InpAtrMult=2.0;
input double InpRiskPct=2.0;            // % of the high-water-mark equity, measured to the fixed stop
input bool   InpDayTrading=true;
input int    InpCloseMinNY=16*60+30;     // 16:30 New York
input int    InpOpenMinNY=18*60;         // 18:00 New York
input bool   InpRandomEntries=false;     // control: random entries at the 18:00 NY slot instead of breakouts
input double InpRandomProb=0.05;
input int    InpSeed=1;
input int    InpMaximumDeviationPoints=100000;
input long   InpMagic=2210260;

class CSym {
public:
   string s; long magic; double highs[]; double lows[]; double atr; double atrSeed; int atrCount; double prevClose; bool havePrev;
   bool signal; bool held; double stop; double lots; ulong ticket; datetime lastBoundary; long episode; long randDay;
   long breakouts,entries,reentries,scheduled,slExits,flatEnds,fails,ndays;
   int qEndDow[7],qEndCur;   // NY minute of the last in-session quote in [15:00, 17:00): latest day per NY weekday / current day (-1 none)
   CSym(){atr=0;atrSeed=0;atrCount=0;prevClose=0;havePrev=false;signal=false;held=false;stop=0;lots=0;ticket=0;lastBoundary=0;episode=0;randDay=-1;
      breakouts=entries=reentries=scheduled=slExits=flatEnds=fails=ndays=0;ArrayInitialize(qEndDow,-1);qEndCur=-1;}
};
CSym *S[];
CTrade trade;
double hwm=0;
datetime lastEquityDay=0;

datetime NthSunday(int year,int month,int n){MqlDateTime t={};t.year=year;t.mon=month;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((7-d.day_of_week)%7)+7*(n-1))*86400);}
int NyOffset(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthSunday(d.year,3,2)+7*3600,off=NthSunday(d.year,11,1)+6*3600;return (utc>=on&&utc<off)?-4*3600:-5*3600;}
datetime NY(datetime utc){return utc+NyOffset(utc);}
// Latest UTC instant <= t at which the New York clock reads 17:00.
datetime Boundary(datetime t){datetime ny=NY(t),b=ny-ny%86400+17*3600;if(b>ny)b-=86400;datetime u=b-NyOffset(t);if(u>t)u-=86400;return u;}
int NyMin(datetime t){datetime ny=NY(t);return (int)((ny%86400)/60);}
int NyDow(datetime t){MqlDateTime d;TimeToStruct(NY(t),d);return d.day_of_week;}

bool Allowed(datetime t){
   if(!InpDayTrading)return true;
   int m=NyMin(t),dw=NyDow(t);
   if(dw==6)return false;
   if(dw==0&&m<InpOpenMinNY)return false;
   if(dw==5&&m>=InpCloseMinNY)return false;
   return m<InpCloseMinNY||m>=InpOpenMinNY;
}
bool InSessionAt(string s,datetime t){datetime from=0,to=0;MqlDateTime d;TimeToStruct(t,d);long sec=(long)(t%86400);
   for(uint i=0;SymbolInfoSessionTrade(s,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)if(sec>=(long)from&&sec<(long)to)return true;return false;}
bool InSession(string s){return InSessionAt(s,TimeCurrent());}
bool SessionEndsWithin(string s,long seconds){datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(s,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)if(sec>=(long)from&&sec<(long)to)return (long)to<86400&&(long)to-sec<=seconds;return false;}
// Day-trading flat time: close at 16:30 NY, or earlier when the symbol cannot be traded until then:
// - the tester applies the symbol's current (US summer) session table, fixed in UTC, to all history, so in US winter
//   indices/metals stop trading at 16:00 NY: close 5 minutes before the session ends;
// - older index quotes stop before 16:30 NY (e.g. 15:58, and Fridays differ from Mon-Thu): close 5 minutes before the time
//   quotes stopped on the latest earlier day with the same NY weekday (known at the time, no look-ahead).
bool FlatTime(CSym *x,datetime t){
   if(!InpDayTrading)return false;
   if(!Allowed(t))return true;
   int m=NyMin(t);if(m>=InpCloseMinNY)return false;
   if(m>=InpCloseMinNY-60&&SessionEndsWithin(x.s,300))return true;
   int q=x.qEndDow[NyDow(t)];return q>=0&&m>=q-5;
}
// Seed the per-weekday quote-end minutes from the M1 bars of the 3 weeks before the start.
void SeedQuoteEnd(CSym *x,datetime from,datetime to){
   MqlRates r[];int n=CopyRates(x.s,PERIOD_M1,from,to-1,r);long last[7];ArrayInitialize(last,-1);
   for(int i=0;i<n;i++){datetime t=r[i].time;int m=NyMin(t);if(m<900||m>=1020||!InSessionAt(x.s,t))continue;
      long dd=(long)(NY(t)/86400);int dw=NyDow(t);if(dd!=last[dw]){last[dw]=dd;x.qEndDow[dw]=m;}else x.qEndDow[dw]=MathMax(x.qEndDow[dw],m);}
}
void Push(double &a[],double v,int n){int k=ArraySize(a);ArrayResize(a,k+1);a[k]=v;if(ArraySize(a)>n)ArrayRemove(a,0,1);}
double Max(const double &a[]){double m=-DBL_MAX;for(int i=0;i<ArraySize(a);i++)m=MathMax(m,a[i]);return m;}
double Min(const double &a[]){double m=DBL_MAX;for(int i=0;i<ArraySize(a);i++)m=MathMin(m,a[i]);return m;}
bool Ready(CSym *x){return ArraySize(x.highs)==InpEntryDays&&ArraySize(x.lows)==InpExitDays&&x.atrCount>=InpAtrDays;}
double EntryLevel(CSym *x){return Max(x.highs);}
double ExitLevel(CSym *x){return Min(x.lows);}
double ActiveStop(CSym *x){return MathMax(x.stop,ExitLevel(x));}

// Close one completed New York day [a, b) from M30 bars; days without quotes are skipped.
bool CompleteDay(CSym *x,datetime a,datetime b){
   MqlRates r[];int n=CopyRates(x.s,PERIOD_M30,a,b-1,r);if(n<=0)return false;
   double h=-DBL_MAX,l=DBL_MAX,c=0;int used=0;
   for(int i=0;i<n;i++){if(r[i].time<a||r[i].time>=b)continue;h=MathMax(h,r[i].high);l=MathMin(l,r[i].low);c=r[i].close;used++;}
   if(used==0)return false;
   Push(x.highs,h,InpEntryDays);Push(x.lows,l,InpExitDays);
   double tr=x.havePrev?MathMax(h-l,MathMax(MathAbs(h-x.prevClose),MathAbs(l-x.prevClose))):h-l;
   if(x.atrCount<InpAtrDays){x.atrSeed+=tr;x.atrCount++;if(x.atrCount==InpAtrDays)x.atr=x.atrSeed/InpAtrDays;}else x.atr=(x.atr*(InpAtrDays-1)+tr)/InpAtrDays;
   x.prevClose=c;x.havePrev=true;return true;
}

bool PositionAlive(CSym *x){return x.ticket!=0&&PositionSelectByTicket(x.ticket);}
double PositionNet(ulong id){double net=0;if(!HistorySelectByPosition(id))return 0;
   for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);net+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);}return net;}

double Lots(CSym *x,double entry,double stop){
   double loss=0;if(!OrderCalcProfit(ORDER_TYPE_BUY,x.s,1.0,entry,stop,loss)||loss>=0)return 0;
   double st=SymbolInfoDouble(x.s,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(x.s,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(x.s,SYMBOL_VOLUME_MAX);
   double v=NormalizeDouble(MathMax(mn,MathCeil((InpRiskPct/100.0*hwm/-loss-1e-10)/st)*st),8);return MathMin(v,mx);
}

bool Buy(CSym *x,double lots,string why){
   MqlTick q;if(!SymbolInfoTick(x.s,q)||q.ask<=0)return false;
   double sl=NormalizeDouble(ActiveStop(x),(int)SymbolInfoInteger(x.s,SYMBOL_DIGITS));
   double gap=MathMax(SymbolInfoInteger(x.s,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(x.s,SYMBOL_TRADE_FREEZE_LEVEL))*SymbolInfoDouble(x.s,SYMBOL_POINT);
   if(q.bid-sl<=gap)return false;
   trade.SetExpertMagicNumber(x.magic);
   if(!trade.Buy(lots,x.s,0,sl,0,why)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){x.fails++;return false;}
   ulong d=trade.ResultDeal();HistoryDealSelect(d);x.ticket=(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID);x.held=true;x.lots=lots;
   PrintFormat("TURTLE_OPEN sym=%s ep=%I64d why=%s price=%.5f stop=%.5f active=%.5f lots=%.2f hwm=%.2f",x.s,x.episode,why,q.ask,x.stop,sl,lots,hwm);
   return true;
}

void LogClose(CSym *x,string reason){
   PrintFormat("TURTLE_CLOSE sym=%s ep=%I64d reason=%s time=%I64d net=%.2f",x.s,x.episode,reason,(long)TimeCurrent(),PositionNet(x.ticket));
   x.ticket=0;x.held=false;
}

void Process(CSym *x){
   datetime now=TimeCurrent();
   datetime b=Boundary(now);
   if(x.lastBoundary==0)x.lastBoundary=b;
   if(b>x.lastBoundary){if(CompleteDay(x,x.lastBoundary,b))x.ndays++;x.lastBoundary=b;
      if(x.qEndCur>=0){int dw=NyDow(b-60);if(x.qEndCur!=x.qEndDow[dw])PrintFormat("TURTLE_QEND sym=%s time=%I64d dow=%d min=%d",x.s,(long)b,dw,x.qEndCur);x.qEndDow[dw]=x.qEndCur;}
      x.qEndCur=-1;}
   if(!Ready(x))return;
   if(x.held&&!PositionAlive(x)){x.slExits++;LogClose(x,"stop");x.signal=false;}
   MqlTick q;if(!SymbolInfoTick(x.s,q)||q.bid<=0||now-q.time>120)return;
   bool session=InSession(x.s);
   if(session){int qm=NyMin(q.time);if(qm>=900&&qm<1020&&qm>x.qEndCur)x.qEndCur=qm;}
   // raise the broker stop at the first tradable tick after the rollover (indices/metals are closed at 17:00 NY);
   // if price has already gapped through the new stop, close at the market
   if(x.held&&session&&PositionAlive(x)){double sl=NormalizeDouble(ActiveStop(x),(int)SymbolInfoInteger(x.s,SYMBOL_DIGITS));
      if(sl>PositionGetDouble(POSITION_SL)+SymbolInfoDouble(x.s,SYMBOL_POINT)/2){
         double gap=MathMax(SymbolInfoInteger(x.s,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(x.s,SYMBOL_TRADE_FREEZE_LEVEL))*SymbolInfoDouble(x.s,SYMBOL_POINT);
         if(q.bid-sl<=gap){if(trade.PositionClose(x.ticket)){x.slExits++;LogClose(x,"stop_gap");x.signal=false;return;}}
         else trade.PositionModify(x.ticket,sl,0);}}
   // scheduled close (day-trading mode)
   if(InpDayTrading&&x.held&&FlatTime(x,now)&&session){if(trade.PositionClose(x.ticket)){x.scheduled++;LogClose(x,"scheduled");}}
   // signal end while flat (price below the active stop)
   if(x.signal&&!x.held&&q.bid<ActiveStop(x)){x.signal=false;x.flatEnds++;PrintFormat("TURTLE_END sym=%s ep=%I64d time=%I64d",x.s,x.episode,(long)now);}
   // new signal
   if(!x.signal){
      bool fire=false;double ref=0;
      if(!InpRandomEntries){double lvl=EntryLevel(x);if(q.bid>lvl){fire=true;ref=MathMax(lvl,q.bid);}}
      else{long day=(long)(Boundary(now)/86400);int m=NyMin(now);
         if(session&&Allowed(now)&&m>=InpOpenMinNY&&day!=x.randDay){x.randDay=day;if(MathRand()/32768.0<InpRandomProb){fire=true;ref=q.bid;}}}
      if(fire){x.signal=true;x.stop=ref-InpAtrMult*x.atr;x.episode++;x.breakouts++;x.lots=0;
         PrintFormat("TURTLE_SIGNAL sym=%s ep=%I64d time=%I64d ref=%.5f stop=%.5f atr=%.5f",x.s,x.episode,(long)now,ref,x.stop,x.atr);}
   }
   // entry / re-entry
   if(x.signal&&!x.held&&session&&Allowed(now)&&!FlatTime(x,now)&&q.bid>=ActiveStop(x)){
      if(x.lots<=0){double l=Lots(x,q.ask,x.stop);if(l>0&&Buy(x,l,"entry"))x.entries++;}
      else if(Buy(x,x.lots,"reentry"))x.reentries++;
   }
}

int OnInit(){
   string parts[];int n=StringSplit(InpSymbols,',',parts);if(n<1)return INIT_PARAMETERS_INCORRECT;
   if(InpEntryDays<2||InpExitDays<2||InpAtrDays<2||InpAtrMult<=0||InpRiskPct<=0||InpRiskPct>10||(InpDayTrading&&InpCloseMinNY>=InpOpenMinNY))return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
   ArrayResize(S,n);datetime now=TimeCurrent(),b=Boundary(now);
   for(int i=0;i<n;i++){S[i]=new CSym();S[i].s=parts[i];S[i].magic=InpMagic+i;if(!SymbolSelect(parts[i],true))return INIT_FAILED;
      // backfill completed New York days before the start
      datetime a=b-(datetime)(140*86400),cur=Boundary(a);
      while(cur<b){datetime nx=Boundary(cur+86400+3600);if(nx<=cur)nx=cur+86400;CompleteDay(S[i],cur,nx);cur=nx;}
      S[i].lastBoundary=b;SeedQuoteEnd(S[i],b-(datetime)(21*86400),b);
      PrintFormat("TURTLE_QSEED sym=%s min=%d,%d,%d,%d,%d,%d,%d",parts[i],S[i].qEndDow[0],S[i].qEndDow[1],S[i].qEndDow[2],S[i].qEndDow[3],S[i].qEndDow[4],S[i].qEndDow[5],S[i].qEndDow[6]);
      PrintFormat("TURTLE_SPEC sym=%s days=%d atr=%.5f entry=%.5f exit=%.5f contract=%.2f step=%.2f",parts[i],ArraySize(S[i].highs),S[i].atr,Ready(S[i])?EntryLevel(S[i]):0,Ready(S[i])?ExitLevel(S[i]):0,
         SymbolInfoDouble(parts[i],SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(parts[i],SYMBOL_VOLUME_STEP));
      for(int dw=0;dw<7;dw++){string segs="";datetime f=0,t=0;
         for(uint k=0;SymbolInfoSessionTrade(parts[i],(ENUM_DAY_OF_WEEK)dw,k,f,t);k++)segs+=StringFormat("%s%02d:%02d-%02d:%02d",k?",":"",(int)(f/3600),(int)(f%3600/60),(int)(t/3600),(int)(t%3600/60));
         PrintFormat("TURTLE_SESSION sym=%s dow=%d utc=%s",parts[i],dw,segs);}}
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpSeed);hwm=AccountInfoDouble(ACCOUNT_EQUITY);
   PrintFormat("TURTLE_CFG entry=%d exit=%d atr=%d mult=%.2f risk=%.2f day=%d close=%d open=%d random=%d p=%.5f seed=%d",InpEntryDays,InpExitDays,InpAtrDays,InpAtrMult,InpRiskPct,InpDayTrading,InpCloseMinNY,InpOpenMinNY,InpRandomEntries,InpRandomProb,InpSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   hwm=MathMax(hwm,AccountInfoDouble(ACCOUNT_EQUITY));
   for(int i=0;i<ArraySize(S);i++)Process(S[i]);
   datetime b=Boundary(TimeCurrent());
   if(b!=lastEquityDay){lastEquityDay=b;PrintFormat("TURTLE_DAY epoch=%I64d equity=%.2f balance=%.2f hwm=%.2f",(long)b,AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),hwm);}
}

void OnDeinit(const int reason){
   for(int i=0;i<ArraySize(S);i++){
      PrintFormat("TURTLE_SUMMARY sym=%s days=%I64d signals=%I64d entries=%I64d reentries=%I64d scheduled=%I64d sl_exits=%I64d flat_ends=%I64d fails=%I64d",
         S[i].s,S[i].ndays,S[i].breakouts,S[i].entries,S[i].reentries,S[i].scheduled,S[i].slExits,S[i].flatEnds,S[i].fails);
      delete S[i];}
}
