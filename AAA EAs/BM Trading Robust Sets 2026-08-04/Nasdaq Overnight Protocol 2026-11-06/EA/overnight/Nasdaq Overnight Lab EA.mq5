#property copyright "Research implementation of the Nasdaq close-to-open anomaly"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"
#include "..\_Shared\CalyxAdaptivePortfolio.mqh"

enum ENUM_NEGATIVE_DAY_DEFINITION
{
   NEGATIVE_CLOSE_TO_CLOSE=0, // Today's 16:00 close below the prior trading day's 16:00 close
   NEGATIVE_OPEN_TO_CLOSE=1   // Today's 16:00 close below today's 09:30 open
};

input group "Core strategy (New York time)"
input bool   InpEnableTrading=true;
input bool   InpRequireNegativeDay=true;       // False tests the unconditional overnight "Go Long" calendar rule
input ENUM_NEGATIVE_DAY_DEFINITION InpNegativeDayDefinition=NEGATIVE_CLOSE_TO_CLOSE;
input double InpNegativeDayThresholdPercent=0.0; // Enter when the selected day return is below -threshold
input bool   InpAllowFridayEntry=true;           // Friday close is held to Monday pre-open
input int    InpCashOpenHour=9;
input int    InpCashOpenMinute=30;
input int    InpCashCloseHour=16;
input int    InpCashCloseMinute=0;
input int    InpEntryHour=16;
input int    InpEntryMinute=0;
input int    InpExitHour=9;
input int    InpExitMinute=29;
input int    InpEntryWindowMinutes=10;
input int    InpExitWindowMinutes=31;
input int    InpMinimumCashSessionBars=300;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input bool   InpAdaptivePortfolioControls=false;
input double InpEmergencyStopPercent=2.0;
input double InpRewardRisk=0.0; // 0 keeps the calendar exit; positive values add a fixed R target
input int    InpMaxSpreadPoints=0;
input int    InpMaxDeviationPoints=30;
input long   InpMagic=84081601;

input group "Research lab (off = production path)"
input bool   InpLabEnabled=false;
input int    InpLabRedMode=1;       // 0 none, 1 session down, 3 session up (by InpNegativeDayDefinition)
input int    InpLabEntryType=0;     // 0 timed market entry, 1 RSI then swing break
input int    InpLabEntryStart=960;  // New York minute of day
input int    InpLabEntryEnd=970;
input int    InpLabExit=569;
input ENUM_TIMEFRAMES InpLabTF=PERIOD_M15;
input int    InpLabRSIPeriod=14;
input double InpLabRSILevel=0;      // 0 off; long needs RSI below it, short above 100 minus it
input int    InpLabSwingBars=2;     // bars each side of the swing, 0 = no swing condition
input int    InpLabAtrPeriod=14;
input double InpLabStopAtr=0;       // 0 = InpEmergencyStopPercent
input double InpLabTargetAtr=0;
input double InpLabLockAt=0;        // +R that moves the stop, 0 off
input double InpLabLockTo=-0.5;     // R level the stop moves to
input int    InpLabDirection=1;     // 1 long, -1 short mirror, 0 random direction at the long trigger
input int    InpLabSeed=1;

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
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   if(lots>raw+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw,lots);
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const double entry,const double stop)
{
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || stop>=entry) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double one_lot_loss=MathAbs(one_lot_result);
   if(one_lot_loss<=0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent*adaptive/100.0;
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
   if(now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   if(now_ny.day_of_week==5 && !InpAllowFridayEntry) return;
   int minute_of_day=now_ny.hour*60+now_ny.min;
   int entry_minute=InpEntryHour*60+InpEntryMinute;
   if(minute_of_day<entry_minute || minute_of_day>=entry_minute+InpEntryWindowMinutes) return;
   ulong ticket=0; datetime opened=0;
   if(SelectOurPosition(ticket,opened) || TradedOnNewYorkDate(now_ny)) return;
   int today_key=DateKey(now_ny);
   if(g_last_evaluated_ny_date==today_key) return;

   double cash_return=0.0; int bars=0;
   bool has_cash_return=NegativeDayReturn(now_ny,cash_return,bars);
   if(InpRequireNegativeDay && !has_cash_return) return;
   g_last_evaluated_ny_date=today_key;
   if(InpRequireNegativeDay && cash_return>=-MathAbs(InpNegativeDayThresholdPercent)) return;
   // The Markov calculation copies a long completed-D1 history. Evaluate it
   // only once, after the time/day/signal gates have produced a valid entry.
   if(!HAMA_SafeRegimeAllowsDirection(1)) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0) return;
   double stop=NormalizeDouble(tick.ask*(1.0-MathAbs(InpEmergencyStopPercent)/100.0),
                               (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   double target=(InpRewardRisk>0.0 ? NormalizeDouble(tick.ask+(tick.ask-stop)*InpRewardRisk,
                                                      (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS)) : 0.0);
   double lots=LotsForRisk(tick.ask,stop);
   if(lots<=0.0)
   {
      Print("Nasdaq overnight entry skipped: 1% risk size is below the broker minimum or contract data is missing");
      return;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=(InpRequireNegativeDay
                   ? StringFormat("Overnight after %.3f%% cash day",cash_return)
                   : "Overnight unconditional Go Long");
   if(!trade.Buy(lots,_Symbol,0.0,stop,target,comment))
      Print("Nasdaq overnight entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

int g_lab_rsi=INVALID_HANDLE,g_lab_atr=INVALID_HANDLE,g_lab_done=0,g_lab_checked=0;
bool g_lab_ok=false,g_lab_armed=false,g_lab_locked=false;
datetime g_lab_bar=0;
double g_lab_R=0.0;

double LabValue(const int handle)
{
   double v[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,1,1,v)!=1) return -1.0;
   return v[0];
}

bool LabSession(const MqlDateTime &now_ny,MqlDateTime &session)
{
   int minute=now_ny.hour*60+now_ny.min;
   session=now_ny;
   if(minute>=InpCashCloseHour*60+InpCashCloseMinute && now_ny.day_of_week>=1 && now_ny.day_of_week<=5) return true;
   datetime t=StructToTime(now_ny);
   for(int i=0;i<7;i++)
   {
      t-=86400; TimeToStruct(t,session);
      if(session.day_of_week>=1 && session.day_of_week<=5) return true;
   }
   return false;
}

bool LabNightOk(const MqlDateTime &session)
{
   if(InpLabRedMode==0) return true;
   double ret=0.0; int bars=0;
   if(!NegativeDayReturn(session,ret,bars)) return false;
   if(InpLabRedMode==3) return ret>0.0;
   return ret<0.0;
}

double LabSwing(const int side)
{
   for(int i=InpLabSwingBars+2;i<300;i++)
   {
      double level=(side>0?iHigh(_Symbol,InpLabTF,i):iLow(_Symbol,InpLabTF,i));
      if(level<=0.0) return 0.0;
      bool ok=true;
      for(int j=1;j<=InpLabSwingBars && ok;j++)
      {
         double a=(side>0?iHigh(_Symbol,InpLabTF,i-j):iLow(_Symbol,InpLabTF,i-j)),b=(side>0?iHigh(_Symbol,InpLabTF,i+j):iLow(_Symbol,InpLabTF,i+j));
         if(side>0 ? (a>=level || b>level) : (a<=level || b<level)) ok=false;
      }
      if(ok) return level;
   }
   return 0.0;
}

void LabEnter(const int dir)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return;
   double price=(dir>0?tick.ask:tick.bid),atr=0.0;
   if(InpLabStopAtr>0.0 || InpLabTargetAtr>0.0) { atr=LabValue(g_lab_atr); if(atr<=0.0) return; }
   double dist=(InpLabStopAtr>0.0?InpLabStopAtr*atr:price*MathAbs(InpEmergencyStopPercent)/100.0);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double stop=NormalizeDouble(price-dir*dist,digits),target=(InpLabTargetAtr>0.0?NormalizeDouble(price+dir*InpLabTargetAtr*atr,digits):0.0);
   double lots=LotsForRisk(price,price-dist);
   if(lots<=0.0) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool ok=(dir>0?trade.Buy(lots,_Symbol,0.0,stop,target,"Overnight lab"):trade.Sell(lots,_Symbol,0.0,stop,target,"Overnight lab"));
   if(ok) { g_lab_R=dist; g_lab_locked=false; }
   else Print("Overnight lab entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void LabManage(const MqlDateTime &now_ny)
{
   ulong ticket=0; datetime opened=0;
   if(!SelectOurPosition(ticket,opened)) return;
   if(now_ny.day_of_week>=1 && now_ny.day_of_week<=5)
   {
      MqlDateTime e=now_ny; e.hour=InpLabExit/60; e.min=InpLabExit%60; e.sec=0;
      datetime exit_time=NewYorkToServer(e);
      if(TimeCurrent()>=exit_time && opened<exit_time)
      {
         trade.SetExpertMagicNumber((ulong)InpMagic);
         trade.SetTypeFillingBySymbol(_Symbol);
         trade.SetDeviationInPoints(InpMaxDeviationPoints);
         if(!trade.PositionClose(ticket)) Print("Overnight lab exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
         return;
      }
   }
   if(InpLabLockAt<=0.0 || g_lab_locked || g_lab_R<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool is_long=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   double open=PositionGetDouble(POSITION_PRICE_OPEN),gain=(is_long?tick.bid-open:open-tick.ask);
   if(gain<InpLabLockAt*g_lab_R) return;
   double stop=NormalizeDouble(is_long?open+InpLabLockTo*g_lab_R:open-InpLabLockTo*g_lab_R,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   trade.SetExpertMagicNumber((ulong)InpMagic);
   if(trade.PositionModify(ticket,stop,PositionGetDouble(POSITION_TP))) g_lab_locked=true;
}

void LabEntry(const MqlDateTime &now_ny)
{
   if(!InpEnableTrading || now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   int minute=now_ny.hour*60+now_ny.min;
   if(minute<InpLabEntryStart || minute>=InpLabEntryEnd) return;
   ulong ticket=0; datetime opened=0;
   if(SelectOurPosition(ticket,opened)) return;
   MqlDateTime session;
   if(!LabSession(now_ny,session)) return;
   int key=DateKey(session);
   if(g_lab_done==key) return;
   if(g_lab_checked!=key) { g_lab_checked=key; g_lab_ok=LabNightOk(session); g_lab_armed=false; g_lab_bar=0; }
   if(!g_lab_ok) return;
   int side=(InpLabDirection==0?1:InpLabDirection);
   if(InpLabEntryType==0)
   {
      g_lab_done=key;
      if(InpLabRSILevel>0.0)
      {
         double rsi=LabValue(g_lab_rsi);
         if(rsi<=0.0 || (side>0 ? rsi>=InpLabRSILevel : rsi<=100.0-InpLabRSILevel)) return;
      }
      LabEnter(side);
      return;
   }
   datetime bar=iTime(_Symbol,InpLabTF,0);
   if(bar==g_lab_bar) return;
   g_lab_bar=bar;
   MqlDateTime w=now_ny; w.hour=InpLabEntryStart/60; w.min=InpLabEntryStart%60; w.sec=0;
   if(iTime(_Symbol,InpLabTF,1)<NewYorkToServer(w)) return;
   if(InpLabRSILevel<=0.0) g_lab_armed=true;
   else
   {
      double rsi=LabValue(g_lab_rsi);
      if(rsi>0.0 && (side>0 ? rsi<InpLabRSILevel : rsi>100.0-InpLabRSILevel)) g_lab_armed=true;
   }
   if(!g_lab_armed) return;
   if(InpLabSwingBars>0)
   {
      double level=LabSwing(side),close=iClose(_Symbol,InpLabTF,1);
      if(level<=0.0 || (side>0 ? close<=level : close>=level)) return;
   }
   g_lab_done=key;
   LabEnter(InpLabDirection==0 ? ((MathRand()&1)==1?1:-1) : side);
}

void ProcessStrategy()
{
   if(InpLabEnabled)
   {
      datetime lab_now=TimeCurrent();
      if(lab_now<=0) return;
      MqlDateTime lab_ny; TimeToStruct(ServerToNewYork(lab_now),lab_ny);
      LabManage(lab_ny);
      LabEntry(lab_ny);
      return;
   }
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
   if(InpRiskPercent<=0.0 || InpRiskPercent>10.0 || InpEmergencyStopPercent<=0.0 ||
      InpRewardRisk<0.0 || InpEntryHour<0 || InpEntryHour>23 || InpEntryMinute<0 || InpEntryMinute>59 ||
      InpExitHour<0 || InpExitHour>23 || InpExitMinute<0 || InpExitMinute>59)
   {
      Print("Invalid risk settings");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpLabEnabled)
   {
      MathSrand(InpLabSeed);
      if(InpLabRSILevel>0.0) { g_lab_rsi=iRSI(_Symbol,InpLabTF,InpLabRSIPeriod,PRICE_CLOSE); if(g_lab_rsi==INVALID_HANDLE) return INIT_FAILED; }
      if(InpLabStopAtr>0.0 || InpLabTargetAtr>0.0) { g_lab_atr=iATR(_Symbol,InpLabTF,InpLabAtrPeriod); if(g_lab_atr==INVALID_HANDLE) return INIT_FAILED; }
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
