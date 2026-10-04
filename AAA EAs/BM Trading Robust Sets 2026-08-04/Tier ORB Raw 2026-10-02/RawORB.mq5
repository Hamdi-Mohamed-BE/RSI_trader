#property strict
#property version "1.00"
#property description "Tester-only raw 15-minute NY ORB, M5 close confirmation, opposite-range SL, timed exit."
#include <Trade/Trade.mqh>
input double InpRiskPercent=1.0;
input int InpServerUtcOffsetHours=0;
input int InpCloseHourNY=15;
input int InpCloseMinuteNY=55;
input long InpMagic=10021545;
input string InpAuditTag="smoke";
CTrade trade;
datetime lastBar=0,lastCloseAttempt=0;
int dayKey=0,usedDay=0,ranges=0,signals=0,fills=0,skips=0,closeFailures=0;
double rangeHigh=0,rangeLow=0;
int audit=INVALID_HANDLE;
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
 double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
 return NormalizeDouble(MathRound(v/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double Lots(ENUM_ORDER_TYPE side,double entry,double stop,double budget)
{
 double one=0;if(!OrderCalcProfit(side,_Symbol,1.,entry,stop,one) || MathAbs(one)<=0)return 0;
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(lo<=0 || hi<=0 || step<=0)return 0;
 double qty=MathFloor((MathMin(hi,budget/MathAbs(one))+1e-12)/step)*step;
 return qty+1e-12<lo ? 0 : qty;
}
void ManageClose(datetime now)
{
 ulong ticket;if(!OwnPosition(ticket))return;
 datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
 bool overdue=DateKey(now)!=DateKey(opened) || MinuteNY(now)>=InpCloseHourNY*60+InpCloseMinuteNY;
 if(!overdue || now-lastCloseAttempt<60 || !SessionOpen(now))return;
 lastCloseAttempt=now;
 bool ok=trade.PositionClose(ticket);
 if(!ok || trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFailures++;PrintFormat("RAWORB_CLOSE_FAIL time=%s retcode=%u",TimeToString(now,TIME_DATE|TIME_SECONDS),trade.ResultRetcode());}
}
int OnInit()
{
 if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("Research-only EA: live attachment disabled");return INIT_FAILED;}
 if(InpRiskPercent<=0 || InpRiskPercent>1 || SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)<=0)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(50);trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
 audit=FileOpen("RawORB_"+InpAuditTag+"_signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(audit==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"time","signal_bar","side","range_high","range_low","signal_close","entry_quote","stop","risk_budget","lots","quoted_risk","retcode");
 PrintFormat("RAWORB_SPEC symbol=%s digits=%d ticksize=%.8f tickvalue=%.8f lots_min=%.8f lots_step=%.8f lots_max=%.8f stops=%d point=%.8f",
  _Symbol,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),
  SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),
  (int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),_Point);
 return INIT_SUCCEEDED;
}
void OnTick()
{
 datetime now=TimeCurrent();ManageClose(now);
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0 || bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(ny.day_of_week<1 || ny.day_of_week>5)return;
 int key=DateKey(now);if(key!=dayKey){dayKey=key;rangeHigh=rangeLow=0;}
 int minute=MinuteNY(now);
 if(minute<585 || minute>=InpCloseHourNY*60+InpCloseMinuteNY)return;
 if(rangeHigh==0)
 {
  datetime start=BuildTime(ny.year,ny.mon,ny.day,0)+570*60;
  datetime serverStart=now-(NewYork(now)-start);
  MqlRates rb[];
  if(CopyRates(_Symbol,PERIOD_M5,serverStart,serverStart+600,rb)!=3)return;
  for(int i=0;i<3;i++)if(rb[i].time!=serverStart+i*300 || rb[i].time+300>now)return;
  rangeHigh=MathMax(rb[0].high,MathMax(rb[1].high,rb[2].high));
  rangeLow=MathMin(rb[0].low,MathMin(rb[1].low,rb[2].low));
  ranges++;
 }
 if(usedDay==dayKey)return;
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1)return;
 if(DateKey(r[0].time)!=dayKey || MinuteNY(r[0].time)<585 || r[0].time+300>now)return;
 int side=(r[0].close>rangeHigh ? 1 : (r[0].close<rangeLow ? -1 : 0));if(side==0)return;
 usedDay=dayKey;signals++;
 ulong ticket;if(OwnPosition(ticket)){skips++;return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return;}
 double entry=side>0?q.ask:q.bid,stop=Price(side>0?rangeLow:rangeHigh);
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 bool valid=side>0 ? q.bid-stop>minimum : stop-q.ask>minimum;
 if(!valid || !SessionOpen(now)){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.;
 double lot=Lots(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop,budget);if(lot<=0){skips++;return;}
 double quoted=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,entry,stop,quoted)){skips++;return;}
 bool ok=side>0?trade.Buy(lot,_Symbol,0,stop,0,"RawORB long"):trade.Sell(lot,_Symbol,0,stop,0,"RawORB short");
 FileWrite(audit,TimeToString(now,TIME_DATE|TIME_SECONDS),TimeToString(r[0].time,TIME_DATE|TIME_SECONDS),side,rangeHigh,rangeLow,r[0].close,entry,stop,budget,lot,MathAbs(quoted),trade.ResultRetcode());
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE)fills++;
 else{skips++;PrintFormat("RAWORB_ENTRY_FAIL retcode=%u",trade.ResultRetcode());}
}
void OnDeinit(const int reason)
{
 PrintFormat("RAWORB_SUMMARY ranges=%d signals=%d fills=%d skips=%d close_failures=%d",ranges,signals,fills,skips,closeFailures);
 if(audit!=INVALID_HANDLE)FileClose(audit);
}
