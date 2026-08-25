#property copyright "US100 selective opening-range research build"
#property version   "1.10"
#property strict

#include <Trade/Trade.mqh>

input group "New York opening range"
input int             InpOpeningRangeMinutes=30;
input int             InpEntryCutoffHour=11;
input int             InpEntryCutoffMinute=30;
input int             InpFlatHour=15;
input int             InpFlatMinute=55;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;

input group "Range and activity regime"
input int             InpBaselineDays=20;
input double          InpMinimumOpeningRelativeVolume=0.80;
input double          InpMinimumRangeDailyATR=0.05;
input double          InpMaximumRangeDailyATR=0.35;
input double          InpMinimumBreakoutRelativeVolume=0.80;
input double          InpBreakoutBodyMinimum=0.55;
input double          InpBreakoutBufferDailyATR=0.015;
input bool            InpRequireSessionVWAP=true;

input group "Breakout and retest"
input int             InpTradeDirection=0; // 0=both, 1=long only, 2=short only
input bool            InpUseTimeDirectionFilter=false;
input int             InpLongOnlyStartHour=10;
input int             InpLongOnlyStartMinute=30;
input int             InpShortOnlyStartHour=11;
input int             InpShortOnlyStartMinute=0;
input int             InpMaximumRetestBars=3;
input double          InpRetestToleranceRange=0.12;
input double          InpMaximumPreRetestExcursionRange=0.60;

input group "Risk and exits"
input double          InpRiskPercent=1.00;
input double          InpFixedRiskMoney=0.00; // >0 overrides percent risk
input double          InpStopBufferRange=0.05;
input double          InpMaximumStopDailyATR=0.80;
input double          InpRewardRisk=2.00;
input double          InpBreakEvenAtR=1.00;
input double          InpMaximumSpreadRangePercent=10.0;
input int             InpMaximumDeviationPoints=50;
input long            InpMagic=86260821;
input bool            InpOptimizeForWinRate=false;

input group "Broker clock"
input bool            InpUseAutomaticLiveServerOffset=true;
input int             InpTesterServerUTCOffsetHours=0;
input int             InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_signal_bar=0;
int g_session_key=0;
bool g_range_attempted=false;
bool g_range_ready=false;
bool g_traded_today=false;
double g_range_high=0.0;
double g_range_low=0.0;
double g_range_width=0.0;
double g_daily_atr=0.0;
double g_opening_relative_volume=0.0;
int g_breakout_direction=0;
int g_breakout_age=0;
double g_initial_risk=0.0;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime value={0};
   value.year=year; value.mon=month; value.day=1; value.hour=12;
   datetime first=StructToTime(value);
   TimeToStruct(first,value);
   return 1+((7-value.day_of_week)%7)+(occurrence-1)*7;
}

int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime value; TimeToStruct(utc_time,value);
   MqlDateTime start={0},finish={0};
   start.year=value.year; start.mon=3; start.day=NthSunday(value.year,3,2); start.hour=7;
   finish.year=value.year; finish.mon=11; finish.day=NthSunday(value.year,11,1); finish.hour=6;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? -4 : -5);
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march=NthSunday(ny.year,3,2);
   int november=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march;
   return ny.day<november;
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

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc=server_time-ServerUTCOffsetSeconds();
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

datetime NewYorkToServer(const MqlDateTime &ny)
{
   MqlDateTime local=ny;
   datetime local_time=StructToTime(local);
   int offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   return local_time-offset*3600+ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &value)
{
   return value.year*10000+value.mon*100+value.day;
}

void PreviousCalendarDay(MqlDateTime &value)
{
   value.hour=12; value.min=0; value.sec=0;
   datetime prior=StructToTime(value)-86400;
   TimeToStruct(prior,value);
}

datetime SessionTime(const MqlDateTime &date,const int hour,const int minute)
{
   MqlDateTime value=date;
   value.hour=hour; value.min=minute; value.sec=0;
   return NewYorkToServer(value);
}

double Median(double &values[])
{
   int count=ArraySize(values);
   if(count<=0) return 0.0;
   ArraySort(values);
   if((count%2)==1) return values[count/2];
   return (values[count/2-1]+values[count/2])*0.5;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return raw;
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw)
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
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   double cash=(InpFixedRiskMoney>0.0 ? InpFixedRiskMoney : AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0);
   if(cash<=0.0) return 0.0;
   return NormalizeLots(cash/one_lot);
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong candidate=PositionGetTicket(index);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool TradedOnDate(const MqlDateTime &ny_date)
{
   MqlDateTime start=ny_date,finish=ny_date;
   start.hour=0; start.min=0; start.sec=0;
   finish.hour=23; finish.min=59; finish.sec=59;
   if(!HistorySelect(NewYorkToServer(start),NewYorkToServer(finish))) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      ulong ticket=HistoryDealGetTicket(index);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(ticket,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN)
         return true;
   }
   return false;
}

bool RTHStats(const MqlDateTime &ny_date,double &high,double &low,double &close)
{
   datetime from=SessionTime(ny_date,9,30);
   datetime through=SessionTime(ny_date,15,59)+59;
   MqlRates rates[];
   int copied=CopyRates(_Symbol,PERIOD_M5,from,through,rates);
   if(copied<60) return false;
   high=-DBL_MAX; low=DBL_MAX; close=rates[copied-1].close;
   for(int index=0;index<copied;index++)
   {
      high=MathMax(high,rates[index].high);
      low=MathMin(low,rates[index].low);
   }
   return high>low && close>0.0;
}

bool PreviousRTHClose(MqlDateTime &from_date,double &close)
{
   int attempts=0;
   while(attempts<12)
   {
      PreviousCalendarDay(from_date);
      attempts++;
      if(from_date.day_of_week==0 || from_date.day_of_week==6) continue;
      double high=0.0,low=0.0;
      if(RTHStats(from_date,high,low,close)) return true;
   }
   return false;
}

double HistoricalDailyATR(const MqlDateTime &current_date)
{
   double samples[];
   int found=0,attempts=0;
   MqlDateTime candidate=current_date;
   while(found<InpBaselineDays && attempts<InpBaselineDays*3+20)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(candidate.day_of_week==0 || candidate.day_of_week==6) continue;
      double high=0.0,low=0.0,close=0.0;
      if(!RTHStats(candidate,high,low,close)) continue;
      double previous_close=0.0;
      MqlDateTime lookup=candidate;
      if(!PreviousRTHClose(lookup,previous_close)) continue;
      double true_range=MathMax(high-low,MathMax(MathAbs(high-previous_close),MathAbs(low-previous_close)));
      if(true_range<=0.0) continue;
      ArrayResize(samples,found+1);
      samples[found++]=true_range;
   }
   return Median(samples);
}

double OpeningStats(const MqlDateTime &ny_date,double &high,double &low)
{
   datetime from=SessionTime(ny_date,9,30);
   datetime through=from+InpOpeningRangeMinutes*60-1;
   MqlRates rates[];
   int copied=CopyRates(_Symbol,PERIOD_M1,from,through,rates);
   if(copied<InpOpeningRangeMinutes) return 0.0;
   high=-DBL_MAX; low=DBL_MAX;
   double volume=0.0;
   for(int index=0;index<copied;index++)
   {
      high=MathMax(high,rates[index].high);
      low=MathMin(low,rates[index].low);
      volume+=(double)rates[index].tick_volume;
   }
   return volume;
}

double HistoricalOpeningVolume(const MqlDateTime &current_date)
{
   double samples[];
   int found=0,attempts=0;
   MqlDateTime candidate=current_date;
   while(found<InpBaselineDays && attempts<InpBaselineDays*3+20)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(candidate.day_of_week==0 || candidate.day_of_week==6) continue;
      double high=0.0,low=0.0;
      double volume=OpeningStats(candidate,high,low);
      if(volume<=0.0 || high<=low) continue;
      ArrayResize(samples,found+1);
      samples[found++]=volume;
   }
   return Median(samples);
}

double SameClockRelativeVolume(const MqlRates &signal)
{
   MqlDateTime signal_ny;
   TimeToStruct(ServerToNewYork(signal.time),signal_ny);
   double samples[];
   int found=0,attempts=0;
   MqlDateTime candidate=signal_ny;
   while(found<InpBaselineDays && attempts<InpBaselineDays*3+20)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(candidate.day_of_week==0 || candidate.day_of_week==6) continue;
      datetime from=SessionTime(candidate,signal_ny.hour,signal_ny.min);
      MqlRates bars[];
      int copied=CopyRates(_Symbol,InpSignalTimeframe,from,from+PeriodSeconds(InpSignalTimeframe)-1,bars);
      if(copied!=1 || bars[0].tick_volume<=0) continue;
      ArrayResize(samples,found+1);
      samples[found++]=(double)bars[0].tick_volume;
   }
   double baseline=Median(samples);
   return (baseline>0.0 ? (double)signal.tick_volume/baseline : 0.0);
}

double SessionVWAP(const datetime from,const datetime through)
{
   MqlRates bars[];
   int copied=CopyRates(_Symbol,InpSignalTimeframe,from,through,bars);
   if(copied<=0) return 0.0;
   double weighted=0.0,volume=0.0;
   for(int index=0;index<copied;index++)
   {
      double activity=(double)bars[index].tick_volume;
      double typical=(bars[index].high+bars[index].low+bars[index].close)/3.0;
      weighted+=typical*activity;
      volume+=activity;
   }
   return (volume>0.0 ? weighted/volume : 0.0);
}

double BodyRatio(const MqlRates &bar)
{
   double width=bar.high-bar.low;
   return (width>0.0 ? MathAbs(bar.close-bar.open)/width : 0.0);
}

bool SpreadAcceptable()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || g_range_width<=0.0) return false;
   return (tick.ask-tick.bid)/g_range_width*100.0<=InpMaximumSpreadRangePercent;
}

bool TimeDirectionAllowed(const int direction)
{
   if(!InpUseTimeDirectionFilter) return true;
   MqlDateTime ny_now;
   TimeToStruct(ServerToNewYork(TimeCurrent()),ny_now);
   int now_minutes=ny_now.hour*60+ny_now.min;
   int long_only=InpLongOnlyStartHour*60+InpLongOnlyStartMinute;
   int short_only=InpShortOnlyStartHour*60+InpShortOnlyStartMinute;
   if(now_minutes<long_only) return true;
   if(now_minutes<short_only) return direction>0;
   return direction<0;
}

bool BuildOpeningRange(const MqlDateTime &ny_date)
{
   double volume=OpeningStats(ny_date,g_range_high,g_range_low);
   if(volume<=0.0 || g_range_high<=g_range_low) return false;
   g_range_width=g_range_high-g_range_low;
   g_daily_atr=HistoricalDailyATR(ny_date);
   double volume_baseline=HistoricalOpeningVolume(ny_date);
   if(g_daily_atr<=0.0 || volume_baseline<=0.0) return false;
   g_opening_relative_volume=volume/volume_baseline;
   double normalized_range=g_range_width/g_daily_atr;
   if(normalized_range<InpMinimumRangeDailyATR || normalized_range>InpMaximumRangeDailyATR) return false;
   if(g_opening_relative_volume<InpMinimumOpeningRelativeVolume) return false;
   return true;
}

bool EnterTrade(const int direction)
{
   if(g_traded_today || !SpreadAcceptable()) return false;
   if(!TimeDirectionAllowed(direction)) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? g_range_low-InpStopBufferRange*g_range_width
                             : g_range_high+InpStopBufferRange*g_range_width);
   stop=NormalizePrice(stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || risk>InpMaximumStopDailyATR*g_daily_atr) return false;
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(risk<minimum) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("ORB skipped: broker minimum lot is larger than the requested risk size.");
      return false;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   string note=StringFormat("US100 OR30 RV %.2f",g_opening_relative_volume);
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,note)
                          : trade.Sell(lots,_Symbol,0.0,stop,target,note));
   if(!sent)
   {
      Print("ORB entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_traded_today=true;
   g_initial_risk=risk;
   return true;
}

bool RetestAccepted(const int direction,const MqlRates &bar)
{
   double tolerance=InpRetestToleranceRange*g_range_width;
   if(direction>0)
      return bar.low<=g_range_high+tolerance && bar.close>=g_range_high && bar.close>bar.open;
   return bar.high>=g_range_low-tolerance && bar.close<=g_range_low && bar.close<bar.open;
}

void EvaluateClosedBar(const MqlDateTime &ny_date,const datetime range_start,const datetime range_end)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,bars)!=1) return;
   MqlRates bar=bars[0];
   datetime cutoff=SessionTime(ny_date,InpEntryCutoffHour,InpEntryCutoffMinute);
   if(bar.time<range_end || bar.time>=cutoff) return;

   if(g_breakout_direction!=0)
   {
      g_breakout_age++;
      double excursion=(g_breakout_direction>0 ? bar.high-g_range_high : g_range_low-bar.low);
      if(g_breakout_age>InpMaximumRetestBars || excursion>InpMaximumPreRetestExcursionRange*g_range_width)
      {
         g_breakout_direction=0;
         return;
      }
      if(RetestAccepted(g_breakout_direction,bar))
      {
         int direction=g_breakout_direction;
         g_breakout_direction=0;
         EnterTrade(direction);
      }
      return;
   }

   if(BodyRatio(bar)<InpBreakoutBodyMinimum) return;
   if(SameClockRelativeVolume(bar)<InpMinimumBreakoutRelativeVolume) return;
   double buffer=InpBreakoutBufferDailyATR*g_daily_atr;
   int direction=0;
   if(bar.close>g_range_high+buffer && bar.close>bar.open) direction=1;
   else if(bar.close<g_range_low-buffer && bar.close<bar.open) direction=-1;
   if(direction==0) return;
   if((InpTradeDirection==1 && direction<0) || (InpTradeDirection==2 && direction>0)) return;
   if(InpRequireSessionVWAP)
   {
      double vwap=SessionVWAP(range_start,bar.time+PeriodSeconds(InpSignalTimeframe)-1);
      if(vwap<=0.0 || (direction>0 && bar.close<=vwap) || (direction<0 && bar.close>=vwap)) return;
   }
   g_breakout_direction=direction;
   g_breakout_age=0;
}

void ManagePosition(const MqlDateTime &ny_now,const bool new_signal_bar)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   int now_minutes=ny_now.hour*60+ny_now.min;
   if(now_minutes>=InpFlatHour*60+InpFlatMinute)
   {
      trade.SetExpertMagicNumber((ulong)InpMagic);
      trade.SetTypeFillingBySymbol(_Symbol);
      trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!trade.PositionClose(ticket))
         Print("ORB session close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return;
   }
   if(!new_signal_bar || InpBreakEvenAtR<=0.0) return;
   long type=PositionGetInteger(POSITION_TYPE);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   if(g_initial_risk<=0.0 && current_stop>0.0 && MathAbs(entry-current_stop)>SymbolInfoDouble(_Symbol,SYMBOL_POINT))
      g_initial_risk=MathAbs(entry-current_stop);
   if(g_initial_risk<=0.0 || MathAbs(current_stop-entry)<=SymbolInfoDouble(_Symbol,SYMBOL_POINT)) return;
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,closed)!=1) return;
   double favorable=(type==POSITION_TYPE_BUY ? closed[0].high-entry : entry-closed[0].low);
   if(favorable<InpBreakEvenAtR*g_initial_risk) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if((type==POSITION_TYPE_BUY && entry>=tick.bid-minimum) ||
      (type==POSITION_TYPE_SELL && entry<=tick.ask+minimum)) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(!trade.PositionModify(ticket,NormalizePrice(entry),target))
      Print("ORB break-even update failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ResetSession(const MqlDateTime &ny_date)
{
   g_session_key=DateKey(ny_date);
   g_range_attempted=false;
   g_range_ready=false;
   g_traded_today=TradedOnDate(ny_date);
   g_range_high=0.0; g_range_low=0.0; g_range_width=0.0;
   g_daily_atr=0.0; g_opening_relative_volume=0.0;
   g_breakout_direction=0; g_breakout_age=0; g_initial_risk=0.0;
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime ny_now;
   TimeToStruct(ServerToNewYork(now_server),ny_now);
   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   bool new_bar=(current_bar>0 && current_bar!=g_last_signal_bar);
   if(new_bar) g_last_signal_bar=current_bar;
   if(DateKey(ny_now)!=g_session_key) ResetSession(ny_now);
   ManagePosition(ny_now,new_bar);
   if(!new_bar || g_traded_today || ny_now.day_of_week==0 || ny_now.day_of_week==6) return;
   datetime range_start=SessionTime(ny_now,9,30);
   datetime range_end=range_start+InpOpeningRangeMinutes*60;
   datetime cutoff=SessionTime(ny_now,InpEntryCutoffHour,InpEntryCutoffMinute);
   if(now_server<range_end || now_server>=cutoff) return;
   if(!g_range_attempted)
   {
      g_range_attempted=true;
      g_range_ready=BuildOpeningRange(ny_now);
   }
   if(!g_range_ready) return;
   EvaluateClosedBar(ny_now,range_start,range_end);
}

int OnInit()
{
   if(InpOpeningRangeMinutes<5 || InpOpeningRangeMinutes>120 || InpBaselineDays<10 ||
      InpMinimumOpeningRelativeVolume<=0.0 || InpMinimumRangeDailyATR<=0.0 ||
      InpMaximumRangeDailyATR<=InpMinimumRangeDailyATR || InpMinimumBreakoutRelativeVolume<=0.0 ||
      InpBreakoutBodyMinimum<0.0 || InpBreakoutBodyMinimum>1.0 || InpMaximumRetestBars<1 ||
      InpTradeDirection<0 || InpTradeDirection>2 ||
      InpLongOnlyStartHour<0 || InpLongOnlyStartHour>23 || InpLongOnlyStartMinute<0 || InpLongOnlyStartMinute>59 ||
      InpShortOnlyStartHour<0 || InpShortOnlyStartHour>23 || InpShortOnlyStartMinute<0 || InpShortOnlyStartMinute>59 ||
      InpShortOnlyStartHour*60+InpShortOnlyStartMinute<=InpLongOnlyStartHour*60+InpLongOnlyStartMinute ||
      InpRetestToleranceRange<0.0 || InpMaximumPreRetestExcursionRange<=0.0 ||
       InpFixedRiskMoney<0.0 || (InpFixedRiskMoney<=0.0 && (InpRiskPercent<=0.0 || InpRiskPercent>3.0)) || InpStopBufferRange<0.0 ||
      InpMaximumStopDailyATR<=0.0 || InpRewardRisk<=0.0 || InpMaximumSpreadRangePercent<=0.0)
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   EventSetTimer(10);
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

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double profit=TesterStatistics(STAT_PROFIT);
   double factor=TesterStatistics(STAT_PROFIT_FACTOR);
   double drawdown=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double wins=TesterStatistics(STAT_PROFIT_TRADES);
   double win_rate=(trades>0.0 ? 100.0*wins/trades : 0.0);
   if(InpOptimizeForWinRate)
   {
      if(trades<24.0 || profit<=0.0 || factor<=1.0 || drawdown<=0.0 || win_rate<66.67)
         return -1000.0+win_rate+MathMin(24.0,trades)/100.0;
      return (win_rate-66.67)*MathSqrt(trades)*MathMin(3.0,factor)/(1.0+drawdown);
   }
   if(trades<25.0 || profit<=0.0 || factor<=1.0 || drawdown<=0.0) return -1000.0+trades;
   return (profit/drawdown)*MathMin(2.0,MathSqrt(trades/60.0))*MathMin(2.5,factor);
}
