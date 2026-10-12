"""Isolated native raw DMC comparison. Never attaches to the running trading terminal."""
from pathlib import Path
import argparse, importlib.util, hashlib, json, os, re, shutil, subprocess, time

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('dated_dmc_runner',PACKAGE/'DMC Video Levels Research 2026-09-25/run_dmc.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.ROOT=ROOT
native.OUT=ROOT/'native'
native.STATUS=native.OUT/'status.json'
native.REPORT_DIR=native.TESTER/'reports/calyx-dmc-video-levels'
SOURCE=ROOT/'EA/Calyx DMC Multi Timeframe Research.mq5'
EXPERT='Calyx DMC Multi Timeframe Research.ex5'
SETS='Selected Portfolio Settings 2026-09-01/'
CONFIG={
    'login':native.CONFIG['login'],'server':native.CONFIG['server'],
    'profile':'Calyx Research Empty','deposit':10000,'currency':'USD','leverage':'1:2000',
    'model':4,'execution_delay_ms':150,'period':'H1','timeout_seconds':2400,
    'end_date':'2026.10.12',
    'periods':{'3m':'2026.07.12','6m':'2026.04.12','1y':'2025.10.12','3y':'2023.10.12'},
    'expert_dir':r'AAA Research\DMC Exact Video 20261012',
    'portable_overrides':{'InpDmCStopMode':'1','InpDmCStopATR':'1.5'},
    'variants':{'BASE':{'overrides':{}}},
    'eas':{
        'current':{'production_ex5':'AAA Final EAs/AAA Final DmC EA/AAA Final DmC EA.ex5','production_expert_file':'DMC Current Production.ex5','research_expert_file':'DMC Current Production.ex5'},
        'fresh':{'production_ex5':'AAA Final EAs/Calyx DMC Fresh Reaction EA/Calyx DMC Fresh Reaction EA.ex5','production_expert_file':'DMC Fresh Reaction Production.ex5','research_expert_file':'DMC Fresh Reaction Production.ex5'},
        'video':{'production_ex5':str(SOURCE.with_suffix('.ex5').relative_to(PACKAGE)),'production_expert_file':EXPERT,'research_expert_file':EXPERT},
    },
    'configs':{
        'CUR':{'label':'Current DMC Gold','ea':'current','set':SETS+'07 DmC - ASIA 3R - DYNAMIC 50-20.set','native_symbol':'XAUUSD'},
        'FRX':{'label':'Fresh Reaction Gold','ea':'fresh','set':SETS+'21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set','native_symbol':'XAUUSD'},
        'FRU':{'label':'Fresh Reaction US100','ea':'fresh','set':SETS+'22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set','native_symbol':'USTEC'},
        'BTCTRANSFER':{'label':'Fresh Reaction US100 rules transferred to BTC (not active)','ea':'fresh','set':SETS+'22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set','native_symbol':'USTEC'},
        'VIDEO':{'label':'New multi-timeframe DMC reconstruction','ea':'video','set':str((ROOT/'Video.set').relative_to(PACKAGE)),'native_symbol':''},
    },
}
native.CONFIG=CONFIG
CONFIG['configs']={'OCT12_'+key:value for key,value in CONFIG['configs'].items()}
original_set=native.set_text
def settings(key,symbol,variant):
    if key=='OCT12_VIDEO':return (ROOT/'Video.set').read_text()
    return original_set(key,symbol,variant)
native.set_text=settings

def compile_new():
    log=SOURCE.with_suffix('.compile.log')
    began=time.time()
    command=f'"{native.TESTER / "MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"'
    subprocess.run(command,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    body=native.text(log) if log.is_file() else ''
    if not re.search(r'\b0 errors?, 0 warnings?\b',body):raise RuntimeError(body[-4000:])
    binary=SOURCE.with_suffix('.ex5')
    assert binary.is_file() and binary.stat().st_mtime>=began-2
    frozen={
        'source_sha256':native.sha(SOURCE),'ex5_sha256':native.sha(binary),
        'plan_sha256':native.sha(ROOT/'PLAN.json'),'set_sha256':native.sha(ROOT/'Video.set'),
        'caption_sha256':native.sha(ROOT/'t9Bssop4uqo.en-orig.json3'),
        'control_ex5_sha256':{k:native.sha(PACKAGE/e['production_ex5']) for k,e in CONFIG['eas'].items() if k!='video'},
        'compile_tail':body[-500:],'created_utc':native.now(),
    }
    (ROOT/'BUILD.json').write_text(json.dumps(frozen,indent=2))
    print(body[-500:],flush=True)

def validate_freeze():
    build=json.loads((ROOT/'BUILD.json').read_text())
    assert build['source_sha256']==native.sha(SOURCE)
    assert build['ex5_sha256']==native.sha(SOURCE.with_suffix('.ex5'))
    assert build['plan_sha256']==native.sha(ROOT/'PLAN.json')
    assert build['set_sha256']==native.sha(ROOT/'Video.set')
    for key,digest in build['control_ex5_sha256'].items():assert digest==native.sha(PACKAGE/CONFIG['eas'][key]['production_ex5'])

def run_one(key,symbol,period):
    CONFIG['period']='M15' if key=='VIDEO' else 'H1'
    result=native.run_case('OCT12_'+key,symbol,'BASE',period)
    if result['journal_flags']['critical'] or result['journal_flags']['init_failed']:
        raise RuntimeError('Native initialization/runtime failure '+result['case'])
    trades=json.loads((native.OUT/result['case']/'trades.json').read_text())
    if len(trades)!=result['metrics']['trades']:
        raise RuntimeError('Native deal count does not match report '+result['case'])
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['compile','smoke','all','summary'])
    args=parser.parse_args()
    native.OUT.mkdir(exist_ok=True)
    if args.stage=='compile':compile_new();return
    validate_freeze()
    if native.isolated_running():raise RuntimeError('Isolated tester already running; refuse contention')
    destination=native.TESTER/'MQL5/Experts'/CONFIG['expert_dir']
    destination.mkdir(parents=True,exist_ok=True)
    for ea in CONFIG['eas'].values():
        shutil.copy2(PACKAGE/ea['production_ex5'],destination/ea['production_expert_file'])
    if args.stage=='smoke':
        run_one('CUR','XAUUSD','3m');run_one('VIDEO','XAUUSD','3m')
    elif args.stage=='all':
        for period in CONFIG['periods']:
            for key,symbol in [('CUR','XAUUSD'),('FRX','XAUUSD'),('VIDEO','XAUUSD'),('FRU','USTEC'),('VIDEO','USTEC'),('BTCTRANSFER','BTCUSD'),('VIDEO','BTCUSD')]:
                run_one(key,symbol,period)
    records=[]
    for path in sorted(native.OUT.glob('dmcv-*/run.json')):
        row=json.loads(path.read_text())
        if row.get('ok'):records.append(row)
    (ROOT/'RESULTS.json').write_text(json.dumps(records,indent=2))
    native.status(state='done',event=f'{args.stage} completed; {len(records)} matching native cases')

if __name__=='__main__':main()
