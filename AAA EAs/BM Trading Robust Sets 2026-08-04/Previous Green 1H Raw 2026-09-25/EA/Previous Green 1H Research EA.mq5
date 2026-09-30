#property copyright "Calyx research: raw Previous-Green 1H idea (heyastral.ai/u/lucas_lalk names only; rules are our own)"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test:
//   Signal  : the just-closed signal-timeframe candle is green (close > open) -> buy at the next bar.
//             Both-directions mode: a red candle -> sell (mirror).
//   Stop    : signal candle low (long) / high (short). Target: InpRewardRisk x stop distance.
//   Position: one at a time; no trailing, time exit or session filter.
//   Guard   : skip when the stop is closer than InpMinStopSpreadMultiple x current spread.
//   Control : InpSignalMode=1 ignores the candle colour (long-only: buy after every candle; both: direction
//             alternates by bar index) with the same stop/target, to test whether "green" adds anything.

enum ENUM_PG_DIRECTION { PG_LONG_ONLY=0, PG_BOTH=1 };
enum ENUM_PG_SIGNAL    { PG_SIGNAL_COLOUR=0, PG_SIGNAL_CONTROL_ANY=1 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input double InpRewardRisk=3.0;
input long   InpMagic=1092501;
input bool   InpAdaptivePortfolioControls=false;

input group "Previous-Green rules"
input ENUM_TIMEFRAMES   InpSignalTimeframe=PERIOD_H1;
input ENUM_PG_DIRECTION InpDirectionMode=PG_LONG_ONLY;
input ENUM_PG_SIGNAL    InpSignalMode=PG_SIGNAL_COLOUR;
input double            InpMinStopSpreadMultiple=3.0;

#include "AAA_Final_Common.mqh"

datetime g_pg_last_bar=0;

int OnInit()
{
   if(InpRewardRisk<=0.0 || InpRiskPercent<=0.0) return INIT_PARAMETERS_INCORRECT;
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(!AAA_NewBar(_Symbol,InpSignalTimeframe,g_pg_last_bar) || !InpEnableTrading) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates bar[];
   ArraySetAsSeries(bar,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,bar)<3) return;

   int direction=0;
   if(InpSignalMode==PG_SIGNAL_COLOUR)
     {
      if(bar[1].close>bar[1].open) direction=1;
      else if(InpDirectionMode==PG_BOTH && bar[1].close<bar[1].open) direction=-1;
     }
   else
     {
      direction=1;
      if(InpDirectionMode==PG_BOTH && ((long)(bar[1].time/PeriodSeconds(InpSignalTimeframe))%2)==1) direction=-1;
     }
   if(direction==0) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? bar[1].low : bar[1].high);
   double distance=(direction>0 ? entry-stop : stop-entry);
   if(distance<=0.0) return;
   if(distance<InpMinStopSpreadMultiple*(tick.ask-tick.bid)) return;
   AAA_SendMarket(_Symbol,direction,stop,InpRewardRisk,InpRiskPercent,InpMagic,
                  (direction>0 ? "PG1H long" : "PG1H short"));
}
