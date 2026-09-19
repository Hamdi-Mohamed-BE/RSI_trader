from __future__ import annotations
import argparse
import configparser
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
RAW=PACKAGE/'D14 H1 M5 Break Retest Raw 2026-09-13'
spec=importlib.util.spec_from_file_location('raw_tools',RAW/'run_raw.py')
raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
TESTER=raw.TESTER
NAME='XAU D14 Break Retest Research'
SOURCE=ROOT/'EA'/f'{NAME}.mq5'
EXPERT=Path('AAA Research')/'D14 Full Pipeline 20260913'
CODE_HASH=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
TRAIN=('2021.09.05','2024.09.05')
VALID=('2024.09.05','2025.09.05')
LOCKED=('2025.09.05','2026.09.05')
DEFAULT={'InpRiskPercent':1.0,'InpH1Pivot':2,'InpM5Pivot':2,'InpZoneMode':0,'InpWickMode':0,
         'InpDirection':0,'InpHoldBars':3,'InpStopBufferATR':0.0,'InpTargetR':2.0,
         'InpManagement':0,'InpMaxHoldHours':0,'InpMaxZoneHours':0,'InpSessionStart':0,'InpSessionEnd':24}

def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False),encoding='utf-8')
def normalize(config):return {k:type(DEFAULT[k])(v) for k,v in {**DEFAULT,**config}.items()}
def signature(config):return hashlib.sha256(json.dumps(normalize(config),sort_keys=True).encode()).hexdigest()[:12]
def score(r,validation=False):
    count=r['trades'];minimum=5 if validation else 15;target=15 if validation else 50
    if count<minimum:return -10000+count
    pf=min(r['net_pf'] if r['net_pf'] is not None else 5,5)
    return 25*math.log(max(pf,.01))+.12*r['return_pct']-1.2*r['dd_pct']-.2*max(0,target-count)
def annotate_trades(trades,audit):
    accepted=[];signal=None
    for a in audit:
        if a['event']=='signal':signal=a
        elif a['event']=='accepted':
            assert signal is not None
            accepted.append((a,signal));signal=None
    assert len(trades)==len(accepted)
    for t,(a,s) in zip(trades,accepted):
        assert abs(t['open_price']-float(a['entry']))<.002
        t.update(initial_stop=float(a['stop']),initial_target=float(a['target']),planned_risk_cash=float(s['risk_cash']),
                 equity_at_signal=float(s['equity']),equity_after_entry=float(a['equity']),
                 entry_spread_cost=float(s['entry_spread_cost']))
    return trades
def prepare():
    for folder in (ROOT/'Runs',ROOT/'Sets',ROOT/'Backtest Reports',ROOT/'Audit',TESTER/'MQL5'/'Experts'/EXPERT,
                   TESTER/'backtest-configs'/'d14-full-pipeline',TESTER/'reports'/'d14-full-pipeline'):
        folder.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE,TESTER/'MQL5'/'Experts'/EXPERT/SOURCE.name)
    log=ROOT/'compile.log';started=time.time()
    command=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{TESTER/"MQL5"/"Experts"/EXPERT/SOURCE.name}" /log:"{log}"'
    subprocess.run(command,cwd=TESTER,timeout=120,startupinfo=raw.hidden())
    assert log.is_file() and log.stat().st_mtime>started-2
    detail=log.read_text(encoding='utf-16',errors='replace')
    if '0 errors, 0 warnings' not in detail:raise RuntimeError(detail)
    shutil.copy2(TESTER/'MQL5'/'Experts'/EXPERT/f'{NAME}.ex5',ROOT/'EA'/f'{NAME}.ex5')
    print('COMPILED: zero errors/warnings',flush=True)

def run(config,window=TRAIN,model=1,delay=1,stage='screen'):
    config=normalize(config);cs=signature(config)
    tag=f'{stage}-{cs}-{window[0].replace(".","")}-{window[1].replace(".","")}-m{model}-d{delay}'
    saved=ROOT/'Runs'/f'{tag}.json'
    if saved.exists():
        r=json.loads(saved.read_text())
        if r['source_sha256']==CODE_HASH:return r
        raise RuntimeError(f'Existing result source differs: {tag}. Preserve evidence and use a new output folder.')
    magic=84200000+int(hashlib.sha256(tag.encode()).hexdigest()[:7],16)
    settings={**config,'InpMagic':magic,'InpDeviationPoints':30,'InpExportBars':False}
    render=lambda v:str(v).lower() if isinstance(v,bool) else str(v)
    setname=tag+'.set'
    (ROOT/'Sets'/setname).write_text(''.join(f'{k}={render(v)}\n' for k,v in settings.items()),encoding='utf-8')
    shutil.copy2(ROOT/'Sets'/setname,TESTER/'MQL5'/'Profiles'/'Tester'/setname)
    reference=configparser.ConfigParser();reference.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(reference['Common'])
    ini='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Tester]\n'
    ini+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setname}\nSymbol=XAUUSD\nPeriod=M5\n'
    ini+=f'Login={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode={delay}\nOptimization=0\n'
    ini+=f'FromDate={window[0]}\nToDate={window[1]}\nForwardMode=0\nReport=reports\\d14-full-pipeline\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    cfg=TESTER/'backtest-configs'/'d14-full-pipeline'/f'{tag}.ini';cfg.write_text(ini,encoding='utf-16')
    oldlogs={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')}
    started=time.time();print('START '+tag,flush=True)
    proc=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=raw.hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:proc.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        proc.kill();raise RuntimeError(f'Owned research tester timed out: {tag}')
    report=TESTER/'reports'/'d14-full-pipeline'/f'{tag}.htm'
    if not report.is_file() or report.stat().st_mtime<started-2:raise RuntimeError(f'No fresh report: {tag}')
    for p in report.parent.glob(tag+'*'):shutil.copy2(p,ROOT/'Backtest Reports'/p.name)
    audits=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/D14Optimized-{magic}.csv') if p.stat().st_mtime>started-2]
    if len(audits)!=1:raise RuntimeError(f'Missing or ambiguous fresh audit {tag}')
    auditfile=ROOT/'Audit'/f'{tag}.csv';shutil.copy2(audits[0],auditfile)
    journal=''
    for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if p.stat().st_mtime<started-2:continue
        with p.open('rb') as f:f.seek(oldlogs.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
    (ROOT/'Audit'/f'{tag}-journal.log').write_text(journal,encoding='utf-8')
    metrics,trades=raw.report_stats(report,'XAU D14 break/retest research')
    audit=list(csv.DictReader(auditfile.open(encoding='utf-8-sig')))
    annotate_trades(trades,audit)
    dump(ROOT/'Audit'/f'{tag}-trades.json',trades)
    row={'tag':tag,'config':config,'config_id':cs,'source_sha256':CODE_HASH,'stage':stage,'window':window,'model':model,'delay_ms':delay,
         'elapsed_seconds':round(time.time()-started,2),'dd_pct':raw.parser.percent(metrics['equity_dd_relative']),
         'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
         'errors':[r for r in audit if r['event'] in ('error','manage_error')],
         'zones':sum(r['event']=='zone' for r in audit),'holds':sum(r['event']=='held' for r in audit),
         'signals':sum(r['event']=='signal' for r in audit),'trail_updates':sum(r['event']=='trail' for r in audit),
         'time_exits':sum(r['event']=='time_exit' for r in audit),
         'quality_journal':[line for line in journal.splitlines() if re.search('real ticks|execution delay|RAW CONTRACT|SELF TEST',line,re.I)],**metrics}
    row['score']=score(row);dump(saved,row)
    print('DONE '+json.dumps({'stage':stage,'id':cs,'n':row['trades'],'return':round(row['return_pct'],2),'pf':round(row['net_pf'] or 0,3),'dd':row['dd_pct'],'score':round(row['score'],2)}),flush=True)
    return row

def top_distinct(rows,n):
    found={}
    for r in sorted(rows,key=lambda r:(r['score'],r['trades']),reverse=True):
        if r['config_id'] not in found:found[r['config_id']]=r
        if len(found)==n:break
    return list(found.values())
def parity():
    r=run(DEFAULT,raw.WINDOWS['6m'],4,stage='parity')
    original=json.loads((RAW/'Audit'/'xauusd-d14-raw-6m-model4-trades.json').read_text())
    actual=json.loads((ROOT/'Audit'/f'{r["tag"]}-trades.json').read_text())
    keys=['open_time','close_time','side','volume','open_price','close_price','gross_profit','commission','swap','net_profit']
    assert [{k:t[k] for k in keys} for t in original]==[{k:t[k] for k in keys} for t in actual]
    dump(ROOT/'raw-parity.json',{'passed':True,'trades':len(actual),'source_sha256':CODE_HASH,'compared_fields':keys})
    print('RAW PARITY PASSED: all seven trades and costs exactly match.',flush=True)

def search():
    rows=[]
    for hp,mp,zone,wick,side in itertools.product((1,2),(1,2),(0,1),(0,1),(0,1,-1)):
        c={**DEFAULT,'InpH1Pivot':hp,'InpM5Pivot':mp,'InpZoneMode':zone,'InpWickMode':wick,'InpDirection':side}
        rows.append(run(c,stage='structure'))
    leaders=top_distinct(rows,3);dump(ROOT/'stage-structure.json',{'leaders':[r['config'] for r in leaders],'runs':[r['tag'] for r in rows]})
    for leader in leaders:
        for buf,rr in itertools.product((0,.10,.25),(.75,1,1.5,2,3)):
            c={**leader['config'],'InpStopBufferATR':buf,'InpTargetR':rr};rows.append(run(c,stage='exits'))
    leaders=top_distinct(rows,2);dump(ROOT/'stage-exits.json',{'leaders':[r['config'] for r in leaders]})
    for leader in leaders:
        for management,hours in ((0,0),(1,0),(2,0),(3,0),(0,6),(0,24)):
            c={**leader['config'],'InpManagement':management,'InpMaxHoldHours':hours};rows.append(run(c,stage='management'))
    leader=top_distinct(rows,1)[0]
    for change in ({'InpHoldBars':4},{'InpHoldBars':5},{'InpMaxZoneHours':8},{'InpMaxZoneHours':24},
                   {'InpSessionStart':6,'InpSessionEnd':16},{'InpSessionStart':12,'InpSessionEnd':20}):
        rows.append(run({**leader['config'],**change},stage='filters'))
    finalists=top_distinct(rows,5)
    dump(ROOT/'search-finalists.json',{'development_only':True,'finalists':[r['config'] for r in finalists],'screen_runs':[r['tag'] for r in rows],
                                     'unique_screen_configs':len({r['config_id'] for r in rows})})
    return finalists

def select(finalists):
    candidates=[]
    for f in finalists:
        train=run(f['config'],TRAIN,4,stage='confirm-train');valid=run(f['config'],VALID,4,stage='confirm-validation')
        eligible=train['trades']>=30 and valid['trades']>=10 and train['net_profit']>0 and valid['net_profit']>0 and (train['net_pf'] or 0)>1 and (valid['net_pf'] or 0)>1
        scores=[score(train),score(valid,True)]
        candidates.append({'config':f['config'],'train':train['tag'],'validation':valid['tag'],'eligible':eligible,'worst_score':min(scores),'mean_score':sum(scores)/2})
    chosen=max(candidates,key=lambda r:(r['eligible'],r['worst_score'],r['mean_score']))
    freeze=ROOT/'frozen-selection.json'
    if freeze.exists():
        previous=json.loads(freeze.read_text())
        assert previous['selected']==chosen,'Frozen selection would change; stop rather than retune using final-year evidence.'
        return previous['selected']
    payload={'frozen_at_epoch':time.time(),'selected':chosen,'candidates':candidates,'selection_uses_final_year':False}
    dump(ROOT/'frozen-selection.json',payload);print('FROZEN SELECTION '+json.dumps(chosen),flush=True)
    return chosen

def neighbours(c):
    return [{**c,'InpH1Pivot':max(1,c['InpH1Pivot']-1) if c['InpH1Pivot']>1 else 2},
            {**c,'InpM5Pivot':max(1,c['InpM5Pivot']-1) if c['InpM5Pivot']>1 else 2},
            {**c,'InpTargetR':max(.25,c['InpTargetR']-.25)},{**c,'InpTargetR':c['InpTargetR']+.25},
            {**c,'InpStopBufferATR':max(0,c['InpStopBufferATR']-.05) if c['InpStopBufferATR'] else .05},
            {**c,'InpStopBufferATR':c['InpStopBufferATR']+.10},
            {**c,'InpHoldBars':max(2,c['InpHoldBars']-1)},{**c,'InpHoldBars':c['InpHoldBars']+1}]
def final_stage(selected):
    c=selected['config'];result={}
    for p,w in raw.WINDOWS.items():result[p]=run(c,w,4,stage='final-'+p)['tag']
    for p in ('1y','5y'):result['safe-'+p]=run({**c,'InpRiskPercent':.5},raw.WINDOWS[p],4,stage='safe-'+p)['tag']
    for delay in (500,2000):result[f'delay-{delay}']=run(c,LOCKED,4,delay,stage='latency')['tag']
    result['neighbours']=[run(n,VALID,4,stage='neighbour')['tag'] for n in neighbours(c)]
    dump(ROOT/'final-runs.json',result)
    saved=ROOT/'Sets'/'SELECTED RESEARCH ONLY - XAU D14 Break Retest.set'
    saved.write_text(''.join(f'{k}={v}\n' for k,v in c.items()),encoding='utf-8')
    return result

def walk_forward():
    anchors=[{**DEFAULT,'InpM5Pivot':mp,'InpZoneMode':zone,'InpWickMode':zone,'InpDirection':side}
             for mp,zone,side in itertools.product((1,2),(0,1),(0,1))]
    folds=[]
    for year in (2023,2024,2025):
        train=(f'{year-2}.09.05',f'{year}.09.05');test=(f'{year}.09.05',f'{year+1}.09.05')
        rows=[run(c,train,1,stage=f'wf-{year}-train') for c in anchors]
        winner=top_distinct(rows,1)[0];testrow=run(winner['config'],test,4,stage=f'wf-{year}-test')
        folds.append({'train':train,'test':test,'winner':winner['config'],'train_report':winner['tag'],'test_report':testrow['tag']})
        dump(ROOT/'walk-forward.json',{'anchors':anchors,'folds':folds})
    return folds

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--stage',choices=('all','parity','search','finish'),default='all');args=cli.parse_args()
    prepare()
    if args.stage in ('all','parity'):parity()
    if args.stage=='parity':return
    if args.stage in ('all','search'):finalists=search()
    else:finalists=[{'config':c} for c in json.loads((ROOT/'search-finalists.json').read_text())['finalists']]
    if args.stage=='search':return
    selected=select(finalists);final_stage(selected);walk_forward()
    print('ALL NATIVE STAGES COMPLETE. Statistical/cost/logic audit remains.',flush=True)
if __name__=='__main__':main()
