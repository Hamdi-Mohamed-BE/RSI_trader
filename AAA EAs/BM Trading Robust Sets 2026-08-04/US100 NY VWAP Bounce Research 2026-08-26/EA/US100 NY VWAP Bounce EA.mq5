#property copyright "US100 New York VWAP bounce research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_VB_CONFIRMATION
{
   VB_DIRECTIONAL=0,
   VB_SIDE_ONLY=1
};

enum ENUM_VB_TREND_FILTER
{
   VB_TREND_NONE=0,
   VB_TREND_VWAP_SLOPE=1,
   VB_TREND_EMA=2
};

enum ENUM_VB_STOP_MODE
{
   VB_STOP_REJECTION=0,
   VB_STOP_PULLBACK_SWING=1,
   VB_STOP_DAILY_RANGE=2
};

enum ENUM_VB_TARGET_MODE
{
   VB_TARGET_EXTENSION_EXTREME=0,
   VB_TARGET_FIXED_R=1
};

input group "New York session"
input int                    InpCashOpenHour=9;
input int                    InpCashOpenMinute=30;
input int                    InpORBMinutes=15;
input int                    InpSetupWindowMinutes=90;
input int                    InpFlatHour=15;
input int                    InpFlatMinute=55;
input bool                   InpWeekdaysOnly=true;

input group "Extension and VWAP rejection"
input ENUM_VB_CONFIRMATION   InpConfirmation=VB_SIDE_ONLY;
input ENUM_VB_TREND_FILTER   InpTrendFilter=VB_TREND_EMA;
input double                 InpExtensionBufferDailyRange=0.0;
input double                 InpTouchToleranceDailyRange=0.01;
input bool                   InpFirstTouchOnly=true;
input int                    InpVWAPSlopeBars=3;
input int                    InpFastEMA=20;
input int                    InpSlowEMA=50;

input group "Stop, target and risk"
input ENUM_VB_STOP_MODE      InpStopMode=VB_STOP_DAILY_RANGE;
input int                    InpDailyRangeLookback=20;
input double                 InpStopBufferDailyRange=0.01;
input double                 InpDailyRangeStopMultiple=0.25;
input double                 InpMaximumStopDailyRange=1.5;
input ENUM_VB_TARGET_MODE    InpTargetMode=VB_TARGET_FIXED_R;
input double                 InpRewardRisk=2.0;
input double                 InpRiskPercent=1.0;

input group "Broker execution"
input double                 InpMaximumSpreadRiskPercent=10.0;
input int                    InpMaximumDeviationPoints=50;
input long                   InpMagic=86260827;
input bool                   InpUseAutomaticLiveServerOffset=true;
input int                    InpTesterServerUTCOffsetHours=0;
input int                    InpManualLiveServerUTCOffsetHours=0;
input bool                   InpShowVWAP=true;

CTrade trade;
datetime g_last_m5_bar=0;
int g_session_key=0;
bool g_traded_today=false;
bool g_extension_found=false;
bool g_touch_consumed=false;
int g_direction=0;
double g_orb_high=0.0;
double g_orb_low=0.0;
double g_extension_extreme=0.0;
double g_pullback_extreme=0.0;
double g_daily_range=0.0;
double g_initial_risk=0.0;
int g_fast_handle=INVALID_HANDLE;
int g_slow_handle=INVALID_HANDLE;

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

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime local=source;
   datetime value=StructToTime(local);
   int offset=(NewYorkDateUsesDST(source) ? -4 : -5);
   datetime utc=value-offset*3600;
   return utc+ServerUTCOffsetSeconds();
}

datetime NYTime(const MqlDateTime &date,const int hour,const int minute)
{
   MqlDateTime value=date;
   value.hour=hour; value.min=minute; value.sec=0;
   return NewYorkToServer(value);
}

int DateKey(const MqlDateTime &value)
{
   return value.year*10000+value.mon*100+value.day;
}

void PreviousCalendarDay(MqlDateTime &value)
{
   value.hour=12; value.min=0; value.sec=0;
   datetime previous=StructToTime(value)-86400;
   TimeToStruct(previous,value);
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

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double result=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,result) || result==0.0) return 0.0;
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(cash/MathAbs(result));
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

bool TradedOnDate(const MqlDateTime &date)
{
   MqlDateTime start=date;
   start.hour=0; start.min=0; start.sec=0;
   MqlDateTime finish=start;
   finish.hour=23; finish.min=59; finish.sec=59;
   if(!HistorySelect(NewYorkToServer(start),NewYorkToServer(finish))) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN)
         return true;
   }
   return false;
}

bool SessionRange(const MqlDateTime &date,double &high,double &low,int &bars)
{
   datetime from=NYTime(date,9,30);
   datetime to=NYTime(date,16,0)-1;
   MqlRates rates[];
   bars=CopyRates(_Symbol,PERIOD_M5,from,to,rates);
   if(bars<=0) return false;
   high=-DBL_MAX; low=DBL_MAX;
   for(int index=0;index<bars;index++)
   {
      high=MathMax(high,rates[index].high);
      low=MathMin(low,rates[index].low);
   }
   return high>low;
}

double PreviousRTHRangeMedian(const MqlDateTime &current_date)
{
   double samples[];
   int found=0,attempts=0;
   MqlDateTime candidate=current_date;
   while(found<InpDailyRangeLookback && attempts<InpDailyRangeLookback*3+20)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(candidate.day_of_week==0 || candidate.day_of_week==6) continue;
      double high=0.0,low=0.0; int bars=0;
      if(!SessionRange(candidate,high,low,bars) || bars<60) continue;
      ArrayResize(samples,found+1);
      samples[found]=high-low;
      found++;
   }
   if(found<MathMin(14,InpDailyRangeLookback)) return 0.0;
   return Median(samples);
}

bool BuildORB(const MqlDateTime &date)
{
   datetime from=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   datetime to=from+InpORBMinutes*60-1;
   MqlRates rates[];
   int copied=CopyRates(_Symbol,PERIOD_M5,from,to,rates);
   if(copied<InpORBMinutes/5) return false;
   g_orb_high=-DBL_MAX; g_orb_low=DBL_MAX;
   for(int index=0;index<copied;index++)
   {
      g_orb_high=MathMax(g_orb_high,rates[index].high);
      g_orb_low=MathMin(g_orb_low,rates[index].low);
   }
   return g_orb_high>g_orb_low;
}

bool AnchoredVWAP(const MqlDateTime &date,const datetime through,double &vwap,double &prior_vwap)
{
   datetime from=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   MqlRates rates[];
   int copied=CopyRates(_Symbol,PERIOD_M5,from,through+299,rates);
   if(copied<=0) return false;
   double pv=0.0,volume=0.0;
   double history[];
   ArrayResize(history,copied);
   for(int index=0;index<copied;index++)
   {
      double activity=(double)rates[index].tick_volume;
      pv+=((rates[index].high+rates[index].low+rates[index].close)/3.0)*activity;
      volume+=activity;
      history[index]=(volume>0.0 ? pv/volume : rates[index].close);
   }
   if(volume<=0.0) return false;
   vwap=history[copied-1];
   int prior=MathMax(0,copied-1-InpVWAPSlopeBars);
   prior_vwap=history[prior];
   return true;
}

bool EMAFilter(const int direction,const MqlRates &bar)
{
   double fast[1],slow[1];
   int shift=iBarShift(_Symbol,PERIOD_M5,bar.time,false);
   if(shift<0 || CopyBuffer(g_fast_handle,0,shift,1,fast)!=1 || CopyBuffer(g_slow_handle,0,shift,1,slow)!=1)
      return false;
   if(direction>0) return fast[0]>slow[0] && bar.close>fast[0];
   return fast[0]<slow[0] && bar.close<fast[0];
}

bool SpreadOK(const double risk)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || risk<=0.0) return false;
   return (tick.ask-tick.bid)/risk*100.0<=InpMaximumSpreadRiskPercent;
}

bool EnterTrade(const int direction,const MqlRates &bar)
{
   if(g_traded_today) return false;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double buffer=InpStopBufferDailyRange*g_daily_range;
   double stop=0.0;
   if(InpStopMode==VB_STOP_REJECTION)
      stop=(direction>0 ? bar.low-buffer : bar.high+buffer);
   else if(InpStopMode==VB_STOP_PULLBACK_SWING)
      stop=(direction>0 ? g_pullback_extreme-buffer : g_pullback_extreme+buffer);
   else
      stop=(direction>0 ? entry-InpDailyRangeStopMultiple*g_daily_range : entry+InpDailyRangeStopMultiple*g_daily_range);
   stop=NormalizePrice(stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || risk>InpMaximumStopDailyRange*g_daily_range || !SpreadOK(risk)) return false;
   double target=0.0;
   if(InpTargetMode==VB_TARGET_EXTENSION_EXTREME)
      target=g_extension_extreme;
   else
      target=(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   target=NormalizePrice(target);
   if((direction>0 && target<=entry) || (direction<0 && target>=entry)) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum || MathAbs(target-entry)<minimum) return false;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,"NY VWAP bounce")
                          : trade.Sell(lots,_Symbol,0.0,stop,target,"NY VWAP bounce"));
   if(!sent)
   {
      Print("VWAP bounce entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_traded_today=true;
   g_initial_risk=risk;
   return true;
}

void DrawVWAP(const double value)
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowVWAP || value<=0.0) return;
   string name=StringFormat("NYVWAP_%I64d_%s",InpMagic,_Symbol);
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_HLINE,0,0,value);
   ObjectSetDouble(0,name,OBJPROP_PRICE,value);
   ObjectSetInteger(0,name,OBJPROP_COLOR,clrMediumSeaGreen);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,2);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
}

void EvaluateClosedBar(const MqlDateTime &date)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,1,bars)!=1) return;
   MqlRates bar=bars[0];
   datetime open=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   datetime orb_end=open+InpORBMinutes*60;
   datetime setup_end=orb_end+InpSetupWindowMinutes*60;
   if(bar.time<orb_end || bar.time>=setup_end) return;
   if((g_orb_high<=g_orb_low) && !BuildORB(date)) return;
   double vwap=0.0,prior_vwap=0.0;
   if(!AnchoredVWAP(date,bar.time,vwap,prior_vwap)) return;
   DrawVWAP(vwap);
   double extension_buffer=InpExtensionBufferDailyRange*g_daily_range;
   if(!g_extension_found)
   {
      bool up=bar.high>g_orb_high+extension_buffer;
      bool down=bar.low<g_orb_low-extension_buffer;
      if(up==down) return;
      g_direction=(up ? 1 : -1);
      g_extension_found=true;
      g_extension_extreme=(g_direction>0 ? bar.high : bar.low);
      g_pullback_extreme=(g_direction>0 ? bar.low : bar.high);
   }
   else
   {
      if(g_direction>0)
      {
         g_extension_extreme=MathMax(g_extension_extreme,bar.high);
         g_pullback_extreme=MathMin(g_pullback_extreme,bar.low);
      }
      else
      {
         g_extension_extreme=MathMin(g_extension_extreme,bar.low);
         g_pullback_extreme=MathMax(g_pullback_extreme,bar.high);
      }
   }
   if(g_touch_consumed && InpFirstTouchOnly) return;
   double tolerance=InpTouchToleranceDailyRange*g_daily_range;
   bool touched=(g_direction>0 ? bar.low<=vwap+tolerance : bar.high>=vwap-tolerance);
   if(!touched) return;
   if(InpFirstTouchOnly) g_touch_consumed=true;
   bool same_side=(g_direction>0 ? (bar.open>vwap && bar.close>vwap) : (bar.open<vwap && bar.close<vwap));
   if(!same_side) return;
   if(InpConfirmation==VB_DIRECTIONAL)
   {
      if(g_direction>0 && bar.close<=bar.open) return;
      if(g_direction<0 && bar.close>=bar.open) return;
   }
   if(InpTrendFilter==VB_TREND_VWAP_SLOPE)
   {
      if(g_direction>0 && vwap<=prior_vwap) return;
      if(g_direction<0 && vwap>=prior_vwap) return;
   }
   else if(InpTrendFilter==VB_TREND_EMA && !EMAFilter(g_direction,bar)) return;
   EnterTrade(g_direction,bar);
}

void ManagePosition(const MqlDateTime &now_ny)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   int now_minutes=now_ny.hour*60+now_ny.min;
   if(now_minutes<InpFlatHour*60+InpFlatMinute) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   if(!trade.PositionClose(ticket)) Print("VWAP bounce session close failed: ",trade.ResultRetcodeDescription());
}

void ResetSession(const MqlDateTime &date)
{
   g_session_key=DateKey(date);
   g_traded_today=TradedOnDate(date);
   g_extension_found=false;
   g_touch_consumed=false;
   g_direction=0;
   g_orb_high=0.0; g_orb_low=0.0;
   g_extension_extreme=0.0; g_pullback_extreme=0.0;
   g_daily_range=0.0; g_initial_risk=0.0;
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_ny;
   TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(DateKey(now_ny)!=g_session_key) ResetSession(now_ny);
   ManagePosition(now_ny);
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current<=0 || current==g_last_m5_bar) return;
   g_last_m5_bar=current;
   if(g_traded_today || (InpWeekdaysOnly && (now_ny.day_of_week==0 || now_ny.day_of_week==6))) return;
   datetime open=NYTime(now_ny,InpCashOpenHour,InpCashOpenMinute);
   datetime start=open+InpORBMinutes*60;
   datetime finish=start+InpSetupWindowMinutes*60+300;
   if(now_server<start || now_server>=finish) return;
   if(g_daily_range<=0.0)
   {
      g_daily_range=PreviousRTHRangeMedian(now_ny);
      if(g_daily_range<=0.0 || !BuildORB(now_ny)) return;
   }
   EvaluateClosedBar(now_ny);
}

int OnInit()
{
   if(InpORBMinutes<5 || (InpORBMinutes%5)!=0 || InpORBMinutes>60 ||
      InpSetupWindowMinutes<5 || InpSetupWindowMinutes>240 || InpVWAPSlopeBars<1 ||
      InpFastEMA<2 || InpSlowEMA<=InpFastEMA || InpDailyRangeLookback<14 ||
      InpDailyRangeStopMultiple<=0.0 || InpMaximumStopDailyRange<=0.0 ||
      InpRewardRisk<=0.0 || InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   g_fast_handle=iMA(_Symbol,PERIOD_M5,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow_handle=iMA(_Symbol,PERIOD_M5,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_fast_handle==INVALID_HANDLE || g_slow_handle==INVALID_HANDLE) return INIT_FAILED;
   g_last_m5_bar=iTime(_Symbol,PERIOD_M5,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_handle);
   if(g_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_handle);
   ObjectDelete(0,StringFormat("NYVWAP_%I64d_%s",InpMagic,_Symbol));
}

void OnTick(){ ProcessStrategy(); }
void OnTimer(){ ProcessStrategy(); }

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<40.0 || profit<=0.0 || pf<1.02 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/100.0))*MathMin(pf,3.0);
}
