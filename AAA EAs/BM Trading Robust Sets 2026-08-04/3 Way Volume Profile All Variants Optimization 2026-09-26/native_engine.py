"""Conditional native MT5 staged parameter search. No live or website writes.

Commands: parity, search, status. All research stages are resumable and hash checked.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'3 Way Volume Profile Pipeline 2026-09-26'))
import run_qualification as q
h=q.h
EA=ROOT/'EA'
OUT=ROOT/'native'
OUT.mkdir(exist_ok=True)
FIELDS=['tf','rr','bins','value','atr','buffer','breakout','near','depth','entry','stop','stop_param',
        'trail','trail_start','trail_distance','exit','session','direction','filter','day','max_day',
        'max_positions','reentry','max_bars','weekend','setups','poc_buffer']
BASE=dict(zip(FIELDS,[15,2,64,70,14,0.1,1,0.5,0.25,0,0,2,0,1,1.5,0,0,0,0,0,0,1,1,0,1,4,0.2]))

def dump(path,data): q.dump(path,data)
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def progress(**data):
    dump(ROOT/'progress.json',dict(utc=h.now(),**data))
    print(data,flush=True)

def build_cases(cases,folder):
    if h.isolated_running(): raise RuntimeError('Isolated tester is busy; will not compile or replace its research binary')
    vectors=',\n'.join(' {'+','.join(str(c[f]) for f in FIELDS)+'}' for c in cases)
    source='#property strict\n#property version "1.00"\ndouble Cases[][27]={\n'+vectors+'\n};\n#include "SearchLogic.mqh"\n'
    src=EA/'3WVP Search.mq5'
    # Generated native case table; source transformations are limited to this new research folder.
    src.write_text(source,encoding='utf-8')
    log=EA/'search.compile.log'
    began=time.time()
    subprocess.run(f'"{h.TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',
                   creationflags=subprocess.CREATE_NO_WINDOW,timeout=240)
    body=h.text(log)
    if not re.search(r'0 errors?, 0 warnings?',body): raise RuntimeError(body[-5000:])
    ex5=src.with_suffix('.ex5')
    if ex5.stat().st_mtime<began-2: raise RuntimeError('No fresh search binary')
    for f in (src,ex5,log,EA/'RawCore.mqh',EA/'SearchLogic.mqh'):
        shutil.copy2(f,folder/f.name)
    dest=h.TESTER/'MQL5'/'Experts'/'AAA Research'/'3WVP All Search 20260926'
    dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ex5,dest/ex5.name)
    return h.sha(ex5)

def parse_xml(path,cases):
    root=ET.parse(path).getroot()
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'}
    result=[]; headers=None
    for row in root.findall('.//s:Row',ns):
        values=[]
        for cell in row.findall('s:Cell',ns):
            idx=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if idx:
                while len(values)<int(idx)-1: values.append('')
            data=cell.find('s:Data',ns)
            values.append(''.join(data.itertext()) if data is not None else '')
        if 'Pass' in values and 'InpCase' in values:
            headers=values; continue
        if not headers or len(values)!=len(headers): continue
        record=dict(zip(headers,values))
        if not record.get('InpCase','').strip().isdigit(): continue
        index=int(record['InpCase'])
        if not 0<=index<len(cases): raise RuntimeError('Unexpected optimizer index')
        numeric={}
        for k,v in record.items():
            try: numeric[k]=float(v.replace(' ',''))
            except ValueError: numeric[k]=v
        result.append(dict(index=index,parameters=cases[index],native=numeric))
    if len(result)!=len(cases) or len({r['index'] for r in result})!=len(cases):
        raise RuntimeError(f'Incomplete optimization XML: {len(result)}/{len(cases)}; headers={headers}')
    return result

def batch(symbol,name,cases,start='2021.09.26',end='2024.09.26',model=1,optimize=True,min_trades=60):
    q.verified_build()
    folder=OUT/(symbol+'-'+name)
    folder.mkdir(exist_ok=True)
    frozen=dict(symbol=symbol,cases=cases,start=start,end=end,model=model,optimize=optimize,min_trades=min_trades,
                logic_sha=h.sha(EA/'SearchLogic.mqh'),core_sha=h.sha(EA/'RawCore.mqh'),protocol_sha=h.sha(ROOT/'PROTOCOL.md'))
    manifest=folder/'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=frozen: raise RuntimeError('Batch inputs changed: '+name)
        if (folder/'results.json').exists(): return json.loads((folder/'results.json').read_text())
    else: dump(manifest,frozen)
    h.wait_for_port_3000()
    sha=build_cases(cases,folder)
    dump(folder/'build.json',dict(ex5_sha256=sha))
    profile=h.TESTER/'MQL5'/'Profiles'/'Charts'/q.BINDING['profile']
    if not profile.is_dir() or list(profile.glob('*.chr')): raise RuntimeError('Research profile is not empty')
    tag='3wvpa-'+symbol+'-'+name
    set_name=tag+'.set'
    body=f'InpCase=0||0||1||{len(cases)-1}||'+('Y' if optimize else 'N')+f'\nInpMinimumRankTrades={min_trades}\nInpResearchSession=0\nInpResearchBrokerUtcOffsetMinutes=0\nInpUseDynamicTrailingSL=false\n'
    (folder/set_name).write_text(body)
    (h.TESTER/'MQL5'/'Profiles'/'Tester'/set_name).write_text(body)
    extension='.xml' if optimize else '.htm'
    reports=h.TESTER/'reports'/'calyx-3wvp-all'; reports.mkdir(parents=True,exist_ok=True)
    report=reports/(tag+extension)
    settings={'Common':{'Login':q.BINDING['login'],'Server':q.BINDING['server']},
              'Experts':{'Enabled':0,'AllowLiveTrading':0,'AllowDllImport':0},
              'Tester':{'Expert':'AAA Research\\3WVP All Search 20260926\\3WVP Search','ExpertParameters':set_name,
                        'Symbol':symbol,'Period':'M15','Deposit':10000,'Currency':'USD','Leverage':q.BINDING['leverage'],
                        'Model':model,'ExecutionMode':150,'Optimization':1 if optimize else 0,'OptimizationCriterion':6,
                        'FromDate':start,'ToDate':end,'ForwardMode':0,'Report':'reports\\calyx-3wvp-all\\'+tag+extension,
                        'ReplaceReport':1,'ShutdownTerminal':1,'UseLocal':1,'UseRemote':0,'UseCloud':0,'Visual':0}}
    ini=folder/'tester.ini'
    ini.write_text('\n'.join('['+section+']\n'+'\n'.join(f'{k}={v}' for k,v in values.items()) for section,values in settings.items()),encoding='utf-8-sig')
    if h.isolated_running(): raise RuntimeError('Isolated tester became busy')
    offsets={p:p.stat().st_size for p in h.log_files()}
    began=time.time()
    progress(state='running',symbol=symbol,stage=name,cases=len(cases),model=model)
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    proc=subprocess.Popen(f'"{h.TESTER / "terminal64.exe"}" /portable /profile:"{q.BINDING["profile"]}" /config:"{ini}"',
                          cwd=h.TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup)
    try: proc.wait(timeout=6*3600)
    except subprocess.TimeoutExpired:
        proc.terminate(); proc.wait(timeout=30); raise RuntimeError('Owned research batch timed out')
    journal=''
    for p in h.log_files():
        if p.stat().st_mtime<began-2: continue
        with p.open('rb') as f:
            f.seek(offsets.get(p,0)); journal+='\n['+str(p.relative_to(h.TESTER))+']\n'+f.read().decode('utf-16-le',errors='replace')
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    if proc.returncode!=0 or not report.exists() or report.stat().st_mtime<began-2:
        raise RuntimeError('No successful fresh report '+name+'\n'+journal[-3000:])
    fatal=[line for line in journal.splitlines() if re.search(r'initialization failed|start time changed|not enough history|access violation|critical error',line,re.I)]
    if fatal: raise RuntimeError('Native evidence failed history/init checks: '+str(fatal[:6]))
    (folder/(report.name+'.gz')).write_bytes(gzip.compress(report.read_bytes(),mtime=0))
    if optimize:
        results=parse_xml(report,cases)
    else:
        report_text=h.text(report)
        applied=h._report_inputs(report)
        if symbol not in report_text or start not in report_text or end not in report_text or applied.get('InpCase')!='0':
            raise RuntimeError('Native confirmation report does not match the requested case')
        metrics=h.summarize(report)
        trades=h._native_trades(report,tag)
        result=dict(parameters=cases[0],metrics=metrics,source_sha=sha,report_sha=h.sha(report),
                    relative_equity_dd_pct=h._number(h._metric(report_text,'Equity Drawdown Relative')),
                    coverage=sorted(set(re.findall(r'real ticks begin from[^\r\n]*',journal))),
                    failures=sorted(set(line for line in journal.splitlines() if 'failed market' in line or 'invalid stops' in line)))
        positions={}
        for match in re.finditer(r'ALLVP_POSITION\|(\d+)\|(\d+)\|(\d+)\|(-?[\d.]+)',journal):
            pid,opened,closed,pnl=match.groups()
            positions[pid]=dict(position_id=int(pid),open_time=int(opened),close_time=int(closed),pnl=float(pnl))
        summaries=re.findall(r'ALLVP_SUMMARY\|(\d+)\|(\d+)\|([\d.]+)\|(-?[\d.]+)\|([\d.]+)',journal)
        if not summaries: raise RuntimeError('Missing exact whole-position audit from tester')
        n,w,pf,net,dd=summaries[-1]
        result['position_metrics']=dict(trades=int(n),wins=int(w),win_rate_pct=100*int(w)/max(1,int(n)),profit_factor=float(pf),net_profit=float(net),equity_dd_pct=float(dd))
        if len(positions)!=int(n) or abs(float(net)-metrics['net_profit'])>0.05:
            raise RuntimeError('Whole-position audit does not reconcile with native cash P/L')
        dump(folder/'positions.json',sorted(positions.values(),key=lambda x:(x['close_time'],x['position_id'])))
        (folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
        results=[result]
    dump(folder/'results.json',results)
    progress(state='batch complete',symbol=symbol,stage=name,cases=len(cases),elapsed=round(time.time()-began,1))
    return results

def score(row,min_trades=60):
    n=row.get('native',{})
    if n:
        trades=n.get('Trades',0); profit=n.get('Profit',0); pf=n.get('Profit Factor',0); dd=n.get('Equity DD %',n.get('Drawdown %',100))
    else:
        m=row['metrics']; trades=m['trades']; profit=m['net_profit']; pf=m['profit_factor']; dd=row.get('relative_equity_dd_pct',m['max_drawdown_pct'])
    if trades<min_trades or profit<=0 or pf<=1: return -1000
    return min(pf,3)*(trades/100)**0.5*(profit/10000)/(0.05+dd/100)

def patches(stage,symbol):
    if stage=='timeframe': return [{'tf':x} for x in [1,3,5,15,30,16385,16388,16408]]
    if stage=='entry': return [{'entry':x} for x in range(5)]
    if stage=='stop':
        return ([{'stop':0}]+[{'stop':1,'stop_param':x} for x in [0.5,0.75,1,1.5,2,3,4]]+
                [{'stop':2,'stop_param':x} for x in [0.05,0.1,0.2]]+
                [{'stop':3,'stop_param':x} for x in ([5,10,20] if symbol=='XAUUSD' else [0.1,0.2,0.4])]+
                [{'stop':4},{'stop':5}])
    if stage=='trailing':
        return ([{'trail':0}]+[{'trail':1,'trail_start':x} for x in [0.5,1,1.5]]+
                [{'trail':2,'trail_start':s,'trail_distance':d} for s in [0.5,1,1.5,2] for d in [1,1.5,2]]+
                [{'trail':3,'trail_distance':d} for d in [0.05,0.1,0.2]]+
                [{'trail':4},{'trail':5},{'trail':7}]+[{'trail':6,'trail_distance':d} for d in [1.5,2,3]])
    if stage=='rr_exit':
        return ([{'exit':0,'rr':x} for x in [0.5,0.75,1,1.25,1.5,2,2.5,3,4,5,6]]+
                [{'exit':1,'trail':2,'trail_distance':d} for d in [1,1.5,2,3]]+
                [{'exit':2},{'exit':3},{'exit':4},{'exit':5,'trail':2,'trail_start':1}])
    if stage=='session': return [{'session':x} for x in range(6)]
    if stage=='direction': return [{'direction':x} for x in range(3)]
    if stage=='filters': return [{'filter':x} for x in range(7)]
    if stage=='management':
        return ([{'day':x} for x in range(4)]+[{'max_day':x} for x in range(4)]+
                [{'max_positions':1},{'max_positions':2},{'reentry':0},{'reentry':1}]+
                [{'max_bars':x} for x in [0,16,32]]+[{'weekend':0},{'weekend':1}])
    if stage=='profile':
        space={'bins':[32,64,96],'value':[60,70,80],'atr':[7,14,28],'buffer':[0,0.1,0.25,0.5],
               'breakout':[0.5,1,1.5,2],'near':[0.25,0.5,1],'depth':[0,0.25,0.5]}
        return [{k:v} for k,values in space.items() for v in values]
    raise ValueError(stage)

def dedupe(cases):
    return list({digest(c):c for c in cases}.values())

def neighborhood(base):
    # Vary active dimensions, not ignored RR/stop fields that would fake a plateau.
    exit_key='rr' if base['exit'] not in (1,2) else 'trail_distance' if base['exit']==1 else 'value'
    stop_key='stop_param' if base['stop'] in (1,2,3) else 'buffer'
    av=[max(0.5,base['rr']+d) for d in [-0.25,0,0.25]] if exit_key=='rr' else [base[exit_key]*v for v in [0.9,1,1.1]]
    cv=[base[stop_key]*v for v in [0.8,1,1.2]] if stop_key=='stop_param' else [max(0,base['buffer']+d) for d in [-0.05,0,0.05]]
    return dedupe([base|{exit_key:a,'breakout':base['breakout']*b,stop_key:c} for a,b,c in itertools.product(av,[0.8,1,1.2],cv)])

def parity():
    result=batch('XAUUSD','parity',[BASE],start='2025.09.26',end='2026.09.26',model=4,optimize=False)[0]
    prior=json.loads((q.RAW/'native'/'3wvp-XAUUSD-BRK-1y'/'run.json').read_text())
    a=json.loads(gzip.decompress((OUT/'XAUUSD-parity'/'trades.json.gz').read_bytes()))
    b=json.loads(gzip.decompress((q.RAW/'native'/'3wvp-XAUUSD-BRK-1y'/'trades.json.gz').read_bytes()))
    clean=lambda trades:[{k:v for k,v in t.items() if k!='ea'} for t in trades]
    check=dict(metrics_equal=result['metrics']==prior['metrics'],trades_equal=clean(a)==clean(b))
    dump(ROOT/'parity.json',check)
    if not all(check.values()): raise RuntimeError('Search extensions OFF do not match raw '+str(check))

def search():
    parity_check=json.loads((ROOT/'parity.json').read_text())
    if not all(parity_check.values()): raise RuntimeError('No raw parity')
    qualified=json.loads((ROOT.parent/'qualification.json').read_text())
    for c in q.CFG['candidates']:
        if not any(x['status']=='QUALIFIED' and x['symbol']==c['symbol'] and x['variant']==c['variant'] for x in qualified): continue
        base=BASE|{'setups':c['setups']}; leaders=[base]; ledger=[]
        for stage in ['timeframe','entry','stop','trailing','rr_exit','session','direction','filters','management','profile']:
            cases=dedupe(leaders+[b|p for b in leaders for p in patches(stage,c['symbol'])])
            result=batch(c['symbol'],c['variant']+'-'+stage,cases)
            ledger.extend(dict(stage=stage,**r) for r in result)
            dump(ROOT/'SEARCH RESULTS.json',ledger)
            eligible=[r for r in result if score(r)>-1000]
            if not eligible:
                progress(state='rejected',stage=stage,reason='No positive candidate with >=60 development trades'); break
            leaders=[r['parameters'] for r in sorted(eligible,key=score,reverse=True)[:3]]
            dump(ROOT/'leaders.json',dict(symbol=c['symbol'],stage=stage,parameters=leaders,passes=len(ledger),unique=len({digest(r['parameters']) for r in ledger})))
        else:
            neighbors=[]
            for b in leaders:
                neighbors.extend(neighborhood(b))
            result=batch(c['symbol'],c['variant']+'-plateau',dedupe(neighbors))
            ledger.extend(dict(stage='plateau',**r) for r in result); dump(ROOT/'SEARCH RESULTS.json',ledger)
            finalists=[]
            for b in leaders:
                ids={digest(p) for p in neighborhood(b)}
                near=[r for r in result if digest(r['parameters']) in ids]
                fraction=sum(score(r)>-1000 for r in near)/max(1,len(near))
                if fraction>=2/3: finalists.append(b)
            dump(ROOT/'development-finalists.json',finalists)
            validated=[]
            for i,p in enumerate(finalists):
                r=batch(c['symbol'],f'{c["variant"]}-validation-{i}',[p],start='2024.09.26',end='2025.09.26',model=4,optimize=False)[0]
                if r['metrics']['profit_factor']>=1.15 and score(r,30)>-1000: validated.append(r)
            if not validated:
                progress(state='rejected',reason='No finalist passed validation'); continue
            winner=max(validated,key=lambda r:score(r,30)); dump(ROOT/'validation-selection.json',winner)
            holdout=batch(c['symbol'],c['variant']+'-holdout',[winner['parameters']],start='2019.09.26',end='2021.09.26',model=4,optimize=False)[0]
            accepted=holdout['metrics']['profit_factor']>=1.15 and score(holdout,30)>-1000
            dump(ROOT/'holdout-verdict.json',dict(passed=accepted,result=holdout,promotion_authorized=False))
            progress(state='holdout complete',passed=accepted,note='Monte Carlo and cost/coverage audit still required; no deployment')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('stage',choices=['parity','search','status']); args=ap.parse_args()
    if args.stage=='status':
        print((ROOT/'progress.json').read_text() if (ROOT/'progress.json').exists() else 'not started'); return
    # Share the qualification lock to prevent two harnesses using the same tester.
    lock=ROOT.parent/'.qualification.lock'; fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode()); os.close(fd)
    try: {'parity':parity,'search':search}[args.stage]()
    except BaseException as e:
        progress(state='failed',error=str(e)); raise
    finally: lock.unlink(missing_ok=True)

if __name__=='__main__': main()

