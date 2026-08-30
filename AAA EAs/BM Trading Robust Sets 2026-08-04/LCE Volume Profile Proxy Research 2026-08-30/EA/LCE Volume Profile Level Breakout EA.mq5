#property copyright "Transparent systematic proxy for the public LCE rules"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Execution session"
input ENUM_TIMEFRAMES InpExecutionTimeframe=PERIOD_M5;
input int InpServerUTCOffsetHours=0;
input int InpEntryStartHourNY=9;
input int InpEntryStartMinuteNY=30;
input int InpEntryEndHourNY=12;
input int InpForcedCloseHourNY=16;
input int InpMaximumTradesPerDay=2;
input bool InpStopAfterFirstWinner=true;

input group "Volume-profile level proxy"
input int InpProfileLookbackDays=20;
input ENUM_TIMEFRAMES InpProfileTimeframe=PERIOD_M15;
input int InpProfileRows=160;
input double InpMinimumNodeVolumeFactor=1.00;
input double InpMinimumNodeSpacingH1ATR=0.75;
input double InpZoneHalfWidthSpacingFraction=0.15;
input double InpLevelPenetration=0.50;
input int InpMaximumProfileNodes=24;

input group "20/50 EMA cloud"
input int InpFastEMAPeriod=20;
input int InpSlowEMAPeriod=50;
input int InpATRPeriod=14;
input double InpCloudFlatATR=0.05;
input int InpMinimumCloudScore=0;
input bool InpUseH1Cloud=true;
input bool InpUseM30Cloud=true;
input bool InpUseM15Cloud=true;
input bool InpUseM5Cloud=true;

input group "Breakout and risk"
input int InpStructureLookbackBars=6;
input double InpStopBufferATR=0.10;
input double InpMinimumTargetR=0.75;
input double InpRiskPercent=1.00;
input bool InpMoveToBreakEven=true;
input double InpBreakEvenTargetFraction=0.50;
input double InpMaximumSpreadATR=0.10;
input int InpMaximumDeviationPoints=50;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input long InpMagic=863200;

CTrade g_trade;
int g_atr_m5=INVALID_HANDLE;
int g_atr_h1=INVALID_HANDLE;
int g_fast_h1=INVALID_HANDLE,g_slow_h1=INVALID_HANDLE,g_cloud_atr_h1=INVALID_HANDLE;
int g_fast_m30=INVALID_HANDLE,g_slow_m30=INVALID_HANDLE,g_cloud_atr_m30=INVALID_HANDLE;
int g_fast_m15=INVALID_HANDLE,g_slow_m15=INVALID_HANDLE,g_cloud_atr_m15=INVALID_HANDLE;
int g_fast_m5=INVALID_HANDLE,g_slow_m5=INVALID_HANDLE,g_cloud_atr_m5=INVALID_HANDLE;
datetime g_last_bar=0;
long g_session_day=0;
bool g_profile_ready=false;
bool g_day_won=false;
int g_day_trades=0;
double g_levels[];
double g_strengths[];
int g_level_count=0;
double g_initial_risk=0.0;

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first={0}; first.year=year; first.mon=month; first.day=1;
   MqlDateTime converted={0}; TimeToStruct(StructToTime(first),converted);
   int first_sunday=1+((7-converted.day_of_week)%7);
   return first_sunday+7*(nth-1);
}

bool IsNewYorkDST(const datetime utc_time)
{
   MqlDateTime value={0}; TimeToStruct(utc_time,value);
   if(value.mon>3 && value.mon<11) return true;
   if(value.mon<3 || value.mon>11) return false;
   if(value.mon==3)
   {
      int day=NthSunday(value.year,3,2);
      if(value.day!=day) return value.day>day;
      return value.hour>=7;
   }
   int day=NthSunday(value.year,11,1);
   if(value.day!=day) return value.day<day;
   return value.hour<6;
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-InpServerUTCOffsetHours*3600;
   return utc_time+(IsNewYorkDST(utc_time) ? -4*3600 : -5*3600);
}

long NewYorkDayKey(const datetime server_time)
{
   MqlDateTime value={0}; TimeToStruct(ServerToNewYork(server_time),value);
   return (long)value.year*10000+(long)value.mon*100+(long)value.day;
}

int NewYorkMinute(const datetime server_time)
{
   MqlDateTime value={0}; TimeToStruct(ServerToNewYork(server_time),value);
   return value.hour*60+value.min;
}

int NewYorkWeekday(const datetime server_time)
{
   MqlDateTime value={0}; TimeToStruct(ServerToNewYork(server_time),value);
   return value.day_of_week;
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
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   if(cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   return NormalizeLots(cash/one_lot);
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

bool ReadBufferValue(const int handle,const int shift,double &value)
{
   double values[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,values)!=1) return false;
   value=values[0];
   return MathIsValidNumber(value);
}

bool ReadATR(const int handle,const int shift,double &value)
{
   if(!ReadBufferValue(handle,shift,value)) return false;
   return value>0.0;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

void ResetDay(const long day_key)
{
   g_session_day=day_key;
   g_profile_ready=false;
   g_day_won=false;
   g_day_trades=0;
   g_level_count=0;
   ArrayResize(g_levels,0);
   ArrayResize(g_strengths,0);
}

int CloudDirection(const int fast_handle,const int slow_handle,const int atr_handle)
{
   double fast1=0.0,fast2=0.0,slow1=0.0,slow2=0.0,atr=0.0;
   if(!ReadBufferValue(fast_handle,1,fast1) || !ReadBufferValue(fast_handle,2,fast2) ||
      !ReadBufferValue(slow_handle,1,slow1) || !ReadBufferValue(slow_handle,2,slow2) ||
      !ReadATR(atr_handle,1,atr)) return 0;
   double gap=fast1-slow1;
   double slope=((fast1-fast2)+(slow1-slow2))*0.5;
   if(gap>InpCloudFlatATR*atr && slope>0.0) return 1;
   if(gap<-InpCloudFlatATR*atr && slope<0.0) return -1;
   return 0;
}

int CloudScore()
{
   int score=0;
   if(InpUseH1Cloud) score+=CloudDirection(g_fast_h1,g_slow_h1,g_cloud_atr_h1);
   if(InpUseM30Cloud) score+=CloudDirection(g_fast_m30,g_slow_m30,g_cloud_atr_m30);
   if(InpUseM15Cloud) score+=CloudDirection(g_fast_m15,g_slow_m15,g_cloud_atr_m15);
   if(InpUseM5Cloud) score+=CloudDirection(g_fast_m5,g_slow_m5,g_cloud_atr_m5);
   return score;
}

bool DirectionPasses(const int direction)
{
   int score=CloudScore();
   if(direction>0) return score>=InpMinimumCloudScore;
   return score<=-InpMinimumCloudScore;
}

bool BuildProfile(const datetime cutoff)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   datetime from=cutoff-InpProfileLookbackDays*86400;
   int copied=CopyRates(_Symbol,InpProfileTimeframe,from,cutoff,bars);
   if(copied<200) return false;

   double low=DBL_MAX,high=-DBL_MAX;
   for(int index=0;index<copied;index++)
   {
      low=MathMin(low,bars[index].low);
      high=MathMax(high,bars[index].high);
   }
   if(high<=low) return false;
   int rows=MathMax(40,MathMin(InpProfileRows,400));
   double row_size=(high-low)/rows;
   if(row_size<=0.0) return false;
   double volumes[]; ArrayResize(volumes,rows); ArrayInitialize(volumes,0.0);
   double total=0.0;
   for(int index=0;index<copied;index++)
   {
      double typical=(bars[index].high+bars[index].low+bars[index].close)/3.0;
      int bin=(int)MathFloor((typical-low)/row_size);
      bin=MathMax(0,MathMin(rows-1,bin));
      double volume=(double)bars[index].tick_volume;
      volumes[bin]+=volume;
      total+=volume;
   }
   if(total<=0.0) return false;
   double average=total/rows;
   double h1atr=0.0;
   if(!ReadATR(g_atr_h1,1,h1atr)) return false;
   double minimum_spacing=InpMinimumNodeSpacingH1ATR*h1atr;

   ArrayResize(g_levels,0); ArrayResize(g_strengths,0); g_level_count=0;
   for(int bin=2;bin<rows-2;bin++)
   {
      double volume=volumes[bin];
      bool local_peak=volume>=volumes[bin-1] && volume>volumes[bin+1] &&
                      volume>=volumes[bin-2] && volume>=volumes[bin+2];
      if(!local_peak || volume<InpMinimumNodeVolumeFactor*average) continue;
      double price=low+(bin+0.5)*row_size;
      if(g_level_count>0 && price-g_levels[g_level_count-1]<minimum_spacing)
      {
         if(volume>g_strengths[g_level_count-1])
         {
            g_levels[g_level_count-1]=price;
            g_strengths[g_level_count-1]=volume;
         }
         continue;
      }
      int size=g_level_count+1;
      ArrayResize(g_levels,size); ArrayResize(g_strengths,size);
      g_levels[g_level_count]=price;
      g_strengths[g_level_count]=volume;
      g_level_count++;
   }

   while(g_level_count>InpMaximumProfileNodes)
   {
      int weakest=0;
      for(int index=1;index<g_level_count;index++)
         if(g_strengths[index]<g_strengths[weakest]) weakest=index;
      for(int index=weakest;index<g_level_count-1;index++)
      {
         g_levels[index]=g_levels[index+1];
         g_strengths[index]=g_strengths[index+1];
      }
      g_level_count--;
      ArrayResize(g_levels,g_level_count); ArrayResize(g_strengths,g_level_count);
   }

   // Removing weak nodes can disturb order only through deletion; enforce ascending order defensively.
   for(int left=0;left<g_level_count-1;left++)
      for(int right=left+1;right<g_level_count;right++)
         if(g_levels[right]<g_levels[left])
         {
            double swap=g_levels[left]; g_levels[left]=g_levels[right]; g_levels[right]=swap;
            swap=g_strengths[left]; g_strengths[left]=g_strengths[right]; g_strengths[right]=swap;
         }
   g_profile_ready=(g_level_count>=3);
   return g_profile_ready;
}

double ZoneHalfWidth(const int index)
{
   if(g_level_count<2 || index<0 || index>=g_level_count) return 0.0;
   double spacing=DBL_MAX;
   if(index>0) spacing=MathMin(spacing,g_levels[index]-g_levels[index-1]);
   if(index<g_level_count-1) spacing=MathMin(spacing,g_levels[index+1]-g_levels[index]);
   return spacing==DBL_MAX ? 0.0 : spacing*InpZoneHalfWidthSpacingFraction;
}

double RecentLow(const MqlRates &rates[])
{
   double value=DBL_MAX;
   for(int index=1;index<=MathMin(InpStructureLookbackBars,ArraySize(rates)-1);index++)
      value=MathMin(value,rates[index].low);
   return value;
}

double RecentHigh(const MqlRates &rates[])
{
   double value=-DBL_MAX;
   for(int index=1;index<=MathMin(InpStructureLookbackBars,ArraySize(rates)-1);index++)
      value=MathMax(value,rates[index].high);
   return value;
}

bool PlaceTrade(const int direction,const int level_index,const MqlRates &rates[],const double atr)
{
   if(HasOurPosition() || g_day_trades>=InpMaximumTradesPerDay || (InpStopAfterFirstWinner && g_day_won)) return false;
   if(direction>0 && !InpAllowLong) return false;
   if(direction<0 && !InpAllowShort) return false;
   if(!DirectionPasses(direction) || !SpreadPasses(atr)) return false;
   int target_index=level_index+direction;
   if(target_index<0 || target_index>=g_level_count) return false;
   MqlTick tick={0}; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double half=ZoneHalfWidth(level_index);
   double stop=(direction>0 ? MathMin(RecentLow(rates),g_levels[level_index]-half)-InpStopBufferATR*atr
                            : MathMax(RecentHigh(rates),g_levels[level_index]+half)+InpStopBufferATR*atr);
   double target=g_levels[target_index];
   if(direction>0 && target<=entry) return false;
   if(direction<0 && target>=entry) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=entry-broker_gap;
   if(direction<0 && stop-entry<broker_gap) stop=entry+broker_gap;
   double risk=MathAbs(entry-stop);
   double reward=MathAbs(target-entry);
   if(risk<=0.0 || reward/risk<InpMinimumTargetR) return false;
   stop=NormalizePrice(stop); target=NormalizePrice(target);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"LCE VP level long")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"LCE VP level short"));
   if(!sent)
   {
      Print("LCE proxy order rejected: ",g_trade.ResultRetcodeDescription());
      return false;
   }
   g_initial_risk=risk;
   return true;
}

void ManagePosition()
{
   MqlTick tick={0}; if(!SymbolInfoTick(_Symbol,tick)) return;
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
      if(InpMoveToBreakEven && target>0.0)
      {
         double progress=(buy ? current-open : open-current);
         double target_distance=MathAbs(target-open);
         if(progress>=InpBreakEvenTargetFraction*target_distance)
         {
            double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
            double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                               (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
            bool valid=(buy ? open>stop && open<current-gap : (stop<=0.0 || open<stop) && open>current+gap);
            if(valid) g_trade.PositionModify(ticket,NormalizePrice(open),target);
         }
      }
      if(NewYorkMinute(TimeCurrent())>=InpForcedCloseHourNY*60)
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
   if(!found) g_initial_risk=0.0;
}

void ProcessClosedBar()
{
   int required=InpStructureLookbackBars+5;
   MqlRates rates[]; ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpExecutionTimeframe,0,required,rates)<required) return;
   const MqlRates bar=rates[1];
   int weekday=NewYorkWeekday(bar.time);
   long day_key=NewYorkDayKey(bar.time);
   if(day_key!=g_session_day) ResetDay(day_key);
   if(weekday==0 || weekday==6) return;
   int minute=NewYorkMinute(bar.time);
   int start=InpEntryStartHourNY*60+InpEntryStartMinuteNY;
   int end=InpEntryEndHourNY*60;
   if(minute<start || minute>=InpForcedCloseHourNY*60) return;
   if(!g_profile_ready && minute>=start)
      BuildProfile(bar.time);
   if(!g_profile_ready || minute>=end || HasOurPosition() || g_day_trades>=InpMaximumTradesPerDay ||
      (InpStopAfterFirstWinner && g_day_won)) return;
   double atr=0.0; if(!ReadATR(g_atr_m5,1,atr)) return;
   bool bullish=bar.close>bar.open;
   bool bearish=bar.close<bar.open;
   int long_level=-1;
   int short_level=-1;
   for(int index=1;index<g_level_count-1;index++)
   {
      double half=ZoneHalfWidth(index);
      double long_trigger=g_levels[index]-half+2.0*half*InpLevelPenetration;
      double short_trigger=g_levels[index]+half-2.0*half*InpLevelPenetration;
      if(bullish && rates[2].close<long_trigger && bar.close>=long_trigger) long_level=index;
      if(bearish && rates[2].close>short_trigger && bar.close<=short_trigger)
      {
         short_level=index;
         break;
      }
   }
   if(long_level>=0) { PlaceTrade(1,long_level,rates,atr); return; }
   if(short_level>=0) PlaceTrade(-1,short_level,rates,atr);
}

int MakeEMA(const ENUM_TIMEFRAMES timeframe,const int period)
{
   return iMA(_Symbol,timeframe,period,0,MODE_EMA,PRICE_CLOSE);
}

int MakeATR(const ENUM_TIMEFRAMES timeframe)
{
   return iATR(_Symbol,timeframe,InpATRPeriod);
}

int OnInit()
{
   if(InpEntryStartHourNY<0 || InpEntryStartHourNY>23 || InpEntryStartMinuteNY<0 ||
      InpEntryStartMinuteNY>59 || InpEntryEndHourNY<=InpEntryStartHourNY || InpEntryEndHourNY>23 ||
      InpForcedCloseHourNY<InpEntryEndHourNY || InpForcedCloseHourNY>23 || InpMaximumTradesPerDay<1 ||
      InpProfileLookbackDays<2 || InpProfileRows<40 || InpProfileRows>400 ||
      InpMinimumNodeVolumeFactor<=0.0 || InpMinimumNodeSpacingH1ATR<=0.0 ||
      InpZoneHalfWidthSpacingFraction<=0.0 || InpZoneHalfWidthSpacingFraction>=0.45 ||
      InpLevelPenetration<0.0 || InpLevelPenetration>1.0 || InpMaximumProfileNodes<3 ||
      InpFastEMAPeriod<2 || InpSlowEMAPeriod<=InpFastEMAPeriod || InpATRPeriod<2 ||
      InpMinimumCloudScore<0 || InpMinimumCloudScore>4 || InpStructureLookbackBars<2 ||
      InpMinimumTargetR<=0.0 || InpRiskPercent<=0.0 || InpBreakEvenTargetFraction<=0.0 ||
      InpBreakEvenTargetFraction>=1.0 || InpMaximumSpreadATR<0.0)
      return INIT_PARAMETERS_INCORRECT;

   g_atr_m5=MakeATR(InpExecutionTimeframe); g_atr_h1=MakeATR(PERIOD_H1);
   g_fast_h1=MakeEMA(PERIOD_H1,InpFastEMAPeriod); g_slow_h1=MakeEMA(PERIOD_H1,InpSlowEMAPeriod); g_cloud_atr_h1=MakeATR(PERIOD_H1);
   g_fast_m30=MakeEMA(PERIOD_M30,InpFastEMAPeriod); g_slow_m30=MakeEMA(PERIOD_M30,InpSlowEMAPeriod); g_cloud_atr_m30=MakeATR(PERIOD_M30);
   g_fast_m15=MakeEMA(PERIOD_M15,InpFastEMAPeriod); g_slow_m15=MakeEMA(PERIOD_M15,InpSlowEMAPeriod); g_cloud_atr_m15=MakeATR(PERIOD_M15);
   g_fast_m5=MakeEMA(PERIOD_M5,InpFastEMAPeriod); g_slow_m5=MakeEMA(PERIOD_M5,InpSlowEMAPeriod); g_cloud_atr_m5=MakeATR(PERIOD_M5);
   if(g_atr_m5==INVALID_HANDLE || g_atr_h1==INVALID_HANDLE ||
      g_fast_h1==INVALID_HANDLE || g_slow_h1==INVALID_HANDLE || g_cloud_atr_h1==INVALID_HANDLE ||
      g_fast_m30==INVALID_HANDLE || g_slow_m30==INVALID_HANDLE || g_cloud_atr_m30==INVALID_HANDLE ||
      g_fast_m15==INVALID_HANDLE || g_slow_m15==INVALID_HANDLE || g_cloud_atr_m15==INVALID_HANDLE ||
      g_fast_m5==INVALID_HANDLE || g_slow_m5==INVALID_HANDLE || g_cloud_atr_m5==INVALID_HANDLE)
      return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpExecutionTimeframe,0);
   ResetDay(0);
   return INIT_SUCCEEDED;
}

void ReleaseHandle(int &handle)
{
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   handle=INVALID_HANDLE;
}

void OnDeinit(const int reason)
{
   ReleaseHandle(g_atr_m5); ReleaseHandle(g_atr_h1);
   ReleaseHandle(g_fast_h1); ReleaseHandle(g_slow_h1); ReleaseHandle(g_cloud_atr_h1);
   ReleaseHandle(g_fast_m30); ReleaseHandle(g_slow_m30); ReleaseHandle(g_cloud_atr_m30);
   ReleaseHandle(g_fast_m15); ReleaseHandle(g_slow_m15); ReleaseHandle(g_cloud_atr_m15);
   ReleaseHandle(g_fast_m5); ReleaseHandle(g_slow_m5); ReleaseHandle(g_cloud_atr_m5);
}

void OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 || !HistoryDealSelect(transaction.deal)) return;
   if(HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol) return;
   long entry=HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY) return;
   double cash=HistoryDealGetDouble(transaction.deal,DEAL_PROFIT)+HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION)+HistoryDealGetDouble(transaction.deal,DEAL_SWAP);
   g_day_trades++;
   if(cash>0.0) g_day_won=true;
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,InpExecutionTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   ProcessClosedBar();
}
