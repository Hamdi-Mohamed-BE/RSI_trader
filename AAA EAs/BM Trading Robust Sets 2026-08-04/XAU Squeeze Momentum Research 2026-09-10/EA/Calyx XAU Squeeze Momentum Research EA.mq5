#property copyright "Calyx research - H1 squeeze momentum breakout"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=5.0;
input double InpMaximumEffectiveLeverage=9.8;
input long   InpMagic=1091010;
input string InpTradeComment="SQZ-H1-STD";
input int    InpMaximumSpreadPoints=0;

input group "Squeeze and momentum"
input int    InpSqueezeLength=20;
input double InpBollingerMultiplier=2.0;
input double InpKeltnerMultiplier=1.5;
input int    InpMomentumLength=20;
input int    InpTrendSMAPeriod=200;
input bool   InpRequireMomentumRising=true;

input group "Protection and exits"
input int    InpATRPeriod=14;
input int    InpATRMethod=0;                  // 0 Wilder ATR (raw rule), 1 simple mean true range
input double InpStopATR=3.0;
input double InpTargetR=2.0;
input int    InpTrailingMode=1;              // 0 none, 1 H1 ATR ratchet, 2 completed-M15 Dynamic, 3 completed-H1 low
input double InpTrailATR=3.0;
input double InpBreakEvenAtR=0.0;            // 0 disables tick-level break-even
input double InpPartialExitAtR=0.0;           // 0 disables the partial exit
input double InpPartialExitFraction=0.50;
input int    InpMomentumExitMode=2;           // 0 off, 1 negative only, 2 negative or loses configured fraction
input double InpMomentumFadeFraction=0.50;
input int    InpMaximumHoldH1Bars=0;          // 0 disables the time exit
input double InpDynamicTriggerFraction=0.50;
input double InpDynamicLockFraction=0.20;

input group "UTC entry filter"
input int    InpSessionStartHourUTC=0;
input int    InpSessionEndHourUTC=24;
input int    InpWeekdayMask=62;               // bits 1..5 = Monday..Friday

CTrade Trade;
datetime g_last_h1_bar=0;
datetime g_last_m15_bar=0;
datetime g_entry_time=0;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_initial_target=0.0;
double g_highest_completed_high=0.0;
double g_initial_volume=0.0;
bool g_partial_done=false;

double Price(const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

bool SelectOurPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic &&
         PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) return true;
   }
   return false;
}

double SMA(const MqlRates &bars[],const int shift,const int length)
{
   double sum=0.0;
   for(int i=shift;i<shift+length;i++) sum+=bars[i].close;
   return sum/(double)length;
}

double MeanTrueRange(const MqlRates &bars[],const int shift,const int length)
{
   double sum=0.0;
   for(int i=shift;i<shift+length;i++)
   {
      double prior_close=bars[i+1].close;
      double tr=MathMax(bars[i].high-bars[i].low,
                        MathMax(MathAbs(bars[i].high-prior_close),MathAbs(bars[i].low-prior_close)));
      sum+=tr;
   }
   return sum/(double)length;
}

double TrueRangeAt(const MqlRates &bars[],const int shift)
{
   double prior_close=bars[shift+1].close;
   return MathMax(bars[shift].high-bars[shift].low,
                  MathMax(MathAbs(bars[shift].high-prior_close),MathAbs(bars[shift].low-prior_close)));
}

double WilderATR(const MqlRates &bars[],const int shift,const int length)
{
   // Seed well before the requested completed bar and roll forward.  The burn-in
   // keeps the result independent of the arbitrary first bar loaded by the EA.
   const int burn_in=100;
   int seed_shift=shift+burn_in;
   double atr=0.0;
   for(int i=seed_shift;i<seed_shift+length;i++) atr+=TrueRangeAt(bars,i);
   atr/=(double)length;
   for(int i=seed_shift-1;i>=shift;i--)
      atr=(atr*(double)(length-1)+TrueRangeAt(bars,i))/(double)length;
   return atr;
}

bool SqueezeOn(const MqlRates &bars[],const int shift)
{
   int length=InpSqueezeLength;
   double basis=SMA(bars,shift,length);
   double variance=0.0;
   for(int i=shift;i<shift+length;i++) variance+=MathPow(bars[i].close-basis,2.0);
   double deviation=MathSqrt(variance/(double)length);
   double range=MeanTrueRange(bars,shift,length);
   double upper_bb=basis+InpBollingerMultiplier*deviation;
   double lower_bb=basis-InpBollingerMultiplier*deviation;
   double upper_kc=basis+InpKeltnerMultiplier*range;
   double lower_kc=basis-InpKeltnerMultiplier*range;
   return lower_bb>lower_kc && upper_bb<upper_kc;
}

double MomentumSource(const MqlRates &bars[],const int shift)
{
   double highest=bars[shift].high;
   double lowest=bars[shift].low;
   for(int i=shift+1;i<shift+InpSqueezeLength;i++)
   {
      highest=MathMax(highest,bars[i].high);
      lowest=MathMin(lowest,bars[i].low);
   }
   double midpoint=(highest+lowest)/2.0;
   double close_average=SMA(bars,shift,InpSqueezeLength);
   double blended_midline=(midpoint+close_average)/2.0;
   return bars[shift].close-blended_midline;
}

double LinearRegressionMomentum(const MqlRates &bars[],const int shift)
{
   int length=InpMomentumLength;
   double sum_x=(double)length*(length-1)/2.0;
   double sum_x2=(double)(length-1)*length*(2*length-1)/6.0;
   double sum_y=0.0;
   double sum_xy=0.0;
   for(int x=0;x<length;x++)
   {
      int series_index=shift+(length-1-x);
      double y=MomentumSource(bars,series_index);
      sum_y+=y;
      sum_xy+=(double)x*y;
   }
   double denominator=(double)length*sum_x2-sum_x*sum_x;
   if(MathAbs(denominator)<DBL_EPSILON) return 0.0;
   double slope=((double)length*sum_xy-sum_x*sum_y)/denominator;
   double intercept=(sum_y-slope*sum_x)/(double)length;
   return intercept+slope*(length-1);
}

bool LoadH1(MqlRates &bars[])
{
   int need=MathMax(InpTrendSMAPeriod,
                    MathMax(InpMomentumLength+InpSqueezeLength,InpATRPeriod+105))+8;
   ArraySetAsSeries(bars,true);
   return CopyRates(_Symbol,PERIOD_H1,1,need,bars)>=need;
}

double ATRAt(const MqlRates &bars[],const int shift)
{
   if(InpATRMethod==1) return MeanTrueRange(bars,shift,InpATRPeriod);
   return WilderATR(bars,shift,InpATRPeriod);
}

bool SessionAllowed(const datetime bar_time)
{
   MqlDateTime part;
   TimeToStruct(bar_time,part);
   if((InpWeekdayMask & (1<<part.day_of_week))==0) return false;
   if(InpSessionStartHourUTC==0 && InpSessionEndHourUTC==24) return true;
   if(InpSessionStartHourUTC<InpSessionEndHourUTC)
      return part.hour>=InpSessionStartHourUTC && part.hour<InpSessionEndHourUTC;
   return part.hour>=InpSessionStartHourUTC || part.hour<InpSessionEndHourUTC;
}

double NormalizeLots(const double requested,const bool round_up=true)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(requested<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0) return 0.0;
   if(!round_up && requested<minimum) return 0.0;
   double lots=round_up
      ? MathCeil((MathMin(requested,maximum)-1e-12)/step)*step
      : MathFloor((MathMin(requested,maximum)+1e-12)/step)*step;
   lots=MathMin(maximum,lots);
   if(round_up) lots=MathMax(minimum,lots);
   else if(lots<minimum) return 0.0;
   if(round_up && lots>requested+1e-12)
      PrintFormat("Squeeze Momentum risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",requested,lots);
   int digits=(int)MathMax(0,MathRound(-MathLog10(step)));
   return NormalizeDouble(lots,digits);
}

double LotsForRiskAndLeverage(const double entry,const double stop)
{
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double one_lot_loss=0.0;
   if(equity<=0.0 || !OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,stop,one_lot_loss)) return 0.0;
   one_lot_loss=MathAbs(one_lot_loss);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_lots=equity*(InpRiskPercent/100.0)/one_lot_loss;
   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double leverage_lots=(contract>0.0 && entry>0.0)
                        ? equity*InpMaximumEffectiveLeverage/(contract*entry)
                        : risk_lots;
   return NormalizeLots(MathMin(risk_lots,leverage_lots));
}

bool EntrySignal(const MqlRates &bars[],double &atr,double &momentum)
{
   if(!SqueezeOn(bars,1) || SqueezeOn(bars,0)) return false;
   momentum=LinearRegressionMomentum(bars,0);
   double prior=LinearRegressionMomentum(bars,1);
   if(momentum<=0.0 || (InpRequireMomentumRising && momentum<=prior)) return false;
   if(bars[0].close<=SMA(bars,0,InpTrendSMAPeriod)) return false;
   atr=ATRAt(bars,0);
   return atr>0.0 && MathIsValidNumber(atr);
}

void RestorePositionState()
{
   if(!SelectOurPosition()) return;
   g_entry_time=(datetime)PositionGetInteger(POSITION_TIME);
   g_initial_entry=PositionGetDouble(POSITION_PRICE_OPEN);
   g_initial_stop=PositionGetDouble(POSITION_SL);
   g_initial_target=PositionGetDouble(POSITION_TP);
   if(g_initial_volume<=0.0) g_initial_volume=PositionGetDouble(POSITION_VOLUME);
   if(g_highest_completed_high<=0.0) g_highest_completed_high=g_initial_entry;
}

bool ModifyStop(const double candidate)
{
   if(!SelectOurPosition()) return false;
   ulong ticket=(ulong)PositionGetInteger(POSITION_TICKET);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double current_sl=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=(double)MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                  SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   double next=Price(candidate);
   if(next<=current_sl+point || next>=tick.bid-minimum) return false;
   return Trade.PositionModify(ticket,next,target);
}

void ManageAtNewH1(const MqlRates &bars[])
{
   if(!SelectOurPosition()) return;
   RestorePositionState();
   double current_momentum=LinearRegressionMomentum(bars,0);
   double prior_momentum=LinearRegressionMomentum(bars,1);
   bool exit_momentum=(InpMomentumExitMode>=1 && current_momentum<=0.0);
   if(InpMomentumExitMode>=2 && prior_momentum>0.0 &&
      current_momentum<prior_momentum*(1.0-InpMomentumFadeFraction)) exit_momentum=true;
   int held_bars=g_entry_time>0 ? iBarShift(_Symbol,PERIOD_H1,g_entry_time,false) : 0;
   bool exit_time=InpMaximumHoldH1Bars>0 && held_bars>=InpMaximumHoldH1Bars;
   if(exit_momentum || exit_time)
   {
      ulong ticket=(ulong)PositionGetInteger(POSITION_TICKET);
      Trade.PositionClose(ticket);
      return;
   }
   if(InpTrailingMode==1)
   {
      g_highest_completed_high=MathMax(g_highest_completed_high,bars[0].high);
      double atr=ATRAt(bars,0);
      if(atr>0.0) ModifyStop(g_highest_completed_high-InpTrailATR*atr);
   }
   else if(InpTrailingMode==3)
      ModifyStop(bars[0].low);
}

void ManageDynamicM15()
{
   if(InpTrailingMode!=2 || !SelectOurPosition()) return;
   datetime current=iTime(_Symbol,PERIOD_M15,0);
   if(current<=0 || current==g_last_m15_bar) return;
   g_last_m15_bar=current;
   RestorePositionState();
   if(g_initial_entry<=0.0 || g_initial_stop>=g_initial_entry) return;
   double completed_close=iClose(_Symbol,PERIOD_M15,1);
   double path=g_initial_target>g_initial_entry
               ? g_initial_target-g_initial_entry
               : g_initial_entry-g_initial_stop;
   if(completed_close>=g_initial_entry+InpDynamicTriggerFraction*path)
      ModifyStop(g_initial_entry+InpDynamicLockFraction*path);
}

void ManageIntrabar()
{
   if(!SelectOurPosition()) return;
   RestorePositionState();
   if(g_initial_entry<=0.0 || g_initial_stop>=g_initial_entry) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0) return;
   double one_r=g_initial_entry-g_initial_stop;
   if(InpBreakEvenAtR>0.0 && tick.bid>=g_initial_entry+InpBreakEvenAtR*one_r)
      ModifyStop(g_initial_entry);
   if(!g_partial_done && InpPartialExitAtR>0.0 &&
      tick.bid>=g_initial_entry+InpPartialExitAtR*one_r)
   {
      double current=PositionGetDouble(POSITION_VOLUME);
      double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
      double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
      double close_lots=NormalizeLots(g_initial_volume*InpPartialExitFraction,false);
      if(close_lots>=minimum && current-close_lots>=minimum-step*0.1)
      {
         ulong ticket=(ulong)PositionGetInteger(POSITION_TICKET);
         if(Trade.PositionClosePartial(ticket,close_lots)) g_partial_done=true;
      }
      else g_partial_done=true;
   }
}

void TryEnter(const MqlRates &bars[])
{
   if(!InpEnableTrading || SelectOurPosition() || !SessionAllowed(bars[0].time)) return;
   if(!HAMA_SafeRegimeAllowsDirection(1)) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0) return;
   if(InpMaximumSpreadPoints>0 &&
      (tick.ask-tick.bid)/SymbolInfoDouble(_Symbol,SYMBOL_POINT)>InpMaximumSpreadPoints) return;
   double atr=0.0;
   double momentum=0.0;
   if(!EntrySignal(bars,atr,momentum)) return;
   double entry=tick.ask;
   double stop=Price(entry-InpStopATR*atr);
   double target=InpTargetR>0.0 ? Price(entry+InpStopATR*atr*InpTargetR) : 0.0;
   double lots=LotsForRiskAndLeverage(entry,stop);
   if(lots<=0.0) return;
   Trade.SetExpertMagicNumber((ulong)InpMagic);
   Trade.SetTypeFillingBySymbol(_Symbol);
   if(!Trade.Buy(lots,_Symbol,0.0,stop,target,InpTradeComment)) return;
   g_entry_time=TimeCurrent();
   g_initial_entry=Trade.ResultPrice()>0.0 ? Trade.ResultPrice() : entry;
   g_initial_stop=stop;
   g_initial_target=target;
   g_highest_completed_high=g_initial_entry;
   g_initial_volume=lots;
   g_partial_done=false;
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpMaximumEffectiveLeverage<=0.0 ||
      InpSqueezeLength<5 || InpMomentumLength<5 || InpTrendSMAPeriod<20 ||
      InpATRPeriod<2 || InpATRMethod<0 || InpATRMethod>1 ||
      InpStopATR<=0.0 || InpTargetR<0.0 ||
      InpTrailingMode<0 || InpTrailingMode>3 || InpTrailATR<=0.0 ||
      InpBreakEvenAtR<0.0 || InpPartialExitAtR<0.0 ||
      InpPartialExitFraction<=0.0 || InpPartialExitFraction>=1.0 ||
      InpMomentumExitMode<0 || InpMomentumExitMode>2 ||
      InpMomentumFadeFraction<0.0 || InpMomentumFadeFraction>1.0 ||
      InpDynamicTriggerFraction<=0.0 || InpDynamicLockFraction<0.0 ||
      InpDynamicLockFraction>=InpDynamicTriggerFraction ||
      InpSessionStartHourUTC<0 || InpSessionStartHourUTC>23 ||
      InpSessionEndHourUTC<1 || InpSessionEndHourUTC>24) return INIT_PARAMETERS_INCORRECT;
   Trade.SetExpertMagicNumber((ulong)InpMagic);
   Trade.SetTypeFillingBySymbol(_Symbol);
   g_last_h1_bar=iTime(_Symbol,PERIOD_H1,0);
   g_last_m15_bar=iTime(_Symbol,PERIOD_M15,0);
   RestorePositionState();
   return INIT_SUCCEEDED;
}

void OnTick()
{
   ManageIntrabar();
   ManageDynamicM15();
   datetime current=iTime(_Symbol,PERIOD_H1,0);
   if(current<=0 || current==g_last_h1_bar) return;
   g_last_h1_bar=current;
   MqlRates bars[];
   if(!LoadH1(bars)) return;
   ManageAtNewH1(bars);
   TryEnter(bars);
}
