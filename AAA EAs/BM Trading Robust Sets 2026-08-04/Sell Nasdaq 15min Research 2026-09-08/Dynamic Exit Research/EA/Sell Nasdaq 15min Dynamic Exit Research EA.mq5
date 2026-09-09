#property copyright "Calyx research implementation"
#property version   "1.10"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

enum ENUM_STOP_DISTANCE_MODE
{
   STOP_FIXED_PIPS=0,
   STOP_SETUP_HIGH=1,
   STOP_OPENING_RANGE=2,
   STOP_ATR=3,
   STOP_MAX_RANGE_ATR=4
};

enum ENUM_TARGET_DISTANCE_MODE
{
   TARGET_FIXED_PIPS=0,
   TARGET_R_MULTIPLE=1,
   TARGET_OPENING_RANGE=2,
   TARGET_ATR=3
};

input group "Research gate"
input bool   InpEnableTrading=false;

input group "New York M15 setup"
input double InpNewYorkOpenHour=9.5;          // 09:30 America/New_York
input int    InpOpeningRangeMinutes=15;       // First New York candle
input bool   InpRequirePriorLondonBearish=true; // 09:15-09:30 candle must close bearish
input double InpMinimumBodyFraction=0.0;      // Bearish body / full candle range
input double InpMinimumSetupRangePips=0.0;    // 0 disables the lower bound
input double InpMaximumSetupRangePips=0.0;    // 0 disables the upper bound
input double InpEntryBufferPips=0.0;          // Sell stop below first M15 low
input int    InpEntryWindowMinutes=60;        // Minutes after 09:45
input bool   InpCancelIfSetupHighBreaks=false;

input group "Weekday selection"
input bool   InpTradeMonday=true;
input bool   InpTradeTuesday=true;
input bool   InpTradeWednesday=true;
input bool   InpTradeThursday=true;
input bool   InpTradeFriday=true;

input group "Risk and exits"
input double InpRiskPercent=1.0;
input ENUM_STOP_DISTANCE_MODE InpStopMode=STOP_FIXED_PIPS;
input double InpStopPips=600.0;               // 1 pip = 10 broker points
input double InpStopRangeMultiple=1.0;
input int    InpAtrPeriod=14;
input double InpStopAtrMultiple=1.5;
input double InpDynamicStopBufferPips=0.0;
input double InpMinimumDynamicStopPips=0.0;   // 0 disables the floor
input double InpMaximumDynamicStopPips=0.0;   // 0 disables the ceiling
input ENUM_TARGET_DISTANCE_MODE InpTargetMode=TARGET_FIXED_PIPS;
input double InpTargetPips=1000.0;
input double InpTargetRMultiple=2.0;
input double InpTargetRangeMultiple=2.0;
input double InpTargetAtrMultiple=3.0;
input double InpHardExitNyHour=15.9166667;    // 15:55 New York
input double InpBreakEvenAtR=0.0;             // 0 disables
input double InpTrailStartAtR=0.0;            // 0 disables
input double InpTrailDistanceR=0.5;
input bool   InpUseDynamic5020=false;          // At 50% of TP, lock 20% of TP
input int    InpMaxSpreadBrokerPoints=0;       // 0 uses recorded broker spread without an added gate
input int    InpMaxDeviationBrokerPoints=30;

input group "Identity"
input long   InpMagic=980908150;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC;
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_minute_bar=0;
int g_atr_handle=INVALID_HANDLE;

struct WindowStats
{
   double open;
   double high;
   double low;
   double close;
   int bars;
};

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

double PipSize()
{
   // Calyx display convention requested by the user: one pip equals ten broker points.
   return 10.0*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
}

double PriceToTick(const double value,const int rounding=0)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   double units=value/tick;
   if(rounding<0) units=MathFloor(units+1e-9);
   else if(rounding>0) units=MathCeil(units-1e-9);
   else units=MathRound(units);
   return NormalizeDouble(units*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
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
   double one_lot=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_SELL,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   double loss=MathAbs(one_lot);
   if(loss<=0.0) return 0.0;
   return NormalizeVolume((AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0)/loss);
}

bool SpreadOK()
{
   if(InpMaxSpreadBrokerPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadBrokerPoints;
}

double CompletedM15ATR()
{
   if(g_atr_handle==INVALID_HANDLE) return 0.0;
   double values[1];
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1) return 0.0;
   return values[0];
}

bool CalculateExitDistances(const double entry,const WindowStats &setup,double &stop_distance,double &target_distance)
{
   double pip=PipSize();
   double range=setup.high-setup.low;
   double atr=CompletedM15ATR();
   double buffer=InpDynamicStopBufferPips*pip;
   if(pip<=0.0 || range<=0.0) return false;

   if(InpStopMode==STOP_FIXED_PIPS)
      stop_distance=InpStopPips*pip;
   else if(InpStopMode==STOP_SETUP_HIGH)
      stop_distance=(setup.high-entry)+buffer;
   else if(InpStopMode==STOP_OPENING_RANGE)
      stop_distance=range*InpStopRangeMultiple+buffer;
   else if(InpStopMode==STOP_ATR)
   {
      if(atr<=0.0) return false;
      stop_distance=atr*InpStopAtrMultiple+buffer;
   }
   else
   {
      if(atr<=0.0) return false;
      stop_distance=MathMax(range*InpStopRangeMultiple,atr*InpStopAtrMultiple)+buffer;
   }

   double stop_pips=stop_distance/pip;
   if(InpMinimumDynamicStopPips>0.0 && stop_pips<InpMinimumDynamicStopPips)
      stop_distance=InpMinimumDynamicStopPips*pip;
   if(InpMaximumDynamicStopPips>0.0 && stop_distance/pip>InpMaximumDynamicStopPips)
      stop_distance=InpMaximumDynamicStopPips*pip;
   if(stop_distance<=0.0) return false;

   if(InpTargetMode==TARGET_FIXED_PIPS)
      target_distance=InpTargetPips*pip;
   else if(InpTargetMode==TARGET_R_MULTIPLE)
      target_distance=stop_distance*InpTargetRMultiple;
   else if(InpTargetMode==TARGET_OPENING_RANGE)
      target_distance=range*InpTargetRangeMultiple;
   else
   {
      if(atr<=0.0) return false;
      target_distance=atr*InpTargetAtrMultiple;
   }
   return target_distance>0.0;
}

bool GetWindowStats(const datetime from,const datetime until,WindowStats &stats)
{
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M1,from,until-1,rates);
   if(count<=0) return false;
   int first=0,last=0;
   stats.high=-DBL_MAX;
   stats.low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(rates[i].time<rates[first].time) first=i;
      if(rates[i].time>rates[last].time) last=i;
      stats.high=MathMax(stats.high,rates[i].high);
      stats.low=MathMin(stats.low,rates[i].low);
   }
   stats.open=rates[first].open;
   stats.close=rates[last].close;
   stats.bars=count;
   return true;
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

bool HasPendingOrder()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic)
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

void DeletePendingOrders()
{
   trade.SetExpertMagicNumber((ulong)InpMagic);
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic)
         if(!trade.OrderDelete(ticket))
            Print("Sell-stop deletion failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   }
}

void ClosePositions()
{
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         if(!trade.PositionClose(ticket,InpMaxDeviationBrokerPoints))
            Print("Hard-exit close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   }
}

bool TodaySetupWindow(const MqlDateTime &now_ny,WindowStats &prior,WindowStats &setup)
{
   MqlDateTime ny_open=now_ny;
   SetClockFromDecimal(ny_open,InpNewYorkOpenHour);
   datetime open_server=NewYorkToServer(ny_open);
   datetime setup_end=open_server+InpOpeningRangeMinutes*60;
   datetime prior_start=open_server-InpOpeningRangeMinutes*60;
   if(!GetWindowStats(prior_start,open_server,prior) || prior.bars<InpOpeningRangeMinutes-2) return false;
   if(!GetWindowStats(open_server,setup_end,setup) || setup.bars<InpOpeningRangeMinutes-2) return false;
   return true;
}

void ManageOpenPosition()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   double initial_risk=InpStopPips*PipSize();
   double target_distance=InpTargetPips*PipSize();
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=point;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)!=POSITION_TYPE_SELL) continue;
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      double move=entry-tick.bid;
      double desired=current_sl;
      bool change=false;
      if(InpBreakEvenAtR>0.0 && move>=initial_risk*InpBreakEvenAtR && (current_sl==0.0 || entry<current_sl-tick_size/2.0))
      {
         desired=entry;
         change=true;
      }
      if(InpUseDynamic5020 && move>=target_distance*0.50)
      {
         double lock=entry-target_distance*0.20;
         if(current_sl==0.0 || lock<desired-tick_size/2.0) { desired=lock; change=true; }
      }
      if(InpTrailStartAtR>0.0 && move>=initial_risk*InpTrailStartAtR)
      {
         double trail=tick.bid+initial_risk*InpTrailDistanceR;
         if(current_sl==0.0 || trail<desired-tick_size/2.0) { desired=trail; change=true; }
      }
      desired=PriceToTick(desired,1);
      if(change && desired>=tick.ask+minimum_distance && (current_sl==0.0 || desired<current_sl-tick_size/2.0))
      {
         trade.SetExpertMagicNumber((ulong)InpMagic);
         if(!trade.PositionModify(ticket,desired,tp))
            Print("Position management failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      }
   }
}

void ManageTimeAndInvalidation()
{
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(TimeCurrent()),now_ny);
   int minute=now_ny.hour*60+now_ny.min;
   int setup_end=NyMinute(InpNewYorkOpenHour)+InpOpeningRangeMinutes;
   if(minute>=NyMinute(InpHardExitNyHour))
   {
      DeletePendingOrders();
      ClosePositions();
      return;
   }
   if(minute>=setup_end+InpEntryWindowMinutes) DeletePendingOrders();
   if(InpCancelIfSetupHighBreaks && HasPendingOrder())
   {
      WindowStats prior,setup;
      MqlTick tick;
      if(TodaySetupWindow(now_ny,prior,setup) && SymbolInfoTick(_Symbol,tick) && tick.ask>=setup.high)
         DeletePendingOrders();
   }
   if(HasPosition()) ManageOpenPosition();
}

bool PlaceSellStop(const double requested_entry,const MqlDateTime &now_ny,const WindowStats &setup)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !SpreadOK()) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   double entry=PriceToTick(requested_entry,-1);
   if(tick.bid-entry<minimum_distance) return false;
   double stop_distance=0.0,target_distance=0.0;
   if(!CalculateExitDistances(entry,setup,stop_distance,target_distance)) return false;
   double stop=PriceToTick(entry+stop_distance,1);
   double target=PriceToTick(entry-target_distance,-1);
   double lots=LotsForRisk(entry,stop);
   if(lots<=0.0) return false;
   MqlDateTime expiry_ny=now_ny;
   int expiry_minutes=NyMinute(InpNewYorkOpenHour)+InpOpeningRangeMinutes+InpEntryWindowMinutes;
   expiry_ny.hour=expiry_minutes/60; expiry_ny.min=expiry_minutes%60; expiry_ny.sec=0;
   datetime expiry=NewYorkToServer(expiry_ny);
   if(expiry<=TimeCurrent()) return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   bool ok=trade.SellStop(lots,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expiry,"Sell Nasdaq dynamic exit research");
   if(!ok) Print("Sell stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return ok;
}

void EvaluateSetup()
{
   if(!InpEnableTrading || HasPosition() || HasPendingOrder()) return;
   datetime now_server=TimeCurrent();
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(!DayAllowed(now_ny.day_of_week)) return;
   int minute=now_ny.hour*60+now_ny.min;
   int setup_end=NyMinute(InpNewYorkOpenHour)+InpOpeningRangeMinutes;
   if(minute<setup_end || minute>=setup_end+InpEntryWindowMinutes || AttemptedToday(now_ny)) return;

   WindowStats prior,setup;
   if(!TodaySetupWindow(now_ny,prior,setup)) return;
   if(setup.close>=setup.open) return;
   if(InpRequirePriorLondonBearish && prior.close>=prior.open) return;
   if(!HAMA_SafeRegimeAllowsDirection(-1)) return;
   double range=setup.high-setup.low;
   if(range<=0.0) return;
   double body=(setup.open-setup.close)/range;
   if(body+1e-9<InpMinimumBodyFraction) return;
   double range_pips=range/PipSize();
   if(InpMinimumSetupRangePips>0.0 && range_pips<InpMinimumSetupRangePips) return;
   if(InpMaximumSetupRangePips>0.0 && range_pips>InpMaximumSetupRangePips) return;
   PlaceSellStop(setup.low-InpEntryBufferPips*PipSize(),now_ny,setup);
}

int OnInit()
{
   if(InpOpeningRangeMinutes<=0 || InpEntryWindowMinutes<=0 || InpRiskPercent<=0.0 || InpRiskPercent>100.0 ||
      InpStopPips<=0.0 || InpTargetPips<=0.0 || InpStopRangeMultiple<=0.0 || InpAtrPeriod<2 ||
      InpStopAtrMultiple<=0.0 || InpDynamicStopBufferPips<0.0 || InpMinimumDynamicStopPips<0.0 ||
      InpMaximumDynamicStopPips<0.0 || (InpMaximumDynamicStopPips>0.0 && InpMaximumDynamicStopPips<=InpMinimumDynamicStopPips) ||
      InpTargetRMultiple<=0.0 || InpTargetRangeMultiple<=0.0 || InpTargetAtrMultiple<=0.0 || InpEntryBufferPips<0.0 ||
      InpMinimumBodyFraction<0.0 || InpMinimumBodyFraction>1.0 ||
      InpMinimumSetupRangePips<0.0 || InpMaximumSetupRangePips<0.0 ||
      (InpMaximumSetupRangePips>0.0 && InpMaximumSetupRangePips<=InpMinimumSetupRangePips) ||
      InpTrailDistanceR<=0.0 || InpMagic<=0 ||
      (!InpTradeMonday && !InpTradeTuesday && !InpTradeWednesday && !InpTradeThursday && !InpTradeFriday))
      return INIT_PARAMETERS_INCORRECT;
   if((InpStopMode!=STOP_FIXED_PIPS || InpTargetMode!=TARGET_FIXED_PIPS) &&
      (InpBreakEvenAtR>0.0 || InpTrailStartAtR>0.0 || InpUseDynamic5020))
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M15,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(!InpEnableTrading) Print("Research gate is OFF. Load an approved SET deliberately.");
   Print("Sell Nasdaq 15min: ",DoubleToString(InpStopPips,0)," pip stop = ",
         DoubleToString(InpStopPips*PipSize(),2)," price units; ",DoubleToString(InpTargetPips,0),
         " pip target = ",DoubleToString(InpTargetPips*PipSize(),2)," price units.");
   g_last_minute_bar=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManageTimeAndInvalidation();
   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current>0 && current!=g_last_minute_bar)
   {
      g_last_minute_bar=current;
      EvaluateSetup();
   }
}
