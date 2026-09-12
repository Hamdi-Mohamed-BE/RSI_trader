"""Recover the ongoing unchanged run, prove lookup parity, complete coverage."""
from __future__ import annotations
import ctypes
import json
import shutil
from pathlib import Path
import run_coverage as run

ROOT=run.ROOT

def recover_one_year():
    # This is our already-verified isolated terminal, not the user's terminal.
    handle=ctypes.windll.kernel32.OpenProcess(0x00100000,False,3064)
    if handle:
        print('WAIT for the already running unmodified XAU one-year test',flush=True)
        ctypes.windll.kernel32.WaitForSingleObject(handle,2400000)
        ctypes.windll.kernel32.CloseHandle(handle)
    tag='news-pulse-xau-1y-model4'
    report=run.TESTER/'reports'/'news-full-coverage'/(tag+'.htm')
    assert report.is_file(),'Unmodified one-year test did not finish'
    journal=(run.TESTER/'Tester'/'Agent-127.0.0.1-3000'/'logs'/'20260912.log').read_text(encoding='utf-16')
    begin=journal.rfind('News Pulse tester calendar accepted:')
    assert begin>=0
    journal=journal[begin:]
    assert 'requested=20250905..20260905' in journal
    for path in report.parent.glob(tag+'*'):
        shutil.copy2(path,ROOT/'Backtest Reports'/path.name)
    (ROOT/'Audit'/(tag+'-journal.txt')).write_text(journal,encoding='utf-8')
    result=run.parse_result('news-pulse-xau','1y',4,ROOT/'Backtest Reports'/report.name,journal)
    (ROOT/(tag+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('RECOVERED unmodified one-year control: '+json.dumps(result['stats']),flush=True)

def main():
    recover_one_year()
    backup=ROOT/'Unmodified Control';backup.mkdir(exist_ok=True)
    for name in ('BUILD MANIFEST.json','compile.log'):
        shutil.copy2(ROOT/name,backup/name)
    for path in (ROOT/'EA').iterdir():
        if path.is_file():shutil.copy2(path,backup/path.name)
    controls={}
    for slug in run.SLUGS:
        tag=f'{slug}-6m-model4'
        report=ROOT/'Backtest Reports'/(tag+'.htm')
        journal=(ROOT/'Audit'/(tag+'-journal.txt')).read_text()
        result=run.parse_result(slug,'6m',4,report,journal)
        controls[slug]=result
        (backup/(tag+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        shutil.copy2(report,backup/report.name)
        shutil.copy2(ROOT/'Audit'/(tag+'-journal.txt'),backup/(tag+'-journal.txt'))
    run.prepare(indexed_lookup=True)
    parity=[]
    for slug in run.SLUGS:
        accelerated=run.run(slug,'6m',4)
        control=controls[slug]
        assert accelerated['trades']==control['trades'],f'Trade-level parity FAILED: {slug}'
        assert accelerated['stats']==control['stats'],f'Native-stat parity FAILED: {slug}'
        for key in ('calendar_expected','calendar_attempted','calendar_placed','events_without_closed_trades'):
            assert accelerated[key]==control[key],f'Calendar parity FAILED: {slug}'
        parity.append({'slug':slug,'period':'6m','trades':len(control['trades']),'all_trade_fields_equal':True,
                       'all_stats_equal':True,'calendar_audit_equal':True,
                       'control_report_sha256':control['source_report_sha256'],
                       'indexed_report_sha256':accelerated['source_report_sha256']})
    (ROOT/'LOOKUP PARITY.json').write_text(json.dumps(parity,indent=2),encoding='utf-8')
    print('PARITY PASSED for all three untouched native controls',flush=True)
    for period in ('1y','3y','5y'):
        for slug in run.SLUGS:
            result_file=ROOT/f'{slug}-{period}-model4.json'
            if result_file.is_file():continue
            run.run(slug,period,4)

if __name__=='__main__':main()
