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
// ---- optimisation inputs (2026-11-10); defaults = the raw rules
input int    InpGbwTF=240;               // bar minutes: 60 / 240 / 1440
input int    InpGbwDirection=2;          // 2 both (raw), 0 long only, 1 short only
input bool   InpGbwExitOnCross=true;     // raw: close on the opposite cross
input double InpGbwTargetR=0.0;          // 0 = no target (raw)
input double InpGbwBreakEvenR=0.0;       // 0 = off
input double InpGbwTrailATR=0.0;         // 0 = off; trail at this x ATR once in profit by 1R
ENUM_TIMEFRAMES GbwTF() { return (InpGbwTF==60 ? PERIOD_H1 : (InpGbwTF==1440 ? PERIOD_D1 : PERIOD_H4)); }
double g_gbw_risk=0.0;

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
   double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<=0.0 || st<=0.0) return 0.0;
   return MathMax(mn,MathMin(mx,MathCeil((MathMin(raw,mx)-1e-12)/st)*st));
  }

void Open(const int rule,const double atr)
  {
   int dir=(InpRandomDirection ? ((MathRand()&1)==1?1:-1) : rule);
   if((InpGbwDirection==0 && dir<0) || (InpGbwDirection==1 && dir>0)) return;
   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || atr<=0.0) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*InpStopATR*atr,dg),tp=(InpGbwTargetR>0.0 ? NormalizeDouble(e+dir*InpGbwTargetR*InpStopATR*atr,dg) : 0.0);
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,sl);
   if(v<=0.0) { Print("GBW skipped: no valid volume"); return; }
   g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0.0,sl,tp,"GBW"):g_trade.Sell(v,_Symbol,0.0,sl,tp,"GBW"));
   if(ok) { g_rule_dir=rule; g_gbw_risk=InpStopATR*atr; } else Print("GBW order rejected: ",g_trade.ResultRetcodeDescription());
  }

int OnInit()
  {
   if(InpRiskPercent<=0.0 || InpSignalPeriod<1 || InpStopATR<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_short=iBands(_Symbol,GbwTF(),InpShortBB,0,InpBBDeviation,PRICE_CLOSE);
   g_long=iBands(_Symbol,GbwTF(),InpLongBB,0,InpBBDeviation,PRICE_CLOSE);
   g_atr=iATR(_Symbol,GbwTF(),InpATRPeriod);
   if(InpTrendPeriod>0) g_sma=iMA(_Symbol,GbwTF(),InpTrendPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(g_short==INVALID_HANDLE || g_long==INVALID_HANDLE || g_atr==INVALID_HANDLE || (InpTrendPeriod>0 && g_sma==INVALID_HANDLE)) return INIT_FAILED;
   MathSrand(InpSeed); g_last_bar=iTime(_Symbol,GbwTF(),0);
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

void ManageGbw()
  {
   if((InpGbwBreakEvenR<=0.0 && InpGbwTrailATR<=0.0) || g_gbw_risk<=0.0) return;
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS); double atr[1]; bool haveAtr=(CopyBuffer(g_atr,0,1,1,atr)==1);
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      int dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      double op=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),px=(dir>0?k.bid:k.ask),gain=(px-op)*dir,want=sl;
      if(InpGbwBreakEvenR>0.0 && gain>=InpGbwBreakEvenR*g_gbw_risk) want=(dir>0?MathMax(want,op):(want<=0.0?op:MathMin(want,op)));
      if(InpGbwTrailATR>0.0 && haveAtr && gain>=g_gbw_risk) { double tr=px-dir*InpGbwTrailATR*atr[0]; want=(dir>0?MathMax(want,tr):(want<=0.0?tr:MathMin(want,tr))); }
      want=NormalizeDouble(want,dg);
      if((dir>0 && want>sl+_Point*0.5) || (dir<0 && (sl<=0.0 || want<sl-_Point*0.5)))
        { g_trade.SetExpertMagicNumber((ulong)InpMagic); if(!g_trade.PositionModify(t,want,tp)) Print("GBW modify failed: ",g_trade.ResultRetcodeDescription()); }
     }
  }

void OnTick()
  {
   ManageGbw();
   datetime b0=iTime(_Symbol,GbwTF(),0);
   if(b0<=0 || b0==g_last_bar) return;
   g_last_bar=b0;
   double w1,s1,w2,s2;
   if(!WaveAndSignal(1,w1,s1) || !WaveAndSignal(2,w2,s2)) return;
   int cross=(w2<=s2 && w1>s1 ? 1 : (w2>=s2 && w1<s1 ? -1 : 0));
   if(cross==0) return;
   ulong ticket=0; int dir=0;
   if(InpGbwExitOnCross && Position(ticket,dir) && cross==-g_rule_dir)                         // exit when the wave crosses back against the signal that opened the trade
     {
      g_trade.SetExpertMagicNumber((ulong)InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints);
      if(!g_trade.PositionClose(ticket)) { Print("GBW exit failed: ",g_trade.ResultRetcodeDescription()); return; }
     }
   if(Position(ticket,dir)) return;
   double c1=iClose(_Symbol,GbwTF(),1),atr[1];
   if(CopyBuffer(g_atr,0,1,1,atr)!=1) return;
   if(InpTrendPeriod>0)
     {
      double sma[1]; if(CopyBuffer(g_sma,0,1,1,sma)!=1) return;
      if((cross>0 && c1<=sma[0]) || (cross<0 && c1>=sma[0])) return;
     }
   Open(cross,atr[0]);
  }
