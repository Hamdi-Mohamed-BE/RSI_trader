"""Mechanical research clone; writes only the new research folder and isolated tester."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
ORIGINAL=BASE/'Slow Multi Asset Trend Research 2026-09-06/EA/Calyx Slow Trend EA.mq5'
INSTALLED=Path(r'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\Calyx ANY BALANCE - RECOMMENDED ADAPTIVE\Calyx Slow Trend EA.ex5')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ea=ROOT/'EA';ea.mkdir(exist_ok=True)
    source=ORIGINAL.read_text();(ea/'source-snapshot.mq5').write_text(source)
    source=source.replace('CTrade trade;', '#include "../filters.mqh"\nCTrade trade;')
    source=source.replace('if(signal==0 || !SessionAllowed()', 'if(!ResearchFilter(signal)) return;\n   if(signal==0 || !SessionAllowed()')
    source=source.replace('if(InpTesterOnly && !MQLInfoInteger(MQL_TESTER))','if(!MQLInfoInteger(MQL_TESTER))')
    source=source.replace('atrHandle=iATR(', 'researchADX=iADX(_Symbol,InpSignalTimeframe,14);if(researchADX==INVALID_HANDLE)return INIT_FAILED;\n   atrHandle=iATR(')
    source=source.replace('if(atrHandle!=INVALID_HANDLE) IndicatorRelease(atrHandle);','if(researchADX!=INVALID_HANDLE) IndicatorRelease(researchADX);\n   if(atrHandle!=INVALID_HANDLE) IndicatorRelease(atrHandle);')
    source=source.replace('CloseIfRequired(signal);\n   TryEntry(signal,strength,stamp);','ResearchObserve(signal);\n   CloseIfRequired(signal);\n   ResearchObserve(signal);\n   TryEntry(signal,strength,stamp);\n   ResearchObserve(signal);')
    path=ea/'SlowFilter.mq5';path.write_text(source)
    log=ROOT/'compile.log'
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{path}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
    assert '0 errors, 0 warnings' in log.read_text(encoding='utf-16'),log.read_text(encoding='utf-16')
    dest=TESTER/'MQL5/Experts/AAA Research/SlowFilter20260929';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path.with_suffix('.ex5'),dest/'SlowFilter.ex5')
    shutil.copy2(INSTALLED,ROOT/'InstalledBaseline.ex5');shutil.copy2(INSTALLED,dest/'InstalledBaseline.ex5')
    manifest={str(p):sha(p) for p in [ORIGINAL,INSTALLED,path,path.with_suffix('.ex5'),ROOT/'filters.mqh',BASE/'_Shared/CalyxAdaptivePortfolio.mqh',ROOT/'PROTOCOL.md']}
    (ROOT/'BUILD.json').write_text(json.dumps(manifest,indent=2));print('Research compile: 0 errors, 0 warnings. Installed baseline copied only to isolated tester.')
if __name__=='__main__':main()
