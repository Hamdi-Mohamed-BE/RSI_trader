#property strict
#property version "1.00"
#property description "3 Way Gold: XAUUSD momentum (H4), Donchian breakout (M15, London-NY overlap) and turn-of-month modules."
#property description "Settings locked to the 2026-09-30 optimised BEST version (QuantLab Gold Trio Pipeline). Research evidence only."
// Production build of `QuantLab Gold Trio Pipeline 2026-09-30/EA/TrioLogic.mqh` with the three frozen BEST cases.
// Trading logic is unchanged; additions: installer risk inputs, shared adaptive governor, server-to-UTC session clock,
// per-module enable switches. With InpServerUtcOffsetHours=0 in the tester it reproduces the research trades exactly.
#include <Trade/Trade.mqh>
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/_Shared/CalyxAdaptivePortfolio.mqh"

input group "3 Way Gold modules (locked optimised settings)"
input bool   InpEnableTrading=true;          // false: manage open positions only, no new entries
input bool   InpEnableMomentum=true;         // A: H4 time-series momentum
input bool   InpEnableBreakout=true;         // B: M15 Donchian breakout + volatility, London-NY overlap
input bool   InpEnableTurnOfMonth=true;      // C: long from the last trading day to trading day +2
input bool   InpMarketEntries=false;         // FTMO build only: A and B enter at market (the FTMO guard admits no pending orders)

input group "Risk (applied to EACH module trade)"
input double InpRiskPercent=1.0;             // % of equity per module trade; lots rounded UP to the broker step/minimum
input int    InpRiskMode=0;                  // 0 = percent of equity, 1 = fixed money per module trade
input double InpFixedRiskMoney=0.0;          // used when InpRiskMode=1
input bool   InpAdaptivePortfolioControls=false;

input group "Execution and clock"
input long   InpMagic=930930100;             // modules use InpMagic+0 (A), +1 (B), +2 (C)
input int    InpMaximumDeviationPoints=1000;
input bool   InpAutoServerUtcOffsetLive=true; // live: derive the server UTC offset from the terminal clock
input int    InpServerUtcOffsetHours=0;       // tester / manual offset (Exness servers are UTC = 0)
input datetime InpTradeFrom=0;                // tester only: no entries before this time (warm-up)
input bool   InpResearchLedger=false;         // tester only: write a per-position ledger to Common\Files

#define NF 23
#define MAXS 3
// module,tf,entry,offset,stop,sl,rr,trail,start,dist,exit,session,direction,filter,day,max_day,hold,flat,season,p1,p2,p3,p4
const double Cases[3][NF]={
 {0,240,2,0.5,0,3,0,3,0.5,1,3,0,0,1,1,0,0,0,0,24,0.5,50,1},     // A momentum: H4, limit 0.5 ATR, 3 ATR stop, no TP, 50% at 1R, ATR trail 1 ATR from 0.5R, EMA200 bias, no Monday
 {1,15,2,0.5,0,4,2.5,3,1,1.5,3,4,0,5,0,0,0,0,0,960,60,0.1,50}, // B breakout: M15, limit 0.5 ATR, 4 ATR stop, 2.5R, 50% at 1R, ATR trail 1.5 from 1R, overlap 12-16 UTC, spread filter
 {2,1440,0,0,0,2,2.5,1,0.5,0,0,0,0,0,1,0,0,0,0,-1,2,0,0}       // C turn of month: Day -1 entry, 2 D1-ATR stop, 2.5R, breakeven at 0.5R, no Monday, exit Day +2
};
CTrade trade;
double tickSize=0,lotStep=0,minLot=0;
struct Slot{int c;long magic;datetime lastBar,mgmtBar,lastClose,lastRetry,entryDayC,day,confTime;int dayEntries,entries,confSide;
 double trailDist,best,pendSL,confLevel;ulong posId;bool partialDone;int adxH,h4H,d1H,ema200H,ema20H;};
Slot S[MAXS];int NS=0;
int entryFails=0,closeFails=0,closeClosed=0,modifyFails=0,modifyClosed=0,cancelFails=0,skips=0,stale=0,trails=0,partialSkips=0,retries=0,partials=0;
struct Entry{ulong id;int slot;datetime time;int side;double risk,requestedRisk,sl,tp,volume,fill,atr;};
Entry initial[];
struct Memo{ulong order;int slot;double budget,atr;};
Memo memos[];

double F(int s,int k){if(k==6 && S[s].c<2 && InpRR05ModuleTarget>0)return InpRR05ModuleTarget;return Cases[S[s].c][k];}
int Mod(int s){return (int)F(s,0);}
ENUM_TIMEFRAMES TFof(int m){if(m==5)return PERIOD_M5;if(m==15)return PERIOD_M15;if(m==30)return PERIOD_M30;if(m==60)return PERIOD_H1;if(m==240)return PERIOD_H4;if(m==1440)return PERIOD_D1;return PERIOD_H1;}
ENUM_TIMEFRAMES TF(int s){return TFof((int)F(s,1));}
ENUM_TIMEFRAMES MTF(int s){return Mod(s)==2?PERIOD_H1:TF(s);}
string Name(int s){int m=Mod(s);return m==0?"MOM":(m==1?"BRK":"TOM");}
long ServerOffset(){
 if(!MQLInfoInteger(MQL_TESTER)&&InpAutoServerUtcOffsetLive){datetime srv=TimeTradeServer(),gmt=TimeGMT();if(srv>0&&gmt>0)return (long)MathRound((double)(srv-gmt)/3600.0)*3600;}
 return (long)InpServerUtcOffsetHours*3600;
}
datetime Utc(datetime server){return server-(datetime)ServerOffset();}
bool Own(int s,ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==S[s].magic)return true;}ticket=0;return false;}
bool OwnOrder(int s,ulong &ticket){for(int i=OrdersTotal()-1;i>=0;i--){ticket=OrderGetTicket(i);if(ticket&&OrderGetString(ORDER_SYMBOL)==_Symbol&&OrderGetInteger(ORDER_MAGIC)==S[s].magic)return true;}ticket=0;return false;}
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Session(datetime now,int &remaining){
 MqlDateTime dt;TimeToStruct(now,dt);int sec=(int)(now%86400);datetime a,b;remaining=0;
 for(uint i=0;i<20;i++){
  if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)dt.day_of_week,i,a,b))break;
  int lo=(int)((long)a%86400),hi=(int)((long)b%86400);if(hi==0)hi=86400;
  if(sec>=lo&&sec<hi){remaining=hi-sec;return true;}
 }
 return false;
}
double Average(const double &x[],int end,int n){double s=0;for(int i=end-n+1;i<=end;i++)s+=x[i];return s/n;}
void EMA(const MqlRates &r[],int n,int period,double &out[]){ArrayResize(out,n);out[0]=r[0].close;double a=2.0/(period+1);for(int i=1;i<n;i++)out[i]=a*r[i].close+(1-a)*out[i-1];}
void TR(const MqlRates &r[],int n,double &tr[]){ArrayResize(tr,n);tr[0]=r[0].high-r[0].low;for(int i=1;i<n;i++)tr[i]=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));}
double Highest(const MqlRates &r[],int from,int to){double h=-DBL_MAX;for(int i=from;i<=to;i++)h=MathMax(h,r[i].high);return h;}
double Lowest(const MqlRates &r[],int from,int to){double l=DBL_MAX;for(int i=from;i<=to;i++)l=MathMin(l,r[i].low);return l;}
double Buffer(int h,int b=0){double a[];if(h==INVALID_HANDLE)return 0;return CopyBuffer(h,b,1,1,a)==1?a[0]:0;}
int Sunday(int y,int mon,int nth){MqlDateTime d={};d.year=y;d.mon=mon;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+(nth-1)*7;}
datetime NY(datetime t){MqlDateTime d;TimeToStruct(t,d);int y=d.year;d.mon=3;d.day=Sunday(y,3,2);d.hour=7;d.min=d.sec=0;datetime a=StructToTime(d);d.mon=11;d.day=Sunday(y,11,1);d.hour=6;datetime b=StructToTime(d);return t+((t>=a&&t<b)?-4:-5)*3600;}
// Session filters are defined in UTC (research ran on a UTC server clock).
bool EntrySession(int s,datetime server){datetime t=Utc(server);int code=(int)F(s,11),u=(int)(t%86400),ny=(int)(NY(t)%86400);
 if(code==1)return u<28800;if(code==2)return u>=25200&&u<57600;if(code==3)return ny>=34200&&ny<57600;
 if(code==4)return u>=43200&&u<57600;if(code==5)return ny>=34200&&ny<39600;return true;}
int Month(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.year*12+d.mon;}
int TradingDayOfMonth(datetime day){MqlDateTime d;TimeToStruct(day,d);int k=0;for(datetime x=day-(d.day-1)*86400;x<=day;x+=86400){MqlDateTime y;TimeToStruct(x,y);if(y.day_of_week>=1&&y.day_of_week<=5)k++;}return k;}
int TradingDaysLeft(datetime day){MqlDateTime d;TimeToStruct(day,d);int k=0;datetime x=day+86400;MqlDateTime y;TimeToStruct(x,y);while(y.mon==d.mon){if(y.day_of_week>=1&&y.day_of_week<=5)k++;x+=86400;TimeToStruct(x,y);}return k;}
bool CalendarOK(int s,datetime t){MqlDateTime d;TimeToStruct(t,d);int season=(int)F(s,18),k=(int)F(s,14);
 if(season==1&&d.mon<10)return false;if(season==2&&d.mon<7)return false;
 if((k==1||k==3)&&d.day_of_week==1)return false;if((k==2||k==3)&&d.day_of_week==5)return false;return true;}
double CurrentATR(int s){MqlRates r[];if(CopyRates(_Symbol,MTF(s),1,15,r)!=15)return 0;double tr[];TR(r,15,tr);return Average(tr,14,14);}

bool FilterOK(int s,int side,double atr){
 int f=(int)F(s,13);if(f==0)return true;
 ENUM_TIMEFRAMES tf=Mod(s)==2?PERIOD_D1:TF(s);
 if(f==1){double e=Buffer(S[s].ema200H);return e>0&&side*(iClose(_Symbol,tf,1)-e)>0;}
 if(f==2){double e=Buffer(S[s].h4H);return e>0&&side*(iClose(_Symbol,PERIOD_H4,1)-e)>0;}
 if(f==3)return Buffer(S[s].adxH)>=20;
 if(f==4){MqlRates r[];int n=CopyRates(_Symbol,tf,1,130,r);if(n!=130)return false;double tr[];TR(r,n,tr);double now=Average(tr,n-1,14);int less=0;
  for(int j=n-101;j<n-1;j++)if(Average(tr,j,14)<now)less++;return less>=20&&less<=80;}
 if(f==5){MqlTick q;return SymbolInfoTick(_Symbol,q)&&q.ask-q.bid<=.1*atr;}
 if(f==6){double e=Buffer(S[s].d1H);return e>0&&side*(iClose(_Symbol,PERIOD_D1,1)-e)>0;}
 return true;
}

void Close(int s,string why){
 ulong ticket;if(!Own(s,ticket))return;datetime now=TimeCurrent();if(now-S[s].lastClose<30)return;S[s].lastClose=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
  uint c=trade.ResultRetcode();if(c==TRADE_RETCODE_POSITION_CLOSED&&!Own(s,ticket))return;
  if(c==TRADE_RETCODE_MARKET_CLOSED){closeClosed++;return;}
  closeFails++;PrintFormat("3WG_CLOSE_FAIL module=%s code=%u why=%s",Name(s),c,why);
 }
}

double StopFor(int s,int side,double entry,double atr,const MqlRates &r[],int n,double &sl){
 int type=(int)F(s,4);double v=F(s,5),dist=0;
 if(type==0)dist=v*atr;else if(type==1)dist=entry*v/100;
 if(type<=1){sl=Price(entry-side*dist);return dist;}
 int bars=type==2?5:20;if(n<bars){sl=0;return 0;}
 double ext=side>0?Lowest(r,n-bars,n-1):Highest(r,n-bars,n-1);sl=Price(ext-side*0.1*atr);return side*(entry-sl);
}

void Record(int s,ulong id,double budget,double atr){
 for(int i=0;i<ArraySize(initial);i++)if(initial[i].id==id)return;
 int k=ArraySize(initial);ArrayResize(initial,k+1);ZeroMemory(initial[k]);
 initial[k].id=id;initial[k].slot=s;initial[k].time=(datetime)PositionGetInteger(POSITION_TIME);initial[k].side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].fill=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);
 initial[k].requestedRisk=budget;initial[k].atr=atr;double p=0;
 if(OrderCalcProfit(initial[k].side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,initial[k].volume,initial[k].fill,initial[k].sl,p))initial[k].risk=-p;
 S[s].trailDist=MathAbs(initial[k].fill-initial[k].sl);S[s].best=initial[k].fill;S[s].posId=id;S[s].partialDone=false;S[s].pendSL=0;
}
// Re-attaching to a chart with an open position: recover trail state from the position itself.
void Capture(int s){ulong t;if(!Own(s,t))return;ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);if(id==S[s].posId)return;
 double budget=0,atr=0;for(int i=0;i<ArraySize(memos);i++)if(memos[i].order==id){budget=memos[i].budget;atr=memos[i].atr;break;}
 Record(s,id,budget,atr);}

double RiskBudget(int s){
 double base=InpRiskMode==1?InpFixedRiskMoney:AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 return base*CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,S[s].magic);
}

bool Enter(int s,int side,double atr,datetime signalTime,const MqlRates &r[],int n){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0||atr<=0){skips++;return false;}
 int m=Mod(s);
 int kind=m==2?0:(int)F(s,2);if(kind==1||InpMarketEntries)kind=0;bool pending=kind>=2;
 double entry=side>0?q.ask:q.bid;if(pending)entry=Price(entry+side*(kind==3?1:-1)*F(s,3)*atr);
 double sl=0,dist=StopFor(s,side,entry,atr,r,n,sl);if(dist<=0||sl<=0){skips++;return false;}
 double rr=F(s,6),tp=rr>0?Price(entry+side*dist*rr):0,unit=0,margin=0;
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(type,_Symbol,1,entry,sl,unit)||unit>=0){skips++;return false;}
 double goal=RiskBudget(s);if(goal<=0){skips++;return false;}
 double volume=MathMax(minLot,MathCeil((goal/-unit-1e-10)/lotStep)*lotStep);volume=NormalizeDouble(volume,8);
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=pending?entry:(side>0?q.bid:q.ask);
 if(volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||side*(ref-sl)<MathMax(gap,tickSize)||(tp>0&&side*(tp-ref)<gap)||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return false;}
 if(pending){double mkt=side>0?q.ask:q.bid;if((kind==3?side*(entry-mkt):side*(mkt-entry))<MathMax(gap,tickSize)){skips++;return false;}}
 trade.SetExpertMagicNumber(S[s].magic);bool ok=false;string cm="3WG "+Name(s);
 if(!pending)ok=side>0?trade.Buy(volume,_Symbol,0,sl,tp,cm):trade.Sell(volume,_Symbol,0,sl,tp,cm);
 else{datetime expiry=TimeCurrent()+4*PeriodSeconds(TF(s));
  if(kind==3)ok=side>0?trade.BuyStop(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,cm):trade.SellStop(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,cm);
  else ok=side>0?trade.BuyLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,cm):trade.SellLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,cm);}
 uint code=trade.ResultRetcode();
 if(!ok||(code!=TRADE_RETCODE_DONE&&code!=TRADE_RETCODE_PLACED)){entryFails++;PrintFormat("3WG_ENTRY_FAIL module=%s code=%u",Name(s),code);return false;}
 S[s].dayEntries++;S[s].entries++;
 if(pending){int k=ArraySize(memos);ArrayResize(memos,k+1);memos[k].order=trade.ResultOrder();memos[k].slot=s;memos[k].budget=goal;memos[k].atr=atr;return true;}
 ulong ticket;if(!Own(s,ticket)){entryFails++;return false;}
 Record(s,(ulong)PositionGetInteger(POSITION_IDENTIFIER),goal,atr);
 return true;
}

void Modify(int s,ulong ticket,double want,double tp){
 if(trade.PositionModify(ticket,want,tp)&&trade.ResultRetcode()==TRADE_RETCODE_DONE){trails++;S[s].pendSL=0;return;}
 uint c=trade.ResultRetcode();
 if(c==TRADE_RETCODE_MARKET_CLOSED){modifyClosed++;S[s].pendSL=want;return;}   // retried after the reopen
 if(c!=TRADE_RETCODE_NO_CHANGES&&c!=TRADE_RETCODE_POSITION_CLOSED){modifyFails++;PrintFormat("3WG_MODIFY_FAIL module=%s code=%u",Name(s),c);}
}

void Trail(int s,const MqlRates &bar){
 ulong ticket;if(!Own(s,ticket)||S[s].trailDist<=0)return;int type=(int)F(s,7);if(type==0)return;
 long ptype=PositionGetInteger(POSITION_TYPE);double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 if(bar.time+PeriodSeconds(MTF(s))<=(datetime)PositionGetInteger(POSITION_TIME))return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 int side=ptype==POSITION_TYPE_BUY?1:-1;
 S[s].best=side>0?MathMax(S[s].best,bar.high):MathMin(S[s].best,bar.low);
 double R=S[s].trailDist;if(side*(S[s].best-open)<F(s,8)*R)return;
 double want=0;
 if(type==1)want=open;
 else if(type==2)want=S[s].best-side*R;
 else if(type==3){double a=CurrentATR(s);if(a<=0)return;want=S[s].best-side*F(s,9)*a;}
 else if(type==4)want=S[s].best-side*S[s].best*F(s,9)/100;
 else if(type==5){want=Buffer(S[s].ema20H);if(want<=0)return;}
 want=Price(want);
 if(side>0){if(want<=sl+tickSize/2||q.bid-want<MathMax(gap,tickSize))return;}
 else{if((sl>0&&want>=sl-tickSize/2)||want-q.ask<MathMax(gap,tickSize))return;}
 Modify(s,ticket,want,tp);
}

void Manage(int s,datetime now){
 Capture(s);ulong ticket;int remaining=0;bool session=Session(now,remaining);MqlDateTime dt;TimeToStruct(now,dt);
 int flat=(int)F(s,17);bool flatNow=session&&remaining<=900&&(flat==1||(flat==2&&dt.day_of_week==5));
 ulong ot;if(flatNow&&OwnOrder(s,ot)){if(!trade.OrderDelete(ot))cancelFails++;}
 if(!Own(s,ticket)){S[s].pendSL=0;return;}
 if(flatNow){Close(s,"flat");return;}
 if((int)F(s,10)==1&&F(s,16)>0&&now-(datetime)PositionGetInteger(POSITION_TIME)>=(long)F(s,16)*PeriodSeconds(TF(s))){Close(s,"time");return;}
 int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double open=PositionGetDouble(POSITION_PRICE_OPEN);
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double price=side>0?q.bid:q.ask;
 if((int)F(s,10)==3&&!S[s].partialDone&&S[s].trailDist>0&&side*(price-open)>=S[s].trailDist){
  double vol=PositionGetDouble(POSITION_VOLUME),part=NormalizeDouble(MathFloor((vol*.5+1e-12)/lotStep)*lotStep,8);
  if(part>=minLot&&vol-part>=minLot){if(trade.PositionClosePartial(ticket,part)&&trade.ResultRetcode()==TRADE_RETCODE_DONE){S[s].partialDone=true;partials++;}else if(trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED)closeFails++;}
  else{S[s].partialDone=true;partialSkips++;}
  if(!Own(s,ticket))return;
 }
 if(S[s].pendSL>0&&session&&now-S[s].lastRetry>=60){
  S[s].lastRetry=now;double sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),want=S[s].pendSL,gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
  bool tighter=side>0?want>sl+tickSize/2:(sl<=0||want<sl-tickSize/2);bool valid=side*(price-want)>=MathMax(gap,tickSize);
  if(!tighter||!valid)S[s].pendSL=0;else{retries++;Modify(s,ticket,want,tp);}
 }
}

bool CanOpen(int s,datetime now,datetime barOpen){
 int remaining=0;if(!InpEnableTrading)return false;if(InpTradeFrom>0&&now<InpTradeFrom)return false;if(now-barOpen>=300){stale++;return false;}
 if(!Session(now,remaining)||remaining<1800)return false;
 MqlDateTime dt;TimeToStruct(now,dt);if(dt.day_of_week<1||dt.day_of_week>5)return false;
 if(!EntrySession(s,now)||!CalendarOK(s,now))return false;
 if(F(s,15)>0&&S[s].dayEntries>=(int)F(s,15))return false;
 return true;
}

int SignalA(int s,const MqlRates &r[],int n,double &atr){
 double tr[],e[];TR(r,n,tr);EMA(r,n,(int)F(s,21),e);int z=n-1;atr=Average(tr,z,14);if(atr<=0)return 0;
 int L=(int)F(s,19);double k=F(s,20);bool brk=F(s,22)>0;double ret=r[z].close-r[z-L].close;int side=0;
 if(ret>k*atr&&e[z]>e[z-1]&&(!brk||r[z].close>Highest(r,z-L,z-1)))side=1;
 if(ret<-k*atr&&e[z]<e[z-1]&&(!brk||r[z].close<Lowest(r,z-L,z-1)))side=-1;
 return side;
}
int SignalB(int s,const MqlRates &r[],int n,double &atr){
 double tr[];TR(r,n,tr);int z=n-1,vw=(int)F(s,22),R=(int)F(s,19),N=(int)F(s,20);double edge=F(s,21);
 atr=Average(tr,z,14);if(atr<=0)return 0;bool expanding=true;
 if(vw>0){double sum=0;for(int i=z-vw+1;i<=z;i++)sum+=Average(tr,i,14);expanding=atr>sum/vw;}
 double hi=Highest(r,z-R,z-1),lo=Lowest(r,z-R,z-1),range=hi-lo;if(range<=0)return 0;double pos=(r[z].close-lo)/range;
 int side=0;
 if(expanding&&r[z].close>Highest(r,z-N,z-1)&&pos>=1-edge)side=1;
 if(expanding&&r[z].close<Lowest(r,z-N,z-1)&&pos<=edge)side=-1;
 return side;
}
int Bars4(int s){if(Mod(s)==0)return 600;int need=(int)F(s,19)+(int)F(s,22)+30;return need>700?need:700;}
bool DirectionOK(int s,int side){int d=(int)F(s,12);return !((d==1&&side<0)||(d==2&&side>0));}

void ModuleAB(int s,datetime now){
 int sec=PeriodSeconds(TF(s));datetime bar=now-now%sec;if(bar==S[s].lastBar)return;S[s].lastBar=bar;
 int want=Bars4(s);MqlRates r[];int n=CopyRates(_Symbol,TF(s),1,want,r);if(n!=want){stale++;return;}
 if(r[n-1].time+sec!=bar)return;
 ulong t;if(Own(s,t)){Trail(s,r[n-1]);return;}
 if(OwnOrder(s,t))return;
 if(S[s].confTime>0){
  int cs=S[s].confSide;bool fire=r[n-1].time>S[s].confTime&&cs*(r[n-1].close-S[s].confLevel)>0;S[s].confTime=0;
  if(fire&&CanOpen(s,now,bar)){double tr[];TR(r,n,tr);double atr=Average(tr,n-1,14);Enter(s,cs,atr,r[n-1].time,r,n);}
  return;
 }
 if(!CanOpen(s,now,bar))return;
 double atr=0;int side=Mod(s)==0?SignalA(s,r,n,atr):SignalB(s,r,n,atr);
 if(side==0||!DirectionOK(s,side)||!FilterOK(s,side,atr))return;
 if((int)F(s,2)==1){S[s].confTime=r[n-1].time;S[s].confSide=side;S[s].confLevel=side>0?r[n-1].high:r[n-1].low;return;}
 Enter(s,side,atr,r[n-1].time,r,n);
}

void ModuleC(int s,datetime now){
 datetime day=now-now%86400;MqlDateTime dt;TimeToStruct(now,dt);if(dt.day_of_week<1||dt.day_of_week>5)return;
 int td=TradingDayOfMonth(day);ulong t;int remaining=0;bool session=Session(now,remaining);
 int before=(int)MathRound(-F(s,19)),exitTd=(int)MathRound(F(s,20));
 if(Own(s,t)){
  datetime opened=(datetime)PositionGetInteger(POSITION_TIME);datetime openedDay=opened-opened%86400;
  bool rolled=Month(day)!=Month(openedDay);
  bool exitDay=rolled&&td==exitTd,late=(rolled&&td>exitTd)||day-openedDay>10*86400;
  if((exitDay&&session&&remaining<=900)||late)Close(s,exitDay?"day-exit":"late-exit");
  return;
 }
 if(!InpEnableTrading||(InpTradeFrom>0&&now<InpTradeFrom)||day==S[s].entryDayC||!session||remaining<3600)return;
 double hour=F(s,21);if(hour>0&&(now%86400)<(long)(hour*3600))return;
 if(TradingDaysLeft(day)!=before-1)return;
 S[s].entryDayC=day;
 if(!CalendarOK(s,now))return;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_D1,1,30,r);if(n!=30){stale++;return;}
 double tr[];TR(r,n,tr);double atr=Average(tr,n-1,14);if(atr<=0)return;
 if(!FilterOK(s,1,atr))return;
 Enter(s,1,atr,day,r,n);
}
void TrailC(int s,datetime now){
 if((int)F(s,7)==0)return;int sec=3600;datetime bar=now-now%sec;if(bar==S[s].mgmtBar)return;S[s].mgmtBar=bar;
 ulong t;if(!Own(s,t))return;MqlRates r[];if(CopyRates(_Symbol,PERIOD_H1,1,1,r)!=1)return;if(r[0].time+sec!=bar)return;Trail(s,r[0]);
}

int OnInit(){
 if(InpRiskMode<0||InpRiskMode>1||(InpRiskMode==0&&(InpRiskPercent<=0||InpRiskPercent>10))||(InpRiskMode==1&&InpFixedRiskMoney<=0))return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("3 Way Gold needs a hedging account: its three modules hold independent positions.");return INIT_FAILED;}
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(tickSize<=0||lotStep<=0||minLot<=0)return INIT_FAILED;
 bool on[3];on[0]=InpEnableMomentum;on[1]=InpEnableBreakout;on[2]=InpEnableTurnOfMonth;NS=0;
 for(int i=0;i<3;i++){
  ZeroMemory(S[i]);S[i].c=i;S[i].magic=InpMagic+i;
  S[i].adxH=S[i].h4H=S[i].d1H=S[i].ema200H=S[i].ema20H=INVALID_HANDLE;
 }
 for(int i=0;i<3;i++){if(!on[i])continue;
  if(NS!=i){S[NS]=S[i];}
  int f=(int)Cases[i][13];ENUM_TIMEFRAMES tf=(int)Cases[i][0]==2?PERIOD_D1:TFof((int)Cases[i][1]);
  if(f==1)S[NS].ema200H=iMA(_Symbol,tf,200,0,MODE_EMA,PRICE_CLOSE);if(f==2)S[NS].h4H=iMA(_Symbol,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE);
  if(f==3)S[NS].adxH=iADX(_Symbol,tf,14);if(f==6)S[NS].d1H=iMA(_Symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);
  NS++;
  if((int)Cases[i][7]==5)S[NS-1].ema20H=iMA(_Symbol,MTF(NS-1),20,0,MODE_EMA,PRICE_CLOSE);
 }
 if(NS==0){Print("3 Way Gold: all modules disabled.");return INIT_PARAMETERS_INCORRECT;}
 trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
 PrintFormat("3WG_SPEC symbol=%s modules=%d%d%d market_entries=%d risk=%s%.4f adaptive=%d utc_offset_h=%d magic=%I64d",_Symbol,InpEnableMomentum,InpEnableBreakout,InpEnableTurnOfMonth,InpMarketEntries,
  InpRiskMode==1?"USD ":"% ",InpRiskMode==1?InpFixedRiskMoney:InpRiskPercent,InpAdaptivePortfolioControls,(int)(ServerOffset()/3600),InpMagic);
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();datetime day=now-now%86400;
 for(int s=0;s<NS;s++){
  if(S[s].day!=day){S[s].day=day;S[s].dayEntries=0;}
  Manage(s,now);
  if(Mod(s)==2){ModuleC(s,now);TrailC(s,now);}else ModuleAB(s,now);
 }
}
struct Item{ulong id;long magic;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){
 if(!InpResearchLedger)return 0;
 HistorySelect(0,TimeCurrent());Item rows[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){
  ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;rows[k].magic=HistoryDealGetInteger(deal,DEAL_MAGIC);}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 FolderCreate("Calyx3WayGold",FILE_COMMON);
 int f=FileOpen("Calyx3WayGold\\ledger.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","module","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 for(int k=0;k<n;k++){
  int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double p=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;int m=(int)(rows[k].magic-InpMagic);
  string nm=m==0?"A_MOM":(m==1?"B_BRK":(m==2?"C_TOM":"?"));
  FileWrite(f,rows[k].id,nm,(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,ix>=0?initial[ix].sl:0,ix>=0?initial[ix].tp:0,ix>=0?initial[ix].requestedRisk:0,ix>=0?initial[ix].risk:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p);
 }
 FileClose(f);return 0;
}
void OnDeinit(const int reason){
 for(int s=0;s<NS;s++){IndicatorRelease(S[s].adxH);IndicatorRelease(S[s].h4H);IndicatorRelease(S[s].d1H);IndicatorRelease(S[s].ema200H);IndicatorRelease(S[s].ema20H);}
 PrintFormat("3WG_SUMMARY slots=%d entryFails=%d closeFails=%d closeClosed=%d modifyFails=%d modifyClosed=%d cancelFails=%d skips=%d stale=%d trails=%d retries=%d partials=%d",NS,entryFails,closeFails,closeClosed,modifyFails,modifyClosed,cancelFails,skips,stale,trails,retries,partials);
}
