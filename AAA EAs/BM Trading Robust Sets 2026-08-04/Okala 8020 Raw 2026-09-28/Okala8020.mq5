#property strict
#property version "1.01"
#property description "Tester-only mechanical 80/20 CFD adaptation; true 200-second tick bars."
#include <Trade/Trade.mqh>
input int InpSetup=0;
input double InpGridShift=0;
input int InpExit=0;
input double InpFixedRisk=100;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
input long InpMagic=9288020;
struct Bar {datetime t; double o,h,l,c;};
Bar cur200,cur600,b[100],h[30]; int nb=0,nh=0;
bool init200=false,init600=false,full200=false,full600=false;
CTrade trade; double ts=0,step=0,minlot=0;
int trace=INVALID_HANDLE,groups=INVALID_HANDLE;
int gid=0,entries=0,signals=0,fails=0,partials=0,beFails=0,skips=0;
int dir=0,stage=0,daycount=0,kind=0;
datetime nyday=0,opened=0,lastUsed=0,lastManage=0;
double usedLevel=0,base=0,initialVolume=0,fill=0,initialSL=0,target=0,risk=0;
bool livegroup=false,bePending=false;
long lastSecond=-1; double intervalLow=0,intervalHighBalance=0;
int forkdir=0,crossdir=0;datetime forkExpiry=0,crossExpiry=0;
double forkExtreme=0,forkTrigger=0,forkLevel=0,crossPoint=0,crossLevel=0;
bool forkTest=false,crossTest=false,crossH=false;

double RoundTick(double p){return NormalizeDouble(MathRound(p/ts)*ts,_Digits);}
datetime MakeDate(int year,int month,int day,int hour){MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=day;d.hour=hour;return StructToTime(d);}
datetime NewYork(datetime utc){MqlDateTime d,a;TimeToStruct(utc,d);TimeToStruct(MakeDate(d.year,3,1,0),a);int march=1+(7-a.day_of_week)%7+7;TimeToStruct(MakeDate(d.year,11,1,0),a);int nov=1+(7-a.day_of_week)%7;bool dst=utc>=MakeDate(d.year,3,march,7) && utc<MakeDate(d.year,11,nov,6);return utc-(dst?4:5)*3600;}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
double Level(double p){double base100=MathFloor((p-InpGridShift)/100)*100+InpGridShift,best=base100+20;for(int j=-1;j<=1;j++)for(int k=0;k<2;k++){double x=base100+j*100+(k==0?20:80);if(MathAbs(x-p)<MathAbs(best-p))best=x;}return best;}
void Push200(){for(int i=98;i>=0;i--)b[i+1]=b[i];b[0]=cur200;nb=MathMin(nb+1,100);}
void Push600(){for(int i=28;i>=0;i--)h[i+1]=h[i];h[0]=cur600;nh=MathMin(nh+1,30);}
void TickBar(Bar &x,datetime t,double p){x.t=t;x.o=p;x.h=p;x.l=p;x.c=p;}
bool Bars(datetime t,double p){
 bool fresh=false;datetime k=t-t%200,j=t-t%600;
 if(!init600){TickBar(cur600,j,p);init600=true;}else if(cur600.t!=j){if(full600)Push600();full600=true;TickBar(cur600,j,p);}else{cur600.h=MathMax(cur600.h,p);cur600.l=MathMin(cur600.l,p);cur600.c=p;}
 if(!init200){TickBar(cur200,k,p);init200=true;}else if(cur200.t!=k){if(full200){Push200();fresh=true;}full200=true;TickBar(cur200,k,p);}else{cur200.h=MathMax(cur200.h,p);cur200.l=MathMin(cur200.l,p);cur200.c=p;}
 return fresh;
}
void Arm(datetime now){
 forkdir=0;forkTest=false;
 if(nb<4 || b[0].t+200!=cur200.t || b[3].t+600!=b[0].t)return;
 double range=b[0].h-b[0].l,body=MathAbs(b[0].c-b[0].o),lower=MathMin(b[0].c,b[0].o)-b[0].l,upper=b[0].h-MathMax(b[0].c,b[0].o);
 if(range>=4 && body<=.35*range){
  if(lower>=.5*range && b[3].o-b[1].c>=20 && MathAbs(b[0].l-Level(b[0].l))<=2){forkdir=1;forkExtreme=b[0].l;forkTrigger=b[0].h+ts;forkLevel=Level(b[0].l);}
  else if(upper>=.5*range && b[1].c-b[3].o>=20 && MathAbs(b[0].h-Level(b[0].h))<=2){forkdir=-1;forkExtreme=b[0].h;forkTrigger=b[0].l-ts;forkLevel=Level(b[0].h);}
  forkExpiry=cur200.t+200;
 }
 int s=b[0].c>b[0].o?1:-1;
 if(s*(b[0].c-b[0].o)>=4 && s*(b[1].c-b[1].o)>=4 && MathAbs(b[0].o-b[1].c)<=2){
  double junction=(b[0].o+b[1].c)/2,lev=Level(junction);
  if(MathAbs(junction-lev)<=2){crossdir=s;crossPoint=junction;crossLevel=lev;crossExpiry=now+600;crossTest=false;crossH=false;
   if(nh>=2 && h[0].t+600==cur600.t && h[1].t+600==h[0].t)
    crossH=s*(h[0].c-h[1].c)>=20 && s*(h[0].h-h[1].h)>0 && s*(h[0].l-h[1].l)>0;
  }
 }
}
double Repair(int s,double entry){
 double result=entry+s*60;
 for(int i=1;i<MathMin(nb,36);i++){
  double p=s>0?b[i].h:b[i].l;
  bool wickless=s>0?(b[i].c<b[i].o && b[i].h-b[i].o<=ts):(b[i].c>b[i].o && b[i].o-b[i].l<=ts);
  double dist=s*(p-entry);if(!wickless || dist<30 || dist>=s*(result-entry))continue;
  bool touched=s>0?cur200.h>=p:cur200.l<=p;
  for(int j=i-1;j>=0;j--)if(s>0?b[j].h>=p:b[j].l<=p){touched=true;break;}
  if(!touched)result=p;
 }
 return RoundTick(result);
}
void Capture(bool force){
 if(!livegroup)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double bal=AccountInfoDouble(ACCOUNT_BALANCE)-base,eq=AccountInfoDouble(ACCOUNT_EQUITY)-base;
 if(lastSecond<0){intervalLow=eq;intervalHighBalance=bal;}
 intervalLow=MathMin(intervalLow,eq);intervalHighBalance=MathMax(intervalHighBalance,bal);
 if(force || lastSecond!=q.time_msc/1000){
  FileWriteLong(trace,q.time_msc);FileWriteInteger(trace,gid,INT_VALUE);FileWriteDouble(trace,bal);FileWriteDouble(trace,eq);FileWriteDouble(trace,intervalLow);FileWriteDouble(trace,intervalHighBalance);
  intervalLow=eq;intervalHighBalance=bal;lastSecond=q.time_msc/1000;
 }
}
void EndGroup(){
 Capture(true);MqlTick q;SymbolInfoTick(_Symbol,q);
 FileWrite(groups,gid,(long)opened,q.time_msc,dir,kind,DoubleToString(initialVolume,8),DoubleToString(fill,8),DoubleToString(initialSL,8),DoubleToString(target,8),DoubleToString(risk,8),DoubleToString(base,8),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE)-base,8));
 livegroup=false;lastSecond=-1;stage=0;bePending=false;lastManage=0;
}
void Enter(int s,double lev,int setup,datetime now){
 signals++;if(daycount>=7 || livegroup || (now-lastUsed<600 && MathAbs(usedLevel-lev)<ts)){skips++;return;}
 MqlTick q;SymbolInfoTick(_Symbol,q);if(q.ask-q.bid>2 || q.ask<=0 || q.bid<=0){skips++;return;}
 double entry=s>0?q.ask:q.bid,stop=RoundTick(entry-s*10),tp=InpExit==1?RoundTick(entry+s*15):Repair(s,entry),unit=0;
 ENUM_ORDER_TYPE typ=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(typ,_Symbol,1,entry,stop,unit) || unit>=0){fails++;return;}
 double volume=MathFloor(InpFixedRisk/-unit/(4*step)+1e-9)*(4*step),margin=0;
 if(volume<4*minlot || volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX) || !OrderCalcMargin(typ,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=s>0?q.bid:q.ask;
 if(s*(ref-stop)<gap || s*(tp-ref)<gap){skips++;return;}
 if(setup==1 && s*(stop-forkExtreme)>=0){skips++;return;}
 base=AccountInfoDouble(ACCOUNT_BALANCE);gid++;string comment=StringFormat("8020 G%d S%d",gid,setup);
 bool ok=s>0?trade.Buy(volume,_Symbol,0,stop,tp,comment):trade.Sell(volume,_Symbol,0,stop,tp,comment);
 if(!ok || trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("O8_FAIL kind=entry code=%u",trade.ResultRetcode());return;}
 ulong ticket;if(!Own(ticket)){fails++;return;}
 livegroup=true;initialVolume=PositionGetDouble(POSITION_VOLUME);fill=PositionGetDouble(POSITION_PRICE_OPEN);initialSL=PositionGetDouble(POSITION_SL);target=PositionGetDouble(POSITION_TP);dir=s;kind=setup;opened=(datetime)PositionGetInteger(POSITION_TIME);stage=0;
 if(!OrderCalcProfit(typ,_Symbol,initialVolume,fill,initialSL,unit)){fails++;Print("O8_FAIL kind=riskcalc");}risk=-unit;
 entries++;daycount++;lastUsed=now;usedLevel=lev;forkdir=0;crossdir=0;lastSecond=-1;Capture(true);
 PrintFormat("O8_OPEN group=%d time=%I64d kind=%d side=%d grid=%.2f fill=%.5f sl=%.5f target=%.5f lot=%.4f risk=%.4f",gid,(long)opened,setup,s,lev,fill,initialSL,target,initialVolume,risk);
}
void Manage(datetime now){
 if(!livegroup)return;Capture(false);ulong ticket;
 if(!Own(ticket)){EndGroup();return;}
 MqlTick q;SymbolInfoTick(_Symbol,q);datetime ny=NewYork(now);int sec=(int)(ny%86400);
 if((now-opened>=1200 || sec>=15*3600+55*60) && now-lastManage>=1){
  lastManage=now;if(!trade.PositionClose(ticket)){fails++;PrintFormat("O8_FAIL kind=timeclose code=%u",trade.ResultRetcode());}Capture(true);if(!Own(ticket))EndGroup();return;
 }
 if(InpExit==1)return;
 double move=dir*((dir>0?q.bid:q.ask)-fill);
 if(stage==0 && move>=15){
  if(trade.PositionClosePartial(ticket,initialVolume*.5) && trade.ResultRetcode()==TRADE_RETCODE_DONE){stage=1;partials++;bePending=true;Capture(true);}else{fails++;PrintFormat("O8_FAIL kind=partial1 code=%u",trade.ResultRetcode());}
 }
 if(bePending && Own(ticket)){
  if(trade.PositionModify(ticket,RoundTick(fill),PositionGetDouble(POSITION_TP)) && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_NO_CHANGES))bePending=false;else beFails++;
 }
 if(stage==1 && move>=30 && Own(ticket)){
  if(trade.PositionClosePartial(ticket,initialVolume*.25) && trade.ResultRetcode()==TRADE_RETCODE_DONE){stage=2;partials++;Capture(true);}else{fails++;PrintFormat("O8_FAIL kind=partial2 code=%u",trade.ResultRetcode());}
 }
 if(!Own(ticket))EndGroup();
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: Strategy Tester required");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging tester required for partials");return INIT_FAILED;}
 ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(ts<=0 || step<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(200);
 trace=FileOpen("Calyx802020260928\\"+InpTag+"-trace.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 groups=FileOpen("Calyx802020260928\\"+InpTag+"-groups.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(trace==INVALID_HANDLE || groups==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(groups,"group","open_time","close_msc","side","setup","volume","fill","sl","target","risk","base","net");
 PrintFormat("O8_SPEC symbol=%s contract=%.8f tick=%.8f min=%.8f step=%.8f stops=%d",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),ts,minlot,step,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL));return INIT_SUCCEEDED;
}
void OnTick(){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;datetime now=q.time,ny=NewYork(now),day=ny-ny%86400;int sec=(int)(ny%86400);
 Manage(now);bool fresh=Bars(now,q.bid);if(fresh)Arm(now);
 if(day!=nyday){nyday=day;daycount=0;}
 if(now<InpTradeFrom || livegroup || !((sec>=34200 && sec<41400)||(sec>=48600 && sec<55800)))return;
 if(forkdir!=0 && now<forkExpiry && (InpSetup==0 || InpSetup==1)){
  int s=forkdir;
  if(s*(q.bid-forkExtreme)<-ts){forkdir=0;}else{
   if(MathAbs(q.bid-forkExtreme)<=2)forkTest=true;
   if(forkTest && s*(q.bid-forkTrigger)>=0){Enter(s,forkLevel,1,now);forkdir=0;}
  }
 }
 if(livegroup)return;
 if(crossdir!=0 && now<crossExpiry && (InpSetup==0 || InpSetup==2 || (InpSetup==3 && crossH))){
  int s=crossdir;
  if(s*(q.bid-crossPoint)<-3){crossdir=0;}else{
   if(MathAbs(q.bid-crossPoint)<=2)crossTest=true;
   if(crossTest && s*(q.bid-crossPoint)>=2){Enter(s,crossLevel,crossH?3:2,now);crossdir=0;}
  }
 }
}
double OnTester(){
 if(livegroup)EndGroup();FileFlush(trace);FileFlush(groups);
 if(!HistorySelect(0,TimeCurrent()))return -999;
 int f=FileOpen("Calyx802020260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return -999;
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong id=HistoryDealGetTicket(i);if(!id)continue;
  FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);if(groups!=INVALID_HANDLE)FileClose(groups);PrintFormat("O8_SUMMARY tag=%s entries=%d signals=%d skips=%d partials=%d failures=%d beRetries=%d",InpTag,entries,signals,skips,partials,fails,beFails);}
