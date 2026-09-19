"""Compile, isolated tester parity, and offline website publication. Never installs live charts."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path
from datetime import date, datetime, timezone
ROOT=Path(__file__).resolve().parent; P=ROOT.parent
RESEARCH=P/'Gold Overnight Value Area Pipeline 2026-09-19'
TESTER=P/'_Backtests/MT5-DMC-20260811'
SOURCE=ROOT/'EA/Gold Overnight Value Area EA.mq5'
STORE=P.parent/'EA store'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,default=str),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    log=ROOT/'compile.log'
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
    text=log.read_text(encoding='utf-16');assert '0 errors, 0 warnings' in text,text
    save(ROOT/'build.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')),adaptive_sha256=sha(P/'_Shared/CalyxAdaptivePortfolio.mqh')))
    print('COMPILE PASSED',flush=True)
def parity():
    # Only the isolated terminal may be launched; never close/restart the normal terminal.
    command="Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    processes=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True)
    assert str(TESTER).lower() not in processes.lower(),'Isolated tester already running'
    base=RESEARCH/'native/gva-raw-959d9253ab-1y-d150-r1-m4'
    case='gold-va-production-parity-1y';out=ROOT/'verification'/case;out.mkdir(parents=True,exist_ok=True)
    dest=TESTER/'MQL5/Experts/AAA Research/Gold VA Production';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE.with_suffix('.ex5'),dest/SOURCE.with_suffix('.ex5').name)
    settings=next(base.glob('*.set')).read_text(encoding='utf-8-sig')
    settings=settings.replace('InpCase=gva-raw-959d9253ab-1y-d150-r1-m4',f'InpCase={case}')
    settings+='\nInpAutoServerUTCOffset=false\nInpAdaptivePortfolioControls=false\nInpRiskMode=0\nInpWriteAudit=true\n'
    for f in (out/(case+'.set'),TESTER/'MQL5/Profiles/Tester'/(case+'.set')):f.write_text(settings)
    ini=(base/'tester.ini').read_text(encoding='utf-8-sig').replace('AAA Research\\Gold VA Pipeline 20260919\\Gold Overnight Value Area Research','AAA Research\\Gold VA Production\\Gold Overnight Value Area EA').replace('gva-raw-959d9253ab-1y-d150-r1-m4',case)
    (out/'tester.ini').write_text(ini,encoding='utf-8-sig')
    logs=lambda:list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
    offsets={p:p.stat().st_size for p in logs()};began=time.time()
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{out/"tester.ini"}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
    print('ISOLATED PARITY STARTED',proc.pid,flush=True)
    proc.wait(timeout=1800)
    journal=''
    for f in logs():
        if f.stat().st_mtime<began:continue
        with f.open('rb') as h:h.seek(offsets.get(f,0));journal+=h.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt').write_text(journal,encoding='utf-8')
    report=TESTER/'reports'/(case+'.htm');assert report.stat().st_mtime>=began-2
    shutil.copy2(report,out/report.name)
    audits=[f for f in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{case}-audit.csv') if f.stat().st_mtime>=began-2];assert len(audits)==1
    shutil.copy2(audits[0],out/'audit.csv')
    verify_existing()
def verify_existing():
    base=RESEARCH/'native/gva-raw-959d9253ab-1y-d150-r1-m4'
    case='gold-va-production-parity-1y';out=ROOT/'verification'/case
    meta=read(base/'run.json');meta['fingerprint']=sha(SOURCE);meta['params']['InpCase']=case;save(out/'run.json',meta)
    sys.path.insert(0,str(RESEARCH));import frozen_parser
    summary=frozen_parser.parse_case(out)
    old=read(base/'trades.json');new=read(out/'trades.json')
    keys=['open_time','close_time','side','volume','open_price','close_price','net_profit','commission','swap','stop','target']
    mismatches=[i for i,(a,b) in enumerate(zip(old,new)) if {k:a[k] for k in keys}!={k:b[k] for k in keys}]
    result=dict(passed=len(old)==len(new) and not mismatches,old_count=len(old),new_count=len(new),mismatches=mismatches,summary=summary,source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')))
    save(ROOT/'parity.json',result);assert result['passed'],result
    print('200-TRADE NATIVE PARITY PASSED',flush=True)
def publish():
    tested=read(ROOT/'parity.json');assert tested['passed'] and tested['source_sha256']==sha(SOURCE) and tested['binary_sha256']==sha(SOURCE.with_suffix('.ex5'))
    sys.path.insert(0,str(STORE))
    from app.gold_value_area import payload,SLUG
    from app.evidence_cache import CACHE_ROOT,write_json
    from app.catalog import get_sellable_catalog
    from tools.precompute_evidence_cache import build_portfolio,common_cached_window
    before={};published={}
    for period in ('6m','1y','3y','5y'):
        out,rows=payload(period);folder=CACHE_ROOT/'products'/SLUG/'standard'
        write_json(folder/(period+'.json'),out);write_json(folder/(period+'.trades.json'),rows)
        existing=read(CACHE_ROOT/'portfolio/standard'/f'{period}.json')
        before[period]=existing['stats']
        rebuilt=build_portfolio(get_sellable_catalog(),period,*common_cached_window(get_sellable_catalog(),period))
        published[period]=dict(raw=out['stats'],portfolio=rebuilt['stats'],portfolio_period=rebuilt['period'])
    save(ROOT/'publication.json',dict(before=before,after=published,source_sha256=sha(SOURCE),published_at=datetime.now(timezone.utc).isoformat()))
    print('PRODUCT AND PORTFOLIO CACHE PUBLISHED',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--verify-existing',action='store_true');args=p.parse_args()
    if args.native:build();parity()
    if args.verify_existing:verify_existing()
    if args.publish:publish()
