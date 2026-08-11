#property copyright "Research implementation of the US100 Asia-London continuation rule"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_TESTER_SERVER_CLOCK
{
   TESTER_CLOCK_UTC=0,
   TESTER_CLOCK_EET_EEST=1,
   TESTER_CLOCK_MANUAL=2
};

input group "Research gate"
input bool   InpEnableTrading=false; // Keep false until the supplied test preset is deliberately loaded

input group "Signal (America/New_York clock)"
input double InpAsiaNyStartHour=18.0;       // Previous New York calendar day
input double InpAsiaNyEndHour=3.0;
input double InpLondonNyStartHour=3.0;
input double InpNewYorkOpenHour=9.5;        // 09:30
input int    InpOpeningRangeMinutes=15;
input double InpExtremeProximityPoints=20.0; // 20.00 index points = 2,000 ticks when tick size is 0.01
input double InpMaximumOpeningRangePoints=400.0;
input bool   InpTradeLongs=true;
input bool   InpTradeShorts=true;

input group "Tested execution"
input double InpRiskPercent=1.0;
input double InpStopOpeningRangeMultiple=1.25;
input double InpMinimumStopPoints=20.0;
input double InpRewardRisk=2.0;
input double InpLastEntryNyHour=10.5;       // 10:30
input double InpHardExitNyHour=16.0;
input int    InpMaxSpreadBrokerPoints=0;    // 0 = no extra filter; research used each broker's recorded spread
input int    InpMaxDeviationBrokerPoints=30;

input group "Identity"
input long   InpMagic=84102001;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input ENUM_TESTER_SERVER_CLOCK InpTesterServerClock=TESTER_CLOCK_UTC; // Exness USTEC history is UTC
input int    InpTesterManualUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_minute_bar=0;

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
   int offset=EuropeUTCOffsetHours(utc_standard);
   return server_time-offset*3600;
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

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

MqlDateTime PreviousCalendarDay(const MqlDateTime &source)
{
   MqlDateTime result=source;
   result.hour=12; result.min=0; result.sec=0;
   datetime value=StructToTime(result)-86400;
   TimeToStruct(value,result);
   return result;
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

double LotsForRisk(const ENUM_ORDER_TYPE side,const double entry,const double stop)
{
   double one_lot=0.0;
   if(!OrderCalcProfit(side,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   double loss=MathAbs(one_lot);
   if(loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/loss);
}

bool SpreadOK()
{
   if(InpMaxSpreadBrokerPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadBrokerPoints;
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

bool HasPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   return false;
}

bool HasPendingOrder()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic) return true;
   }
   return false;
}

bool HasExposure()
{
   return HasPosition() || HasPendingOrder();
}

bool AttemptedToday(const MqlDateTime &now_ny)
{
   MqlDateTime start=now_ny;
   start.hour=0; start.min=0; start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent())) return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket==0) continue;
      if(HistoryOrderGetString(ticket,ORDER_SYMBOL)==_Symbol && HistoryOrderGetInteger(ticket,ORDER_MAGIC)==InpMagic)
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
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic)
      {
         if(!trade.OrderDelete(ticket))
            Print("Pending-order deletion failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      }
   }
}

void ClosePositions()
{
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         if(!trade.PositionClose(ticket,InpMaxDeviationBrokerPoints))
            Print("Hard-exit close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      }
   }
}

void ManageTimeLimits()
{
   if(!HasExposure()) return;
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(TimeCurrent()),now_ny);
   int minute=now_ny.hour*60+now_ny.min;
   if(minute>=NyMinute(InpHardExitNyHour))
   {
      DeletePendingOrders();
      ClosePositions();
      return;
   }
   if(minute>=NyMinute(InpLastEntryNyHour)) DeletePendingOrders();
}

bool SendEntry(const int direction,const double requested_entry,const double stop_distance,const MqlDateTime &now_ny)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !SpreadOK()) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationBrokerPoints);

   MqlDateTime expiry_ny=now_ny;
   SetClockFromDecimal(expiry_ny,InpLastEntryNyHour);
   datetime expiry=NewYorkToServer(expiry_ny);
   if(expiry<=TimeCurrent()) return false;

   if(direction>0)
   {
      bool market=(tick.ask>=requested_entry);
      double entry=PriceToTick(market ? tick.ask : requested_entry,market ? 0 : 1);
      double stop=PriceToTick(entry-stop_distance,-1);
      double target=PriceToTick(entry+InpRewardRisk*stop_distance,1);
      double lots=LotsForRisk(ORDER_TYPE_BUY,entry,stop);
      if(lots<=0.0) return false;
      bool ok=false;
      if(market)
         ok=trade.Buy(lots,_Symbol,0.0,stop,target,"US100 Asia-London LONG");
      else if(entry-tick.ask>=minimum_distance)
         ok=trade.BuyStop(lots,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expiry,"US100 Asia-London LONG");
      else
         return false;
      if(!ok) Print("Long entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return ok;
   }

   bool market=(tick.bid<=requested_entry);
   double entry=PriceToTick(market ? tick.bid : requested_entry,market ? 0 : -1);
   double stop=PriceToTick(entry+stop_distance,1);
   double target=PriceToTick(entry-InpRewardRisk*stop_distance,-1);
   double lots=LotsForRisk(ORDER_TYPE_SELL,entry,stop);
   if(lots<=0.0) return false;
   bool ok=false;
   if(market)
      ok=trade.Sell(lots,_Symbol,0.0,stop,target,"US100 Asia-London SHORT");
   else if(tick.bid-entry>=minimum_distance)
      ok=trade.SellStop(lots,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expiry,"US100 Asia-London SHORT");
   else
      return false;
   if(!ok) Print("Short entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   return ok;
}

void EvaluateSetup()
{
   if(!InpEnableTrading || HasExposure()) return;
   datetime now_server=TimeCurrent();
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   int minute=now_ny.hour*60+now_ny.min;
   int or_end=NyMinute(InpNewYorkOpenHour)+InpOpeningRangeMinutes;
   if(minute<or_end || minute>=NyMinute(InpLastEntryNyHour) || AttemptedToday(now_ny)) return;

   MqlDateTime previous=PreviousCalendarDay(now_ny);
   MqlDateTime asia_start_ny=previous;
   SetClockFromDecimal(asia_start_ny,InpAsiaNyStartHour);
   MqlDateTime asia_end_ny=now_ny;
   SetClockFromDecimal(asia_end_ny,InpAsiaNyEndHour);
   MqlDateTime london_start_ny=now_ny;
   SetClockFromDecimal(london_start_ny,InpLondonNyStartHour);
   MqlDateTime ny_open_ny=now_ny;
   SetClockFromDecimal(ny_open_ny,InpNewYorkOpenHour);
   MqlDateTime or_end_ny=ny_open_ny;
   datetime or_end_server=NewYorkToServer(ny_open_ny)+InpOpeningRangeMinutes*60;

   WindowStats asia,london,opening_range;
   if(!GetWindowStats(NewYorkToServer(asia_start_ny),NewYorkToServer(asia_end_ny),asia) || asia.bars<180) return;
   if(!GetWindowStats(NewYorkToServer(london_start_ny),NewYorkToServer(ny_open_ny),london) || london.bars<180) return;
   if(!GetWindowStats(NewYorkToServer(ny_open_ny),or_end_server,opening_range) || opening_range.bars<12) return;

   double asia_move=asia.close-asia.open;
   double london_move=london.close-london.open;
   int direction=0;
   if(asia_move>0.0 && london_move>0.0) direction=1;
   else if(asia_move<0.0 && london_move<0.0) direction=-1;
   else return;
   if((direction>0 && !InpTradeLongs) || (direction<0 && !InpTradeShorts)) return;

   double opening_range_size=opening_range.high-opening_range.low;
   if(opening_range_size<=0.0 || opening_range_size>InpMaximumOpeningRangePoints) return;
   double proximity=(direction>0 ? MathAbs(opening_range.high-asia.high) : MathAbs(opening_range.low-asia.low));
   if(proximity>InpExtremeProximityPoints) return;

   double stop_distance=MathMax(opening_range_size*InpStopOpeningRangeMultiple,InpMinimumStopPoints);
   double requested_entry=(direction>0 ? opening_range.high : opening_range.low);
   SendEntry(direction,requested_entry,stop_distance,now_ny);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpExtremeProximityPoints<=0.0 ||
      InpMaximumOpeningRangePoints<=0.0 || InpOpeningRangeMinutes<=0 ||
      InpStopOpeningRangeMultiple<=0.0 || InpMinimumStopPoints<=0.0 || InpRewardRisk<=0.0 ||
      InpLastEntryNyHour<=InpNewYorkOpenHour || InpHardExitNyHour<=InpLastEntryNyHour ||
      InpMagic<=0 || (!InpTradeLongs && !InpTradeShorts))
      return INIT_PARAMETERS_INCORRECT;

   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick>0.0)
      Print("Signal threshold = ",DoubleToString(InpExtremeProximityPoints,2)," index points = ",
            DoubleToString(InpExtremeProximityPoints/tick,0)," broker ticks at tick size ",DoubleToString(tick,8),".");
   if(!InpEnableTrading) Print("Research gate is OFF. Load the BEST TEST preset or enable trading deliberately.");
   g_last_minute_bar=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   ManageTimeLimits();
   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current>0 && current!=g_last_minute_bar)
   {
      g_last_minute_bar=current;
      EvaluateSetup();
   }
}
