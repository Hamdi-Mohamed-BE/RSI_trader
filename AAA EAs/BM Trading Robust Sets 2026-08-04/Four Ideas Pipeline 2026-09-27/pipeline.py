"""Immutable raw gate runner. Uses only the isolated native tester, never live API."""
from pathlib import Path
import gzip,importlib.util,json,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
RAW=BASE/'Four Screenshot Ideas Raw 2026-09-27'
sys.path.insert(0,str(RAW))
import run as original
import audit
h=original.h
from app.mt5_evidence_jobs import _metric,_number
TESTER=original.TESTER
CASES=original.CFG['cases']
PERIODS={'6m':'2026.03.27','3y':'2023.09.27','5y':'2021.09.27'}
END='2026.09.27'

def save(path,obj):
 path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def status(message,**kw):
 print(message,flush=True)
 save(ROOT/'status.json',dict(message=message,updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw))

def freeze():
 b=json.loads((RAW/'BUILD.json').read_text())
 for name,key in [('FourIdeas.mq5','source_sha'),('FourIdeas.ex5','binary_sha'),('RULES.md','rules_sha'),('run-config.json','config_sha')]:
  assert h.sha(RAW/name)==b[key],name
 assert h.sha(original.DEST/'FourIdeas.ex5')==b['binary_sha']
 f=dict(raw_build=b,protocol_sha=h.sha(ROOT/'PROTOCOL.md'),runner_sha=h.sha(Path(__file__)),periods=PERIODS,end=END,
        gate=dict(min_pf=1.15,min_trades=30,positive_net=True,control='higher return/equityDD in BOTH 3y and 5y'),
        deployment=False)
 p=ROOT/'FROZEN.json'
 if p.exists():assert json.loads(p.read_text())==f,'Frozen configuration changed'
 else:save(p,f)
 return f

def run(case,period,model,frozen):
 tag=f"{case['id']}-{period}-m{model}"
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 if (out/'run.json').exists():
  r=json.loads((out/'run.json').read_text());assert r['ok'] and r['frozen']==frozen
  if not (out/'AUDIT.json').exists():audit.audit(out)
  status('Retained '+tag);return
 start=PERIODS[period]
 vals=dict(InpMode=case['mode'],InpControl=str(case['control']).lower(),InpRiskPercent=1.0,InpNotionalUSD=10000.0,InpServerUtcOffsetHours=0,InpMagic=9274040,InpTag=tag)
 setname='four-pipeline-'+tag+'.set'
 body='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8')
 (TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 common=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini'
 ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Four Ideas 20260927\\FourIdeas
ExpertParameters={setname}
Symbol={case['symbol']}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={END}
Report=reports\\four-pipeline-20260927\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=TESTER/'reports/four-pipeline-20260927';reportdir.mkdir(parents=True,exist_ok=True)
 original.free();offsets={p:p.stat().st_size for p in h.logfiles()};begin=time.time()
 status('START '+tag,case=tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own research test timed out: '+tag)
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<begin-2:continue
  with p.open('rb') as f:
   f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 report=reportdir/(tag+'.htm')
 assert report.exists() and report.stat().st_mtime>=begin-2,('Missing fresh report',journal[-3000:])
 actual=h._report_inputs(report)
 bad=[k for k,v in vals.items() if k not in actual or not h._same_setting(str(v),actual[k])]
 assert not bad,(tag,bad)
 rb=h._read_report(report)
 assert all(v in rb for v in (start,END,case['symbol'],'M1'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(p,journal,re.I)) for k,p in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed','margin_call':r'stop out|margin call','entry_fail':r'IDEA_ENTRY_FAIL','close_fail':r'IDEA_CLOSE_FAIL','cancel_fail':r'IDEA_CANCEL_FAIL'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_volume')),flags
 trades=h._native_trades(report,tag);metrics=h._native_metrics(report)
 metrics.update(max_equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),max_balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')),max_equity_dd_usd=_number(_metric(rb,'Equity Drawdown Maximal')))
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.11,(tag,len(trades),metrics)
 (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0));save(out/'trades.json',trades)
 r=dict(ok=True,case=case,period=period,model=model,start=start,end=END,inputs=actual,metrics=metrics,flags=flags,frozen=frozen,report_sha=h.sha(report),elapsed_seconds=time.time()-begin,summary=re.findall(r'IDEA_SUMMARY[^\r\n]+',journal),symbol_spec=re.findall(r'IDEA_SPEC[^\r\n]+',journal),real_ticks=sorted(set(re.findall(r'real ticks begin from[^\r\n]+',journal))))
 save(out/'run.json',r)
 a=audit.audit(out)
 status('DONE '+tag+' '+json.dumps(dict(return_pct=metrics['return_pct'],trades=len(trades),equity_dd=metrics['max_equity_dd_pct'],late=len(a['late_exits']))))

def main():
 frozen=freeze()
 stage=sys.argv[1] if len(sys.argv)>1 else 'all'
 if stage in ('screen','all'):
  for p in ('3y','5y'):
   for c in CASES:run(c,p,1,frozen)
 if stage in ('confirm','all'):
  for p in ('3y','5y'):
   for c in CASES:run(c,p,4,frozen)
  for c in CASES[:4]:run(c,'6m',4,frozen)
 status('COMPLETE '+stage)
if __name__=='__main__':main()
