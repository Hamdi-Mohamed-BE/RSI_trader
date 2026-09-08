#property copyright "Calyx Session VWAP Liquidity Snapback research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_SV_SESSION { SV_ALL_DAY=0, SV_ASIA=1, SV_LONDON=2, SV_NEW_YORK=3, SV_OVERLAP=4 };
enum ENUM_SV_CONFIRM { SV_CLOSE_INSIDE=0, SV_REJECTION_CANDLE=1, SV_ENGULFING=2 };
enum ENUM_SV_REGIME { SV_REGIME_NONE=0, SV_ADX15=1, SV_ADX20=2, SV_ADX25=3, SV_EMA_FLAT=4, SV_ADX25_EMA_FLAT=5, SV_DAILY_SIDEWAYS=6 };
enum ENUM_SV_DIRECTION { SV_BOTH=0, SV_LONG_ONLY=1, SV_SHORT_ONLY=2 };
enum ENUM_SV_STOP { SV_CANDLE=0, SV_SWING=1, SV_SESSION_EXTREME=2, SV_ATR=3 };
enum ENUM_SV_TARGET { SV_VWAP=0, SV_FIXED_R=1 };
enum ENUM_SV_MANAGEMENT { SV_NONE=0, SV_BREAKEVEN=1, SV_ATR_TRAIL=2, SV_DYNAMIC_M15_50_20=3 };

input group "Signal"
input ENUM_TIMEFRAMES    InpSignalTimeframe=PERIOD_M15;
input ENUM_SV_SESSION    InpSession=SV_NEW_YORK;
input double             InpDeviationSigma=2.0;
input ENUM_SV_CONFIRM    InpConfirmation=SV_CLOSE_INSIDE;
input ENUM_SV_REGIME     InpRegime=SV_ADX25_EMA_FLAT;
input ENUM_SV_DIRECTION  InpDirection=SV_BOTH;
input int                InpMaximumTradesPerSession=1;

input group "Stop, target and management"
input ENUM_SV_STOP       InpStopMode=SV_ATR;
input double             InpStopValue=1.0;
input ENUM_SV_TARGET     InpTargetMode=SV_FIXED_R;
input double             InpRewardRisk=1.0;
input ENUM_SV_MANAGEMENT InpManagement=SV_NONE;
input double             InpRiskPercent=1.0;

input group "Execution and safety"
input bool               InpAvoidHighImpactUSDNews=false;
input int                InpNewsBlockMinutes=30;
input double             InpMaximumSpreadRiskPercent=25.0;
input int                InpMaximumDeviationPoints=100;
input long               InpMagic=969060400;
input bool               InpTesterOnly=true;
input int                InpTesterServerUTCOffsetHours=0;
input bool               InpUseAutomaticLiveServerOffset=true;
input int                InpManualLiveServerUTCOffsetHours=0;
input bool               InpShowVWAP=true;

CTrade trade;
datetime g_last_bar=0;
int g_session_key=0;
int g_trades_session=0;
double g_initial_risk=0.0;
int g_atr_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime x={0};x.year=year;x.mon=month;x.day=1;x.hour=12;
   datetime first=StructToTime(x);TimeToStruct(first,x);
   return 1+((7-x.day_of_week)%7)+(occurrence-1)*7;
}

int LastSunday(const int year,const int month)
{
   MqlDateTime x={0};x.year=year;x.mon=month+1;x.day=1;x.hour=12;
   if(month==12){x.year=year+1;x.mon=1;}
   datetime last=StructToTime(x)-86400;TimeToStruct(last,x);
   return x.day-x.day_of_week;
}

int NewYorkUTCOffset(const datetime utc)
{
   MqlDateTime x;TimeToStruct(utc,x);MqlDateTime a={0},b={0};
   a.year=x.year;a.mon=3;a.day=NthSunday(x.year,3,2);a.hour=7;
   b.year=x.year;b.mon=11;b.day=NthSunday(x.year,11,1);b.hour=6;
   return (utc>=StructToTime(a) && utc<StructToTime(b) ? -4 : -5);
}

int LondonUTCOffset(const datetime utc)
{
   MqlDateTime x;TimeToStruct(utc,x);MqlDateTime a={0},b={0};
   a.year=x.year;a.mon=3;a.day=LastSunday(x.year,3);a.hour=1;
   b.year=x.year;b.mon=10;b.day=LastSunday(x.year,10);b.hour=1;
   return (utc>=StructToTime(a) && utc<StructToTime(b) ? 1 : 0);
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();datetime utc=TimeGMT();
   if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime value){return value-ServerUTCOffsetSeconds();}

datetime SessionLocalTime(const datetime server)
{
   datetime utc=ServerToUTC(server);
   if(InpSession==SV_LONDON)return utc+LondonUTCOffset(utc)*3600;
   if(InpSession==SV_NEW_YORK || InpSession==SV_OVERLAP)return utc+NewYorkUTCOffset(utc)*3600;
   return utc;
}

int DateKey(const datetime server)
{
   MqlDateTime x;TimeToStruct(SessionLocalTime(server),x);return x.year*10000+x.mon*100+x.day;
}

void SessionMinutes(int &start,int &finish)
{
   if(InpSession==SV_ALL_DAY){start=0;finish=1440;}
   else if(InpSession==SV_ASIA){start=0;finish=480;}
   else if(InpSession==SV_LONDON){start=480;finish=990;}
   else if(InpSession==SV_NEW_YORK){start=570;finish=960;}
   else {start=570;finish=720;}
}

datetime LocalToServer(MqlDateTime &local)
{
   datetime local_value=StructToTime(local);int offset=0;
   if(InpSession==SV_LONDON)
   {
      // Noon of the local date gives an unambiguous DST lookup for session anchors.
      datetime guess=local_value;offset=LondonUTCOffset(guess);
   }
   else if(InpSession==SV_NEW_YORK || InpSession==SV_OVERLAP)
   {
      datetime guess=local_value+5*3600;offset=NewYorkUTCOffset(guess);
   }
   datetime utc=local_value-offset*3600;return utc+ServerUTCOffsetSeconds();
}

bool SessionBounds(const datetime server,datetime &from,datetime &to)
{
   MqlDateTime local;TimeToStruct(SessionLocalTime(server),local);int start,finish;SessionMinutes(start,finish);
   local.hour=start/60;local.min=start%60;local.sec=0;from=LocalToServer(local);
   if(finish>=1440){to=from+86400;}else{local.hour=finish/60;local.min=finish%60;to=LocalToServer(local);}
   return to>from;
}

bool InEntryWindow(const datetime server)
{
   MqlDateTime x;TimeToStruct(SessionLocalTime(server),x);int minute=x.hour*60+x.min,start,finish;SessionMinutes(start,finish);
   return minute>=start+30 && minute<finish-15;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<minimum || minimum<=0 || step<=0)return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,maximum)+1e-12)/step)*step,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double pnl=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,pnl) || pnl==0)return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(pnl));
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;return true;}}
   return false;
}

int TradesInSession(const datetime from,const datetime to)
{
   if(!HistorySelect(from,to))return 0;int count=0;
   for(int i=HistoryDealsTotal()-1;i>=0;i--){ulong d=HistoryDealGetTicket(i);if(d>0 && HistoryDealGetString(d,DEAL_SYMBOL)==_Symbol && HistoryDealGetInteger(d,DEAL_MAGIC)==InpMagic && HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN)count++;}
   return count;
}

bool ReadBuffer(const int handle,const int buffer,const int shift,double &value)
{
   double a[1];if(CopyBuffer(handle,buffer,shift,1,a)!=1)return false;value=a[0];return MathIsValidNumber(value);
}

bool SessionVWAP(const datetime signal_open,double &vwap,double &deviation,double &high,double &low,int &bars)
{
   datetime from,to;if(!SessionBounds(signal_open,from,to))return false;
   MqlRates rates[];bars=CopyRates(_Symbol,InpSignalTimeframe,from,signal_open-1,rates);
   if(bars<6)return false;
   double volume=0,pv=0,p2v=0;high=-DBL_MAX;low=DBL_MAX;
   for(int i=0;i<bars;i++)
   {
      double w=(double)MathMax(1,rates[i].tick_volume),p=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      volume+=w;pv+=p*w;p2v+=p*p*w;high=MathMax(high,rates[i].high);low=MathMin(low,rates[i].low);
   }
   if(volume<=0)return false;vwap=pv/volume;deviation=MathSqrt(MathMax(0.0,p2v/volume-vwap*vwap));return deviation>0 && high>low;
}

bool DailySideways(const datetime signal_time)
{
   int shift=iBarShift(_Symbol,PERIOD_D1,signal_time,false);if(shift<0)return false;
   double recent=iClose(_Symbol,PERIOD_D1,shift+1),past=iClose(_Symbol,PERIOD_D1,shift+21);
   return recent>0 && past>0 && MathAbs(recent/past-1.0)<=0.05;
}

bool RegimeAllows(const datetime signal_time)
{
   double adx_value=0;if(!ReadBuffer(g_adx_handle,0,1,adx_value))return false;
   if(InpRegime==SV_ADX15 && adx_value>15)return false;
   if(InpRegime==SV_ADX20 && adx_value>20)return false;
   if(InpRegime==SV_ADX25 && adx_value>25)return false;
   if(InpRegime==SV_DAILY_SIDEWAYS)return DailySideways(signal_time);
   if(InpRegime==SV_EMA_FLAT || InpRegime==SV_ADX25_EMA_FLAT)
   {
      if(InpRegime==SV_ADX25_EMA_FLAT && adx_value>25)return false;
      int seconds=PeriodSeconds(InpSignalTimeframe);int back=MathMax(1,(int)MathRound(3600.0/seconds));double now=0,prior=0,atr=0;
      if(!ReadBuffer(g_ema_handle,0,1,now) || !ReadBuffer(g_ema_handle,0,1+back,prior) || !ReadBuffer(g_atr_handle,0,1,atr) || atr<=0)return false;
      if(MathAbs(now-prior)/atr>0.20)return false;
   }
   return true;
}

bool HighImpactNewsBlocked()
{
   if(!InpAvoidHighImpactUSDNews || (bool)MQLInfoInteger(MQL_TESTER))return false;
   datetime now=TimeTradeServer();MqlCalendarValue values[];int total=CalendarValueHistory(values,now-InpNewsBlockMinutes*60,now+InpNewsBlockMinutes*60,NULL,"USD");
   for(int i=0;i<total;i++){MqlCalendarEvent event;if(CalendarEventById(values[i].event_id,event) && event.importance==CALENDAR_IMPORTANCE_HIGH)return true;}
   return false;
}

bool SpreadOK(const double risk)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || risk<=0)return false;return 100.0*(tick.ask-tick.bid)/risk<=InpMaximumSpreadRiskPercent;
}

void DrawVWAP(const double value)
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowVWAP)return;string name=StringFormat("SVWAP_%I64d_%s",InpMagic,_Symbol);
   if(ObjectFind(0,name)<0)ObjectCreate(0,name,OBJ_HLINE,0,0,value);ObjectSetDouble(0,name,OBJPROP_PRICE,value);ObjectSetInteger(0,name,OBJPROP_COLOR,clrMediumSeaGreen);
}

bool Enter(const int side,const MqlRates &bar,const MqlRates &previous,const double vwap,const double session_high,const double session_low,const double atr)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return false;double entry=(side>0?tick.ask:tick.bid),raw_stop=0;
   if(InpStopMode==SV_CANDLE)raw_stop=(side>0?bar.low-InpStopValue*atr:bar.high+InpStopValue*atr);
   else if(InpStopMode==SV_SWING)
   {
      MqlRates x[];ArraySetAsSeries(x,true);if(CopyRates(_Symbol,InpSignalTimeframe,1,4,x)<2)return false;double extreme=(side>0?DBL_MAX:-DBL_MAX);
      for(int i=0;i<ArraySize(x);i++)extreme=(side>0?MathMin(extreme,x[i].low):MathMax(extreme,x[i].high));raw_stop=(side>0?extreme-InpStopValue*atr:extreme+InpStopValue*atr);
   }
   else if(InpStopMode==SV_SESSION_EXTREME)raw_stop=(side>0?MathMin(session_low,bar.low)-InpStopValue*atr:MathMax(session_high,bar.high)+InpStopValue*atr);
   else raw_stop=entry-side*InpStopValue*atr;
   double risk=side>0?entry-raw_stop:raw_stop-entry;if(risk<=0 || risk>5*atr || !SpreadOK(risk))return false;
   double target=(InpTargetMode==SV_VWAP?vwap:entry+side*InpRewardRisk*risk);if(side*(target-entry)<=0.25*risk)return false;
   double stop=NormalizePrice(raw_stop);target=NormalizePrice(target);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum || MathAbs(target-entry)<minimum)return false;ENUM_ORDER_TYPE type=(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double lots=LotsForRisk(type,entry,stop);if(lots<=0)return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(side>0?trade.Buy(lots,_Symbol,0,stop,target,"Session VWAP snapback"):trade.Sell(lots,_Symbol,0,stop,target,"Session VWAP snapback"));
   if(!sent){Print("Session VWAP entry failed: ",trade.ResultRetcodeDescription());return false;}g_initial_risk=risk;g_trades_session++;return true;
}

void ManagePosition(const datetime now)
{
   ulong ticket=0;if(!SelectOurPosition(ticket))return;datetime from,to;if(!SessionBounds(now,from,to))return;
   if(now>=to || now<from)
   {
      trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);trade.PositionClose(ticket);return;
   }
   if(InpManagement==SV_NONE || g_initial_risk<=0)return;
   long type=PositionGetInteger(POSITION_TYPE);int side=(type==POSITION_TYPE_BUY?1:-1);double entry=PositionGetDouble(POSITION_PRICE_OPEN),old_stop=PositionGetDouble(POSITION_SL),target=PositionGetDouble(POSITION_TP);
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;double market=(side>0?tick.bid:tick.ask),progress=side*(market-entry)/g_initial_risk,new_stop=old_stop;
   if(InpManagement==SV_BREAKEVEN && progress>=1)new_stop=(side>0?MathMax(old_stop,entry):MathMin(old_stop,entry));
   else if(InpManagement==SV_ATR_TRAIL && progress>=1){double atr=0;if(!ReadBuffer(g_atr_handle,0,1,atr))return;double candidate=market-side*1.5*atr;new_stop=(side>0?MathMax(old_stop,candidate):MathMin(old_stop,candidate));}
   else if(InpManagement==SV_DYNAMIC_M15_50_20 && progress>=0.5){MqlRates m15[];ArraySetAsSeries(m15,true);if(CopyRates(_Symbol,PERIOD_M15,1,1,m15)!=1)return;double close_progress=side*(m15[0].close-entry)/g_initial_risk;if(close_progress>=0.5){double candidate=entry+side*0.2*g_initial_risk;new_stop=(side>0?MathMax(old_stop,candidate):MathMin(old_stop,candidate));}}
   new_stop=NormalizePrice(new_stop);if(new_stop!=old_stop)trade.PositionModify(ticket,new_stop,target);
}

void EvaluateClosedBar()
{
   MqlRates b[];ArraySetAsSeries(b,true);if(CopyRates(_Symbol,InpSignalTimeframe,1,2,b)!=2)return;MqlRates bar=b[0],previous=b[1];
   datetime from,to;if(!SessionBounds(bar.time,from,to) || bar.time<from || bar.time>=to || !InEntryWindow(TimeCurrent()))return;
   if(DateKey(bar.time)!=g_session_key){g_session_key=DateKey(bar.time);g_trades_session=TradesInSession(from,to);}
   if(g_trades_session>=InpMaximumTradesPerSession || HighImpactNewsBlocked() || !RegimeAllows(bar.time))return;ulong ticket=0;if(SelectOurPosition(ticket))return;
   double vwap=0,deviation=0,session_high=0,session_low=0;int count=0;if(!SessionVWAP(bar.time,vwap,deviation,session_high,session_low,count))return;DrawVWAP(vwap);
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;double spread=tick.ask-tick.bid,upper=vwap+InpDeviationSigma*deviation,lower=vwap-InpDeviationSigma*deviation;
   bool long_signal=bar.low+spread<=lower && bar.close+spread>lower;bool short_signal=bar.high>=upper && bar.close<upper;
   if(InpConfirmation==SV_REJECTION_CANDLE){long_signal=long_signal && bar.close>bar.open;short_signal=short_signal && bar.close<bar.open;}
   else if(InpConfirmation==SV_ENGULFING){long_signal=long_signal && bar.close>bar.open && bar.close>=previous.open && bar.open<=previous.close;short_signal=short_signal && bar.close<bar.open && bar.close<=previous.open && bar.open>=previous.close;}
   if(InpDirection==SV_LONG_ONLY)short_signal=false;if(InpDirection==SV_SHORT_ONLY)long_signal=false;if(long_signal==short_signal)return;
   double atr=0;if(!ReadBuffer(g_atr_handle,0,1,atr) || atr<=0)return;Enter(long_signal?1:-1,bar,previous,vwap,session_high,session_low,atr);
}

void Process()
{
   datetime now=TimeCurrent();if(now<=0)return;ManagePosition(now);datetime bar=iTime(_Symbol,InpSignalTimeframe,0);if(bar<=0 || bar==g_last_bar)return;g_last_bar=bar;EvaluateClosedBar();
}

int OnInit()
{
   if(InpTesterOnly && !(bool)MQLInfoInteger(MQL_TESTER)){Print("Research build: live/demo chart attachment is disabled.");return INIT_FAILED;}
   if(InpDeviationSigma<=0 || InpStopValue<0 || InpRewardRisk<=0 || InpMaximumTradesPerSession<1 || InpRiskPercent!=1.0 || InpMagic<=0)return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,14);g_adx_handle=iADX(_Symbol,InpSignalTimeframe,14);g_ema_handle=iMA(_Symbol,InpSignalTimeframe,50,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_adx_handle==INVALID_HANDLE || g_ema_handle==INVALID_HANDLE)return INIT_FAILED;
   datetime from,to;if(SessionBounds(TimeCurrent(),from,to)){g_session_key=DateKey(TimeCurrent());g_trades_session=TradesInSession(from,to);}g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);EventSetTimer(10);return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle);if(g_adx_handle!=INVALID_HANDLE)IndicatorRelease(g_adx_handle);if(g_ema_handle!=INVALID_HANDLE)IndicatorRelease(g_ema_handle);ObjectDelete(0,StringFormat("SVWAP_%I64d_%s",InpMagic,_Symbol));
}

void OnTick(){Process();}
void OnTimer(){Process();}

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES),profit=TesterStatistics(STAT_PROFIT),pf=TesterStatistics(STAT_PROFIT_FACTOR),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<20 || profit<=0 || pf<1.0 || dd<=0)return -1000+trades;return profit/dd*MathMin(2.0,MathSqrt(trades/100.0))*MathMin(pf,3.0);
}
