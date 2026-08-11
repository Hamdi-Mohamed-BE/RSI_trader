#property copyright "Evidence-driven opening range breakout research EA"
#property version   "1.10"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_ORB_SESSION_ZONE
{
   ORB_NEW_YORK=0,
   ORB_UTC=1
};

enum ENUM_ORB_ENTRY_MODE
{
   ORB_DIRECT_BREAKOUT=0,
   ORB_BREAK_AND_RETEST=1
};

enum ENUM_ORB_STOP_MODE
{
   ORB_STOP_SIGNAL_CANDLE=0,
   ORB_STOP_OPPOSITE_RANGE=1
};

input group "Session and opening range"
input bool                  InpEnableTrading=true;
input ENUM_ORB_SESSION_ZONE InpSessionZone=ORB_NEW_YORK;
input int                   InpSessionHour=9;
input int                   InpSessionMinute=30;
input int                   InpOpeningRangeMinutes=15;
input int                   InpTradeWindowMinutes=120;
input int                   InpFlatHour=15;
input int                   InpFlatMinute=55;
input bool                  InpWeekdaysOnly=true;
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M5;

input group "Data and volume confirmation"
input int                   InpRelativeVolumeDays=20;
input double                InpMinOpeningRelativeVolume=0.80;
input int                   InpBarVolumeLookback=20;
input double                InpMinBreakoutRelativeVolume=1.10;
input ENUM_TIMEFRAMES       InpATRTimeframe=PERIOD_M15;
input int                   InpATRPeriod=14;
input double                InpMinRangeATR=0.35;
input double                InpMaxRangeATR=1.80;
input bool                  InpRequireVWAP=true;
input bool                  InpUseEMATrend=true;
input int                   InpFastEMA=20;
input int                   InpSlowEMA=50;

input group "Tick-activity volume profile (known at range close)"
input bool                  InpUseProfileValueArea=false;
input bool                  InpUseProfilePOCBias=false;
input bool                  InpUseProfileBoundaryLVN=false;
input int                   InpProfileStartHour=8;
input int                   InpProfileStartMinute=0;
input int                   InpProfileBins=48;
input double                InpProfileValueAreaPercent=70.0;
input double                InpMaxBoundaryNodeRatio=1.00;
input int                   InpMinimumProfileTicks=100;
input bool                  InpShowProfileLevels=true;

input group "Breakout and entry"
input ENUM_ORB_ENTRY_MODE   InpEntryMode=ORB_BREAK_AND_RETEST;
input double                InpBreakoutBodyMinimum=0.55;
input double                InpBreakoutBufferATR=0.03;
input int                   InpRetestBars=3;
input double                InpRetestToleranceATR=0.15;
input double                InpRetestBodyMinimum=0.30;

input group "Stops, target, and management"
input ENUM_ORB_STOP_MODE    InpStopMode=ORB_STOP_SIGNAL_CANDLE;
input double                InpStopBufferATR=0.10;
input double                InpMaximumStopATR=2.00;
input double                InpRewardRisk=2.00;
input double                InpBreakEvenAtR=1.00;
input double                InpTrailStartAtR=0.0;
input double                InpTrailCandleBufferATR=0.10;

input group "Risk and execution"
input double                InpRiskPercent=1.0;
input double                InpMaxSpreadRangePercent=12.0;
input int                   InpMaxDeviationPoints=30;
input long                  InpMagic=86080701;

input group "Broker clock"
input bool                  InpUseAutomaticLiveServerOffset=true;
input int                   InpTesterServerUTCOffsetHours=0;
input int                   InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_atr_handle=INVALID_HANDLE;
int g_fast_ema_handle=INVALID_HANDLE;
int g_slow_ema_handle=INVALID_HANDLE;
datetime g_last_signal_bar=0;
int g_session_date_key=0;
bool g_range_ready=false;
bool g_traded_today=false;
double g_range_high=0.0;
double g_range_low=0.0;
double g_range_volume=0.0;
double g_opening_relative_volume=0.0;
double g_atr=0.0;
int g_breakout_direction=0;
int g_breakout_age=0;
double g_breakout_high=0.0;
double g_breakout_low=0.0;
double g_initial_risk=0.0;
bool g_profile_ready=false;
long g_profile_tick_count=0;
double g_profile_poc=0.0;
double g_profile_vah=0.0;
double g_profile_val=0.0;
double g_profile_long_node_ratio=0.0;
double g_profile_short_node_ratio=0.0;

bool ProfileFilterEnabled()
{
   return InpUseProfileValueArea || InpUseProfilePOCBias || InpUseProfileBoundaryLVN;
}

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=1; p.hour=12;
   datetime first=StructToTime(p);
   TimeToStruct(first,p);
   return 1+((7-p.day_of_week)%7)+(occurrence-1)*7;
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

datetime ServerToSession(const datetime server_time)
{
   datetime utc=server_time-ServerUTCOffsetSeconds();
   if(InpSessionZone==ORB_UTC) return utc;
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

datetime SessionToServer(const MqlDateTime &source)
{
   MqlDateTime session=source;
   datetime local=StructToTime(session);
   datetime utc=local;
   if(InpSessionZone==ORB_NEW_YORK)
   {
      int offset=(NewYorkDateUsesDST(source) ? -4 : -5);
      utc=local-offset*3600;
   }
   return utc+ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

void PreviousCalendarDay(MqlDateTime &p)
{
   p.hour=12; p.min=0; p.sec=0;
   datetime value=StructToTime(p)-86400;
   TimeToStruct(value,p);
}

datetime SessionAnchor(const MqlDateTime &session_date)
{
   MqlDateTime anchor=session_date;
   anchor.hour=InpSessionHour; anchor.min=InpSessionMinute; anchor.sec=0;
   return SessionToServer(anchor);
}

double Median(double &values[])
{
   int count=ArraySize(values);
   if(count<=0) return 0.0;
   ArraySort(values);
   if((count%2)==1) return values[count/2];
   return (values[count/2-1]+values[count/2])*0.5;
}

double NormalizePrice(const double price)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return price;
   return NormalizeDouble(MathRound(price/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
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
   double result=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,result)) return 0.0;
   double one_lot_loss=MathAbs(result);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/one_lot_loss);
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool TradedOnSessionDate(const MqlDateTime &session_date)
{
   MqlDateTime start=session_date;
   start.hour=0; start.min=0; start.sec=0;
   MqlDateTime finish=start;
   finish.hour=23; finish.min=59; finish.sec=59;
   if(!HistorySelect(SessionToServer(start),SessionToServer(finish))) return false;
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

double OpeningWindowVolume(const MqlDateTime &session_date,double &high,double &low,int &bars)
{
   datetime from=SessionAnchor(session_date);
   datetime to=from+InpOpeningRangeMinutes*60-1;
   MqlRates rates[];
   bars=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(bars<=0) return 0.0;
   high=-DBL_MAX; low=DBL_MAX;
   double volume=0.0;
   for(int i=0;i<bars;i++)
   {
      high=MathMax(high,rates[i].high);
      low=MathMin(low,rates[i].low);
      volume+=(double)rates[i].tick_volume;
   }
   return volume;
}

double PreviousOpeningVolumeMedian(const MqlDateTime &current_date)
{
   double samples[];
   int found=0;
   MqlDateTime candidate=current_date;
   int attempts=0;
   while(found<InpRelativeVolumeDays && attempts<InpRelativeVolumeDays*3+15)
   {
      PreviousCalendarDay(candidate);
      attempts++;
      if(InpWeekdaysOnly && (candidate.day_of_week==0 || candidate.day_of_week==6)) continue;
      double high=0.0,low=0.0; int bars=0;
      double volume=OpeningWindowVolume(candidate,high,low,bars);
      if(bars<MathMax(1,InpOpeningRangeMinutes/2) || volume<=0.0) continue;
      ArrayResize(samples,found+1);
      samples[found]=volume;
      found++;
   }
   return Median(samples);
}

string ProfileObjectName(const string suffix)
{
   return StringFormat("ORBVP_%I64d_%s_%s",InpMagic,_Symbol,suffix);
}

void DeleteProfileObjects()
{
   ObjectDelete(0,ProfileObjectName("POC"));
   ObjectDelete(0,ProfileObjectName("VAH"));
   ObjectDelete(0,ProfileObjectName("VAL"));
}

void DrawProfileLine(const string suffix,const double price,const color line_color,const ENUM_LINE_STYLE style)
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowProfileLevels || price<=0.0) return;
   string name=ProfileObjectName(suffix);
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_HLINE,0,0,price);
   ObjectSetDouble(0,name,OBJPROP_PRICE,price);
   ObjectSetInteger(0,name,OBJPROP_COLOR,line_color);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,(suffix=="POC" ? 2 : 1));
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetString(0,name,OBJPROP_TOOLTIP,"ORB tick-activity profile "+suffix);
}

void UpdateProfileDisplay()
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowProfileLevels || !g_profile_ready) return;
   DrawProfileLine("POC",g_profile_poc,clrOrange,STYLE_SOLID);
   DrawProfileLine("VAH",g_profile_vah,clrDodgerBlue,STYLE_DASH);
   DrawProfileLine("VAL",g_profile_val,clrDodgerBlue,STYLE_DASH);
   Comment("ORB tick-activity profile (broker quotes, not exchange volume)\n",
           "POC: ",DoubleToString(g_profile_poc,_Digits),
           "   VAH: ",DoubleToString(g_profile_vah,_Digits),
           "   VAL: ",DoubleToString(g_profile_val,_Digits),"\n",
           "Opening relative volume: ",DoubleToString(g_opening_relative_volume,2),
           "   profile ticks: ",(string)g_profile_tick_count,"\n",
           "OR-high node / average: ",DoubleToString(g_profile_long_node_ratio,2),
           "   OR-low node / average: ",DoubleToString(g_profile_short_node_ratio,2));
   ChartRedraw(0);
}

bool BuildTickActivityProfile(const MqlDateTime &session_date)
{
   g_profile_ready=false;
   g_profile_tick_count=0;
   g_profile_poc=0.0; g_profile_vah=0.0; g_profile_val=0.0;
   g_profile_long_node_ratio=0.0; g_profile_short_node_ratio=0.0;

   MqlDateTime profile_date=session_date;
   profile_date.hour=InpProfileStartHour;
   profile_date.min=InpProfileStartMinute;
   profile_date.sec=0;
   datetime profile_start=SessionToServer(profile_date);
   datetime range_end=SessionAnchor(session_date)+InpOpeningRangeMinutes*60;
   if(profile_start>=range_end) return false;

   MqlTick ticks[];
   ulong from_msc=(ulong)profile_start*1000;
   ulong to_msc=(ulong)range_end*1000-1;
   ResetLastError();
   int copied=CopyTicksRange(_Symbol,ticks,COPY_TICKS_ALL,from_msc,to_msc);
   if(copied<InpMinimumProfileTicks)
   {
      Print("ORB profile unavailable: ",copied," ticks from ",
            TimeToString(profile_start,TIME_DATE|TIME_MINUTES)," to ",
            TimeToString(range_end,TIME_DATE|TIME_MINUTES),"; error ",GetLastError());
      return false;
   }

   double prices[];
   ArrayResize(prices,copied);
   int usable=0;
   double profile_low=DBL_MAX,profile_high=-DBL_MAX;
   for(int i=0;i<copied;i++)
   {
      double price=0.0;
      if(ticks[i].bid>0.0 && ticks[i].ask>0.0) price=(ticks[i].bid+ticks[i].ask)*0.5;
      else if(ticks[i].last>0.0) price=ticks[i].last;
      else if(ticks[i].bid>0.0) price=ticks[i].bid;
      else if(ticks[i].ask>0.0) price=ticks[i].ask;
      if(price<=0.0 || !MathIsValidNumber(price)) continue;
      prices[usable++]=price;
      profile_low=MathMin(profile_low,price);
      profile_high=MathMax(profile_high,price);
   }
   if(usable<InpMinimumProfileTicks || profile_high<=profile_low) return false;
   ArrayResize(prices,usable);

   int bins=InpProfileBins;
   double width=(profile_high-profile_low)/(double)bins;
   if(width<=0.0) return false;
   double activity[];
   ArrayResize(activity,bins);
   ArrayInitialize(activity,0.0);
   for(int i=0;i<usable;i++)
   {
      int index=(int)MathFloor((prices[i]-profile_low)/width);
      if(index<0) index=0;
      if(index>=bins) index=bins-1;
      activity[index]+=1.0;
   }

   int poc_index=0;
   double total=0.0;
   for(int i=0;i<bins;i++)
   {
      total+=activity[i];
      if(activity[i]>activity[poc_index]) poc_index=i;
   }
   if(total<=0.0) return false;

   int value_low=poc_index,value_high=poc_index;
   double included=activity[poc_index];
   double target=total*InpProfileValueAreaPercent/100.0;
   while(included<target && (value_low>0 || value_high<bins-1))
   {
      double next_low=(value_low>0 ? activity[value_low-1] : -1.0);
      double next_high=(value_high<bins-1 ? activity[value_high+1] : -1.0);
      if(next_high>=next_low && value_high<bins-1)
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

   int high_index=(int)MathFloor((g_range_high-profile_low)/width);
   int low_index=(int)MathFloor((g_range_low-profile_low)/width);
   high_index=MathMax(0,MathMin(bins-1,high_index));
   low_index=MathMax(0,MathMin(bins-1,low_index));
   double average=total/(double)bins;

   g_profile_tick_count=usable;
   g_profile_poc=NormalizePrice(profile_low+(poc_index+0.5)*width);
   g_profile_val=NormalizePrice(profile_low+value_low*width);
   g_profile_vah=NormalizePrice(profile_low+(value_high+1)*width);
   g_profile_long_node_ratio=(average>0.0 ? activity[high_index]/average : 0.0);
   g_profile_short_node_ratio=(average>0.0 ? activity[low_index]/average : 0.0);
   g_profile_ready=true;
   UpdateProfileDisplay();
   return true;
}

bool ProfileAllows(const int direction,const double breakout_close)
{
   if(!ProfileFilterEnabled()) return true;
   if(!g_profile_ready) return false;
   if(InpUseProfileValueArea)
   {
      if(direction>0 && breakout_close<=g_profile_vah) return false;
      if(direction<0 && breakout_close>=g_profile_val) return false;
   }
   if(InpUseProfilePOCBias)
   {
      double midpoint=(g_range_high+g_range_low)*0.5;
      if(direction>0 && g_profile_poc>midpoint) return false;
      if(direction<0 && g_profile_poc<midpoint) return false;
   }
   if(InpUseProfileBoundaryLVN)
   {
      double ratio=(direction>0 ? g_profile_long_node_ratio : g_profile_short_node_ratio);
      if(ratio>InpMaxBoundaryNodeRatio) return false;
   }
   return true;
}

bool LatestIndicatorValue(const int handle,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,1,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
}

bool BuildOpeningRange(const MqlDateTime &session_date)
{
   int bars=0;
   g_range_volume=OpeningWindowVolume(session_date,g_range_high,g_range_low,bars);
   if(bars<MathMax(1,InpOpeningRangeMinutes/2) || g_range_volume<=0.0 || g_range_high<=g_range_low)
      return false;
   if((ProfileFilterEnabled() || InpShowProfileLevels) && !g_profile_ready)
   {
      bool profile_built=BuildTickActivityProfile(session_date);
      if(ProfileFilterEnabled() && !profile_built) return false;
   }
   if(!LatestIndicatorValue(g_atr_handle,g_atr)) return false;
   double median=PreviousOpeningVolumeMedian(session_date);
   if(median<=0.0) return false;
   g_opening_relative_volume=g_range_volume/median;
   UpdateProfileDisplay();
   double width=g_range_high-g_range_low;
   double ratio=width/g_atr;
   if(ratio<InpMinRangeATR || ratio>InpMaxRangeATR) return false;
   if(g_opening_relative_volume<InpMinOpeningRelativeVolume) return false;
   g_range_ready=true;
   return true;
}

double CandleBodyRatio(const MqlRates &bar)
{
   double width=bar.high-bar.low;
   return (width>0.0 ? MathAbs(bar.close-bar.open)/width : 0.0);
}

double BarRelativeVolume(const MqlRates &signal)
{
   int seconds=PeriodSeconds(InpSignalTimeframe);
   if(seconds<=0) return 0.0;
   MqlRates prior[];
   datetime from=signal.time-(InpBarVolumeLookback+5)*seconds;
   int count=CopyRates(_Symbol,InpSignalTimeframe,from,signal.time-1,prior);
   if(count<=0) return 0.0;
   int use=MathMin(count,InpBarVolumeLookback);
   double samples[]; ArrayResize(samples,use);
   for(int i=0;i<use;i++) samples[i]=(double)prior[count-use+i].tick_volume;
   double median=Median(samples);
   return (median>0.0 ? (double)signal.tick_volume/median : 0.0);
}

double SessionVWAP(const datetime from,const datetime through)
{
   MqlRates rates[];
   int count=CopyRates(_Symbol,InpSignalTimeframe,from,through,rates);
   if(count<=0) return 0.0;
   double weighted=0.0,volume=0.0;
   for(int i=0;i<count;i++)
   {
      double v=(double)rates[i].tick_volume;
      weighted+=((rates[i].high+rates[i].low+rates[i].close)/3.0)*v;
      volume+=v;
   }
   return (volume>0.0 ? weighted/volume : 0.0);
}

bool TrendAllows(const int direction)
{
   if(!InpUseEMATrend) return true;
   double fast=0.0,slow=0.0;
   if(!LatestIndicatorValue(g_fast_ema_handle,fast) || !LatestIndicatorValue(g_slow_ema_handle,slow)) return false;
   return (direction>0 ? fast>slow : fast<slow);
}

bool SpreadOK()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || g_range_high<=g_range_low) return false;
   double spread=tick.ask-tick.bid;
   return spread/(g_range_high-g_range_low)*100.0<=InpMaxSpreadRangePercent;
}

bool EnterTrade(const int direction,const MqlRates &signal)
{
   if(!InpEnableTrading || g_traded_today || !SpreadOK()) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double buffer=InpStopBufferATR*g_atr;
   double stop=0.0;
   if(InpStopMode==ORB_STOP_OPPOSITE_RANGE)
      stop=(direction>0 ? g_range_low-buffer : g_range_high+buffer);
   else
      stop=(direction>0 ? signal.low-buffer : signal.high+buffer);
   stop=NormalizePrice(stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || risk>InpMaximumStopATR*g_atr) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0)
   {
      Print("ORB entry skipped: calculated risk size is below the broker minimum or contract data is missing.");
      return false;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=StringFormat("ORB RV %.2f BV %.2f",g_opening_relative_volume,BarRelativeVolume(signal));
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent)
   {
      Print("ORB entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_traded_today=true;
   g_initial_risk=risk;
   return true;
}

bool IsRetest(const int direction,const MqlRates &bar)
{
   double tolerance=InpRetestToleranceATR*g_atr;
   if(CandleBodyRatio(bar)<InpRetestBodyMinimum) return false;
   if(direction>0)
      return bar.low<=g_range_high+tolerance && bar.low>=g_range_high-2.0*tolerance &&
             bar.close>=g_range_high && bar.close>bar.open;
   return bar.high>=g_range_low-tolerance && bar.high<=g_range_low+2.0*tolerance &&
          bar.close<=g_range_low && bar.close<bar.open;
}

void EvaluateClosedSignalBar(const MqlDateTime &session_date,const datetime range_start,
                             const datetime range_end,const datetime trade_end)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,bars)!=1) return;
   MqlRates bar=bars[0];
   if(bar.time<range_end || bar.time>=trade_end) return;

   if(g_breakout_direction!=0)
   {
      g_breakout_age++;
      if(g_breakout_age>InpRetestBars)
      {
         g_breakout_direction=0;
         return;
      }
      if(IsRetest(g_breakout_direction,bar))
      {
         int direction=g_breakout_direction;
         g_breakout_direction=0;
         EnterTrade(direction,bar);
      }
      return;
   }

   if(CandleBodyRatio(bar)<InpBreakoutBodyMinimum) return;
   double bar_relvol=BarRelativeVolume(bar);
   if(bar_relvol<InpMinBreakoutRelativeVolume) return;
   double buffer=InpBreakoutBufferATR*g_atr;
   int direction=0;
   if(bar.close>g_range_high+buffer && bar.close>bar.open) direction=1;
   else if(bar.close<g_range_low-buffer && bar.close<bar.open) direction=-1;
   if(direction==0 || !TrendAllows(direction) || !ProfileAllows(direction,bar.close)) return;
   if(InpRequireVWAP)
   {
      double vwap=SessionVWAP(range_start,bar.time+PeriodSeconds(InpSignalTimeframe)-1);
      if(vwap<=0.0 || (direction>0 && bar.close<=vwap) || (direction<0 && bar.close>=vwap)) return;
   }
   if(InpEntryMode==ORB_DIRECT_BREAKOUT)
      EnterTrade(direction,bar);
   else
   {
      g_breakout_direction=direction;
      g_breakout_age=0;
      g_breakout_high=bar.high;
      g_breakout_low=bar.low;
   }
}

void ResetSession(const MqlDateTime &session_date)
{
   g_session_date_key=DateKey(session_date);
   g_range_ready=false;
   g_traded_today=TradedOnSessionDate(session_date);
   g_range_high=0.0; g_range_low=0.0; g_range_volume=0.0;
   g_opening_relative_volume=0.0; g_atr=0.0;
   g_breakout_direction=0; g_breakout_age=0;
   g_profile_ready=false; g_profile_tick_count=0;
   g_profile_poc=0.0; g_profile_vah=0.0; g_profile_val=0.0;
   g_profile_long_node_ratio=0.0; g_profile_short_node_ratio=0.0;
   DeleteProfileObjects();
   if(!(bool)MQLInfoInteger(MQL_TESTER)) Comment("");
}

void ManagePosition(const MqlDateTime &now_session,const bool new_signal_bar)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   if(!PositionSelectByTicket(ticket)) return;
   int now_minutes=now_session.hour*60+now_session.min;
   int flat_minutes=InpFlatHour*60+InpFlatMinute;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(now_minutes>=flat_minutes)
   {
      if(!trade.PositionClose(ticket))
         Print("ORB time exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return;
   }
   long type=PositionGetInteger(POSITION_TYPE);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double risk=g_initial_risk;
   if(risk<=0.0 && current_sl>0.0) risk=MathAbs(entry-current_sl);
   if(risk<=0.0) return;
   double profit_distance=(type==POSITION_TYPE_BUY ? current-entry : entry-current);
   double candidate=current_sl;
   if(InpBreakEvenAtR>0.0 && profit_distance>=InpBreakEvenAtR*risk)
   {
      if(type==POSITION_TYPE_BUY && (candidate<=0.0 || candidate<entry)) candidate=entry;
      if(type==POSITION_TYPE_SELL && (candidate<=0.0 || candidate>entry)) candidate=entry;
   }
   if(new_signal_bar && InpTrailStartAtR>0.0 && profit_distance>=InpTrailStartAtR*risk)
   {
      MqlRates closed[]; ArraySetAsSeries(closed,true);
      if(CopyRates(_Symbol,InpSignalTimeframe,1,1,closed)==1)
      {
         double trail=(type==POSITION_TYPE_BUY ? closed[0].low-InpTrailCandleBufferATR*g_atr
                                                : closed[0].high+InpTrailCandleBufferATR*g_atr);
         trail=NormalizePrice(trail);
         if(type==POSITION_TYPE_BUY && trail>candidate && trail<tick.bid) candidate=trail;
         if(type==POSITION_TYPE_SELL && (candidate<=0.0 || trail<candidate) && trail>tick.ask) candidate=trail;
      }
   }
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(candidate>0.0 && MathAbs(candidate-current_sl)>=MathMax(tick_size,SymbolInfoDouble(_Symbol,SYMBOL_POINT)))
   {
      if(!trade.PositionModify(ticket,NormalizePrice(candidate),tp))
         Print("ORB stop update failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   }
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_session; TimeToStruct(ServerToSession(now_server),now_session);
   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   bool new_bar=(current_bar>0 && current_bar!=g_last_signal_bar);
   if(new_bar) g_last_signal_bar=current_bar;
   if(DateKey(now_session)!=g_session_date_key) ResetSession(now_session);
   ManagePosition(now_session,new_bar);
   if(!new_bar || g_traded_today) return;
   if(InpWeekdaysOnly && (now_session.day_of_week==0 || now_session.day_of_week==6)) return;
   datetime range_start=SessionAnchor(now_session);
   datetime range_end=range_start+InpOpeningRangeMinutes*60;
   datetime trade_end=range_end+InpTradeWindowMinutes*60;
   if(now_server<range_end || now_server>=trade_end) return;
   if(!g_range_ready && !BuildOpeningRange(now_session)) return;
   EvaluateClosedSignalBar(now_session,range_start,range_end,trade_end);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpOpeningRangeMinutes<5 ||
      InpTradeWindowMinutes<5 || InpRelativeVolumeDays<2 || InpBarVolumeLookback<2 ||
      InpATRPeriod<2 || InpMinRangeATR<=0.0 || InpMaxRangeATR<=InpMinRangeATR ||
      InpBreakoutBodyMinimum<0.0 || InpBreakoutBodyMinimum>1.0 ||
      InpRetestBodyMinimum<0.0 || InpRetestBodyMinimum>1.0 ||
      InpRewardRisk<=0.0 || InpMaximumStopATR<=0.0 || InpFastEMA<2 || InpSlowEMA<=InpFastEMA ||
      InpProfileStartHour<0 || InpProfileStartHour>23 || InpProfileStartMinute<0 || InpProfileStartMinute>59 ||
      InpProfileBins<12 || InpProfileBins>200 || InpProfileValueAreaPercent<50.0 ||
      InpProfileValueAreaPercent>95.0 || InpMaxBoundaryNodeRatio<=0.0 || InpMinimumProfileTicks<10)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpATRTimeframe,InpATRPeriod);
   g_fast_ema_handle=iMA(_Symbol,InpATRTimeframe,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow_ema_handle=iMA(_Symbol,InpATRTimeframe,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_fast_ema_handle==INVALID_HANDLE || g_slow_ema_handle==INVALID_HANDLE)
      return INIT_FAILED;
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_fast_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_ema_handle);
   if(g_slow_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_ema_handle);
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
   if(trades<40.0 || profit<=0.0 || pf<1.05 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/80.0))*MathMin(pf,3.0);
}
