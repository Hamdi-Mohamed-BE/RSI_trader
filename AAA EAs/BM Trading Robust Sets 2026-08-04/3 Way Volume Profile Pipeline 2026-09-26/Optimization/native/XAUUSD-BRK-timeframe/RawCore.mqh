
// Raw rules fixed 2026-09-26 before any test (transcript supplied by the user).
//   Profile  : previous session = last UTC day with >= InpMinimumProfileBars M1 bars; typical price x tick volume,
//              InpBins bins, InpValueAreaPercent value area -> POC, VAH, VAL; session close = that day's last M1 close.
//   Setup 1  : POC bounce (only if the previous session closed OUTSIDE the value area). bar[1] touches the POC and
//              confirms in the bounce direction (side price came from = bar[2] close vs POC): rejection (wick through
//              the POC, close back on the origin side, candle colour in trade direction) or engulfing at the POC.
//              Stop POC -/+ InpPocStopATR x ATR; one POC trade per session.
//   Setup 2  : VA reversal (only if the previous session closed INSIDE the value area). A bar closes outside VAH/VAL,
//              then a bar closes back inside -> trade back into the area; stop beyond the excursion extreme
//              + InpStopBufferATR x ATR. Repeatable within the session.
//   Setup 3  : VA breakout (any session). Close >= VAH + InpBreakoutATR x ATR (short: <= VAL - ...); pullback to within
//              InpPullbackNearATR x ATR of the level without closing deeper than InpMaxPullbackDepth of the VA width
//              (else the setup is cancelled); break of structure = close beyond the highest high (lowest low) made
//              between the breakout and the pullback -> enter; stop beyond the pullback extreme + buffer.
//   Target   : InpRewardRisk x risk (video: 2R). Market entry at the next bar. One position at a time.
//   InpSetups: bitmask 1 = POC bounce, 2 = VA reversal, 4 = VA breakout, 7 = combined system.

bool   InpEnableTrading=true;
double InpRiskPercent=1.0;
double InpRewardRisk=2.0;
long   InpMagic=1092601;
bool   InpAdaptivePortfolioControls=false;

ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
int    InpSetups=7;
int    InpBins=64;
double InpValueAreaPercent=70.0;
int    InpMinimumProfileBars=300;
int    InpATRPeriod=14;
double InpPocStopATR=0.2;
double InpStopBufferATR=0.1;
double InpBreakoutATR=1.0;
double InpPullbackNearATR=0.5;
double InpMaxPullbackDepth=0.25;
double InpMinStopSpreadMultiple=3.0;

#include "..\..\..\3 Way Volume Profile Raw 2026-09-26\EA\AAA_Final_Common.mqh"

datetime g_vp_last_bar=0;
int      g_atr=INVALID_HANDLE;
int      g_day=0;
bool     g_ready=false, g_prev_inside=false, g_poc_done=false;
double   g_poc=0, g_vah=0, g_val=0;
// VA reversal state
bool     g_exc_up=false, g_exc_dn=false;
double   g_exc_high=0, g_exc_low=0;
// Breakout state (per direction): 0 idle, 1 broke out, 2 pulled back
int      g_bo_up=0, g_bo_dn=0;
double   g_bo_up_high=0, g_bo_up_pull=0, g_bo_dn_low=0, g_bo_dn_pull=0;

int VP_Key(const datetime t) { MqlDateTime d; TimeToStruct(t,d); return d.year*10000+d.mon*100+d.day; }

bool VP_BuildProfile(const datetime day_start)
{
   for(int back=1;back<=4;back++)
     {
      datetime start=day_start-back*86400, finish=start+86400;
      MqlRates r[];
      int n=CopyRates(_Symbol,PERIOD_M1,start,finish-1,r);
      if(n<InpMinimumProfileBars) continue;
      double hi=-DBL_MAX,lo=DBL_MAX;
      for(int i=0;i<n;i++) { hi=MathMax(hi,r[i].high); lo=MathMin(lo,r[i].low); }
      if(hi<=lo) continue;
      double bins[]; ArrayResize(bins,InpBins); ArrayInitialize(bins,0);
      double width=(hi-lo)/InpBins,total=0;
      for(int i=0;i<n;i++)
        {
         double typical=(r[i].high+r[i].low+r[i].close)/3.0;
         int b=(int)MathFloor((typical-lo)/width); b=MathMax(0,MathMin(InpBins-1,b));
         bins[b]+=(double)r[i].tick_volume; total+=(double)r[i].tick_volume;
        }
      if(total<=0) continue;
      int p=0; for(int i=1;i<InpBins;i++) if(bins[i]>bins[p]) p=i;
      int left=p,right=p; double covered=bins[p];
      while(covered<total*InpValueAreaPercent/100.0 && (left>0 || right<InpBins-1))
        {
         double below=(left>0 ? bins[left-1] : -1), above=(right<InpBins-1 ? bins[right+1] : -1);
         if(above>=below && right<InpBins-1) { right++; covered+=bins[right]; } else { left--; covered+=bins[left]; }
        }
      OptProfileHigh=hi; OptProfileLow=lo;
      g_poc=lo+(p+0.5)*width; g_val=lo+left*width; g_vah=lo+(right+1)*width;
      double close=r[n-1].close;
      g_prev_inside=(close>=g_val && close<=g_vah);
      return g_val<g_vah;
     }
   return false;
}

void VP_ResetSession()
{
   g_poc_done=false; g_exc_up=false; g_exc_dn=false; g_bo_up=0; g_bo_dn=0;
}

bool VP_Enter(const int direction,const double stop,const string comment)
{
   return OptEnter(direction,stop,comment);
}

void CoreOnTick()
{
   if(!InpEnableTrading || !AAA_NewBar(_Symbol,InpSignalTimeframe,g_vp_last_bar)) return;
   MqlRates b[];
   ArraySetAsSeries(b,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,b)<3) return;
   int day=VP_Key(b[0].time);
   if(day!=g_day)
     {
      g_day=day;
      MqlDateTime d; TimeToStruct(b[0].time,d); d.hour=0; d.min=0; d.sec=0;
      g_ready=VP_BuildProfile(StructToTime(d));
      VP_ResetSession();
      if(g_ready) PrintFormat("3WVP %d profile POC %.5f VAH %.5f VAL %.5f prev close %s",day,g_poc,g_vah,g_val,(g_prev_inside ? "inside" : "outside"));
      return;   // the first bar of the session only builds the profile
     }
   if(!g_ready) return;
   double atr=AAA_BufferValue(g_atr,0,1);
   if(atr==EMPTY_VALUE || atr<=0.0) return;
   double width=g_vah-g_val;
   bool flat=!OptExposureFull();

   // ---- Setup 2 state: VA reversal (previous session inside) ----
   if((InpSetups&2)!=0 && g_prev_inside)
     {
      if(b[1].close>g_vah) { if(!g_exc_up) g_exc_high=b[1].high; g_exc_up=true; g_exc_high=MathMax(g_exc_high,b[1].high); }
      if(b[1].close<g_val) { if(!g_exc_dn) g_exc_low=b[1].low; g_exc_dn=true; g_exc_low=MathMin(g_exc_low,b[1].low); }
     }
   // ---- Setup 3 state: breakout / pullback ----
   if((InpSetups&4)!=0)
     {
      if(g_bo_up==0 && b[1].close>=g_vah+InpBreakoutATR*atr) { g_bo_up=1; g_bo_up_high=b[1].high; }
      else if(g_bo_up==1)
        {
         g_bo_up_high=MathMax(g_bo_up_high,b[1].high);
         if(b[1].close<g_vah-InpMaxPullbackDepth*width) g_bo_up=0;
         else if(b[1].low<=g_vah+InpPullbackNearATR*atr) { g_bo_up=2; g_bo_up_pull=b[1].low; }
        }
      else if(g_bo_up==2)
        {
         if(b[1].close<g_vah-InpMaxPullbackDepth*width) g_bo_up=0;
         else g_bo_up_pull=MathMin(g_bo_up_pull,b[1].low);
        }
      if(g_bo_dn==0 && b[1].close<=g_val-InpBreakoutATR*atr) { g_bo_dn=1; g_bo_dn_low=b[1].low; }
      else if(g_bo_dn==1)
        {
         g_bo_dn_low=MathMin(g_bo_dn_low,b[1].low);
         if(b[1].close>g_val+InpMaxPullbackDepth*width) g_bo_dn=0;
         else if(b[1].high>=g_val-InpPullbackNearATR*atr) { g_bo_dn=2; g_bo_dn_pull=b[1].high; }
        }
      else if(g_bo_dn==2)
        {
         if(b[1].close>g_val+InpMaxPullbackDepth*width) g_bo_dn=0;
         else g_bo_dn_pull=MathMax(g_bo_dn_pull,b[1].high);
        }
     }
   if(!flat) return;

   // ---- Setup 1: POC bounce (previous session outside) ----
   if((InpSetups&1)!=0 && !g_prev_inside && !g_poc_done)
     {
      bool touched=(b[1].low<=g_poc && b[1].high>=g_poc) || (b[2].low<=g_poc && b[2].high>=g_poc);
      if(touched)
        {
         int from=(b[2].close>g_poc ? 1 : (b[2].close<g_poc ? -1 : 0));   // side price came from -> bounce direction
         bool bull_rej=(b[1].low<g_poc && b[1].close>g_poc && b[1].close>b[1].open);
         bool bear_rej=(b[1].high>g_poc && b[1].close<g_poc && b[1].close<b[1].open);
         bool bull_eng=(b[1].close>b[1].open && b[2].close<b[2].open && b[1].close>=b[2].open && b[1].open<=b[2].close);
         bool bear_eng=(b[1].close<b[1].open && b[2].close>b[2].open && b[1].close<=b[2].open && b[1].open>=b[2].close);
         if(from>0 && (bull_rej || bull_eng) && b[1].close>g_poc)
           { if(VP_Enter(1,g_poc-InpPocStopATR*atr,"VP POC long")) { g_poc_done=true; return; } }
         if(from<0 && (bear_rej || bear_eng) && b[1].close<g_poc)
           { if(VP_Enter(-1,g_poc+InpPocStopATR*atr,"VP POC short")) { g_poc_done=true; return; } }
        }
     }
   // ---- Setup 2: VA reversal trigger ----
   if((InpSetups&2)!=0 && g_prev_inside)
     {
      bool inside=(b[1].close<g_vah && b[1].close>g_val);
      if(g_exc_up && inside) { g_exc_up=false; if(VP_Enter(-1,g_exc_high+InpStopBufferATR*atr,"VP reversal short")) return; }
      if(g_exc_dn && inside) { g_exc_dn=false; if(VP_Enter(1,g_exc_low-InpStopBufferATR*atr,"VP reversal long")) return; }
     }
   // ---- Setup 3: breakout trigger (break of structure) ----
   if((InpSetups&4)!=0)
     {
      if(g_bo_up==2 && b[1].close>g_bo_up_high)
        { g_bo_up=0; if(VP_Enter(1,g_bo_up_pull-InpStopBufferATR*atr,"VP breakout long")) return; }
      if(g_bo_dn==2 && b[1].close<g_bo_dn_low)
        { g_bo_dn=0; if(VP_Enter(-1,g_bo_dn_pull+InpStopBufferATR*atr,"VP breakout short")) return; }
     }
}

int CoreOnInit()
{
   if(InpRewardRisk<=0.0 || InpRiskPercent<=0.0 || InpBins<8 || InpSetups<1 || InpSetups>7) return INIT_PARAMETERS_INCORRECT;
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   return (g_atr==INVALID_HANDLE ? INIT_FAILED : INIT_SUCCEEDED);
}

void CoreOnDeinit(const int reason) { IndicatorRelease(g_atr); }


