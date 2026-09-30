#property strict
#property version "1.00"
#property description "Research only: NY 09:30 M15 range, later M15 close breakout, signal-candle stop."
#include <Trade/Trade.mqh>

input double InpRewardRisk=0.5;
input double InpRiskPercent=1.0;
input int InpServerUtcOffsetHours=0;
input int InpCloseHourNY=15;
input int InpCloseMinuteNY=55;
input long InpMagic=9271530;
input string InpAuditTag="smoke";
input datetime InpAuditStart=D'2026.03.02 00:00';

CTrade trade;
datetime lastBar=0,lastCloseAttempt=0;
int dayKey=0,usedDay=0,ranges=0,signals=0,fills=0,skips=0,closeFailures=0;
double rangeHigh=0,rangeLow=0;
datetime rangeTime=0;

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
double Price(double v){return NormalizeDouble(v,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));}
double NormalizeLots(double raw)
{
 // Same upward research sizing convention as the existing native pipeline.
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(raw<=0 || lo<=0 || hi<=0 || step<=0)return 0;
 return MathMax(lo,MathMin(hi,MathCeil((MathMin(raw,hi)-1e-12)/step)*step));
}
double Lots(ENUM_ORDER_TYPE side,double entry,double stop)
{
 double one=0;if(!OrderCalcProfit(side,_Symbol,1.,entry,stop,one) || MathAbs(one)<=0)return 0;
 return NormalizeLots(AccountInfoDouble(ACCOUNT_EQUITY)*MathMin(InpRiskPercent,1.)/100./MathAbs(one));
}
void ManageClose(datetime now)
{
 ulong ticket;if(!OwnPosition(ticket))return;
 datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
 bool overdue=DateKey(now)!=DateKey(opened) || MinuteNY(now)>=InpCloseHourNY*60+InpCloseMinuteNY;
 if(!overdue || now-lastCloseAttempt<60 || !SessionOpen(now))return;
 lastCloseAttempt=now;
 bool ok=trade.PositionClose(ticket);
 if(!ok || trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFailures++;PrintFormat("ORB15_CLOSE_FAIL time=%s retcode=%u",TimeToString(now,TIME_DATE|TIME_SECONDS),trade.ResultRetcode());}
}
int OnInit()
{
 if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("Research-only EA: live attachment disabled");return INIT_FAILED;}
 if(InpRewardRisk<=0 || InpRiskPercent<=0 || InpRiskPercent>1)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 return INIT_SUCCEEDED;
}
void OnTick()
{
 datetime now=TimeCurrent();ManageClose(now);
 datetime bar=iTime(_Symbol,PERIOD_M15,0);if(bar<=0 || bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(ny.day_of_week<1 || ny.day_of_week>5)return;
 int key=DateKey(now);if(key!=dayKey){dayKey=key;rangeHigh=rangeLow=0;rangeTime=0;}
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M15,1,1,r)!=1)return;
 if(DateKey(r[0].time)!=dayKey || r[0].time+900>now)return;
 if(MinuteNY(r[0].time)==570)
 {
  rangeHigh=r[0].high;rangeLow=r[0].low;rangeTime=r[0].time;ranges++;
  PrintFormat("ORB15_RANGE|%s|%.8f|%.8f",TimeToString(rangeTime,TIME_DATE|TIME_SECONDS),rangeHigh,rangeLow);return;
 }
 if(rangeTime==0 || r[0].time<=rangeTime || usedDay==dayKey || MinuteNY(now)>=InpCloseHourNY*60+InpCloseMinuteNY)return;
 int side=(r[0].close>rangeHigh ? 1 : (r[0].close<rangeLow ? -1 : 0));if(side==0)return;
 usedDay=dayKey;signals++;
 ulong ticket;if(OwnPosition(ticket)){skips++;Print("ORB15_SKIP existing-position");return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return;}
 double entry=side>0?q.ask:q.bid,stop=Price(side>0?r[0].low:r[0].high);
 double distance=side*(entry-stop),target=Price(entry+side*InpRewardRisk*distance);
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool valid=distance>0 && (side>0 ? q.bid-stop>=minimum && target-q.bid>=minimum : stop-q.ask>=minimum && q.ask-target>=minimum);
 if(!valid || !SessionOpen(now)){skips++;PrintFormat("ORB15_SKIP invalid-or-closed time=%s",TimeToString(now,TIME_DATE|TIME_SECONDS));return;}
 double lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop);if(lot<=0){skips++;return;}
 PrintFormat("ORB15_SIGNAL|%s|%s|%d|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f",
  TimeToString(now,TIME_DATE|TIME_SECONDS),TimeToString(r[0].time,TIME_DATE|TIME_SECONDS),side,rangeHigh,rangeLow,r[0].high,r[0].low,r[0].close,entry,stop,target,lot);
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,target,"ORB15 raw long"):trade.Sell(lot,_Symbol,0,stop,target,"ORB15 raw short");
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE)fills++;
 else{skips++;PrintFormat("ORB15_ENTRY_FAIL retcode=%u",trade.ResultRetcode());}
}
void OnDeinit(const int reason)
{
 PrintFormat("ORB15_SUMMARY ranges=%d signals=%d fills=%d skips=%d close_failures=%d",ranges,signals,fills,skips,closeFailures);
 MqlRates bars[];int total=CopyRates(_Symbol,PERIOD_M15,InpAuditStart,TimeCurrent(),bars);
 int file=FileOpen("ORB15_"+InpAuditTag+"_bars.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(file==INVALID_HANDLE){Print("ORB15_EXPORT_FAILED");return;}
 FileWrite(file,"time","open","high","low","close");
 for(int i=0;i<total;i++)if(bars[i].time+900<=TimeCurrent())
  FileWrite(file,TimeToString(bars[i].time,TIME_DATE|TIME_SECONDS),DoubleToString(bars[i].open,8),DoubleToString(bars[i].high,8),DoubleToString(bars[i].low,8),DoubleToString(bars[i].close,8));
 FileClose(file);
}
