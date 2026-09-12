#property copyright "Calyx research implementation of Baltussen et al. (2021)"
#property version   "1.01"
#property strict

#include <Trade/Trade.mqh>

input group "Raw paper signal (New York time)"
input bool   InpEnableTrading=true;
input int    InpEntryHour=15;
input int    InpEntryMinute=30;
input int    InpExitHour=16;
input int    InpExitMinute=0;
input int    InpEntryWindowMinutes=10;
input int    InpExitWindowMinutes=30;
input bool   InpRequireNyDstSession=true; // Exness USTEC has no 15:30-16:00 NY session in winter

input group "Common comparison risk and execution"
input double InpRiskPercent=1.0;
input double InpEmergencyStopPercent=2.0;
input int    InpMaxSpreadPoints=0;
input int    InpMaxDeviationPoints=30;
input long   InpMagic=84123001;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_last_evaluated_ny_date=0;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=1; p.hour=12;
   datetime first=StructToTime(p);
   TimeToStruct(first,p);
   int first_sunday=1+((7-p.day_of_week)%7);
   return first_sunday+(occurrence-1)*7;
}

int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   int march_sunday=NthSunday(p.year,3,2);
   int november_sunday=NthSunday(p.year,11,1);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=march_sunday; start.hour=7;
   finish.year=p.year; finish.mon=11; finish.day=november_sunday; finish.hour=6;
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
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE direction,const double entry,const double stop)
{
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(direction,_Symbol,1.0,entry,stop,one_lot_result)) return 0.0;
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
   if(!HistorySelect(NewYorkToServer(start),NewYorkToServer(finish))) return false;
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

bool PreviousCashClose(const MqlDateTime &today_ny,const datetime now_server,double &previous_close)
{
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M1,now_server-8*24*60*60,now_server-1,rates);
   if(count<=0) return false;
   int today_key=DateKey(today_ny);
   for(int i=count-1;i>=0;i--)
   {
      MqlDateTime bar_ny; TimeToStruct(ServerToNewYork(rates[i].time),bar_ny);
      if(DateKey(bar_ny)>=today_key || bar_ny.day_of_week<1 || bar_ny.day_of_week>5) continue;
      int target_minute=InpExitHour*60+InpExitMinute-1;
      if(bar_ny.hour*60+bar_ny.min==target_minute)
      {
         previous_close=rates[i].close;
         return previous_close>0.0;
      }
   }
   return false;
}

bool CloseDuePosition(const MqlDateTime &now_ny)
{
   ulong ticket=0; datetime opened_server=0;
   if(!SelectOurPosition(ticket,opened_server)) return false;
   MqlDateTime opened_ny; TimeToStruct(ServerToNewYork(opened_server),opened_ny);
   // Submit during the final tradable minute. A request sent exactly at a
   // cash-session boundary can be rejected and must never carry overnight.
   bool stale=(DateKey(opened_ny)<DateKey(now_ny));
   int minute_of_day=now_ny.hour*60+now_ny.min;
   int scheduled_close_minute=InpExitHour*60+InpExitMinute;
   int exit_minute=MathMax(0,scheduled_close_minute-1);
   if(!stale && (minute_of_day<exit_minute || minute_of_day>=exit_minute+InpExitWindowMinutes)) return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(!trade.PositionClose(ticket))
      Print("Closing-momentum exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return true;
}

void TryEntry(const datetime now_server,const MqlDateTime &now_ny)
{
   if(!InpEnableTrading || !SpreadOK()) return;
   if(now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   if(InpRequireNyDstSession && !NewYorkDateUsesDST(now_ny)) return;
   int minute_of_day=now_ny.hour*60+now_ny.min;
   int entry_minute=InpEntryHour*60+InpEntryMinute;
   if(minute_of_day<entry_minute || minute_of_day>=entry_minute+InpEntryWindowMinutes) return;
   ulong ticket=0; datetime opened=0;
   if(SelectOurPosition(ticket,opened) || TradedOnNewYorkDate(now_ny)) return;
   int today_key=DateKey(now_ny);
   if(g_last_evaluated_ny_date==today_key) return;

   MqlTick tick;
   double previous_close=0.0;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0 ||
      !PreviousCashClose(now_ny,now_server,previous_close)) return;

   g_last_evaluated_ny_date=today_key;
   double midpoint=(tick.ask+tick.bid)*0.5;
   double rest_of_day_return=(midpoint/previous_close-1.0)*100.0;
   if(MathAbs(rest_of_day_return)<1e-12) return;

   bool buy=(rest_of_day_return>0.0);
   ENUM_ORDER_TYPE direction=(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(buy ? tick.ask : tick.bid);
   double stop=(buy ? entry*(1.0-InpEmergencyStopPercent/100.0)
                    : entry*(1.0+InpEmergencyStopPercent/100.0));
   stop=NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   double lots=LotsForRisk(direction,entry,stop);
   if(lots<=0.0)
   {
      Print("Closing-momentum entry failed: contract data cannot produce a valid lot size");
      return;
   }

   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=StringFormat("ROD %.3f%% -> %s",rest_of_day_return,(buy ? "LONG" : "SHORT"));
   bool sent=(buy ? trade.Buy(lots,_Symbol,0.0,stop,0.0,comment)
                  : trade.Sell(lots,_Symbol,0.0,stop,0.0,comment));
   if(!sent)
      Print("Closing-momentum entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(CloseDuePosition(now_ny)) return;
   TryEntry(now_server,now_ny);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>10.0 || InpEmergencyStopPercent<=0.0 ||
      InpEntryHour<0 || InpEntryHour>23 || InpEntryMinute<0 || InpEntryMinute>59 ||
      InpExitHour<0 || InpExitHour>23 || InpExitMinute<0 || InpExitMinute>59)
      return INIT_PARAMETERS_INCORRECT;
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
