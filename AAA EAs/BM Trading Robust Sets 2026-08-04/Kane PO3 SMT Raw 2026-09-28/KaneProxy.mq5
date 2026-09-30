#property strict
#property version "1.00"
#property description "Tester-only Kane approximation: custom NY H4, synchronized CFD SMT, M3 inversion."
#include <Trade/Trade.mqh>
input int InpMode=1;
input bool InpBoth=true;
input double InpRR=0;
input bool InpProtected=true;
input double InpFixedRisk=100;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
input long InpMagic=9282605;
CTrade trade; double ts=0,step=0,minlot=0,spTick=0;
int trace=INVALID_HANDLE,groups=INVALID_HANDLE,signalFile=INVALID_HANDLE,manageFile=INVALID_HANDLE;
int gid=0,entries=0,signals=0,fails=0,partials=0,beFails=0,skips=0,kind=0,dir=0,stage=0,dayEntries=0;
int syncMiss=0,referenceMiss=0,decisions=0,beMoves=0;
datetime opened=0,lastManage=0,lastbar=0,dayKey=0,refHour=0;
double base=0,initialVolume=0,fill=0,initialSL=0,target=0,risk=0;
bool livegroup=false,bePending=false,traded=false,refsOK=false;
long lastSecond=-1;double intervalLow=0,intervalHighBalance=0;
double dh=0,dl=0,nh=0,nl=0,sh=0,spLow=0,n4h=0,n4l=0,s4h=0,s4l=0;
datetime h4Start=0,hourStart=0;
double prevManageBid=0,prevManageAsk=0,hourOpen=0,m15Hi=0,m15Lo=0;
datetime manageHour=0,manage15=0;
datetime MakeDate(int year,int month,int day,int hour){MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=day;d.hour=hour;return StructToTime(d);}
datetime NewYork(datetime utc){MqlDateTime d,a;TimeToStruct(utc,d);TimeToStruct(MakeDate(d.year,3,1,0),a);int march=1+(7-a.day_of_week)%7+7;TimeToStruct(MakeDate(d.year,11,1,0),a);int nov=1+(7-a.day_of_week)%7;bool dst=utc>=MakeDate(d.year,3,march,7) && utc<MakeDate(d.year,11,nov,6);return utc-(dst?4:5)*3600;}
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
  tp=RoundTick(distance); if(s*(tp-entry)<0.5*MathAbs(entry-stop)){skips++;return;}
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
 entries++;dayEntries++;lastSecond=-1;Capture(true);
}


bool Range(string symbol,datetime a,datetime z,int minimum,double &hi,double &lo){
 MqlRates r[];int n=CopyRates(symbol,PERIOD_M1,a,z-1,r);
 if(n<minimum)return false;
 if(r[0].time<a||r[n-1].time>=z)return false;
 hi=-DBL_MAX;lo=DBL_MAX;
 for(int i=0;i<n;i++){hi=MathMax(hi,r[i].high);lo=MathMin(lo,r[i].low);}
 return hi>lo;
}
bool References(datetime now){
 datetime ny=NewYork(now),nyday=ny-ny%86400,offset=now-ny;
 hourStart=now-now%3600;
 h4Start=nyday+(((int)(ny%86400)/3600-2)/4*4+2)*3600+offset; // only entry hours >=10
 if(refHour==hourStart && refsOK)return true;
 refHour=hourStart;refsOK=false;
 datetime prev=nyday-86400;
 for(int i=0;i<7&&Holiday(prev);i++)prev-=86400;
 datetime prevOffset=prev+43200-NewYork(prev+43200);
 if(!Range(_Symbol,prev+prevOffset,prev+prevOffset+86400,600,dh,dl))return false;
 if(!Range(_Symbol,hourStart-3600,hourStart,50,nh,nl)||!Range("US500",hourStart-3600,hourStart,50,sh,spLow))return false;
 if(!Range(_Symbol,h4Start-14400,h4Start,180,n4h,n4l)||!Range("US500",h4Start-14400,h4Start,180,s4h,s4l))return false;
 refsOK=true;return true;
}
void ProcessBar(datetime now){
 if(now<InpTradeFrom||livegroup||dayEntries>=2)return;
 datetime ny=NewYork(now);int minutes=(int)(ny%86400)/60;
 if(Holiday(ny)||minutes<600||minutes>=690)return;
 decisions++;
 if(!References(now)){referenceMiss++;return;}
 // Strictly closed and timestamp-aligned records from both feeds.
 MqlRates n[],s[];datetime end=now-now%180;
 int count=CopyRates(_Symbol,PERIOD_M3,end-5*3600,end-1,n);
 int countS=CopyRates("US500",PERIOD_M3,end-5*3600,end-1,s);
 if(count<20||count!=countS||n[count-1].time!=end-180){syncMiss++;return;}
 for(int i=0;i<count;i++)if(n[i].time!=s[i].time||n[i].time>=end){syncMiss++;return;}
 double ch=-DBL_MAX,cl=DBL_MAX,csh=-DBL_MAX,csl=DBL_MAX,c4h=-DBL_MAX,c4l=DBL_MAX,cs4h=-DBL_MAX,cs4l=DBL_MAX;
 int hourCount=0;
 for(int i=0;i<count;i++){
  if(n[i].time>=h4Start){c4h=MathMax(c4h,n[i].high);c4l=MathMin(c4l,n[i].low);cs4h=MathMax(cs4h,s[i].high);cs4l=MathMin(cs4l,s[i].low);}
  if(n[i].time>=hourStart){hourCount++;ch=MathMax(ch,n[i].high);cl=MathMin(cl,n[i].low);csh=MathMax(csh,s[i].high);csl=MathMin(csl,s[i].low);}
 }
 if(hourCount<1)return;
 bool nt=ch>=nh+ts,st=csh>=sh+spTick,nb=cl<=nl-ts,sb=csl<=spLow-spTick;
 bool shortOK=InpMode==0?nt:(nt!=st);
 bool longOK=InpMode==0?nb:(nb!=sb);
 double price=n[count-1].close,dayEQ=(dh+dl)/2,h4EQ=(n4h+n4l)/2;
 if(InpMode!=0){
  shortOK=shortOK && (c4h>=n4h+ts||cs4h>=s4h+spTick) && price>dayEQ && price>h4EQ;
  longOK=longOK && (c4l<=n4l-ts||cs4l<=s4l-spTick) && price<dayEQ && price<h4EQ;
 }
 int side=0;double gaplo=0,gaphi=0;datetime gapTime=0;
 for(int i=count-2;i>=MathMax(2,count-11);i--){
  if(shortOK&&n[i].low>=n[i-2].high+ts && n[count-2].close>=n[i-2].high && price<n[i-2].high){side=-1;gaplo=n[i-2].high;gaphi=n[i].low;gapTime=n[i].time+180;break;}
  if(longOK&&n[i-2].low>=n[i].high+ts && n[count-2].close<=n[i-2].low && price>n[i-2].low){side=1;gaplo=n[i].high;gaphi=n[i-2].low;gapTime=n[i].time+180;break;}
 }
 if(side==0)return;
 MqlTick q;SymbolInfoTick(_Symbol,q);double buffer=MathMax(2*ts,q.ask-q.bid);
 double stop=side>0?MathMin(cl,q.bid)-buffer:MathMax(ch,q.ask)+buffer;
 double eq=(MathMax(nh,ch)+MathMin(nl,cl))/2;
 int old=gid;Enter(side,stop,eq);
 if(livegroup&&gid>old){
  FileWrite(signalFile,gid,(long)now,(long)end,(long)gapTime,side,price,dayEQ,h4EQ,nh,nl,sh,spLow,ch,cl,csh,csl,n4h,n4l,s4h,s4l,c4h,c4l,cs4h,cs4l,gaplo,gaphi,eq,(long)hourStart,(long)h4Start,count);
  prevManageBid=q.bid;prevManageAsk=q.ask;manageHour=0;manage15=0;
 }
}
void ManageBE(datetime now,MqlTick &q){
 if(InpMode<2||stage>0)return;
 datetime hr=now-now%3600,qt=now-now%900;
 if(manageHour!=hr){MqlRates r[];if(CopyRates(_Symbol,PERIOD_H1,0,1,r)==1&&r[0].time==hr)hourOpen=r[0].open;else hourOpen=0;manageHour=hr;}
 if(manage15!=qt){MqlRates r[];if(CopyRates(_Symbol,PERIOD_M15,1,1,r)==1&&r[0].time==qt-900){m15Hi=r[0].high;m15Lo=r[0].low;}else{m15Hi=0;m15Lo=0;}manage15=qt;}
 double p=dir>0?q.bid:q.ask,prev=dir>0?prevManageBid:prevManageAsk;
 bool trigger=InpMode==3?dir*(p-fill)>=MathAbs(fill-initialSL):
  ((hourOpen>0&&dir*(prev-hourOpen)<=0&&dir*(p-hourOpen)>0)||
   (dir>0&&m15Hi>0&&prev<=m15Hi&&p>m15Hi)||(dir<0&&m15Lo>0&&prev>=m15Lo&&p<m15Lo));
 if(trigger&&dir*(p-fill)>0)bePending=true;
 prevManageBid=q.bid;prevManageAsk=q.ask;
 if(!bePending||now-lastManage<60)return;
 double unit=0;ENUM_ORDER_TYPE typ=dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(typ,_Symbol,1,fill,fill+dir,unit)||unit<=0)return;
 double pad=MathMax(ts,q.ask-q.bid+0.70/unit),newstop=RoundTick(fill+dir*pad);
 double minDistance=MathMax(ts,MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point);
 ulong ticket;if(!Own(ticket))return;double old=PositionGetDouble(POSITION_SL);
 if(dir*(newstop-old)<=0||dir*(p-newstop)<=minDistance)return;
 lastManage=now;
 if(!trade.PositionModify(ticket,newstop,target)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){beFails++;fails++;PrintFormat("CB_FAIL modify %u",trade.ResultRetcode());return;}
 stage=1;beMoves++;bePending=false;FileWrite(manageFile,gid,(long)now,old,newstop,p,fill,initialSL,hourOpen,m15Hi,m15Lo,InpMode);Capture(true);
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: Strategy Tester required");return INIT_FAILED;}
 if(_Symbol!="USTEC"||!SymbolSelect("US500",true))return INIT_FAILED;
 ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);spTick=SymbolInfoDouble("US500",SYMBOL_TRADE_TICK_SIZE);step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(ts<=0||step<=0||spTick<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(200);
 trace=FileOpen("CalyxKane20260928\\"+InpTag+"-trace.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 groups=FileOpen("CalyxKane20260928\\"+InpTag+"-groups.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 signalFile=FileOpen("CalyxKane20260928\\"+InpTag+"-signals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 manageFile=FileOpen("CalyxKane20260928\\"+InpTag+"-management.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(trace==INVALID_HANDLE||groups==INVALID_HANDLE||signalFile==INVALID_HANDLE||manageFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(groups,"group","open_time","close_msc","side","setup","volume","fill","sl","target","risk","base","net");
 FileWrite(signalFile,"group","now","end","gap_time","side","close","day_eq","h4_eq","nh","nl","sh","sl","ch","cl","csh","csl","n4h","n4l","s4h","s4l","c4h","c4l","cs4h","cs4l","gap_lo","gap_hi","eq","hour_start","h4_start","aligned_bars");
 FileWrite(manageFile,"group","time","old_sl","new_sl","price","fill","initial_sl","hour_open","m15_high","m15_low","mode");
 PrintFormat("CB_SPEC symbol=%s contract=%.8f tick=%.8f min=%.8f step=%.8f stops=%d swaplong=%.8f swapshort=%.8f swapmode=%d",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),ts,minlot,step,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT),(int)SymbolInfoInteger(_Symbol,SYMBOL_SWAP_MODE));
 return INIT_SUCCEEDED;
}
void OnTick(){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;datetime now=q.time,ny=NewYork(now),day=ny-ny%86400;
 if(dayKey!=day){dayKey=day;dayEntries=0;refsOK=false;}
 if(livegroup){Capture(false);ulong ticket;if(!Own(ticket))EndGroup();else if(ny%86400>=43200)Close();else ManageBE(now,q);}
 if(lastbar!=now-now%180){lastbar=now-now%180;ProcessBar(now);}
}
double OnTester(){
 if(livegroup)EndGroup();FileFlush(trace);FileFlush(groups);FileFlush(signalFile);FileFlush(manageFile);
 if(!HistorySelect(0,TimeCurrent()))return -999;
 int f=FileOpen("CalyxKane20260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return -999;
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong id=HistoryDealGetTicket(i);if(!id)continue;
  FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));
 }
 FileClose(f);return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(trace!=INVALID_HANDLE)FileClose(trace);if(groups!=INVALID_HANDLE)FileClose(groups);if(signalFile!=INVALID_HANDLE)FileClose(signalFile);if(manageFile!=INVALID_HANDLE)FileClose(manageFile);PrintFormat("CB_SUMMARY tag=%s entries=%d signals=%d skips=%d partials=%d failures=%d beRetries=%d beMoves=%d decisions=%d syncMissing=%d referenceMissing=%d",InpTag,entries,signals,skips,partials,fails,beFails,beMoves,decisions,syncMiss,referenceMiss);}
