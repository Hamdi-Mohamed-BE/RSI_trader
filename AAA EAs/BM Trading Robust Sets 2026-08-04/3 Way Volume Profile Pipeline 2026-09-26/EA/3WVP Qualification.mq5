// Research wrapper. Original raw source is included unchanged; controls default OFF.
#define OnTick VP_Original_OnTick
#define OnInit VP_Original_OnInit
#include "..\..\3 Way Volume Profile Raw 2026-09-26\EA\3 Way Volume Profile Research EA.mq5"
#undef OnTick
#undef OnInit

input group "Qualification control - research only"
input bool InpNoSignalControl=false;
input int InpControlSeed=101;
input double InpControlProbability=0.008;
input double InpControlStopATR=2.0;

double VP_ControlUniform(const datetime stamp,const uint salt)
{
   uint x=(uint)stamp ^ (uint)InpControlSeed ^ salt;
   x^=x>>16; x*=2246822507; x^=x>>13; x*=3266489909; x^=x>>16;
   return (double)x/4294967296.0;
}

int OnInit()
{
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   if(InpControlProbability<=0 || InpControlProbability>=1 || InpControlStopATR<=0)
      return INIT_PARAMETERS_INCORRECT;
   return VP_Original_OnInit();
}

void OnTick()
{
   if(!InpNoSignalControl) { VP_Original_OnTick(); return; }
   if(!InpEnableTrading || !AAA_NewBar(_Symbol,InpSignalTimeframe,g_vp_last_bar)) return;
   int day=VP_Key(g_vp_last_bar);
   if(day!=g_day) { g_day=day; return; }
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   double atr=AAA_BufferValue(g_atr,0,1);
   if(atr==EMPTY_VALUE || atr<=0) return;
   if(VP_ControlUniform(g_vp_last_bar,2654435769)>=InpControlProbability) return;
   int direction=(VP_ControlUniform(g_vp_last_bar,2246822519)<0.5 ? -1 : 1);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   double entry=(direction>0 ? tick.ask : tick.bid);
   VP_Enter(direction,entry-direction*InpControlStopATR*atr,"VP no-signal control");
}
