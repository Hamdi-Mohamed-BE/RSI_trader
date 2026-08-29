#property copyright "Transparent research proxy based on the public Patrick Nill interview"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_PBD_SETUP_MODE
{
   PBD_RECLAIMS_ONLY=0,
   PBD_BREAKOUT_RETESTS_ONLY=1,
   PBD_RECLAIMS_AND_BREAKOUTS=2
};

enum ENUM_PBD_STATE
{
   PBD_IDLE=0,
   PBD_LOW_RECLAIM_CONFIRM=1,
   PBD_HIGH_RECLAIM_CONFIRM=2,
   PBD_UP_BREAK_WAIT=3,
   PBD_UP_RETEST_CONFIRM=4,
   PBD_DOWN_BREAK_WAIT=5,
   PBD_DOWN_RETEST_CONFIRM=6
};

input group "Fair-value zone"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input int InpATRPeriod=14;
input int InpRangeBars=20;
input int InpImpulseBars=6;
input double InpMinimumImpulseATR=1.50;
input double InpMinimumRangeATR=0.75;
input double InpMaximumRangeATR=3.00;
input int InpMinimumAlternatingTouches=3;
input double InpTouchToleranceFraction=0.15;
input bool InpAllowDProfile=false;
input int InpZoneMaximumBars=192;

input group "Entry confirmation"
input ENUM_PBD_SETUP_MODE InpSetupMode=PBD_RECLAIMS_AND_BREAKOUTS;
input double InpMinimumSweepATR=0.05;
input double InpBreakoutBufferATR=0.05;
input double InpRetestToleranceATR=0.20;
input double InpMaximumRetestDepthFraction=0.35;
input int InpConfirmationBars=3;
input bool InpRequireBreakoutRetest=true;
input bool InpFollowImpulseOnly=false;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

input group "Optional higher-timeframe context"
input bool InpUseH4TrendFilter=false;
input int InpH4EMAPeriod=50;

input group "New York daytime filter"
input bool InpUseNewYorkSession=false;
input int InpNewYorkStartHour=2;
input int InpNewYorkEndHour=16;
input int InpServerUTCOffsetHours=0;

input group "Risk and exits"
input double InpRiskPercent=1.00;
input double InpStopBufferATR=0.10;
input double InpRewardRisk=3.00;
input bool InpUseMeasuredImpulseTarget=false;
input double InpMaximumTargetR=6.00;
input bool InpMoveToBreakEven=true;
input double InpBreakEvenAtR=1.00;
input bool InpUseStructureTrail=true;
input double InpTrailStartR=2.00;
input double InpTrailBufferATR=0.10;
input int InpMaximumHoldingHours=72;
input double InpMaximumSpreadATR=0.12;
input int InpMaximumDeviationPoints=50;
input long InpMagic=862929;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
int g_h4_ema_handle=INVALID_HANDLE;
datetime g_last_bar=0;

bool g_zone_active=false;
bool g_zone_traded=false;
double g_zone_high=0.0;
double g_zone_low=0.0;
double g_impulse_size=0.0;
int g_profile_direction=0;
datetime g_zone_time=0;

ENUM_PBD_STATE g_state=PBD_IDLE;
datetime g_state_time=0;
double g_state_extreme=0.0;
double g_state_trigger_high=0.0;
double g_state_trigger_low=0.0;
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

bool SessionPasses(const datetime server_time)
{
   if(!InpUseNewYorkSession) return true;
   MqlDateTime value={0};
   TimeToStruct(ServerToNewYork(server_time),value);
   if(value.day_of_week==0 || value.day_of_week==6) return false;
   return value.hour>=InpNewYorkStartHour && value.hour<InpNewYorkEndHour;
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

void ClearSignalState()
{
   g_state=PBD_IDLE;
   g_state_time=0;
   g_state_extreme=0.0;
   g_state_trigger_high=0.0;
   g_state_trigger_low=0.0;
}

void ClearZone()
{
   g_zone_active=false;
   g_zone_traded=false;
   g_zone_high=0.0;
   g_zone_low=0.0;
   g_impulse_size=0.0;
   g_profile_direction=0;
   g_zone_time=0;
   ClearSignalState();
}

int BarsElapsed(const datetime older,const datetime newer)
{
   int seconds=PeriodSeconds(InpSignalTimeframe);
   if(seconds<=0 || newer<=older) return 0;
   return (int)((newer-older)/seconds);
}

bool DetectZone(const MqlRates &rates[],const double atr)
{
   int required=InpRangeBars+InpImpulseBars+2;
   if(ArraySize(rates)<=required || atr<=0.0) return false;
   double high=-DBL_MAX;
   double low=DBL_MAX;
   for(int index=2;index<InpRangeBars+2;index++)
   {
      high=MathMax(high,rates[index].high);
      low=MathMin(low,rates[index].low);
   }
   double width=high-low;
   if(width<=0.0) return false;
   double width_atr=width/atr;
   if(width_atr<InpMinimumRangeATR || width_atr>InpMaximumRangeATR) return false;

   double tolerance=InpTouchToleranceFraction*width;
   int last_side=0;
   int alternating=0;
   bool saw_high=false;
   bool saw_low=false;
   for(int index=InpRangeBars+1;index>=2;index--)
   {
      bool near_high=rates[index].high>=high-tolerance;
      bool near_low=rates[index].low<=low+tolerance;
      int side=0;
      if(near_high && near_low)
         side=(MathAbs(high-rates[index].close)<=MathAbs(rates[index].close-low) ? 1 : -1);
      else if(near_high) side=1;
      else if(near_low) side=-1;
      if(side==1) saw_high=true;
      if(side==-1) saw_low=true;
      if(side!=0 && side!=last_side)
      {
         alternating++;
         last_side=side;
      }
   }
   if(!saw_high || !saw_low || alternating<InpMinimumAlternatingTouches) return false;

   int newer_index=InpRangeBars+1;
   int older_index=InpRangeBars+InpImpulseBars+1;
   double impulse=rates[newer_index].close-rates[older_index].close;
   int profile=0;
   if(impulse>=InpMinimumImpulseATR*atr) profile=1;
   else if(impulse<=-InpMinimumImpulseATR*atr) profile=-1;
   else if(!InpAllowDProfile) return false;

   g_zone_high=high;
   g_zone_low=low;
   g_impulse_size=MathAbs(impulse);
   g_profile_direction=profile;
   g_zone_time=rates[1].time;
   g_zone_active=true;
   g_zone_traded=false;
   ClearSignalState();
   return true;
}

bool H4TrendPasses(const int direction)
{
   if(!InpUseH4TrendFilter) return true;
   double ema[];
   MqlRates h4[];
   ArraySetAsSeries(h4,true);
   if(g_h4_ema_handle==INVALID_HANDLE || CopyBuffer(g_h4_ema_handle,0,1,1,ema)!=1 || CopyRates(_Symbol,PERIOD_H4,1,1,h4)!=1)
      return false;
   return (direction>0 ? h4[0].close>ema[0] : h4[0].close<ema[0]);
}

bool DirectionPasses(const int direction)
{
   if(direction>0 && !InpAllowLong) return false;
   if(direction<0 && !InpAllowShort) return false;
   if(InpFollowImpulseOnly && g_profile_direction!=0 && direction!=g_profile_direction) return false;
   return H4TrendPasses(direction);
}

bool PlaceTrade(const int direction,const double structural_extreme,const double atr,const string comment)
{
   if(!DirectionPasses(direction) || !SpreadPasses(atr) || HasOurPosition()) return false;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? structural_extreme-InpStopBufferATR*atr : structural_extreme+InpStopBufferATR*atr);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=entry-broker_gap;
   if(direction<0 && stop-entry<broker_gap) stop=entry+broker_gap;
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target_distance=InpRewardRisk*risk;
   if(InpUseMeasuredImpulseTarget && g_impulse_size>target_distance)
      target_distance=MathMin(g_impulse_size,InpMaximumTargetR*risk);
   double target=(direction>0 ? entry+target_distance : entry-target_distance);
   stop=NormalizePrice(stop);
   target=NormalizePrice(target);
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0)
   {
      Print("PBD proxy skipped: volume below broker minimum.");
      return false;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent)
   {
      Print("PBD proxy order rejected: ",g_trade.ResultRetcodeDescription());
      return false;
   }
   g_initial_risk=risk;
   g_zone_traded=true;
   ClearSignalState();
   return true;
}

void ManagePosition()
{
   bool found=false;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return;
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
      double favorable=(buy ? current-open : open-current);
      double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
      double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
      double candidate=stop;

      if(InpMoveToBreakEven && g_initial_risk>0.0 && favorable>=InpBreakEvenAtR*g_initial_risk)
         candidate=open;

      if(InpUseStructureTrail && g_initial_risk>0.0 && favorable>=InpTrailStartR*g_initial_risk)
      {
         double atr=0.0;
         MqlRates bars[];
         ArraySetAsSeries(bars,true);
         if(ReadATR(1,atr) && CopyRates(_Symbol,InpSignalTimeframe,1,3,bars)==3)
         {
            double structural=(buy ? MathMin(bars[0].low,bars[1].low)-InpTrailBufferATR*atr
                                   : MathMax(bars[0].high,bars[1].high)+InpTrailBufferATR*atr);
            if(buy) candidate=MathMax(candidate,structural);
            else candidate=(candidate<=0.0 ? structural : MathMin(candidate,structural));
         }
      }

      candidate=NormalizePrice(candidate);
      bool improves=(buy ? candidate>stop && candidate<current-broker_gap
                         : (stop<=0.0 || candidate<stop) && candidate>current+broker_gap);
      if(improves) g_trade.PositionModify(ticket,candidate,target);

      if(InpMaximumHoldingHours>0)
      {
         datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent()>=opened+InpMaximumHoldingHours*3600)
            g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
      }
   }
   if(!found) g_initial_risk=0.0;
}

void StartState(const ENUM_PBD_STATE state,const MqlRates &bar,const double extreme)
{
   g_state=state;
   g_state_time=bar.time;
   g_state_extreme=extreme;
   g_state_trigger_high=bar.high;
   g_state_trigger_low=bar.low;
}

void ProcessActiveZone(const MqlRates &rates[],const double atr)
{
   const MqlRates bar=rates[1];
   double width=g_zone_high-g_zone_low;
   if(width<=0.0) { ClearZone(); return; }
   if(BarsElapsed(g_zone_time,bar.time)>InpZoneMaximumBars) { ClearZone(); return; }
   if(g_zone_traded || HasOurPosition() || !SessionPasses(bar.time)) return;

   int state_age=(g_state_time>0 ? BarsElapsed(g_state_time,bar.time) : 0);
   if(g_state!=PBD_IDLE && state_age>InpConfirmationBars)
      ClearSignalState();

   bool use_reclaims=(InpSetupMode==PBD_RECLAIMS_ONLY || InpSetupMode==PBD_RECLAIMS_AND_BREAKOUTS);
   bool use_breakouts=(InpSetupMode==PBD_BREAKOUT_RETESTS_ONLY || InpSetupMode==PBD_RECLAIMS_AND_BREAKOUTS);

   if(g_state==PBD_LOW_RECLAIM_CONFIRM && state_age>=1)
   {
      if(bar.close>bar.open && bar.close>g_state_trigger_high)
      {
         PlaceTrade(1,g_state_extreme,atr,"PBD low reclaim");
         return;
      }
      if(bar.close<g_zone_low) ClearSignalState();
      return;
   }
   if(g_state==PBD_HIGH_RECLAIM_CONFIRM && state_age>=1)
   {
      if(bar.close<bar.open && bar.close<g_state_trigger_low)
      {
         PlaceTrade(-1,g_state_extreme,atr,"PBD high reclaim");
         return;
      }
      if(bar.close>g_zone_high) ClearSignalState();
      return;
   }
   if(g_state==PBD_UP_BREAK_WAIT && state_age>=1)
   {
      if(!InpRequireBreakoutRetest && bar.close>bar.open && bar.close>g_state_trigger_high)
      {
         PlaceTrade(1,MathMin(g_state_extreme,bar.low),atr,"PBD up confirmation");
         return;
      }
      bool retest=bar.low<=g_zone_high+InpRetestToleranceATR*atr &&
                  bar.close>=g_zone_high-InpMaximumRetestDepthFraction*width;
      if(retest)
      {
         StartState(PBD_UP_RETEST_CONFIRM,bar,MathMin(g_state_extreme,bar.low));
         return;
      }
      if(bar.close<g_zone_low) ClearSignalState();
      return;
   }
   if(g_state==PBD_UP_RETEST_CONFIRM && state_age>=1)
   {
      if(bar.close>bar.open && bar.close>g_state_trigger_high && bar.close>g_zone_high)
      {
         PlaceTrade(1,g_state_extreme,atr,"PBD up retest");
         return;
      }
      if(bar.close<g_zone_low) ClearSignalState();
      return;
   }
   if(g_state==PBD_DOWN_BREAK_WAIT && state_age>=1)
   {
      if(!InpRequireBreakoutRetest && bar.close<bar.open && bar.close<g_state_trigger_low)
      {
         PlaceTrade(-1,MathMax(g_state_extreme,bar.high),atr,"PBD down confirmation");
         return;
      }
      bool retest=bar.high>=g_zone_low-InpRetestToleranceATR*atr &&
                  bar.close<=g_zone_low+InpMaximumRetestDepthFraction*width;
      if(retest)
      {
         StartState(PBD_DOWN_RETEST_CONFIRM,bar,MathMax(g_state_extreme,bar.high));
         return;
      }
      if(bar.close>g_zone_high) ClearSignalState();
      return;
   }
   if(g_state==PBD_DOWN_RETEST_CONFIRM && state_age>=1)
   {
      if(bar.close<bar.open && bar.close<g_state_trigger_low && bar.close<g_zone_low)
      {
         PlaceTrade(-1,g_state_extreme,atr,"PBD down retest");
         return;
      }
      if(bar.close>g_zone_high) ClearSignalState();
      return;
   }

   if(g_state!=PBD_IDLE) return;
   if(use_reclaims && bar.low<g_zone_low-InpMinimumSweepATR*atr && bar.close>g_zone_low && bar.close<g_zone_high)
   {
      StartState(PBD_LOW_RECLAIM_CONFIRM,bar,bar.low);
      return;
   }
   if(use_reclaims && bar.high>g_zone_high+InpMinimumSweepATR*atr && bar.close<g_zone_high && bar.close>g_zone_low)
   {
      StartState(PBD_HIGH_RECLAIM_CONFIRM,bar,bar.high);
      return;
   }
   if(use_breakouts && bar.close>g_zone_high+InpBreakoutBufferATR*atr)
   {
      StartState(PBD_UP_BREAK_WAIT,bar,bar.low);
      return;
   }
   if(use_breakouts && bar.close<g_zone_low-InpBreakoutBufferATR*atr)
      StartState(PBD_DOWN_BREAK_WAIT,bar,bar.high);
}

void ProcessClosedBar()
{
   int required=InpRangeBars+InpImpulseBars+12;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required,rates)<required) return;
   double atr=0.0;
   if(!ReadATR(1,atr)) return;
   if(g_zone_active)
   {
      ProcessActiveZone(rates,atr);
      return;
   }
   DetectZone(rates,atr);
}

int OnInit()
{
   if(InpATRPeriod<2 || InpRangeBars<6 || InpImpulseBars<2 || InpMinimumImpulseATR<0.0 ||
      InpMaximumRangeATR<=InpMinimumRangeATR || InpMinimumAlternatingTouches<2 ||
      InpTouchToleranceFraction<=0.0 || InpTouchToleranceFraction>=0.5 || InpZoneMaximumBars<1 ||
      InpConfirmationBars<1 || InpRiskPercent<=0.0 || InpRewardRisk<=0.0 ||
      InpMaximumTargetR<InpRewardRisk || InpMaximumHoldingHours<1)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_h4_ema_handle=iMA(_Symbol,PERIOD_H4,InpH4EMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_h4_ema_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   ClearZone();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_h4_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_h4_ema_handle);
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   ProcessClosedBar();
}
