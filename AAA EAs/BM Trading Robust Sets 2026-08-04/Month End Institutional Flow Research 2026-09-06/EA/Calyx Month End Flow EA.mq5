#property copyright "Calyx Month-End Institutional Flow research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_MF_WINDOW { MF_CLASSIC=0, MF_LAST1=1, MF_LAST2=2, MF_LAST3=3, MF_FIRST1=4, MF_FIRST3=5, MF_LAST2_FIRST2=6, MF_LAST3_FIRST3=7 };
enum ENUM_MF_ENTRY { MF_LONDON_OPEN=0, MF_NY_OPEN=1, MF_NY_FIRST_HOUR=2, MF_NY_POWER_HOUR=3 };
enum ENUM_MF_CONFIRM { MF_CONFIRM_NONE=0, MF_CANDLE=1, MF_BREAKOUT=2 };
enum ENUM_MF_TREND { MF_TREND_NONE=0, MF_EMA20=1, MF_EMA50=2, MF_MOMENTUM20=3, MF_EMA20_MOMENTUM20=4, MF_PRIOR_DAY_REVERSAL=5, MF_PRIOR_DAY_STRENGTH=6 };
enum ENUM_MF_DIRECTION { MF_LONG_ONLY=0, MF_SHORT_ONLY=1, MF_DAILY_TREND=2 };
enum ENUM_MF_STOP { MF_ATR=0, MF_PRIOR_DAY=1, MF_SIGNAL_CANDLE=2 };
enum ENUM_MF_MANAGEMENT { MF_MANAGE_NONE=0, MF_BREAKEVEN=1, MF_ATR_TRAIL=2, MF_DYNAMIC_M15_50_20=3 };

input group "Calendar and signal"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M30;
input ENUM_MF_WINDOW InpCalendarWindow=MF_CLASSIC;
input ENUM_MF_ENTRY InpEntryTime=MF_NY_FIRST_HOUR;
input ENUM_MF_CONFIRM InpConfirmation=MF_CONFIRM_NONE;
input ENUM_MF_TREND InpTrendFilter=MF_TREND_NONE;
input ENUM_MF_DIRECTION InpDirection=MF_LONG_ONLY;

input group "Stop, target and management"
input int InpMaximumHoldHours=24;
input ENUM_MF_STOP InpStopMode=MF_ATR;
input double InpStopValue=1.5;
input double InpRewardRisk=2.5;
input ENUM_MF_MANAGEMENT InpManagement=MF_MANAGE_NONE;
input double InpRiskPercent=1.0;

input group "Execution and safety"
input double InpMaximumSpreadRiskPercent=20.0;
input int InpMaximumDeviationPoints=100;
input long InpMagic=969060500;
input bool InpTesterOnly=true;
input int InpTesterServerUTCOffsetHours=0;
input bool InpUseAutomaticLiveServerOffset=true;
input int InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_bar=0;
double g_initial_risk=0.0;
int g_atr_handle=INVALID_HANDLE;
int g_ema20_handle=INVALID_HANDLE;
int g_ema50_handle=INVALID_HANDLE;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime value={0};value.year=year;value.mon=month;value.day=1;value.hour=12;
   datetime first=StructToTime(value);TimeToStruct(first,value);
   return 1+((7-value.day_of_week)%7)+(occurrence-1)*7;
}

int LastSunday(const int year,const int month)
{
   MqlDateTime value={0};value.year=year;value.mon=month+1;value.day=1;value.hour=12;
   if(month==12){value.year=year+1;value.mon=1;}
   datetime last=StructToTime(value)-86400;TimeToStruct(last,value);return value.day-value.day_of_week;
}

int NewYorkUTCOffset(const datetime utc)
{
   MqlDateTime value;TimeToStruct(utc,value);MqlDateTime start={0},finish={0};
   start.year=value.year;start.mon=3;start.day=NthSunday(value.year,3,2);start.hour=7;
   finish.year=value.year;finish.mon=11;finish.day=NthSunday(value.year,11,1);finish.hour=6;
   return (utc>=StructToTime(start) && utc<StructToTime(finish) ? -4 : -5);
}

int LondonUTCOffset(const datetime utc)
{
   MqlDateTime value;TimeToStruct(utc,value);MqlDateTime start={0},finish={0};
   start.year=value.year;start.mon=3;start.day=LastSunday(value.year,3);start.hour=1;
   finish.year=value.year;finish.mon=10;finish.day=LastSunday(value.year,10);finish.hour=1;
   return (utc>=StructToTime(start) && utc<StructToTime(finish) ? 1 : 0);
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER))return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset)return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();datetime utc=TimeGMT();
   if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime value){return value-ServerUTCOffsetSeconds();}
datetime NewYorkLocal(const datetime server){datetime utc=ServerToUTC(server);return utc+NewYorkUTCOffset(utc)*3600;}
datetime EntryLocal(const datetime server)
{
   datetime utc=ServerToUTC(server);
   if(InpEntryTime==MF_LONDON_OPEN)return utc+LondonUTCOffset(utc)*3600;
   return utc+NewYorkUTCOffset(utc)*3600;
}

int DateKey(const datetime local){MqlDateTime value;TimeToStruct(local,value);return value.year*10000+value.mon*100+value.day;}

int DaysInMonth(const int year,const int month)
{
   if(month==2)return ((year%4==0 && (year%100!=0 || year%400==0))?29:28);
   if(month==4 || month==6 || month==9 || month==11)return 30;return 31;
}

bool Weekday(const int year,const int month,const int day)
{
   MqlDateTime value={0};value.year=year;value.mon=month;value.day=day;value.hour=12;datetime stamp=StructToTime(value);TimeToStruct(stamp,value);
   return value.day_of_week>=1 && value.day_of_week<=5;
}

void BusinessPositions(const datetime server,int &from_start,int &to_end)
{
   MqlDateTime value;TimeToStruct(NewYorkLocal(server),value);from_start=0;to_end=0;int finish=DaysInMonth(value.year,value.mon);
   for(int day=1;day<=value.day;day++)if(Weekday(value.year,value.mon,day))from_start++;
   for(int day=value.day;day<=finish;day++)if(Weekday(value.year,value.mon,day))to_end++;
}

bool CalendarAllows(const datetime server)
{
   int from_start=0,to_end=0;BusinessPositions(server,from_start,to_end);
   if(InpCalendarWindow==MF_CLASSIC)return to_end==1 || from_start<=3;
   if(InpCalendarWindow==MF_LAST1)return to_end==1;
   if(InpCalendarWindow==MF_LAST2)return to_end<=2;
   if(InpCalendarWindow==MF_LAST3)return to_end<=3;
   if(InpCalendarWindow==MF_FIRST1)return from_start==1;
   if(InpCalendarWindow==MF_FIRST3)return from_start<=3;
   if(InpCalendarWindow==MF_LAST2_FIRST2)return to_end<=2 || from_start<=2;
   return to_end<=3 || from_start<=3;
}

int EntryMinute()
{
   if(InpEntryTime==MF_LONDON_OPEN)return 480;
   if(InpEntryTime==MF_NY_OPEN)return 570;
   if(InpEntryTime==MF_NY_FIRST_HOUR)return 630;
   return 900;
}

bool EntryCrossed(const datetime current_bar,const datetime previous_bar)
{
   datetime current_local=EntryLocal(current_bar),previous_local=EntryLocal(previous_bar);
   if(DateKey(current_local)!=DateKey(previous_local))return false;
   MqlDateTime current,previous;TimeToStruct(current_local,current);TimeToStruct(previous_local,previous);
   int target=EntryMinute(),now=current.hour*60+current.min,before=previous.hour*60+previous.min;
   return before<target && now>=target && now<=target+75;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0)return 0.0;
   double volume=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   if(volume>raw+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw,volume);
   return NormalizeDouble(volume,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double pnl=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,pnl) || pnl==0)return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(pnl));
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--){ulong value=PositionGetTicket(i);if(value>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=value;return true;}}
   return false;
}

bool ReadBuffer(const int handle,const int shift,double &value)
{
   double buffer[1];if(CopyBuffer(handle,0,shift,1,buffer)!=1)return false;value=buffer[0];return MathIsValidNumber(value);
}

bool TrendAllows(int &side)
{
   double prior_close=iClose(_Symbol,PERIOD_D1,1),older_close=iClose(_Symbol,PERIOD_D1,21),two_days=iClose(_Symbol,PERIOD_D1,2);
   if(prior_close<=0 || older_close<=0 || two_days<=0)return false;
   double momentum=prior_close/older_close-1.0,day_return=prior_close/two_days-1.0;
   if(InpDirection==MF_LONG_ONLY)side=1;else if(InpDirection==MF_SHORT_ONLY)side=-1;else side=(momentum>=0?1:-1);
   double ema20=0,ema50=0;if(!ReadBuffer(g_ema20_handle,1,ema20) || !ReadBuffer(g_ema50_handle,1,ema50))return false;
   if(InpTrendFilter==MF_EMA20 && side*(prior_close-ema20)<=0)return false;
   if(InpTrendFilter==MF_EMA50 && side*(prior_close-ema50)<=0)return false;
   if(InpTrendFilter==MF_MOMENTUM20 && side*momentum<=0)return false;
   if(InpTrendFilter==MF_EMA20_MOMENTUM20 && (side*(prior_close-ema20)<=0 || side*momentum<=0))return false;
   if(InpTrendFilter==MF_PRIOR_DAY_REVERSAL && side*day_return>=0)return false;
   if(InpTrendFilter==MF_PRIOR_DAY_STRENGTH && side*day_return<=0)return false;
   return true;
}

bool SpreadOK(const double risk)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || risk<=0)return false;return 100.0*(tick.ask-tick.bid)/risk<=InpMaximumSpreadRiskPercent;
}

bool Enter(const int side,const MqlRates &signal,const double atr)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return false;double entry=(side>0?tick.ask:tick.bid),raw_stop=0;
   if(InpStopMode==MF_ATR)raw_stop=entry-side*InpStopValue*atr;
   else if(InpStopMode==MF_PRIOR_DAY){double extreme=(side>0?iLow(_Symbol,PERIOD_D1,1):iHigh(_Symbol,PERIOD_D1,1));if(extreme<=0)return false;raw_stop=extreme-side*InpStopValue*atr;}
   else raw_stop=(side>0?signal.low-InpStopValue*atr:signal.high+InpStopValue*atr);
   double risk=(side>0?entry-raw_stop:raw_stop-entry);if(risk<=0 || risk>6.0*atr || !SpreadOK(risk))return false;
   double stop=NormalizePrice(raw_stop),target=NormalizePrice(entry+side*InpRewardRisk*risk),point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;if(risk<minimum || MathAbs(target-entry)<minimum)return false;
   ENUM_ORDER_TYPE type=(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double lots=LotsForRisk(type,entry,stop);if(lots<=0)return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(side>0?trade.Buy(lots,_Symbol,0,stop,target,"Month-end flow"):trade.Sell(lots,_Symbol,0,stop,target,"Month-end flow"));
   if(!sent){Print("Month-end entry failed: ",trade.ResultRetcodeDescription());return false;}g_initial_risk=risk;return true;
}

void ManagePosition()
{
   ulong ticket=0;if(!SelectOurPosition(ticket))return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);if(TimeCurrent()-opened>=InpMaximumHoldHours*3600){trade.PositionClose(ticket);return;}
   if(InpManagement==MF_MANAGE_NONE)return;
   long type=PositionGetInteger(POSITION_TYPE);int side=(type==POSITION_TYPE_BUY?1:-1);double entry=PositionGetDouble(POSITION_PRICE_OPEN),old_stop=PositionGetDouble(POSITION_SL),target=PositionGetDouble(POSITION_TP);
   if(g_initial_risk<=0)g_initial_risk=MathAbs(entry-old_stop);if(g_initial_risk<=0)return;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;double market=(side>0?tick.bid:tick.ask),progress=side*(market-entry)/g_initial_risk,new_stop=old_stop;
   if(InpManagement==MF_BREAKEVEN && progress>=1.0)new_stop=(side>0?MathMax(old_stop,entry):MathMin(old_stop,entry));
   else if(InpManagement==MF_ATR_TRAIL && progress>=1.0){double atr=0;if(!ReadBuffer(g_atr_handle,1,atr))return;double candidate=market-side*1.5*atr;new_stop=(side>0?MathMax(old_stop,candidate):MathMin(old_stop,candidate));}
   else if(InpManagement==MF_DYNAMIC_M15_50_20){MqlRates bars[];ArraySetAsSeries(bars,true);if(CopyRates(_Symbol,PERIOD_M15,1,1,bars)!=1)return;double close_progress=side*(bars[0].close-entry)/g_initial_risk;if(close_progress>=0.5*InpRewardRisk){double candidate=entry+side*0.2*InpRewardRisk*g_initial_risk;new_stop=(side>0?MathMax(old_stop,candidate):MathMin(old_stop,candidate));}}
   new_stop=NormalizePrice(new_stop);if(new_stop!=old_stop)trade.PositionModify(ticket,new_stop,target);
}

void EvaluateEntry(const datetime current_bar,const datetime previous_bar)
{
   ulong ticket=0;if(SelectOurPosition(ticket) || !EntryCrossed(current_bar,previous_bar) || !CalendarAllows(current_bar))return;
   MqlRates bars[];ArraySetAsSeries(bars,true);if(CopyRates(_Symbol,InpSignalTimeframe,1,2,bars)!=2)return;MqlRates signal=bars[0],earlier=bars[1];
   int side=0;if(!TrendAllows(side))return;
   if(InpConfirmation==MF_CANDLE && side*(signal.close-signal.open)<=0)return;
   if(InpConfirmation==MF_BREAKOUT && ((side>0 && signal.close<=earlier.high) || (side<0 && signal.close>=earlier.low)))return;
   double atr=0;if(!ReadBuffer(g_atr_handle,1,atr) || atr<=0)return;Enter(side,signal,atr);
}

void Process()
{
   ManagePosition();datetime current=iTime(_Symbol,InpSignalTimeframe,0);if(current<=0 || current==g_last_bar)return;datetime previous=g_last_bar;g_last_bar=current;EvaluateEntry(current,previous);
}

int OnInit()
{
   if(InpTesterOnly && !(bool)MQLInfoInteger(MQL_TESTER)){Print("Research build: live/demo chart attachment is disabled.");return INIT_FAILED;}
   if(InpMaximumHoldHours<1 || InpStopValue<=0 || InpRewardRisk<0.5 || InpRiskPercent<=0.0 || InpRiskPercent>10.0 || InpMagic<=0)return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,14);g_ema20_handle=iMA(_Symbol,PERIOD_D1,20,0,MODE_EMA,PRICE_CLOSE);g_ema50_handle=iMA(_Symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_ema20_handle==INVALID_HANDLE || g_ema50_handle==INVALID_HANDLE)return INIT_FAILED;
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);EventSetTimer(10);return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle);if(g_ema20_handle!=INVALID_HANDLE)IndicatorRelease(g_ema20_handle);if(g_ema50_handle!=INVALID_HANDLE)IndicatorRelease(g_ema50_handle);
}

void OnTick(){Process();}
void OnTimer(){Process();}

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES),profit=TesterStatistics(STAT_PROFIT),pf=TesterStatistics(STAT_PROFIT_FACTOR),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<20 || profit<=0 || pf<1.0 || dd<=0)return -1000+trades;return profit/dd*MathMin(2.0,MathSqrt(trades/100.0))*MathMin(pf,3.0);
}
