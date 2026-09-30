// Isolated research extension. Immutable baseline is included for parity/provenance.
#define OnInit RawInit
#define OnTick RawTick
#define OnTester RawTester
#define OnDeinit RawDeinit
#include "RawCore.mqh"
#undef OnInit
#undef OnTick
#undef OnTester
#undef OnDeinit
input int InpCase=0;
// tf,entry,offset,stop,sl,rr,trail,start,dist,exit,session,direction,filter,day,
// max_day,max_pos,reentry,hold,weekend,flat,atr,fast,slow,pullback,lookback,slope,cutoff
double C(int k){return Cases[InpCase][k];}
ENUM_TIMEFRAMES TF(){int t=(int)C(0);return (ENUM_TIMEFRAMES)(t<60?t:t==60?PERIOD_H1:PERIOD_H4);}
string Tag(){return InpTag+"-"+(string)InpCase;}
string Dir="CalyxNasdaqTrend20260929\\";
datetime engineBar=0,engineDay=0,m15Bar=0;int attempts=0,modifyFails=0,cancelFails=0,partialSkips=0;
double currentATR=0,currentEMA=0;int adxH=INVALID_HANDLE,htfH=INVALID_HANDLE;
datetime confirmTime=0;int confirmSide=0;double confirmLevel=0;
struct Memo {ulong order;double budget,atr,quote,spread;datetime signal;int rawSide,side;};Memo orders[];
double peak[];bool partial[];datetime lastExit[];
bool Selected(){return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;}
int Count(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0&&Selected())n++;
 for(int i=OrdersTotal()-1;i>=0;i--)if(OrderGetTicket(i)>0&&OrderGetString(ORDER_SYMBOL)==_Symbol&&OrderGetInteger(ORDER_MAGIC)==InpMagic)n++;return n;}
int FindEntry(ulong id){for(int i=0;i<ArraySize(initial);i++)if(initial[i].id==id)return i;return -1;}
void Capture(){for(int j=PositionsTotal()-1;j>=0;j--){ulong ticket=PositionGetTicket(j);if(!ticket||!Selected())continue;
 ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);if(FindEntry(id)>=0)continue;
 int k=ArraySize(initial),mi=-1;for(int v=0;v<ArraySize(orders);v++)if(orders[v].order==id){mi=v;break;}
 ArrayResize(initial,k+1);ArrayResize(peak,k+1);ArrayResize(partial,k+1);ArrayResize(lastExit,k+1);ZeroMemory(initial[k]);
 initial[k].id=id;initial[k].time=(datetime)PositionGetInteger(POSITION_TIME);initial[k].side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].fill=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);
 initial[k].requestedRisk=mi>=0?orders[mi].budget:0;initial[k].atr=mi>=0?orders[mi].atr:currentATR;
 double p=0;if(OrderCalcProfit(initial[k].side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,initial[k].volume,initial[k].fill,initial[k].sl,p))initial[k].risk=-p;
 peak[k]=initial[k].fill;partial[k]=false;lastExit[k]=0;
 if(signalFile!=INVALID_HANDLE)FileWrite(signalFile,id,mi>=0?(long)orders[mi].signal:0,(long)initial[k].time,mi>=0?orders[mi].rawSide:0,initial[k].side,initial[k].atr,initial[k].requestedRisk,initial[k].risk,mi>=0?orders[mi].quote:0,initial[k].fill,mi>=0?orders[mi].spread:0);
}}
int Sunday(int y,int mon,int nth){MqlDateTime d={};d.year=y;d.mon=mon;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+(nth-1)*7;}
datetime NY(datetime t){MqlDateTime d;TimeToStruct(t,d);int y=d.year;d.mon=3;d.day=Sunday(y,3,2);d.hour=7;d.min=d.sec=0;datetime a=StructToTime(d);d.mon=11;d.day=Sunday(y,11,1);d.hour=6;datetime b=StructToTime(d);return t+((t>=a&&t<b)?-4:-5)*3600;}
bool EntrySession(datetime t){int s=(int)C(10),u=(int)(t%86400),ny=(int)(NY(t)%86400);
 if(s==0)return u>=25200&&u<61200;if(s==1)return u<28800;if(s==2)return u>=25200&&u<57600;
 if(s==3)return ny>=34200&&ny<57600;if(s==4)return u>=43200&&u<57600;if(s==5)return ny>=34200&&ny<39600;return true;}
bool Flat(datetime now){MqlDateTime d;TimeToStruct(now,d);int rem=0;bool session=Session(now,rem);
 if(C(19)>0&&(now%86400>=C(26)*3600||(session&&rem<=300)))return true;
 if(C(18)==0&&((d.day_of_week==5&&now%86400>=C(26)*3600)||d.day_of_week==6||d.day_of_week==0))return true;
 if((int)C(9)==5&&!EntrySession(now))return true;return false;}
bool DayAllowed(datetime t){MqlDateTime d;TimeToStruct(t,d);if(d.day_of_week==0||d.day_of_week==6)return false;int k=(int)C(13);
 return !((k==1||k==3)&&d.day_of_week==1)&&!((k==2||k==3)&&d.day_of_week==5);}
double Extreme(bool high,int bars){MqlRates r[];if(CopyRates(_Symbol,TF(),1,bars,r)!=bars)return 0;double v=high?-DBL_MAX:DBL_MAX;
 for(int i=0;i<bars;i++)v=high?MathMax(v,r[i].high):MathMin(v,r[i].low);return v;}
double Buffer(int h,int b=0){double a[];return CopyBuffer(h,b,1,1,a)==1?a[0]:0;}
int RegimeState(MqlRates &r[],int i){double ret=r[i].close/r[i-20].close-1;return ret<-.005?0:ret>.005?2:1;}
bool RegimeAllows(MqlRates &r[],int side){int n=ArraySize(r),counts[3][3];ArrayInitialize(counts,0);
 for(int j=n-253;j<=n-2;j++)counts[RegimeState(r,j-1)][RegimeState(r,j)]++;
 int state=RegimeState(r,n-1),total=counts[state][0]+counts[state][1]+counts[state][2];
 return total>=20&&side*(counts[state][2]-counts[state][0])>0;}
int GetSignal(MqlRates &r[],double &atr,double &ema20){int n=ArraySize(r),z=n-1;double tr[],sum[],em[],slowema[],e20[],trendSlow[];ArrayResize(tr,n);ArrayResize(sum,n+1);sum[0]=0;
 for(int j=0;j<n;j++){tr[j]=j==0?r[j].high-r[j].low:MathMax(r[j].high-r[j].low,MathMax(MathAbs(r[j].high-r[j-1].close),MathAbs(r[j].low-r[j-1].close)));sum[j+1]=sum[j]+tr[j];}
 atr=(sum[n]-sum[n-(int)C(20)])/C(20);EMA(r,n,(int)C(21),em);EMA(r,n,(int)C(22),trendSlow);EMA(r,n,(int)C(23),e20);ema20=e20[z];if(atr<=0)return 0;
 bool longTouch=false,shortTouch=false;for(int j=z-(int)C(24);j<z;j++){if(r[j].low<=e20[j])longTouch=true;if(r[j].high>=e20[j])shortTouch=true;}
 int side=0;if(em[z]>trendSlow[z]&&em[z]>em[z-(int)C(25)]&&longTouch&&r[z].close>r[z-1].high&&r[z].close>e20[z])side=1;
 if(em[z]<trendSlow[z]&&em[z]<em[z-(int)C(25)]&&shortTouch&&r[z].close<r[z-1].low&&r[z].close<e20[z])side=-1;
 if(side==0)return 0;int f=(int)C(12);
 if(f==1){EMA(r,n,200,slowema);if(side*(r[z].close-slowema[z])<=0)return 0;}
 if(f==2&&side*(iClose(_Symbol,PERIOD_H4,1)-Buffer(htfH))<=0)return 0;
 if(f==3&&Buffer(adxH)<20)return 0;if(f==4&&side*(Buffer(adxH,1)-Buffer(adxH,2))<=0)return 0;
 if(f==5){int less=0;for(int j=z-100;j<z;j++)if((sum[j+1]-sum[j+1-(int)C(20)])/C(20)<atr)less++;if(less<20||less>80)return 0;}
 if(f==6){MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask-q.bid>.1*atr)return 0;}
 if(f==7&&!RegimeAllows(r,side))return 0;return side;}
bool LastLossStop(datetime now){HistorySelect(now-now%86400,now);for(int j=HistoryDealsTotal()-1;j>=0;j--){ulong d=HistoryDealGetTicket(j);
 if(HistoryDealGetInteger(d,DEAL_MAGIC)==InpMagic&&HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_OUT)return HistoryDealGetInteger(d,DEAL_REASON)==DEAL_REASON_SL&&HistoryDealGetDouble(d,DEAL_PROFIT)<0;}return false;}
bool Capacity(datetime now){int limit=(int)C(14);if(C(16)>0&&attempts==limit&&LastLossStop(now))limit++;return attempts<limit&&Count()<(int)C(15);}
void Submit(int raw,datetime sig,double atr){datetime now=TimeCurrent();if(!Capacity(now)||Flat(now)||!EntrySession(now)||!DayAllowed(now))return;
 if((C(11)==1&&raw<0)||(C(11)==2&&raw>0))return;attempts++;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;int s=InpControl?((Hash((uint)(now/86400)+InpSeed)&1)==1?1:-1):raw;
 int kind=(int)C(1);bool pending=kind>=2;double entry=s>0?q.ask:q.bid;
 if(pending)entry=Price(entry+s*(kind==4?1:-1)*(kind==3?C(2):C(2)*atr));
 double distance=C(4)*atr;int stop=(int)C(3);if(stop==1)distance=entry*C(4)/100;if(stop==2)distance=C(4);
 double sl=entry-s*distance;if(stop>=3)sl=Extreme(s<0,stop==3?1:stop==4?5:20)-s*.1*atr;sl=Price(sl);double risk=s*(entry-sl);
 if(risk<=0){skips++;return;}double tp=Price(entry+s*C(5)*(stop==0?distance:risk));int ex=(int)C(9);
 if(ex==1||ex==3||ex==5)tp=0;if(ex==2){tp=Price(Extreme(s>0,20));if(s*(tp-entry)<=0){skips++;return;}}
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=pending?entry:s>0?q.bid:q.ask;
 if(s*(ref-sl)<MathMax(gap,tickSize)||(tp>0&&s*(tp-ref)<gap)){skips++;return;}
 if(pending&&((kind==4?s*(entry-(s>0?q.ask:q.bid)):s*((s>0?q.ask:q.bid)-entry))<MathMax(gap,tickSize))){skips++;return;}
 double unit=0,margin=0;ENUM_ORDER_TYPE type=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,unit)||unit>=0){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100/C(15),volume=NormalizeDouble(MathMax(minLot,MathCeil((budget/-unit-1e-10)/lotStep)*lotStep),8);
 if(volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 datetime expiry=now+4*PeriodSeconds(TF());if(C(19)>0)expiry=(datetime)MathMin(expiry,now-now%86400+C(26)*3600);bool ok=false;
 if(!pending)ok=s>0?trade.Buy(volume,_Symbol,0,sl,tp,"NasdaqTrend"):trade.Sell(volume,_Symbol,0,sl,tp,"NasdaqTrend");
 else if(kind==4)ok=s>0?trade.BuyStop(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,"NasdaqTrend"):trade.SellStop(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,"NasdaqTrend");
 else ok=s>0?trade.BuyLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,"NasdaqTrend"):trade.SellLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,"NasdaqTrend");
 if(!ok||(trade.ResultRetcode()!=TRADE_RETCODE_DONE&&trade.ResultRetcode()!=TRADE_RETCODE_PLACED)){entryFails++;return;}
 int k=ArraySize(orders);ArrayResize(orders,k+1);orders[k].order=trade.ResultOrder();orders[k].budget=budget;orders[k].atr=atr;orders[k].quote=entry;orders[k].spread=q.ask-q.bid;orders[k].signal=sig;orders[k].rawSide=raw;orders[k].side=s;entries++;Capture();}
void Manage(datetime now,bool newBar,bool newM15){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;bool flat=Flat(now);
 if(flat)for(int j=OrdersTotal()-1;j>=0;j--){ulong o=OrderGetTicket(j);if(o&&OrderGetString(ORDER_SYMBOL)==_Symbol&&OrderGetInteger(ORDER_MAGIC)==InpMagic)if(!trade.OrderDelete(o))cancelFails++;}
 for(int j=PositionsTotal()-1;j>=0;j--){ulong ticket=PositionGetTicket(j);if(!ticket||!Selected())continue;int k=FindEntry((ulong)PositionGetInteger(POSITION_IDENTIFIER));if(k<0)continue;
 if(flat||(C(17)>0&&now-initial[k].time>=C(17)*60)){
  if(now-lastExit[k]>=60){lastExit[k]=now;bool ok=trade.PositionClose(ticket);uint code=trade.ResultRetcode();if((!ok||code!=TRADE_RETCODE_DONE)&&code!=TRADE_RETCODE_POSITION_CLOSED)closeFails++;}continue;}
 int s=initial[k].side;double open=initial[k].fill,risk=s*(open-initial[k].sl),price=s>0?q.bid:q.ask,favor=s*(price-open);if(risk<=0)continue;
 peak[k]=s>0?MathMax(peak[k],price):MathMin(peak[k],price);
 if((int)C(9)==4&&!partial[k]&&favor>=risk){double vol=PositionGetDouble(POSITION_VOLUME),part=NormalizeDouble(MathFloor((vol*.5+1e-12)/lotStep)*lotStep,8);
  if(part>=minLot&&vol-part>=minLot){if(trade.PositionClosePartial(ticket,part)&&trade.ResultRetcode()==TRADE_RETCODE_DONE)partial[k]=true;else closeFails++;}else{partial[k]=true;partialSkips++;}
  if(!PositionSelectByTicket(ticket))continue;}
 int trail=(int)C(6);if(trail==0)continue;double sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),candidate=sl;
 if(trail==7&&newM15){double ref=initial[k].tp>0?MathAbs(initial[k].tp-open):risk;if(s*(iClose(_Symbol,PERIOD_M15,1)-open)>=.5*ref)candidate=open+s*.2*ref;}
 else if(trail!=7&&favor>=C(7)*risk&&(newBar||trail==1)){
  if(trail==1)candidate=open;if(trail==2&&currentATR>0)candidate=price-s*C(8)*currentATR;
  if(trail==3)candidate=price-s*price*C(8)/100;if(trail==4&&currentEMA>0)candidate=currentEMA;
  if(trail==5)candidate=Extreme(s<0,5);if(trail==6&&currentATR>0)candidate=peak[k]-s*C(8)*currentATR;}
 candidate=Price(candidate);double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
 if(candidate>0&&s*(candidate-sl)>tickSize*.5&&s*(price-candidate)>=MathMax(gap,tickSize)){
  bool ok=trade.PositionModify(ticket,candidate,tp);uint code=trade.ResultRetcode();if((!ok||code!=TRADE_RETCODE_DONE)&&code!=TRADE_RETCODE_NO_CHANGES&&code!=TRADE_RETCODE_POSITION_CLOSED)modifyFails++;}
 }}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER)||InpCase<0||InpCase>=ArrayRange(Cases,0)||InpRiskPercent<=0||InpRiskPercent>1)return INIT_FAILED;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);if(tickSize<=0||lotStep<=0||minLot<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);FolderCreate("CalyxNasdaqTrend20260929",FILE_COMMON);
 adxH=iADX(_Symbol,TF(),14);htfH=iMA(_Symbol,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE);if(adxH==INVALID_HANDLE||htfH==INVALID_HANDLE)return INIT_FAILED;
 if(!MQLInfoInteger(MQL_OPTIMIZATION)){
  trace=FileOpen(Dir+Tag()+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');signalFile=FileOpen(Dir+Tag()+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(trace==INVALID_HANDLE||signalFile==INVALID_HANDLE)return INIT_FAILED;
  FileWrite(trace,"time","balance","equity");FileWrite(signalFile,"position_id","signal_time","fill_time","raw_side","side","atr","requested_risk","actual_risk","quote","fill","spread");
  PrintFormat("GV_SPEC broker=%s server=%s demo=%d symbol=%s contract=%.8f min=%.8f step=%.8f",AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO,_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),minLot,lotStep);}
 return INIT_SUCCEEDED;}
void OnTick(){datetime now=TimeCurrent();Capture();datetime day=now-now%86400;if(day!=engineDay){engineDay=day;attempts=0;confirmTime=0;}
 datetime bar=iTime(_Symbol,TF(),0),m15=iTime(_Symbol,PERIOD_M15,0);bool newBar=bar!=engineBar;Manage(now,newBar,m15!=m15Bar);m15Bar=m15;
 datetime minute=now-now%60;if(minute!=lastMinute){lastMinute=minute;if(trace!=INVALID_HANDLE&&now>=InpTradeFrom)FileWrite(trace,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 if(!newBar)return;engineBar=bar;if(now<InpTradeFrom||now-bar>=300)return;
 bool entryOK=Capacity(now)&&!Flat(now)&&EntrySession(now)&&DayAllowed(now);int remain=0;entryOK=entryOK&&Session(now,remain)&&remain>=1800;
 if(!entryOK&&Count()==0)return;
 MqlRates r[];int n=400;if(CopyRates(_Symbol,TF(),1,n,r)!=n||r[n-1].time+PeriodSeconds(TF())!=bar){stale++;return;}
 int side=GetSignal(r,currentATR,currentEMA);if(!entryOK)return;
 if(confirmTime>0){if(r[n-1].time>confirmTime&&confirmSide*(r[n-1].close-confirmLevel)>0)Submit(confirmSide,r[n-1].time,currentATR);confirmTime=0;return;}
 if(side==0)return;if((int)C(1)==1){confirmTime=r[n-1].time;confirmSide=side;confirmLevel=side>0?r[n-1].high:r[n-1].low;return;}Submit(side,r[n-1].time,currentATR);}
double OnTester(){HistorySelect(0,TimeCurrent());Item rows[];int n=0,boundary=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;string comment=HistoryDealGetString(deal,DEAL_COMMENT);if(StringFind(comment,"end of test")>=0)boundary++;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);}
 int f=FileOpen(Dir+Tag()+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 double gp=0,gl=0,net=0;int wins=0,badRisk=0;
 for(int k=0;k<n;k++){int ix=FindEntry(rows[k].id);double p=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;net+=p;if(p>0){gp+=p;wins++;}else gl-=p;
  if(ix<0||initial[ix].risk<=0||initial[ix].requestedRisk<=0)badRisk++;
  FileWrite(f,rows[k].id,(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,ix>=0?initial[ix].sl:0,ix>=0?initial[ix].tp:0,ix>=0?initial[ix].requestedRisk:0,ix>=0?initial[ix].risk:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,p);}
 FileClose(f);double pf=gl>0?gp/gl:gp>0?99:0,dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);int failures=entryFails+closeFails+modifyFails+cancelFails+badRisk+boundary;
 double score=n<60||failures>0?-1000:net>0?(pf-1)*MathSqrt(n)/(1+dd/10):-1-MathAbs(net)/10000-dd/100;
 f=FileOpen(Dir+Tag()+"-net.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 FileWriteString(f,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"balance_dd_pct\":%.8f,\"score\":%.8f,\"entry_fail\":%d,\"close_fail\":%d,\"modify_fail\":%d,\"cancel_fail\":%d,\"bad_risk\":%d,\"boundary\":%d,\"partial_skips\":%d,\"constraint_skips\":%d}",n,net,pf,n>0?100.0*wins/n:0,dd,TesterStatistics(STAT_BALANCE_DDREL_PERCENT),score,entryFails,closeFails,modifyFails,cancelFails,badRisk,boundary,partialSkips,skips));FileClose(f);return score;}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);if(signalFile!=INVALID_HANDLE)FileClose(signalFile);IndicatorRelease(adxH);IndicatorRelease(htfH);}
