#property copyright "Research reconstruction from engineered-liquidity transcript"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"

enum ENUM_ELS_RISK_MODE
{
   ELS_RISK_PERCENT=0,
   ELS_RISK_FIXED_USD=1
};

input group "Signal structure"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input int    InpSwingStrength=2;
input int    InpLiquidityLookback=40;
input int    InpTargetLookback=40;
input int    InpATRPeriod=14;
input double InpMinimumSweepATR=0.01;
input double InpMaximumSweepATR=0.75;
input double InpStopBufferATR=0.08;
input bool   InpRequireDirectionalCandle=true;
input bool   InpRequireDisplacementClose=false;

input group "Dominant trend"
input ENUM_TIMEFRAMES InpTrendTimeframe=PERIOD_H4;
input int    InpTrendFastEMA=20;
input int    InpTrendSlowEMA=50;
input bool   InpRequireFastEMASlope=true;

input group "Exit and frequency"
input double InpMinimumRewardRisk=1.50;
input double InpMaximumRewardRisk=8.00;
input int    InpMaximumHoldingBars=64;
input int    InpMaximumTradesPerDay=2;
input bool   InpAllowLong=true;
input bool   InpAllowShort=true;

input group "Risk and execution"
input ENUM_ELS_RISK_MODE InpRiskMode=ELS_RISK_PERCENT;
input double InpRiskPercent=1.00;
input double InpFixedRiskMoney=100.00;
input double InpMaximumSpreadATR=0.08;
input int    InpMaximumDeviationPoints=80;
input ulong  InpMagic=86830001;

CTrade g_trade;
int g_atr=INVALID_HANDLE;
int g_fast=INVALID_HANDLE;
int g_slow=INVALID_HANDLE;
datetime g_last_signal_bar=0;
long g_day_key=0;
int g_day_trades=0;

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(double lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || minimum<=0.0 || maximum<=0.0 || lots<minimum) return 0.0;
   lots=MathFloor(MathMin(lots,maximum)/step+1e-9)*step;
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9)
   {
      probe*=10.0;
      digits++;
   }
   return NormalizeDouble(lots,digits);
}

bool BufferValue(const int handle,const int buffer,const int shift,double &value)
{
   double data[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,data)!=1) return false;
   value=data[0];
   return MathIsValidNumber(value) && value!=EMPTY_VALUE;
}

long DateKey(const datetime when)
{
   MqlDateTime value={0};
   TimeToStruct(when,value);
   return (long)value.year*10000L+(long)value.mon*100L+value.day;
}

bool HasPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   return false;
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double risk_money=(InpRiskMode==ELS_RISK_FIXED_USD
                      ? InpFixedRiskMoney
                      : AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0);
   if(risk_money<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,result)) return 0.0;
   double loss_per_lot=MathAbs(result);
   if(loss_per_lot<=0.0) return 0.0;
   return NormalizeLots(risk_money/loss_per_lot);
}

int TrendDirection()
{
   double fast1=0.0,fast2=0.0,slow1=0.0;
   if(!BufferValue(g_fast,0,1,fast1) || !BufferValue(g_fast,0,2,fast2) || !BufferValue(g_slow,0,1,slow1))
      return 0;
   double close=iClose(_Symbol,InpTrendTimeframe,1);
   if(close<=0.0) return 0;
   if(fast1>slow1 && close>fast1 && (!InpRequireFastEMASlope || fast1>fast2)) return 1;
   if(fast1<slow1 && close<fast1 && (!InpRequireFastEMASlope || fast1<fast2)) return -1;
   return 0;
}

bool IsSwingLow(MqlRates &rates[],const int index,const int strength)
{
   double level=rates[index].low;
   for(int offset=1;offset<=strength;offset++)
      if(level>=rates[index-offset].low || level>=rates[index+offset].low) return false;
   return true;
}

bool IsSwingHigh(MqlRates &rates[],const int index,const int strength)
{
   double level=rates[index].high;
   for(int offset=1;offset<=strength;offset++)
      if(level<=rates[index-offset].high || level<=rates[index+offset].high) return false;
   return true;
}

bool FindRecentSwing(MqlRates &rates[],const int direction,double &level,int &swing_index)
{
   int first=InpSwingStrength+2; // excludes the signal candle from swing confirmation
   int last=InpLiquidityLookback;
   for(int index=first;index<=last;index++)
   {
      if(direction>0 && IsSwingLow(rates,index,InpSwingStrength))
      {
         level=rates[index].low;
         swing_index=index;
         return true;
      }
      if(direction<0 && IsSwingHigh(rates,index,InpSwingStrength))
      {
         level=rates[index].high;
         swing_index=index;
         return true;
      }
   }
   return false;
}

double OpposingLiquidityTarget(MqlRates &rates[],const int direction)
{
   double target=(direction>0 ? -DBL_MAX : DBL_MAX);
   for(int index=2;index<=InpTargetLookback;index++)
   {
      if(direction>0) target=MathMax(target,rates[index].high);
      else target=MathMin(target,rates[index].low);
   }
   return target;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   return SymbolInfoTick(_Symbol,tick) && tick.ask>0.0 && tick.bid>0.0 &&
          tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool SendTrade(const int direction,const double raw_stop,const double raw_target,const double atr)
{
   if(!DTS_EntrySessionAllowed()) return false;
   if(HasPosition() || g_day_trades>=InpMaximumTradesPerDay) return false;
   if((direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) return false;
   if(!SpreadPasses(atr)) return false;

   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(raw_stop);
   double target=NormalizePrice(raw_target);
   if(direction>0 && (stop>=entry || target<=entry)) return false;
   if(direction<0 && (stop<=entry || target>=entry)) return false;

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=NormalizePrice(entry-broker_gap);
   if(direction<0 && stop-entry<broker_gap) stop=NormalizePrice(entry+broker_gap);
   if(direction>0 && target-entry<broker_gap) return false;
   if(direction<0 && entry-target<broker_gap) return false;

   double risk=MathAbs(entry-stop);
   double reward=MathAbs(target-entry);
   if(risk<=0.0) return false;
   double rr=reward/risk;
   if(rr<InpMinimumRewardRisk || rr>InpMaximumRewardRisk) return false;

   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   string comment=(direction>0 ? "Engineered low sweep" : "Engineered high sweep");
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(sent)
   {
      g_day_trades++;
      return true;
   }
   Print("Engineered-liquidity order rejected: ",g_trade.ResultRetcodeDescription());
   return false;
}

void EvaluateSignal()
{
   int required=MathMax(InpLiquidityLookback,InpTargetLookback)+InpSwingStrength+5;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required,rates)<required) return;

   long day=DateKey(rates[1].time);
   if(day!=g_day_key)
   {
      g_day_key=day;
      g_day_trades=0;
   }
   if(g_day_trades>=InpMaximumTradesPerDay || HasPosition()) return;

   double atr=0.0;
   if(!BufferValue(g_atr,0,1,atr) || atr<=0.0) return;
   int direction=TrendDirection();
   if(direction==0) return;
   if(!HAMA_SafeRegimeAllowsDirection(direction)) return;

   double level=0.0;
   int swing_index=-1;
   if(!FindRecentSwing(rates,direction,level,swing_index)) return;

   MqlRates signal=rates[1];
   double minimum_sweep=InpMinimumSweepATR*atr;
   double maximum_sweep=InpMaximumSweepATR*atr;
   double stop_buffer=InpStopBufferATR*atr;
   bool valid=false;
   if(direction>0)
   {
      double depth=level-signal.low;
      valid=(depth>=minimum_sweep && depth<=maximum_sweep && signal.close>level);
      if(InpRequireDirectionalCandle) valid=valid && signal.close>signal.open;
      if(InpRequireDisplacementClose) valid=valid && signal.close>rates[2].high;
      if(valid) SendTrade(1,signal.low-stop_buffer,OpposingLiquidityTarget(rates,1),atr);
   }
   else
   {
      double depth=signal.high-level;
      valid=(depth>=minimum_sweep && depth<=maximum_sweep && signal.close<level);
      if(InpRequireDirectionalCandle) valid=valid && signal.close<signal.open;
      if(InpRequireDisplacementClose) valid=valid && signal.close<rates[2].low;
      if(valid) SendTrade(-1,signal.high+stop_buffer,OpposingLiquidityTarget(rates,-1),atr);
   }
}

void ManagePosition()
{
   if(InpMaximumHoldingBars<=0) return;
   int seconds=PeriodSeconds(InpSignalTimeframe);
   if(seconds<=0) return;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      if(TimeCurrent()>=opened+(long)InpMaximumHoldingBars*seconds)
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
}

int OnInit()
{
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   if(InpSwingStrength<1 || InpLiquidityLookback<InpSwingStrength*2+5 ||
      InpTargetLookback<5 || InpATRPeriod<2 || InpMaximumSweepATR<InpMinimumSweepATR ||
      InpTrendFastEMA<2 || InpTrendSlowEMA<=InpTrendFastEMA ||
      InpMinimumRewardRisk<=0.0 || InpMaximumRewardRisk<InpMinimumRewardRisk ||
      (InpRiskMode==ELS_RISK_PERCENT && (InpRiskPercent<=0.0 || InpRiskPercent>10.0)) ||
      (InpRiskMode==ELS_RISK_FIXED_USD && InpFixedRiskMoney<=0.0)) return INIT_PARAMETERS_INCORRECT;

   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_fast=iMA(_Symbol,InpTrendTimeframe,InpTrendFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow=iMA(_Symbol,InpTrendTimeframe,InpTrendSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr==INVALID_HANDLE || g_fast==INVALID_HANDLE || g_slow==INVALID_HANDLE) return INIT_FAILED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
   if(g_fast!=INVALID_HANDLE) IndicatorRelease(g_fast);
   if(g_slow!=INVALID_HANDLE) IndicatorRelease(g_slow);
}

void OnTick()
{
   DTS_ManageDynamicTrailing((long)InpMagic);
   ManagePosition();
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_signal_bar) return;
   g_last_signal_bar=current;
   EvaluateSignal();
}
