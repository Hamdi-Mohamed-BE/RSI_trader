#property copyright "Mechanical research proxy derived from the supplied top-down trading transcript"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"

enum ENUM_TDFVG_BIAS_MODE
{
   TDFVG_NO_BIAS=0,
   TDFVG_H4_BIAS=1,
   TDFVG_D1_AND_H4_BIAS=2
};

input group "Top-down technical proxy"
input bool                  InpEnableTrading=true;
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M15;
input ENUM_TDFVG_BIAS_MODE  InpBiasMode=TDFVG_H4_BIAS;
input int                   InpBiasFastPeriod=20;
input int                   InpBiasSlowPeriod=50;
input bool                  InpAllowLong=true;
input bool                  InpAllowShort=true;

input group "Liquidity sweep and displacement"
input int                   InpSweepLookbackBars=24;
input double                InpSweepBufferATR=0.02;
input bool                  InpRequireSweepCloseBack=true;
input double                InpDisplacementBodyATR=0.60;
input double                InpMinimumFVGATR=0.03;
input double                InpMaximumFVGATR=1.00;
input int                   InpRetestExpiryBars=6;

input group "Stops and targets"
input int                   InpATRPeriod=14;
input double                InpStopBufferATR=0.10;
input double                InpMinimumStopATR=0.30;
input double                InpMaximumStopATR=3.00;
input double                InpRewardRisk=2.00;
input double                InpBreakEvenAtR=1.00;
input int                   InpMaximumHoldingBars=96;

input group "Risk and execution"
input double                InpRiskPercent=1.00;
input double                InpMaximumSpreadATRPercent=15.0;
input int                   InpMaximumTradesPerBrokerDay=2;
input bool                  InpWeekdaysOnly=false;
input int                   InpMaximumDeviationPoints=50;
input long                  InpMagic=86270827;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
int g_h4_fast_handle=INVALID_HANDLE;
int g_h4_slow_handle=INVALID_HANDLE;
int g_d1_fast_handle=INVALID_HANDLE;
int g_d1_slow_handle=INVALID_HANDLE;
datetime g_last_signal_bar=0;
datetime g_last_setup_bar=0;

int g_pending_direction=0;
double g_pending_entry=0.0;
double g_pending_stop=0.0;
double g_pending_zone_low=0.0;
double g_pending_zone_high=0.0;
int g_pending_bars_left=0;

double NormalizePrice(const double price)
{
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick_size<=0.0) return price;
   return NormalizeDouble(MathRound(price/tick_size)*tick_size,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(volume,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_loss)) return 0.0;
   one_lot_loss=MathAbs(one_lot_loss);
   if(one_lot_loss<=0.0) return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/one_lot_loss);
}

bool ReadValue(const int handle,const int shift,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
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
   ticket=0;
   return false;
}

int BiasForHandles(const int fast_handle,const int slow_handle,const ENUM_TIMEFRAMES timeframe)
{
   double fast=0.0,slow=0.0;
   if(!ReadValue(fast_handle,1,fast) || !ReadValue(slow_handle,1,slow)) return 0;
   double close=iClose(_Symbol,timeframe,1);
   if(close<=0.0) return 0;
   if(close>fast && fast>slow) return 1;
   if(close<fast && fast<slow) return -1;
   return 0;
}

bool BiasPasses(const int direction)
{
   if(InpBiasMode==TDFVG_NO_BIAS) return true;
   int h4=BiasForHandles(g_h4_fast_handle,g_h4_slow_handle,PERIOD_H4);
   if(h4!=direction) return false;
   if(InpBiasMode==TDFVG_H4_BIAS) return true;
   int d1=BiasForHandles(g_d1_fast_handle,g_d1_slow_handle,PERIOD_D1);
   return d1==direction;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATRPercent<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0 || atr<=0.0) return false;
   return (tick.ask-tick.bid)/atr*100.0<=InpMaximumSpreadATRPercent;
}

int TradesToday()
{
   MqlDateTime now_parts;
   TimeToStruct(TimeCurrent(),now_parts);
   now_parts.hour=0; now_parts.min=0; now_parts.sec=0;
   datetime start=StructToTime(now_parts);
   if(!HistorySelect(start,TimeCurrent()+60)) return 0;
   int count=0;
   for(int index=0;index<HistoryDealsTotal();index++)
   {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT) count++;
   }
   return count;
}

void ClearPending()
{
   g_pending_direction=0;
   g_pending_entry=0.0;
   g_pending_stop=0.0;
   g_pending_zone_low=0.0;
   g_pending_zone_high=0.0;
   g_pending_bars_left=0;
}

bool SendEntry(const int direction,const double planned_stop,const double atr)
{
   if(!DTS_EntrySessionAllowed()) return false;
   if(!InpEnableTrading || !SpreadPasses(atr) || TradesToday()>=InpMaximumTradesPerBrokerDay) return false;
   if(!HAMA_SafeRegimeAllowsDirection(direction)) return false;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(planned_stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<InpMinimumStopATR*atr || risk>InpMaximumStopATR*atr) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(risk<=broker_gap) return false;
   double target=NormalizePrice(entry+direction*InpRewardRisk*risk);
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0)
   {
      Print("TDFVG skipped: requested risk is below the broker minimum volume.");
      return false;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"TDFVG long")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"TDFVG short"));
   if(!sent) Print("TDFVG order failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ProcessPending(const double atr)
{
   if(g_pending_direction==0) return;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) { ClearPending(); return; }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(g_pending_direction>0)
   {
      if(tick.ask<=g_pending_stop || tick.ask<g_pending_zone_low) { ClearPending(); return; }
      if(tick.ask<=g_pending_entry && tick.ask<=g_pending_zone_high)
      {
         double stop=g_pending_stop;
         ClearPending();
         SendEntry(1,stop,atr);
      }
   }
   else
   {
      if(tick.bid>=g_pending_stop || tick.bid>g_pending_zone_high) { ClearPending(); return; }
      if(tick.bid>=g_pending_entry && tick.bid>=g_pending_zone_low)
      {
         double stop=g_pending_stop;
         ClearPending();
         SendEntry(-1,stop,atr);
      }
   }
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double current=(buy ? tick.bid : tick.ask);
   double initial_risk=(InpRewardRisk>0.0 && target>0.0 ? MathAbs(target-open)/InpRewardRisk : MathAbs(open-stop));
   if(initial_risk<=0.0) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);

   if(InpBreakEvenAtR>0.0)
   {
      double favorable=(buy ? current-open : open-current);
      if(favorable>=InpBreakEvenAtR*initial_risk)
      {
         double candidate=NormalizePrice(open);
         bool improves=(buy ? candidate>stop : (stop<=0.0 || candidate<stop));
         if(improves) g_trade.PositionModify(ticket,candidate,target);
      }
   }
   if(InpMaximumHoldingBars>0)
   {
      int seconds=PeriodSeconds(InpSignalTimeframe);
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      if(seconds>0 && TimeCurrent()>=opened+InpMaximumHoldingBars*seconds)
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
}

void DetectNewSetup(const double atr)
{
   int required=InpSweepLookbackBars+8;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,InpSignalTimeframe,0,required,rates);
   if(copied<required || rates[1].time==g_last_setup_bar) return;

   MqlDateTime signal_time;
   TimeToStruct(rates[1].time,signal_time);
   if(InpWeekdaysOnly && (signal_time.day_of_week==0 || signal_time.day_of_week==6)) return;

   double prior_low=DBL_MAX,prior_high=-DBL_MAX;
   for(int shift=4;shift<4+InpSweepLookbackBars;shift++)
   {
      prior_low=MathMin(prior_low,rates[shift].low);
      prior_high=MathMax(prior_high,rates[shift].high);
   }

   MqlRates completion=rates[1];
   MqlRates displacement=rates[2];
   MqlRates sweep=rates[3];
   double sweep_buffer=InpSweepBufferATR*atr;
   bool swept_low=sweep.low<prior_low-sweep_buffer;
   bool swept_high=sweep.high>prior_high+sweep_buffer;
   if(InpRequireSweepCloseBack)
   {
      swept_low=swept_low && sweep.close>prior_low;
      swept_high=swept_high && sweep.close<prior_high;
   }

   double body=MathAbs(displacement.close-displacement.open);
   bool bull_displacement=displacement.close>displacement.open && body>=InpDisplacementBodyATR*atr && displacement.close>sweep.high;
   bool bear_displacement=displacement.close<displacement.open && body>=InpDisplacementBodyATR*atr && displacement.close<sweep.low;
   bool bull_fvg=completion.low>sweep.high;
   bool bear_fvg=completion.high<sweep.low;

   int direction=0;
   double zone_low=0.0,zone_high=0.0;
   if(InpAllowLong && swept_low && bull_displacement && bull_fvg && BiasPasses(1))
   {
      direction=1;
      zone_low=sweep.high;
      zone_high=completion.low;
   }
   else if(InpAllowShort && swept_high && bear_displacement && bear_fvg && BiasPasses(-1))
   {
      direction=-1;
      zone_low=completion.high;
      zone_high=sweep.low;
   }
   if(direction==0) return;

   double fvg_width=zone_high-zone_low;
   if(fvg_width<InpMinimumFVGATR*atr || fvg_width>InpMaximumFVGATR*atr) return;
   double entry=(zone_low+zone_high)*0.5;
   double stop=(direction>0 ? sweep.low-InpStopBufferATR*atr : sweep.high+InpStopBufferATR*atr);
   double planned_risk=(direction>0 ? entry-stop : stop-entry);
   if(planned_risk<InpMinimumStopATR*atr || planned_risk>InpMaximumStopATR*atr) return;

   g_pending_direction=direction;
   g_pending_entry=NormalizePrice(entry);
   g_pending_stop=NormalizePrice(stop);
   g_pending_zone_low=NormalizePrice(zone_low);
   g_pending_zone_high=NormalizePrice(zone_high);
   g_pending_bars_left=InpRetestExpiryBars;
   g_last_setup_bar=rates[1].time;
}

int OnInit()
{
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   if(InpSignalTimeframe<PERIOD_M5 || InpBiasFastPeriod<2 || InpBiasSlowPeriod<=InpBiasFastPeriod ||
      InpSweepLookbackBars<5 || InpATRPeriod<2 || InpRetestExpiryBars<1 || InpRiskPercent<=0.0 ||
      InpRewardRisk<=0.0 || InpMinimumStopATR<=0.0 || InpMaximumStopATR<InpMinimumStopATR)
      return INIT_PARAMETERS_INCORRECT;

   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_h4_fast_handle=iMA(_Symbol,PERIOD_H4,InpBiasFastPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h4_slow_handle=iMA(_Symbol,PERIOD_H4,InpBiasSlowPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_d1_fast_handle=iMA(_Symbol,PERIOD_D1,InpBiasFastPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_d1_slow_handle=iMA(_Symbol,PERIOD_D1,InpBiasSlowPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_h4_fast_handle==INVALID_HANDLE || g_h4_slow_handle==INVALID_HANDLE ||
      g_d1_fast_handle==INVALID_HANDLE || g_d1_slow_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_h4_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_h4_fast_handle);
   if(g_h4_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_h4_slow_handle);
   if(g_d1_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_d1_fast_handle);
   if(g_d1_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_d1_slow_handle);
}

void OnTick()
{
   DTS_ManageDynamicTrailing(InpMagic);
   ManagePosition();
   double atr=0.0;
   if(!ReadValue(g_atr_handle,1,atr)) return;
   ProcessPending(atr);

   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(current_bar<=0 || current_bar==g_last_signal_bar) return;
   g_last_signal_bar=current_bar;
   if(g_pending_direction!=0)
   {
      g_pending_bars_left--;
      if(g_pending_bars_left<=0) ClearPending();
   }
   if(g_pending_direction==0)
      DetectNewSetup(atr);
}
