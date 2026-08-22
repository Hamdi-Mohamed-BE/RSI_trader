#ifndef GR_STRATEGY_ID
   #error GR_STRATEGY_ID must be defined by the EA wrapper
#endif
#ifndef GR_STRATEGY_NAME
   #define GR_STRATEGY_NAME "GoldenRock"
#endif
#ifndef GR_DEFAULT_MAGIC
   #define GR_DEFAULT_MAGIC 815000
#endif
#ifndef GR_DEFAULT_ENTRY_TF
   #define GR_DEFAULT_ENTRY_TF PERIOD_M15
#endif
#ifndef GR_DEFAULT_CONTEXT_TF
   #define GR_DEFAULT_CONTEXT_TF PERIOD_H1
#endif
#ifndef GR_DEFAULT_BIAS_TF
   #define GR_DEFAULT_BIAS_TF PERIOD_H4
#endif
#ifndef GR_DEFAULT_SESSION_FILTER
   #define GR_DEFAULT_SESSION_FILTER true
#endif

#include <Trade/Trade.mqh>

input group "Trading and risk"
input bool                 InpEnableTrading=true;
input long                 InpMagic=GR_DEFAULT_MAGIC;
input double               InpRiskPercent=1.0;
input bool                 InpAllowLong=true;
input bool                 InpAllowShort=true;
input int                  InpMaximumTradesPerDay=2;
input double               InpRewardRisk=2.0;
input double               InpMinimumTargetRR=1.0;

input group "Timeframes and sessions"
input ENUM_TIMEFRAMES      InpEntryTF=GR_DEFAULT_ENTRY_TF;
input ENUM_TIMEFRAMES      InpContextTF=GR_DEFAULT_CONTEXT_TF;
input ENUM_TIMEFRAMES      InpBiasTF=GR_DEFAULT_BIAS_TF;
input bool                 InpUseSessionFilter=GR_DEFAULT_SESSION_FILTER;
input int                  InpServerUTCOffsetHours=0;
input int                  InpSession1StartUTC=7;
input int                  InpSession1EndUTC=11;
input bool                 InpUseSecondSession=true;
input int                  InpSession2StartUTC=13;
input int                  InpSession2EndUTC=17;

input group "Signal definitions"
input int                  InpATRPeriod=14;
input int                  InpFastEMAPeriod=20;
input int                  InpSlowEMAPeriod=50;
input int                  InpADXPeriod=14;
input double               InpMinimumADX=18.0;
input int                  InpStructureLookback=20;
input int                  InpSwingStrength=2;
input double               InpMinimumBodyATR=0.25;
input double               InpMinimumWickFraction=0.35;
input double               InpPullbackToleranceATR=0.25;
input double               InpSweepBufferATR=0.05;
input double               InpBreakoutBufferATR=0.10;
input double               InpMaximumExtensionATR=1.50;
input int                  InpSetupExpiryBars=6;

input group "Stops and management"
input double               InpStopBufferATR=0.20;
input bool                 InpUseBreakEven=true;
input double               InpBreakEvenAtR=1.0;
input bool                 InpUseATRTrailing=true;
input double               InpTrailStartR=1.5;
input double               InpTrailATR=1.5;
input int                  InpMaximumHoldBars=96;

input group "Execution controls"
input double               InpMaximumSpreadPrice=1.00;
input int                  InpMaximumDeviationPoints=100;
input bool                 InpVerboseLog=false;

struct GRSignal
{
   int direction;
   double stop;
   double target;
   string reason;
};

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
int g_fast_bias_handle=INVALID_HANDLE;
int g_slow_bias_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;
int g_entry_ema_handle=INVALID_HANDLE;
datetime g_last_entry_bar=0;
int g_day_key=0;
int g_trades_today=0;

// Shared pending state. Every wrapper runs in its own EA instance, so state cannot
// leak between strategies or charts.
int g_state=0;
int g_pending_direction=0;
int g_pending_bars=0;
double g_pending_level=0.0;
double g_pending_extreme=0.0;
double g_zone_low=0.0;
double g_zone_high=0.0;

void GR_Log(const string text)
{
   if(InpVerboseLog) Print(GR_STRATEGY_NAME,": ",text);
}

int GR_DateKey(const datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return parts.year*10000+parts.mon*100+parts.day;
}

datetime GR_ToUTC(const datetime server_time)
{
   return server_time-(InpServerUTCOffsetHours*3600);
}

bool GR_HourInRange(const int hour,const int start_hour,const int end_hour)
{
   if(start_hour==end_hour) return true;
   if(start_hour<end_hour) return hour>=start_hour && hour<end_hour;
   return hour>=start_hour || hour<end_hour;
}

bool GR_InSession(const datetime server_time)
{
   if(!InpUseSessionFilter) return true;
   MqlDateTime parts;
   TimeToStruct(GR_ToUTC(server_time),parts);
   if(GR_HourInRange(parts.hour,InpSession1StartUTC,InpSession1EndUTC)) return true;
   if(InpUseSecondSession && GR_HourInRange(parts.hour,InpSession2StartUTC,InpSession2EndUTC)) return true;
   return false;
}

bool GR_IsNewBar()
{
   datetime current=iTime(_Symbol,InpEntryTF,0);
   if(current<=0 || current==g_last_entry_bar) return false;
   g_last_entry_bar=current;
   return true;
}

double GR_NormalizePrice(const double price)
{
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   return NormalizeDouble(MathRound(price/tick_size)*tick_size,digits);
}

double GR_NormalizeLots(const double raw_lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw_lots<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw_lots,maximum)+1e-12)/step)*step;
   if(lots<minimum) return 0.0;
   return NormalizeDouble(lots,8);
}

double GR_LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   if(MathAbs(one_lot_result)<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return GR_NormalizeLots(risk_cash/MathAbs(one_lot_result));
}

bool GR_SelectPosition(ulong &ticket)
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
   ticket=0;
   return false;
}

string GR_RiskKey(const ulong ticket)
{
   return "GRR_"+IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN))+"_"+
          IntegerToString((int)InpMagic)+"_"+IntegerToString((int)ticket);
}

bool GR_CopyRates(const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);
   return CopyRates(_Symbol,timeframe,0,count,rates)>=count;
}

double GR_BufferValue(const int handle,const int buffer,const int shift)
{
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,buffer,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

double GR_ATR()
{
   double value=GR_BufferValue(g_atr_handle,0,1);
   return value==EMPTY_VALUE ? 0.0 : value;
}

double GR_Highest(const MqlRates &rates[],const int first,const int last)
{
   int size=ArraySize(rates);
   int stop=MathMin(last,size-1);
   if(first<0 || first>stop) return 0.0;
   double value=rates[first].high;
   for(int index=first+1;index<=stop;index++) value=MathMax(value,rates[index].high);
   return value;
}

double GR_Lowest(const MqlRates &rates[],const int first,const int last)
{
   int size=ArraySize(rates);
   int stop=MathMin(last,size-1);
   if(first<0 || first>stop) return 0.0;
   double value=rates[first].low;
   for(int index=first+1;index<=stop;index++) value=MathMin(value,rates[index].low);
   return value;
}

double GR_Body(const MqlRates &bar)
{
   return MathAbs(bar.close-bar.open);
}

double GR_Range(const MqlRates &bar)
{
   return MathMax(bar.high-bar.low,SymbolInfoDouble(_Symbol,SYMBOL_POINT));
}

bool GR_BullishDisplacement(const MqlRates &rates[],const double atr)
{
   return rates[1].close>rates[1].open && GR_Body(rates[1])>=InpMinimumBodyATR*atr &&
          rates[1].close>rates[2].high;
}

bool GR_BearishDisplacement(const MqlRates &rates[],const double atr)
{
   return rates[1].close<rates[1].open && GR_Body(rates[1])>=InpMinimumBodyATR*atr &&
          rates[1].close<rates[2].low;
}

int GR_EMABias()
{
   double fast1=GR_BufferValue(g_fast_bias_handle,0,1);
   double fast3=GR_BufferValue(g_fast_bias_handle,0,3);
   double slow1=GR_BufferValue(g_slow_bias_handle,0,1);
   double adx=GR_BufferValue(g_adx_handle,0,1);
   if(fast1==EMPTY_VALUE || fast3==EMPTY_VALUE || slow1==EMPTY_VALUE || adx==EMPTY_VALUE) return 0;
   if(adx<InpMinimumADX) return 0;
   if(fast1>slow1 && fast1>fast3) return 1;
   if(fast1<slow1 && fast1<fast3) return -1;
   return 0;
}

bool GR_RecentSwingHigh(const MqlRates &rates[],double &price)
{
   int size=ArraySize(rates);
   int maximum=MathMin(InpStructureLookback,size-InpSwingStrength-1);
   for(int index=InpSwingStrength+1;index<=maximum;index++)
   {
      bool swing=true;
      for(int side=1;side<=InpSwingStrength;side++)
      {
         if(rates[index].high<=rates[index-side].high || rates[index].high<=rates[index+side].high)
         {
            swing=false;
            break;
         }
      }
      if(swing)
      {
         price=rates[index].high;
         return true;
      }
   }
   return false;
}

bool GR_RecentSwingLow(const MqlRates &rates[],double &price)
{
   int size=ArraySize(rates);
   int maximum=MathMin(InpStructureLookback,size-InpSwingStrength-1);
   for(int index=InpSwingStrength+1;index<=maximum;index++)
   {
      bool swing=true;
      for(int side=1;side<=InpSwingStrength;side++)
      {
         if(rates[index].low>=rates[index-side].low || rates[index].low>=rates[index+side].low)
         {
            swing=false;
            break;
         }
      }
      if(swing)
      {
         price=rates[index].low;
         return true;
      }
   }
   return false;
}

bool GR_SessionRangeForCurrentDay(const int start_utc,const int end_utc,double &high,double &low)
{
   MqlRates rates[];
   if(!GR_CopyRates(InpEntryTF,600,rates)) return false;
   datetime now_utc=GR_ToUTC(rates[1].time);
   int current_day=GR_DateKey(now_utc);
   high=-DBL_MAX;
   low=DBL_MAX;
   int found=0;
   for(int index=1;index<ArraySize(rates);index++)
   {
      datetime utc=GR_ToUTC(rates[index].time);
      if(GR_DateKey(utc)!=current_day) continue;
      MqlDateTime parts;
      TimeToStruct(utc,parts);
      if(!GR_HourInRange(parts.hour,start_utc,end_utc)) continue;
      high=MathMax(high,rates[index].high);
      low=MathMin(low,rates[index].low);
      found++;
   }
   return found>=4 && high>low;
}

void GR_ClearPending()
{
   g_state=0;
   g_pending_direction=0;
   g_pending_bars=0;
   g_pending_level=0.0;
   g_pending_extreme=0.0;
   g_zone_low=0.0;
   g_zone_high=0.0;
}

void GR_ResetSignal(GRSignal &signal)
{
   signal.direction=0;
   signal.stop=0.0;
   signal.target=0.0;
   signal.reason="";
}

void GR_FixedTarget(GRSignal &signal,const double entry)
{
   double risk=MathAbs(entry-signal.stop);
   if(risk<=0.0) return;
   if(signal.target<=0.0 || signal.direction*(signal.target-entry)/risk<InpMinimumTargetRR)
      signal.target=entry+signal.direction*InpRewardRisk*risk;
}

bool GR_OpenSignal(GRSignal &signal)
{
   if(signal.direction==0 || !InpEnableTrading) return false;
   if(signal.direction>0 && !InpAllowLong) return false;
   if(signal.direction<0 && !InpAllowShort) return false;
   if(g_trades_today>=InpMaximumTradesPerDay) return false;
   ulong existing=0;
   if(GR_SelectPosition(existing)) return false;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=signal.direction>0 ? tick.ask : tick.bid;
   if(entry<=0.0) return false;
   GR_FixedTarget(signal,entry);

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point,
                                   SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));
   if(signal.direction>0)
   {
      signal.stop=MathMin(signal.stop,tick.bid-minimum_distance);
      signal.target=MathMax(signal.target,tick.ask+minimum_distance);
   }
   else
   {
      signal.stop=MathMax(signal.stop,tick.ask+minimum_distance);
      signal.target=MathMin(signal.target,tick.bid-minimum_distance);
   }
   signal.stop=GR_NormalizePrice(signal.stop);
   signal.target=GR_NormalizePrice(signal.target);
   if((signal.direction>0 && signal.stop>=entry) || (signal.direction<0 && signal.stop<=entry)) return false;

   ENUM_ORDER_TYPE type=signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double lots=GR_LotsForRisk(type,entry,signal.stop);
   if(lots<=0.0)
   {
      GR_Log("Rejected: broker minimum volume exceeds risk budget.");
      return false;
   }
   bool opened=signal.direction>0
      ? g_trade.Buy(lots,_Symbol,0.0,signal.stop,signal.target,signal.reason)
      : g_trade.Sell(lots,_Symbol,0.0,signal.stop,signal.target,signal.reason);
   if(!opened)
   {
      GR_Log("Order failed: "+g_trade.ResultRetcodeDescription());
      return false;
   }
   ulong ticket=0;
   if(GR_SelectPosition(ticket))
   {
      double open_price=PositionGetDouble(POSITION_PRICE_OPEN);
      GlobalVariableSet(GR_RiskKey(ticket),MathAbs(open_price-signal.stop));
   }
   g_trades_today++;
   GR_ClearPending();
   return true;
}

void GR_ManagePosition()
{
   ulong ticket=0;
   if(!GR_SelectPosition(ticket)) return;
   long type=PositionGetInteger(POSITION_TYPE);
   int direction=type==POSITION_TYPE_BUY ? 1 : -1;
   double open_price=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double mark=direction>0 ? tick.bid : tick.ask;
   string key=GR_RiskKey(ticket);
   double initial_risk=GlobalVariableCheck(key) ? GlobalVariableGet(key) : MathAbs(open_price-stop);
   if(initial_risk<=0.0) return;
   double current_r=direction*(mark-open_price)/initial_risk;
   double new_stop=stop;

   if(InpUseBreakEven && current_r>=InpBreakEvenAtR)
   {
      if(direction>0 && (new_stop<open_price || new_stop==0.0)) new_stop=open_price;
      if(direction<0 && (new_stop>open_price || new_stop==0.0)) new_stop=open_price;
   }
   if(InpUseATRTrailing && current_r>=InpTrailStartR)
   {
      double atr=GR_ATR();
      if(atr>0.0)
      {
         double candidate=direction>0 ? mark-InpTrailATR*atr : mark+InpTrailATR*atr;
         if(direction>0 && candidate>new_stop) new_stop=candidate;
         if(direction<0 && (new_stop==0.0 || candidate<new_stop)) new_stop=candidate;
      }
   }
   new_stop=GR_NormalizePrice(new_stop);
   if(new_stop!=stop && ((direction>0 && new_stop<tick.bid) || (direction<0 && new_stop>tick.ask)))
      g_trade.PositionModify(ticket,new_stop,target);

   if(InpMaximumHoldBars>0)
   {
      int shift=iBarShift(_Symbol,InpEntryTF,opened,false);
      if(shift>=InpMaximumHoldBars)
      {
         g_trade.PositionClose(ticket);
         if(GlobalVariableCheck(key)) GlobalVariableDel(key);
      }
   }
}

bool GR_EvaluateTrend(GRSignal &signal,const MqlRates &entry[],const double atr)
{
   int bias=GR_EMABias();
   if(bias==0) return false;
   double ema1=GR_BufferValue(g_entry_ema_handle,0,1);
   double ema2=GR_BufferValue(g_entry_ema_handle,0,2);
   if(ema1==EMPTY_VALUE || ema2==EMPTY_VALUE) return false;
   bool long_pullback=entry[1].low<=ema1+InpPullbackToleranceATR*atr && entry[1].close>ema1 &&
                      entry[2].low<=ema2+InpPullbackToleranceATR*atr;
   bool short_pullback=entry[1].high>=ema1-InpPullbackToleranceATR*atr && entry[1].close<ema1 &&
                       entry[2].high>=ema2-InpPullbackToleranceATR*atr;
   if(bias>0 && long_pullback && entry[1].close>entry[1].open &&
      entry[1].close-entry[1].low>=InpMinimumBodyATR*atr &&
      entry[1].close-ema1<=InpMaximumExtensionATR*atr)
   {
      signal.direction=1;
      signal.stop=GR_Lowest(entry,1,5)-InpStopBufferATR*atr;
      signal.reason="GR01 trend pullback";
      return true;
   }
   if(bias<0 && short_pullback && entry[1].close<entry[1].open &&
      entry[1].high-entry[1].close>=InpMinimumBodyATR*atr &&
      ema1-entry[1].close<=InpMaximumExtensionATR*atr)
   {
      signal.direction=-1;
      signal.stop=GR_Highest(entry,1,5)+InpStopBufferATR*atr;
      signal.reason="GR01 trend pullback";
      return true;
   }
   return false;
}

bool GR_EvaluateBreakout(GRSignal &signal,const MqlRates &entry[],const double atr)
{
   if(g_state==1)
   {
      g_pending_bars--;
      bool retest=g_pending_direction>0
         ? entry[1].low<=g_pending_level+InpPullbackToleranceATR*atr && entry[1].close>g_pending_level && entry[1].close>entry[1].open
         : entry[1].high>=g_pending_level-InpPullbackToleranceATR*atr && entry[1].close<g_pending_level && entry[1].close<entry[1].open;
      if(retest)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0
            ? GR_Lowest(entry,1,3)-InpStopBufferATR*atr
            : GR_Highest(entry,1,3)+InpStopBufferATR*atr;
         signal.reason="GR02 breakout retest";
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   double high=GR_Highest(entry,2,InpStructureLookback+1);
   double low=GR_Lowest(entry,2,InpStructureLookback+1);
   if(high<=low || high-low<1.5*atr) return false;
   if(entry[1].close>high+InpBreakoutBufferATR*atr && entry[1].close>entry[1].open && GR_Body(entry[1])>=InpMinimumBodyATR*atr)
   {
      g_state=1; g_pending_direction=1; g_pending_level=high; g_pending_bars=InpSetupExpiryBars;
      GR_Log("Bullish breakout armed; waiting for retest.");
   }
   else if(entry[1].close<low-InpBreakoutBufferATR*atr && entry[1].close<entry[1].open && GR_Body(entry[1])>=InpMinimumBodyATR*atr)
   {
      g_state=1; g_pending_direction=-1; g_pending_level=low; g_pending_bars=InpSetupExpiryBars;
      GR_Log("Bearish breakout armed; waiting for retest.");
   }
   return false;
}

bool GR_EvaluateSweep(GRSignal &signal,const MqlRates &entry[],const double atr,const string label)
{
   if(g_state==1)
   {
      g_pending_bars--;
      bool confirmed=g_pending_direction>0 ? GR_BullishDisplacement(entry,atr) : GR_BearishDisplacement(entry,atr);
      if(confirmed)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0 ? g_pending_extreme-InpStopBufferATR*atr : g_pending_extreme+InpStopBufferATR*atr;
         signal.reason=label;
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   double high=GR_Highest(entry,2,InpStructureLookback+1);
   double low=GR_Lowest(entry,2,InpStructureLookback+1);
   double upper_wick=entry[1].high-MathMax(entry[1].open,entry[1].close);
   double lower_wick=MathMin(entry[1].open,entry[1].close)-entry[1].low;
   if(entry[1].high>high+InpSweepBufferATR*atr && entry[1].close<high && upper_wick/GR_Range(entry[1])>=InpMinimumWickFraction)
   {
      g_state=1; g_pending_direction=-1; g_pending_level=high; g_pending_extreme=entry[1].high; g_pending_bars=InpSetupExpiryBars;
   }
   else if(entry[1].low<low-InpSweepBufferATR*atr && entry[1].close>low && lower_wick/GR_Range(entry[1])>=InpMinimumWickFraction)
   {
      g_state=1; g_pending_direction=1; g_pending_level=low; g_pending_extreme=entry[1].low; g_pending_bars=InpSetupExpiryBars;
   }
   return false;
}

bool GR_EvaluateMTF(GRSignal &signal,const MqlRates &entry[],const MqlRates &context[],const double atr)
{
   int bias=GR_EMABias();
   if(bias==0) return false;
   double context_high=GR_Highest(context,1,InpStructureLookback);
   double context_low=GR_Lowest(context,1,InpStructureLookback);
   double midpoint=(context_high+context_low)/2.0;
   double local_high=GR_Highest(entry,2,7);
   double local_low=GR_Lowest(entry,2,7);
   if(bias>0 && entry[1].low<local_low && entry[1].close>entry[2].high && entry[1].close<=midpoint &&
      GR_Body(entry[1])>=InpMinimumBodyATR*atr)
   {
      signal.direction=1;
      signal.stop=entry[1].low-InpStopBufferATR*atr;
      signal.target=context_high;
      signal.reason="GR04 HTF discount reclaim";
      return true;
   }
   if(bias<0 && entry[1].high>local_high && entry[1].close<entry[2].low && entry[1].close>=midpoint &&
      GR_Body(entry[1])>=InpMinimumBodyATR*atr)
   {
      signal.direction=-1;
      signal.stop=entry[1].high+InpStopBufferATR*atr;
      signal.target=context_low;
      signal.reason="GR04 HTF premium reclaim";
      return true;
   }
   return false;
}

bool GR_EvaluateSMC(GRSignal &signal,const MqlRates &entry[],const MqlRates &context[],const double atr)
{
   if(g_state==2)
   {
      g_pending_bars--;
      bool touched=entry[1].low<=g_zone_high && entry[1].high>=g_zone_low;
      bool confirmed=g_pending_direction>0
         ? touched && entry[1].close>g_zone_high && entry[1].close>entry[1].open
         : touched && entry[1].close<g_zone_low && entry[1].close<entry[1].open;
      if(confirmed)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0 ? g_zone_low-InpStopBufferATR*atr : g_zone_high+InpStopBufferATR*atr;
         signal.reason="GR06 BOS order-block retest";
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   double previous_high=GR_Highest(context,2,InpStructureLookback+1);
   double previous_low=GR_Lowest(context,2,InpStructureLookback+1);
   int direction=0;
   if(context[1].close>previous_high && context[1].close>context[1].open) direction=1;
   else if(context[1].close<previous_low && context[1].close<context[1].open) direction=-1;
   if(direction==0) return false;
   for(int index=2;index<=MathMin(10,ArraySize(context)-1);index++)
   {
      bool opposing=direction>0 ? context[index].close<context[index].open : context[index].close>context[index].open;
      if(!opposing) continue;
      g_zone_low=context[index].low;
      g_zone_high=context[index].high;
      g_state=2; g_pending_direction=direction; g_pending_bars=InpSetupExpiryBars*4;
      return false;
   }
   return false;
}

bool GR_EvaluateICT(GRSignal &signal,const MqlRates &entry[],const double atr)
{
   double asia_high=0.0,asia_low=0.0;
   if(!GR_SessionRangeForCurrentDay(0,6,asia_high,asia_low)) return false;
   if(g_state==1)
   {
      g_pending_bars--;
      bool displacement=g_pending_direction>0 ? GR_BullishDisplacement(entry,atr) : GR_BearishDisplacement(entry,atr);
      bool fair_value_gap=g_pending_direction>0 ? entry[1].low>entry[3].high : entry[1].high<entry[3].low;
      if(displacement && fair_value_gap)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0 ? g_pending_extreme-InpStopBufferATR*atr : g_pending_extreme+InpStopBufferATR*atr;
         signal.target=g_pending_direction>0 ? asia_high : asia_low;
         signal.reason="GR07 killzone sweep FVG";
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   if(entry[1].low<asia_low-InpSweepBufferATR*atr && entry[1].close>asia_low)
   {
      g_state=1; g_pending_direction=1; g_pending_extreme=entry[1].low; g_pending_bars=InpSetupExpiryBars;
   }
   else if(entry[1].high>asia_high+InpSweepBufferATR*atr && entry[1].close<asia_high)
   {
      g_state=1; g_pending_direction=-1; g_pending_extreme=entry[1].high; g_pending_bars=InpSetupExpiryBars;
   }
   return false;
}

bool GR_EvaluateCRT(GRSignal &signal,const MqlRates &entry[],const double atr)
{
   MqlRates reference=entry[2];
   MqlRates manipulation=entry[1];
   if(reference.high-reference.low<1.0*atr) return false;
   double upper_wick=manipulation.high-MathMax(manipulation.open,manipulation.close);
   double lower_wick=MathMin(manipulation.open,manipulation.close)-manipulation.low;
   if(manipulation.low<reference.low-InpSweepBufferATR*atr && manipulation.close>reference.low &&
      manipulation.close>manipulation.open && lower_wick/GR_Range(manipulation)>=InpMinimumWickFraction)
   {
      signal.direction=1;
      signal.stop=manipulation.low-InpStopBufferATR*atr;
      signal.target=reference.high;
      signal.reason="GR08 CRT low manipulation";
      return true;
   }
   if(manipulation.high>reference.high+InpSweepBufferATR*atr && manipulation.close<reference.high &&
      manipulation.close<manipulation.open && upper_wick/GR_Range(manipulation)>=InpMinimumWickFraction)
   {
      signal.direction=-1;
      signal.stop=manipulation.high+InpStopBufferATR*atr;
      signal.target=reference.low;
      signal.reason="GR08 CRT high manipulation";
      return true;
   }
   return false;
}

bool GR_EvaluateSNR(GRSignal &signal,const MqlRates &entry[],const MqlRates &context[],const double atr)
{
   double resistance=0.0,support=0.0;
   if(!GR_RecentSwingHigh(context,resistance) || !GR_RecentSwingLow(context,support)) return false;
   if(g_state==1)
   {
      g_pending_bars--;
      bool shift=g_pending_direction>0 ? GR_BullishDisplacement(entry,atr) : GR_BearishDisplacement(entry,atr);
      bool gap=g_pending_direction>0 ? entry[1].low>entry[3].high : entry[1].high<entry[3].low;
      if(shift && gap)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0 ? g_pending_extreme-InpStopBufferATR*atr : g_pending_extreme+InpStopBufferATR*atr;
         signal.target=g_pending_direction>0 ? resistance : support;
         signal.reason="GR09 SNR sweep MSS FVG";
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   if(entry[1].low<support-InpSweepBufferATR*atr && entry[1].close>support)
   {
      g_state=1; g_pending_direction=1; g_pending_extreme=entry[1].low; g_pending_bars=InpSetupExpiryBars;
   }
   else if(entry[1].high>resistance+InpSweepBufferATR*atr && entry[1].close<resistance)
   {
      g_state=1; g_pending_direction=-1; g_pending_extreme=entry[1].high; g_pending_bars=InpSetupExpiryBars;
   }
   return false;
}

bool GR_EvaluateSMCSweep(GRSignal &signal,const MqlRates &entry[],const MqlRates &context[],const double atr)
{
   double context_high=GR_Highest(context,2,InpStructureLookback+1);
   double context_low=GR_Lowest(context,2,InpStructureLookback+1);
   if(g_state==2)
   {
      g_pending_bars--;
      bool touched=entry[1].low<=g_zone_high && entry[1].high>=g_zone_low;
      bool confirmed=g_pending_direction>0
         ? touched && entry[1].close>g_zone_high && entry[1].close>entry[1].open
         : touched && entry[1].close<g_zone_low && entry[1].close<entry[1].open;
      if(confirmed)
      {
         signal.direction=g_pending_direction;
         signal.stop=g_pending_direction>0 ? g_pending_extreme-InpStopBufferATR*atr : g_pending_extreme+InpStopBufferATR*atr;
         signal.target=g_pending_direction>0 ? context_high : context_low;
         signal.reason="GR10 sweep BOS retest";
         return true;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   if(g_state==1)
   {
      g_pending_bars--;
      bool displacement=g_pending_direction>0 ? GR_BullishDisplacement(entry,atr) : GR_BearishDisplacement(entry,atr);
      if(displacement)
      {
         MqlRates order_block=entry[2];
         g_zone_low=order_block.low;
         g_zone_high=order_block.high;
         g_state=2;
         g_pending_bars=InpSetupExpiryBars;
         return false;
      }
      if(g_pending_bars<=0) GR_ClearPending();
      return false;
   }
   double local_high=GR_Highest(entry,2,InpStructureLookback+1);
   double local_low=GR_Lowest(entry,2,InpStructureLookback+1);
   if(entry[1].low<local_low-InpSweepBufferATR*atr && entry[1].close>local_low)
   {
      g_state=1; g_pending_direction=1; g_pending_extreme=entry[1].low; g_pending_bars=InpSetupExpiryBars;
   }
   else if(entry[1].high>local_high+InpSweepBufferATR*atr && entry[1].close<local_high)
   {
      g_state=1; g_pending_direction=-1; g_pending_extreme=entry[1].high; g_pending_bars=InpSetupExpiryBars;
   }
   return false;
}

bool GR_Evaluate(GRSignal &signal)
{
   GR_ResetSignal(signal);
   int need=MathMax(InpStructureLookback+10,80);
   MqlRates entry[],context[];
   if(!GR_CopyRates(InpEntryTF,need,entry) || !GR_CopyRates(InpContextTF,need,context)) return false;
   double atr=GR_ATR();
   if(atr<=0.0) return false;

   switch(GR_STRATEGY_ID)
   {
      case 1:  return GR_EvaluateTrend(signal,entry,atr);
      case 2:  return GR_EvaluateBreakout(signal,entry,atr);
      case 3:  return GR_EvaluateSweep(signal,entry,atr,"GR03 liquidity sweep MSS");
      case 4:  return GR_EvaluateMTF(signal,entry,context,atr);
      case 6:  return GR_EvaluateSMC(signal,entry,context,atr);
      case 7:  return GR_EvaluateICT(signal,entry,atr);
      case 8:  return GR_EvaluateCRT(signal,entry,atr);
      case 9:  return GR_EvaluateSNR(signal,entry,context,atr);
      case 10: return GR_EvaluateSMCSweep(signal,entry,context,atr);
   }
   return false;
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpRewardRisk<=0.0 ||
      InpStructureLookback<5 || InpSwingStrength<1)
      return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_atr_handle=iATR(_Symbol,InpEntryTF,InpATRPeriod);
   g_fast_bias_handle=iMA(_Symbol,InpBiasTF,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_slow_bias_handle=iMA(_Symbol,InpBiasTF,InpSlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_adx_handle=iADX(_Symbol,InpBiasTF,InpADXPeriod);
   g_entry_ema_handle=iMA(_Symbol,InpEntryTF,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_fast_bias_handle==INVALID_HANDLE ||
      g_slow_bias_handle==INVALID_HANDLE || g_adx_handle==INVALID_HANDLE ||
      g_entry_ema_handle==INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_fast_bias_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_bias_handle);
   if(g_slow_bias_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_bias_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_entry_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_entry_ema_handle);
   Comment("");
}

void OnTick()
{
   GR_ManagePosition();
   if(!GR_IsNewBar()) return;

   datetime closed_bar=iTime(_Symbol,InpEntryTF,1);
   int today=GR_DateKey(GR_ToUTC(closed_bar));
   if(today!=g_day_key)
   {
      g_day_key=today;
      g_trades_today=0;
      GR_ClearPending();
   }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double spread=tick.ask-tick.bid;
   if(InpMaximumSpreadPrice>0.0 && spread>InpMaximumSpreadPrice)
   {
      GR_Log("Rejected: spread exceeds price-unit limit.");
      return;
   }
   if(!GR_InSession(closed_bar)) return;
   ulong ticket=0;
   if(GR_SelectPosition(ticket)) return;
   if(g_trades_today>=InpMaximumTradesPerDay) return;

   GRSignal signal;
   if(GR_Evaluate(signal)) GR_OpenSignal(signal);
   Comment(GR_STRATEGY_NAME,"\nStrategy ID: ",GR_STRATEGY_ID,"\nPending state: ",g_state,
           "\nTrades today: ",g_trades_today,"/",InpMaximumTradesPerDay);
}
