#property copyright "Calyx paper-replication research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

input group "Paper replication"
input bool   InpEnableTrading=false;
input double InpLondonOpenHour=8.0;          // 08:00 Europe/London
input int    InpFormationMinutes=30;          // Paper signal: first 30 minutes
input double InpExitLondonHour=17.0;          // Explicit because the paper omits its selected exit
input bool   InpReverseSignal=false;          // Paper reports the GBPUSD relationship as reversed
input bool   InpTradeMonday=true;
input bool   InpTradeTuesday=true;
input bool   InpTradeWednesday=true;
input bool   InpTradeThursday=true;
input bool   InpTradeFriday=true;

input group "Risk and execution"
input double InpRiskPercent=1.0;              // Calyx default and installer-controlled risk
input int    InpAtrPeriod=14;
input double InpEmergencyStopAtrMultiple=10.0;// Operational protection; paper exit remains time-based
input int    InpExitSecondsEarly=30;
input int    InpMaxDeviationBrokerPoints=20;

input group "Identity"
input long   InpMagic=980908401;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC;
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_m1_bar=0;
int g_atr_handle=INVALID_HANDLE;

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

int LondonUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=LastSunday(p.year,3); start.hour=1;
   finish.year=p.year; finish.mon=10; finish.day=LastSunday(p.year,10); finish.hour=1;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? 1 : 0);
}

bool LondonDateUsesDST(const MqlDateTime &london)
{
   int march=LastSunday(london.year,3),october=LastSunday(london.year,10);
   if(london.mon>3 && london.mon<10) return true;
   if(london.mon<3 || london.mon>10) return false;
   if(london.mon==3) return london.day>=march;
   return london.day<october;
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

datetime ServerToLondon(const datetime server_time)
{
   datetime utc=ServerToUTC(server_time);
   return utc+LondonUTCOffsetHours(utc)*3600;
}

datetime LondonToServer(const MqlDateTime &source)
{
   MqlDateTime london=source;
   int offset=(LondonDateUsesDST(london) ? 1 : 0);
   datetime utc=StructToTime(london)-offset*3600;
   return UTCToServer(utc);
}

int MinuteOfDay(const double decimal_hour)
{
   return (int)MathRound(decimal_hour*60.0);
}

void SetClockFromMinute(MqlDateTime &p,const int minute)
{
   p.hour=minute/60;
   p.min=minute%60;
   p.sec=0;
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

bool AttemptedToday(const MqlDateTime &now_london)
{
   MqlDateTime start=now_london;
   start.hour=0; start.min=0; start.sec=0;
   if(!HistorySelect(LondonToServer(start),TimeCurrent())) return false;
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

bool FormationReturn(const MqlDateTime &today_london,double &formation_return)
{
   MqlDateTime begin= today_london;
   MqlDateTime finish=today_london;
   int open_minute=MinuteOfDay(InpLondonOpenHour);
   SetClockFromMinute(begin,open_minute);
   SetClockFromMinute(finish,open_minute+InpFormationMinutes);
   datetime server_begin=LondonToServer(begin);
   datetime server_finish=LondonToServer(finish);

   MqlRates bars[];
   int count=CopyRates(_Symbol,PERIOD_M5,server_begin,server_finish-1,bars);
   if(count<InpFormationMinutes/5) return false;
   int earliest=0,latest=0;
   for(int i=1;i<count;i++)
   {
      if(bars[i].time<bars[earliest].time) earliest=i;
      if(bars[i].time>bars[latest].time) latest=i;
   }
   if(MathAbs((long)(bars[earliest].time-server_begin))>60) return false;
   if(server_finish-bars[latest].time>6*60) return false;
   if(bars[earliest].open<=0.0 || bars[latest].close<=0.0) return false;
   formation_return=MathLog(bars[latest].close/bars[earliest].open);
   return MathIsValidNumber(formation_return);
}

double EmergencyDistance()
{
   if(g_atr_handle==INVALID_HANDLE) return 0.0;
   double values[1];
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1 || values[0]<=0.0) return 0.0;
   return values[0]*InpEmergencyStopAtrMultiple;
}

void ClosePaperPosition()
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

void EvaluatePaperEntry()
{
   if(!InpEnableTrading || HasPosition()) return;
   MqlDateTime now_london; TimeToStruct(ServerToLondon(TimeCurrent()),now_london);
   if(!DayAllowed(now_london.day_of_week) || AttemptedToday(now_london)) return;
   int entry_minute=MinuteOfDay(InpLondonOpenHour)+InpFormationMinutes;
   if(now_london.hour*60+now_london.min!=entry_minute) return;

   double r1=0.0;
   if(!FormationReturn(now_london,r1) || r1==0.0) return;
   int direction=(r1>0.0 ? 1 : -1);
   if(InpReverseSignal) direction=-direction;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double distance=EmergencyDistance();
   if(distance<=0.0) return;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=PriceToTick(entry-direction*distance);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return;

   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   string comment=(InpReverseSignal ? "Raw London reverse" : "Raw London momentum");
   bool ok=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,0.0,comment) : trade.Sell(lots,_Symbol,0.0,stop,0.0,comment));
   if(!ok) Print("Paper entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

int OnInit()
{
   int open_minute=MinuteOfDay(InpLondonOpenHour);
   int exit_minute=MinuteOfDay(InpExitLondonHour);
   if(InpRiskPercent<=0.0 || InpRiskPercent>100.0 || InpAtrPeriod<2 || InpEmergencyStopAtrMultiple<=0.0 ||
      InpFormationMinutes<=0 || InpFormationMinutes%5!=0 || open_minute<0 ||
      open_minute+InpFormationMinutes>=exit_minute || exit_minute>24*60 ||
      InpExitSecondsEarly<0 || InpExitSecondsEarly>=300 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   if(!InpTradeMonday && !InpTradeTuesday && !InpTradeWednesday && !InpTradeThursday && !InpTradeFriday)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M15,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(!InpEnableTrading) Print("Research gate is OFF. Load an approved research SET deliberately.");
   g_last_m1_bar=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   MqlDateTime now_london; TimeToStruct(ServerToLondon(TimeCurrent()),now_london);
   int now_seconds=now_london.hour*3600+now_london.min*60+now_london.sec;
   int exit_seconds=MinuteOfDay(InpExitLondonHour)*60-InpExitSecondsEarly;
   if(now_seconds>=exit_seconds && HasPosition()) ClosePaperPosition();

   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current>0 && current!=g_last_m1_bar)
   {
      g_last_m1_bar=current;
      EvaluatePaperEntry();
   }
}
