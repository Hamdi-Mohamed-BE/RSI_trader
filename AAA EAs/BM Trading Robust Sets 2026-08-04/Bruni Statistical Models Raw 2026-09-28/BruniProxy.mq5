#property strict
#property version "1.00"
#property description "Tester-only labelled Bruni approximation; NOT exact interview strategy."
#include <Trade/Trade.mqh>
input int InpMode=1;
input bool InpBoth=true;
input double InpRR=2;
input bool InpProtected=true;
input double InpFixedRisk=100;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
input long InpMagic=9282603;
CTrade trade; double ts=0,step=0,minlot=0;
int trace=INVALID_HANDLE,groups=INVALID_HANDLE,atrHandle=INVALID_HANDLE;
int gid=0,entries=0,signals=0,fails=0,partials=0,beFails=0,skips=0,kind=0,dir=0,stage=0;
datetime opened=0,lastManage=0,lastbar=0,tradeDay=0;
double base=0,initialVolume=0,fill=0,initialSL=0,target=0,risk=0;
bool livegroup=false,bePending=false,traded=false;
long lastSecond=-1;double intervalLow=0,intervalHighBalance=0;
struct Zone {datetime time;double low,high,gap;int side;bool used,touched;};
Zone actual,peripheral;
double swingHigh=0,swingLow=0;
datetime swingHighTime=0,swingLowTime=0;
double RoundTick(double p){return NormalizeDouble(MathRound(p/ts)*ts,_Digits);}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
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
  if(InpRR>0)tp=RoundTick(entry+s*MathAbs(entry-stop)*InpRR);
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

bool Valid(MqlRates &r,int direction){
 return (r.close-r.open)*direction<0 && MathAbs(r.close-r.open)>MathMax(r.high-MathMax(r.open,r.close),MathMin(r.open,r.close)-r.low);
}
bool BuildZone(MqlRates &r[],int n,int side,double atr,Zone &z){
 int found=0,first=-1,last=-1,need=InpMode==0?1:3;
 for(int j=n-2;j>=MathMax(0,n-13);j--){
  if(Valid(r[j],side)){found++;if(last<0)last=j;first=j;if(found==need)break;}
 }
 if(found<need)return false;
 ZeroMemory(z);z.low=r[first].low;z.high=r[first].high;z.side=side;z.time=r[n-1].time;
 double e1=side>0?DBL_MAX:-DBL_MAX,e2=e1;
 for(int j=first;j<=last;j++){
  z.low=MathMin(z.low,r[j].low);z.high=MathMax(z.high,r[j].high);
  double w=side>0?r[j].low:r[j].high;
  if(side>0){if(w<e1){e2=e1;e1=w;}else if(w<e2)e2=w;}
  else {if(w>e1){e2=e1;e1=w;}else if(w>e2)e2=w;}
 }
 z.gap=last>first?MathAbs(e1-e2):0;
 // Explicit approximation: displacement beyond the zone must exceed its width.
 if(side>0 && r[n-1].close-z.high<z.high-z.low)return false;
 if(side<0 && z.low-r[n-1].close<z.high-z.low)return false;
 return z.high>z.low && atr>0;
}
void ProcessBar(datetime now){
 MqlRates r[];int n=CopyRates(_Symbol,PERIOD_M15,1,150,r);if(n<30||r[n-1].time+900!=now-now%900)return;
 double av[1];if(CopyBuffer(atrHandle,0,1,1,av)!=1||av[0]<=0)return;double atr=av[0];
 int j=n-3;bool ph=true,pl=true;
 for(int k=j-2;k<=j+2;k++){if(k==j)continue;ph=ph&&r[j].high>r[k].high;pl=pl&&r[j].low<r[k].low;}
 if(ph){swingHigh=r[j].high;swingHighTime=r[j].time;}
 if(pl){swingLow=r[j].low;swingLowTime=r[j].time;}
 int side=0;
 if(swingHighTime>0&&r[n-1].close>swingHigh+0.05*atr&&r[n-2].close<=swingHigh+0.05*atr)side=1;
 if(swingLowTime>0&&r[n-1].close<swingLow-0.05*atr&&r[n-2].close>=swingLow-0.05*atr)side=-1;
 if(side!=0){Zone z;if(BuildZone(r,n,side,atr,z)){peripheral=actual;actual=z;}}
 if(peripheral.time>0){
  double depth=peripheral.side>0?peripheral.high-.75*(peripheral.high-peripheral.low):peripheral.low+.75*(peripheral.high-peripheral.low);
  if((peripheral.side>0&&r[n-1].low<=depth)||(peripheral.side<0&&r[n-1].high>=depth))peripheral.touched=true;
 }
 if(now<InpTradeFrom||livegroup||actual.time==0)return;
 MqlDateTime d;TimeToStruct(now,d);int minute=d.hour*60+d.min;
 if(d.day_of_week==0||d.day_of_week==6||minute<360||minute>=960||(d.day_of_week==5&&minute>=840)||tradeDay==now-now%86400)return;
 bool useP=peripheral.time>0&&peripheral.side!=actual.side&&peripheral.touched;
 Zone z;if(useP)z=peripheral;else z=actual;
 if(z.used||z.time>=r[n-1].time||now-z.time>5*86400)return;
 bool touch=r[n-1].low<=z.high && r[n-1].high>=z.low;
 bool reject=z.side>0?r[n-1].close>z.high:r[n-1].close<z.low;
 if(!touch||!reject)return;
 if(InpMode==2){
  double threshold=StringFind(_Symbol,"JPY")>=0?.005:.05*atr;
  if(z.gap<=threshold)return;
 }
 if(useP)peripheral.used=true;else actual.used=true;
 Enter(z.side,z.side>0?z.low-.1*atr:z.high+.1*atr,0);
 if(livegroup)tradeDay=now-now%86400;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: Strategy Tester required");return INIT_FAILED;}
 ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(ts<=0||step<=0)return INIT_FAILED;
 atrHandle=iATR(_Symbol,PERIOD_M15,14);if(atrHandle==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(200);
 trace=FileOpen("CalyxBruni20260928\\"+InpTag+"-trace.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 groups=FileOpen("CalyxBruni20260928\\"+InpTag+"-groups.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(trace==INVALID_HANDLE||groups==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(groups,"group","open_time","close_msc","side","setup","volume","fill","sl","target","risk","base","net");
 PrintFormat("CB_SPEC symbol=%s contract=%.8f tick=%.8f min=%.8f step=%.8f stops=%d swaplong=%.8f swapshort=%.8f swapmode=%d",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),ts,minlot,step,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT),(int)SymbolInfoInteger(_Symbol,SYMBOL_SWAP_MODE));
 return INIT_SUCCEEDED;
}
void OnTick(){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;datetime now=q.time;MqlDateTime d;TimeToStruct(now,d);
 if(livegroup){
  Capture(false);ulong ticket;if(!Own(ticket))EndGroup();
  else if(now-opened>=48*3600||(d.day_of_week==5&&(d.hour*60+d.min)>=1185))Close();
 }
 if(lastbar!=now-now%900){lastbar=now-now%900;ProcessBar(now);}
}
double OnTester(){
 if(livegroup)EndGroup();FileFlush(trace);FileFlush(groups);
 if(!HistorySelect(0,TimeCurrent()))return -999;
 int f=FileOpen("CalyxBruni20260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return -999;
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong id=HistoryDealGetTicket(i);if(!id)continue;
  FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);if(groups!=INVALID_HANDLE)FileClose(groups);PrintFormat("CB_SUMMARY tag=%s entries=%d signals=%d skips=%d partials=%d failures=%d beRetries=%d",InpTag,entries,signals,skips,partials,fails,beFails);}

