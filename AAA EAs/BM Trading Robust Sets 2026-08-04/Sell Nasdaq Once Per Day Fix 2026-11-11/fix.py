"""Sell Nasdaq 15min once-per-day fix (owner 2026-11-11: "the sell nasdaq dynamic exit just hit stop loss but it re created the same order again ... yes [fix it]
and show this EA performance difference").

Cause found in both sources: AttemptedToday() returned FALSE when HistorySelect() failed, i.e. a history gap re-armed the day (fail open). Fix (asserted edits,
originals in before/):
  1. HistorySelect failure -> treat the day as attempted (fail safe).
  2. Live only: a per-account / per-magic / per-New-York-day GlobalVariable counter (also survives restarts and reconnects). Not used in the tester.
  3. input InpMaxAttemptsPerDay (default 1 = the tested rule: any own order today blocks the day). 2+ = research only, re-arm after a stop-out
     (counts own SELL / SELL_STOP orders).
The guarded builds' held-stop transform (Core 9/build.py virtual_stop) anchors stay byte-identical.
python fix.py patch | compile"""
import hashlib, shutil, subprocess, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; BAK = H / 'before'
SRC = [B / 'Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/EA/Sell Nasdaq 15min Dynamic Exit Research EA.mq5',
       B / 'Sell Nasdaq 15min Research 2026-09-08/EA/Sell Nasdaq 15min EA.mq5']
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'
OLD_BODY = """bool AttemptedToday(const MqlDateTime &now_ny)
{
   MqlDateTime start=now_ny;
   start.hour=0; start.min=0; start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent())) return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket>0 && HistoryOrderGetString(ticket,ORDER_SYMBOL)==_Symbol && HistoryOrderGetInteger(ticket,ORDER_MAGIC)==InpMagic)
         return true;
   }
   return false;
}
"""
NEW_BODY = """// 2026-11-11 once-per-day fix: live attempt counter per account / magic / New York day (GlobalVariable; survives history gaps and restarts).
string AttemptKey(const MqlDateTime &now_ny)
{
   return StringFormat("CSN15_%I64d_%I64d_%04d%02d%02d",AccountInfoInteger(ACCOUNT_LOGIN),(long)InpMagic,now_ny.year,now_ny.mon,now_ny.day);
}
int AttemptLatch(const MqlDateTime &now_ny)
{
   string key=AttemptKey(now_ny);
   return (GlobalVariableCheck(key) ? (int)GlobalVariableGet(key) : 0);
}
void RecordAttempt(const MqlDateTime &now_ny)
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return;
   GlobalVariableSet(AttemptKey(now_ny),AttemptLatch(now_ny)+1);
   GlobalVariablesDeleteAll(StringFormat("CSN15_%I64d_%I64d_",AccountInfoInteger(ACCOUNT_LOGIN),(long)InpMagic),TimeCurrent()-5*86400);
}

bool AttemptedToday(const MqlDateTime &now_ny)
{
   int max_attempts=(InpMaxAttemptsPerDay<1 ? 1 : InpMaxAttemptsPerDay);
   if(!(bool)MQLInfoInteger(MQL_TESTER) && AttemptLatch(now_ny)>=max_attempts) return true;
   MqlDateTime start=now_ny;
   start.hour=0; start.min=0; start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent())) return true;      // 2026-11-11: fail safe (was: return false -> re-armed the day)
   int attempts=0;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket>0 && HistoryOrderGetString(ticket,ORDER_SYMBOL)==_Symbol && HistoryOrderGetInteger(ticket,ORDER_MAGIC)==InpMagic)
      {
         if(max_attempts==1) return true;                                          // tested rule: any own order today blocks the day
         ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)HistoryOrderGetInteger(ticket,ORDER_TYPE);
         if(type==ORDER_TYPE_SELL_STOP || type==ORDER_TYPE_SELL) attempts++;
      }
   }
   return attempts>=max_attempts;
}
"""
INPUT = "input long   InpMagic=980908150;\n"
INPUT_NEW = INPUT + "input int    InpMaxAttemptsPerDay=1;          // 1 = tested rule (one sell stop per New York day); 2+ = re-arm after a stop-out (research only)\n"


def read(p):
    raw = p.read_bytes(); return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def sub1(t, a, b):
    assert t.count(a) == 1, (a[:80], t.count(a)); return t.replace(a, b)


def patch():
    for p in SRC:
        t = read(p)
        if 'InpMaxAttemptsPerDay' in t: print('already', p.name); continue
        d = BAK / p.relative_to(B); d.parent.mkdir(parents=True, exist_ok=True)
        for f in (p, p.with_suffix('.ex5')):
            if not (d.parent / f.name).exists(): shutil.copy2(f, d.parent / f.name)
        t = sub1(t, OLD_BODY, NEW_BODY); t = sub1(t, INPUT, INPUT_NEW)
        call = next(x for x in t.split('\n') if x.startswith('   PlaceSellStop(setup.low-InpEntryBufferPips*PipSize(),now_ny'))
        t = sub1(t, call + '\n', '   if(' + call.strip().rstrip(';') + ') RecordAttempt(now_ny);\n')
        p.write_text(t, encoding='utf-8'); print('patched', p.name)


def compile_all():
    for p in SRC:
        log = p.with_suffix('.fix.compile.log'); started = time.time()
        subprocess.run(f'"{EDITOR}" /portable /compile:"{p}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]
        ex5 = p.with_suffix('.ex5'); assert ex5.stat().st_mtime >= started - 2
        print('COMPILED', p.name, hashlib.sha256(ex5.read_bytes()).hexdigest()[:12])


if __name__ == '__main__':
    patch() if sys.argv[1:] == ['patch'] else compile_all()
