// Research-only extension; frozen raw level builder is included verbatim.
#define OnInit LC_RawInit
#define OnTick LC_RawTick
#define OnDeinit LC_RawDeinit
#include "RawCore.mqh"
#undef OnInit
#undef OnTick
#undef OnDeinit
input int InpCase=0;
input int InpStrategy=0; // 0 touch, 1 retest (parity), 2 both
double C(int k){return Cases[InpCase][k];}
ENUM_TIMEFRAMES TF(){int t=(int)C(0);return (ENUM_TIMEFRAMES)(t<60?t:t==60?PERIOD_H1:t==240?PERIOD_H4:PERIOD_D1);}
int ema50=INVALID_HANDLE,ema20=INVALID_HANDLE,htf=INVALID_HANDLE,adx=INVALID_HANDLE;
datetime signalBar=0,signalDay=0,m15bar=0;
int dailyEntries=0;bool touchUsed[8],retryUsed[8];datetime formedSeen[8],confirmAt[8];
ulong savedTickets[];double savedRisk[];bool partialDone[];datetime exitAttempt[];
int EngineCount(){return InpStrategy==2?2:1;}
long Magic(int e){return InpMagic+e;}
bool SelectedOwn(){long m=PositionGetInteger(POSITION_MAGIC);return PositionGetString(POSITION_SYMBOL)==_Symbol && (m==InpMagic || (InpStrategy==2 && m==InpMagic+1));}
int Engine(){return (int)(PositionGetInteger(POSITION_MAGIC)-InpMagic);}
int Track(ulong ticket){for(int j=0;j<ArraySize(savedTickets);j++)if(savedTickets[j]==ticket)return j;
 int n=ArraySize(savedTickets);ArrayResize(savedTickets,n+1);ArrayResize(savedRisk,n+1);ArrayResize(partialDone,n+1);ArrayResize(exitAttempt,n+1);
 savedTickets[n]=ticket;savedRisk[n]=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));partialDone[n]=false;exitAttempt[n]=0;return n;}
int CountEngine(int e){int n=0;for(int j=PositionsTotal()-1;j>=0;j--){if(PositionGetTicket(j)>0 && SelectedOwn() && Engine()==e)n++;}
 for(int j=OrdersTotal()-1;j>=0;j--){if(OrderGetTicket(j)>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==Magic(e))n++;}return n;}
double Buf(int handle,int buffer=0,int shift=1){double a[];return CopyBuffer(handle,buffer,shift,1,a)==1?a[0]:0;}
int Sunday(int y,int m,int nth){MqlDateTime d={};d.year=y;d.mon=m;d.day=1;datetime t=StructToTime(d);TimeToStruct(t,d);return 1+(7-d.day_of_week)%7+(nth-1)*7;}
datetime NY(datetime t){MqlDateTime d;TimeToStruct(t,d);int y=d.year;d.mon=3;d.day=Sunday(y,3,2);d.hour=7;d.min=d.sec=0;datetime a=StructToTime(d);d.mon=11;d.day=Sunday(y,11,1);d.hour=6;datetime b=StructToTime(d);return t+((t>=a && t<b)?-4:-5)*3600;}
bool Session(datetime t){int h=(int)(t%86400),n=(int)(NY(t)%86400),s=(int)C(10);
 if(s==1)return h<8*3600;if(s==2)return h>=7*3600 && h<16*3600;if(s==3)return n>=34200 && n<57600;
 if(s==4)return h>=12*3600 && h<16*3600;if(s==5)return n>=34200 && n<39600;return true;}
bool Allowed(int side,datetime now){MqlDateTime d;TimeToStruct(now,d);int exclude=(int)C(13);
 if((exclude==1 || exclude==3)&&d.day_of_week==1)return false;if((exclude==2 || exclude==3)&&d.day_of_week==5)return false;
 if((C(11)==1 && side<0)||(C(11)==2 && side>0)||!Session(now))return false;
 int f=(int)C(12);if(f==1)return side*(Buf(ema50)-Buf(ema50,0,2))>0;
 if(f==2)return side*(iClose(_Symbol,PERIOD_H1,1)-Buf(htf))>0;if(f==3)return Buf(adx)>=20;
 if(f==4)return side*(Buf(adx,1)-Buf(adx,2))>0;
 if(f==5){double a[];if(CopyBuffer(atrHandle,0,2,100,a)!=100)return false;int less=0;for(int j=0;j<100;j++)if(a[j]<atr)less++;return less>=20 && less<=80;}
 if(f==6){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return false;return q.ask-q.bid<=.1*atr;}return true;}
double Extreme(bool high,int bars,int shift=1){MqlRates r[];if(CopyRates(_Symbol,TF(),shift,bars,r)!=bars)return 0;double v=high?-DBL_MAX:DBL_MAX;
 for(int j=0;j<bars;j++)v=high?MathMax(v,r[j].high):MathMin(v,r[j].low);return v;}
bool StopGeometry(int side,double entry,double stop,double target,MqlTick &q,bool market){double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 double ref=market?(side>0?q.bid:q.ask):entry;return side*(entry-stop)>0 && side*(ref-stop)>=gap && (target==0 || (side*(target-entry)>0 && side*(target-ref)>=gap));}
void Submit(int i,int e,datetime now){if(now<InpTradeFrom)return;int side=Side(i);
 if((C(14)>0 && dailyEntries>=(int)C(14)) || CountEngine(e)>=(int)C(15)){busy++;return;}
 if(!Allowed(side,now))return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double entry=side>0?q.ask:q.bid;int kind=(int)C(1);bool pending=kind>=2;
 if(pending){double offset=(kind==3?C(2):C(2)*atr);entry=Rounded(entry+side*(kind==4?offset:-offset));}
 double distance=C(4)*atr;int mode=(int)C(3);
 if(mode==1)distance=entry*C(4)/100;if(mode==2)distance=C(4);
 double stop=entry-side*distance;
 if(mode==3)stop=side>0?iLow(_Symbol,TF(),1)-.1*atr:iHigh(_Symbol,TF(),1)+.1*atr;
 if(mode==4)stop=Extreme(side<0,5)-side*.1*atr;if(mode==5)stop=levels[i].p-side*.1*atr;
 stop=NormalizeDouble((side>0?MathFloor(stop/tickSize):MathCeil(stop/tickSize))*tickSize,_Digits);
 double risk=side*(entry-stop);if(risk<=0){skips++;return;}
 // ATR stop/target uses the original unrounded ATR distance for raw parity.
 double target=Rounded(entry+side*C(5)*(mode==0?distance:risk));int ex=(int)C(9);
 if(ex==1 || ex==3)target=0;
 if(ex==2){target=0;double near=DBL_MAX;for(int k=0;k<8;k++){double diff=side*(levels[k].p-entry);
  if(levels[k].formed<=now && levels[k].expiry>now && diff>0 && diff<near){near=diff;target=Rounded(levels[k].p);}}
  if(target==0){skips++;return;}}
 if(!StopGeometry(side,entry,stop,target,q,!pending)){skips++;return;}
 double one=0;ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;if(!OrderCalcProfit(type,_Symbol,1,entry,stop,one)||MathAbs(one)<=0)return;
 double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100/EngineCount()/C(15);
 double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double raw=cash/MathAbs(one),volume=MathMax(vmin,MathMin(vmax,MathCeil((raw-1e-12)/step)*step)),margin=0;
 if(!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 trade.SetExpertMagicNumber(Magic(e));bool ok=false;string comment="LC "+Names[i];datetime expires=now+4*PeriodSeconds(TF());
 if(!pending)ok=side>0?trade.Buy(volume,_Symbol,0,stop,target,comment):trade.Sell(volume,_Symbol,0,stop,target,comment);
 else if(kind==4)ok=side>0?trade.BuyStop(volume,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expires,comment):trade.SellStop(volume,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expires,comment);
 else ok=side>0?trade.BuyLimit(volume,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expires,comment):trade.SellLimit(volume,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expires,comment);
 if(ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_PLACED)){entries++;dailyEntries++;
  if(!MQLInfoInteger(MQL_OPTIMIZATION))PrintFormat("LC_EXT_ORDER level=%d engine=%d at=%I64d risk=%.8f budget=%.8f",i,e,(long)now,volume*MathAbs(one),cash);
 }else entryFails++;
}
void Signal(int i,int e,datetime now){if(C(1)==1 && e==0 && InpStrategy!=1){confirmAt[i]=now;return;}Submit(i,e,now);}
bool LastWasStop(int e){if(!HistorySelect(TimeCurrent()-86400,TimeCurrent()))return false;for(int j=HistoryDealsTotal()-1;j>=0;j--){ulong id=HistoryDealGetTicket(j);
 if(HistoryDealGetInteger(id,DEAL_MAGIC)==Magic(e) && HistoryDealGetInteger(id,DEAL_ENTRY)==DEAL_ENTRY_OUT)return HistoryDealGetInteger(id,DEAL_REASON)==DEAL_REASON_SL;}return false;}
void Manage(datetime now,bool newBar,bool newM15){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 MqlDateTime dt;TimeToStruct(now,dt);bool flat=(C(19)>0 && now%86400>=21*3600)||(C(18)==0 && dt.day_of_week==5 && now%86400>=20*3600)||((int)C(9)==3 && NY(now)%86400>=57600);
 for(int j=OrdersTotal()-1;j>=0;j--){ulong o=OrderGetTicket(j);if(o && OrderGetString(ORDER_SYMBOL)==_Symbol && (OrderGetInteger(ORDER_MAGIC)==InpMagic || (InpStrategy==2 && OrderGetInteger(ORDER_MAGIC)==InpMagic+1)) && flat)trade.OrderDelete(o);}
 for(int j=PositionsTotal()-1;j>=0;j--){ulong t=PositionGetTicket(j);if(!t||!SelectedOwn())continue;int k=Track(t);trade.SetExpertMagicNumber(PositionGetInteger(POSITION_MAGIC));
  datetime opened=(datetime)PositionGetInteger(POSITION_TIME);if(flat || (C(17)>0 && now-opened>=C(17)*60)){
   if(now-exitAttempt[k]>=60){exitAttempt[k]=now;if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE)closeFails++;}continue;}
  double r=savedRisk[k],open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);if(r<=0)continue;
  int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;double price=side>0?q.bid:q.ask,favor=side*(price-open);
  if((int)C(9)==4 && !partialDone[k] && favor>=r){double vol=PositionGetDouble(POSITION_VOLUME),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double part=MathFloor((vol*.5+1e-12)/step)*step;if(part>=vmin && vol-part>=vmin){if(trade.PositionClosePartial(t,part) && trade.ResultRetcode()==TRADE_RETCODE_DONE)partialDone[k]=true;}else partialDone[k]=true;
   if(!PositionSelectByTicket(t))continue;}
  int trail=(int)C(6);if(trail==0)continue;double candidate=sl;bool ready=favor>=C(7)*r;
  if(trail==7){if(!newM15)continue;double reference=tp>0?MathAbs(tp-open):r;double closed=iClose(_Symbol,PERIOD_M15,1);
   if(side*(closed-open)>=.5*reference)candidate=open+side*.2*reference;}
  else if(ready && (newBar || trail==1)){
   if(trail==1)candidate=open;
   if(trail==2)candidate=price-side*C(8)*atr;
   if(trail==3)candidate=price-side*price*C(8)/100;
   if(trail==4)candidate=Buf(ema20);
   if(trail==5)candidate=Extreme(side<0,5);
   if(trail==6){int shift=iBarShift(_Symbol,TF(),opened,false);if(shift>=0)candidate=Extreme(side>0,shift+1,0)-side*C(8)*atr;}
  }
  candidate=Rounded(candidate);double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
  if(candidate>0 && side*(candidate-sl)>tickSize*.5 && side*(price-candidate)>=gap)trade.PositionModify(t,candidate,tp);
 }
}
int OnInit(){if(InpCase<0 || InpCase>=ArrayRange(Cases,0)||InpStrategy<0 || InpStrategy>2)return INIT_PARAMETERS_INCORRECT;
 int result=LC_RawInit();if(result!=INIT_SUCCEEDED)return result;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_FAILED;
 IndicatorRelease(atrHandle);atrHandle=iATR(_Symbol,TF(),(int)C(20));ema50=iMA(_Symbol,TF(),50,0,MODE_EMA,PRICE_CLOSE);ema20=iMA(_Symbol,TF(),20,0,MODE_EMA,PRICE_CLOSE);
 htf=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);adx=iADX(_Symbol,TF(),14);
 return atrHandle==INVALID_HANDLE||ema50==INVALID_HANDLE||ema20==INVALID_HANDLE||htf==INVALID_HANDLE||adx==INVALID_HANDLE?INIT_FAILED:INIT_SUCCEEDED;}
void OnDeinit(const int reason){LC_RawDeinit(reason);IndicatorRelease(ema50);IndicatorRelease(ema20);IndicatorRelease(htf);IndicatorRelease(adx);}
void OnTick(){datetime now=TimeCurrent();MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0)return;
 if(Midnight(now)!=signalDay){signalDay=Midnight(now);dailyEntries=0;}
 bool newBar=false;MqlRates bar[];datetime m=now-now%60;
 // Raw ATR/levels cadence preserved: management happens before indicator refresh.
 datetime b=iTime(_Symbol,TF(),0),f=iTime(_Symbol,PERIOD_M15,0);bool newM15=f!=m15bar;Manage(now,b!=signalBar,newM15);m15bar=f;
 if(m!=lastMinute){lastMinute=m;if(b!=signalBar){double a[];if(CopyBuffer(atrHandle,0,1,1,a)!=1||a[0]<=0)return;atr=a[0];signalBar=b;newBar=CopyRates(_Symbol,TF(),1,1,bar)==1 && bar[0].time+PeriodSeconds(TF())<=now;}
  if(atr>0)UpdateLevels(now,q.bid);}
 if(atr<=0){previousBid=q.bid;return;}
 for(int i=0;i<8;i++){if(formedSeen[i]!=levels[i].formed){formedSeen[i]=levels[i].formed;touchUsed[i]=false;retryUsed[i]=false;confirmAt[i]=0;}
  if((int)C(22)!=0 && (int)C(22)!=i/2+1){levels[i].state=3;continue;}
  if(C(16)>0 && touchUsed[i] && !retryUsed[i] && levels[i].state==3 && levels[i].expiry>now && CountEngine(0)==0 && LastWasStop(0) && Side(i)*(q.bid-levels[i].p)<0){levels[i].state=0;retryUsed[i]=true;}
 }
 if(newBar){for(int i=0;i<8;i++){
  int side=Side(i);bool outside=side*(bar[0].close-levels[i].p)>0;
  if(confirmAt[i]>0 && bar[0].time+PeriodSeconds(TF())>confirmAt[i]){if(outside && now<levels[i].expiry)Submit(i,0,now);confirmAt[i]=0;}
  if(InpStrategy==0 || (levels[i].state!=1 && levels[i].state!=2))continue;
  if(now>=levels[i].expiry || now-levels[i].touched>C(21)*PeriodSeconds(TF())){levels[i].state=3;continue;}
  if(levels[i].state==1 && bar[0].time+PeriodSeconds(TF())>levels[i].touched && outside){levels[i].state=2;levels[i].broken=bar[0].time;}
  else if(levels[i].state==2 && bar[0].time>levels[i].broken && outside && (side>0?bar[0].low<=levels[i].p:bar[0].high>=levels[i].p)){levels[i].state=3;Submit(i,InpStrategy==2?1:0,now);}
 }}
 for(int i=0;i<8;i++){
  if(now>=levels[i].expiry){levels[i].state=3;continue;}if(levels[i].state!=0 || previousBid<=0)continue;int side=Side(i);
  if(side*(previousBid-levels[i].p)<0 && side*(q.bid-levels[i].p)>=0){levels[i].touched=now;levels[i].state=1;touchUsed[i]=true;
   if(InpStrategy!=1){Signal(i,0,now);if(InpStrategy==0)levels[i].state=3;}
   else if(CountEngine(0)>=(int)C(15))levels[i].state=3;
  }
 }previousBid=q.bid;
}
struct Ledger {datetime opened,ended;double volume,outvol,op,cp,gross,commission,swap,fee;long magic;int side;};
double OnTester(){HistorySelect(0,TimeCurrent());ulong ids[];double pnl[];bool closed[];Ledger data[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){ulong d=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(ids[a]==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(ids,n);ArrayResize(pnl,n);ArrayResize(closed,n);ArrayResize(data,n);ZeroMemory(data[k]);ids[k]=id;pnl[k]=0;closed[k]=false;}
  pnl[k]+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
  data[k].gross+=HistoryDealGetDouble(d,DEAL_PROFIT);data[k].commission+=HistoryDealGetDouble(d,DEAL_COMMISSION);data[k].swap+=HistoryDealGetDouble(d,DEAL_SWAP);data[k].fee+=HistoryDealGetDouble(d,DEAL_FEE);
  double v=HistoryDealGetDouble(d,DEAL_VOLUME),price=HistoryDealGetDouble(d,DEAL_PRICE);datetime when=(datetime)HistoryDealGetInteger(d,DEAL_TIME);
  if(HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN){data[k].volume+=v;data[k].op+=v*price;if(data[k].opened==0)data[k].opened=when;data[k].magic=HistoryDealGetInteger(d,DEAL_MAGIC);data[k].side=type==DEAL_TYPE_BUY?1:-1;}
  if(HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_OUT){closed[k]=true;data[k].outvol+=v;data[k].cp+=v*price;data[k].ended=when;}
 }
 double gp=0,gl=0,net=0;int count=0,wins=0;for(int k=0;k<n;k++)if(closed[k]){count++;net+=pnl[k];if(pnl[k]>0){wins++;gp+=pnl[k];}else gl-=pnl[k];}
 double pf=gl>0?gp/gl:gp>0?99:0,dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
 double score=count<60?-1000:net>0?(pf-1)*MathSqrt(count)/(1+dd/10):-1-MathAbs(net)/10000-dd/100;
 string file="CalyxLC20260928\\"+InpTag+"-"+(string)InpCase+".json";FolderCreate("CalyxLC20260928",FILE_COMMON);
 int h=FileOpen(file,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);if(h!=INVALID_HANDLE){FileWriteString(h,StringFormat("{\"trades\":%d,\"net_profit\":%.8f,\"profit_factor\":%.8f,\"win_rate_pct\":%.8f,\"equity_dd_pct\":%.8f,\"score\":%.8f}",count,net,pf,count>0?100.0*wins/count:0,dd,score));FileClose(h);}
 if(!MQLInfoInteger(MQL_OPTIMIZATION)){h=FileOpen("CalyxLC20260928\\"+InpTag+"-ledger.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);if(h!=INVALID_HANDLE){FileWriteString(h,"[");bool first=true;
  for(int k=0;k<n;k++)if(closed[k] && data[k].volume>0 && data[k].outvol>0){if(!first)FileWriteString(h,",");first=false;
   FileWriteString(h,StringFormat("{\"position_id\":%I64u,\"open_epoch\":%I64d,\"close_epoch\":%I64d,\"magic\":%I64d,\"side_code\":%d,\"volume\":%.8f,\"closed_volume\":%.8f,\"open_price\":%.10f,\"close_price\":%.10f,\"gross_profit\":%.8f,\"commission\":%.8f,\"swap\":%.8f,\"fee\":%.8f,\"net_profit\":%.8f}",ids[k],(long)data[k].opened,(long)data[k].ended,data[k].magic,data[k].side,data[k].volume,data[k].outvol,data[k].op/data[k].volume,data[k].cp/data[k].outvol,data[k].gross,data[k].commission,data[k].swap,data[k].fee,pnl[k]));}
  FileWriteString(h,"]");FileClose(h);}}
 return score;
}
