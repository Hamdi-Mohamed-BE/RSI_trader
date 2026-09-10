#property copyright "Calyx isolated DMC H4 fresh-ladder research build"
#property version   "1.00"
#property strict

#include "..\..\BM Trading\AAA Final\AAA Final DmC EA\AAA_Final_Common.mqh"

enum CALYX_H4_ENTRY_MODE
{
   CALYX_TOUCH_ENTRY = 0,
   CALYX_CONFIRMED_M15_ENTRY = 1
};

enum CALYX_H4_STOP_MODE
{
   CALYX_ATR_STOP = 0,
   CALYX_PREVIOUS_M15_EXTREME = 1,
   CALYX_COMPLETED_TOUCH_BAR_EXTREME = 2
};

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1091001;
input int    InpMaxTradesPerDay=2;
input int    InpMaxSpreadPoints=0;

input group "H4 ladder"
input int    InpH4LookbackBars=360;
input int    InpATRPeriod=14;
input double InpDuplicateLevelH4ATR=0.10;
input double InpTouchToleranceM15ATR=0.05;
input int    InpMaximumPriorM15Touches=0;

input group "No-lookahead entry and stop"
input CALYX_H4_ENTRY_MODE InpEntryMode=CALYX_TOUCH_ENTRY;
input CALYX_H4_STOP_MODE  InpStopMode=CALYX_ATR_STOP;
input double InpStopM15ATR=1.0;
input double InpStopBufferM15ATR=0.02;
input bool   InpConfirmedRequireOpenOnApproachSide=true;

input group "Same-H4-ladder target"
input double InpTargetFrontRunM15ATR=0.0;
input double InpMinimumRR=0.0;
input double InpMaximumRR=20.0;
input double InpMaximumStopM15ATR=8.0;

input group "Optional research session"
input bool InpUseUTCSession=false;
input int  InpSessionStartHourUTC=0;
input int  InpSessionEndHourUTC=24;

struct H4Level
{
   double price;
   datetime source_open;
   datetime source_close;
   int prior_touches;
   bool consumed;
};

H4Level g_levels[];
datetime g_last_m15_bar=0;
datetime g_last_h4_bar=0;
double g_last_mid=0.0;
double g_m15_atr=0.0;
double g_h4_atr=0.0;

bool H4L_SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 &&
          (tick.ask-tick.bid)/point<=(double)InpMaxSpreadPoints;
}

bool H4L_SessionAllowed(const datetime server_time)
{
   if(!InpUseUTCSession) return true;
   MqlDateTime utc;
   TimeToStruct(AAA_ToUTC(server_time),utc);
   if(InpSessionStartHourUTC==InpSessionEndHourUTC) return true;
   if(InpSessionStartHourUTC<InpSessionEndHourUTC)
      return utc.hour>=InpSessionStartHourUTC && utc.hour<InpSessionEndHourUTC;
   return utc.hour>=InpSessionStartHourUTC || utc.hour<InpSessionEndHourUTC;
}

int H4L_TodayTradeCount()
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
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN)
         count++;
   }
   return count;
}

void H4L_AddLevel(H4Level &levels[],const double price,const datetime source_open,
                  const datetime source_close,const double duplicate_tolerance)
{
   if(price<=0.0 || source_close<=source_open) return;
   for(int i=0;i<ArraySize(levels);i++)
   {
      if(MathAbs(levels[i].price-price)>duplicate_tolerance) continue;
      // Initial bars are processed newest first. During the live run, replace an
      // older clustered rail when a newly completed H4 candle creates a fresh one.
      if(source_close>levels[i].source_close)
      {
         levels[i].price=price;
         levels[i].source_open=source_open;
         levels[i].source_close=source_close;
         levels[i].prior_touches=0;
         levels[i].consumed=false;
      }
      return;
   }
   int size=ArraySize(levels);
   ArrayResize(levels,size+1);
   levels[size].price=price;
   levels[size].source_open=source_open;
   levels[size].source_close=source_close;
   levels[size].prior_touches=0;
   levels[size].consumed=false;
}

bool H4L_BuildLevels()
{
   ArrayResize(g_levels,0);
   g_h4_atr=AAA_ATR(_Symbol,PERIOD_H4,InpATRPeriod,1);
   g_m15_atr=AAA_ATR(_Symbol,PERIOD_M15,InpATRPeriod,1);
   if(g_h4_atr<=0.0 || g_h4_atr==EMPTY_VALUE ||
      g_m15_atr<=0.0 || g_m15_atr==EMPTY_VALUE)
      return false;

   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int requested=MathMax(3,InpH4LookbackBars+2);
   int copied=CopyRates(_Symbol,PERIOD_H4,0,requested,bars);
   if(copied<3) return false;
   int maximum=MathMin(InpH4LookbackBars,copied-1);
   double duplicate_tolerance=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),
                                      g_h4_atr*InpDuplicateLevelH4ATR);
   datetime current_h4_open=bars[0].time;
   for(int shift=1;shift<=maximum;shift++)
   {
      datetime close_time=(shift==1 ? current_h4_open : bars[shift-1].time);
      double body_low=MathMin(bars[shift].open,bars[shift].close);
      double body_high=MathMax(bars[shift].open,bars[shift].close);
      H4L_AddLevel(g_levels,body_low,bars[shift].time,close_time,duplicate_tolerance);
      H4L_AddLevel(g_levels,body_high,bars[shift].time,close_time,duplicate_tolerance);
   }
   return ArraySize(g_levels)>=3;
}

int H4L_HistoricalTouchCount(const H4Level &level,const datetime cutoff,const double tolerance)
{
   if(level.source_close<=0 || level.source_close>cutoff) return 1000000;
   MqlRates bars[];
   int copied=CopyRates(_Symbol,PERIOD_M15,level.source_close,cutoff-1,bars);
   if(copied<=0) return 0;
   int touches=0;
   for(int i=0;i<copied;i++)
   {
      if(bars[i].low<=level.price+tolerance && bars[i].high>=level.price-tolerance)
      {
         touches++;
         if(touches>InpMaximumPriorM15Touches) return touches;
      }
   }
   return touches;
}

void H4L_InitializeTouchCounts(const datetime cutoff)
{
   double tolerance=g_m15_atr*InpTouchToleranceM15ATR;
   for(int i=0;i<ArraySize(g_levels);i++)
      g_levels[i].prior_touches=H4L_HistoricalTouchCount(g_levels[i],cutoff,tolerance);
}

bool H4L_IsFresh(const H4Level &level,const datetime cutoff)
{
   if(level.consumed || level.source_close<=0 || level.source_close>cutoff) return false;
   return level.prior_touches<=InpMaximumPriorM15Touches;
}

void H4L_RecordCompletedM15(const MqlRates &bar)
{
   double tolerance=g_m15_atr*InpTouchToleranceM15ATR;
   for(int i=0;i<ArraySize(g_levels);i++)
   {
      if(g_levels[i].source_close>bar.time) continue;
      if(bar.low<=g_levels[i].price+tolerance && bar.high>=g_levels[i].price-tolerance)
         g_levels[i].prior_touches++;
   }
}

void H4L_PruneOldLevels()
{
   datetime oldest=iTime(_Symbol,PERIOD_H4,InpH4LookbackBars);
   if(oldest<=0) return;
   int write=0;
   for(int read=0;read<ArraySize(g_levels);read++)
   {
      if(g_levels[read].source_open<oldest) continue;
      if(write!=read) g_levels[write]=g_levels[read];
      write++;
   }
   ArrayResize(g_levels,write);
}

void H4L_AddLatestClosedH4()
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_H4,0,2,bars)<2) return;
   double duplicate_tolerance=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),
                                      g_h4_atr*InpDuplicateLevelH4ATR);
   double body_low=MathMin(bars[1].open,bars[1].close);
   double body_high=MathMax(bars[1].open,bars[1].close);
   H4L_AddLevel(g_levels,body_low,bars[1].time,bars[0].time,duplicate_tolerance);
   H4L_AddLevel(g_levels,body_high,bars[1].time,bars[0].time,duplicate_tolerance);
   H4L_PruneOldLevels();
}

bool H4L_FindTarget(const int direction,const double entry,const double signal_level,double &target)
{
   double separation=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),
                             g_h4_atr*InpDuplicateLevelH4ATR);
   double candidate=(direction>0 ? DBL_MAX : -DBL_MAX);
   for(int i=0;i<ArraySize(g_levels);i++)
   {
      if(direction>0 && g_levels[i].price>MathMax(entry,signal_level)+separation &&
         g_levels[i].price<candidate)
         candidate=g_levels[i].price;
      if(direction<0 && g_levels[i].price<MathMin(entry,signal_level)-separation &&
         g_levels[i].price>candidate)
         candidate=g_levels[i].price;
   }
   if((direction>0 && candidate==DBL_MAX) || (direction<0 && candidate==-DBL_MAX))
      return false;
   target=candidate-direction*g_m15_atr*InpTargetFrontRunM15ATR;
   return direction*(target-entry)>0.0;
}

bool H4L_BuildStopAndTarget(const int direction,const H4Level &level,const MqlRates &reference_bar,
                            const double entry,double &stop,double &target)
{
   if(InpEntryMode==CALYX_CONFIRMED_M15_ENTRY ||
      InpStopMode==CALYX_COMPLETED_TOUCH_BAR_EXTREME)
      stop=(direction>0 ? reference_bar.low-g_m15_atr*InpStopBufferM15ATR
                        : reference_bar.high+g_m15_atr*InpStopBufferM15ATR);
   else if(InpStopMode==CALYX_PREVIOUS_M15_EXTREME)
      stop=(direction>0 ? reference_bar.low-g_m15_atr*InpStopBufferM15ATR
                        : reference_bar.high+g_m15_atr*InpStopBufferM15ATR);
   else
      stop=entry-direction*g_m15_atr*InpStopM15ATR;

   if(direction*(entry-stop)<=0.0) return false;
   if(MathAbs(entry-stop)>g_m15_atr*InpMaximumStopM15ATR) return false;
   if(!H4L_FindTarget(direction,entry,level.price,target)) return false;
   double risk=MathAbs(entry-stop);
   double reward=MathAbs(target-entry);
   if(risk<=0.0 || reward<=0.0) return false;
   double rr=reward/risk;
   return rr>=InpMinimumRR && rr<=InpMaximumRR;
}

bool H4L_Send(const int direction,const double stop,const double target,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   double sl=AAA_Price(_Symbol,stop);
   double tp=AAA_Price(_Symbol,target);
   if(direction>0 && (sl>=entry-minimum || tp<=entry+minimum)) return false;
   if(direction<0 && (sl<=entry+minimum || tp>=entry-minimum)) return false;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=AAA_LotsForRisk(_Symbol,type,entry,sl,InpRiskPercent);
   if(lots<=0.0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(20);
   if(direction>0) return AAA_Trade.Buy(lots,_Symbol,0.0,sl,tp,comment);
   return AAA_Trade.Sell(lots,_Symbol,0.0,sl,tp,comment);
}

bool H4L_CanTradeNow()
{
   if(!InpEnableTrading || !H4L_SpreadOK() || !H4L_SessionAllowed(TimeCurrent())) return false;
   if(AAA_HasExposure(_Symbol,InpMagic)) return false;
   if(InpMaxTradesPerDay>0 && H4L_TodayTradeCount()>=InpMaxTradesPerDay) return false;
   return true;
}

void H4L_ProcessConfirmedEntry()
{
   if(!H4L_CanTradeNow()) return;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M15,0,3,bars)<3) return;
   double tolerance=g_m15_atr*InpTouchToleranceM15ATR;

   int selected=-1;
   int selected_direction=0;
   double best_distance=DBL_MAX;
   for(int i=0;i<ArraySize(g_levels);i++)
   {
      if(!H4L_IsFresh(g_levels[i],bars[1].time)) continue;
      bool long_touch=bars[1].low<=g_levels[i].price+tolerance &&
                      bars[1].close>g_levels[i].price;
      bool short_touch=bars[1].high>=g_levels[i].price-tolerance &&
                       bars[1].close<g_levels[i].price;
      if(InpConfirmedRequireOpenOnApproachSide)
      {
         long_touch=long_touch && bars[1].open>g_levels[i].price;
         short_touch=short_touch && bars[1].open<g_levels[i].price;
      }
      int direction=0;
      if(long_touch && !short_touch) direction=1;
      else if(short_touch && !long_touch) direction=-1;
      if(direction==0) continue;
      double distance=MathAbs(bars[1].close-g_levels[i].price);
      if(distance<best_distance)
      {
         selected=i;
         selected_direction=direction;
         best_distance=distance;
      }
   }
   if(selected<0) return;

   g_levels[selected].consumed=true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(selected_direction>0 ? tick.ask : tick.bid);
   double stop=0.0,target=0.0;
   if(!H4L_BuildStopAndTarget(selected_direction,g_levels[selected],bars[1],entry,stop,target)) return;
   H4L_Send(selected_direction,stop,target,"Calyx H4 ladder confirmed");
}

void H4L_ProcessTouchEntry(const double current_mid)
{
   if(g_last_mid<=0.0 || !H4L_CanTradeNow()) return;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M15,0,2,bars)<2) return;
   double tolerance=g_m15_atr*InpTouchToleranceM15ATR;

   int selected=-1;
   int selected_direction=0;
   double best_distance=DBL_MAX;
   for(int i=0;i<ArraySize(g_levels);i++)
   {
      if(!H4L_IsFresh(g_levels[i],bars[0].time)) continue;
      int direction=0;
      if(g_last_mid>g_levels[i].price+tolerance && current_mid<=g_levels[i].price+tolerance)
         direction=1;
      else if(g_last_mid<g_levels[i].price-tolerance && current_mid>=g_levels[i].price-tolerance)
         direction=-1;
      if(direction==0) continue;
      double distance=MathAbs(current_mid-g_levels[i].price);
      if(distance<best_distance)
      {
         selected=i;
         selected_direction=direction;
         best_distance=distance;
      }
   }
   if(selected<0) return;

   // A rail is consumed on its first detected touch even if spread, RR or size rejects the order.
   g_levels[selected].consumed=true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(selected_direction>0 ? tick.ask : tick.bid);
   double stop=0.0,target=0.0;
   if(!H4L_BuildStopAndTarget(selected_direction,g_levels[selected],bars[1],entry,stop,target)) return;
   H4L_Send(selected_direction,stop,target,"Calyx H4 ladder touch");
}

int OnInit()
{
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   g_last_m15_bar=iTime(_Symbol,PERIOD_M15,0);
   g_last_h4_bar=iTime(_Symbol,PERIOD_H4,0);
   if(H4L_BuildLevels()) H4L_InitializeTouchCounts(g_last_m15_bar);
   Print("Calyx DMC H4 Fresh Ladder research loaded on ",_Symbol,
         "; no-lookahead mode=",(int)InpEntryMode,
         "; risk=",DoubleToString(InpRiskPercent,2),"%.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double mid=(tick.bid+tick.ask)*0.5;
   datetime current_m15=iTime(_Symbol,PERIOD_M15,0);
   bool new_bar=current_m15>0 && current_m15!=g_last_m15_bar;
   if(new_bar)
   {
      g_last_m15_bar=current_m15;
      double latest_m15_atr=AAA_ATR(_Symbol,PERIOD_M15,InpATRPeriod,1);
      if(latest_m15_atr>0.0 && latest_m15_atr!=EMPTY_VALUE) g_m15_atr=latest_m15_atr;
      if(InpEntryMode==CALYX_CONFIRMED_M15_ENTRY) H4L_ProcessConfirmedEntry();
      MqlRates completed[];
      ArraySetAsSeries(completed,true);
      if(CopyRates(_Symbol,PERIOD_M15,1,1,completed)==1) H4L_RecordCompletedM15(completed[0]);

      datetime current_h4=iTime(_Symbol,PERIOD_H4,0);
      if(current_h4>0 && current_h4!=g_last_h4_bar)
      {
         g_last_h4_bar=current_h4;
         double latest_h4_atr=AAA_ATR(_Symbol,PERIOD_H4,InpATRPeriod,1);
         if(latest_h4_atr>0.0 && latest_h4_atr!=EMPTY_VALUE) g_h4_atr=latest_h4_atr;
         H4L_AddLatestClosedH4();
      }
   }
   if(InpEntryMode==CALYX_TOUCH_ENTRY && ArraySize(g_levels)>=3)
      H4L_ProcessTouchEntry(mid);
   g_last_mid=mid;
}
