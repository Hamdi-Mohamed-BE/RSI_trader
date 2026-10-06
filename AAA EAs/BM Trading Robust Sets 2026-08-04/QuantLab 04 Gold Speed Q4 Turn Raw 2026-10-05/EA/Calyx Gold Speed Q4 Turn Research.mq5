#property strict
#property version "1.00"
#property description "Tester-only public-idea gold reconstruction. ALL numeric rules OURS. PROTOCOL.txt 2026-10-05."
#include <Trade/Trade.mqh>
input int InpModules=7; // 1=adaptive H4, 2=Q4 H1, 4=month-turn
input bool InpBreakoutQ4Only=true;
input bool InpControl=false;         // A/B/D random direction; C mid-month window
input double InpRiskPercent=1.0;
input uint InpSeed=20261005;
input datetime InpTradeFrom=D'2025.10.05';
input string InpTag="smoke";
input long InpMagic=1005040;

#define NMOD 3
CTrade trade;
double tickSize=0,lotStep=0,minLot=0;
datetime lastBar[NMOD],lastTrace=0,lastClose[NMOD],lastDay=0;
double trailDist[NMOD],bestPrice[NMOD];
int trace=INVALID_HANDLE,signalFile=INVALID_HANDLE;
int entries[NMOD],entryFails=0,closeFails=0,modifyFails=0,skips=0,stale=0,trails=0,minlotSkips=0;
struct Entry {ulong id;int module;datetime time;int side;double risk,requestedRisk,sl,tp,volume,fill,atr;};
Entry initial[];
string Name(int m){return m==0?"A_SPEED":(m==1?"B_Q4":"C_TURN");}
bool On(int m){return (InpModules&(1<<m))!=0;}
long Magic(int m){return InpMagic+m;}
bool Own(int m,ulong &ticket){
 for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==Magic(m))return true;}
 ticket=0;return false;
}
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Session(datetime now,int &remaining){
 MqlDateTime dt;TimeToStruct(now,dt);int s=(int)(now%86400);datetime a,b;remaining=0;
 for(uint i=0;i<20;i++){
  if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)dt.day_of_week,i,a,b))break;
  int lo=(int)((long)a%86400),hi=(int)((long)b%86400);if(hi==0)hi=86400;
  if(s>=lo && s<hi){remaining=hi-s;return true;}
 }
 return false;
}
uint Hash(uint x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}
double Average(const double &x[],int end,int n){double s=0;for(int i=end-n+1;i<=end;i++)s+=x[i];return s/n;}
void EMA(const MqlRates &r[],int n,int period,double &out[]){ArrayResize(out,n);out[0]=r[0].close;double a=2.0/(period+1);for(int i=1;i<n;i++)out[i]=a*r[i].close+(1-a)*out[i-1];}
void TR(const MqlRates &r[],int n,double &tr[]){ArrayResize(tr,n);tr[0]=r[0].high-r[0].low;for(int i=1;i<n;i++)tr[i]=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));}
double Highest(const MqlRates &r[],int from,int to){double h=-DBL_MAX;for(int i=from;i<=to;i++)h=MathMax(h,r[i].high);return h;}
double Lowest(const MqlRates &r[],int from,int to){double l=DBL_MAX;for(int i=from;i<=to;i++)l=MathMin(l,r[i].low);return l;}

void Close(int m,string why){
 int remaining=0;if(!Session(TimeCurrent(),remaining))return;
 ulong ticket;if(!Own(m,ticket))return;datetime now=TimeCurrent();if(now-lastClose[m]<30)return;lastClose[m]=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
  if(trade.ResultRetcode()==TRADE_RETCODE_POSITION_CLOSED && !Own(m,ticket)){Print("GS_CLOSE_RACE already closed");return;}
  closeFails++;PrintFormat("GS_CLOSE_FAIL module=%s code=%u why=%s",Name(m),trade.ResultRetcode(),why);
 }
}

// Opens a position for module m. rawSide is the rule's direction; the control replaces it with a seeded coin flip.
bool Enter(int m,int rawSide,double distance,double rr,datetime signalTime,double atr){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0||distance<=0){skips++;return false;}
 int remaining=0;if(!Session(TimeCurrent(),remaining)){skips++;return false;}
 int s=rawSide;
 if(InpControl && m!=2)s=((Hash((uint)(signalTime/60)+InpSeed+(uint)m)&1)==1)?1:-1;
 double entry=s>0?q.ask:q.bid,sl=Price(entry-s*distance),tp=rr>0?Price(entry+s*distance*rr):0,unit=0,margin=0;
 ENUM_ORDER_TYPE type=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(type,_Symbol,1,entry,sl,unit)||unit>=0){skips++;return false;}
 double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 double volume=MathFloor((goal/-unit+1e-10)/lotStep)*lotStep;
 if(volume<minLot-1e-10){minlotSkips++;return false;}
 volume=NormalizeDouble(volume,8);double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=s>0?q.bid:q.ask;
 if(volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||s*(ref-sl)<MathMax(gap,tickSize)||(tp>0&&s*(tp-ref)<gap)||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return false;}
 trade.SetExpertMagicNumber(Magic(m));
 bool ok=s>0?trade.Buy(volume,_Symbol,0,sl,tp,"GS_"+Name(m)):trade.Sell(volume,_Symbol,0,sl,tp,"GS_"+Name(m));
 if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){entryFails++;PrintFormat("GS_ENTRY_FAIL module=%s code=%u",Name(m),trade.ResultRetcode());return false;}
 ulong ticket;if(!Own(m,ticket)){entryFails++;return false;}
 int k=ArraySize(initial);ArrayResize(initial,k+1);ZeroMemory(initial[k]);
 initial[k].id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);initial[k].module=m;initial[k].time=(datetime)PositionGetInteger(POSITION_TIME);initial[k].side=s;
 initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].fill=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);
 initial[k].requestedRisk=goal;initial[k].atr=atr;
 double actual=0;if(OrderCalcProfit(type,_Symbol,initial[k].volume,initial[k].fill,initial[k].sl,actual))initial[k].risk=-actual;
 double quoted=0;if(!OrderCalcProfit(type,_Symbol,initial[k].volume,entry,sl,quoted)){Print("GS_AUDIT_FAILED profit calculation");return false;}
 PrintFormat("GS_ENTRY position=%I64u module=%s requested=%.8f quote_stop_cash=%.8f actual_stop_cash=%.8f",initial[k].id,Name(m),goal,-quoted,initial[k].risk);
 trailDist[m]=MathAbs(initial[k].fill-initial[k].sl);bestPrice[m]=initial[k].fill;
 FileWrite(signalFile,initial[k].id,Name(m),(long)signalTime,(long)TimeCurrent(),rawSide,s,atr,distance,entry,initial[k].fill,q.ask-q.bid);
 entries[m]++;return true;
}

// Trail from +1R at the initial stop distance behind the best closed-bar extreme; tighten only.
void Trail(int m,const MqlRates &bar){
 int remaining=0;if(!Session(TimeCurrent(),remaining))return;
 ulong ticket;if(!Own(m,ticket)||trailDist[m]<=0)return;
 long type=PositionGetInteger(POSITION_TYPE);double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 if(bar.time+PeriodSeconds(m==0?PERIOD_H4:PERIOD_H1)<=(datetime)PositionGetInteger(POSITION_TIME))return;  // bar closed before the entry
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if(type==POSITION_TYPE_BUY){
  bestPrice[m]=MathMax(bestPrice[m],bar.high);if(bestPrice[m]-open<trailDist[m])return;
  double want=Price(bestPrice[m]-trailDist[m]);if(want<=sl+tickSize/2||q.bid-want<MathMax(gap,tickSize))return;
  if(trade.PositionModify(ticket,want,tp)&&trade.ResultRetcode()==TRADE_RETCODE_DONE)trails++;else{modifyFails++;PrintFormat("GS_MODIFY_FAIL module=%s code=%u",Name(m),trade.ResultRetcode());}
 }else{
  bestPrice[m]=MathMin(bestPrice[m],bar.low);if(open-bestPrice[m]<trailDist[m])return;
  double want=Price(bestPrice[m]+trailDist[m]);if((sl>0&&want>=sl-tickSize/2)||want-q.ask<MathMax(gap,tickSize))return;
  if(trade.PositionModify(ticket,want,tp)&&trade.ResultRetcode()==TRADE_RETCODE_DONE)trails++;else{modifyFails++;PrintFormat("GS_MODIFY_FAIL module=%s code=%u",Name(m),trade.ResultRetcode());}
 }
}

bool NewBar(int m,ENUM_TIMEFRAMES tf,datetime now,datetime &barOpen){
 int sec=PeriodSeconds(tf);barOpen=now-now%sec;if(barOpen==lastBar[m])return false;lastBar[m]=barOpen;return true;
}
bool CanOpen(datetime now,datetime barOpen){
 int remaining=0;if(now<InpTradeFrom)return false;if(now-barOpen>=300){stale++;return false;}
 if(!Session(now,remaining)||remaining<1800)return false;
 MqlDateTime dt;TimeToStruct(now,dt);return dt.day_of_week>=1&&dt.day_of_week<=5;
}

void ModuleA(datetime now){
 datetime bar;if(!NewBar(0,PERIOD_H4,now,bar))return;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_H4,1,600,r);if(n!=600){stale++;return;}
 if(r[n-1].time+14400!=bar)return;
 ulong t;if(Own(0,t)){Trail(0,r[n-1]);return;}
 if(!CanOpen(now,bar))return;
 double tr[],e[],a[];TR(r,n,tr);EMA(r,n,100,e);int z=n-1;ArrayResize(a,n);ArrayInitialize(a,0);
 for(int i=13;i<n;i++)a[i]=Average(tr,i,14);
 double atr=a[z],avgAtr=Average(a,z,50);if(atr<=0)return;
 int lookback=atr>avgAtr?6:24;
 double ret=r[z].close-r[z-lookback].close;int side=0;
 double hi=Highest(r,z-lookback,z-1),lo=Lowest(r,z-lookback,z-1);
 if(ret>0.5*atr&&e[z]>e[z-1]&&r[z].close>hi)side=1;
 if(ret<-0.5*atr&&e[z]<e[z-1]&&r[z].close<lo)side=-1;
 if(side!=0 && Enter(0,side,2.5*atr,0,r[z].time,atr))
  PrintFormat("GS_A bar=%s lookback=%d atr=%.10f atr_mean=%.10f close=%.10f old_close=%.10f ema=%.10f prev_ema=%.10f high=%.10f low=%.10f raw=%d",TimeToString(r[z].time,TIME_DATE|TIME_MINUTES),lookback,atr,avgAtr,r[z].close,r[z-lookback].close,e[z],e[z-1],hi,lo,side);
}

void ModuleB(datetime now){
 datetime bar;if(!NewBar(1,PERIOD_H1,now,bar))return;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_H1,1,700,r);if(n!=700){stale++;return;}
 if(r[n-1].time+3600!=bar)return;
 ulong t;if(Own(1,t)){Trail(1,r[n-1]);return;}
 if(!CanOpen(now,bar))return;
 MqlDateTime dt;TimeToStruct(now,dt);if(InpBreakoutQ4Only&&dt.mon<10)return;
 double tr[],a[];TR(r,n,tr);int z=n-1;ArrayResize(a,n);ArrayInitialize(a,0);
 for(int i=13;i<n;i++)a[i]=Average(tr,i,14);
 double atr=a[z],avgAtr=Average(a,z,50);if(atr<=0)return;bool expanding=atr>avgAtr;
 double hi=Highest(r,z-480,z-1),lo=Lowest(r,z-480,z-1),range=hi-lo;if(range<=0)return;double pos=(r[z].close-lo)/range;
 double bh=Highest(r,z-60,z-1),bl=Lowest(r,z-60,z-1);int side=0;
 if(expanding&&r[z].close>bh&&pos>=0.9)side=1;
 if(expanding&&r[z].close<bl&&pos<=0.1)side=-1;
 if(side!=0 && Enter(1,side,2.0*atr,2.5,r[z].time,atr))
  PrintFormat("GS_B bar=%s atr=%.10f atr_mean=%.10f close=%.10f range_high=%.10f range_low=%.10f break_high=%.10f break_low=%.10f raw=%d",TimeToString(r[z].time,TIME_DATE|TIME_MINUTES),atr,avgAtr,r[z].close,hi,lo,bh,bl,side);
}

// Weekday-based trading-day calendar (broker holidays are not modelled).
int TradingDayOfMonth(datetime day){MqlDateTime d;TimeToStruct(day,d);int k=0;for(datetime x=day-(d.day-1)*86400;x<=day;x+=86400){MqlDateTime y;TimeToStruct(x,y);if(y.day_of_week>=1&&y.day_of_week<=5)k++;}return k;}
bool LastTradingDay(datetime day){MqlDateTime d;TimeToStruct(day,d);datetime x=day+86400;MqlDateTime y;TimeToStruct(x,y);while(y.day_of_week==0||y.day_of_week==6){x+=86400;TimeToStruct(x,y);}return y.mon!=d.mon;}
datetime entryDayC=0;
int Month(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.year*12+d.mon;}
void ModuleC(datetime now){
 datetime day=now-now%86400;MqlDateTime dt;TimeToStruct(now,dt);if(dt.day_of_week<1||dt.day_of_week>5)return;
 int td=TradingDayOfMonth(day);ulong t;int remaining=0;bool session=Session(now,remaining);
 if(Own(2,t)){
  datetime opened=(datetime)PositionGetInteger(POSITION_TIME);datetime openedDay=opened-opened%86400;
  bool rolled=Month(day)!=Month(openedDay);   // raw: entered on the last trading day, so the month has rolled over
  bool exitDay,late;
  if(InpControl){exitDay=!rolled&&td==12;late=rolled||td>12;}
  else{exitDay=rolled&&td==2;late=(rolled&&td>2)||day-openedDay>10*86400;}
  if((exitDay&&session&&remaining<=900)||late)Close(2,exitDay?"day-exit":"late-exit");
  return;
 }
 if(now<InpTradeFrom||day==entryDayC||!session||remaining<3600)return;
 bool entryDay=InpControl?(td==10):LastTradingDay(day);if(!entryDay)return;
 entryDayC=day;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_D1,1,30,r);if(n!=30){stale++;return;}
 double tr[];TR(r,n,tr);double atr=Average(tr,n-1,14);if(atr<=0)return;
 Enter(2,1,2.0*atr,0,day,atr);
}

int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY; tester required");return INIT_FAILED;}
 if(InpModules<=0||InpModules>7||InpRiskPercent<=0||InpRiskPercent>1.0)return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("GS_REQUIRES_HEDGING");return INIT_FAILED;}
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(tickSize<=0||lotStep<=0||minLot<=0)return INIT_FAILED;
 ArrayInitialize(lastBar,0);ArrayInitialize(lastClose,0);ArrayInitialize(trailDist,0);ArrayInitialize(bestPrice,0);ArrayInitialize(entries,0);
 trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 FolderCreate("CalyxGoldSpeed20261005",FILE_COMMON);
 trace=FileOpen("CalyxGoldSpeed20261005\\"+InpTag+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 signalFile=FileOpen("CalyxGoldSpeed20261005\\"+InpTag+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(trace==INVALID_HANDLE||signalFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(trace,"time","balance","equity");
 FileWrite(signalFile,"position_id","module","signal_time","fill_time","raw_side","actual_side","atr","stop_distance","quote","fill","spread");
 PrintFormat("GS_SPEC symbol=%s broker=%s server=%s demo=%d currency=%s contract=%.8f min=%.8f step=%.8f tick=%.8f modules=%d q4=%d control=%d",_Symbol,AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO,AccountInfoString(ACCOUNT_CURRENCY),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),minLot,lotStep,tickSize,InpModules,InpBreakoutQ4Only,InpControl);
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();
 datetime slot=now-now%300;if(slot!=lastTrace){lastTrace=slot;if(now>=InpTradeFrom)FileWrite(trace,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 if(On(0))ModuleA(now);
 if(On(1))ModuleB(now);
 if(On(2))ModuleC(now);

}
struct Item {ulong id;long magic;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){
 HistorySelect(0,TimeCurrent());Item rows[];int n=0;
 int df=FileOpen("CalyxGoldSpeed20261005\\\\"+InpTag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(df==INVALID_HANDLE)return -999;
 FileWrite(df,"deal","position_id","order","entry","type","epoch","volume","price","gross","commission","swap","fee");
 for(int j=0;j<HistoryDealsTotal();j++){
  ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  FileWrite(df,deal,HistoryDealGetInteger(deal,DEAL_POSITION_ID),HistoryDealGetInteger(deal,DEAL_ORDER),HistoryDealGetInteger(deal,DEAL_ENTRY),type,HistoryDealGetInteger(deal,DEAL_TIME),HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE));
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;rows[k].magic=HistoryDealGetInteger(deal,DEAL_MAGIC);}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen("CalyxGoldSpeed20261005\\"+InpTag+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","module","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 for(int k=0;k<n;k++){
  int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double net=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;int m=(int)(rows[k].magic-InpMagic);
  FileWrite(f,rows[k].id,(m>=0&&m<NMOD)?Name(m):"?",(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,ix>=0?initial[ix].sl:0,ix>=0?initial[ix].tp:0,ix>=0?initial[ix].requestedRisk:0,ix>=0?initial[ix].risk:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,net);
 }
 FileClose(f);FileClose(df);return TesterStatistics(STAT_PROFIT_FACTOR);
}
void OnDeinit(const int why){
 if(trace!=INVALID_HANDLE)FileClose(trace);if(signalFile!=INVALID_HANDLE)FileClose(signalFile);
 PrintFormat("GS_SUMMARY A=%d B=%d C=%d entryFails=%d closeFails=%d modifyFails=%d skips=%d minlot_skips=%d stale=%d trails=%d",entries[0],entries[1],entries[2],entryFails,closeFails,modifyFails,skips,minlotSkips,stale,trails);
}
