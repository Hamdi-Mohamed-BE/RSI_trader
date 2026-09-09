#property copyright "Calyx paper-replication research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_RAW_INTRADAY_SIGNAL
{
   RAW_REST_OF_DAY=0,         // Paper's main rule: prior close to 15:30
   RAW_OVERNIGHT_FIRST_HALF=1,// Paper comparator: prior close to 10:00
   RAW_SIGN_AGREEMENT=2       // Trade only when both paper signals agree
};

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

input group "Paper replication"
input bool   InpEnableTrading=false;
input ENUM_RAW_INTRADAY_SIGNAL InpSignal=RAW_REST_OF_DAY;
input double InpCashOpenNyHour=9.5;          // 09:30 America/New_York
input double InpSignalNyHour=15.5;           // 30 minutes before 16:00 close
input double InpCashCloseNyHour=16.0;
input int    InpFirstHalfMinutes=30;
input bool   InpTradeMonday=true;
input bool   InpTradeTuesday=true;
input bool   InpTradeWednesday=true;
input bool   InpTradeThursday=true;
input bool   InpTradeFriday=true;

input group "Risk and execution"
input double InpRiskPercent=1.0;              // Calyx default: 1% maximum emergency-stop risk
input int    InpAtrPeriod=14;
input double InpEmergencyStopAtrMultiple=10.0;// Operational protection; paper exit remains time-based
input int    InpExitSecondsBeforeClose=30;     // Avoid broker session closing before an exact-close order
input int    InpMaxDeviationBrokerPoints=30;

input group "Identity"
input long   InpMagic=980908301;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC;
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_minute_bar=0;
int g_atr_handle=INVALID_HANDLE;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=1; p.hour=12;
   datetime first=StructToTime(p);
   TimeToStruct(first,p);
   return 1+((7-p.day_of_week)%7)+(occurrence-1)*7;
}

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

int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=NthSunday(p.year,3,2); start.hour=7;
   finish.year=p.year; finish.mon=11; finish.day=NthSunday(p.year,11,1); finish.hour=6;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? -4 : -5);
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march=NthSunday(ny.year,3,2),november=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march;
   return ny.day<november;
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

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc=ServerToUTC(server_time);
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime ny=source;
   int ny_offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   datetime utc=StructToTime(ny)-ny_offset*3600;
   return UTCToServer(utc);
}

void SetClockFromDecimal(MqlDateTime &p,const double decimal_hour)
{
   int total=(int)MathRound(decimal_hour*60.0);
   p.hour=total/60;
   p.min=total%60;
   p.sec=0;
}

int NyMinute(const double decimal_hour)
{
   return (int)MathRound(decimal_hour*60.0);
}

double PriceToTick(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   double loss=MathAbs(one_lot);
   if(loss<=0.0) return 0.0;
   return NormalizeVolume((AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0)/loss);
}

bool HasPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   return false;
}

bool AttemptedToday(const MqlDateTime &now_ny)
{
   MqlDateTime start=now_ny;
   start.hour=0; start.min=0; start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent())) return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket>0 && HistoryOrderGetString(ticket,ORDER_SYMBOL)==_Symbol && HistoryOrderGetInteger(ticket,ORDER_MAGIC)==InpMagic)
         return true;
   }
   return false;
}

bool DayAllowed(const int day_of_week)
{
   if(day_of_week==1) return InpTradeMonday;
   if(day_of_week==2) return InpTradeTuesday;
   if(day_of_week==3) return InpTradeWednesday;
   if(day_of_week==4) return InpTradeThursday;
   if(day_of_week==5) return InpTradeFriday;
   return false;
}

bool PriceAtCompletedMinute(const MqlDateTime &ny_time,double &price)
{
   MqlDateTime target=ny_time;
   target.sec=0;
   datetime server_end=NewYorkToServer(target);
   // The test itself runs on M15. Reading the completed M15 bar makes both the
   // 10:00 and 16:00 reference prices stable across weekend history boundaries.
   datetime server_start=server_end-60*60;
   MqlRates bars[];
   int count=CopyRates(_Symbol,PERIOD_M15,server_start,server_end-1,bars);
   if(count<=0) return false;
   int latest=0;
   for(int i=1;i<count;i++) if(bars[i].time>bars[latest].time) latest=i;
   if(server_end-bars[latest].time>30*60) return false;
   price=bars[latest].close;
   return price>0.0;
}

bool PreviousCashClose(const MqlDateTime &today_ny,double &price)
{
   MqlDateTime candidate=today_ny;
   SetClockFromDecimal(candidate,InpCashCloseNyHour);
   datetime day=StructToTime(candidate)-86400;
   for(int attempt=0;attempt<7;attempt++,day-=86400)
   {
      MqlDateTime prior; TimeToStruct(day,prior);
      if(prior.day_of_week==0 || prior.day_of_week==6) continue;
      // PriceAtCompletedMinute expects an interval endpoint; 16:00 returns the 15:59 close.
      if(PriceAtCompletedMinute(prior,price)) return true;
   }
   return false;
}

bool FirstHalfHourPrice(const MqlDateTime &today_ny,double &price)
{
   MqlDateTime endpoint=today_ny;
   int minute=NyMinute(InpCashOpenNyHour)+InpFirstHalfMinutes;
   endpoint.hour=minute/60; endpoint.min=minute%60; endpoint.sec=0;
   return PriceAtCompletedMinute(endpoint,price);
}

double EmergencyDistance()
{
   if(g_atr_handle==INVALID_HANDLE) return 0.0;
   double values[1];
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1 || values[0]<=0.0) return 0.0;
   return values[0]*InpEmergencyStopAtrMultiple;
}

int SignalDirection(const MqlDateTime &today_ny,const double market_price)
{
   double previous_close=0.0;
   if(!PreviousCashClose(today_ny,previous_close) || previous_close<=0.0)
      return 0;
   int rod=(market_price>previous_close ? 1 : (market_price<previous_close ? -1 : 0));
   if(InpSignal==RAW_REST_OF_DAY) return rod;

   double first_half=0.0;
   if(!FirstHalfHourPrice(today_ny,first_half) || first_half<=0.0) return 0;
   int onfh=(first_half>previous_close ? 1 : (first_half<previous_close ? -1 : 0));
   if(InpSignal==RAW_OVERNIGHT_FIRST_HALF) return onfh;
   return (rod!=0 && rod==onfh ? rod : 0);
}

void CloseAtCashClose()
{
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         if(!trade.PositionClose(ticket,InpMaxDeviationBrokerPoints))
            Print("Paper close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      }
   }
}

void EvaluateRawEntry()
{
   if(!InpEnableTrading || HasPosition()) return;
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(TimeCurrent()),now_ny);
   if(!DayAllowed(now_ny.day_of_week)) return;
   if(AttemptedToday(now_ny)) return;
   if(now_ny.hour*60+now_ny.min!=NyMinute(InpSignalNyHour)) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double midpoint=(tick.bid+tick.ask)/2.0;
   int direction=SignalDirection(now_ny,midpoint);
   if(direction==0) return;

   double distance=EmergencyDistance();
   if(distance<=0.0) return;
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=PriceToTick(entry-direction*distance);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0) return;

   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   string comment=(InpSignal==RAW_REST_OF_DAY ? "Raw ROD" : (InpSignal==RAW_OVERNIGHT_FIRST_HALF ? "Raw ONFH" : "Raw agreement"));
   bool ok=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,0.0,comment) : trade.Sell(lots,_Symbol,0.0,stop,0.0,comment));
   if(!ok) Print("Paper entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>100.0 || InpAtrPeriod<2 || InpEmergencyStopAtrMultiple<=0.0 ||
      InpExitSecondsBeforeClose<0 || InpExitSecondsBeforeClose>=1800 ||
      InpFirstHalfMinutes<=0 || NyMinute(InpCashOpenNyHour)+InpFirstHalfMinutes>=NyMinute(InpSignalNyHour) ||
      NyMinute(InpSignalNyHour)>=NyMinute(InpCashCloseNyHour) || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   if(!InpTradeMonday && !InpTradeTuesday && !InpTradeWednesday && !InpTradeThursday && !InpTradeFriday)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M15,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(!InpEnableTrading) Print("Research gate is OFF. Load an approved research SET deliberately.");
   g_last_minute_bar=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(TimeCurrent()),now_ny);
   int now_seconds=now_ny.hour*3600+now_ny.min*60+now_ny.sec;
   int exit_seconds=NyMinute(InpCashCloseNyHour)*60-InpExitSecondsBeforeClose;
   if(now_seconds>=exit_seconds && HasPosition()) CloseAtCashClose();

   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current>0 && current!=g_last_minute_bar)
   {
      g_last_minute_bar=current;
      EvaluateRawEntry();
   }
}
