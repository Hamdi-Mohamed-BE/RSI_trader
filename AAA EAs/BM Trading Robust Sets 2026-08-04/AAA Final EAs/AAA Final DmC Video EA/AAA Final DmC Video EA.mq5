#property copyright "Mechanical implementation of the public DmC video supplied by the user"
#property version   "2.00"
#property strict

#include "..\AAA Final DmC EA\AAA_Final_Common.mqh"

enum DMC_ENTRY_MODE
{
   DMC_CONFIRMATION_CLOSE = 0,
   DMC_CONFIRMATION_RETEST = 1
};

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1082611;
input int    InpMaxSpreadPoints=0;
input int    InpMaxTradesPerDay=1;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H1;

input group "Video level definition"
input bool   InpUseDailyLevels=true;
input bool   InpUseWeeklyLevels=true;
input bool   InpUseMonthlyLevels=true;
input int    InpDailyLookback=90;
input int    InpWeeklyLookback=78;
input int    InpMonthlyLookback=36;
input int    InpATRPeriod=14;
input double InpDuplicateLevelATR=0.15;

input group "Failure, regain and entry"
input DMC_ENTRY_MODE InpEntryMode=DMC_CONFIRMATION_CLOSE;
input bool   InpAllowFirstTouchFailure=true;
input bool   InpAllowQuickRegain=true;
input bool   InpRequireCandleDirection=true;
input double InpTouchToleranceATR=0.08;
input double InpCloseConfirmationATR=0.03;

input group "Video exits"
input double InpLevelBufferATR=0.08;
input double InpTargetFrontRunATR=0.03;
input double InpMinimumRR=1.0;
input double InpMaximumRR=8.0;
input bool   InpAllowSwingFallback=true;
input int    InpFallbackSwingBars=24;
input double InpMaximumStopATR=8.0;

struct DMCLevel
{
   double price;
   ENUM_TIMEFRAMES source_tf;
   datetime source_open;
   datetime source_close;
};

datetime g_dmc_last_bar=0;

bool DMC_SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

int DMC_TimeframeStrength(const ENUM_TIMEFRAMES timeframe)
{
   if(timeframe==PERIOD_MN1) return 3;
   if(timeframe==PERIOD_W1) return 2;
   return 1;
}

void DMC_AddLevel(DMCLevel &levels[],const double price,const ENUM_TIMEFRAMES timeframe,
                  const datetime source_open,const datetime source_close,const double duplicate_tolerance)
{
   if(price<=0.0 || source_close<=source_open) return;
   for(int i=0;i<ArraySize(levels);i++)
   {
      if(MathAbs(levels[i].price-price)>duplicate_tolerance) continue;
      if(DMC_TimeframeStrength(timeframe)>DMC_TimeframeStrength(levels[i].source_tf))
      {
         levels[i].price=price;
         levels[i].source_tf=timeframe;
         levels[i].source_open=source_open;
         levels[i].source_close=source_close;
      }
      return;
   }
   int size=ArraySize(levels);
   ArrayResize(levels,size+1);
   levels[size].price=price;
   levels[size].source_tf=timeframe;
   levels[size].source_open=source_open;
   levels[size].source_close=source_close;
}

void DMC_AddTimeframeLevels(DMCLevel &levels[],const ENUM_TIMEFRAMES timeframe,const int lookback,
                            const double duplicate_tolerance)
{
   if(lookback<1) return;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,timeframe,0,lookback+2,bars);
   if(copied<3) return;
   datetime current_period_open=bars[0].time;
   int maximum=MathMin(lookback,copied-1);
   for(int shift=1;shift<=maximum;shift++)
   {
      datetime close_time=(shift==1 ? current_period_open : bars[shift-1].time);
      double body_low=MathMin(bars[shift].open,bars[shift].close);
      double body_high=MathMax(bars[shift].open,bars[shift].close);
      DMC_AddLevel(levels,body_low,timeframe,bars[shift].time,close_time,duplicate_tolerance);
      DMC_AddLevel(levels,body_high,timeframe,bars[shift].time,close_time,duplicate_tolerance);
   }
}

bool DMC_BuildLevels(DMCLevel &levels[],const double atr)
{
   ArrayResize(levels,0);
   double duplicate_tolerance=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),atr*InpDuplicateLevelATR);
   if(InpUseDailyLevels) DMC_AddTimeframeLevels(levels,PERIOD_D1,InpDailyLookback,duplicate_tolerance);
   if(InpUseWeeklyLevels) DMC_AddTimeframeLevels(levels,PERIOD_W1,InpWeeklyLookback,duplicate_tolerance);
   if(InpUseMonthlyLevels) DMC_AddTimeframeLevels(levels,PERIOD_MN1,InpMonthlyLookback,duplicate_tolerance);
   return ArraySize(levels)>=3;
}

bool DMC_RangeTouchesLevel(const datetime from_time,const datetime to_time,const ENUM_TIMEFRAMES timeframe,
                           const double level,const double tolerance)
{
   if(to_time<from_time) return false;
   MqlRates bars[];
   int copied=CopyRates(_Symbol,timeframe,from_time,to_time,bars);
   if(copied<=0) return false;
   for(int i=0;i<copied;i++)
      if(bars[i].low<=level+tolerance && bars[i].high>=level-tolerance) return true;
   return false;
}

bool DMC_IsUntestedBefore(const DMCLevel &level,const datetime signal_open,const double tolerance)
{
   if(level.source_close<=0 || level.source_close>=signal_open) return false;
   datetime current_source_open=iTime(_Symbol,level.source_tf,0);
   if(current_source_open<=0) return false;

   if(level.source_close<current_source_open &&
      DMC_RangeTouchesLevel(level.source_close,current_source_open-1,level.source_tf,level.price,tolerance))
      return false;

   datetime lower_start=MathMax(level.source_close,current_source_open);
   if(lower_start<signal_open &&
      DMC_RangeTouchesLevel(lower_start,signal_open-1,InpSignalTimeframe,level.price,tolerance))
      return false;

   return true;
}

int DMC_TodayTradeCount()
{
   datetime start=AAA_UTCDateTime(TimeCurrent(),0);
   if(!HistorySelect(start,TimeCurrent())) return 0;
   int count=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(ticket,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN) count++;
   }
   return count;
}

bool DMC_FirstTouchSignal(const DMCLevel &level,MqlRates &bars[],const int direction,
                          const double tolerance,const double confirmation)
{
   if(InpEntryMode==DMC_CONFIRMATION_CLOSE)
   {
      if(!DMC_IsUntestedBefore(level,bars[1].time,tolerance)) return false;
      if(direction>0)
      {
         if(bars[1].low>level.price+tolerance || bars[1].close<=level.price+confirmation) return false;
         if(InpRequireCandleDirection && bars[1].close<=bars[1].open) return false;
      }
      else
      {
         if(bars[1].high<level.price-tolerance || bars[1].close>=level.price-confirmation) return false;
         if(InpRequireCandleDirection && bars[1].close>=bars[1].open) return false;
      }
      return true;
   }

   if(!DMC_IsUntestedBefore(level,bars[2].time,tolerance)) return false;
   if(direction>0)
   {
      bool rejection=(bars[2].low<=level.price+tolerance && bars[2].close>level.price+confirmation);
      bool retest=(bars[1].low<=level.price+tolerance && bars[1].close>level.price+confirmation);
      if(InpRequireCandleDirection) retest=(retest && bars[1].close>bars[1].open);
      return rejection && retest;
   }
   bool rejection=(bars[2].high>=level.price-tolerance && bars[2].close<level.price-confirmation);
   bool retest=(bars[1].high>=level.price-tolerance && bars[1].close<level.price-confirmation);
   if(InpRequireCandleDirection) retest=(retest && bars[1].close<bars[1].open);
   return rejection && retest;
}

bool DMC_QuickRegainSignal(const DMCLevel &level,MqlRates &bars[],const int direction,const double confirmation)
{
   if(InpEntryMode==DMC_CONFIRMATION_CLOSE)
   {
      if(direction>0)
         return bars[2].close<level.price-confirmation && bars[1].close>level.price+confirmation;
      return bars[2].close>level.price+confirmation && bars[1].close<level.price-confirmation;
   }

   if(direction>0)
   {
      bool regained=(bars[3].close<level.price-confirmation && bars[2].close>level.price+confirmation);
      bool retest=(bars[1].low<=level.price && bars[1].close>level.price+confirmation);
      if(InpRequireCandleDirection) retest=(retest && bars[1].close>bars[1].open);
      return regained && retest;
   }
   bool regained=(bars[3].close>level.price+confirmation && bars[2].close<level.price-confirmation);
   bool retest=(bars[1].high>=level.price && bars[1].close<level.price-confirmation);
   if(InpRequireCandleDirection) retest=(retest && bars[1].close<bars[1].open);
   return regained && retest;
}

bool DMC_FindBracket(DMCLevel &levels[],MqlRates &bars[],const int direction,const double signal_level,
                     const double entry,const double atr,double &stop,double &target)
{
   double separation=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),atr*InpDuplicateLevelATR);
   double nearest_below=-DBL_MAX;
   double nearest_above=DBL_MAX;
   for(int i=0;i<ArraySize(levels);i++)
   {
      if(levels[i].price<signal_level-separation && levels[i].price>nearest_below)
         nearest_below=levels[i].price;
      if(levels[i].price>signal_level+separation && levels[i].price<nearest_above)
         nearest_above=levels[i].price;
   }

   if(InpAllowSwingFallback)
   {
      int count=MathMin(InpFallbackSwingBars,ArraySize(bars)-1);
      double swing_low=DBL_MAX,swing_high=-DBL_MAX;
      for(int i=1;i<=count;i++)
      {
         swing_low=MathMin(swing_low,bars[i].low);
         swing_high=MathMax(swing_high,bars[i].high);
      }
      if(nearest_below==-DBL_MAX && swing_low<signal_level-separation) nearest_below=swing_low;
      if(nearest_above==DBL_MAX && swing_high>signal_level+separation) nearest_above=swing_high;
   }

   if(nearest_below==-DBL_MAX || nearest_above==DBL_MAX) return false;
   if(direction>0)
   {
      stop=nearest_below-atr*InpLevelBufferATR;
      target=nearest_above-atr*InpTargetFrontRunATR;
      if(stop>=entry || target<=entry) return false;
   }
   else
   {
      stop=nearest_above+atr*InpLevelBufferATR;
      target=nearest_below+atr*InpTargetFrontRunATR;
      if(stop<=entry || target>=entry) return false;
   }

   double risk=MathAbs(entry-stop);
   double reward=MathAbs(target-entry);
   if(risk<=0.0 || reward<=0.0 || risk>InpMaximumStopATR*atr) return false;
   double rr=reward/risk;
   return rr>=InpMinimumRR && rr<=InpMaximumRR;
}

bool DMC_SendMarket(const int direction,const double stop,const double target,const string reason)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=AAA_Price(_Symbol,stop);
   double tp=AAA_Price(_Symbol,target);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(direction>0 && (sl>=entry-minimum_distance || tp<=entry+minimum_distance)) return false;
   if(direction<0 && (sl<=entry+minimum_distance || tp>=entry-minimum_distance)) return false;

   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=AAA_LotsForRisk(_Symbol,type,entry,sl,InpRiskPercent);
   if(lots<=0.0)
   {
      Print("DMC video: calculated size is below the broker minimum or contract data is unavailable");
      return false;
   }

   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(20);
   if(direction>0) return AAA_Trade.Buy(lots,_Symbol,0.0,sl,tp,reason);
   return AAA_Trade.Sell(lots,_Symbol,0.0,sl,tp,reason);
}

void DMC_Run()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_dmc_last_bar)) return;
   if(!InpEnableTrading || !DMC_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   if(InpMaxTradesPerDay>0 && DMC_TodayTradeCount()>=InpMaxTradesPerDay) return;

   int required=MathMax(InpFallbackSwingBars+3,8);
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required,bars)<required) return;
   double atr=AAA_ATR(_Symbol,InpSignalTimeframe,InpATRPeriod,1);
   if(atr<=0.0 || atr==EMPTY_VALUE) return;

   DMCLevel levels[];
   if(!DMC_BuildLevels(levels,atr)) return;
   double tolerance=atr*InpTouchToleranceATR;
   double confirmation=atr*InpCloseConfirmationATR;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;

   int best_direction=0;
   double best_level=0.0,best_distance=DBL_MAX;
   string best_reason="";
   for(int i=0;i<ArraySize(levels);i++)
   {
      for(int direction=-1;direction<=1;direction+=2)
      {
         bool first_touch=InpAllowFirstTouchFailure && DMC_FirstTouchSignal(levels[i],bars,direction,tolerance,confirmation);
         bool regain=InpAllowQuickRegain && DMC_QuickRegainSignal(levels[i],bars,direction,confirmation);
         if(!first_touch && !regain) continue;
         double entry=(direction>0 ? tick.ask : tick.bid);
         double distance=MathAbs(entry-levels[i].price);
         if(distance>=best_distance) continue;
         best_direction=direction;
         best_level=levels[i].price;
         best_distance=distance;
         best_reason=(first_touch ? "DMCV2 level failure" : "DMCV2 quick regain");
      }
   }
   if(best_direction==0) return;

   double entry=(best_direction>0 ? tick.ask : tick.bid);
   double stop=0.0,target=0.0;
   if(!DMC_FindBracket(levels,bars,best_direction,best_level,entry,atr,stop,target)) return;
   DMC_SendMarket(best_direction,stop,target,best_reason);
}

int OnInit()
{
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   Print("AAA Final DmC Video EA loaded on ",_Symbol,
         ". Video-mechanical rules; risk=",DoubleToString(InpRiskPercent,2),"%.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   DMC_Run();
}

