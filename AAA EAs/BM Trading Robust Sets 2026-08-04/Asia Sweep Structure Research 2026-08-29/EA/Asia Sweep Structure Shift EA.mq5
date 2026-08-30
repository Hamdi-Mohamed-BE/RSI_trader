#property copyright "Transparent research implementation of the supplied Asia sweep rules"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_SWEEP_STATE
{
   SWEEP_IDLE=0,
   SWEEP_HIGH_WAIT_BEAR_BOS=1,
   SWEEP_LOW_WAIT_BULL_BOS=2
};

input group "Signal and session"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int InpATRPeriod=14;
input int InpAsiaStartHourNY=20;
input int InpAsiaEndHourNY=0;
input int InpEntryStartHourNY=0;
input int InpEntryEndHourNY=5;
input int InpServerUTCOffsetHours=0;
input int InpMinimumAsiaBars=24;
input double InpMinimumAsiaRangeATR=1.00;
input double InpMaximumAsiaRangeATR=8.00;

input group "Sweep and structure shift"
input double InpMinimumSweepATR=0.03;
input int InpMaximumBarsAfterSweep=12;
input int InpStructureLookbackBars=12;
input int InpSwingStrength=1;
input double InpBOSBufferATR=0.00;
input bool InpRequireReclaimClose=true;
input bool InpRequireDirectionalBOSCandle=true;
input double InpMinimumMidpointR=0.00;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input bool InpOneTradePerDay=true;

input group "Risk and exits"
input double InpRiskPercent=1.00;
input double InpStopBufferATR=0.05;
input double InpRewardRisk=1.50;
input bool InpMoveToBreakEven=false;
input double InpBreakEvenAtR=1.00;
input bool InpCloseAtNewYorkHour=true;
input int InpForcedCloseHourNY=12;
input double InpMaximumSpreadATR=0.08;
input int InpMaximumDeviationPoints=30;
input long InpMagic=862930;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar=0;

long g_trading_day=0;
double g_asia_high=0.0;
double g_asia_low=0.0;
int g_asia_bars=0;
bool g_asia_ready=false;
bool g_traded_today=false;

ENUM_SWEEP_STATE g_state=SWEEP_IDLE;
datetime g_sweep_time=0;
double g_sweep_extreme=0.0;
double g_structure_level=0.0;
double g_initial_risk=0.0;

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first={0};
   first.year=year;
   first.mon=month;
   first.day=1;
   MqlDateTime converted={0};
   TimeToStruct(StructToTime(first),converted);
   int first_sunday=1+((7-converted.day_of_week)%7);
   return first_sunday+7*(nth-1);
}

bool IsNewYorkDST(const datetime utc_time)
{
   MqlDateTime value={0};
   TimeToStruct(utc_time,value);
   if(value.mon>3 && value.mon<11) return true;
   if(value.mon<3 || value.mon>11) return false;
   if(value.mon==3)
   {
      int start_day=NthSunday(value.year,3,2);
      if(value.day>start_day) return true;
      if(value.day<start_day) return false;
      return value.hour>=7;
   }
   int end_day=NthSunday(value.year,11,1);
   if(value.day<end_day) return true;
   if(value.day>end_day) return false;
   return value.hour<6;
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-InpServerUTCOffsetHours*3600;
   return utc_time+(IsNewYorkDST(utc_time) ? -4*3600 : -5*3600);
}

long NewYorkDayKey(const datetime server_time)
{
   MqlDateTime value={0};
   TimeToStruct(ServerToNewYork(server_time),value);
   return (long)value.year*10000+(long)value.mon*100+(long)value.day;
}

int NewYorkMinute(const datetime server_time)
{
   MqlDateTime value={0};
   TimeToStruct(ServerToNewYork(server_time),value);
   return value.hour*60+value.min;
}

int NewYorkWeekday(const datetime server_time)
{
   MqlDateTime value={0};
   TimeToStruct(ServerToNewYork(server_time),value);
   return value.day_of_week;
}

bool HourWindowContains(const int minute_of_day,const int start_hour,const int end_hour)
{
   int start=start_hour*60;
   int end=end_hour*60;
   if(start==end) return true;
   if(start<end) return minute_of_day>=start && minute_of_day<end;
   return minute_of_day>=start || minute_of_day<end;
}

long TradingDayForBar(const datetime server_time)
{
   datetime ny=ServerToNewYork(server_time);
   MqlDateTime value={0};
   TimeToStruct(ny,value);
   if(InpAsiaStartHourNY>InpAsiaEndHourNY && value.hour>=InpAsiaStartHourNY)
      ny+=86400;
   TimeToStruct(ny,value);
   return (long)value.year*10000+(long)value.mon*100+(long)value.day;
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw_lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor(raw_lots/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   if(risk_cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   return NormalizeLots(risk_cash/one_lot);
}

bool IsOurSelectedPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool HasOurPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
      if(PositionGetTicket(index)>0 && IsOurSelectedPosition()) return true;
   return false;
}

bool ReadATR(const int shift,double &value)
{
   double values[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,values)!=1) return false;
   value=values[0];
   return value>0.0;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

void ClearSweep()
{
   g_state=SWEEP_IDLE;
   g_sweep_time=0;
   g_sweep_extreme=0.0;
   g_structure_level=0.0;
}

void ResetTradingDay(const long day_key)
{
   g_trading_day=day_key;
   g_asia_high=0.0;
   g_asia_low=0.0;
   g_asia_bars=0;
   g_asia_ready=false;
   g_traded_today=false;
   ClearSweep();
}

int BarsElapsed(const datetime older,const datetime newer)
{
   int seconds=PeriodSeconds(InpSignalTimeframe);
   if(seconds<=0 || newer<=older) return 0;
   return (int)((newer-older)/seconds);
}

double RecentStructureLow(const MqlRates &rates[])
{
   int available=ArraySize(rates);
   int maximum=MathMin(InpStructureLookbackBars+2,available-InpSwingStrength-1);
   for(int index=2+InpSwingStrength;index<=maximum;index++)
   {
      bool swing=true;
      for(int offset=1;offset<=InpSwingStrength;offset++)
         if(rates[index].low>=rates[index-offset].low || rates[index].low>rates[index+offset].low) swing=false;
      if(swing) return rates[index].low;
   }
   double level=DBL_MAX;
   for(int index=2;index<=MathMin(InpStructureLookbackBars+1,available-1);index++)
      level=MathMin(level,rates[index].low);
   return level;
}

double RecentStructureHigh(const MqlRates &rates[])
{
   int available=ArraySize(rates);
   int maximum=MathMin(InpStructureLookbackBars+2,available-InpSwingStrength-1);
   for(int index=2+InpSwingStrength;index<=maximum;index++)
   {
      bool swing=true;
      for(int offset=1;offset<=InpSwingStrength;offset++)
         if(rates[index].high<=rates[index-offset].high || rates[index].high<rates[index+offset].high) swing=false;
      if(swing) return rates[index].high;
   }
   double level=-DBL_MAX;
   for(int index=2;index<=MathMin(InpStructureLookbackBars+1,available-1);index++)
      level=MathMax(level,rates[index].high);
   return level;
}

bool MidpointPasses(const int direction,const double entry,const double stop) 
{
   if(InpMinimumMidpointR<=0.0) return true;
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double midpoint=(g_asia_high+g_asia_low)*0.5;
   double distance=(direction>0 ? midpoint-entry : entry-midpoint);
   return distance/risk>=InpMinimumMidpointR;
}

bool PlaceTrade(const int direction,const double atr)
{
   if(HasOurPosition() || g_traded_today || !SpreadPasses(atr)) return false;
   if(direction>0 && !InpAllowLong) return false;
   if(direction<0 && !InpAllowShort) return false;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? g_sweep_extreme-InpStopBufferATR*atr : g_sweep_extreme+InpStopBufferATR*atr);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=entry-broker_gap;
   if(direction<0 && stop-entry<broker_gap) stop=entry+broker_gap;
   if(!MidpointPasses(direction,entry,stop)) return false;
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target=(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   stop=NormalizePrice(stop);
   target=NormalizePrice(target);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("Asia sweep skipped: broker minimum volume exceeds calculated risk.");
      return false;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"Asia low sweep BOS")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"Asia high sweep BOS"));
   if(!sent)
   {
      Print("Asia sweep order rejected: ",g_trade.ResultRetcodeDescription());
      return false;
   }
   g_initial_risk=risk;
   g_traded_today=true;
   ClearSweep();
   return true;
}

void ManagePosition()
{
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool found=false;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !IsOurSelectedPosition()) continue;
      found=true;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double current=(buy ? tick.bid : tick.ask);
      if(g_initial_risk<=0.0) g_initial_risk=MathAbs(open-stop);
      if(InpMoveToBreakEven && g_initial_risk>0.0)
      {
         double favorable=(buy ? current-open : open-current);
         if(favorable>=InpBreakEvenAtR*g_initial_risk)
         {
            double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
            double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                               (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
            bool valid=(buy ? open>stop && open<current-gap : (stop<=0.0 || open<stop) && open>current+gap);
            if(valid) g_trade.PositionModify(ticket,NormalizePrice(open),target);
         }
      }
      if(InpCloseAtNewYorkHour && NewYorkMinute(TimeCurrent())>=InpForcedCloseHourNY*60)
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
   if(!found) g_initial_risk=0.0;
}

void ProcessClosedBar()
{
   int required=InpStructureLookbackBars+InpSwingStrength+8;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required,rates)<required) return;
   const MqlRates bar=rates[1];
   int weekday=NewYorkWeekday(bar.time);
   int minute_of_day=NewYorkMinute(bar.time);
   long day_key=TradingDayForBar(bar.time);
   bool in_asia=HourWindowContains(minute_of_day,InpAsiaStartHourNY,InpAsiaEndHourNY);
   bool in_entry=HourWindowContains(minute_of_day,InpEntryStartHourNY,InpEntryEndHourNY);

   if(in_asia)
   {
      // Sunday evening New York is Monday's live Asia range. Saturday is closed.
      if(weekday==6) return;
      if(day_key!=g_trading_day) ResetTradingDay(day_key);
      if(g_asia_bars==0)
      {
         g_asia_high=bar.high;
         g_asia_low=bar.low;
      }
      else
      {
         g_asia_high=MathMax(g_asia_high,bar.high);
         g_asia_low=MathMin(g_asia_low,bar.low);
      }
      g_asia_bars++;
      return;
   }

   if(weekday==0 || weekday==6) return;

   if(day_key!=g_trading_day) return;
   double atr=0.0;
   if(!ReadATR(1,atr)) return;
   if(!g_asia_ready && minute_of_day>=InpAsiaEndHourNY*60)
   {
      double range=g_asia_high-g_asia_low;
      g_asia_ready=(g_asia_bars>=InpMinimumAsiaBars && range>=InpMinimumAsiaRangeATR*atr && range<=InpMaximumAsiaRangeATR*atr);
   }
   if(!g_asia_ready || !in_entry || (InpOneTradePerDay && g_traded_today)) return;

   int age=(g_sweep_time>0 ? BarsElapsed(g_sweep_time,bar.time) : 0);
   if(g_state!=SWEEP_IDLE && age>InpMaximumBarsAfterSweep)
      ClearSweep();

   if(g_state==SWEEP_HIGH_WAIT_BEAR_BOS)
   {
      g_sweep_extreme=MathMax(g_sweep_extreme,bar.high);
      if(InpRequireReclaimClose && bar.close>g_asia_high)
      {
         ClearSweep();
         return;
      }
      bool directional=(!InpRequireDirectionalBOSCandle || bar.close<bar.open);
      if(age>=1 && directional && bar.close<g_structure_level-InpBOSBufferATR*atr)
         PlaceTrade(-1,atr);
      return;
   }
   if(g_state==SWEEP_LOW_WAIT_BULL_BOS)
   {
      g_sweep_extreme=MathMin(g_sweep_extreme,bar.low);
      if(InpRequireReclaimClose && bar.close<g_asia_low)
      {
         ClearSweep();
         return;
      }
      bool directional=(!InpRequireDirectionalBOSCandle || bar.close>bar.open);
      if(age>=1 && directional && bar.close>g_structure_level+InpBOSBufferATR*atr)
         PlaceTrade(1,atr);
      return;
   }

   bool high_sweep=bar.high>g_asia_high+InpMinimumSweepATR*atr && (!InpRequireReclaimClose || bar.close<g_asia_high);
   bool low_sweep=bar.low<g_asia_low-InpMinimumSweepATR*atr && (!InpRequireReclaimClose || bar.close>g_asia_low);
   if(high_sweep && low_sweep) return;
   if(high_sweep && InpAllowShort)
   {
      g_state=SWEEP_HIGH_WAIT_BEAR_BOS;
      g_sweep_time=bar.time;
      g_sweep_extreme=bar.high;
      g_structure_level=RecentStructureLow(rates);
      return;
   }
   if(low_sweep && InpAllowLong)
   {
      g_state=SWEEP_LOW_WAIT_BULL_BOS;
      g_sweep_time=bar.time;
      g_sweep_extreme=bar.low;
      g_structure_level=RecentStructureHigh(rates);
   }
}

int OnInit()
{
   if(InpATRPeriod<2 || InpAsiaStartHourNY<0 || InpAsiaStartHourNY>23 ||
      InpAsiaEndHourNY<0 || InpAsiaEndHourNY>23 || InpEntryStartHourNY<0 ||
      InpEntryStartHourNY>23 || InpEntryEndHourNY<0 || InpEntryEndHourNY>23 ||
      InpMinimumAsiaBars<1 || InpMinimumAsiaRangeATR<=0.0 ||
      InpMaximumAsiaRangeATR<=InpMinimumAsiaRangeATR || InpMaximumBarsAfterSweep<1 ||
      InpStructureLookbackBars<4 || InpSwingStrength<1 || InpRiskPercent<=0.0 ||
      InpRewardRisk<=0.0 || InpBreakEvenAtR<=0.0 || InpMaximumSpreadATR<0.0)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   ResetTradingDay(0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   ProcessClosedBar();
}
