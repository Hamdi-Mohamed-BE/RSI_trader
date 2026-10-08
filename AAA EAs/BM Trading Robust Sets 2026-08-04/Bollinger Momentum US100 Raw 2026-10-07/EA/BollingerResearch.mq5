#property strict
#property version "1.00"
#property description "Research only: closed-bar Bollinger momentum vs fixed 2R / contrarian controls. Refuses live initialisation."
#include <Trade/Trade.mqh>

input ENUM_TIMEFRAMES InpTimeframe=PERIOD_H1;
input int InpBandsPeriod=20;
input double InpBandsDeviation=2.0;
input int InpATRPeriod=14;
input double InpStopATR=2.0;
input int InpVariant=0; // 0 momentum-middle, 1 momentum-2R, 2 contrarian-middle
input double InpRiskPercent=1.0;
input double InpTargetR=2.0;
input int InpStartNYMinutes=570;
input int InpEndNYMinutes=958; // historical quote archive often ends at 15:58 NY
input int InpServerUTCOffsetMinutes=0;
input int InpBrokerCloseBufferSeconds=60;
input bool InpUseCashCalendar=true;
input long InpMagic=2026100701;
input int InpDeviationPoints=50;
input bool InpLogBars=true;

CTrade tr;
int bands=INVALID_HANDLE,atrh=INVALID_HANDLE;
datetime last_bar=0;
int order_errors=0,close_errors=0,size_skips=0;

datetime UTCTime(const int y,const int m,const int d,const int hour)
{
 MqlDateTime v; ZeroMemory(v); v.year=y; v.mon=m; v.day=d; v.hour=hour; return StructToTime(v);
}
int Sunday(const int y,const int m,const int n)
{
 MqlDateTime f; TimeToStruct(UTCTime(y,m,1,0),f); return 1+((7-f.day_of_week)%7)+7*(n-1);
}
datetime NY(const datetime st)
{
 datetime utc=st-InpServerUTCOffsetMinutes*60; MqlDateTime v; TimeToStruct(utc,v);
 datetime begin=UTCTime(v.year,3,Sunday(v.year,3,2),7);
 datetime end=UTCTime(v.year,11,Sunday(v.year,11,1),6);
 return utc+(utc>=begin && utc<end ? -4 : -5)*3600;
}
bool CashClosed(const int key)
{
 int days[]={20200101,20200120,20200217,20200410,20200525,20200703,20200907,20201126,20201225,
 20210101,20210118,20210215,20210402,20210531,20210705,20210906,20211125,20211224,
 20220117,20220221,20220415,20220530,20220620,20220704,20220905,20221124,20221226,
 20230102,20230116,20230220,20230407,20230529,20230619,20230704,20230904,20231123,20231225};
 for(int i=0;i<ArraySize(days);i++) if(key==days[i]) return true;
 return false;
}
bool CashHalfDay(const int key)
{
 int days[]={20201127,20201224,20211126,20221125,20230703,20231124};
 for(int i=0;i<ArraySize(days);i++) if(key==days[i]) return true;
 return false;
}
bool Session(const datetime st)
{
 MqlDateTime v; TimeToStruct(NY(st),v); int minutes=v.hour*60+v.min;
 int key=v.year*10000+v.mon*100+v.day;
 if(InpUseCashCalendar && CashClosed(key)) return false;
 int end=(InpUseCashCalendar && CashHalfDay(key) ? MathMin(InpEndNYMinutes,778) : InpEndNYMinutes);
 return v.day_of_week>=1 && v.day_of_week<=5 && minutes>=InpStartNYMinutes && minutes<end;
}
bool BrokerCloseDue(const datetime st)
{
 MqlDateTime v; TimeToStruct(st,v); int seconds=v.hour*3600+v.min*60+v.sec;
 datetime begin,end;
 for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)v.day_of_week,i,begin,end);i++)
 {
  int a=(int)((long)begin%86400),b=(int)((long)end%86400);
  if(b==0) b=86400;
  if(b<=a) b+=86400;
  if(seconds>=a && seconds<b && seconds>=b-InpBrokerCloseBufferSeconds) return true;
 }
 return false;
}
bool OurPosition(ulong &ticket)
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) {ticket=t;return true;}
 }
 return false;
}
bool Read(const int handle,const int buffer,double &v)
{
 double a[]; if(CopyBuffer(handle,buffer,1,1,a)!=1) return false; v=a[0]; return MathIsValidNumber(v) && v>0;
}
bool Close(const ulong ticket,const string reason)
{
 PrintFormat("BB_EXIT|%s|%s|%I64u",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),reason,ticket);
 bool ok=tr.PositionClose(ticket,(ulong)InpDeviationPoints);
 if(!ok || (tr.ResultRetcode()!=TRADE_RETCODE_DONE && tr.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
 {close_errors++; Print("BB_CLOSE_ERROR|",tr.ResultRetcodeDescription());return false;}
 return true;
}
void Enter(const int direction,const double atr,const MqlRates &signal,const double middle,const double upper,const double lower)
{
 MqlTick q; if(!SymbolInfoTick(_Symbol,q) || q.ask<=0 || q.bid<=0) return;
 double ep=(direction>0 ? q.ask : q.bid),point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
 int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
 double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
 double distance=MathMax(atr*InpStopATR,gap+2*point);
 double sl=NormalizeDouble(ep-direction*distance,digits);
 double tp=(InpVariant==1 ? NormalizeDouble(ep+direction*distance*InpTargetR,digits) : 0.0);
 ENUM_ORDER_TYPE typ=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
 double one=0; if(!OrderCalcProfit(typ,_Symbol,1.0,ep,sl,one) || MathAbs(one)<=0) return;
 double risk=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
 double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(step<=0 || minimum<=0) return;
 double volume=NormalizeDouble(MathFloor(MathMin(risk/MathAbs(one),maximum)/step+1e-9)*step,8);
 if(volume<minimum) {size_skips++;Print("BB_SIZE_SKIP");return;}
 string comment=(direction>0 ? "BB long" : "BB short");
 bool sent=(direction>0 ? tr.Buy(volume,_Symbol,0,sl,tp,comment) : tr.Sell(volume,_Symbol,0,sl,tp,comment));
 if(!sent || tr.ResultRetcode()!=TRADE_RETCODE_DONE) {order_errors++;Print("BB_ORDER_ERROR|",tr.ResultRetcodeDescription());return;}
 ulong ticket=0; if(!OurPosition(ticket)) {order_errors++;Print("BB_ORDER_ERROR|fill position not found");return;}
 double fill=PositionGetDouble(POSITION_PRICE_OPEN),cash=0;
 if(!OrderCalcProfit(typ,_Symbol,volume,fill,sl,cash)) {order_errors++;Print("BB_ORDER_ERROR|filled risk calculation failed");return;}
 PrintFormat("BB_ENTRY|%s|%I64u|%d|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%.8f|%s",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),ticket,direction,fill,sl,tp,volume,MathAbs(cash),signal.close,middle,upper,lower,atr,TimeToString(signal.time,TIME_DATE|TIME_SECONDS));
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)) {Print("Research-only EA: live trading prohibited");return INIT_FAILED;}
 if(InpVariant<0 || InpVariant>2 || InpBandsPeriod<2 || InpBandsDeviation<=0 || InpATRPeriod<2 || InpStopATR<=0 || InpRiskPercent<=0 || InpRiskPercent>10 || InpStartNYMinutes<0 || InpEndNYMinutes>1440 || InpStartNYMinutes>=InpEndNYMinutes) return INIT_PARAMETERS_INCORRECT;
 bands=iBands(_Symbol,InpTimeframe,InpBandsPeriod,0,InpBandsDeviation,PRICE_CLOSE);
 atrh=iATR(_Symbol,InpTimeframe,InpATRPeriod);
 if(bands==INVALID_HANDLE || atrh==INVALID_HANDLE) return INIT_FAILED;
 tr.SetExpertMagicNumber((ulong)InpMagic); tr.SetTypeFillingBySymbol(_Symbol);tr.SetDeviationInPoints((ulong)InpDeviationPoints);
 for(int day=0;day<7;day++)
 {
  datetime a,b;
  for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)day,i,a,b);i++)
   PrintFormat("BB_SESSION|%d|%u|%s|%s",day,i,TimeToString(a,TIME_SECONDS),TimeToString(b,TIME_SECONDS));
 }
 last_bar=iTime(_Symbol,InpTimeframe,0); return INIT_SUCCEEDED;
}
void OnTick()
{
 ulong ticket=0;
 if(OurPosition(ticket) && (!Session(TimeCurrent()) || BrokerCloseDue(TimeCurrent()))) {Close(ticket,BrokerCloseDue(TimeCurrent()) ? "broker-session" : "session");return;}
 datetime current=iTime(_Symbol,InpTimeframe,0); if(current<=0 || current==last_bar) return; last_bar=current;
 MqlRates r[]; if(CopyRates(_Symbol,InpTimeframe,1,1,r)!=1) return;
 double middle,upper,lower,atr;
 if(!Read(bands,0,middle) || !Read(bands,1,upper) || !Read(bands,2,lower) || !Read(atrh,0,atr)) return;
 bool held=OurPosition(ticket); int side=(held ? (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1) : 0);
 if(InpLogBars) PrintFormat("BB_BAR|%s|%s|%.8f|%.8f|%.8f|%.8f|%.8f|%d|%d",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(r[0].time,TIME_DATE|TIME_SECONDS),r[0].close,middle,upper,lower,atr,side,(int)Session(TimeCurrent()));
 if(held)
 {
  if(InpVariant!=1)
  {
   bool exit=(InpVariant==0 ? (side>0 ? r[0].close<=middle : r[0].close>=middle) : (side>0 ? r[0].close>=middle : r[0].close<=middle));
   if(exit) Close(ticket,"middle");
  }
  return;
 }
 if(!Session(TimeCurrent()) || BrokerCloseDue(TimeCurrent())) return;
 int direction=(r[0].close>upper ? 1 : (r[0].close<lower ? -1 : 0)); if(direction==0) return;
 if(InpVariant==2) direction=-direction;
 Enter(direction,atr,r[0],middle,upper,lower);
}
void OnDeinit(const int reason)
{
 PrintFormat("BB_SUMMARY|order_errors=%d|close_errors=%d|size_skips=%d",order_errors,close_errors,size_skips);
 if(bands!=INVALID_HANDLE) IndicatorRelease(bands); if(atrh!=INVALID_HANDLE) IndicatorRelease(atrh);
}
