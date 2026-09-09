#property copyright "Calyx raw paper-replication research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

enum ENUM_OVERNIGHT_DIRECTION
{
   OVERNIGHT_LONG_ONLY=0,
   OVERNIGHT_SHORT_ONLY=1,
   OVERNIGHT_BOTH=2
};

enum ENUM_OVERNIGHT_STOP
{
   OVERNIGHT_STOP_PERCENT=0,
   OVERNIGHT_STOP_ATR=1
};

enum ENUM_OVERNIGHT_REGIME
{
   OVERNIGHT_REGIME_NONE=0,
   OVERNIGHT_REGIME_EMA50=1,
   OVERNIGHT_REGIME_EMA200=2,
   OVERNIGHT_REGIME_EMA50_SLOPE=3
};

input group "Raw Vojtko-Dujava MAX(10) rule"
input bool   InpEnableTrading=false;
input int    InpLookbackCalendarDays=10;
input int    InpEntryNewYorkHour=16;
input int    InpEntryNewYorkMinute=0;
input int    InpExitNewYorkHour=10;
input int    InpExitNewYorkMinute=0;
input bool   InpTradeFridayNight=true;
input bool   InpTradeMondayNight=true;
input bool   InpTradeTuesdayNight=true;
input bool   InpRequireRegularNYSEDay=true;
input double InpPaperCapitalAllocationPercent=100.0;

input group "Calyx pipeline risk and direction"
input bool   InpUseDefinedRiskStop=false;
input double InpRiskPercent=1.0;
input ENUM_OVERNIGHT_DIRECTION InpDirectionMode=OVERNIGHT_LONG_ONLY;
input ENUM_OVERNIGHT_STOP InpStopMode=OVERNIGHT_STOP_ATR;
input double InpStopPercent=3.0;
input ENUM_TIMEFRAMES InpStopATRTimeframe=PERIOD_D1;
input int    InpStopATRPeriod=14;
input double InpStopATRMultiplier=1.0;
input double InpTargetR=0.0;
input double InpBreakEvenAtR=0.0;
input double InpTrailStartR=0.0;
input ENUM_TIMEFRAMES InpTrailATRTimeframe=PERIOD_H1;
input int    InpTrailATRPeriod=14;
input double InpTrailATRMultiplier=1.0;

input group "Calyx pipeline filters"
input ENUM_OVERNIGHT_REGIME InpRegimeMode=OVERNIGHT_REGIME_NONE;
input double InpMinimumDailyATRPercent=0.0;
input double InpMaximumDailyATRPercent=0.0;

input group "Execution"
input int    InpEntryWindowMinutes=15;
input int    InpMaxDeviationBrokerPoints=50;
input long   InpMagic=981009901;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC; // Exness tester strategy timestamps are UTC
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_last_entry_date=0;
double g_initial_risk=0.0;

int LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=31; p.hour=12;
   while(p.day>28)
   {
      datetime value=StructToTime(p);
      TimeToStruct(value,p);
      if(p.day_of_week==0) return p.day;
      p.day--;
   }
   return p.day;
}

int EuropeUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=LastSunday(p.year,3); start.hour=1;
   finish.year=p.year; finish.mon=10; finish.day=LastSunday(p.year,10); finish.hour=1;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? 3 : 2);
}

int AutomaticLiveOffsetSeconds()
{
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   if(!(bool)MQLInfoInteger(MQL_TESTER))
   {
      int offset=(InpUseAutomaticLiveServerOffset ? AutomaticLiveOffsetSeconds() : InpManualLiveServerUTCOffsetHours*3600);
      return server_time-offset;
   }
   if(InpTesterServerClock==TESTER_CLOCK_UTC) return server_time;
   if(InpTesterServerClock==TESTER_CLOCK_MANUAL) return server_time-InpTesterManualUTCOffsetHours*3600;
   datetime utc_standard=server_time-2*3600;
   return server_time-EuropeUTCOffsetHours(utc_standard)*3600;
}

datetime UTCToServer(const datetime utc_time)
{
   if(!(bool)MQLInfoInteger(MQL_TESTER))
   {
      int offset=(InpUseAutomaticLiveServerOffset ? AutomaticLiveOffsetSeconds() : InpManualLiveServerUTCOffsetHours*3600);
      return utc_time+offset;
   }
   if(InpTesterServerClock==TESTER_CLOCK_UTC) return utc_time;
   if(InpTesterServerClock==TESTER_CLOCK_MANUAL) return utc_time+InpTesterManualUTCOffsetHours*3600;
   return utc_time+EuropeUTCOffsetHours(utc_time)*3600;
}

int NthWeekdayOfMonth(const int year,const int month,const int weekday,const int occurrence)
{
   MqlDateTime first={0};
   first.year=year; first.mon=month; first.day=1; first.hour=12;
   datetime value=StructToTime(first); TimeToStruct(value,first);
   return 1+((weekday-first.day_of_week+7)%7)+(occurrence-1)*7;
}

int LastWeekdayOfMonth(const int year,const int month,const int weekday)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month+1; p.day=1; p.hour=12;
   if(month==12) { p.year=year+1; p.mon=1; }
   datetime value=StructToTime(p)-86400; TimeToStruct(value,p);
   return p.day-((p.day_of_week-weekday+7)%7);
}

datetime EasterSunday(const int year)
{
   int a=year%19;
   int b=year/100;
   int c=year%100;
   int d=b/4;
   int e=b%4;
   int f=(b+8)/25;
   int g=(b-f+1)/3;
   int h=(19*a+b-d-g+15)%30;
   int i=c/4;
   int k=c%4;
   int l=(32+2*e+2*i-h-k)%7;
   int m=(a+11*h+22*l)/451;
   int month=(h+l-7*m+114)/31;
   int day=((h+l-7*m+114)%31)+1;
   MqlDateTime p={0}; p.year=year; p.mon=month; p.day=day; p.hour=12;
   return StructToTime(p);
}

bool IsObservedFixedHoliday(const MqlDateTime &p,const int month,const int day)
{
   MqlDateTime fixed={0}; fixed.year=p.year; fixed.mon=month; fixed.day=day; fixed.hour=12;
   datetime value=StructToTime(fixed); TimeToStruct(value,fixed);
   int observed=day;
   if(fixed.day_of_week==6) observed=day-1;
   else if(fixed.day_of_week==0) observed=day+1;
   return p.mon==month && p.day==observed;
}

bool IsNewYearObserved(const MqlDateTime &p)
{
   if(IsObservedFixedHoliday(p,1,1)) return true;
   if(p.mon==12 && p.day==31)
   {
      MqlDateTime next={0}; next.year=p.year+1; next.mon=1; next.day=1; next.hour=12;
      datetime value=StructToTime(next); TimeToStruct(value,next);
      return next.day_of_week==6;
   }
   return false;
}

bool IsNYSEHoliday(const MqlDateTime &p)
{
   if(p.day_of_week==0 || p.day_of_week==6) return true;
   if(IsNewYearObserved(p)) return true;
   if(p.mon==1 && p.day==NthWeekdayOfMonth(p.year,1,1,3)) return true;
   if(p.mon==2 && p.day==NthWeekdayOfMonth(p.year,2,1,3)) return true;
   MqlDateTime good_friday; TimeToStruct(EasterSunday(p.year)-2*86400,good_friday);
   if(p.mon==good_friday.mon && p.day==good_friday.day) return true;
   if(p.mon==5 && p.day==LastWeekdayOfMonth(p.year,5,1)) return true;
   if(p.year>=2022 && IsObservedFixedHoliday(p,6,19)) return true;
   if(IsObservedFixedHoliday(p,7,4)) return true;
   if(p.mon==9 && p.day==NthWeekdayOfMonth(p.year,9,1,1)) return true;
   if(p.mon==11 && p.day==NthWeekdayOfMonth(p.year,11,4,4)) return true;
   if(IsObservedFixedHoliday(p,12,25)) return true;
   if(p.year==2025 && p.mon==1 && p.day==9) return true;
   return false;
}

bool IsNYSEEarlyClose(const MqlDateTime &p)
{
   int thanksgiving=NthWeekdayOfMonth(p.year,11,4,4);
   if(p.mon==11 && p.day==thanksgiving+1 && p.day_of_week==5) return true;
   if(p.mon==12 && p.day==24 && p.day_of_week>=1 && p.day_of_week<=4) return true;
   if(p.mon==7 && p.day==3 && p.day_of_week>=1 && p.day_of_week<=4) return true;
   return false;
}

int NewYorkOffsetForLocal(const datetime local_time)
{
   MqlDateTime p; TimeToStruct(local_time,p);
   int march=NthWeekdayOfMonth(p.year,3,0,2);
   int november=NthWeekdayOfMonth(p.year,11,0,1);
   if(p.mon>3 && p.mon<11) return -4;
   if(p.mon<3 || p.mon>11) return -5;
   if(p.mon==3) return (p.day>march || (p.day==march && p.hour>=2)) ? -4 : -5;
   return (p.day<november || (p.day==november && p.hour<2)) ? -4 : -5;
}

datetime NewYorkLocalToUTC(const datetime local_time)
{
   return local_time-NewYorkOffsetForLocal(local_time)*3600;
}

datetime UTCToNewYork(const datetime utc_time)
{
   MqlDateTime u; TimeToStruct(utc_time,u);
   int march=NthWeekdayOfMonth(u.year,3,0,2);
   int november=NthWeekdayOfMonth(u.year,11,0,1);
   MqlDateTime start={0},finish={0};
   start.year=u.year; start.mon=3; start.day=march; start.hour=7;
   finish.year=u.year; finish.mon=11; finish.day=november; finish.hour=6;
   int offset=(utc_time>=StructToTime(start) && utc_time<StructToTime(finish)) ? -4 : -5;
   return utc_time+offset*3600;
}

datetime ServerToNewYork(const datetime server_time)
{
   return UTCToNewYork(ServerToUTC(server_time));
}

int DateKey(const datetime value)
{
   MqlDateTime p; TimeToStruct(value,p);
   return p.year*10000+p.mon*100+p.day;
}

double CloseAtNewYorkTime(const datetime local_target)
{
   datetime server_target=UTCToServer(NewYorkLocalToUTC(local_target));
   int shift=iBarShift(_Symbol,PERIOD_M1,server_target,false);
   if(shift<0) return 0.0;
   datetime found=iTime(_Symbol,PERIOD_M1,shift);
   if(found<=0 || MathAbs((double)(found-server_target))>300.0) return 0.0;
   return iClose(_Symbol,PERIOD_M1,shift);
}

int ExtremeBreakDirection(const double current_price,const datetime current_ny)
{
   MqlDateTime p; TimeToStruct(current_ny,p);
   p.hour=InpEntryNewYorkHour; p.min=InpEntryNewYorkMinute; p.sec=0;
   datetime local_anchor=StructToTime(p);
   double highest=0.0,lowest=DBL_MAX;
   for(int i=1;i<=InpLookbackCalendarDays;i++)
   {
      double close=CloseAtNewYorkTime(local_anchor-i*86400);
      if(close<=0.0) return 0;
      if(close>highest) highest=close;
      if(close<lowest) lowest=close;
   }
   if((InpDirectionMode==OVERNIGHT_LONG_ONLY || InpDirectionMode==OVERNIGHT_BOTH) && highest>0.0 && current_price>highest)
      return 1;
   if((InpDirectionMode==OVERNIGHT_SHORT_ONLY || InpDirectionMode==OVERNIGHT_BOTH) && lowest<DBL_MAX && current_price<lowest)
      return -1;
   return 0;
}

bool IndicatorValue(const int handle,const int shift,double &value)
{
   if(handle==INVALID_HANDLE) return false;
   double buffer[];
   if(CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
}

bool ATRValue(const ENUM_TIMEFRAMES timeframe,const int period,double &value)
{
   int handle=iATR(_Symbol,timeframe,period);
   if(handle==INVALID_HANDLE) return false;
   bool ok=IndicatorValue(handle,1,value);
   IndicatorRelease(handle);
   return ok;
}

bool EMAValue(const int period,const int shift,double &value)
{
   int handle=iMA(_Symbol,PERIOD_D1,period,0,MODE_EMA,PRICE_CLOSE);
   if(handle==INVALID_HANDLE) return false;
   bool ok=IndicatorValue(handle,shift,value);
   IndicatorRelease(handle);
   return ok;
}

bool PassesPipelineFilters(const int direction,const double price)
{
   if(InpRegimeMode!=OVERNIGHT_REGIME_NONE)
   {
      int period=(InpRegimeMode==OVERNIGHT_REGIME_EMA200 ? 200 : 50);
      double current=0.0,prior=0.0;
      if(!EMAValue(period,1,current)) return false;
      if(direction>0 && price<=current) return false;
      if(direction<0 && price>=current) return false;
      if(InpRegimeMode==OVERNIGHT_REGIME_EMA50_SLOPE)
      {
         if(!EMAValue(period,6,prior)) return false;
         if(direction>0 && current<=prior) return false;
         if(direction<0 && current>=prior) return false;
      }
   }
   if(InpMinimumDailyATRPercent>0.0 || InpMaximumDailyATRPercent>0.0)
   {
      double atr=0.0;
      if(!ATRValue(PERIOD_D1,InpStopATRPeriod,atr) || price<=0.0) return false;
      double percent=atr/price*100.0;
      if(InpMinimumDailyATRPercent>0.0 && percent<InpMinimumDailyATRPercent) return false;
      if(InpMaximumDailyATRPercent>0.0 && percent>InpMaximumDailyATRPercent) return false;
   }
   return true;
}

bool EligibleEntryDay(const MqlDateTime &p)
{
   bool selected=(p.day_of_week==5 && InpTradeFridayNight) ||
                 (p.day_of_week==1 && InpTradeMondayNight) ||
                 (p.day_of_week==2 && InpTradeTuesdayNight);
   if(!selected) return false;
   if(InpRequireRegularNYSEDay && (IsNYSEHoliday(p) || IsNYSEEarlyClose(p))) return false;
   return true;
}

bool OurPosition(ulong &ticket,datetime &entry_time,long &type,double &entry,double &stop,double &target)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      type=PositionGetInteger(POSITION_TYPE);
      entry=PositionGetDouble(POSITION_PRICE_OPEN);
      stop=PositionGetDouble(POSITION_SL);
      target=PositionGetDouble(POSITION_TP);
      return true;
   }
   return false;
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   int digits=0; double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9) { probe*=10.0; digits++; }
   return NormalizeDouble(volume,digits);
}

double PaperAllocationVolume(const double price)
{
   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(price<=0.0 || contract<=0.0) return 0.0;
   double capital=AccountInfoDouble(ACCOUNT_EQUITY)*InpPaperCapitalAllocationPercent/100.0;
   return NormalizeVolume(capital/(price*contract));
}

double PriceToTick(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

bool StopDistance(const double price,double &distance)
{
   if(InpStopMode==OVERNIGHT_STOP_PERCENT)
      distance=price*InpStopPercent/100.0;
   else
   {
      double atr=0.0;
      if(!ATRValue(InpStopATRTimeframe,InpStopATRPeriod,atr)) return false;
      distance=atr*InpStopATRMultiplier;
   }
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   distance=MathMax(distance,minimum);
   return distance>0.0 && MathIsValidNumber(distance);
}

double RiskVolume(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_loss)) return 0.0;
   one_lot_loss=MathAbs(one_lot_loss);
   if(one_lot_loss<=0.0) return 0.0;
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(budget/one_lot_loss);
}

void ManagePipelinePosition(const ulong ticket,const long type,const double entry,const double stop,const double target)
{
   if(!InpUseDefinedRiskStop || stop<=0.0) return;
   double price=(type==POSITION_TYPE_BUY ? SymbolInfoDouble(_Symbol,SYMBOL_BID) : SymbolInfoDouble(_Symbol,SYMBOL_ASK));
   if(g_initial_risk<=0.0) g_initial_risk=MathAbs(entry-stop);
   double initial_risk=g_initial_risk;
   if(price<=0.0 || initial_risk<=0.0) return;
   double achieved=(type==POSITION_TYPE_BUY ? price-entry : entry-price)/initial_risk;
   double proposed=stop;
   bool change=false;
   if(InpBreakEvenAtR>0.0 && achieved>=InpBreakEvenAtR)
   {
      if(type==POSITION_TYPE_BUY && proposed<entry) { proposed=entry; change=true; }
      if(type==POSITION_TYPE_SELL && (proposed>entry || proposed==0.0)) { proposed=entry; change=true; }
   }
   if(InpTrailStartR>0.0 && InpTrailATRMultiplier>0.0 && achieved>=InpTrailStartR)
   {
      double atr=0.0;
      if(ATRValue(InpTrailATRTimeframe,InpTrailATRPeriod,atr))
      {
         double trail=(type==POSITION_TYPE_BUY ? price-atr*InpTrailATRMultiplier : price+atr*InpTrailATRMultiplier);
         if(type==POSITION_TYPE_BUY && trail>proposed) { proposed=trail; change=true; }
         if(type==POSITION_TYPE_SELL && (trail<proposed || proposed==0.0)) { proposed=trail; change=true; }
      }
   }
   proposed=PriceToTick(proposed);
   if(change && MathAbs(proposed-stop)>=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE))
      trade.PositionModify(ticket,proposed,target);
}

bool ExitDue(const datetime entry_server,const datetime now_server)
{
   datetime entry_ny=ServerToNewYork(entry_server);
   MqlDateTime e; TimeToStruct(entry_ny,e);
   int days=(e.day_of_week==5 ? 3 : 1);
   e.hour=InpExitNewYorkHour; e.min=InpExitNewYorkMinute; e.sec=0;
   datetime target_ny=StructToTime(e)+days*86400;
   return ServerToNewYork(now_server)>=target_ny;
}

void Evaluate()
{
   if(!InpEnableTrading) return;
   datetime now_server=TimeCurrent();
   ulong ticket=0; datetime entry_server=0; long position_type=-1; double position_entry=0.0,position_stop=0.0,position_target=0.0;
   if(OurPosition(ticket,entry_server,position_type,position_entry,position_stop,position_target))
   {
      ManagePipelinePosition(ticket,position_type,position_entry,position_stop,position_target);
      if(ExitDue(entry_server,now_server)) { trade.PositionClose(ticket); g_initial_risk=0.0; }
      return;
   }
   g_initial_risk=0.0;

   datetime now_ny=ServerToNewYork(now_server);
   MqlDateTime p; TimeToStruct(now_ny,p);
   int minute=p.hour*60+p.min;
   int entry_minute=InpEntryNewYorkHour*60+InpEntryNewYorkMinute;
   int date_key=DateKey(now_ny);
   if(minute<entry_minute || minute>=entry_minute+InpEntryWindowMinutes || date_key==g_last_entry_date) return;
   if(!EligibleEntryDay(p)) { g_last_entry_date=date_key; return; }

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double signal_price=(bid+ask)/2.0;
   int direction=ExtremeBreakDirection(signal_price,now_ny);
   if(bid<=0.0 || ask<=0.0 || direction==0 || !PassesPipelineFilters(direction,signal_price)) { g_last_entry_date=date_key; return; }
   double entry=(direction>0 ? ask : bid),stop=0.0,target=0.0,volume=0.0;
   if(InpUseDefinedRiskStop)
   {
      double distance=0.0;
      if(!StopDistance(entry,distance)) { g_last_entry_date=date_key; return; }
      stop=PriceToTick(direction>0 ? entry-distance : entry+distance);
      if(InpTargetR>0.0) target=PriceToTick(direction>0 ? entry+distance*InpTargetR : entry-distance*InpTargetR);
      volume=RiskVolume(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,entry,stop);
      g_initial_risk=distance;
   }
   else volume=PaperAllocationVolume(entry);
   if(volume<=0.0) { g_last_entry_date=date_key; return; }
   if(direction>0) trade.Buy(volume,_Symbol,0.0,stop,target,InpUseDefinedRiskStop ? "Pipeline MAX10 long" : "Raw MAX10 overnight");
   else trade.Sell(volume,_Symbol,0.0,stop,target,"Pipeline MAX10 short");
   g_last_entry_date=date_key;
}

int OnInit()
{
   if(InpLookbackCalendarDays<2 || InpPaperCapitalAllocationPercent<=0.0 || InpPaperCapitalAllocationPercent>100.0 ||
      InpRiskPercent<=0.0 || InpRiskPercent>100.0 || InpStopPercent<=0.0 || InpStopATRPeriod<2 || InpStopATRMultiplier<=0.0 ||
      InpTargetR<0.0 || InpBreakEvenAtR<0.0 || InpTrailStartR<0.0 || InpTrailATRPeriod<2 || InpTrailATRMultiplier<=0.0 ||
      InpEntryWindowMinutes<1 || InpEntryWindowMinutes>60 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(!InpEnableTrading) Print("Raw research gate is OFF. Load the research SET deliberately.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   Evaluate();
}
