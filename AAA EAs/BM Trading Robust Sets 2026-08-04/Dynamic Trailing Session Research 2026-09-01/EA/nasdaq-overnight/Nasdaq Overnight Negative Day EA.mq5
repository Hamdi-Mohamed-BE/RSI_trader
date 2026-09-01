#property copyright "Research implementation of the Nasdaq close-to-open anomaly"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"

enum ENUM_NEGATIVE_DAY_DEFINITION
{
   NEGATIVE_CLOSE_TO_CLOSE=0, // Today's 16:00 close below the prior trading day's 16:00 close
   NEGATIVE_OPEN_TO_CLOSE=1   // Today's 16:00 close below today's 09:30 open
};

input group "Core strategy (New York time)"
input bool   InpEnableTrading=true;
input ENUM_NEGATIVE_DAY_DEFINITION InpNegativeDayDefinition=NEGATIVE_CLOSE_TO_CLOSE;
input double InpNegativeDayThresholdPercent=0.0; // Enter when the selected day return is below -threshold
input bool   InpAllowFridayEntry=true;           // Friday close is held to Monday pre-open
input int    InpCashOpenHour=9;
input int    InpCashOpenMinute=30;
input int    InpCashCloseHour=16;
input int    InpCashCloseMinute=0;
input int    InpExitHour=9;
input int    InpExitMinute=29;
input int    InpEntryWindowMinutes=10;
input int    InpExitWindowMinutes=31;
input int    InpMinimumCashSessionBars=300;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input double InpEmergencyStopPercent=2.0;
input int    InpMaxSpreadPoints=0;
input int    InpMaxDeviationPoints=30;
input long   InpMagic=84081601;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0; // Exness historical bars are UTC
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_last_evaluated_ny_date=0;

int DaysInMonth(const int year,const int month)
{
   if(month==2) return (((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=1; p.hour=12;
   datetime first=StructToTime(p);
   TimeToStruct(first,p);
   int first_sunday=1+((7-p.day_of_week)%7);
   return first_sunday+(occurrence-1)*7;
}

// Exact modern US DST rule: second Sunday in March to first Sunday in November.
int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   int march_sunday=NthSunday(p.year,3,2);
   int november_sunday=NthSunday(p.year,11,1);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=march_sunday; start.hour=7; // 02:00 EST
   finish.year=p.year; finish.mon=11; finish.day=november_sunday; finish.hour=6; // 02:00 EDT
   datetime dst_start=StructToTime(start);
   datetime dst_finish=StructToTime(finish);
   return (utc_time>=dst_start && utc_time<dst_finish ? -4 : -5);
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   return server_time-ServerUTCOffsetSeconds();
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc=ServerToUTC(server_time);
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march_sunday=NthSunday(ny.year,3,2);
   int november_sunday=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march_sunday;
   return ny.day<november_sunday;
}

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime ny=source;
   int ny_offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   datetime local=StructToTime(ny);
   datetime utc=local-ny_offset*3600;
   return utc+ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
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

double LotsForRisk(const double entry,const double stop)
{
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || stop>=entry) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double one_lot_loss=MathAbs(one_lot_result);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/one_lot_loss);
}

bool SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

bool SelectOurPosition(ulong &ticket,datetime &opened)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         opened=(datetime)PositionGetInteger(POSITION_TIME);
         return true;
      }
   }
   return false;
}

bool TradedOnNewYorkDate(const MqlDateTime &ny)
{
   MqlDateTime start=ny;
   start.hour=0; start.min=0; start.sec=0;
   MqlDateTime finish=start;
   finish.hour=23; finish.min=59; finish.sec=59;
   datetime from=NewYorkToServer(start);
   datetime to=NewYorkToServer(finish);
   if(!HistorySelect(from,to)) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN)
         return true;
   }
   return false;
}

bool PreviousCashClose(const MqlDateTime &today_ny,const datetime current_open_server,double &previous_close)
{
   datetime from=current_open_server-8*24*60*60;
   datetime to=current_open_server-1;
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(count<=0) return false;
   int today_key=DateKey(today_ny);
   for(int i=count-1;i>=0;i--)
   {
      MqlDateTime bar_ny; TimeToStruct(ServerToNewYork(rates[i].time),bar_ny);
      if(DateKey(bar_ny)>=today_key) continue;
      if(bar_ny.day_of_week<1 || bar_ny.day_of_week>5) continue;
      int bar_minute=bar_ny.hour*60+bar_ny.min;
      int target_minute=InpCashCloseHour*60+InpCashCloseMinute-1;
      if(bar_minute==target_minute)
      {
         previous_close=rates[i].close;
         return previous_close>0.0;
      }
   }
   return false;
}

bool NegativeDayReturn(const MqlDateTime &today_ny,double &day_return_percent,int &bar_count)
{
   MqlDateTime start=today_ny;
   start.hour=InpCashOpenHour; start.min=InpCashOpenMinute; start.sec=0;
   MqlDateTime finish=today_ny;
   finish.hour=InpCashCloseHour; finish.min=InpCashCloseMinute; finish.sec=0;
   datetime from=NewYorkToServer(start);
   datetime to=NewYorkToServer(finish)-1;
   MqlRates rates[];
   bar_count=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(bar_count<InpMinimumCashSessionBars) return false;
   double cash_open=rates[0].open;
   double cash_close=rates[bar_count-1].close;
   if(cash_open<=0.0 || cash_close<=0.0) return false;
   double reference=cash_open;
   if(InpNegativeDayDefinition==NEGATIVE_CLOSE_TO_CLOSE)
   {
      if(!PreviousCashClose(today_ny,from,reference)) return false;
   }
   day_return_percent=(cash_close/reference-1.0)*100.0;
   return true;
}

bool CloseDuePosition(const MqlDateTime &now_ny)
{
   ulong ticket=0; datetime opened_server=0;
   if(!SelectOurPosition(ticket,opened_server)) return false;
   MqlDateTime opened_ny; TimeToStruct(ServerToNewYork(opened_server),opened_ny);
   if(DateKey(opened_ny)==DateKey(now_ny)) return false;
   int minute_of_day=now_ny.hour*60+now_ny.min;
   int exit_minute=InpExitHour*60+InpExitMinute;
   if(minute_of_day<exit_minute || minute_of_day>=exit_minute+InpExitWindowMinutes) return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(!trade.PositionClose(ticket))
      Print("Nasdaq overnight exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return true;
}

void TryEntry(const MqlDateTime &now_ny)
{
   if(!DTS_EntrySessionAllowed()) return;
   if(!InpEnableTrading || !SpreadOK()) return;
   if(!HAMA_SafeRegimeAllowsDirection(1)) return;
   if(now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   if(now_ny.day_of_week==5 && !InpAllowFridayEntry) return;
   int minute_of_day=now_ny.hour*60+now_ny.min;
   int close_minute=InpCashCloseHour*60+InpCashCloseMinute;
   if(minute_of_day<close_minute || minute_of_day>=close_minute+InpEntryWindowMinutes) return;
   ulong ticket=0; datetime opened=0;
   if(SelectOurPosition(ticket,opened) || TradedOnNewYorkDate(now_ny)) return;
   int today_key=DateKey(now_ny);
   if(g_last_evaluated_ny_date==today_key) return;

   double cash_return=0.0; int bars=0;
   if(!NegativeDayReturn(now_ny,cash_return,bars)) return;
   g_last_evaluated_ny_date=today_key;
   if(cash_return>=-MathAbs(InpNegativeDayThresholdPercent)) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0) return;
   double stop=NormalizeDouble(tick.ask*(1.0-MathAbs(InpEmergencyStopPercent)/100.0),
                               (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   double lots=LotsForRisk(tick.ask,stop);
   if(lots<=0.0)
   {
      Print("Nasdaq overnight entry skipped: 1% risk size is below the broker minimum or contract data is missing");
      return;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=StringFormat("Overnight after %.3f%% cash day",cash_return);
   if(!trade.Buy(lots,_Symbol,0.0,stop,0.0,comment))
      Print("Nasdaq overnight entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ProcessStrategy()
{
   DTS_ManageDynamicTrailing(InpMagic);
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(CloseDuePosition(now_ny)) return;
   TryEntry(now_ny);
}

int OnInit()
{
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   if(InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpEmergencyStopPercent<=0.0)
   {
      Print("Invalid risk settings");
      return INIT_PARAMETERS_INCORRECT;
   }
   EventSetTimer(15);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   ProcessStrategy();
}

void OnTimer()
{
   ProcessStrategy();
}
