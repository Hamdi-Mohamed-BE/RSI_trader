"""Generate EA/Gold Band Wave Research EA.mq5 from the raw EA with asserted edits; every new input defaults to the raw rule. python build_ea.py (compiles)"""
import subprocess
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
SRC = B / 'Gold Band Wave Raw 2026-11-10/EA/Gold Band Wave Raw EA.mq5'; OUT = H / 'EA/Gold Band Wave Research EA.mq5'
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'


def sub1(t, a, b):
    assert t.count(a) == 1, (a[:100], t.count(a)); return t.replace(a, b)


def main():
    raw = SRC.read_bytes(); t = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')
    t = sub1(t, 'input int    InpDeviationPoints=50;\n', """input int    InpDeviationPoints=50;
// ---- optimisation inputs (2026-11-10); defaults = the raw rules
input int    InpGbwTF=240;               // bar minutes: 60 / 240 / 1440
input int    InpGbwDirection=2;          // 2 both (raw), 0 long only, 1 short only
input bool   InpGbwExitOnCross=true;     // raw: close on the opposite cross
input double InpGbwTargetR=0.0;          // 0 = no target (raw)
input double InpGbwBreakEvenR=0.0;       // 0 = off
input double InpGbwTrailATR=0.0;         // 0 = off; trail at this x ATR once in profit by 1R
ENUM_TIMEFRAMES GbwTF() { return (InpGbwTF==60 ? PERIOD_H1 : (InpGbwTF==1440 ? PERIOD_D1 : PERIOD_H4)); }
double g_gbw_risk=0.0;
""")
    NL = chr(10); head, tail = t.split('ENUM_TIMEFRAMES GbwTF()', 1); body, rest = tail.split(NL, 1)
    n = rest.count('PERIOD_H4'); assert n == 7, n
    t = head + 'ENUM_TIMEFRAMES GbwTF()' + body + NL + rest.replace('PERIOD_H4', 'GbwTF()'); assert t.count('PERIOD_H4') == 1
    t = sub1(t, 'double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*InpStopATR*atr,dg);',
             'double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*InpStopATR*atr,dg),tp=(InpGbwTargetR>0.0 ? NormalizeDouble(e+dir*InpGbwTargetR*InpStopATR*atr,dg) : 0.0);')
    t = sub1(t, 'g_trade.Buy(v,_Symbol,0.0,sl,0.0,"GBW"):g_trade.Sell(v,_Symbol,0.0,sl,0.0,"GBW"));', 'g_trade.Buy(v,_Symbol,0.0,sl,tp,"GBW"):g_trade.Sell(v,_Symbol,0.0,sl,tp,"GBW"));')
    t = sub1(t, '   if(ok) g_rule_dir=rule; else', '   if(ok) { g_rule_dir=rule; g_gbw_risk=InpStopATR*atr; } else')
    t = sub1(t, '   int dir=(InpRandomDirection ? ((MathRand()&1)==1?1:-1) : rule);\n', '   int dir=(InpRandomDirection ? ((MathRand()&1)==1?1:-1) : rule);\n   if((InpGbwDirection==0 && dir<0) || (InpGbwDirection==1 && dir>0)) return;\n')
    t = sub1(t, 'if(Position(ticket,dir) && cross==-g_rule_dir)', 'if(InpGbwExitOnCross && Position(ticket,dir) && cross==-g_rule_dir)')
    t = sub1(t, 'void OnTick()\n  {\n', """void ManageGbw()
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
""")
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(t, encoding='utf-8')
    log = OUT.with_suffix('.compile.log'); subprocess.run(f'"{EDITOR}" /portable /compile:"{OUT}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]; print('COMPILED', OUT.with_suffix('.ex5').is_file())


if __name__ == '__main__':
    main()
