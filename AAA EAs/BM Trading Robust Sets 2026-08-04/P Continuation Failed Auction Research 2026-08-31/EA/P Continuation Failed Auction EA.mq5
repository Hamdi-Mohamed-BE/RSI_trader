#property copyright "P continuation failed-auction research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_P_TARGET_MODE
{
   TARGET_FIXED_RR=0,
   TARGET_IMPULSE_SIZE=1
};

input group "Pattern timeframe"
input ENUM_TIMEFRAMES InpTimeframe=PERIOD_M5;
input int InpATRPeriod=14;

input group "Explosive move"
input int InpImpulseBars=3;
input double InpMinimumImpulseATR=2.0;
input double InpMinimumDirectionalEfficiency=0.65;

input group "Acceptance consolidation"
input int InpMinimumConsolidationBars=4;
input int InpMaximumConsolidationBars=10;
input double InpMaximumConsolidationATR=1.20;
input double InpAcceptanceLocation=0.65;
input int InpProfileBins=24;
input double InpValueAreaPercent=70.0;

input group "Failed auction and absorption proxy"
input int InpMaximumBarsAfterAcceptance=12;
input double InpMinimumSweepATR=0.03;
input double InpMaximumSweepATR=0.60;
input double InpMinimumRejectionClose=0.60;
input int InpVolumeAverageBars=20;
input double InpMinimumVolumeRatio=1.00;

input group "Exit"
input double InpStopBufferATR=0.10;
input ENUM_P_TARGET_MODE InpTargetMode=TARGET_FIXED_RR;
input double InpRewardRisk=2.0;
input double InpMinimumImpulseTargetR=1.0;
input double InpMaximumImpulseTargetR=4.0;
input bool InpUseBreakEven=true;
input double InpBreakEvenAtR=1.0;
input int InpMaximumHoldingBars=36;

input group "Direction and risk"
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input double InpRiskPercent=1.0;
input double InpMaximumSpreadATR=0.0;
input long InpMagic=863310;
input int InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar=0;
bool g_setup_active=false;
int g_setup_direction=0;
int g_setup_age=0;
double g_value_low=0.0;
double g_value_high=0.0;
double g_poc=0.0;
double g_box_low=0.0;
double g_box_high=0.0;
double g_impulse_size=0.0;
datetime g_last_setup_bar=0;

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

bool ReadATR(const int shift,double &atr)
{
   double values[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,values)!=1) return false;
   atr=values[0];
   return atr>0.0;
}

bool IsOurPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket>0 && IsOurPosition()) return true;
   }
   ticket=0;
   return false;
}

string RiskKey(const ulong identifier)
{
   return "PCONT."+(string)InpMagic+"."+(string)identifier+".R";
}

void StoreInitialRisk()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   double risk=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   if(identifier>0 && risk>0.0) GlobalVariableSet(RiskKey(identifier),risk);
}

double InitialRisk()
{
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string key=RiskKey(identifier);
   if(identifier>0 && GlobalVariableCheck(key)) return GlobalVariableGet(key);
   return MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool BuildValueArea(const MqlRates &rates[],const int count,double &value_low,double &value_high,double &poc)
{
   double profile_low=rates[1].low;
   double profile_high=rates[1].high;
   for(int index=2;index<=count;index++)
   {
      profile_low=MathMin(profile_low,rates[index].low);
      profile_high=MathMax(profile_high,rates[index].high);
   }
   if(profile_high<=profile_low) return false;
   double step=(profile_high-profile_low)/InpProfileBins;
   if(step<=0.0) return false;

   double bins[];
   ArrayResize(bins,InpProfileBins);
   ArrayInitialize(bins,0.0);
   double total=0.0;
   for(int bar=1;bar<=count;bar++)
   {
      int first=(int)MathFloor((rates[bar].low-profile_low)/step);
      int last=(int)MathFloor((rates[bar].high-profile_low)/step);
      first=MathMax(0,MathMin(InpProfileBins-1,first));
      last=MathMax(first,MathMin(InpProfileBins-1,last));
      int touched=last-first+1;
      double volume=(double)rates[bar].tick_volume;
      double share=(touched>0 ? volume/touched : volume);
      for(int bin=first;bin<=last;bin++) bins[bin]+=share;
      total+=volume;
   }
   if(total<=0.0) return false;

   int poc_index=0;
   for(int bin=1;bin<InpProfileBins;bin++) if(bins[bin]>bins[poc_index]) poc_index=bin;
   int lower=poc_index;
   int upper=poc_index;
   double accumulated=bins[poc_index];
   double target=total*InpValueAreaPercent/100.0;
   while(accumulated<target && (lower>0 || upper<InpProfileBins-1))
   {
      double below=(lower>0 ? bins[lower-1] : -1.0);
      double above=(upper<InpProfileBins-1 ? bins[upper+1] : -1.0);
      if(above>=below && upper<InpProfileBins-1)
      {
         upper++;
         accumulated+=bins[upper];
      }
      else if(lower>0)
      {
         lower--;
         accumulated+=bins[lower];
      }
      else break;
   }
   value_low=profile_low+lower*step;
   value_high=profile_low+(upper+1)*step;
   poc=profile_low+(poc_index+0.5)*step;
   return true;
}

bool DetectAcceptedImpulse()
{
   int required=InpMaximumConsolidationBars+InpImpulseBars+3;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpTimeframe,0,required,rates)!=required) return false;
   if(rates[1].time==g_last_setup_bar) return false;
   double atr=0.0;
   if(!ReadATR(1,atr)) return false;

   for(int consolidation=InpMinimumConsolidationBars;consolidation<=InpMaximumConsolidationBars;consolidation++)
   {
      int oldest=consolidation+InpImpulseBars;
      double impulse_start=rates[oldest].open;
      double impulse_end=rates[consolidation+1].close;
      double move=impulse_end-impulse_start;
      int direction=(move>0.0 ? 1 : -1);
      if((direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) continue;
      if(MathAbs(move)<InpMinimumImpulseATR*atr) continue;

      double travelled=0.0;
      for(int bar=consolidation+1;bar<=oldest;bar++) travelled+=rates[bar].high-rates[bar].low;
      if(travelled<=0.0 || MathAbs(move)/travelled<InpMinimumDirectionalEfficiency) continue;

      double box_low=rates[1].low;
      double box_high=rates[1].high;
      for(int bar=2;bar<=consolidation;bar++)
      {
         box_low=MathMin(box_low,rates[bar].low);
         box_high=MathMax(box_high,rates[bar].high);
      }
      if(box_high-box_low>InpMaximumConsolidationATR*atr) continue;
      double acceptance_level=impulse_start+move*InpAcceptanceLocation;
      if(direction>0 && box_low<acceptance_level) continue;
      if(direction<0 && box_high>acceptance_level) continue;

      double value_low=0.0,value_high=0.0,poc=0.0;
      if(!BuildValueArea(rates,consolidation,value_low,value_high,poc)) continue;
      g_setup_active=true;
      g_setup_direction=direction;
      g_setup_age=0;
      g_value_low=value_low;
      g_value_high=value_high;
      g_poc=poc;
      g_box_low=box_low;
      g_box_high=box_high;
      g_impulse_size=MathAbs(move);
      g_last_setup_bar=rates[1].time;
      return true;
   }
   return false;
}

double AveragePriorVolume(const MqlRates &rates[],const int start,const int count)
{
   double total=0.0;
   for(int index=start;index<start+count;index++) total+=(double)rates[index].tick_volume;
   return (count>0 ? total/count : 0.0);
}

bool SendEntry(const MqlRates &signal,const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   int direction=g_setup_direction;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   stop=NormalizePrice(stop);
   double risk=MathAbs(entry-stop);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(risk<broker_gap)
   {
      stop=NormalizePrice(entry-direction*broker_gap);
      risk=MathAbs(entry-stop);
   }
   if(risk<=0.0) return false;

   double target_r=InpRewardRisk;
   if(InpTargetMode==TARGET_IMPULSE_SIZE)
      target_r=MathMax(InpMinimumImpulseTargetR,MathMin(InpMaximumImpulseTargetR,g_impulse_size/risk));
   double target=NormalizePrice(entry+direction*target_r*risk);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"P continuation long")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"P continuation short"));
   if(sent) StoreInitialRisk();
   else Print("P continuation order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ProcessActiveSetup()
{
   g_setup_age++;
   if(g_setup_age>InpMaximumBarsAfterAcceptance)
   {
      g_setup_active=false;
      return;
   }
   int required=InpVolumeAverageBars+3;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpTimeframe,0,required,rates)!=required) return;
   double atr=0.0;
   if(!ReadATR(1,atr) || !SpreadPasses(atr)) return;
   MqlRates signal=rates[1];
   double candle_range=signal.high-signal.low;
   if(candle_range<=0.0) return;
   double average_volume=AveragePriorVolume(rates,2,InpVolumeAverageBars);
   bool volume_pass=(InpMinimumVolumeRatio<=0.0 || average_volume<=0.0 ||
                     (double)signal.tick_volume>=average_volume*InpMinimumVolumeRatio);
   bool valid=false;
   if(g_setup_direction>0)
   {
      double depth=g_value_low-signal.low;
      double close_location=(signal.close-signal.low)/candle_range;
      valid=(depth>=InpMinimumSweepATR*atr && depth<=InpMaximumSweepATR*atr &&
             signal.close>g_value_low && close_location>=InpMinimumRejectionClose && volume_pass);
      if(signal.close<g_box_low-InpMaximumSweepATR*atr) g_setup_active=false;
   }
   else
   {
      double depth=signal.high-g_value_high;
      double close_location=(signal.high-signal.close)/candle_range;
      valid=(depth>=InpMinimumSweepATR*atr && depth<=InpMaximumSweepATR*atr &&
             signal.close<g_value_high && close_location>=InpMinimumRejectionClose && volume_pass);
      if(signal.close>g_box_high+InpMaximumSweepATR*atr) g_setup_active=false;
   }
   if(valid)
   {
      if(SendEntry(signal,atr)) g_setup_active=false;
   }
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   int held=iBarShift(_Symbol,InpTimeframe,opened,false);
   if(InpMaximumHoldingBars>0 && held>=InpMaximumHoldingBars)
   {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
      return;
   }
   if(!InpUseBreakEven) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double risk=InitialRisk();
   if(risk<=0.0) return;
   double current=(buy ? tick.bid : tick.ask);
   double favorable=(buy ? current-open : open-current);
   if(favorable<InpBreakEvenAtR*risk) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   bool improves=(buy ? open>stop+point : stop<=0.0 || open<stop-point);
   if(!improves) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.PositionModify(ticket,NormalizePrice(open),target);
}

int OnInit()
{
   if(InpATRPeriod<2 || InpImpulseBars<1 || InpMinimumImpulseATR<=0.0 ||
      InpMinimumDirectionalEfficiency<=0.0 || InpMinimumDirectionalEfficiency>1.0 ||
      InpMinimumConsolidationBars<2 || InpMaximumConsolidationBars<InpMinimumConsolidationBars ||
      InpMaximumConsolidationATR<=0.0 || InpAcceptanceLocation<=0.0 || InpAcceptanceLocation>=1.0 ||
      InpProfileBins<8 || InpValueAreaPercent<=0.0 || InpValueAreaPercent>=100.0 ||
      InpMaximumBarsAfterAcceptance<1 || InpMinimumSweepATR<0.0 ||
      InpMaximumSweepATR<=InpMinimumSweepATR || InpMinimumRejectionClose<=0.0 ||
      InpMinimumRejectionClose>=1.0 || InpVolumeAverageBars<2 || InpStopBufferATR<0.0 ||
      InpRewardRisk<=0.0 || InpMinimumImpulseTargetR<=0.0 ||
      InpMaximumImpulseTargetR<InpMinimumImpulseTargetR || InpRiskPercent<=0.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpTimeframe,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManagePosition();
   datetime bar=iTime(_Symbol,InpTimeframe,0);
   if(bar<=0 || bar==g_last_bar) return;
   g_last_bar=bar;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;
   if(g_setup_active) ProcessActiveSetup();
   else DetectAcceptedImpulse();
}
