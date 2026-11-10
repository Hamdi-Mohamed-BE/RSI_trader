#property copyright "Calyx research: Gold Band Wave clip rules (PLAN.md, frozen 2026-11-10)"
#property version   "1.00"
#property strict
// RESEARCH ONLY. Never attach to a live chart.

#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;
input long   InpMagic=91110001;
input int    InpTrendPeriod=200;      // SMA of the close; 0 = no trend filter (control)
input int    InpShortBB=20;
input int    InpLongBB=50;
input double InpBBDeviation=2.0;
input int    InpSignalPeriod=9;       // SMA of BBTrend ("the line that follows it")
input int    InpATRPeriod=14;
input double InpStopATR=2.0;          // "two times the average candle size"
input bool   InpRandomDirection=false;
input int    InpSeed=1;
input int    InpDeviationPoints=50;
input bool   InpAdaptivePortfolioControls=false;   // P4 build: unused, kept for the installer preset checks

CTrade g_trade;
int g_short=INVALID_HANDLE,g_long=INVALID_HANDLE,g_sma=INVALID_HANDLE,g_atr=INVALID_HANDLE;
datetime g_last_bar=0;
int g_rule_dir=0;                     // direction of the signal that opened the current position (exits follow the rule, also in the random control)

double BBTrend(const int shift)
  {
   double us[1],ls[1],ms[1],ul[1],ll[1];
   if(CopyBuffer(g_short,0,shift,1,ms)!=1 || CopyBuffer(g_short,1,shift,1,us)!=1 || CopyBuffer(g_short,2,shift,1,ls)!=1) return EMPTY_VALUE;
   if(CopyBuffer(g_long,1,shift,1,ul)!=1 || CopyBuffer(g_long,2,shift,1,ll)!=1 || ms[0]==0.0) return EMPTY_VALUE;
   return (MathAbs(ls[0]-ll[0])-MathAbs(us[0]-ul[0]))/ms[0]*100.0;
  }

bool WaveAndSignal(const int shift,double &wave,double &signal)
  {
   wave=BBTrend(shift); if(wave==EMPTY_VALUE) return false;
   double s=0.0;
   for(int i=0;i<InpSignalPeriod;i++) { double v=BBTrend(shift+i); if(v==EMPTY_VALUE) return false; s+=v; }
   signal=s/InpSignalPeriod; return true;
  }

bool Position(ulong &ticket,int &dir)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
        { ticket=t; dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1); return true; }
     }
   return false;
  }

double Lots(const ENUM_ORDER_TYPE type,const double entry,const double stop)
  {
   double one=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one) || MathAbs(one)<=0.0) return 0.0;
   double raw=UR_RiskBudget()/MathAbs(one);   // P4 no guard: installer budget (RiskSupport.mqh)
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<=0.0 || st<=0.0) return 0.0;
   return MathMax(mn,MathMin(mx,MathCeil((MathMin(raw,mx)-1e-12)/st)*st));
  }

void Open(const int rule,const double atr)
  {
   int dir=(InpRandomDirection ? ((MathRand()&1)==1?1:-1) : rule);
   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || atr<=0.0) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*InpStopATR*atr,dg);
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,sl);
   if(v<=0.0) { Print("GBW skipped: no valid volume"); return; }
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0.0,sl,0.0,"GBW"):g_trade.Sell(v,_Symbol,0.0,sl,0.0,"GBW"));
   if(ok) g_rule_dir=rule; else Print("GBW order rejected: ",g_trade.ResultRetcodeDescription());
  }

int OnInit()
  {
   if(InpRiskPercent<=0.0 || InpSignalPeriod<1 || InpStopATR<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_short=iBands(_Symbol,PERIOD_H4,InpShortBB,0,InpBBDeviation,PRICE_CLOSE);
   g_long=iBands(_Symbol,PERIOD_H4,InpLongBB,0,InpBBDeviation,PRICE_CLOSE);
   g_atr=iATR(_Symbol,PERIOD_H4,InpATRPeriod);
   if(InpTrendPeriod>0) g_sma=iMA(_Symbol,PERIOD_H4,InpTrendPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(g_short==INVALID_HANDLE || g_long==INVALID_HANDLE || g_atr==INVALID_HANDLE || (InpTrendPeriod>0 && g_sma==INVALID_HANDLE)) return INIT_FAILED;
   MathSrand(InpSeed); g_last_bar=iTime(_Symbol,PERIOD_H4,0);
   PrintFormat("GBW_SPEC trend=%d bb=%d/%d dev=%.1f signal=%d stopATR=%.1f risk=%.2f random=%d",InpTrendPeriod,InpShortBB,InpLongBB,InpBBDeviation,InpSignalPeriod,InpStopATR,InpRiskPercent,InpRandomDirection);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_short!=INVALID_HANDLE) IndicatorRelease(g_short);
   if(g_long!=INVALID_HANDLE) IndicatorRelease(g_long);
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
   if(g_sma!=INVALID_HANDLE) IndicatorRelease(g_sma);
  }

void OnTick()
  {
   datetime b0=iTime(_Symbol,PERIOD_H4,0);
   if(b0<=0 || b0==g_last_bar) return;
   g_last_bar=b0;
   double w1,s1,w2,s2;
   if(!WaveAndSignal(1,w1,s1) || !WaveAndSignal(2,w2,s2)) return;
   int cross=(w2<=s2 && w1>s1 ? 1 : (w2>=s2 && w1<s1 ? -1 : 0));
   if(cross==0) return;
   ulong ticket=0; int dir=0;
   if(Position(ticket,dir) && cross==-(g_rule_dir!=0 ? g_rule_dir : dir))   // P4 build: after a restart use the position direction                         // exit when the wave crosses back against the signal that opened the trade
     {
      g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints);
      if(!g_trade.PositionClose(ticket)) { Print("GBW exit failed: ",g_trade.ResultRetcodeDescription()); return; }
     }
   if(Position(ticket,dir)) return;
   double c1=iClose(_Symbol,PERIOD_H4,1),atr[1];
   if(CopyBuffer(g_atr,0,1,1,atr)!=1) return;
   if(InpTrendPeriod>0)
     {
      double sma[1]; if(CopyBuffer(g_sma,0,1,1,sma)!=1) return;
      if((cross>0 && c1<=sma[0]) || (cross<0 && c1>=sma[0])) return;
     }
   Open(cross,atr[0]);
  }
