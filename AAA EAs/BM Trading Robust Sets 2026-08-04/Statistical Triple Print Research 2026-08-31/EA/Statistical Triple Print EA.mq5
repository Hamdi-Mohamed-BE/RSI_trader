#property copyright "Mechanical research reconstruction from supplied transcript"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_STP_PROFILE
{
   STP_NORMAL_ACCOUNT=0,
   STP_PROP_FIRM=1
};

input group "Transcript reconstruction"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input int    InpStructureLookback=24;
input int    InpPullbackLookback=14;
input int    InpRequiredValidCandles=3;
input int    InpATRPeriod=14;
input double InpMinimumBreakoutATR=0.80;
input double InpStopBufferATR=0.15;
input double InpMinimumWickGapATR=0.03;
input double InpRewardRisk=2.00;
input int    InpMaximumHoldingBars=48;

input group "Trading window (server time)"
input bool   InpUseTradingWindow=true;
input int    InpStartHour=6;
input int    InpEndHour=22;
input bool   InpCloseFriday=true;
input int    InpFridayCloseHour=20;

input group "Account profile"
input ENUM_STP_PROFILE InpProfile=STP_NORMAL_ACCOUNT;
input double InpNormalRiskPercent=1.00;
input double InpPropRiskPercent=0.35;
input int    InpNormalMaximumTradesPerDay=2;
input int    InpPropMaximumTradesPerDay=1;
input double InpPropDailyLossLimitPercent=1.00;
input double InpPropOverallDrawdownLimitPercent=5.00;
input bool   InpPropCloseAtEndHour=true;

input group "Execution"
input bool   InpAllowLong=true;
input bool   InpAllowShort=true;
input double InpMaximumSpreadATR=0.08;
input int    InpMaximumDeviationPoints=80;
input ulong  InpMagic=86831001;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar=0;
datetime g_position_open_bar=0;
long g_day_key=0;
int g_day_trades=0;
double g_day_start_equity=0.0;
double g_initial_equity=0.0;
bool g_day_locked=false;
bool g_account_locked=false;

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(double lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || lots<minimum) return 0.0;
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

long DateKey(const datetime when)
{
   MqlDateTime value={0};
   TimeToStruct(when,value);
   return (long)value.year*10000L+(long)value.mon*100L+value.day;
}

bool BufferValue(const int handle,const int shift,double &value)
{
   double values[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,values)!=1) return false;
   value=values[0];
   return MathIsValidNumber(value) && value!=EMPTY_VALUE && value>0.0;
}

bool IsValidCandle(const MqlRates &bar)
{
   double body=MathAbs(bar.close-bar.open);
   double upper=bar.high-MathMax(bar.open,bar.close);
   double lower=MathMin(bar.open,bar.close)-bar.low;
   return body>0.0 && body>MathMax(upper,lower);
}

bool HasManagedPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   return false;
}

void CloseManagedPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         g_trade.PositionClose(ticket,InpMaximumDeviationPoints);
   }
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double risk_percent=(InpProfile==STP_PROP_FIRM ? InpPropRiskPercent : InpNormalRiskPercent);
   double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*risk_percent/100.0;
   if(risk_money<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,result)) return 0.0;
   double loss_per_lot=MathAbs(result);
   if(loss_per_lot<=0.0) return 0.0;
   return NormalizeLots(risk_money/loss_per_lot);
}

void RefreshRiskState(const datetime now)
{
   long key=DateKey(now);
   if(key!=g_day_key)
   {
      g_day_key=key;
      g_day_trades=0;
      g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
      g_day_locked=false;
   }
   if(InpProfile!=STP_PROP_FIRM) return;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_day_start_equity>0.0 && InpPropDailyLossLimitPercent>0.0 &&
      equity<=g_day_start_equity*(1.0-InpPropDailyLossLimitPercent/100.0))
      g_day_locked=true;
   if(g_initial_equity>0.0 && InpPropOverallDrawdownLimitPercent>0.0 &&
      equity<=g_initial_equity*(1.0-InpPropOverallDrawdownLimitPercent/100.0))
      g_account_locked=true;

   if((g_day_locked || g_account_locked) && HasManagedPosition()) CloseManagedPosition();
}

bool TradingWindowPasses(const datetime now)
{
   MqlDateTime value={0};
   TimeToStruct(now,value);
   if(value.day_of_week==0 || value.day_of_week==6) return false;
   if(InpCloseFriday && value.day_of_week==5 && value.hour>=InpFridayCloseHour) return false;
   if(!InpUseTradingWindow) return true;
   if(InpStartHour==InpEndHour) return true;
   if(InpStartHour<InpEndHour) return value.hour>=InpStartHour && value.hour<InpEndHour;
   return value.hour>=InpStartHour || value.hour<InpEndHour;
}

void ApplyTimeExits(const datetime now)
{
   if(!HasManagedPosition()) return;
   MqlDateTime value={0};
   TimeToStruct(now,value);
   if(InpCloseFriday && value.day_of_week==5 && value.hour>=InpFridayCloseHour)
   {
      CloseManagedPosition();
      return;
   }
   if(InpProfile==STP_PROP_FIRM && InpPropCloseAtEndHour && InpUseTradingWindow &&
      value.hour>=InpEndHour)
   {
      CloseManagedPosition();
      return;
   }
   if(g_position_open_bar>0 && InpMaximumHoldingBars>0)
   {
      int shift=iBarShift(_Symbol,InpSignalTimeframe,g_position_open_bar,false);
      if(shift>=InpMaximumHoldingBars) CloseManagedPosition();
   }
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   return SymbolInfoTick(_Symbol,tick) && tick.ask>0.0 && tick.bid>0.0 &&
          tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool FindTriplePrint(MqlRates &rates[],const int direction,double &zone_low,double &zone_high)
{
   int found=0;
   zone_low=DBL_MAX;
   zone_high=-DBL_MAX;
   for(int index=2;index<=InpPullbackLookback+1;index++)
   {
      bool countertrend=(direction>0 ? rates[index].close<rates[index].open
                                     : rates[index].close>rates[index].open);
      if(!countertrend || !IsValidCandle(rates[index])) continue;
      zone_low=MathMin(zone_low,rates[index].low);
      zone_high=MathMax(zone_high,rates[index].high);
      found++;
      if(found>=InpRequiredValidCandles) break;
   }
   return found>=InpRequiredValidCandles && zone_low<zone_high;
}

bool WickGapPasses(MqlRates &rates[],const int direction,const double stop,const double atr)
{
   if(InpMinimumWickGapATR<=0.0) return true;
   double nearest=DBL_MAX;
   double second=DBL_MAX;
   for(int index=2;index<=InpPullbackLookback+InpStructureLookback;index++)
   {
      double distance=(direction>0 ? rates[index].low-stop : stop-rates[index].high);
      if(distance<0.0) continue;
      if(distance<nearest)
      {
         second=nearest;
         nearest=distance;
      }
      else if(distance<second) second=distance;
   }
   if(nearest==DBL_MAX || second==DBL_MAX) return false;
   return MathAbs(second-nearest)>=InpMinimumWickGapATR*atr;
}

int DetectSignal(MqlRates &rates[],const double atr,double &raw_stop)
{
   MqlRates signal=rates[1];
   if(!IsValidCandle(signal) || signal.high-signal.low<InpMinimumBreakoutATR*atr) return 0;

   double prior_high=-DBL_MAX;
   double prior_low=DBL_MAX;
   for(int index=3;index<=InpStructureLookback+2;index++)
   {
      prior_high=MathMax(prior_high,rates[index].high);
      prior_low=MathMin(prior_low,rates[index].low);
   }

   int direction=0;
   if(signal.close>signal.open && signal.close>prior_high) direction=1;
   if(signal.close<signal.open && signal.close<prior_low) direction=-1;
   if(direction==0) return 0;
   if((direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) return 0;

   double zone_low=0.0,zone_high=0.0;
   if(!FindTriplePrint(rates,direction,zone_low,zone_high)) return 0;
   raw_stop=(direction>0 ? zone_low-InpStopBufferATR*atr : zone_high+InpStopBufferATR*atr);
   if(!WickGapPasses(rates,direction,raw_stop,atr)) return 0;
   return direction;
}

bool SendTrade(const int direction,const double raw_stop,const double atr)
{
   if(HasManagedPosition() || g_day_locked || g_account_locked || !SpreadPasses(atr)) return false;
   int maximum=(InpProfile==STP_PROP_FIRM ? InpPropMaximumTradesPerDay : InpNormalMaximumTradesPerDay);
   if(g_day_trades>=maximum) return false;

   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(raw_stop);
   if((direction>0 && stop>=entry) || (direction<0 && stop<=entry)) return false;

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=NormalizePrice(entry-broker_gap);
   if(direction<0 && stop-entry<broker_gap) stop=NormalizePrice(entry+broker_gap);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   if((direction>0 && target-entry<broker_gap) || (direction<0 && entry-target<broker_gap)) return false;

   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   string comment=(InpProfile==STP_PROP_FIRM ? "STP Prop" : "STP Normal");
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(sent)
   {
      g_day_trades++;
      g_position_open_bar=iTime(_Symbol,InpSignalTimeframe,0);
   }
   return sent;
}

int OnInit()
{
   if(InpStructureLookback<5 || InpPullbackLookback<3 || InpRequiredValidCandles<1 ||
      InpRequiredValidCandles>InpPullbackLookback || InpATRPeriod<2 ||
      InpMinimumBreakoutATR<=0.0 || InpStopBufferATR<0.0 || InpRewardRisk<=0.0 ||
      InpNormalRiskPercent<=0.0 || InpPropRiskPercent<=0.0 || InpMagic==0)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_initial_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_day_start_equity=g_initial_equity;
   g_day_key=DateKey(TimeCurrent());
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   datetime now=TimeCurrent();
   RefreshRiskState(now);
   ApplyTimeExits(now);

   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(current_bar<=0 || current_bar==g_last_bar) return;
   g_last_bar=current_bar;
   if(!TradingWindowPasses(now) || HasManagedPosition() || g_day_locked || g_account_locked) return;

   double atr=0.0;
   if(!BufferValue(g_atr_handle,1,atr)) return;
   int need=InpStructureLookback+InpPullbackLookback+12;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,need,rates)<need) return;

   double raw_stop=0.0;
   int direction=DetectSignal(rates,atr,raw_stop);
   if(direction!=0) SendTrade(direction,raw_stop,atr);
}
