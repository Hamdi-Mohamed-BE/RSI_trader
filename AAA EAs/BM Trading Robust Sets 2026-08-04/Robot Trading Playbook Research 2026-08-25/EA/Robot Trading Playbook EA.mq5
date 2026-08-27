#property copyright "Robot Trading Playbook research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Signal and structure"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M30;
input int InpRangeLookbackBars=12;
input double InpBreakoutBufferATR=0.05;
input double InpMaximumSignalRangeATR=2.50;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

input group "Transcript setup families"
input bool InpUseBreakoutContinuation=true;
input bool InpUseStarterPlay=true;
input bool InpUseBreakoutRetest=true;
input bool InpUseFakeoutReclaim=true;
input int InpSetupLifeBars=2;
input double InpRetestToleranceATR=0.15;

input group "Higher-timeframe bias"
input bool InpUseBiasFilter=true;
input ENUM_TIMEFRAMES InpBiasTimeframe=PERIOD_H4;
input int InpBiasFastEMA=20;
input int InpBiasSlowEMA=50;

input group "Entry, stop and target"
input int InpATRPeriod=14;
input double InpEntryBufferATR=0.02;
input double InpStopBufferATR=0.10;
input double InpMinimumStopATR=0.40;
input double InpMaximumStopATR=3.00;
input double InpRewardRisk=1.50;
input int InpPendingExpiryBars=2;
input double InpBreakEvenAtR=0.00;
input double InpTrailingStartR=0.00;
input double InpTrailingDistanceR=1.00;
input int InpMaximumHoldingBars=16;

input group "Risk and execution"
input bool InpEnableTrading=true;
input double InpRiskPercent=1.00;
input double InpMaximumSpreadATR=0.08;
input long InpMagic=862508;
input int InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
int g_fast_ema_handle=INVALID_HANDLE;
int g_slow_ema_handle=INVALID_HANDLE;
datetime g_last_bar_time=0;
int g_setup_direction=0;
double g_setup_level=0.0;
datetime g_setup_origin=0;
int g_setup_age=0;

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

bool IsOurPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool HasOurPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
      if(PositionGetTicket(index)>0 && IsOurPosition()) return true;
   return false;
}

bool IsOurOrder()
{
   return OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic;
}

bool HasOurPendingOrder()
{
   for(int index=OrdersTotal()-1;index>=0;index--)
      if(OrderGetTicket(index)>0 && IsOurOrder()) return true;
   return false;
}

void DeleteOurPendingOrders()
{
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   for(int index=OrdersTotal()-1;index>=0;index--)
   {
      ulong ticket=OrderGetTicket(index);
      if(ticket>0 && IsOurOrder()) g_trade.OrderDelete(ticket);
   }
}

bool ReadIndicatorValue(const int handle,const int shift,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value!=EMPTY_VALUE;
}

double RangeHigh(const MqlRates &rates[],const int first_shift,const int count)
{
   double value=-DBL_MAX;
   for(int shift=first_shift;shift<first_shift+count;shift++) value=MathMax(value,rates[shift].high);
   return value;
}

double RangeLow(const MqlRates &rates[],const int first_shift,const int count)
{
   double value=DBL_MAX;
   for(int shift=first_shift;shift<first_shift+count;shift++) value=MathMin(value,rates[shift].low);
   return value;
}

int BiasDirection(const MqlRates &signal)
{
   if(!InpUseBiasFilter) return 2;
   double fast=0.0,slow=0.0;
   if(!ReadIndicatorValue(g_fast_ema_handle,1,fast) || !ReadIndicatorValue(g_slow_ema_handle,1,slow)) return 0;
   if(fast>slow && signal.close>fast) return 1;
   if(fast<slow && signal.close<fast) return -1;
   return 0;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool PlaceStopEntry(const int direction,const MqlRates &signal,const double atr,const string comment)
{
   if(!InpEnableTrading || HasOurPosition() || atr<=0.0 || !SpreadPasses(atr)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   double entry=(direction>0 ? signal.high+InpEntryBufferATR*atr : signal.low-InpEntryBufferATR*atr);
   if(direction>0 && entry<=tick.ask+broker_gap) entry=tick.ask+broker_gap;
   if(direction<0 && entry>=tick.bid-broker_gap) entry=tick.bid-broker_gap;
   double stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   double minimum_stop=InpMinimumStopATR*atr;
   if(direction>0 && entry-stop<minimum_stop) stop=entry-minimum_stop;
   if(direction<0 && stop-entry<minimum_stop) stop=entry+minimum_stop;
   double risk=MathAbs(entry-stop);
   if(risk<=broker_gap || (InpMaximumStopATR>0.0 && risk>InpMaximumStopATR*atr)) return false;

   entry=NormalizePrice(entry);
   stop=NormalizePrice(stop);
   double target=NormalizePrice(entry+direction*risk*InpRewardRisk);
   ENUM_ORDER_TYPE market_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(market_type,entry,stop);
   if(lots<=0.0)
   {
      Print("RTP skipped: requested risk is below broker minimum volume.");
      return false;
   }

   DeleteOurPendingOrders();
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   datetime expiration=0;
   ENUM_ORDER_TYPE_TIME time_type=ORDER_TIME_GTC;
   int period_seconds=PeriodSeconds(InpSignalTimeframe);
   if(InpPendingExpiryBars>0 && period_seconds>0)
   {
      time_type=ORDER_TIME_SPECIFIED;
      expiration=iTime(_Symbol,InpSignalTimeframe,0)+InpPendingExpiryBars*period_seconds;
   }
   bool sent=(direction>0
      ? g_trade.BuyStop(lots,entry,_Symbol,stop,target,time_type,expiration,comment)
      : g_trade.SellStop(lots,entry,_Symbol,stop,target,time_type,expiration,comment));
   if(!sent) Print("RTP pending order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ClearSetup(const bool delete_pending)
{
   if(delete_pending) DeleteOurPendingOrders();
   g_setup_direction=0;
   g_setup_level=0.0;
   g_setup_origin=0;
   g_setup_age=0;
}

void ManagePosition()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !IsOurPosition()) continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double current=(buy ? tick.bid : tick.ask);
      double initial_risk=(InpRewardRisk>0.0 && target>0.0 ? MathAbs(target-open)/InpRewardRisk : MathAbs(open-stop));
      if(initial_risk<=0.0) continue;
      double favorable=(buy ? current-open : open-current);
      double candidate=stop;

      if(InpBreakEvenAtR>0.0 && favorable>=InpBreakEvenAtR*initial_risk)
      {
         double break_even=NormalizePrice(open);
         if(buy ? candidate<break_even : (candidate<=0.0 || candidate>break_even)) candidate=break_even;
      }
      if(InpTrailingStartR>0.0 && favorable>=InpTrailingStartR*initial_risk)
      {
         double trailing=NormalizePrice(current+(buy ? -1.0 : 1.0)*InpTrailingDistanceR*initial_risk);
         if(buy ? trailing>candidate : (candidate<=0.0 || trailing<candidate)) candidate=trailing;
      }
      bool improves=(buy ? candidate>stop : (stop<=0.0 || candidate<stop));
      if(improves) g_trade.PositionModify(ticket,candidate,target);

      if(InpMaximumHoldingBars>0)
      {
         datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
         int seconds=PeriodSeconds(InpSignalTimeframe);
         if(seconds>0 && TimeCurrent()>=opened+InpMaximumHoldingBars*seconds)
            g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
      }
   }
}

bool ProcessActiveSetup(const MqlRates &signal,const double atr,const int bias)
{
   if(g_setup_direction==0 || signal.time<=g_setup_origin || HasOurPosition()) return false;
   g_setup_age++;
   int direction=g_setup_direction;
   bool still_holds=(direction>0 ? signal.close>g_setup_level : signal.close<g_setup_level);
   bool bias_passes=(bias==2 || bias==direction);
   if(!still_holds || !bias_passes || g_setup_age>InpSetupLifeBars)
   {
      ClearSetup(true);
      return false;
   }

   bool opposite_candle=(direction>0 ? signal.close<signal.open : signal.close>signal.open);
   bool retested=(direction>0
      ? signal.low<=g_setup_level+InpRetestToleranceATR*atr
      : signal.high>=g_setup_level-InpRetestToleranceATR*atr);
   if((InpUseStarterPlay && opposite_candle) || (InpUseBreakoutRetest && retested))
   {
      string label=(opposite_candle ? "RTP starter" : "RTP retest");
      if(PlaceStopEntry(direction,signal,atr,label)) return true;
   }
   return HasOurPendingOrder();
}

void ProcessNewBar()
{
   const int needed=InpRangeLookbackBars+5;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,needed,rates)!=needed) return;
   double atr=0.0;
   if(!ReadIndicatorValue(g_atr_handle,1,atr) || atr<=0.0) return;
   MqlRates signal=rates[1];
   double signal_range=signal.high-signal.low;
   if(signal_range<=0.0 || (InpMaximumSignalRangeATR>0.0 && signal_range>InpMaximumSignalRangeATR*atr)) return;
   int bias=BiasDirection(signal);

   if(ProcessActiveSetup(signal,atr,bias)) return;
   if(HasOurPosition() || HasOurPendingOrder()) return;

   double resistance=RangeHigh(rates,2,InpRangeLookbackBars);
   double support=RangeLow(rates,2,InpRangeLookbackBars);
   bool long_breakout=InpAllowLong && (bias==1 || bias==2) && signal.close>resistance+InpBreakoutBufferATR*atr;
   bool short_breakout=InpAllowShort && (bias==-1 || bias==2) && signal.close<support-InpBreakoutBufferATR*atr;

   if(InpUseBreakoutContinuation && (long_breakout || short_breakout))
   {
      int direction=(long_breakout ? 1 : -1);
      g_setup_direction=direction;
      g_setup_level=(direction>0 ? resistance : support);
      g_setup_origin=signal.time;
      g_setup_age=0;
      PlaceStopEntry(direction,signal,atr,"RTP breakout");
      return;
   }

   if(!InpUseFakeoutReclaim) return;
   double prior_resistance=RangeHigh(rates,3,InpRangeLookbackBars);
   double prior_support=RangeLow(rates,3,InpRangeLookbackBars);
   MqlRates false_break=rates[2];
   bool bullish_reclaim=InpAllowLong && (bias==1 || bias==2)
      && false_break.close<prior_support-InpBreakoutBufferATR*atr
      && signal.close>prior_support && signal.close>signal.open;
   bool bearish_reclaim=InpAllowShort && (bias==-1 || bias==2)
      && false_break.close>prior_resistance+InpBreakoutBufferATR*atr
      && signal.close<prior_resistance && signal.close<signal.open;
   if(bullish_reclaim || bearish_reclaim)
      PlaceStopEntry((bullish_reclaim ? 1 : -1),signal,atr,"RTP fakeout");
}

int OnInit()
{
   if(InpRangeLookbackBars<3 || InpATRPeriod<2 || InpRiskPercent<=0.0 || InpRewardRisk<=0.0
      || InpBiasFastEMA<2 || InpBiasSlowEMA<=InpBiasFastEMA || InpSetupLifeBars<1)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(InpUseBiasFilter)
   {
      g_fast_ema_handle=iMA(_Symbol,InpBiasTimeframe,InpBiasFastEMA,0,MODE_EMA,PRICE_CLOSE);
      g_slow_ema_handle=iMA(_Symbol,InpBiasTimeframe,InpBiasSlowEMA,0,MODE_EMA,PRICE_CLOSE);
      if(g_fast_ema_handle==INVALID_HANDLE || g_slow_ema_handle==INVALID_HANDLE) return INIT_FAILED;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_fast_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_ema_handle);
   if(g_slow_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_ema_handle);
}

void OnTick()
{
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessNewBar();
}
