#property copyright "Sweep Engulf Continuation research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_PREVIOUS_CANDLE_FILTER
{
   PREVIOUS_ANY=0,
   PREVIOUS_SAME_DIRECTION=1,
   PREVIOUS_OPPOSITE_DIRECTION=2
};

enum ENUM_STOP_STYLE
{
   STOP_SIGNAL_EXTREME=0,
   STOP_ATR_DISTANCE=1
};

input group "Signal"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H1;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input ENUM_PREVIOUS_CANDLE_FILTER InpPreviousCandleFilter=PREVIOUS_ANY;
input double InpMinimumBodyFraction=0.00;
input double InpMinimumSweepATR=0.00;
input double InpMaximumSignalRangeATR=6.00;

input group "EMA trend filter"
input bool InpUseEMAFilter=true;
input int InpEMAPeriod=50;

input group "Stop and target"
input ENUM_STOP_STYLE InpStopStyle=STOP_SIGNAL_EXTREME;
input int InpATRPeriod=14;
input double InpSignalExtremeBufferATR=0.10;
input double InpATRStopMultiplier=1.50;
input double InpMinimumStopATR=0.50;
input double InpMaximumStopATR=4.00;
input double InpRewardRisk=1.50;
input double InpBreakEvenAtR=0.00;
input double InpTrailingStartR=0.00;
input double InpTrailingDistanceR=1.00;
input int InpMaximumHoldingBars=0;

input group "Risk and execution"
input bool InpEnableTrading=true;
input double InpRiskPercent=0.50;
input double InpMaximumSpreadATR=0.10;
input long InpMagic=862008;
input int InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_time=0;

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
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionGetTicket(i)>0 && IsOurPosition()) return true;
   return false;
}

bool ReadIndicatorValue(const int handle,const int shift,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
}

bool PreviousDirectionPasses(const int direction,const MqlRates &previous)
{
   if(InpPreviousCandleFilter==PREVIOUS_ANY) return true;
   bool previous_bullish=previous.close>previous.open;
   bool previous_bearish=previous.close<previous.open;
   if(InpPreviousCandleFilter==PREVIOUS_SAME_DIRECTION)
      return (direction>0 ? previous_bullish : previous_bearish);
   return (direction>0 ? previous_bearish : previous_bullish);
}

int DetectSignal(const MqlRates &signal,const MqlRates &previous,const double atr,const double ema)
{
   double range=signal.high-signal.low;
   if(range<=0.0 || atr<=0.0) return 0;
   if(InpMinimumBodyFraction>0.0 && MathAbs(signal.close-signal.open)/range<InpMinimumBodyFraction) return 0;
   if(InpMaximumSignalRangeATR>0.0 && range/atr>InpMaximumSignalRangeATR) return 0;

   bool bullish=(signal.low<previous.low && signal.close>previous.high);
   bool bearish=(signal.high>previous.high && signal.close<previous.low);
   if(bullish && InpMinimumSweepATR>0.0 && (previous.low-signal.low)/atr<InpMinimumSweepATR) bullish=false;
   if(bearish && InpMinimumSweepATR>0.0 && (signal.high-previous.high)/atr<InpMinimumSweepATR) bearish=false;

   if(bullish && InpAllowLong && PreviousDirectionPasses(1,previous) && (!InpUseEMAFilter || signal.close>ema)) return 1;
   if(bearish && InpAllowShort && PreviousDirectionPasses(-1,previous) && (!InpUseEMAFilter || signal.close<ema)) return -1;
   return 0;
}

bool CurrentSpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return (tick.ask-tick.bid)<=InpMaximumSpreadATR*atr;
}

bool SendSignalTrade(const int direction,const MqlRates &signal,const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=0.0;
   if(InpStopStyle==STOP_SIGNAL_EXTREME)
      stop=(direction>0 ? signal.low-InpSignalExtremeBufferATR*atr : signal.high+InpSignalExtremeBufferATR*atr);
   else
      stop=entry-direction*InpATRStopMultiplier*atr;

   double minimum_distance=InpMinimumStopATR*atr;
   if(direction>0 && entry-stop<minimum_distance) stop=entry-minimum_distance;
   if(direction<0 && stop-entry<minimum_distance) stop=entry+minimum_distance;
   double risk_distance=MathAbs(entry-stop);
   if(risk_distance<=0.0 || (InpMaximumStopATR>0.0 && risk_distance>InpMaximumStopATR*atr)) return false;

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(risk_distance<broker_gap) stop=entry-direction*broker_gap;
   stop=NormalizePrice(stop);
   double target=NormalizePrice(entry+direction*MathAbs(entry-stop)*InpRewardRisk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("SEC skipped: calculated volume is below broker minimum.");
      return false;
   }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   string comment=(direction>0 ? "SEC bullish" : "SEC bearish");
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent) Print("SEC order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ManagePosition()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
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

void ProcessNewBar()
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,rates)!=3) return;
   double atr=0.0;
   if(!ReadIndicatorValue(g_atr_handle,1,atr)) return;
   double ema=0.0;
   if(InpUseEMAFilter && !ReadIndicatorValue(g_ema_handle,1,ema)) return;
   int direction=DetectSignal(rates[1],rates[2],atr,ema);
   if(direction==0 || HasOurPosition() || !InpEnableTrading || !CurrentSpreadPasses(atr)) return;
   SendSignalTrade(direction,rates[1],atr);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRewardRisk<=0.0 || InpATRPeriod<2 || InpEMAPeriod<2) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(InpUseEMAFilter)
   {
      g_ema_handle=iMA(_Symbol,InpSignalTimeframe,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
      if(g_ema_handle==INVALID_HANDLE) return INIT_FAILED;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
}

void OnTick()
{
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessNewBar();
}