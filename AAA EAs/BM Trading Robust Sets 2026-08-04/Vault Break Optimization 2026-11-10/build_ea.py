"""Generate EA/Vault Break Research EA.mq5 from the raw video EA (InpStrategy 2 path) with asserted edits; every new input defaults to the raw rule.
python build_ea.py  (compiles with the isolated MetaEditor)"""
import subprocess
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
SRC = B / 'Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.mq5'; OUT = H / 'EA/Vault Break Research EA.mq5'
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'


def sub1(t, a, b):
    assert t.count(a) == 1, (a[:100], t.count(a)); return t.replace(a, b)


def main():
    raw = SRC.read_bytes(); t = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')
    t = sub1(t, 'input int    InpDeviationPoints=50;\n', """input int    InpDeviationPoints=50;
// ---- Vault Break optimisation inputs (2026-11-10); defaults = the raw rules
input int    InpVaultTF=30;              // chart timeframe minutes: 15 / 30 / 60
input int    InpVaultAnchorMin=60;       // NY minute of the session open bar (01:00)
input double InpVaultBarrierAtr=0.30;    // barrier = open +/- this x 15-session ATR
input bool   InpVaultUseVwap=true;       // close must also be beyond the session VWAP
input int    InpVaultEntryStart=660;     // NY minute of bar close, first allowed (11:00)
input int    InpVaultEntryEnd=900;       // last allowed (15:00)
input int    InpVaultFlatMin=930;        // flat at this NY minute (15:30)
input int    InpVaultMaxTrades=3;        // trades a day, one at a time
input int    InpVaultStopMode=0;         // 0 points, 1 x 15-session ATR
input double InpVaultStopPoints=75.0;
input double InpVaultStopAtr=0.30;
input int    InpVaultTargetMode=0;       // 0 points, 1 R multiple, 2 none (flat time only)
input double InpVaultTargetPoints=40.0;
input double InpVaultTargetR=1.0;
input double InpVaultBreakEvenR=0.0;     // 0 = off
input double InpVaultTrailStartR=0.0;    // 0 = off
input double InpVaultTrailDistR=0.5;
input int    InpVaultDirection=0;        // 0 long only (raw), 1 short mirror only, 2 both
input double InpVaultAdxMin=0.0;         // 0 = off; ADX(14) on the chart timeframe
input int    InpVaultDayMask=31;         // bit 0 Monday .. bit 4 Friday
double g_vault_risk=0.0;
""")
    t = sub1(t, '   if(InpStrategy==2) return PERIOD_M30;\n', '   if(InpStrategy==2) return (InpVaultTF==15 ? PERIOD_M15 : (InpVaultTF==60 ? PERIOD_H1 : PERIOD_M30));\n')
    t = sub1(t, '   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || stop_dist<=0.0 || target_dist<=0.0) return false;\n',
             '   MqlTick k; if(!SymbolInfoTick(_Symbol,k) || stop_dist<=0.0 || target_dist<0.0) return false;\n')
    t = sub1(t, 'sl=NormalizeDouble(e-dir*stop_dist,dg),tp=NormalizeDouble(e+dir*target_dist,dg);', 'sl=NormalizeDouble(e-dir*stop_dist,dg),tp=(target_dist>0.0 ? NormalizeDouble(e+dir*target_dist,dg) : 0.0);')
    t = sub1(t, '   if(ok) { g_trades++; g_had_pos=true; }\n', '   if(ok) { g_trades++; g_had_pos=true; g_vault_risk=stop_dist; }\n')
    old_vault = t[t.index('void Vault(const datetime t1,const int close_min)'):t.index('void VwapAdx(')]
    t = t.replace(old_vault, """void Vault(const datetime t1,const int close_min)
  {
   ENUM_TIMEFRAMES tf=ChartTF();
   if(g_open01<=0.0)
     {
      datetime a=TodayNy(t1,InpVaultAnchorMin); int s=iBarShift(_Symbol,tf,a,true);
      if(s>=0 && close_min>InpVaultAnchorMin) { double atr=DailyAverage(true); g_open01=iOpen(_Symbol,tf,s); g_barrier=(atr>0.0?InpVaultBarrierAtr*atr:0.0); }
     }
   if(g_barrier<=0.0 || close_min<InpVaultEntryStart || close_min>InpVaultEntryEnd || HasPos() || g_trades>=InpVaultMaxTrades) return;
   if(((InpVaultDayMask>>(NyDow(t1)-1))&1)==0) return;
   if(InpVaultAdxMin>0.0 && AdxValue(1)<=InpVaultAdxMin) return;
   double c=iClose(_Symbol,tf,1),v=Vwap(tf,TodayNy(t1,InpVaultAnchorMin),1);
   if(InpVaultUseVwap && v<=0.0) return;
   int dir=0;
   if(InpVaultDirection!=1 && c>g_open01+g_barrier && (!InpVaultUseVwap || c>v)) dir=1;
   else if(InpVaultDirection!=0 && c<g_open01-g_barrier && (!InpVaultUseVwap || c<v)) dir=-1;
   if(dir==0) return;
   double stop=(InpVaultStopMode==1 ? InpVaultStopAtr*DailyAverage(true) : InpVaultStopPoints);
   double target=(InpVaultTargetMode==0 ? InpVaultTargetPoints : (InpVaultTargetMode==1 ? InpVaultTargetR*stop : 0.0));
   Enter(dir,stop,target,"VAULT");
  }

void ManageVault()
  {
   if(InpStrategy!=2 || (InpVaultBreakEvenR<=0.0 && InpVaultTrailStartR<=0.0) || g_vault_risk<=0.0) return;
   MqlTick k; if(!SymbolInfoTick(_Symbol,k)) return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      int dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      double op=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),px=(dir>0?k.bid:k.ask);
      double gain=(px-op)*dir,want=sl;
      if(InpVaultBreakEvenR>0.0 && gain>=InpVaultBreakEvenR*g_vault_risk) want=(dir>0?MathMax(want,op):(want<=0.0?op:MathMin(want,op)));
      if(InpVaultTrailStartR>0.0 && gain>=InpVaultTrailStartR*g_vault_risk)
        {
         double trail=px-dir*InpVaultTrailDistR*g_vault_risk;
         want=(dir>0?MathMax(want,trail):(want<=0.0?trail:MathMin(want,trail)));
        }
      want=NormalizeDouble(want,dg);
      if((dir>0 && want>sl+_Point*0.5) || (dir<0 && (sl<=0.0 || want<sl-_Point*0.5)))
        { g_trade.SetExpertMagicNumber((ulong)InpMagic); if(!g_trade.PositionModify(t,want,tp)) Print("VAULT modify failed: ",g_trade.ResultRetcodeDescription()); }
     }
  }

""")
    t = sub1(t, '   if(InpStrategy==4) g_adx=iADX(_Symbol,PERIOD_M15,14);\n', '   if(InpStrategy==4) g_adx=iADX(_Symbol,PERIOD_M15,14);\n   if(InpStrategy==2 && InpVaultAdxMin>0.0) { g_adx=iADX(_Symbol,ChartTF(),14); if(g_adx==INVALID_HANDLE) return INIT_FAILED; }\n')
    t = sub1(t, '   int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : 930);\n', '   int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : (InpStrategy==2 ? InpVaultFlatMin : 930));\n   ManageVault();\n')
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(t, encoding='utf-8')
    log = OUT.with_suffix('.compile.log'); subprocess.run(f'"{EDITOR}" /portable /compile:"{OUT}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]; print('COMPILED', OUT.with_suffix('.ex5').is_file())


if __name__ == '__main__':
    main()
