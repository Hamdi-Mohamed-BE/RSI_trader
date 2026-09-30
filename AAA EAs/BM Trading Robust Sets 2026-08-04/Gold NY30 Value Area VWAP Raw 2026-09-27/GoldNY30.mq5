#property strict
#property version "1.00"
#property description "Research only: NY30 profile and closed-M1 VWAP reversal/continuation; raw, no tuning."
#include <Trade/Trade.mqh>
input int InpMode=3; // 0 plain ORB control, 1 reversal, 2 continuation, 3 combined
input double InpRiskPercent=1.0;
input double InpRewardRisk=3.0;
input int InpBins=64;
input double InpValueArea=70.0;
input int InpServerUtcOffsetHours=0;
input int InpExcursionMinutes=15;
input int InpRetestMinutes=10;
input double InpMinStopSpread=3.0;
input long InpMagic=9273030;
input string InpAuditTag="smoke";
CTrade trade;
datetime lastBar=0,lastCloseAttempt=0,lastBEAttempt=0;
int dayKey=0,openingBars=0,attemptR=0,attemptC=0,controlLong=0,controlShort=0,dayFills=0;
int ranges=0,missingProfiles=0,signals=0,fills=0,skips=0,closeFailures=0,beMoves=0,entryFailures=0;
int auditFile=INVALID_HANDLE,profileFile=INVALID_HANDLE;
double orHigh=0,orLow=0,poc=0,vah=0,val=0,sumV=0,sumPV=0,sumP2V=0,vwap=0,upper=0,lower=0;
double prevClose=0,prevUpper=0,prevLower=0,excHigh=0,excLow=0;
bool ready=false,invalidDay=false;
datetime excUp=0,excDown=0,armUp=0,armDown=0;
MqlRates opening[];
int positionEngine=0; // 1 reversal, 2 continuation, 0 control
double tickSize=0;

datetime BuildTime(int y,int m,int d,int h)
{
 MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);
}
int Sunday(int y,int m,int nth)
{
 MqlDateTime x;TimeToStruct(BuildTime(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(nth-1)*7;
}
datetime NewYork(datetime server)
{
 datetime utc=server-InpServerUtcOffsetHours*3600;MqlDateTime x;TimeToStruct(utc,x);
 datetime a=BuildTime(x.year,3,Sunday(x.year,3,2),7),b=BuildTime(x.year,11,Sunday(x.year,11,1),6);
 return utc+((utc>=a && utc<b)?-4:-5)*3600;
}
int DateKey(datetime server)
{
 MqlDateTime x;TimeToStruct(NewYork(server),x);return x.year*10000+x.mon*100+x.day;
}
int MinuteNY(datetime server)
{
 MqlDateTime x;TimeToStruct(NewYork(server),x);return x.hour*60+x.min;
}
bool OwnPosition(ulong &ticket)
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ticket=PositionGetTicket(i);
  if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;
 }
 ticket=0;return false;
}
bool SessionOpen(datetime now)
{
 MqlDateTime x;TimeToStruct(now,x);int seconds=x.hour*3600+x.min*60+x.sec;
 for(uint i=0;i<20;i++)
 {
  datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)x.day_of_week,i,from,to))break;
  int a=(int)from,b=(int)to;
  if(b>a && seconds>=a && seconds<b)return true;
  if(b<=a && (seconds>=a || seconds<b))return true;
 }
 return false;
}
double Price(double v)
{
 return NormalizeDouble(MathRound(v/tickSize)*tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double StopPrice(double v,int side)
{
 double units=v/tickSize;return NormalizeDouble((side>0?MathFloor(units+1e-8):MathCeil(units-1e-8))*tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double Lots(int side,double entry,double stop)
{
 double one=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.,entry,stop,one) || MathAbs(one)<=0)return 0;
 double raw=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100./MathAbs(one);
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(raw<=0 || lo<=0 || hi<=0 || step<=0)return 0;
 return MathMax(lo,MathMin(hi,MathCeil((MathMin(raw,hi)-1e-12)/step)*step));
}
void ResetDay(int key)
{
 dayKey=key;openingBars=0;attemptR=attemptC=controlLong=controlShort=dayFills=0;
 orHigh=0;orLow=0;poc=vah=val=0;sumV=sumPV=sumP2V=0;vwap=upper=lower=0;
 prevClose=prevUpper=prevLower=0;excHigh=excLow=0;excUp=excDown=armUp=armDown=0;ready=false;invalidDay=false;
 ArrayResize(opening,0);
}
bool BuildProfile()
{
 if(openingBars!=30 || invalidDay){missingProfiles++;return false;}
 orHigh=opening[0].high;orLow=opening[0].low;
 for(int i=0;i<30;i++)
 {
  if(MinuteNY(opening[i].time)!=570+i){missingProfiles++;return false;}
  orHigh=MathMax(orHigh,opening[i].high);orLow=MathMin(orLow,opening[i].low);
 }
 if(orHigh<=orLow)return false;
 double bins[];ArrayResize(bins,InpBins);ArrayInitialize(bins,0);
 double width=(orHigh-orLow)/InpBins,total=0;
 for(int i=0;i<30;i++)
 {
  double p=(opening[i].high+opening[i].low+opening[i].close)/3.;
  int b=(int)MathFloor((p-orLow)/width);b=MathMax(0,MathMin(InpBins-1,b));
  bins[b]+=(double)opening[i].tick_volume;total+=(double)opening[i].tick_volume;
 }
 if(total<=0)return false;
 int p=0;for(int i=1;i<InpBins;i++)if(bins[i]>bins[p])p=i;
 int left=p,right=p;double covered=bins[p];
 while(covered<total*InpValueArea/100. && (left>0 || right<InpBins-1))
 {
  double below=left>0?bins[left-1]:-1,above=right<InpBins-1?bins[right+1]:-1;
  if(above>=below && right<InpBins-1){right++;covered+=bins[right];}else{left--;covered+=bins[left];}
 }
 poc=orLow+(p+0.5)*width;val=orLow+left*width;vah=orLow+(right+1)*width;ranges++;
 FileWrite(profileFile,dayKey,TimeToString(opening[29].time+60,TIME_DATE|TIME_SECONDS),orHigh,orLow,poc,vah,val,total);
 return val<vah;
}
void Manage(datetime now)
{
 ulong ticket;if(!OwnPosition(ticket))return;
 datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
 bool overdue=DateKey(now)!=DateKey(opened) || MinuteNY(now)>=955;
 if(overdue)
 {
  if(now-lastCloseAttempt<60 || !SessionOpen(now))return;
  lastCloseAttempt=now;
  if(!trade.PositionClose(ticket) || trade.ResultRetcode()!=TRADE_RETCODE_DONE)
  {closeFailures++;PrintFormat("NY30_CLOSE_FAIL|%s|%u",TimeToString(now,TIME_DATE|TIME_SECONDS),trade.ResultRetcode());}
  return;
 }
 if(positionEngine!=1 || vwap<=0 || now-lastBEAttempt<60)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
 double entry=PositionGetDouble(POSITION_PRICE_OPEN),stop=PositionGetDouble(POSITION_SL),target=PositionGetDouble(POSITION_TP);
 bool touch=side>0 ? vwap>entry && q.bid>=vwap : vwap<entry && q.ask<=vwap;
 if(!touch || side*(entry-stop)<=tickSize/2)return;
 double minimum=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point+tickSize;
 double be=Price(entry);
 if(side>0?q.bid-be<minimum:be-q.ask<minimum)return;
 lastBEAttempt=now;
 if(trade.PositionModify(ticket,be,target) && trade.ResultRetcode()==TRADE_RETCODE_DONE)
 {beMoves++;PrintFormat("NY30_BE|%s|%I64u|%.8f|%.8f|%.8f|%.8f",TimeToString(now,TIME_DATE|TIME_SECONDS),ticket,entry,be,vwap,side>0?q.bid:q.ask);}
 else PrintFormat("NY30_BE_FAIL|%s|%u",TimeToString(now,TIME_DATE|TIME_SECONDS),trade.ResultRetcode());
}
bool Enter(int engine,int side,double extreme,MqlRates &bar,datetime now)
{
 if(engine==1)attemptR=1;
 else if(engine==2)attemptC=1;
 else if(side>0)controlLong=1;else controlShort=1;
 signals++;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return false;}
 double entry=side>0?q.ask:q.bid,stop=StopPrice(extreme-side*tickSize,side);
 double dist=side*(entry-stop),target=Price(entry+side*InpRewardRisk*dist);
 double minStop=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool valid=dist>0 && dist>=InpMinStopSpread*(q.ask-q.bid);
 valid=valid && (side>0 ? q.bid-stop>=minStop && target-q.bid>=minStop : stop-q.ask>=minStop && q.ask-target>=minStop);
 if(!valid || !SessionOpen(now)){skips++;PrintFormat("NY30_SKIP|%s|%d|%d|invalid_stop_or_closed",TimeToString(now,TIME_DATE|TIME_SECONDS),engine,side);return false;}
 double lot=Lots(side,entry,stop),margin=0;
 if(lot<=0 || !OrderCalcMargin(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
 {skips++;PrintFormat("NY30_SKIP|%s|%d|%d|margin_or_lot",TimeToString(now,TIME_DATE|TIME_SECONDS),engine,side);return false;}
 double cashRisk=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,cashRisk)){skips++;return false;}
 PrintFormat("NY30_SIGNAL|%s|%s|%d|%d|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f",
 TimeToString(now,TIME_DATE|TIME_SECONDS),TimeToString(bar.time,TIME_DATE|TIME_SECONDS),engine,side,entry,stop,target,lot,MathAbs(cashRisk),AccountInfoDouble(ACCOUNT_EQUITY),vwap,upper,lower);
 string comment="NY30 "+(engine==1?"R":engine==2?"C":"O");
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,target,comment):trade.Sell(lot,_Symbol,0,stop,target,comment);
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE)
 {
  fills++;dayFills++;positionEngine=engine;lastBEAttempt=0;
  PrintFormat("NY30_FILL|%s|%d|%d|%.8f|%.8f|%I64u",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),engine,side,trade.ResultPrice(),lot,trade.ResultDeal());
  return true;
 }
 skips++;entryFailures++;PrintFormat("NY30_ENTRY_FAIL|%u",trade.ResultRetcode());return false;
}
void Signal(MqlRates &b,datetime now)
{
 if(!ready || MinuteNY(b.time)<600)return;
 // States are based only on completed bars; a subsequent bar must confirm.
 if(excUp>0 && b.time-excUp>InpExcursionMinutes*60)excUp=0;
 if(excDown>0 && b.time-excDown>InpExcursionMinutes*60)excDown=0;
 if(armUp>0 && (b.time-armUp>InpRetestMinutes*60 || b.close<vwap))armUp=0;
 if(armDown>0 && (b.time-armDown>InpRetestMinutes*60 || b.close>vwap))armDown=0;
 if(excUp>0)excHigh=MathMax(excHigh,b.high);
 if(excDown>0)excLow=MathMin(excLow,b.low);
 ulong ticket;bool flat=!OwnPosition(ticket);
 bool can=flat && MinuteNY(now)<930 && dayFills<2;
 bool inside=b.close>val && b.close<vah;
 if(can && (InpMode&1)!=0 && attemptR==0)
 {
  if(excUp>0 && b.time>excUp && inside && b.close<upper && b.close>vwap)
  {Enter(1,-1,excHigh,b,now);can=false;}
  else if(excDown>0 && b.time>excDown && inside && b.close>lower && b.close<vwap)
  {Enter(1,1,excLow,b,now);can=false;}
 }
 if(can && (InpMode&2)!=0 && attemptC==0)
 {
  if(armUp>0 && b.time>armUp && b.low<=upper && b.close>upper && b.close>vah && b.close>b.open)
  {Enter(2,1,b.low,b,now);can=false;}
  else if(armDown>0 && b.time>armDown && b.high>=lower && b.close<lower && b.close<val && b.close<b.open)
  {Enter(2,-1,b.high,b,now);can=false;}
 }
 if(can && InpMode==0)
 {
  if(controlLong==0 && b.close>orHigh && prevClose<=orHigh)Enter(0,1,b.low,b,now);
  else if(controlShort==0 && b.close<orLow && prevClose>=orLow)Enter(0,-1,b.high,b,now);
 }
 // Start fresh excursions after expiry; do not renew the original arming time on every bar.
 if(excUp==0 && b.high>orHigh){excUp=b.time;excHigh=b.high;}
 if(excDown==0 && b.low<orLow){excDown=b.time;excLow=b.low;}
 if(armUp==0 && b.close>MathMax(vah,upper) && prevClose<=MathMax(vah,prevUpper))armUp=b.time;
 if(armDown==0 && b.close<MathMin(val,lower) && prevClose>=MathMin(val,prevLower))armDown=b.time;
}
int OnInit()
{
 if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("Research-only EA: live attachment disabled");return INIT_FAILED;}
 if(InpMode<0 || InpMode>3 || InpRiskPercent<=0 || InpRiskPercent>1 || InpBins<2 || InpBins>1000)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tickSize<=0)tickSize=_Point;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 auditFile=FileOpen("NY30_"+InpAuditTag+"_bars.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 profileFile=FileOpen("NY30_"+InpAuditTag+"_profiles.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(auditFile==INVALID_HANDLE || profileFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(auditFile,"time","open","high","low","close","tick_volume","real_volume","vwap","upper","lower","ready");
 FileWrite(profileFile,"day","known_at","or_high","or_low","poc","vah","val","volume");
 PrintFormat("NY30_SPEC|%s|tick_size=%.8f|contract=%.4f|min_lot=%.4f|lot_step=%.4f|stops=%d|utc_offset=%d",
 _Symbol,tickSize,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),
 (int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),InpServerUtcOffsetHours);
 return INIT_SUCCEEDED;
}
void OnTick()
{
 datetime now=TimeCurrent();Manage(now);
 datetime bar=iTime(_Symbol,PERIOD_M1,0);if(bar<=0 || bar==lastBar)return;lastBar=bar;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M1,1,1,r)!=1 || r[0].time+60>now || now-r[0].time>120)return;
 MqlRates b=r[0];MqlDateTime ny;TimeToStruct(NewYork(b.time),ny);
 if(ny.day_of_week<1 || ny.day_of_week>5)return;
 int key=DateKey(b.time),minute=MinuteNY(b.time);if(key!=dayKey)ResetDay(key);
 if(minute<570 || minute>=955)return;
 double p=(b.high+b.low+b.close)/3.,v=(double)b.tick_volume;
 sumV+=v;sumPV+=v*p;sumP2V+=v*p*p;
 if(sumV<=0)return;
 vwap=sumPV/sumV;double sd=MathSqrt(MathMax(0,sumP2V/sumV-vwap*vwap));upper=vwap+sd;lower=vwap-sd;
 if(minute<600)
 {
  if(minute!=570+openingBars)invalidDay=true;
  ArrayResize(opening,openingBars+1);opening[openingBars]=b;openingBars++;
  if(minute==599)ready=BuildProfile();
 }
 else Signal(b,now);
 FileWrite(auditFile,TimeToString(b.time,TIME_DATE|TIME_SECONDS),b.open,b.high,b.low,b.close,b.tick_volume,b.real_volume,vwap,upper,lower,ready?1:0);
 prevClose=b.close;prevUpper=upper;prevLower=lower;
 Manage(now);
}
void OnDeinit(const int reason)
{
 if(auditFile!=INVALID_HANDLE)FileClose(auditFile);
 if(profileFile!=INVALID_HANDLE)FileClose(profileFile);
 PrintFormat("NY30_SUMMARY ranges=%d missing_profiles=%d signals=%d fills=%d skips=%d entry_failures=%d close_failures=%d be_moves=%d",
 ranges,missingProfiles,signals,fills,skips,entryFailures,closeFailures,beMoves);
}
