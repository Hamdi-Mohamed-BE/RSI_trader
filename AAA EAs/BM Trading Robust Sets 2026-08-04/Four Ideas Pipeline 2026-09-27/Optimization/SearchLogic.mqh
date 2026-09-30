// Conditional research extension for the USDJPY morning-range survivor only.
// Existing raw source remains immutable; OFF uses its original event handlers.
#define OnInit OriginalInit
#define OnTick OriginalTick
#define OnDeinit OriginalDeinit
#define OnTradeTransaction OriginalTransaction
#include "..\..\Four Screenshot Ideas Raw 2026-09-27\FourIdeas.mq5"
#undef OnInit
#undef OnTick
#undef OnDeinit
#undef OnTradeTransaction
input int InpCase=0;
input bool InpForceExtended=false;
// tf,entry,stop,stopDistance,trail,startR,trailDistance,exit,RR,rangeStart,rangeEnd,
// sessionEnd,direction,filter,excludedDay,maxDay,reentry,maxBars,rangeBuffer,atrPeriod
int pEntry,pStop,pTrail,pExit,pDirection,pFilter,pDay,pMaxDay,pReentry,pBars,pATR;
int pStart,pEnd,pFlat,pFills=0;
double pStopD,pTrailStart,pTrailD,pRR,pBuffer;
ENUM_TIMEFRAMES pTF;
int hATR=INVALID_HANDLE,hEMA=INVALID_HANDLE,hHTF=INVALID_HANDLE,hADX=INVALID_HANDLE;
bool base=false,rearm=false,partialDone=false;
datetime signalSeen=0,manageBar=0;
ulong activeTicket=0;
double initialR=0,initialSL=0,highest=0,lowest=0;

double Buffer(int handle,int which=0,int shift=1){double x[];return CopyBuffer(handle,which,shift,1,x)==1?x[0]:0;}
bool Allowed(int side){
 if(pDirection!=0 && pDirection!=side)return false;
 MqlDateTime d;TimeToStruct(Clock(TimeCurrent()),d);
 if((pDay==1 && d.day_of_week==1)||(pDay==2 && d.day_of_week==5)||(pDay==3 && (d.day_of_week==1||d.day_of_week==5)))return false;
 if(pFilter==0)return true;
 if(pFilter==1)return side*(Buffer(hEMA,0,1)-Buffer(hEMA,0,2))>0;
 if(pFilter==2)return side*(iClose(_Symbol,PERIOD_H1,1)-Buffer(hHTF))>0;
 if(pFilter==3)return Buffer(hADX,0)>=20;
 if(pFilter==4)return side*(Buffer(hADX,1)-Buffer(hADX,2))>0;
 if(pFilter==5){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return false;double a=Buffer(hATR);return a>0 && q.ask-q.bid<=.1*a;}
 return false;
}
double StopFor(int side,double entry){
 double value=side>0?rangeLow:rangeHigh,atr=Buffer(hATR);
 if(pStop==1)value=entry-side*pStopD*atr;
 if(pStop==2)value=entry-side*pStopD*_Point;
 if(pStop==3)value=entry-side*entry*pStopD/100.;
 if(pStop==4)value=side>0?iLow(_Symbol,pTF,1):iHigh(_Symbol,pTF,1);
 if(pStop==5){MqlRates r[];if(CopyRates(_Symbol,pTF,1,5,r)!=5)return 0;value=side>0?r[0].low:r[0].high;for(int i=1;i<5;i++)value=side>0?MathMin(value,r[i].low):MathMax(value,r[i].high);}
 return Outward(value,side);
}
double TargetFor(int side,double entry,double sl){
 if(pExit==1 || pExit==5)return entry+side*pRR*MathAbs(entry-sl);
 if(pExit==2)return side>0?iHigh(_Symbol,PERIOD_D1,1):iLow(_Symbol,PERIOD_D1,1);
 return 0;
}
bool ExtendedEnter(int side,bool pending,double level,bool limit){
 if(!Allowed(side))return false;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return false;
 double entry=pending?Price(level):(side>0?q.ask:q.bid),sl=StopFor(side,entry);
 if(sl<=0 || side*(entry-sl)<=0)return false;
 double tp=TargetFor(side,entry,sl);if(tp!=0)tp=Price(tp);
 if(!limit)return Enter(side,sl,tp,pending,level,"Morning");
 double gap=MathMax(tickSize,SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);
 if(side*(entry-(side>0?q.ask:q.bid))>-gap || side*(entry-sl)<gap || (tp!=0 && side*(tp-entry)<gap))return false;
 double lots=Lots(side,entry,sl),margin=0;
 if(lots<=0 || !OrderCalcMargin(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return false;
 bool ok=side>0?trade.BuyLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Ideas Retest"):trade.SellLimit(lots,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,"Ideas Retest");
 return ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_PLACED);
}
void Manage(){
 ulong tk=0;if(!OwnPosition(tk)){activeTicket=0;return;}
 if(tk!=activeTicket){
  activeTicket=tk;initialSL=PositionGetDouble(POSITION_SL);initialR=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-initialSL);
  highest=lowest=PositionGetDouble(POSITION_PRICE_OPEN);partialDone=false;manageBar=0;
 }
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double price=side>0?q.bid:q.ask,entry=PositionGetDouble(POSITION_PRICE_OPEN);
 highest=MathMax(highest,price);lowest=MathMin(lowest,price);
 if(pBars>0 && TimeCurrent()-PositionGetInteger(POSITION_TIME)>=pBars*PeriodSeconds(pTF)){Close();return;}
 datetime bar=iTime(_Symbol,pTF,0);if(bar==manageBar)return;manageBar=bar;
 if(initialR<=0)return;
 double gain=side*(price-entry),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
 if(pExit==5 && !partialDone && gain>=initialR){
  double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),volume=PositionGetDouble(POSITION_VOLUME);
  double closeVolume=MathFloor((volume*.5)/step+1e-8)*step;
  if(closeVolume>=minimum && volume-closeVolume>=minimum){if(trade.PositionClosePartial(tk,closeVolume))partialDone=true;}
  else partialDone=true;
 }
 if(pTrail==0 || gain<pTrailStart*initialR)return;
 double next=sl,atr=Buffer(hATR);
 if(pTrail==1)next=entry;
 if(pTrail==2)next=price-side*pTrailD*atr;
 if(pTrail==3)next=price-side*price*pTrailD/100.;
 if(pTrail==4)next=Buffer(hEMA);
 if(pTrail==5){MqlRates r[];if(CopyRates(_Symbol,pTF,1,5,r)!=5)return;next=side>0?r[0].low:r[0].high;for(int i=1;i<5;i++)next=side>0?MathMin(next,r[i].low):MathMax(next,r[i].high);}
 if(pTrail==6)next=(side>0?highest:lowest)-side*pTrailD*atr;
 if(pTrail==7)next=entry+side*MathMax(0,MathFloor((gain/initialR-.5)/.5)*.5+.2)*initialR;
 next=Outward(next,side);
 double gap=MathMax(tickSize,SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);
 if(side*(next-sl)>=tickSize*.99 && side*(price-next)>gap)trade.PositionModify(tk,next,tp);
}
void ExtendedTick(){
 datetime now=TimeCurrent();ulong tk=0;
 if(OwnPosition(tk)){traded=true;Cancel();Manage();}
 datetime minute=now-now%60;if(minute==lastMinute)return;lastMinute=minute;
 datetime local=Clock(now);MqlDateTime d;TimeToStruct(local,d);int m=Minute(local),key=Key(local);
 if(key!=dayKey){Cancel();dayKey=key;acted=false;traded=false;rangeReady=false;rangeHigh=rangeLow=0;lastM5=0;signalSeen=0;pFills=0;rearm=false;}
 if(dueExit>0 && local>=dueExit){Close();Cancel();if(!OwnPosition(tk))dueExit=0;}
 if(d.day_of_week==0 || d.day_of_week==6 || OwnPosition(tk))return;
 if(m>=pFlat){Cancel();return;}
 if(m<pEnd || pFills>=pMaxDay || (traded && !rearm))return;
 datetime midnight=local-m*60-d.sec;
 if(!acted){
  // The range must be known at the exact scheduled end, identical to raw.
  if(m!=pEnd)return;
  acted=true;rangeReady=Range(now,pStart,pEnd);if(!rangeReady)return;
 }
 if(!rangeReady)return;
 dueExit=midnight+pFlat*60;
 if(pEntry==0){
  if(m!=pEnd && !rearm)return;rearm=false;
  double pad=pBuffer*Buffer(hATR);
  ExtendedEnter(1,true,rangeHigh+pad,false);ExtendedEnter(-1,true,rangeLow-pad,false);return;
 }
 MqlRates b[];if(CopyRates(_Symbol,pTF,1,2,b)!=2 || b[1].time==signalSeen)return;signalSeen=b[1].time;
 if(Minute(Clock(b[1].time))<pEnd || b[1].time+PeriodSeconds(pTF)>now)return;
 int side=b[1].close>rangeHigh?1:b[1].close<rangeLow?-1:0;if(side==0)return;
 if(pEntry==2 && !(side>0?b[0].close>rangeHigh:b[0].close<rangeLow))return;
 if(pEntry==3 || pEntry==4){
  if(OrdersTotal()>0)return;
  double offset=pEntry==3?10*_Point:.25*Buffer(hATR);
  double level=(side>0?rangeHigh:rangeLow)-side*offset;
  ExtendedEnter(side,true,level,true);
 }else ExtendedEnter(side,false,0,false);
 rearm=false;
}
int OnInit(){
 if(InpCase<0 || InpCase>=ArrayRange(Cases,0) || InpMode!=1 || InpControl)return INIT_PARAMETERS_INCORRECT;
 pTF=(ENUM_TIMEFRAMES)(int)Cases[InpCase][0];pEntry=(int)Cases[InpCase][1];pStop=(int)Cases[InpCase][2];pStopD=Cases[InpCase][3];
 pTrail=(int)Cases[InpCase][4];pTrailStart=Cases[InpCase][5];pTrailD=Cases[InpCase][6];pExit=(int)Cases[InpCase][7];pRR=Cases[InpCase][8];
 pStart=(int)Cases[InpCase][9];pEnd=(int)Cases[InpCase][10];pFlat=(int)Cases[InpCase][11];pDirection=(int)Cases[InpCase][12];
 pFilter=(int)Cases[InpCase][13];pDay=(int)Cases[InpCase][14];pMaxDay=(int)Cases[InpCase][15];pReentry=(int)Cases[InpCase][16];pBars=(int)Cases[InpCase][17];pBuffer=Cases[InpCase][18];pATR=(int)Cases[InpCase][19];
 if(pStart<0 || pStart>=pEnd || pEnd>=pFlat || pFlat>=1440)return INIT_PARAMETERS_INCORRECT;
 base=pEntry==0 && pStop==0 && pTrail==0 && pExit==0 && pStart==180 && pEnd==360 && pFlat==1080 && pDirection==0 && pFilter==0 && pDay==0 && pMaxDay==1 && pReentry==0 && pBars==0 && pBuffer==0;
 int ok=OriginalInit();if(ok!=INIT_SUCCEEDED)return ok;
 hATR=iATR(_Symbol,pTF,pATR);hEMA=iMA(_Symbol,pTF,50,0,MODE_EMA,PRICE_CLOSE);hHTF=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);hADX=iADX(_Symbol,pTF,14);
 if(hATR==INVALID_HANDLE||hEMA==INVALID_HANDLE||hHTF==INVALID_HANDLE||hADX==INVALID_HANDLE)return INIT_FAILED;
 return INIT_SUCCEEDED;
}
void OnTick(){if(base && !InpForceExtended)OriginalTick();else ExtendedTick();}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &req,const MqlTradeResult &res){
 OriginalTransaction(tx,req,res);
 if(tx.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(tx.deal) || HistoryDealGetInteger(tx.deal,DEAL_MAGIC)!=InpMagic)return;
 if(HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_IN)pFills++;
 if(HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_OUT && HistoryDealGetInteger(tx.deal,DEAL_REASON)==DEAL_REASON_SL && pReentry!=0 && pFills<pMaxDay)rearm=true;
}
void OnDeinit(const int reason){OriginalDeinit(reason);if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR);if(hEMA!=INVALID_HANDLE)IndicatorRelease(hEMA);if(hHTF!=INVALID_HANDLE)IndicatorRelease(hHTF);if(hADX!=INVALID_HANDLE)IndicatorRelease(hADX);}
double OnTester(){
 HistorySelect(0,TimeCurrent());ulong ids[];double pnl[];int n=0;
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong ticket=HistoryDealGetTicket(i);if(HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic)continue;
  ulong id=(ulong)HistoryDealGetInteger(ticket,DEAL_POSITION_ID);if(id==0)continue;
  int j=0;for(j=0;j<n;j++)if(ids[j]==id)break;
  if(j==n){ArrayResize(ids,n+1);ArrayResize(pnl,n+1);ids[n]=id;pnl[n]=0;n++;}
  pnl[j]+=HistoryDealGetDouble(ticket,DEAL_PROFIT)+HistoryDealGetDouble(ticket,DEAL_COMMISSION)+HistoryDealGetDouble(ticket,DEAL_SWAP);
 }
 double gp=0,gl=0;for(int i=0;i<n;i++){if(pnl[i]>0)gp+=pnl[i];else gl-=pnl[i];}
 double pf=gl>0?gp/gl:0,net=gp-gl,dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
 if(n<60 || pf<=1 || net<=0)return -1000;
 return MathMin(pf,3)*MathSqrt(n/100.)*(net/10000.)/(.05+dd/100.);
}
