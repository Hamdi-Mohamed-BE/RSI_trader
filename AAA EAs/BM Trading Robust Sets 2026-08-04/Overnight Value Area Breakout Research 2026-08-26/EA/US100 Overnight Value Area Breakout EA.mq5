#property copyright "Overnight value-area breakout research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_OVA_ENTRY_MODE
{
   OVA_DIRECT_CLOSE=0,
   OVA_VALUE_AREA_RETEST=1
};

enum ENUM_OVA_STOP_MODE
{
   OVA_SIGNAL_CANDLE=0,
   OVA_PROFILE_POC=1,
   OVA_OPPOSITE_VALUE_AREA=2,
   OVA_DAILY_RANGE_ATR=3
};

input group "New York session"
input int                   InpProfilePreviousDayHour=16;
input int                   InpProfilePreviousDayMinute=30;
input int                   InpCashOpenHour=9;
input int                   InpCashOpenMinute=30;
input int                   InpSignalWindowBars=4;
input int                   InpFlatHour=15;
input int                   InpFlatMinute=55;
input bool                  InpWeekdaysOnly=true;

input group "Overnight tick-activity value profile"
input int                   InpProfileBins=64;
input double                InpValueAreaPercent=70.0;
input int                   InpMinimumProfileBars=500;
input bool                  InpShowProfileLevels=true;

input group "Breakout and confirmation"
input ENUM_OVA_ENTRY_MODE   InpEntryMode=OVA_VALUE_AREA_RETEST;
input bool                  InpRequireDirectionalCandle=true;
input double                InpBreakoutBufferDailyATR=0.0;
input double                InpMinimumRelativeVolume=0.0;
input int                   InpRelativeVolumeLookback=20;
input int                   InpRetestBars=4;
input double                InpRetestToleranceDailyATR=0.08;

input group "Stop, target and risk"
input ENUM_OVA_STOP_MODE    InpStopMode=OVA_DAILY_RANGE_ATR;
input int                   InpDailyRangeLookback=20;
input double                InpStopBufferDailyATR=0.0;
input double                InpATRStopMultiple=1.0;
input double                InpMaximumStopDailyATR=2.5;
input double                InpRewardRisk=1.5;
input double                InpBreakEvenAtR=0.0;
input double                InpRiskPercent=1.0;

input group "Broker execution"
input double                InpMaximumSpreadRiskPercent=10.0;
input int                   InpMaximumDeviationPoints=50;
input long                  InpMagic=86260826;
input bool                  InpUseAutomaticLiveServerOffset=true;
input int                   InpTesterServerUTCOffsetHours=0;
input int                   InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_m15_bar=0;
int g_session_key=0;
bool g_profile_ready=false;
bool g_traded_today=false;
bool g_signal_consumed=false;
int g_breakout_direction=0;
int g_retest_age=0;
double g_profile_poc=0.0;
double g_profile_vah=0.0;
double g_profile_val=0.0;
double g_daily_range_atr=0.0;
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

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime local=source;
   datetime value=StructToTime(local);
   int offset=(NewYorkDateUsesDST(source) ? -4 : -5);
   datetime utc=value-offset*3600;
   return utc+ServerUTCOffsetSeconds();
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

datetime NYTime(const MqlDateTime &session_date,const int hour,const int minute)
{
   MqlDateTime value=session_date;
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
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double one_lot_loss=MathAbs(one_lot_result);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/one_lot_loss);
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

bool TradedOnDate(const MqlDateTime &session_date)
{
   MqlDateTime start=session_date;
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
   datetime from=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   datetime to=NYTime(date,16,0)-1;
   MqlRates rates[];
   bars=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
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
   int found=0;
   int attempts=0;
   MqlDateTime candidate=current_date;
   while(found<InpDailyRangeLookback && attempts<InpDailyRangeLookback*3+20)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(candidate.day_of_week==0 || candidate.day_of_week==6) continue;
      double high=0.0,low=0.0;
      int bars=0;
      if(!SessionRange(candidate,high,low,bars) || bars<250) continue;
      ArrayResize(samples,found+1);
      samples[found]=high-low;
      found++;
   }
   if(found<MathMin(14,InpDailyRangeLookback)) return 0.0;
   return Median(samples);
}

string ObjectName(const string suffix)
{
   return StringFormat("OVAB_%I64d_%s_%s",InpMagic,_Symbol,suffix);
}

void DeleteProfileObjects()
{
   ObjectDelete(0,ObjectName("POC"));
   ObjectDelete(0,ObjectName("VAH"));
   ObjectDelete(0,ObjectName("VAL"));
}

void DrawProfileLine(const string suffix,const double price,const color line_color,const ENUM_LINE_STYLE style)
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowProfileLevels || price<=0.0) return;
   string name=ObjectName(suffix);
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_HLINE,0,0,price);
   ObjectSetDouble(0,name,OBJPROP_PRICE,price);
   ObjectSetInteger(0,name,OBJPROP_COLOR,line_color);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,(suffix=="POC" ? 2 : 1));
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
}

void UpdateDisplay()
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowProfileLevels || !g_profile_ready) return;
   DrawProfileLine("POC",g_profile_poc,clrOrange,STYLE_SOLID);
   DrawProfileLine("VAH",g_profile_vah,clrDodgerBlue,STYLE_DASH);
   DrawProfileLine("VAL",g_profile_val,clrDodgerBlue,STYLE_DASH);
   Comment("Overnight broker tick-activity profile (not exchange volume)\n",
           "VAH: ",DoubleToString(g_profile_vah,_Digits),
           "  POC: ",DoubleToString(g_profile_poc,_Digits),
           "  VAL: ",DoubleToString(g_profile_val,_Digits),"\n",
           "Prior RTH median range: ",DoubleToString(g_daily_range_atr,_Digits));
}

bool BuildOvernightProfile(const MqlDateTime &session_date)
{
   MqlDateTime previous=session_date;
   PreviousCalendarDay(previous);
   datetime from=NYTime(previous,InpProfilePreviousDayHour,InpProfilePreviousDayMinute);
   datetime to=NYTime(session_date,InpCashOpenHour,InpCashOpenMinute)-1;
   MqlRates rates[];
   int copied=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(copied<InpMinimumProfileBars)
   {
      Print("Overnight profile unavailable: ",copied," M1 bars from ",
            TimeToString(from,TIME_DATE|TIME_MINUTES)," to ",TimeToString(to,TIME_DATE|TIME_MINUTES));
      return false;
   }
   double profile_low=DBL_MAX,profile_high=-DBL_MAX;
   for(int index=0;index<copied;index++)
   {
      profile_low=MathMin(profile_low,rates[index].low);
      profile_high=MathMax(profile_high,rates[index].high);
   }
   if(profile_high<=profile_low) return false;
   double width=(profile_high-profile_low)/(double)InpProfileBins;
   if(width<=0.0) return false;
   double activity[];
   ArrayResize(activity,InpProfileBins);
   ArrayInitialize(activity,0.0);
   for(int index=0;index<copied;index++)
   {
      double typical=(rates[index].high+rates[index].low+rates[index].close)/3.0;
      int bin=(int)MathFloor((typical-profile_low)/width);
      bin=MathMax(0,MathMin(InpProfileBins-1,bin));
      activity[bin]+=(double)rates[index].tick_volume;
   }
   int poc=0;
   double total=0.0;
   for(int index=0;index<InpProfileBins;index++)
   {
      total+=activity[index];
      if(activity[index]>activity[poc]) poc=index;
   }
   if(total<=0.0) return false;
   int value_low=poc,value_high=poc;
   double included=activity[poc];
   double target=total*InpValueAreaPercent/100.0;
   while(included<target && (value_low>0 || value_high<InpProfileBins-1))
   {
      double below=(value_low>0 ? activity[value_low-1] : -1.0);
      double above=(value_high<InpProfileBins-1 ? activity[value_high+1] : -1.0);
      if(above>=below && value_high<InpProfileBins-1)
      {
         value_high++;
         included+=activity[value_high];
      }
      else if(value_low>0)
      {
         value_low--;
         included+=activity[value_low];
      }
      else break;
   }
   g_profile_poc=NormalizePrice(profile_low+(poc+0.5)*width);
   g_profile_vah=NormalizePrice(profile_low+(value_high+1)*width);
   g_profile_val=NormalizePrice(profile_low+value_low*width);
   g_profile_ready=true;
   UpdateDisplay();
   return true;
}

double BarRelativeVolume(const MqlRates &signal)
{
   MqlRates prior[];
   int count=CopyRates(_Symbol,PERIOD_M15,signal.time-(InpRelativeVolumeLookback+5)*900,signal.time-1,prior);
   if(count<=0) return 0.0;
   int use=MathMin(count,InpRelativeVolumeLookback);
   double samples[];
   ArrayResize(samples,use);
   for(int index=0;index<use;index++) samples[index]=(double)prior[count-use+index].tick_volume;
   double median=Median(samples);
   return (median>0.0 ? (double)signal.tick_volume/median : 0.0);
}

bool SpreadOK(const double risk)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || risk<=0.0) return false;
   return (tick.ask-tick.bid)/risk*100.0<=InpMaximumSpreadRiskPercent;
}

bool EnterTrade(const int direction,const MqlRates &reference)
{
   if(g_traded_today) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double buffer=InpStopBufferDailyATR*g_daily_range_atr;
   double stop=0.0;
   if(InpStopMode==OVA_SIGNAL_CANDLE)
      stop=(direction>0 ? reference.low-buffer : reference.high+buffer);
   else if(InpStopMode==OVA_PROFILE_POC)
      stop=(direction>0 ? g_profile_poc-buffer : g_profile_poc+buffer);
   else if(InpStopMode==OVA_OPPOSITE_VALUE_AREA)
      stop=(direction>0 ? g_profile_val-buffer : g_profile_vah+buffer);
   else
      stop=(direction>0 ? entry-InpATRStopMultiple*g_daily_range_atr : entry+InpATRStopMultiple*g_daily_range_atr);
   stop=NormalizePrice(stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || risk>InpMaximumStopDailyATR*g_daily_range_atr || !SpreadOK(risk)) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("OVA entry skipped: position size is below the broker minimum or contract data is unavailable.");
      return false;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   string comment=StringFormat("OVA VA%.0f B%d",InpValueAreaPercent,InpProfileBins);
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent)
   {
      Print("OVA entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_traded_today=true;
   g_initial_risk=risk;
   return true;
}

bool RetestAccepted(const int direction,const MqlRates &bar)
{
   double tolerance=InpRetestToleranceDailyATR*g_daily_range_atr;
   if(direction>0)
      return bar.low<=g_profile_vah+tolerance && bar.close>g_profile_vah && bar.close>bar.open;
   return bar.high>=g_profile_val-tolerance && bar.close<g_profile_val && bar.close<bar.open;
}

void EvaluateClosedBar(const MqlDateTime &session_date)
{
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,closed)!=1) return;
   MqlRates bar=closed[0];
   datetime open_time=NYTime(session_date,InpCashOpenHour,InpCashOpenMinute);
   datetime signal_end=open_time+InpSignalWindowBars*900;
   datetime retest_end=signal_end+InpRetestBars*900;
   if(bar.time<open_time || bar.time>=retest_end) return;

   if(g_breakout_direction!=0)
   {
      g_retest_age++;
      if(g_retest_age>InpRetestBars)
      {
         g_breakout_direction=0;
         return;
      }
      if(RetestAccepted(g_breakout_direction,bar))
      {
         int direction=g_breakout_direction;
         g_breakout_direction=0;
         EnterTrade(direction,bar);
      }
      return;
   }
   if(g_signal_consumed || bar.time>=signal_end) return;
   double buffer=InpBreakoutBufferDailyATR*g_daily_range_atr;
   int direction=0;
   if(bar.close>g_profile_vah+buffer) direction=1;
   else if(bar.close<g_profile_val-buffer) direction=-1;
   if(direction==0) return;
   if(InpRequireDirectionalCandle)
   {
      if(direction>0 && bar.close<=bar.open) return;
      if(direction<0 && bar.close>=bar.open) return;
   }
   if(InpMinimumRelativeVolume>0.0 && BarRelativeVolume(bar)<InpMinimumRelativeVolume) return;
   g_signal_consumed=true;
   if(InpEntryMode==OVA_DIRECT_CLOSE) EnterTrade(direction,bar);
   else
   {
      g_breakout_direction=direction;
      g_retest_age=0;
   }
}

void ManagePosition(const MqlDateTime &now_ny)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   int now_minutes=now_ny.hour*60+now_ny.min;
   int flat_minutes=InpFlatHour*60+InpFlatMinute;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   if(now_minutes>=flat_minutes)
   {
      if(!trade.PositionClose(ticket)) Print("OVA time exit failed: ",trade.ResultRetcodeDescription());
      return;
   }
   if(InpBreakEvenAtR<=0.0 || g_initial_risk<=0.0) return;
   long type=PositionGetInteger(POSITION_TYPE);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double favorable=(type==POSITION_TYPE_BUY ? current-entry : entry-current);
   if(favorable<InpBreakEvenAtR*g_initial_risk) return;
   bool improve=(type==POSITION_TYPE_BUY ? current_sl<entry : current_sl>entry);
   if(improve && !trade.PositionModify(ticket,NormalizePrice(entry),tp))
      Print("OVA break-even update failed: ",trade.ResultRetcodeDescription());
}

void ResetSession(const MqlDateTime &session_date)
{
   g_session_key=DateKey(session_date);
   g_profile_ready=false;
   g_traded_today=TradedOnDate(session_date);
   g_signal_consumed=false;
   g_breakout_direction=0;
   g_retest_age=0;
   g_profile_poc=0.0; g_profile_vah=0.0; g_profile_val=0.0;
   g_daily_range_atr=0.0;
   g_initial_risk=0.0;
   DeleteProfileObjects();
   if(!(bool)MQLInfoInteger(MQL_TESTER)) Comment("");
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_ny;
   TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(DateKey(now_ny)!=g_session_key) ResetSession(now_ny);
   ManagePosition(now_ny);
   datetime current_m15=iTime(_Symbol,PERIOD_M15,0);
   bool new_bar=(current_m15>0 && current_m15!=g_last_m15_bar);
   if(!new_bar) return;
   g_last_m15_bar=current_m15;
   if(g_traded_today) return;
   if(InpWeekdaysOnly && (now_ny.day_of_week==0 || now_ny.day_of_week==6)) return;
   datetime cash_open=NYTime(now_ny,InpCashOpenHour,InpCashOpenMinute);
   datetime process_start=cash_open+900;
   datetime process_end=cash_open+(InpSignalWindowBars+InpRetestBars+1)*900;
   if(now_server<process_start || now_server>=process_end) return;
   if(!g_profile_ready)
   {
      g_daily_range_atr=PreviousRTHRangeMedian(now_ny);
      if(g_daily_range_atr<=0.0 || !BuildOvernightProfile(now_ny)) return;
   }
   EvaluateClosedBar(now_ny);
}

int OnInit()
{
   if(InpProfilePreviousDayHour<0 || InpProfilePreviousDayHour>23 ||
      InpProfilePreviousDayMinute<0 || InpProfilePreviousDayMinute>59 ||
      InpCashOpenHour<0 || InpCashOpenHour>23 || InpCashOpenMinute<0 || InpCashOpenMinute>59 ||
      InpSignalWindowBars<1 || InpSignalWindowBars>12 || InpProfileBins<12 || InpProfileBins>200 ||
      InpValueAreaPercent<50.0 || InpValueAreaPercent>95.0 || InpMinimumProfileBars<50 ||
      InpRelativeVolumeLookback<2 || InpRetestBars<1 || InpRetestBars>12 ||
      InpDailyRangeLookback<14 || InpATRStopMultiple<=0.0 || InpMaximumStopDailyATR<=0.0 ||
      InpRewardRisk<=0.0 || InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   g_last_m15_bar=iTime(_Symbol,PERIOD_M15,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   DeleteProfileObjects();
   if(!(bool)MQLInfoInteger(MQL_TESTER)) Comment("");
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
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<40.0 || profit<=0.0 || pf<1.02 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/100.0))*MathMin(pf,3.0);
}
