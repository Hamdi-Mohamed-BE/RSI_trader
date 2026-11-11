"""Generate EA/Overnight Bias ORB Research EA.mq5 from the raw video EA (InpStrategy 4 path) with asserted edits; every new input defaults to the raw rule.
python build_ea.py (compiles)"""
import subprocess
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
SRC = B / 'Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.mq5'; OUT = H / 'EA/Overnight Bias ORB Research EA.mq5'
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'


def sub1(t, a, b):
    assert t.count(a) == 1, (a[:100], t.count(a)); return t.replace(a, b)


def main():
    raw = SRC.read_bytes(); t = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')
    t = sub1(t, 'input int    InpDeviationPoints=50;\n', """input int    InpDeviationPoints=50;
// ---- Overnight Bias ORB optimisation inputs (2026-11-10); defaults = the raw rules
input int    InpOnbORMinutes=15;         // opening range from 09:30: 15 / 30 / 45 / 60 (M15 bars)
input int    InpOnbOvernightStart=0;     // NY minute the overnight range starts (0 = midnight)
input double InpOnbBiasFrac=0.3333333333; // long if the open is in the top fraction, short if in the bottom fraction
input double InpOnbAdxMin=20.0;          // 0 = off
input double InpOnbStopMult=0.30;        // stop = this x 15-day average true daily range
input double InpOnbTargetR=3.0;          // target in R; 0 = none (flat time only)
input int    InpOnbEntryEnd=915;         // last NY minute of an entry bar close
input int    InpOnbFlatMin=930;          // flat at this NY minute
input double InpOnbBreakEvenR=0.0;       // 0 = off
input double InpOnbTrailStartR=0.0;      // 0 = off
input double InpOnbTrailDistR=0.5;
input int    InpOnbDirection=2;          // 2 both (raw), 0 long only, 1 short only
input int    InpOnbDayMask=31;           // bit 0 Monday .. bit 4 Friday
input int    InpOnbMaxTrades=1;          // trades a day (raw 1)
double g_onb_risk=0.0;
""")
    t = sub1(t, '   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || stop_dist<=0.0 || target_dist<=0.0) return false;\n',
             '   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || stop_dist<=0.0 || target_dist<0.0) return false;\n')
    t = sub1(t, 'sl=NormalizeDouble(e-dir*stop_dist,dg),tp=NormalizeDouble(e+dir*target_dist,dg);', 'sl=NormalizeDouble(e-dir*stop_dist,dg),tp=(target_dist>0.0 ? NormalizeDouble(e+dir*target_dist,dg) : 0.0);')
    t = sub1(t, '   if(ok) { g_trades++; g_had_pos=true; }\n', '   if(ok) { g_trades++; g_had_pos=true; g_onb_risk=stop_dist; }\n')
    old = t[t.index('void Onb(const datetime t1,const int close_min,const bool adx,const bool true_range)'):t.index('//------------------------------------------------------------------ events')]
    t = t.replace(old, """void Onb(const datetime t1,const int close_min,const bool adx,const bool true_range)
  {
   int setup_min=570+InpOnbORMinutes;
   if(!g_setup && close_min>=setup_min)                                     // the opening range has closed
     {
      g_setup=true;
      int nb=MathMax(1,InpOnbORMinutes/15);
      int so=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,570),true),sn=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,InpOnbOvernightStart),false);
      if(so<1 || sn<=so) { g_done=true; return; }
      g_onh=iHigh(_Symbol,PERIOD_M15,iHighest(_Symbol,PERIOD_M15,MODE_HIGH,sn-so,so+1)); g_onl=iLow(_Symbol,PERIOD_M15,iLowest(_Symbol,PERIOD_M15,MODE_LOW,sn-so,so+1));
      int last=so-nb+1; if(last<1) { g_done=true; return; }
      g_orh=iHigh(_Symbol,PERIOD_M15,iHighest(_Symbol,PERIOD_M15,MODE_HIGH,nb,last)); g_orl=iLow(_Symbol,PERIOD_M15,iLowest(_Symbol,PERIOD_M15,MODE_LOW,nb,last));
      double op=iOpen(_Symbol,PERIOD_M15,so),rg=g_onh-g_onl;
      if(rg<=0.0) { g_done=true; return; }
      bool raw3=(MathAbs(InpOnbBiasFrac-1.0/3.0)<1e-6);                       // raw thirds: keep the raw expressions bit for bit
      double hi=(raw3 ? g_onl+rg*2.0/3.0 : g_onl+rg*(1.0-InpOnbBiasFrac)),lo=(raw3 ? g_onl+rg/3.0 : g_onl+rg*InpOnbBiasFrac);
      g_bias=(op>=hi ? 1 : (op<=lo ? -1 : 0));
      if(InpUseBias && g_bias==0) g_done=true;
      return;
     }
   if(!g_setup || g_done || close_min<setup_min+15 || close_min>InpOnbEntryEnd || HasPos() || g_trades>=InpOnbMaxTrades) return;
   if(((InpOnbDayMask>>(NyDow(t1)-1))&1)==0) return;
   double c=iClose(_Symbol,PERIOD_M15,1); int rule=0;
   if(c>g_orh && (!InpUseBias || g_bias>0) && InpOnbDirection!=1) rule=1;
   else if(c<g_orl && (!InpUseBias || g_bias<0) && InpOnbDirection!=0) rule=-1;
   if(rule==0) return;
   if(adx && InpOnbAdxMin>0.0 && AdxValue(1)<=InpOnbAdxMin) return;
   double base=DailyAverage(true_range); if(base<=0.0) return;
   if(g_trades+1>=InpOnbMaxTrades) g_done=true;
   bool rawx=(MathAbs(InpOnbStopMult-0.30)<1e-9 && MathAbs(InpOnbTargetR-3.0)<1e-9);       // raw: 0.30 / 0.90 x base, bit for bit
   Enter(Direction(rule),(rawx?0.30*base:InpOnbStopMult*base),(rawx?0.90*base:InpOnbTargetR*InpOnbStopMult*base),(InpStrategy==4?"ONB":"REEL"));
  }

void ManageOnb()
  {
   if(InpStrategy!=4 || (InpOnbBreakEvenR<=0.0 && InpOnbTrailStartR<=0.0) || g_onb_risk<=0.0) return;
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      int dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      double op=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),px=(dir>0?k.bid:k.ask),gain=(px-op)*dir,want=sl;
      if(InpOnbBreakEvenR>0.0 && gain>=InpOnbBreakEvenR*g_onb_risk) want=(dir>0?MathMax(want,op):(want<=0.0?op:MathMin(want,op)));
      if(InpOnbTrailStartR>0.0 && gain>=InpOnbTrailStartR*g_onb_risk) { double tr=px-dir*InpOnbTrailDistR*g_onb_risk; want=(dir>0?MathMax(want,tr):(want<=0.0?tr:MathMin(want,tr))); }
      want=NormalizeDouble(want,dg);
      if((dir>0 && want>sl+_Point*0.5) || (dir<0 && (sl<=0.0 || want<sl-_Point*0.5)))
        { g_trade.SetExpertMagicNumber((ulong)InpMagic); if(!g_trade.PositionModify(t,want,tp)) Print("ONB modify failed: ",g_trade.ResultRetcodeDescription()); }
     }
  }

""")
    t = sub1(t, '   int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : 930);\n', '   int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : (InpStrategy==4 ? InpOnbFlatMin : 930));\n   ManageOnb();\n')
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(t, encoding='utf-8')
    log = OUT.with_suffix('.compile.log'); subprocess.run(f'"{EDITOR}" /portable /compile:"{OUT}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]; print('COMPILED', OUT.with_suffix('.ex5').is_file())


if __name__ == '__main__':
    main()
