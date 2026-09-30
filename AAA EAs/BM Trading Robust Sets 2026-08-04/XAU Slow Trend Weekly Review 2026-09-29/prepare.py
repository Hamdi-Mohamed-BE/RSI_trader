"""Mechanical research cloning only; production files are read but never edited."""
from pathlib import Path
import json,hashlib,shutil,subprocess
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
OLD=BASE/'XAU Slow Trend Filter Review 2026-09-29'
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    original=json.loads((OLD/'BUILD.json').read_text())
    assert all(sha(Path(p))==h for p,h in original.items()),'Previous frozen study changed'
    ea=ROOT/'EA';ea.mkdir(exist_ok=True)
    shutil.copy2(OLD/'filters.mqh',ROOT/'filters.mqh')
    source=(OLD/'EA/SlowFilter.mq5').read_text()
    source=source.replace('#include "../filters.mqh"','#include "../filters.mqh"\n#include "../weekly.mqh"')
    marker='if(lastEntryTime>0 && TimeCurrent()-lastEntryTime<cooldown) return;'
    assert source.count(marker)==1
    source=source.replace(marker,marker+'\n   if(!ResearchWeekPermit(ResearchWeeklyMode,TimeCurrent(),lastEntryTime)) return;')
    marker='if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;'
    assert source.count(marker)==1
    source=source.replace(marker,marker+'\n   if(ResearchWeeklyMode<0 || ResearchWeeklyMode>2 || !ResearchWeeklySelfTest()) return INIT_PARAMETERS_INCORRECT;\n   Print("WEEKLY SELF TEST PASS");')
    path=ea/'SlowWeekly.mq5';path.write_text(source)
    log=ROOT/'compile.log'
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{path}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
    assert '0 errors, 0 warnings' in log.read_text(encoding='utf-16'),log.read_text(encoding='utf-16')
    dest=TESTER/'MQL5/Experts/AAA Research/SlowWeekly20260929';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path.with_suffix('.ex5'),dest/'SlowWeekly.ex5')
    engine=(OLD/'run.py').read_text().replace('SlowFilter20260929','SlowWeekly20260929').replace("'SlowFilter'","'SlowWeekly'").replace('slowfilter-','slowweekly-').replace('slow-filter-20260929','slow-weekly-20260929')
    (ROOT/'engine.py').write_text(engine)
    files=[path,path.with_suffix('.ex5'),dest/'SlowWeekly.ex5',ROOT/'filters.mqh',ROOT/'weekly.mqh',ROOT/'PROTOCOL.md',ROOT/'engine.py',ROOT/'run.py',ROOT/'prepare.py']
    manifest=original|{str(p):sha(p) for p in files}
    (ROOT/'BUILD.json').write_text(json.dumps(manifest,indent=2))
    print('Research compile: 0 errors, 0 warnings. Production remains untouched.')
if __name__=='__main__':main()
