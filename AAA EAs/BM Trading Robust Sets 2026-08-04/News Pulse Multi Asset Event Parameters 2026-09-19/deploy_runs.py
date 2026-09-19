"""Source/research parity, then independent 6m/1y/3y/5y website runs. Tester only."""
import argparse, importlib.util, json, shutil, subprocess
from pathlib import Path
import research as r
from prepare_deployment import SOURCE, SET_NAMES

ROOT=r.ROOT; PACKAGE=r.PACKAGE; DEPLOY=ROOT/'Deployment'
SHARED=PACKAGE/'AAA Final EAs'/'AAA Final News Pulse EA'
OLD=PACKAGE/'News Pulse Full Coverage 2026-09-12'

def selected_settings(asset):
    path=PACKAGE/'Selected Portfolio Settings 2026-09-01'/SET_NAMES[asset]
    return dict(line.split('=',1) for line in r.read(path).splitlines() if '=' in line and not line.startswith(';'))

def make_source(name,calendar):
    code=SOURCE.read_text().replace('../AAA Final News Pulse EA/',SHARED.as_posix()+'/')
    code=code.replace('..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh',(PACKAGE/'_Shared'/'CalyxAdaptivePortfolio.mqh').as_posix())
    code=code.replace((SHARED/'NewsPulseTesterCalendar.mqh').as_posix(),calendar.as_posix())
    (ROOT/(name+'Base.mqh')).write_text(code)
    base=(ROOT/'XAGBaseline.mq5').read_text().replace('"Base.mqh"','"'+name+'Base.mqh"')
    (ROOT/(name+'.mq5')).write_text(base)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--resume',action='store_true');ap.add_argument('--parity-only',action='store_true');args=ap.parse_args()
    DEPLOY.mkdir(exist_ok=True)
    log=DEPLOY/'production-compile.log'
    subprocess.run(f'"{r.TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
    assert '0 errors, 0 warnings' in r.read(log),r.read(log)
    r.settings=selected_settings
    source_hash=r.sha(SOURCE)
    for asset in r.ASSETS:
        variant='ProductionParity';name=asset+variant
        parity_path=DEPLOY/(asset+'-PARITY.json')
        if args.resume and parity_path.exists() and json.loads(parity_path.read_text()).get('source_sha256')==source_hash:
            continue
        make_source(name,ROOT/'Calendar.mqh')
        r.run(asset,variant)
        actual=json.loads((ROOT/'native'/name/'stats.json').read_text())
        expected=json.loads((ROOT/'native'/(asset+'Fitted')/'stats.json').read_text())
        for key in ('final_balance','trades','win_rate_pct','max_drawdown_pct'):
            assert abs(actual[key]-expected[key])<.10,(asset,key,actual[key],expected[key])
        r.save(parity_path,dict(passed=True,source_sha256=source_hash,stats=actual,reference=asset+'Fitted'))
        print('PARITY PASSED',asset,flush=True)
    if args.parity_only:return
    for file in ('OFFICIAL CALENDAR.json','NewsPulseTesterCalendar.mqh'):
        shutil.copy2(OLD/file,DEPLOY/file)
    identity=dict(source_sha256=source_hash,compiled_sha256=r.sha(SOURCE.with_suffix('.ex5')),
                  indexed_lookup=False,event_window_guard=True,
                  changes='Include relocation and verified event-window wrapper only; production parameters unchanged.',
                  dependencies={str(p.relative_to(PACKAGE)).replace('\\','/'):r.sha(p) for p in
                      [SHARED/'AAA_Final_Common.mqh',SHARED/'SafeRegimeFilter.mqh',SHARED/'DynamicTrailingSessionFilter.mqh',PACKAGE/'_Shared'/'CalyxAdaptivePortfolio.mqh']},
                  calendar_sha256=r.sha(DEPLOY/'NewsPulseTesterCalendar.mqh'))
    r.save(DEPLOY/'BUILD MANIFEST.json',identity)
    spec=importlib.util.spec_from_file_location('old_coverage',OLD/'run_coverage.py')
    coverage=importlib.util.module_from_spec(spec);spec.loader.exec_module(coverage);coverage.ROOT=DEPLOY
    r.END=coverage.END.replace('-','.')
    for period,start in coverage.WINDOWS.items():
        for asset in r.ASSETS:
            slug='news-pulse-'+asset.lower();path=DEPLOY/f'{slug}-{period}-model4.json'
            if args.resume and path.exists():
                result=json.loads(path.read_text())
                if result.get('build')==identity and all(result['settings'].get(k)==v for k,v in selected_settings(asset).items()):
                    print('REUSE',slug,period,flush=True);continue
            variant='Production'+period;name=asset+variant
            make_source(name,DEPLOY/'NewsPulseTesterCalendar.mqh')
            r.run(asset,variant,start=start.replace('-','.'))
            folder=ROOT/'native'/name;dest=DEPLOY/'Backtest Reports';dest.mkdir(exist_ok=True)
            for p in folder.iterdir():
                if p.suffix in ('.htm','.png'):shutil.copy2(p,dest/p.name)
            report=dest/f'multi-news-{name}.htm'
            result=coverage.parse_result(slug,period,4,report,(folder/'journal.txt').read_text())
            result['strategy_profile']='multi-event-full-2026-09-19'
            result['optimization_in_sample']=True
            result['selection_window']='2025-09-19 to 2026-09-19 exclusive'
            result['parameters']=json.loads((DEPLOY/'APPROVED.json').read_text())['params'][asset]
            r.save(path,result)
            print('WEBSITE',slug,period,result['stats']['return_pct'],flush=True)

if __name__=='__main__':main()
