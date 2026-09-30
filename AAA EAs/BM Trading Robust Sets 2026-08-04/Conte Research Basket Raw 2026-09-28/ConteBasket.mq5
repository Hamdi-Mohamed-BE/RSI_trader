#property strict
#property version "1.02"
#property description "Tester-only Conte interview CFD adaptations. No deployment capability."
#include <Trade/Trade.mqh>
input int InpMode=0;
input bool InpBoth=false;
input double InpRR=1;
input bool InpProtected=true;
input double InpFixedRisk=100;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
input long InpMagic=9282601;
CTrade trade; double ts=0,step=0,minlot=0;
int trace=INVALID_HANDLE,groups=INVALID_HANDLE,atr5=INVALID_HANDLE,atrD=INVALID_HANDLE;
int gid=0,entries=0,signals=0,fails=0,partials=0,beFails=0,skips=0,kind=0,dir=0,stage=0;
datetime opened=0,lastManage=0,daykey=0,lastbar=0;
double base=0,initialVolume=0,fill=0,initialSL=0,target=0,risk=0;
bool livegroup=false,bePending=false,traded=false,regular=false,marketday=false,rangeOK=false;
long lastSecond=-1;double intervalLow=0,intervalHighBalance=0;
double sumPV=0,sumV=0,rangeHigh=0,rangeLow=0;int rangeBars=0,sessionBars=0,cutoff=57540;
double RoundTick(double p){return NormalizeDouble(MathRound(p/ts)*ts,_Digits);}
datetime MakeDate(int year,int month,int day,int hour){MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=day;d.hour=hour;return StructToTime(d);}
datetime NewYork(datetime utc){MqlDateTime d,a;TimeToStruct(utc,d);TimeToStruct(MakeDate(d.year,3,1,0),a);int march=1+(7-a.day_of_week)%7+7;TimeToStruct(MakeDate(d.year,11,1,0),a);int nov=1+(7-a.day_of_week)%7;bool dst=utc>=MakeDate(d.year,3,march,7) && utc<MakeDate(d.year,11,nov,6);return utc-(dst?4:5)*3600;}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}

int Nth(int y,int m,int weekday,int n){MqlDateTime d;TimeToStruct(MakeDate(y,m,1,0),d);return 1+(weekday-d.day_of_week+7)%7+7*(n-1);}
int Last(int y,int m,int weekday){MqlDateTime d;datetime t=MakeDate(m==12?y+1:y,m==12?1:m+1,1,0)-86400;TimeToStruct(t,d);return d.day-(d.day_of_week-weekday+7)%7;}
datetime Easter(int y){int a=y%19,b=y/100,c=y%100,d=b/4,e=b%4,f=(b+8)/25,g=(b-f+1)/3,h=(19*a+b-d-g+15)%30,i=c/4,k=c%4,l=(32+2*e+2*i-h-k)%7,m=(a+11*h+22*l)/451;return MakeDate(y,(h+l-7*m+114)/31,(h+l-7*m+114)%31+1,0);}
bool Fixed(MqlDateTime &p,int m,int d){MqlDateTime x;TimeToStruct(MakeDate(p.year,m,d,0),x);int obs=d+(x.day_of_week==0?1:x.day_of_week==6?-1:0);return p.mon==m && p.day==obs;}
bool Holiday(datetime local){MqlDateTime p;TimeToStruct(local,p);if(p.day_of_week==0||p.day_of_week==6)return true;
 // NYSE does NOT observe New Year's Day on preceding Friday when January 1 is Saturday.
 if(p.mon==1 && (p.day==1 || (p.day==2&&p.day_of_week==1)))return true;
 if(p.mon==1&&p.day==Nth(p.year,1,1,3))return true;
 if(p.mon==2&&p.day==Nth(p.year,2,1,3))return true;
 if(local-local%86400==Easter(p.year)-2*86400)return true;
 if(p.mon==5&&p.day==Last(p.year,5,1))return true;
 if(p.year>=2022&&Fixed(p,6,19))return true;
 if(Fixed(p,7,4)||Fixed(p,12,25))return true;
 if(p.mon==9&&p.day==Nth(p.year,9,1,1))return true;
 if(p.mon==11&&p.day==Nth(p.year,11,4,4))return true;
 return p.year==2025&&p.mon==1&&p.day==9;
}
bool Early(datetime local){MqlDateTime p;TimeToStruct(local,p);
 return (p.mon==11&&p.day==Nth(p.year,11,4,4)+1) ||
 (p.mon==12&&p.day==24&&p.day_of_week>=1&&p.day_of_week<=4) ||
 (p.mon==7&&p.day==3&&p.day_of_week>=1&&p.day_of_week<=4);
}
double ATR(bool daily){double a[1];if(CopyBuffer(daily?atrD:atr5,0,1,1,a)!=1)return 0;return a[0];}
int SessionCutoff(datetime utc){
 MqlDateTime p;TimeToStruct(utc,p);datetime day=utc-utc%86400,ny=NewYork(utc),rth=utc-ny%86400+34200;
 int result=57540;
 for(uint i=0;i<20;i++){
  datetime a,z;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)p.day_of_week,i,a,z))break;
  long begin=(long)a%86400,finish=(long)z;
  if(finish>86400)finish%=86400;if(finish<=begin)finish+=86400;
  datetime end=day+(datetime)finish;
  if(end>rth&&end<rth+8*3600){int local=(int)(NewYork(end-60)%86400);result=MathMin(result,local);}
 }
 return result;
}
void Capture(bool force){
 if(!livegroup)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 double bal=AccountInfoDouble(ACCOUNT_BALANCE)-base,eq=AccountInfoDouble(ACCOUNT_EQUITY)-base;
 if(lastSecond<0){intervalLow=eq;intervalHighBalance=bal;}
 intervalLow=MathMin(intervalLow,eq);intervalHighBalance=MathMax(intervalHighBalance,bal);
 if(force || lastSecond!=q.time_msc/60000){
  FileWriteLong(trace,q.time_msc);FileWriteInteger(trace,gid,INT_VALUE);FileWriteDouble(trace,bal);FileWriteDouble(trace,eq);FileWriteDouble(trace,intervalLow);FileWriteDouble(trace,intervalHighBalance);
  intervalLow=eq;intervalHighBalance=bal;lastSecond=q.time_msc/60000;
 }
}
void EndGroup(){
 Capture(true);MqlTick q;SymbolInfoTick(_Symbol,q);
 FileWrite(groups,gid,(long)opened,q.time_msc,dir,kind,DoubleToString(initialVolume,8),DoubleToString(fill,8),DoubleToString(initialSL,8),DoubleToString(target,8),DoubleToString(risk,8),DoubleToString(base,8),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE)-base,8));
 livegroup=false;lastSecond=-1;stage=0;bePending=false;lastManage=0;
}

void Close(){
 ulong ticket;if(!Own(ticket)){if(livegroup)EndGroup();return;}
 datetime now=TimeCurrent();if(now-lastManage<60)return;lastManage=now;
 if(!trade.PositionClose(ticket)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("CB_FAIL close %u",trade.ResultRetcode());return;}
 Capture(true);if(!Own(ticket))EndGroup();
}
void Enter(int s,double stop,double distance){
 signals++;if(livegroup)return;MqlTick q;SymbolInfoTick(_Symbol,q);
 double entry=s>0?q.ask:q.bid,tp=0,unit=0,margin=0;
 ENUM_ORDER_TYPE typ=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(InpProtected){
  if(stop==0)stop=entry-s*distance;stop=RoundTick(stop);
  if(!OrderCalcProfit(typ,_Symbol,1,entry,stop,unit)||unit>=0){skips++;return;}
  if(InpRR>0)tp=RoundTick(entry+s*(-unit/SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE))*InpRR);
 }
 double volume=InpProtected?MathFloor(InpFixedRisk/-unit/step+1e-9)*step:1.0;
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=s>0?q.bid:q.ask;
 if(volume<minlot||volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||!OrderCalcMargin(typ,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 if(InpProtected && (s*(ref-stop)<MathMax(gap,ts) || (tp>0&&s*(tp-ref)<gap))){skips++;return;}
 base=AccountInfoDouble(ACCOUNT_BALANCE);gid++;
 bool ok=s>0?trade.Buy(volume,_Symbol,0,stop,tp,StringFormat("CB G%d",gid)):trade.Sell(volume,_Symbol,0,stop,tp,StringFormat("CB G%d",gid));
 if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("CB_FAIL entry %u",trade.ResultRetcode());return;}
 ulong ticket;if(!Own(ticket)){fails++;return;}
 livegroup=true;traded=true;initialVolume=PositionGetDouble(POSITION_VOLUME);fill=PositionGetDouble(POSITION_PRICE_OPEN);
 initialSL=PositionGetDouble(POSITION_SL);target=PositionGetDouble(POSITION_TP);opened=(datetime)PositionGetInteger(POSITION_TIME);kind=InpMode;dir=s;
 risk=0;if(InpProtected && OrderCalcProfit(typ,_Symbol,initialVolume,fill,initialSL,unit))risk=-unit;
 entries++;lastSecond=-1;Capture(true);
}
void ProcessBar(datetime now){
 MqlRates r[1];if(CopyRates(_Symbol,PERIOD_M1,1,1,r)!=1||r[0].time+60!=now-now%60)return;
 datetime n=NewYork(r[0].time);int m=(int)(n%86400)/60;
 if(n-n%86400!=daykey||!regular)return;
 if(m>=570&&m<cutoff/60){double w=InpMode==5?1.0:(double)r[0].tick_volume;sumPV+=(r[0].high+r[0].low+r[0].close)/3*w;sumV+=w;sessionBars++;}
 if(m>=570&&m<600){if(rangeBars==0){rangeHigh=r[0].high;rangeLow=r[0].low;}else{rangeHigh=MathMax(rangeHigh,r[0].high);rangeLow=MathMin(rangeLow,r[0].low);}rangeBars++;rangeOK=rangeBars==30;}
 if(now<InpTradeFrom)return;
 int minute=(int)(NewYork(now)%86400)/60;
 if((InpMode==1||InpMode==5)&&minute>=571&&minute<cutoff/60&&sessionBars>0&&sumV>0){
  double mean=sumPV/sumV;int side=r[0].close>mean?1:r[0].close<mean?-1:0;
  if(livegroup&&side!=dir)Close();
  if(!livegroup&&side!=0){double a=ATR(false);if(!InpProtected||a>0)Enter(side,0,2*a);}
 }
 if(InpMode==0&&!traded&&!livegroup&&rangeOK&&minute>=605&&minute<930&&minute%5==0){
  MqlRates f[1];if(CopyRates(_Symbol,PERIOD_M5,1,1,f)!=1||f[0].time+300!=now-now%60)return;
  if(f[0].close>rangeHigh)Enter(1,rangeLow,0);
  else if(InpBoth&&f[0].close<rangeLow)Enter(-1,rangeHigh,0);
 }
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: Strategy Tester required");return INIT_FAILED;}
 ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(ts<=0||step<=0)return INIT_FAILED;
 atr5=iATR(_Symbol,PERIOD_M5,14);atrD=iATR(_Symbol,PERIOD_D1,14);if(atr5==INVALID_HANDLE||atrD==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(200);
 trace=FileOpen("CalyxConte20260928\\"+InpTag+"-trace.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 groups=FileOpen("CalyxConte20260928\\"+InpTag+"-groups.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(trace==INVALID_HANDLE||groups==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(groups,"group","open_time","close_msc","side","setup","volume","fill","sl","target","risk","base","net");
 PrintFormat("CB_SPEC symbol=%s contract=%.8f tick=%.8f min=%.8f step=%.8f stops=%d swaplong=%.8f swapshort=%.8f swapmode=%d",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),ts,minlot,step,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT),(int)SymbolInfoInteger(_Symbol,SYMBOL_SWAP_MODE));
 for(int d=0;d<7;d++)for(uint j=0;j<20;j++){datetime a,z;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d,j,a,z))break;PrintFormat("CB_SESSION day=%d from=%I64d to=%I64d",d,(long)a,(long)z);}
 return INIT_SUCCEEDED;
}
void OnTick(){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;datetime now=q.time,ny=NewYork(now),day=ny-ny%86400;int sec=(int)(ny%86400);
 if(day!=daykey){daykey=day;traded=false;sumPV=sumV=0;rangeBars=sessionBars=0;rangeOK=false;marketday=!Holiday(ny);regular=marketday&&!Early(ny);cutoff=SessionCutoff(now);}
 if(livegroup){
  Capture(false);ulong ticket;if(!Own(ticket))EndGroup();
  else if(InpMode==2){datetime on=NewYork(opened);if(day>on-on%86400&&marketday&&sec>=34200)Close();}
  else if(sec>=(InpMode==0||InpMode==4?MathMin(55800,cutoff):cutoff))Close();
 }
 if(lastbar!=now-now%60){lastbar=now-now%60;ProcessBar(now);}
 if(now<InpTradeFrom||livegroup||traded||!regular)return;
 if(InpMode==4&&rangeOK&&sec>=36000&&sec<36060)Enter(1,0,rangeHigh-rangeLow);
 else if((InpMode==2&&sec>=cutoff&&sec<cutoff+60)||(InpMode==3&&sec>=34200&&sec<34260)){
  double a=ATR(true);if(!InpProtected||a>0)Enter(1,0,a);
 }
}
double OnTester(){
 if(livegroup)EndGroup();FileFlush(trace);FileFlush(groups);
 if(!HistorySelect(0,TimeCurrent()))return -999;
 int f=FileOpen("CalyxConte20260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return -999;
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong id=HistoryDealGetTicket(i);if(!id)continue;
  FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);if(groups!=INVALID_HANDLE)FileClose(groups);PrintFormat("CB_SUMMARY tag=%s entries=%d signals=%d skips=%d partials=%d failures=%d beRetries=%d",InpTag,entries,signals,skips,partials,fails,beFails);}
