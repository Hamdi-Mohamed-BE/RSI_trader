#property strict
#property version "1.00"
#property description "Tester-only market-style hypotheses. Not a reproduction of the clip."
#include <Trade/Trade.mqh>
input int InpMode=0;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input double InpRR=3.0;
input uint InpSeed=290929;
input datetime InpTradeFrom=D'2021.09.27';
input string InpTag="smoke";
input long InpMagic=9294400;
CTrade trade;
double tickSize=0,lotStep=0,minLot=0;
datetime lastBar=0,lastMinute=0,attemptDay=0,lastClose=0;
int trace=INVALID_HANDLE,signalFile=INVALID_HANDLE,entries=0,entryFails=0,closeFails=0,skips=0,stale=0;
struct Entry {ulong id;datetime time;int side;double risk,requestedRisk,sl,tp,volume,fill,atr;};
Entry initial[];
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
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
void Close(){
 ulong ticket;if(!Own(ticket))return;datetime now=TimeCurrent();if(now-lastClose<60)return;lastClose=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
  if(trade.ResultRetcode()==TRADE_RETCODE_POSITION_CLOSED && !Own(ticket)){Print("MS_CLOSE_RACE already closed");return;}
  closeFails++;PrintFormat("MS_CLOSE_FAIL code=%u",trade.ResultRetcode());
 }
}
uint Hash(uint x){x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return x;}
double Average(double &x[],int end,int n){double s=0;for(int i=end-n+1;i<=end;i++)s+=x[i];return s/n;}
void EMA(MqlRates &r[],int n,int period,double &out[]){ArrayResize(out,n);out[0]=r[0].close;double a=2.0/(period+1);for(int i=1;i<n;i++)out[i]=a*r[i].close+(1-a)*out[i-1];}
int State(double &tr[],int i){double slow=Average(tr,i,100);if(slow<=0)return 1;double ratio=Average(tr,i,14)/slow;return ratio<.8?0:(ratio>1.2?2:1);}
int Signal(MqlRates &r[],int n,double &atr,double &target,double &volratio,double &hotProbability,int &hotCount){
 double tr[],e20[],e50[],e200[];ArrayResize(tr,n);tr[0]=r[0].high-r[0].low;
 for(int i=1;i<n;i++)tr[i]=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));
 EMA(r,n,20,e20);EMA(r,n,50,e50);EMA(r,n,200,e200);int z=n-1;atr=Average(tr,z,14);target=0;volratio=0;hotProbability=0;hotCount=0;
 if(atr<=0)return 0;
 if(InpMode==0){
  if(e50[z]>e200[z]&&e50[z]>e50[z-5]&&r[z-1].low<=e20[z-1]&&r[z].close>r[z-1].high&&r[z].close>e20[z])return 1;
  if(e50[z]<e200[z]&&e50[z]<e50[z-5]&&r[z-1].high>=e20[z-1]&&r[z].close<r[z-1].low&&r[z].close<e20[z])return -1;
 }
 if(InpMode==1){
  double shock=r[z-1].close-r[z-1].open,priorATR=Average(tr,z-2,14);
  if(MathAbs(shock)<2*priorATR)return 0;
  if(shock>0&&r[z].close<r[z].open&&r[z].close>e20[z])return -1;
  if(shock<0&&r[z].close>r[z].open&&r[z].close<e20[z])return 1;
 }
 if(InpMode==2){
  int counts[3][3];ArrayInitialize(counts,0);
  for(int j=n-253;j<=n-2;j++){int a=State(tr,j-1),b=State(tr,j);counts[a][b]++;}
  hotCount=counts[2][0]+counts[2][1]+counts[2][2];hotProbability=(counts[2][2]+1.0)/(hotCount+3.0);
  volratio=atr/Average(tr,z,100);
  if(State(tr,z)!=2||hotCount<20||hotProbability<.55)return 0;
  if(r[z].close>e50[z]&&e50[z]>e50[z-5]&&r[z].close>r[z-1].high)return 1;
  if(r[z].close<e50[z]&&e50[z]<e50[z-5]&&r[z].close<r[z-1].low)return -1;
 }
 if(InpMode==3){
  double mean=0,variance=0,path=0;for(int i=z-21;i<=z-2;i++)mean+=r[i].close;mean/=20;
  for(int i=z-21;i<=z-2;i++)variance+=MathPow(r[i].close-mean,2);double sd=MathSqrt(variance/20);
  for(int i=z-19;i<=z;i++)path+=MathAbs(r[i].close-r[i-1].close);
  if(sd<=0||path<=0||MathAbs(r[z].close-r[z-20].close)/path>=.30||MathAbs(e50[z]-e50[z-5])>=.25*atr)return 0;
  target=mean;
  if(r[z-1].close<mean-2*sd&&r[z].close>=mean-2*sd&&r[z].close<=mean+2*sd)return 1;
  if(r[z-1].close>mean+2*sd&&r[z].close<=mean+2*sd&&r[z].close>=mean-2*sd)return -1;
 }
 return 0;
}
void Enter(int rawSide,double atr,double target,double ratio,double probability,int count,datetime signalTime){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0){skips++;return;}
 double distance=1.5*atr,rawQuote=rawSide>0?q.ask:q.bid,rr=InpRR;
 if(InpMode==3){rr=rawSide*(target-rawQuote)/distance;if(rr<.5||rr>2){skips++;return;}}
 int s=InpControl?((Hash((uint)(TimeCurrent()/86400)+InpSeed)&1)==1?1:-1):rawSide;
 double entry=s>0?q.ask:q.bid,sl=Price(entry-s*distance),tp=Price(entry+s*distance*rr),unit=0,margin=0;
 ENUM_ORDER_TYPE type=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(type,_Symbol,1,entry,sl,unit)||unit>=0){skips++;return;}
 double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 double volume=MathMax(minLot,MathCeil((goal/-unit-1e-10)/lotStep)*lotStep);
 volume=NormalizeDouble(volume,8);double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=s>0?q.bid:q.ask;
 if(volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||s*(ref-sl)<MathMax(gap,tickSize)||s*(tp-ref)<gap||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 bool ok=s>0?trade.Buy(volume,_Symbol,0,sl,tp,"MarketStyles"):trade.Sell(volume,_Symbol,0,sl,tp,"MarketStyles");
 if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){entryFails++;PrintFormat("MS_ENTRY_FAIL code=%u",trade.ResultRetcode());return;}
 ulong ticket;if(!Own(ticket)){entryFails++;return;}int k=ArraySize(initial);ArrayResize(initial,k+1);ZeroMemory(initial[k]);
 initial[k].id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);initial[k].time=(datetime)PositionGetInteger(POSITION_TIME);initial[k].side=s;
 initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].fill=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);initial[k].requestedRisk=goal;initial[k].atr=atr;
 double actual=0;if(OrderCalcProfit(type,_Symbol,initial[k].volume,initial[k].fill,initial[k].sl,actual))initial[k].risk=-actual;
 FileWrite(signalFile,initial[k].id,(long)signalTime,(long)TimeCurrent(),rawSide,s,atr,target,ratio,probability,count,entry,initial[k].fill,q.ask-q.bid);
 entries++;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY; tester required");return INIT_FAILED;}
 if(InpMode<0||InpMode>3||InpRiskPercent<=0||InpRiskPercent>1.0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(tickSize<=0||lotStep<=0||minLot<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 FolderCreate("CalyxMarketStyles20260929",FILE_COMMON);
 trace=FileOpen("CalyxMarketStyles20260929\\"+InpTag+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 signalFile=FileOpen("CalyxMarketStyles20260929\\"+InpTag+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(trace==INVALID_HANDLE||signalFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(trace,"time","balance","equity");FileWrite(signalFile,"position_id","signal_time","fill_time","raw_side","actual_side","atr","mean_target","vol_ratio","hot_probability","hot_count","quote","fill","spread");
 PrintFormat("MS_SPEC symbol=%s description=%s broker=%s server=%s demo=%d currency=%s contract=%.8f min=%.8f step=%.8f tick=%.8f",_Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO,AccountInfoString(ACCOUNT_CURRENCY),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),minLot,lotStep,tickSize);
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();ulong ticket;int remaining=0;bool session=Session(now,remaining);
 if(Own(ticket)){
  int hours=(InpMode==1||InpMode==3)?6:8;
  if(now-(datetime)PositionGetInteger(POSITION_TIME)>=hours*3600||now%86400>=20*3600||(session&&remaining<=300))Close();
 }
 datetime minute=now-now%60;if(minute!=lastMinute){lastMinute=minute;if(now>=InpTradeFrom)FileWrite(trace,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}
 datetime bar=now-now%3600;if(bar==lastBar)return;lastBar=bar;
 if(now<InpTradeFrom||now-bar>=300||Own(ticket)||!session||remaining<1800)return;
 MqlDateTime dt;TimeToStruct(now,dt);if((InpMode!=1&&(dt.day_of_week==0||dt.day_of_week==6))||dt.hour<7||dt.hour>16)return;
 datetime day=now-now%86400;if(attemptDay==day)return;
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_H1,1,400,r);if(n!=400){stale++;return;}
 if(r[n-1].time+3600!=bar){stale++;return;}
 double atr,target,ratio,prob;int count;int side=Signal(r,n,atr,target,ratio,prob,count);if(side==0)return;
 attemptDay=day;Enter(side,atr,target,ratio,prob,count,r[n-1].time);
}
struct Item {ulong id;datetime opened,closed;int side;double volume,outvol,op,cp,gross,commission,swap,fee;};
double OnTester(){
 HistorySelect(0,TimeCurrent());Item rows[];int n=0;
 for(int j=0;j<HistoryDealsTotal();j++){
  ulong deal=HistoryDealGetTicket(j);long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);int k=-1;for(int a=0;a<n;a++)if(rows[a].id==id){k=a;break;}
  if(k<0){k=n++;ArrayResize(rows,n);ZeroMemory(rows[k]);rows[k].id=id;}
  double v=HistoryDealGetDouble(deal,DEAL_VOLUME),p=HistoryDealGetDouble(deal,DEAL_PRICE);datetime t=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
  if(HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN){rows[k].volume+=v;rows[k].op+=v*p;rows[k].opened=t;rows[k].side=type==DEAL_TYPE_BUY?1:-1;}
  else{rows[k].outvol+=v;rows[k].cp+=v*p;rows[k].closed=t;}
  rows[k].gross+=HistoryDealGetDouble(deal,DEAL_PROFIT);rows[k].commission+=HistoryDealGetDouble(deal,DEAL_COMMISSION);rows[k].swap+=HistoryDealGetDouble(deal,DEAL_SWAP);rows[k].fee+=HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int f=FileOpen("CalyxMarketStyles20260929\\"+InpTag+"-trades.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"position_id","open_epoch","close_epoch","side","volume","closed_volume","open_price","close_price","initial_sl","initial_tp","requested_risk","actual_risk","gross_profit","commission","swap","fee","net_profit");
 for(int k=0;k<n;k++){
  int ix=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==rows[k].id){ix=z;break;}
  double net=rows[k].gross+rows[k].commission+rows[k].swap+rows[k].fee;
  FileWrite(f,rows[k].id,(long)rows[k].opened,(long)rows[k].closed,rows[k].side,rows[k].volume,rows[k].outvol,rows[k].op/rows[k].volume,rows[k].outvol>0?rows[k].cp/rows[k].outvol:0,ix>=0?initial[ix].sl:0,ix>=0?initial[ix].tp:0,ix>=0?initial[ix].requestedRisk:0,ix>=0?initial[ix].risk:0,rows[k].gross,rows[k].commission,rows[k].swap,rows[k].fee,net);
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT_FACTOR);
}
void OnDeinit(const int why){if(trace!=INVALID_HANDLE)FileClose(trace);if(signalFile!=INVALID_HANDLE)FileClose(signalFile);PrintFormat("MS_SUMMARY entries=%d entryFails=%d closeFails=%d skips=%d stale=%d",entries,entryFails,closeFails,skips,stale);}
