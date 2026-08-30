#property copyright "CRT parent-range research rebuild"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input ENUM_TIMEFRAMES InpAnchorTimeframe=PERIOD_H4;
input int InpATRPeriod=14;
input double InpMinimumParentRangeATR=0.50;
input double InpMaximumParentRangeATR=2.50;
input double InpSweepBufferATR=0.01;
input double InpMaximumSweepDepthATR=0.75;
input double InpStopBufferATR=0.05;
input bool InpExcludeDoubleSweep=true;
input bool InpRequireDirectionalClose=false;

input bool InpUseDailyTrendFilter=true;
input int InpTrendFastEMA=20;
input int InpTrendSlowEMA=50;

input double InpMinimumRewardRisk=0.50;
input double InpMaximumRewardRisk=5.00;
input int InpMaximumHoldingAnchorBars=8;
input int InpMaximumTradesPerDay=2;

input double InpRiskPercent=1.00;
input double InpMaximumSpreadATR=0.08;
input int InpMaximumDeviationPoints=80;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input ulong InpMagic=86300001;

CTrade g_trade;
int g_atr=INVALID_HANDLE;
int g_daily_fast=INVALID_HANDLE;
int g_daily_slow=INVALID_HANDLE;
datetime g_last_anchor_bar=0;
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
   if(step<=0.0 || minimum<=0.0) return 0.0;
   lots=MathFloor(lots/step+1e-9)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
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
   return MathIsValidNumber(value);
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
   double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   if(risk_money<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double profit=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit)) return 0.0;
   double loss_per_lot=MathAbs(profit);
   if(loss_per_lot<=0.0) return 0.0;
   return NormalizeLots(risk_money/loss_per_lot);
}

int DailyTrend()
{
   if(!InpUseDailyTrendFilter) return 0;
   double fast=0.0,slow=0.0;
   if(!BufferValue(g_daily_fast,0,1,fast) || !BufferValue(g_daily_slow,0,1,slow)) return 99;
   if(fast>slow) return 1;
   if(fast<slow) return -1;
   return 99;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool SendTrade(const int direction,const double raw_stop,const double raw_target,const double atr,const string comment)
{
   if(HasPosition() || g_day_trades>=InpMaximumTradesPerDay) return false;
   if(direction>0 && !InpAllowLong) return false;
   if(direction<0 && !InpAllowShort) return false;
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
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(sent)
   {
      g_day_trades++;
      return true;
   }
   Print("CRT order rejected: ",g_trade.ResultRetcodeDescription());
   return false;
}

void EvaluateConfirmedCRT()
{
   int required=MathMax(20,InpATRPeriod+5);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpAnchorTimeframe,0,required,rates)<required) return;

   double atr=0.0;
   if(!BufferValue(g_atr,0,1,atr) || atr<=0.0) return;
   MqlRates sweep=rates[1];
   MqlRates parent=rates[2];
   double parent_range=parent.high-parent.low;
   if(parent_range<InpMinimumParentRangeATR*atr || parent_range>InpMaximumParentRangeATR*atr) return;

   long today=DateKey(sweep.time);
   if(today!=g_day_key)
   {
      g_day_key=today;
      g_day_trades=0;
   }

   double sweep_buffer=InpSweepBufferATR*atr;
   double stop_buffer=InpStopBufferATR*atr;
   double maximum_depth=InpMaximumSweepDepthATR*atr;
   bool swept_low=sweep.low<parent.low-sweep_buffer;
   bool swept_high=sweep.high>parent.high+sweep_buffer;
   bool close_inside=sweep.close>parent.low && sweep.close<parent.high;
   if(!close_inside) return;
   if(InpExcludeDoubleSweep && swept_low && swept_high) return;

   int trend=DailyTrend();
   if(trend==99) return;
   if(swept_low && parent.low-sweep.low<=maximum_depth &&
      (!InpRequireDirectionalClose || sweep.close>sweep.open) &&
      (!InpUseDailyTrendFilter || trend>0))
   {
      SendTrade(1,sweep.low-stop_buffer,parent.high,atr,"CRT low sweep reclaim");
      return;
   }
   if(swept_high && sweep.high-parent.high<=maximum_depth &&
      (!InpRequireDirectionalClose || sweep.close<sweep.open) &&
      (!InpUseDailyTrendFilter || trend<0))
   {
      SendTrade(-1,sweep.high+stop_buffer,parent.low,atr,"CRT high sweep reclaim");
   }
}

void ManagePosition()
{
   if(InpMaximumHoldingAnchorBars<=0) return;
   int seconds=PeriodSeconds(InpAnchorTimeframe);
   if(seconds<=0) return;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      if(TimeCurrent()>=opened+(long)InpMaximumHoldingAnchorBars*seconds)
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
}

int OnInit()
{
   if(InpATRPeriod<2 || InpMinimumParentRangeATR<=0.0 || InpMaximumParentRangeATR<InpMinimumParentRangeATR ||
      InpMaximumSweepDepthATR<=0.0 || InpRiskPercent<=0.0 || InpRiskPercent>10.0 ||
      InpMinimumRewardRisk<=0.0 || InpMaximumRewardRisk<InpMinimumRewardRisk ||
      InpTrendFastEMA<2 || InpTrendSlowEMA<=InpTrendFastEMA) return INIT_PARAMETERS_INCORRECT;

   g_atr=iATR(_Symbol,InpAnchorTimeframe,InpATRPeriod);
   g_daily_fast=iMA(_Symbol,PERIOD_D1,InpTrendFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_daily_slow=iMA(_Symbol,PERIOD_D1,InpTrendSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr==INVALID_HANDLE || g_daily_fast==INVALID_HANDLE || g_daily_slow==INVALID_HANDLE)
      return INIT_FAILED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_anchor_bar=iTime(_Symbol,InpAnchorTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
   if(g_daily_fast!=INVALID_HANDLE) IndicatorRelease(g_daily_fast);
   if(g_daily_slow!=INVALID_HANDLE) IndicatorRelease(g_daily_slow);
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,InpAnchorTimeframe,0);
   if(current<=0 || current==g_last_anchor_bar) return;
   g_last_anchor_bar=current;
   EvaluateConfirmedCRT();
}
